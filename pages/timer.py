import streamlit as st
import time
import pandas as pd

# --- 1. 블라인드 구조 설정  ---
# type: 'level' or 'break'
# duration: 분 단위
STRUCTURE = [
    {"type": "level", "sb": 200, "bb": 400, "ante": 0, "time": 10},
    {"type": "level", "sb": 400, "bb": 800, "ante": 0, "time": 20}, # 20분? (데이터엔 20이라 적혀있는데, 확인 필요. 일단 입력값대로)
    {"type": "level", "sb": 600, "bb": 1200, "ante": 0, "time": 30},
    {"type": "level", "sb": 800, "bb": 1600, "ante": 0, "time": 40},
    {"type": "level", "sb": 1000, "bb": 2000, "ante": 0, "time": 50},
    {"type": "break", "time": 10, "msg": "100칩 제거 (Color Up)"},
    {"type": "level", "sb": 1500, "bb": 3000, "ante": 0, "time": 60},
    {"type": "level", "sb": 2000, "bb": 4000, "ante": 0, "time": 70},
    {"type": "level", "sb": 2500, "bb": 5000, "ante": 0, "time": 80},
    {"type": "level", "sb": 3000, "bb": 6000, "ante": 0, "time": 90},
    {"type": "level", "sb": 3500, "bb": 7000, "ante": 0, "time": 100},
    {"type": "level", "sb": 4000, "bb": 8000, "ante": 0, "time": 110},
    {"type": "level", "sb": 4500, "bb": 9000, "ante": 0, "time": 120},
    {"type": "break", "time": 10, "msg": "500칩 제거 (Color Up)"},
    {"type": "level", "sb": 5000, "bb": 10000, "ante": 0, "time": 130},
    {"type": "level", "sb": 6000, "bb": 12000, "ante": 0, "time": 140},
    {"type": "level", "sb": 7000, "bb": 14000, "ante": 0, "time": 150},
    {"type": "level", "sb": 8000, "bb": 16000, "ante": 0, "time": 160},
    {"type": "level", "sb": 9000, "bb": 18000, "ante": 0, "time": 170},
    {"type": "level", "sb": 10000, "bb": 20000, "ante": 0, "time": 180},
]

# --- 2. 상태 초기화 함수 ---
def init_state():
    if 'level_idx' not in st.session_state:
        st.session_state.level_idx = 0
    if 'time_left' not in st.session_state:
        # 첫 레벨 시간으로 초기화 (분 -> 초 변환)
        st.session_state.time_left = STRUCTURE[0]['time'] * 60
    if 'is_running' not in st.session_state:
        st.session_state.is_running = False

init_state()

# --- 3. 타이머 로직 ---
st.set_page_config(page_title="홀덤 타이머", page_icon="⏱️", layout="wide")

# 사이드바 (컨트롤 패널)
with st.sidebar:
    st.header("🎮 컨트롤러")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ 시작", type="primary"):
            st.session_state.is_running = True
            st.rerun()
    with col2:
        if st.button("⏸ 일시정지"):
            st.session_state.is_running = False
            st.rerun()
            
    st.divider()
    
    if st.button("⏭ 다음 레벨 강제 이동"):
        if st.session_state.level_idx < len(STRUCTURE) - 1:
            st.session_state.level_idx += 1
            st.session_state.time_left = STRUCTURE[st.session_state.level_idx]['time'] * 60
            st.session_state.is_running = False # 안전하게 일시정지 상태로
            st.rerun()

    if st.button("⏮ 이전 레벨로 복구"):
        if st.session_state.level_idx > 0:
            st.session_state.level_idx -= 1
            st.session_state.time_left = STRUCTURE[st.session_state.level_idx]['time'] * 60
            st.session_state.is_running = False
            st.rerun()

    if st.button("🔄 처음부터 리셋"):
        st.session_state.level_idx = 0
        st.session_state.time_left = STRUCTURE[0]['time'] * 60
        st.session_state.is_running = False
        st.rerun()

    st.info(f"초기 스택: 36,000 chip")

# --- 4. 메인 화면 표시 ---
current_data = STRUCTURE[st.session_state.level_idx]

# (1) 헤더 정보
st.markdown("<h1 style='text-align: center;'>🏆 Texas Hold'em Tournament 🏆</h1>", unsafe_allow_html=True)

# (2) 현재 블라인드 표시 (엄청 크게)
st.markdown("---")

if current_data['type'] == 'level':
    sb = f"{current_data['sb']:,}"
    bb = f"{current_data['bb']:,}"
    display_text = f"<div style='font-size: 80px; font-weight: bold; text-align: center; color: #FF4B4B;'>{sb} / {bb}</div>"
    sub_text = "<div style='text-align: center; font-size: 20px; color: gray;'>BLINDS</div>"
else:
    # 쉬는 시간
    display_text = f"<div style='font-size: 60px; font-weight: bold; text-align: center; color: #00CC96;'>☕ BREAK TIME</div>"
    sub_text = f"<div style='text-align: center; font-size: 25px; color: orange;'>⚠️ {current_data['msg']}</div>"

st.markdown(display_text, unsafe_allow_html=True)
st.markdown(sub_text, unsafe_allow_html=True)
st.markdown("---")

# (3) 타이머 (초 단위 갱신)
timer_placeholder = st.empty()

# 실행 중이면 1초씩 감소
if st.session_state.is_running:
    if st.session_state.time_left > 0:
        # 시간 포맷팅 (MM:SS)
        mins, secs = divmod(st.session_state.time_left, 60)
        timer_str = f"{mins:02d}:{secs:02d}"
        
        # 화면 갱신
        timer_placeholder.markdown(f"<div style='font-size: 120px; font-weight: bold; text-align: center;'>{timer_str}</div>", unsafe_allow_html=True)
        
        time.sleep(1) # 1초 대기
        st.session_state.time_left -= 1
        st.rerun() # 화면 다시 그리기
    else:
        # 시간이 다 됐을 때 (0초)
        st.session_state.is_running = False
        st.balloons() # 풍선 효과
        
        # 다음 레벨로 자동 설정 (자동 시작은 안 함)
        if st.session_state.level_idx < len(STRUCTURE) - 1:
            st.session_state.level_idx += 1
            st.session_state.time_left = STRUCTURE[st.session_state.level_idx]['time'] * 60
            st.success("레벨 종료! 다음 레벨을 시작하려면 시작 버튼을 누르세요.")
        else:
            st.success("모든 게임이 종료되었습니다!")
        st.rerun()

else:
    # 멈춰 있을 때도 시간은 보여줌
    mins, secs = divmod(st.session_state.time_left, 60)
    timer_str = f"{mins:02d}:{secs:02d}"
    timer_placeholder.markdown(f"<div style='font-size: 120px; font-weight: bold; text-align: center; color: #555;'>{timer_str}</div>", unsafe_allow_html=True)


# (4) 다음 레벨 예고
if st.session_state.level_idx < len(STRUCTURE) - 1:
    next_data = STRUCTURE[st.session_state.level_idx + 1]
    if next_data['type'] == 'level':
        next_info = f"Next: {next_data['sb']:,} / {next_data['bb']:,}"
    else:
        next_info = "Next: BREAK TIME"
    st.markdown(f"<div style='text-align: center; font-size: 20px; margin-top: 20px;'>🔜 {next_info}</div>", unsafe_allow_html=True)