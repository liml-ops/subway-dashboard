import streamlit as st
import json
import time
import numpy as np
from datetime import datetime
import base64
import os
import random  
import pytz  

# ==========================================
# 1. 页面配置 & 图片 Base64 转换引擎
# ==========================================
st.set_page_config(page_title="PIDS 智慧站台终端", page_icon="🚇", layout="wide", initial_sidebar_state="collapsed")

def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return f"url('data:image/png;base64,{base64.b64encode(img_file.read()).decode()}')"
    else:
        return "linear-gradient(to right, #e0eafc, #cfdef3)"  

LOCAL_IMAGE_PATH = "image_0.png"
bg_css_url = get_base64_image(LOCAL_IMAGE_PATH)

# 🚨 极简通透风格 (Glassmorphism) UI 重构 + 🌟 手机自适应 🚨
CSS_STYLE = """
    <style>
    /* 默认：强制锁定页面高度，强杀滚动条 */
    html, body, [data-testid="stAppViewContainer"] {
        overflow: hidden !important;
        background-image: BG_IMAGE_PLACEHOLDER;
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
        color: #0F172A; 
    }
    
    header {visibility: hidden;}
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}

    .block-container {
        max-width: 95% !important;
        padding-top: 1rem !important; 
        padding-bottom: 2rem !important; 
    }

    /* 强制接管原生 metric 组件 */
    [data-testid="stMetricValue"] * { color: #0F172A !important; font-weight: 900 !important; }
    [data-testid="stMetricLabel"] * { color: #0F172A !important; font-weight: 900 !important; font-size: 22px !important; }

    /* 顶部信息栏 */
    .header-bar {
        background: rgba(255, 255, 255, 0.25); 
        backdrop-filter: blur(12px); 
        padding: 12px 25px;
        border-radius: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid rgba(255, 255, 255, 0.8); 
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05); 
    }
    
    .station-name { font-size: 36px; font-weight: 900; color: #004D9D; letter-spacing: 2px; display: flex; align-items: center;}
    .time-display { font-size: 26px; font-weight: bold; color: #334155; font-family: monospace;}

    /* 站台标题 */
    .platform-title {
        font-size: 24px; font-weight: 900; color: #0F172A; 
        background: rgba(255, 255, 255, 0.2); backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.6); padding: 6px 20px; 
        border-radius: 8px; margin-top: 10px; margin-bottom: 10px;
        border-left: 6px solid #2563EB; display: inline-block;
    }

    /* 横幅 */
    .guide-banner {
        padding: 10px 15px; border-radius: 8px; font-size: 20px; font-weight: bold;
        text-align: center; margin-bottom: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        backdrop-filter: blur(5px);
    }
    .guide-normal { background-color: rgba(209, 250, 229, 0.7); border: 2px solid #10B981; color: #065F46; } 
    .guide-alert { background-color: rgba(220, 38, 38, 0.85); border: 2px solid #991B1B; color: #FFFFFF; animation: pulse-light 2s infinite;} 

    /* 车厢卡片 */
    .train-car-card {
        background-color: rgba(255, 255, 255, 0.15); backdrop-filter: blur(10px); 
        border-radius: 12px; padding: 15px; border: 1px solid rgba(255, 255, 255, 0.7); 
        border-top: 5px solid #475569; text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-bottom: 10px;
    }

    .car-number { font-size: 18px; color: #475569; margin-bottom: 8px; font-weight: bold;}
    .car-people { font-size: 34px; font-weight: 900; font-family: monospace; margin-bottom: 10px;}

    /* 进度条 */
    .progress-bg { background-color: rgba(226, 232, 240, 0.6); border-radius: 10px; height: 12px; width: 100%; overflow: hidden; border: 1px solid rgba(255,255,255,0.5);}
    .progress-fill { height: 100%; border-radius: 10px; transition: width 0.5s ease;}
    .fill-green { background-color: #10B981; }
    .fill-yellow { background-color: #F59E0B; }
    .fill-red { background-color: #EF4444; }

    /* 底部跑马灯 */
    .marquee-container {
        width: 100%; background-color: rgba(255, 255, 255, 0.85); color: #B45309;
        padding: 10px 0; font-size: 18px; font-weight: 900;
        position: fixed; bottom: 0; left: 0; z-index: 999;
        border-top: 3px solid #F59E0B; backdrop-filter: blur(8px);
    }

    @keyframes pulse-light {
        0% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.5); }
        70% { box-shadow: 0 0 0 15px rgba(220, 38, 38, 0); }
        100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
    }

    /* ========================================== */
    /* 🌟 核心魔法：手机端专属自适应逻辑 (Media Queries) */
    /* ========================================== */
    @media screen and (max-width: 768px) {
        /* 解除手机端的滚动条封印，允许上下滑动 */
        html, body, [data-testid="stAppViewContainer"] {
            overflow: auto !important; 
        }
        
        /* 顶部栏改为上下堆叠布局 */
        .header-bar {
            flex-direction: column;
            gap: 8px;
            padding: 15px;
        }
        
        /* 整体字体按比例缩小，避免撑爆屏幕 */
        .station-name { font-size: 26px; }
        .time-display { font-size: 20px; }
        .platform-title { font-size: 20px; }
        .guide-banner { font-size: 15px; padding: 8px; }
        
        /* 原生的 metric 字体也缩小一点 */
        [data-testid="stMetricLabel"] * { font-size: 16px !important; }
        [data-testid="stMetricValue"] * { font-size: 22px !important; }
        
        /* 车厢卡片字体调整 */
        .car-number { font-size: 16px; }
        .car-people { font-size: 28px; }
        
        /* 给底部跑马灯留出更多空间，防止挡住最后一个车厢 */
        .block-container { padding-bottom: 6rem !important; }
    }
    </style>
"""

st.markdown(CSS_STYLE.replace("BG_IMAGE_PLACEHOLDER", bg_css_url), unsafe_allow_html=True)

DATA_FILE = "realtime_data.json"


# ==========================================
# 2. 核心逻辑与数据生成 (Mock 引擎)
# ==========================================
def read_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data and "left_platform" in data and len(data["left_platform"]) > 0:
                return data
    except Exception:
        pass
    return None

def generate_mock_data():
    """🌟 演示模式引擎：随机生成逼真的候车人数"""
    zones = ["1号门", "2号门", "3号门", "4号门", "5号门", "6号门"]
    return {
        "left_platform": {zone: random.randint(1, 10) for zone in zones},
        "right_platform": {zone: random.randint(1, 12) for zone in zones}
    }

def generate_strategy(data, direction_name):
    counts = list(data.values())
    if sum(counts) == 0: return f"本站 {direction_name} 暂无客流，请安全候车。", "normal"

    mu = np.mean(counts)
    cv = np.std(counts) / mu if mu > 0 else 0
    max_door = max(data, key=data.get)
    min_door = min(data, key=data.get)

    if cv >= 0.15 and (data[max_door] - data[min_door] >= 2): 
        return f"🚨 {direction_name} {max_door}区域候车人数较多，建议您移步至 {min_door}区域 ➡", "alert"
    else:
        return f"🟢 {direction_name} 客流平稳，请有序排队乘车。", "normal"

def get_mock_arrival_time(offset=0):
    current_sec = int(time.time()) + offset
    eta_sec = 300 - (current_sec % 300)
    minutes = max(1, eta_sec // 60)
    return f"{minutes} 分钟"

def render_platform(p_data, p_title, direction_name, eta_offset, destination):
    st.markdown(f'<div class="platform-title">{p_title}</div>', unsafe_allow_html=True)

    eta_str = get_mock_arrival_time(eta_offset)

    col_info1, col_info2, col_info3 = st.columns([1, 1, 2.2])
    with col_info1:
        st.metric(label="📍 开往方向", value=destination)
    with col_info2:
        st.metric(label="⏳ 预计进站", value=eta_str)
    with col_info3:
        p_msg, p_status = generate_strategy(p_data, direction_name)
        banner_class = "guide-alert" if p_status == "alert" else "guide-normal"
        st.markdown(f'<div class="guide-banner {banner_class}">{p_msg}</div>', unsafe_allow_html=True)

    num_zones = len(p_data)
    if num_zones == 0:
        return

    cols = st.columns(num_zones)

    for i, (door, count) in enumerate(p_data.items()):
        max_capacity = 12
        percentage = min((count / max_capacity) * 100, 100)

        if i == 0 or i == num_zones - 1:
            temp_text = "❄️ 强冷 22℃"
        else:
            temp_text = "❄️ 弱冷 25℃"

        if count < 4:
            color_class, status_text = "fill-green", "舒适"
            text_color = '#059669'
            border_color = '#10B981'
        elif count < 7:
            color_class, status_text = "fill-yellow", "适中"
            text_color = '#D97706'
            border_color = '#F59E0B'
        else:
            color_class, status_text = "fill-red", "拥挤"
            text_color = '#DC2626'
            border_color = '#EF4444'

        html_str = f"""
        <div class="train-car-card" style="border-top-color: {border_color};">
            <div class="car-number">{door} 区域 | {temp_text}</div>
            <div class="car-people" style="color: {text_color};">
                {count} <span style="font-size: 20px;">人</span> <span style="font-size: 16px; color: #64748B;">({status_text})</span>
            </div>
            <div class="progress-bg">
                <div class="progress-fill {color_class}" style="width: {percentage}%;"></div>
            </div>
        </div>
        """
        cols[i].markdown(html_str, unsafe_allow_html=True)


# ==========================================
# 3. 实时渲染大屏界面
# ==========================================
placeholder = st.empty()

while True:
    data = read_data()
    if not data:
        data = generate_mock_data()
        
    # 🌟 强制指定亚洲/上海（北京时间）时区
    tz = pytz.timezone('Asia/Shanghai')
    now_str = datetime.now(tz).strftime("%H:%M:%S")

    with placeholder.container():
        st.markdown(f"""
            <div class="header-bar">
                <div class="station-name">
                    <svg viewBox="0 0 100 100" style="height: 38px; width: 38px; margin-right: 12px;">
                        <rect width="100" height="100" rx="20" fill="#004D9D"/>
                        <path d="M25 20 h30 c 25 0 35 15 35 30 s -10 30 -35 30 h -30 v -60 z" fill="none" stroke="white" stroke-width="8"/>
                        <path d="M40 40 h10 c 10 0 10 20 0 20 h -10 v -20 z" fill="white"/>
                    </svg>
                    北京地铁
                </div>
                <div class="time-display">⏱️ {now_str}</div>
            </div>
        """, unsafe_allow_html=True)

        l_data = data.get("left_platform", {})
        r_data = data.get("right_platform", {})

        if l_data:
            render_platform(l_data, "⬅️ 上行站台 (A方向)", "上行列车", 0, "软件园 / 高铁站")

        if l_data and r_data:
            st.markdown("<hr style='border: 1px solid rgba(255, 255, 255, 0.4); margin: 10px 0;'>",
                        unsafe_allow_html=True)

        if r_data:
            render_platform(r_data, "➡️ 下行站台 (B方向)", "下行列车", 150, "大学城 / 国际机场")
        
        st.markdown("<div style='height: 70px; width: 100%;'></div>", unsafe_allow_html=True)

        st.markdown("""
            <div class="marquee-container">
                <marquee scrollamount="8">
                    ⚠️ 站台安全提示：请在黄线外有序等候，遵循先下后上原则乘车，严禁倚靠屏蔽门。本系统实时监控双向客流，请根据指示选择人少区域候车！
                </marquee>
            </div>
        """, unsafe_allow_html=True)

    time.sleep(2)
