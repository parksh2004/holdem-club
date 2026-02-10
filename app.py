import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

import os
import json

# --- 1. 구글 시트 연동 설정 ---
JSON_FILE = 'holdemmanager-487003-a8b3c20d5267.json'
SPREADSHEET_NAME = 'Holdem_Point_System' 

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# 캐싱: 구글 연결 객체는 한 번만 만들어서 재사용
@st.cache_resource
def get_client():
    # 1. 내 컴퓨터(로컬)에 key.json이 있으면 그걸 씀
    if os.path.exists(JSON_FILE):
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
    # 2. 서버(클라우드)에는 파일이 없으니 '비밀 금고(Secrets)'를 씀
    else:
        # st.secrets에서 정보를 가져옴
        key_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    
    client = gspread.authorize(creds)
    return client

# 연결 시도
try:
    client = get_client()
    doc = client.open(SPREADSHEET_NAME)
    sheet_log = doc.worksheet("Sheet1")  # 기록용 시트 (기존 시트)
    
    # 멤버 시트가 없으면 에러가 날 수 있으니 예외처리
    try:
        sheet_members = doc.worksheet("Members") # 멤버 명단 시트
    except:
        # 혹시 Members 시트가 없으면 자동으로 만들어줌
        sheet_members = doc.add_worksheet(title="Members", rows=100, cols=2)
        sheet_members.append_row(["이름"]) # 헤더 추가
        
except Exception as e:
    st.error(f"구글 시트 연결 실패! 설정 파일이나 시트 이름을 확인해주세요.\n{e}")
    st.stop()

# --- 2. 데이터 처리 함수 ---

def get_member_list():
    """Members 시트에서 이름 목록을 가져옵니다."""
    # 첫 번째 열(A열)을 다 가져오고, 첫 줄(헤더 '이름')은 제외
    members = sheet_members.col_values(1)
    if len(members) > 1:
        return members[1:] # 헤더 제외하고 리턴
    return []

def add_new_member(name):
    """새로운 멤버를 Members 시트에 추가합니다."""
    # 이미 있는지 확인
    current_members = get_member_list()
    if name in current_members:
        return False, "이미 등록된 이름입니다."
    
    sheet_members.append_row([name])
    return True, f"{name}님 환영합니다! 등록 완료."

def add_log(name, point, reason, note=""):
    """기록용 시트에 로그 추가"""
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet_log.append_row([date, name, point, reason, note])

# --- 3. 웹 앱 화면 (UI) ---
st.title("♠️ 홀덤 동아리 랭킹 & 기록")

# 탭 구성: 랭킹 / 기록 / 회원관리
tab1, tab2, tab3 = st.tabs(["📊 랭킹 확인", "📝 게임 기록", "➕ 신규 회원"])

# [탭 1] 랭킹 확인
with tab1:
    st.header("실시간 랭킹")
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

    data = sheet_log.get_all_records()
    df = pd.DataFrame(data)
    
    if not df.empty:
        # 이름별 합계 계산 (동점이 있을 수 있으니 순위 처리)
        ranking = df.groupby("이름")["포인트변동"].sum().reset_index()
        ranking = ranking.sort_values(by="포인트변동", ascending=False)
        
        # 순위 매기기
        ranking["순위"] = range(1, len(ranking) + 1)
        ranking = ranking[["순위", "이름", "포인트변동"]] # 컬럼 순서 정리
        ranking.columns = ["순위", "이름", "총 포인트"]   # 컬럼명 깔끔하게
        
        # 1,2,3등 강조해서 보여주기
        st.dataframe(ranking, hide_index=True, use_container_width=True)
    else:
        st.info("아직 게임 기록이 없습니다.")

# [탭 2] 게임 기록 (관리자용)
with tab2:
    st.header("관리자 모드")
    password = st.text_input("관리자 비밀번호", type="password")
    
    if password == "1234":
        # 구글 시트에서 멤버 명단 실시간으로 불러오기
        members = get_member_list()
        
        if not members:
            st.warning("등록된 회원이 없습니다. '신규 회원' 탭에서 멤버를 추가해주세요!")
        else:
            option = st.radio("작업 선택", ["일반 게임 결과", "리바인/구매", "출석 체크"], horizontal=True)
            st.divider()
            
            if option == "일반 게임 결과":
                c1, c2, c3 = st.columns(3)
                with c1: w = st.selectbox("🥇 1등 (+7)", members, index=None, placeholder="선택")
                with c2: s = st.selectbox("🥈 2등 (+5)", members, index=None, placeholder="선택")
                with c3: t = st.selectbox("🥉 3등 (+3)", members, index=None, placeholder="선택")
                
                if st.button("결과 저장", type="primary"):
                    if w and s and t and len({w,s,t}) == 3:
                        add_log(w, 7, "1등"); add_log(s, 5, "2등"); add_log(t, 3, "3등")
                        st.success("저장되었습니다!")
                    else:
                        st.error("1,2,3등을 모두 다르게 선택해주세요.")

            elif option == "리바인/구매":
                target = st.selectbox("누가 사용했나요?", members)
                action = st.selectbox("무엇을?", ["리바인 (-5p)", "사설 대회 (-20p)"])
                if st.button("차감 하기", type="primary"):
                    p = -5 if "리바인" in action else -20
                    add_log(target, p, action)
                    st.success("처리 완료!")

            elif option == "출석 체크":
                # 멀티 셀렉트 박스
                present = st.multiselect("오늘 온 사람 모두 선택", members)
                if st.button("일괄 출석 (+1)", type="primary"):
                    for m in present:
                        add_log(m, 1, "출석")
                    st.success(f"{len(present)}명 출석 처리 완료!")

# [탭 3] 신규 회원 등록
with tab3:
    st.header("신규 회원 등록")
    st.info("새로운 멤버가 오면 여기서 등록하세요. 바로 명단에 추가됩니다.")
    
    new_name = st.text_input("새로운 멤버 이름 (닉네임)")
    
    if st.button("등록하기"):
        if new_name:
            success, msg = add_new_member(new_name)
            if success:
                st.success(msg)
                st.rerun() # 화면 새로고침해서 명단 갱신
            else:
                st.error(msg)
        else:

            st.warning("이름을 입력해주세요.")
