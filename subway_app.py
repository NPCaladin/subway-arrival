import streamlit as st
import requests
from urllib.parse import quote
import time
import re

# API 키 설정 함수
def get_api_key():
    """API 키를 가져오는 함수 (Streamlit Cloud Secrets 또는 하드코딩된 값)"""
    try:
        # Streamlit Cloud Secrets에서 가져오기
        if hasattr(st, 'secrets') and 'API_KEY' in st.secrets:
            return st.secrets['API_KEY']
    except:
        pass
    # 로컬 개발용 (배포 시 Secrets 사용 권장)
    return "654d446e737a6f7239355155714278"

def get_subway_line_name(subway_id):
    """지하철 호선 ID를 호선 이름으로 변환"""
    subway_line_map = {
        '1001': '1호선',
        '1002': '2호선',
        '1003': '3호선',
        '1004': '4호선',
        '1005': '5호선',
        '1006': '6호선',
        '1007': '7호선',
        '1008': '8호선',
        '1009': '9호선',
        '1061': '중앙선',
        '1063': '경의중앙선',
        '1065': '공항철도',
        '1067': '경춘선',
        '1071': '수인분당선',
        '1075': '분당선',
        '1077': '분당선',
        '1081': '신림선',
        '1092': '신분당선',
        '1093': '용인경전철',
        '1094': '의정부경전철',
        '1095': '우이신설선',
        '1096': '서해선',
        '1097': '김포골드라인',
        '1099': '수인선',
    }
    subway_id_str = str(subway_id) if subway_id else ''
    return subway_line_map.get(subway_id_str, f'{subway_id_str}호선' if subway_id_str else '알 수 없음')

# 페이지 설정
st.set_page_config(
    page_title="지하철 실시간 도착 정보",
    page_icon="🚇",
    layout="wide"
)

# 세션 상태 초기화
if 'current_station' not in st.session_state:
    st.session_state.current_station = '지축'
if 'refresh_key' not in st.session_state:
    st.session_state.refresh_key = 0

def fetch_subway_data(station_name):
    """지하철 실시간 도착 정보를 가져오는 함수"""
    API_KEY = get_api_key()
    if not API_KEY:
        st.error("⚠️ API_KEY를 설정해주세요.")
        return None
    
    # URL 인코딩 (UTF-8)
    encoded_station = quote(station_name, safe='')
    url = f"http://swopenAPI.seoul.go.kr/api/subway/{API_KEY}/json/realtimeStationArrival/0/10/{encoded_station}"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # API 에러 응답 확인
        if 'errorMessage' in data:
            error_info = data['errorMessage']
            code = error_info.get('code', '')
            if code != 'INFO-000':
                error_msg = error_info.get('message', '알 수 없는 오류')
                st.error(f"⚠️ API 오류: {error_msg}")
                return None
        
        # API 응답 확인 - 실제 키는 'realtimeArrivalList'
        if 'realtimeArrivalList' in data:
            arrival_list = data['realtimeArrivalList']
            # 리스트가 비어있거나 None인 경우 확인
            if arrival_list and len(arrival_list) > 0:
                return arrival_list
            else:
                return []
        elif 'realtimeStationArrival' in data:
            # 이전 버전 호환성
            arrival_list = data['realtimeStationArrival']
            if arrival_list and len(arrival_list) > 0:
                return arrival_list
            else:
                return []
        elif isinstance(data, list):
            # 응답이 직접 리스트인 경우
            return data if len(data) > 0 else []
        else:
            # 디버깅: 응답 구조 확인
            st.warning(f"⚠️ 예상치 못한 API 응답 형식입니다. 응답 키: {list(data.keys()) if isinstance(data, dict) else '리스트'}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ API 호출 중 오류가 발생했습니다: {str(e)}")
        return None
    except Exception as e:
        st.error(f"⚠️ 오류가 발생했습니다: {str(e)}")
        return None

def is_valid_station_text(text):
    """지하철 관련 유효한 텍스트인지 확인"""
    if not text or len(text) == 0:
        return False
    
    # 이상한 단어 필터링
    invalid_words = ['접수', '글로벌', '수입', '전환', '글로벌 수입']
    if any(word in text for word in invalid_words):
        return False
    
    # 유효한 키워드 확인
    valid_keywords = ['분', '초', '후', '도착', '진입', '전역', '역', '번째']
    if any(keyword in text for keyword in valid_keywords):
        return True
    
    # 역 이름 패턴 확인 (한글 2-4자)
    if re.match(r'^[가-힣]{2,4}$', text.strip()):
        return True
    
    return False

def parse_train_info(train_data):
    """열차 정보를 파싱하는 함수"""
    # barvlDt: 도착까지 남은 시간(초)
    barvl_dt = train_data.get('barvlDt', '0')
    try:
        barvl_seconds = int(barvl_dt) if barvl_dt else 0
    except (ValueError, TypeError):
        barvl_seconds = 0
    
    # 시간 정보 계산
    if barvl_seconds > 0:
        minutes = barvl_seconds // 60
        seconds = barvl_seconds % 60
        if minutes > 0 and seconds > 0:
            time_str = f"{minutes}분 {seconds}초 후"
        elif minutes > 0:
            time_str = f"{minutes}분 후"
        elif seconds > 0:
            time_str = f"{seconds}초 후"
        else:
            time_str = "곧 도착"
    else:
        time_str = "도착"
    
    # arvlMsg2와 arvlMsg3 가져오기
    arvl_msg2 = train_data.get('arvlMsg2', '').strip()
    arvl_msg3 = train_data.get('arvlMsg3', '').strip()
    arvl_cd = train_data.get('arvlCd', '')
    
    # "접수", "글로벌 수입", "전환" 등 이상한 값이 포함되어 있으면 무시
    invalid_words = ['접수', '글로벌', '수입', '전환']
    if any(word in arvl_msg2 for word in invalid_words):
        arvl_msg2 = ''
    if any(word in arvl_msg3 for word in invalid_words):
        arvl_msg3 = ''
    
    # arvlMsg2 유효성 검사
    is_valid_msg2 = is_valid_station_text(arvl_msg2) if arvl_msg2 else False
    
    # 상태 및 시간 정보 결정
    if is_valid_msg2 and ('분' in arvl_msg2 or '초' in arvl_msg2 or '후' in arvl_msg2):
        # arvlMsg2에 시간 정보가 포함되어 있음
        status = arvl_msg2
        time_display = arvl_msg2
    elif is_valid_msg2 and ('도착' in arvl_msg2 or '진입' in arvl_msg2):
        # 도착 또는 진입 메시지
        status = arvl_msg2
        time_display = time_str if barvl_seconds > 0 else "도착"
    elif is_valid_msg2 and '전역' in arvl_msg2:
        # 전역 정보 (예: "[2]번째 전역")
        status = arvl_msg2
        time_display = time_str if barvl_seconds > 0 else "도착"
    else:
        # arvlMsg2가 유효하지 않으면 barvlDt로 계산한 시간 사용
        if barvl_seconds > 0:
            status = time_str
            time_display = time_str
        else:
            # arvlCd 코드로 상태 판단
            if arvl_cd == '0':
                status = "도착"
                time_display = "도착"
            elif arvl_cd == '1':
                status = "진입중"
                time_display = "진입중"
            else:
                status = "도착"
                time_display = "도착"
    
    # 현재 위치 정보
    current_location = ''
    if is_valid_station_text(arvl_msg3):
        current_location = arvl_msg3
    elif is_valid_msg2 and not ('분' in arvl_msg2 or '초' in arvl_msg2):
        # arvlMsg2에서 역 이름 추출 시도
        match = re.search(r'\(([가-힣]+)\)', arvl_msg2)
        if match:
            current_location = match.group(1)
        elif len(arvl_msg2) <= 4 and is_valid_station_text(arvl_msg2):
            current_location = arvl_msg2
    
    # 최종 필터링: status와 time_display에서도 "접수" 등 이상한 단어 제거
    if '접수' in status or '글로벌' in status or '수입' in status or '전환' in status:
        if barvl_seconds > 0:
            status = time_str
        else:
            status = "도착"
    
    if '접수' in time_display or '글로벌' in time_display or '수입' in time_display or '전환' in time_display:
        if barvl_seconds > 0:
            time_display = time_str
        else:
            time_display = "도착"
    
    if '접수' in current_location or '글로벌' in current_location or '수입' in current_location or '전환' in current_location:
        current_location = ''
    
    # 막차 여부 확인 (lstcarAt: 0=일반, 1=막차)
    lstcar_at = train_data.get('lstcarAt', '0')
    is_last_train = (lstcar_at == '1' or lstcar_at == 1)
    
    # 호선 정보
    subway_id = train_data.get('subwayId', '')
    subway_line_name = get_subway_line_name(subway_id)
    
    info = {
        'direction': train_data.get('bstatnNm', '알 수 없음'),  # 도착지 방면
        'status': status,  # 상태 (진입중, 도착 등)
        'time': time_display,  # 남은 시간
        'current': current_location if current_location else '알 수 없음',  # 현재 위치
        'subway_line': subway_id,  # 호선 ID
        'subway_line_name': subway_line_name,  # 호선 이름
        'updn_line': train_data.get('updnLine', ''),  # 상행/하행
        'is_last_train': is_last_train  # 막차 여부
    }
    return info

def display_train_card(train_info, index):
    """열차 정보를 카드 형태로 표시하는 함수"""
    # 막차인 경우 배지 추가
    last_train_badge = ""
    border_color = "#e0e0e0"
    bg_color = "#f8f9fa"
    
    if train_info.get('is_last_train', False):
        last_train_badge = '<span style="background-color: #ff6b6b; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-left: 8px;">막차</span>'
        border_color = "#ff6b6b"
        bg_color = "#fff5f5"
    
    with st.container():
        st.markdown(
            f"""
            <div style="
                border: 2px solid {border_color};
                border-radius: 10px;
                padding: 15px;
                margin: 10px 0;
                background-color: {bg_color};
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                    <h4 style="margin: 0; color: #1976d2;">
                        🚇 {train_info['direction']} 방면{last_train_badge}
                    </h4>
                    <span style="background-color: #1976d2; color: white; padding: 4px 10px; border-radius: 12px; font-size: 13px; font-weight: bold;">
                        {train_info.get('subway_line_name', '알 수 없음')}
                    </span>
                </div>
                <p style="margin: 5px 0; font-size: 18px; font-weight: bold; color: #d32f2f;">
                    {train_info['status']}
                </p>
                <p style="margin: 5px 0; color: #666;">
                    ⏱️ {train_info['time']}
                </p>
                <p style="margin: 5px 0; color: #666;">
                    📍 {train_info['current']}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

# 메인 UI
st.title("🚇 지하철 실시간 도착 정보")

# API 키 확인 및 안내
api_key = get_api_key()
if not api_key:
    st.sidebar.warning("⚠️ API 키를 설정해주세요.")
    st.sidebar.info("💡 Streamlit Cloud Secrets에 API_KEY를 설정하거나, 코드의 get_api_key() 함수를 수정하세요.")

# 검색 및 새로고침 UI
col1, col2 = st.columns([4, 1])

with col1:
    station_input = st.text_input(
        "역 이름을 입력하세요",
        value=st.session_state.current_station,
        key=f"station_input_{st.session_state.refresh_key}",
        placeholder="예: 지축, 강남, 홍대입구"
    )

with col2:
    st.write("")  # 공간 맞추기
    st.write("")  # 공간 맞추기
    if st.button("🔄 새로고침", use_container_width=True):
        st.session_state.refresh_key += 1
        st.rerun()

# 역 이름이 입력되었을 때
if station_input:
    st.session_state.current_station = station_input
    
    # 로딩 표시
    with st.spinner(f"'{station_input}' 역 정보를 불러오는 중..."):
        data = fetch_subway_data(station_input)
    
    if data is None:
        st.error("⚠️ 해당 역을 찾을 수 없습니다. 역 이름을 확인해주세요.")
    elif isinstance(data, list) and len(data) == 0:
        st.warning("⚠️ 현재 도착 예정인 열차가 없습니다.")
    else:
        # 상행선과 하행선 분리
        upbound_trains = []
        downbound_trains = []
        
        for train in data:
            train_info = parse_train_info(train)
            updn = train_info['updn_line']
            
            if '상행' in updn or '내선' in updn or '상' in updn:
                upbound_trains.append(train_info)
            elif '하행' in updn or '외선' in updn or '하' in updn:
                downbound_trains.append(train_info)
            else:
                # 방향이 명확하지 않은 경우 하행선으로 분류
                downbound_trains.append(train_info)
        
        # 탭으로 상행선/하행선 구분
        tab1, tab2 = st.tabs([
            f"🔺 하행선 ({len(downbound_trains)}개)",
            f"🔻 상행선 ({len(upbound_trains)}개)"
        ])
        
        with tab1:
            if downbound_trains:
                st.subheader(f"'{station_input}' 역 하행선 도착 정보")
                for idx, train in enumerate(downbound_trains, 1):
                    display_train_card(train, idx)
            else:
                st.info("하행선 도착 예정 열차가 없습니다.")
        
        with tab2:
            if upbound_trains:
                st.subheader(f"'{station_input}' 역 상행선 도착 정보")
                for idx, train in enumerate(upbound_trains, 1):
                    display_train_card(train, idx)
            else:
                st.info("상행선 도착 예정 열차가 없습니다.")
        
        # 자동 새로고침 옵션 (선택사항)
        st.markdown("---")
        auto_refresh = st.checkbox("🔄 30초마다 자동 새로고침", value=False)
        if auto_refresh:
            time.sleep(30)
            st.rerun()
else:
    st.info("👆 위에 역 이름을 입력해주세요.")

# 하단 정보
st.markdown("---")
st.caption("💡 데이터 제공: 서울시 열린데이터 광장")

