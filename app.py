import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json
import time

# ==========================================
# 1. 설정 및 구글 시트 연동
# ==========================================
st.set_page_config(page_title="홀덤 클럽", layout="wide") # 전체 화면 사용

JSON_FILE = 'holdemmanager-487003-a8b3c20d5267.json'
SPREADSHEET_NAME = 'Holdem_Point_System' 
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_client():
    if os.path.exists(JSON_FILE):
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
    else:
        key_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    return gspread.authorize(creds)

# 시트 연결 (에러 방지)
try:
    client = get_client()
    doc = client.open(SPREADSHEET_NAME)
    sheet_log = doc.worksheet("Sheet1")
    try:
        sheet_members = doc.worksheet("Members")
    except:
        sheet_members = doc.add_worksheet(title="Members", rows=100, cols=2)
        sheet_members.append_row(["이름"])
except Exception as e:
    st.error(f"구글 시트 연결 실패: {e}")
    st.stop()

# ==========================================
# 2. 공통 함수 (캐싱 적용)
# ==========================================
@st.cache_data(ttl=60)
def load_data():
    return sheet_log.get_all_records()

@st.cache_data(ttl=600)
def get_member_list():
    members = sheet_members.col_values(1)
    return members[1:] if len(members) > 1 else []

def clear_cache():
    st.cache_data.clear()

def add_new_member(name):
    if name in get_member_list():
        return False, "이미 있는 이름입니다."
    sheet_members.append_row([name])
    clear_cache()
    return True, "등록 완료"

def add_log(name, point, reason, note=""):
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_log.append_row([date, name, point, reason, note])
    clear_cache()

# ==========================================
# 3. 화면 모드 선택 (사이드바)
# ==========================================
with st.sidebar:
    st.title("메뉴 선택")
    app_mode = st.radio("이동할 화면을 선택하세요", ["📊 메인 시스템 (랭킹/기록)", "⏱️ 대회용 타이머"])
    st.divider()
    st.info("Created for Hold'em Club")

# ==========================================
# [모드 1] 메인 시스템 (랭킹 & 관리)
# ==========================================
if app_mode == "📊 메인 시스템 (랭킹/기록)":
    st.title("♠️ 홀덤 동아리 랭킹 & 기록")
    
    tab1, tab2, tab3 = st.tabs(["📊 랭킹 확인", "📝 관리자 모드", "➕ 신규 회원"])

    # 1. 랭킹
    with tab1:
        if st.button("🔄 랭킹 새로고침"):
            clear_cache()
            st.rerun()
        
        data = load_data()
        df = pd.DataFrame(data)
        if not df.empty:
            ranking = df.groupby("이름")["포인트변동"].sum().reset_index()
            ranking = ranking.sort_values(by="포인트변동", ascending=False)
            ranking["순위"] = range(1, len(ranking) + 1)
            st.dataframe(ranking[["순위", "이름", "포인트변동"]], hide_index=True, use_container_width=True)
        else:
            st.info("데이터가 없습니다.")

    # 2. 관리자
    with tab2:
        pw = st.text_input("관리자 비밀번호", type="password")
        if pw == "1234":
            members = get_member_list()
            if members:
                opt = st.radio("작업", ["게임 결과", "리바인/구매", "출석", "딜러비"], horizontal=True)
                st.divider()
                
                if opt == "게임 결과":
                    c1,c2,c3 = st.columns(3)
                    w = c1.selectbox("1등", members, index=None)
                    s = c2.selectbox("2등", members, index=None)
                    t = c3.selectbox("3등", members, index=None)
                    if st.button("저장", type="primary"):
                        if w and s and t and len({w,s,t})==3:
                            add_log(w,7,"1등"); add_log(s,5,"2등"); add_log(t,3,"3등")
                            st.success("저장 완료"); st.rerun()
                        else: st.error("중복 선택 불가")
                
                elif opt == "리바인/구매":
                    who = st.selectbox("회원", members)
                    what = st.selectbox("항목", ["리바인 (-5p)", "대회 (-20p)"])
                    if st.button("차감"):
                        p = -5 if "리바인" in what else -20
                        add_log(who, p, what)
                        st.success("완료"); st.rerun()
                        
                elif opt == "출석":
                    ppl = st.multiselect("참석자", members)
                    if st.button("일괄 출석"):
                        for p in ppl: add_log(p, 1, "출석")
                        st.success("완료"); st.rerun()

                elif opt == "딜러비":
                    d = st.selectbox("딜러", members, index=None)
                    if st.button("지급"):
                        add_log(d, 3, "딜러 보너스")
                        st.success("완료"); st.rerun()
            else:
                st.warning("회원부터 등록하세요.")

    # 3. 신규 회원
    with tab3:
        nm = st.text_input("닉네임")
        if st.button("등록"):
            suc, msg = add_new_member(nm)
            if suc: st.success(msg); st.rerun()
            else: st.error(msg)

# ==========================================
# [모드 2] 대회용 타이머
# ==========================================
elif app_mode == "⏱️ 대회용 타이머":
    
    # 블라인드 구조
    STRUCTURE = [
        {"type": "level", "sb": 200, "bb": 400, "time": 10},
        {"type": "level", "sb": 400, "bb": 800, "time": 20},
        {"type": "level", "sb": 600, "bb": 1200, "time": 30},
        {"type": "level", "sb": 800, "bb": 1600, "time": 40},
        {"type": "level", "sb": 1000, "bb": 2000, "time": 50},
        {"type": "break", "time": 10, "msg": "100칩 제거 (Color Up)"},
        {"type": "level", "sb": 1500, "bb": 3000, "time": 60},
        {"type": "level", "sb": 2000, "bb": 4000, "time": 70},
        {"type": "level", "sb": 2500, "bb": 5000, "time": 80},
        {"type": "level", "sb": 3000, "bb": 6000, "time": 90},
        {"type": "level", "sb": 3500, "bb": 7000, "time": 100},
        {"type": "level", "sb": 4000, "bb": 8000, "time": 110},
        {"type": "level", "sb": 4500, "bb": 9000, "time": 120},
        {"type": "break", "time": 10, "msg": "500칩 제거 (Color Up)"},
        {"type": "level", "sb": 5000, "bb": 10000, "time": 130},
        {"type": "level", "sb": 6000, "bb": 12000, "time": 140},
        {"type": "level", "sb": 7000, "bb": 14000, "time": 150},
        {"type": "level", "sb": 8000, "bb": 16000, "time": 160},
        {"type": "level", "sb": 9000, "bb": 18000, "time": 170},
        {"type": "level", "sb": 10000, "bb": 20000, "time": 180},
    ]

    # 세션 상태 초기화
    if 'level_idx' not in st.session_state: st.session_state.level_idx = 0
    if 'time_left' not in st.session_state: st.session_state.time_left = STRUCTURE[0]['time'] * 60
    if 'is_running' not in st.session_state: st.session_state.is_running = False
    
    # 컨트롤러 (상단 배치)
    col1, col2, col3, col4, col5 = st.columns([1,1,1,1,2])
    with col1:
        if st.button("▶ 시작", type="primary", use_container_width=True):
            st.session_state.is_running = True
            st.rerun()
    with col2:
        if st.button("⏸ 정지", use_container_width=True):
            st.session_state.is_running = False
            st.rerun()
    with col3:
        if st.button("⏮ 이전", use_container_width=True):
            if st.session_state.level_idx > 0:
                st.session_state.level_idx -= 1
                st.session_state.time_left = STRUCTURE[st.session_state.level_idx]['time'] * 60
                st.session_state.is_running = False; st.rerun()
    with col4:
        if st.button("⏭ 다음", use_container_width=True):
            if st.session_state.level_idx < len(STRUCTURE)-1:
                st.session_state.level_idx += 1
                st.session_state.time_left = STRUCTURE[st.session_state.level_idx]['time'] * 60
                st.session_state.is_running = False; st.rerun()
    with col5:
        st.markdown(f"**Level {st.session_state.level_idx + 1} / {len(STRUCTURE)}**")

    # 화면 표시
    current = STRUCTURE[st.session_state.level_idx]
    
    st.markdown("---")
    if current['type'] == 'level':
        st.markdown(f"<div style='font-size: 80px; font-weight: bold; text-align: center; color: #FF4B4B; line-height: 1.0;'>{current['sb']:,} / {current['bb']:,}</div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center; font-size: 20px; color: gray;'>BLINDS</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='font-size: 60px; font-weight: bold; text-align: center; color: #00CC96; line-height: 1.0;'>☕ BREAK TIME</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: center; font-size: 25px; color: orange;'>⚠️ {current['msg']}</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 타이머 표시
    mins, secs = divmod(st.session_state.time_left, 60)
    timer_color = "black" if st.session_state.is_running else "#888"
    st.markdown(f"<div style='font-size: 140px; font-weight: bold; text-align: center; color: {timer_color}; line-height: 1.0; font-family: monospace;'>{mins:02d}:{secs:02d}</div>", unsafe_allow_html=True)

    # 자동 실행 로직
    if st.session_state.is_running and st.session_state.time_left > 0:
        time.sleep(1)
        st.session_state.time_left -= 1
        st.rerun()
    elif st.session_state.is_running and st.session_state.time_left == 0:
        st.session_state.is_running = False
        st.balloons()
        if st.session_state.level_idx < len(STRUCTURE)-1:
             st.session_state.level_idx += 1
             st.session_state.time_left = STRUCTURE[st.session_state.level_idx]['time'] * 60
             st.success("레벨업! 시작 버튼을 누르세요.")
        st.rerun()
        
    # 다음 레벨 예고
    if st.session_state.level_idx < len(STRUCTURE) - 1:
        nxt = STRUCTURE[st.session_state.level_idx + 1]
        msg = f"{nxt['sb']:,} / {nxt['bb']:,}" if nxt['type']=='level' else "BREAK TIME"
        st.markdown(f"<div style='text-align: center; color: gray; margin-top: 30px;'>Next: {msg}</div>", unsafe_allow_html=True)
