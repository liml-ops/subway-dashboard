import cv2
import json
import time
import os
import numpy as np
from ultralytics import YOLO

# ==========================================
# 1. 基础配置
# ==========================================
VIDEO_PATH = "D:\生成地铁站台人流视频.mp4"
CONFIDENCE_THRESHOLD = 0.20

CONFIG_DIR = "roi_data"
CONFIG_JSON = os.path.join(CONFIG_DIR, "roi_coords.json")

# 🌟 核心升级 1：放弃 pose 模型，使用最强大的标准目标检测模型！
# 它对只有半身、只有头部的遮挡人群极其敏感，绝不漏人！
model = YOLO("yolov8s.pt")

pts = []
polygons = {"left": [], "right": []}
scale_factor = 1.0


def get_display_scale(w, h, max_size=1280):
    global scale_factor
    if max(w, h) <= max_size:
        scale_factor = 1.0
        return w, h
    scale_factor = max_size / float(max(w, h))
    return int(w * scale_factor), int(h * scale_factor)


def draw_polygon_callback(event, x, y, flags, param):
    global pts, scale_factor
    if event == cv2.EVENT_LBUTTONDOWN:
        real_x = int(x / scale_factor)
        real_y = int(y / scale_factor)
        pts.append((real_x, real_y))


def load_or_draw_rois(cap):
    global pts, polygons, scale_factor
    os.makedirs(CONFIG_DIR, exist_ok=True)

    if os.path.exists(CONFIG_JSON):
        with open(CONFIG_JSON, "r") as f:
            data = json.load(f)
            left = [np.array(poly, dtype=np.int32).reshape((-1, 1, 2)) for poly in data.get("left", [])]
            right = [np.array(poly, dtype=np.int32).reshape((-1, 1, 2)) for poly in data.get("right", [])]
            return left, right

    ret, frame = cap.read()
    if not ret: return [], []

    orig_h, orig_w = frame.shape[:2]
    disp_w, disp_h = get_display_scale(orig_w, orig_h, max_size=1280)

    print("\n" + "=" * 60)
    print(f"📐 原始分辨率: {orig_w}x{orig_h} | 显示分辨率: {disp_w}x{disp_h}")
    print("⏸️ 画面已暂停！进入【空间立体 ROI 标定模式】")
    print("👉 重点：请把屏蔽门/玻璃门和地面一起圈起来，不要只画地面！")
    print("👉 按 L 存左侧，按 R 存右侧，Z 撤销，ESC 退出保存。")
    print("=" * 60 + "\n")

    cv2.namedWindow("Draw Ground ROI", cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback("Draw Ground ROI", draw_polygon_callback)

    while True:
        temp_frame = frame.copy()

        if len(pts) > 0:
            cv2.polylines(temp_frame, [np.array(pts, dtype=np.int32)], False, (0, 255, 255), 2)
            for p in pts: cv2.circle(temp_frame, p, 6, (0, 0, 255), -1)

        for poly in polygons["left"]:
            cv2.polylines(temp_frame, [np.array(poly, dtype=np.int32)], True, (0, 255, 0), 2)

        for poly in polygons["right"]:
            cv2.polylines(temp_frame, [np.array(poly, dtype=np.int32)], True, (255, 0, 0), 2)

        display_frame = cv2.resize(temp_frame, (disp_w, disp_h))
        cv2.imshow("Draw Ground ROI", display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key in [ord('l'), ord('L')]:
            if len(pts) >= 3: polygons["left"].append(pts); pts = []
        elif key in [ord('r'), ord('R')]:
            if len(pts) >= 3: polygons["right"].append(pts); pts = []
        elif key in [ord('z'), ord('Z')]:
            if len(pts) > 0: pts.pop()
        elif key == 27:
            break

    cv2.destroyAllWindows()
    with open(CONFIG_JSON, "w") as f:
        json.dump(polygons, f)
    print(f"✅ 配置生成完毕！")

    left = [np.array(poly, dtype=np.int32).reshape((-1, 1, 2)) for poly in polygons["left"]]
    right = [np.array(poly, dtype=np.int32).reshape((-1, 1, 2)) for poly in polygons["right"]]
    return left, right


def process_video():
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened(): return

    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    disp_w, disp_h = get_display_scale(orig_w, orig_h, max_size=1280)

    left_polygons, right_polygons = load_or_draw_rois(cap)

    if not left_polygons and not right_polygons:
        print("❌ 警告：你没有画任何区域！请删掉 roi_data 重画。")
        return

    print("🚀 【抗遮挡靶向分配版】启动！")
    cv2.namedWindow("Live Debug Viewer", cv2.WINDOW_AUTOSIZE)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        debug_frame = frame.copy()

        # YOLOv8 标准版，classes=0 代表只抓人
        results = model.predict(frame, classes=[0], conf=CONFIDENCE_THRESHOLD, verbose=False)

        for poly in left_polygons:
            cv2.polylines(debug_frame, [poly], isClosed=True, color=(0, 255, 0), thickness=2)
        for poly in right_polygons:
            cv2.polylines(debug_frame, [poly], isClosed=True, color=(255, 0, 0), thickness=2)

        total_ai = 0
        total_counted = 0

        output_data = {}
        if left_polygons: output_data["left_platform"] = {f"{i + 1}": 0 for i in range(len(left_polygons))}
        if right_polygons: output_data["right_platform"] = {f"{i + 1}": 0 for i in range(len(right_polygons))}

        if results[0].boxes is not None:
            boxes = results[0].boxes
            total_ai = len(boxes)

            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()

                # 🌟 核心升级 2：使用人体框的正中心作为探针，彻底无视下半身遮挡！
                cx = float((x1 + x2) / 2.0)
                cy = float((y1 + y2) / 2.0)

                # 画出黄色的中心判定点
                cv2.circle(debug_frame, (int(cx), int(cy)), 6, (0, 255, 255), -1)

                best_platform = None
                best_idx = -1
                max_dist = -float('inf')

                # 计算中心点离哪个“门空间”最近
                for j, poly in enumerate(left_polygons):
                    dist = cv2.pointPolygonTest(poly, (cx, cy), measureDist=True)
                    if dist > max_dist:
                        max_dist = dist
                        best_platform = "left_platform"
                        best_idx = j

                for j, poly in enumerate(right_polygons):
                    dist = cv2.pointPolygonTest(poly, (cx, cy), measureDist=True)
                    if dist > max_dist:
                        max_dist = dist
                        best_platform = "right_platform"
                        best_idx = j

                if best_platform is not None:
                    total_counted += 1
                    output_data[best_platform][f"{best_idx + 1}"] += 1

                    cv2.rectangle(debug_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    platform_label = "L" if "left" in best_platform else "R"
                    cv2.putText(debug_frame, f"{platform_label}-{best_idx + 1}",
                                (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

        with open("realtime_data.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f)

        status_color = (0, 255, 0) if total_ai == total_counted else (0, 0, 255)
        cv2.putText(debug_frame, f"AI Found: {total_ai} | Counted: {total_counted}", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, status_color, 4)

        display_frame = cv2.resize(debug_frame, (disp_w, disp_h))
        cv2.imshow("Live Debug Viewer", display_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    process_video()

#python backend_engine.py
#python -m streamlit run app.py