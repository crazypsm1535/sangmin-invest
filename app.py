import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. 페이지 설정 및 디자인 CSS ---
st.set_page_config(page_title="투자 내비게이션", layout="wide")

st.markdown("""
    <style>
    .stMetric { padding: 10px; border-radius: 10px; border: 1px solid rgba(128, 128, 128, 0.2); }
    h1 { font-weight: 800; }
    h2 { border-left: 5px solid #4A90E2; padding-left: 10px; margin-top: 30px; }
    </style>
    """, unsafe_allow_html=True)

def calculate_rsi(series, period=14):
    delta = series.diff()
    up, down = delta.copy(), delta.copy()
    up[up < 0] = 0
    down[down > 0] = 0
    _gain = up.ewm(com=(period - 1), min_periods=period).mean()
    _loss = down.abs().ewm(com=(period - 1), min_periods=period).mean()
    RS = _gain / _loss
    return 100 - (100 / (1 + RS))

@st.cache_data(ttl=3600)
def get_exact_index_data():
    ndx = yf.Ticker("^NDX").history(period="1y")
    sp500 = yf.Ticker("^GSPC").history(period="1y")
    vix = yf.Ticker("^VIX").history(period="1y")
    qqq = yf.Ticker("QQQ").history(period="1y")
    for _df in [ndx, sp500, vix, qqq]:
        if _df.index.tz is not None: _df.index = _df.index.tz_localize(None)
    df = pd.DataFrame(index=ndx.index)
    df['NDX_Close'] = ndx['Close']
    df['SP500_Close'] = sp500['Close']
    df['VIX_Close'] = vix['Close']
    df['Volume'] = qqq['Volume']
    df = df.ffill().dropna()
    df['NDX_125EMA'] = df['NDX_Close'].ewm(span=125, adjust=False).mean()
    df['NDX_50EMA'] = df['NDX_Close'].ewm(span=50, adjust=False).mean()
    df['SP500_200EMA'] = df['SP500_Close'].ewm(span=200, adjust=False).mean()
    df['NDX_RSI'] = calculate_rsi(df['NDX_Close'])
    df['Vol_20MA'] = df['Volume'].rolling(window=20).mean()
    return df.dropna().tail(10)

# --- 2. 데이터 로드 및 계산 ---
df = get_exact_index_data()
current = df.iloc[-1]
prev_3days = df.iloc[-4:-1]

ndx_close = round(float(current['NDX_Close']), 2)
ndx_125 = round(float(current['NDX_125EMA']), 2)
ndx_50 = round(float(current['NDX_50EMA']), 2)
ndx_rsi = round(float(current['NDX_RSI']), 2)
sp500_close = round(float(current['SP500_Close']), 2)
sp500_200 = round(float(current['SP500_200EMA']), 2)
vix = round(float(current['VIX_Close']), 2)
vol_surge = float(current['Volume']) > float(current['Vol_20MA']) * 1.5
is_break_3days = (prev_3days['NDX_Close'] < prev_3days['NDX_125EMA']).all() and (ndx_close < ndx_125)

# --- 3. 사이드바 수동 입력 ---
st.sidebar.title("🛠️ 지표 수동 입력")
st.sidebar.info("사이트에서 확인한 수치를 아래에 입력하십시오.")
input_fg = st.sidebar.number_input("1. 공포와 탐욕 지수 (0~100)", min_value=0, max_value=100, value=50)
input_pcr = st.sidebar.number_input("2. 풋콜레이시오 (PCR)", min_value=0.0, max_value=3.0, value=0.9, step=0.01)
input_hy = st.sidebar.number_input("3. 하이일드 스프레드 (%)", min_value=0.0, max_value=20.0, value=4.0, step=0.1)

# --- 4. 메인 화면 레이아웃 ---
st.title("🧭 투자 비서 시스템 V5.5")
st.markdown("본업에 집중하십시오. 감정에 휘둘리지 않는 데이터 무결성을 최우선으로 보고합니다.")
st.markdown("---")

rsi_status = "-과열 (경계)" if ndx_rsi >= 70 else ("-공포 (기회)" if ndx_rsi <= 30 else "정상 구간")
vix_status = "-위험 구간" if vix >= 30 else "안정 구간"
fg_status = "-기회 포착" if input_fg <= 25 else "정상 구간"
hy_status = "-위험 감지" if input_hy >= 5.0 else "안정 구간"

col1, col2, col3, col4 = st.columns(4)
col1.metric("나스닥 RSI", f"{ndx_rsi}", rsi_status)
col2.metric("VIX 지수", f"{vix}", vix_status)
col3.metric("공포와 탐욕", f"{input_fg}", fg_status)
col4.metric("HY 스프레드", f"{input_hy}%", hy_status)

st.markdown("### 📊 2. 메인 감시 지표 (Primary Triggers)")

trigger_data = {
    "지표": ["나스닥 100 지수 (RSI)", "VIX 지수", "S&P 500 (200일선)", "나스닥 100 (125일선)", "공포와 탐욕 (수동)", "풋콜레이시오 (수동)", "하이일드 스프레드 (수동)"],
    "트리거 발생 기준": ["30 이하 / 70 이상", "30 이상", "지수 이탈", "3거래일 연속 하회", "25 미만", "1.1 이상", "5.0% 이상"],
    "현재 수치 / 상태": [
        f"{ndx_rsi}", f"{vix}", f"{sp500_close:,.2f} (기준: {sp500_200:,.2f})", f"{ndx_close:,.2f} (기준: {ndx_125:,.2f})", 
        f"{input_fg}", f"{input_pcr}", f"{input_hy}%"
    ],
    "현재 판정": [
        "🔴 트리거 발동" if ndx_rsi <= 30 or ndx_rsi >= 70 else "🟢 정상",
        "🔴 위험" if vix >= 30 else "🟢 정상",
        "🔴 200일선 이탈" if sp500_close < sp500_200 else "🟢 지지 중",
        "🟡 브레이크 진입" if is_break_3days else "🟢 정상",
        "🔴 기회 포착" if input_fg <= 25 else "🟢 정상",
        "🔴 바닥 확인" if input_pcr >= 1.1 else "🟢 정상",
        "🔴 위험 감지" if input_hy >= 5.0 else "🟢 안정"
    ]
}
st.table(pd.DataFrame(trigger_data))

st.caption("※ 아래 버튼을 클릭하여 수치를 확인한 후 왼쪽 사이드바에 입력하십시오.")
col_btn1, col_btn2, col_btn3 = st.columns(3)
with col_btn1: st.link_button("🔗 CNN 공포와 탐욕 지수 확인", "https://edition.cnn.com/markets/fear-and-greed", use_container_width=True)
with col_btn2: st.link_button("🔗 CBOE 풋콜레이시오 (PCR) 확인", "https://www.cboe.com/us/options/market_statistics/", use_container_width=True)
with col_btn3: st.link_button("🔗 연준 하이일드 스프레드 확인", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", use_container_width=True)

st.markdown("---")

# [전략별 박스 레이아웃 - V5.5 통합 마스터 플랜 적용]
st.subheader("🎯 3대 투자 전략별 현재 대응 모드 (V5.5 통합)")
c1, c2, c3 = st.columns(3)

with c1:
    st.info("#### 🛡️ NH ISA\n**하이퍼-실드 V4.0**")
    if ndx_rsi <= 30: 
        st.error("**[액셀러 모드]**\n\n나스닥2x 100%")
    elif is_break_3days: 
        st.warning("**[브레이크]**\n\n국채 50% / 금 50%")
    elif ndx_rsi >= 70:
        st.warning("**[과열 방어]**\n\n나스닥2x 20% / 모멘텀 10% / 국채 35% / 금 35%")
    else: 
        st.success("**[평상시]**\n\n나스닥2x 45% / 모멘텀 25% / 국채 15% / 금 15%")

with c2:
    st.info("#### 🚀 메리츠 해외직투\n**하이퍼-액셀러레이터 V1.3**")
    if ndx_rsi <= 30: 
        st.error("**[액셀러 모드]**\n\nMAGS 50% / MGK 50%")
    elif is_break_3days: 
        st.warning("**[브레이크]**\n\nTLT 50% / GLDM 50%")
    elif ndx_rsi >= 70:
        st.warning("**[과열 방어]**\n\nMAGS 30% / MGK 30% / TLT 20% / GLDM 20%")
    else: 
        st.success("**[평상시]**\n\nMAGS 40% / MGK 40% / TLT 10% / GLDM 10%")

with c3:
    st.info("#### 🧠 삼성 연금저축\n**하이퍼-스마트 DCA**")
    if ndx_rsi <= 30: 
        st.error("**[액셀러 모드]**\n\n빅테크TOP7 62.5% / 모멘텀 37.5%")
    elif is_break_3days: 
        st.warning("**[브레이크]**\n\n모멘텀 35% / 동일가중 65%")
    elif ndx_rsi >= 70:
        st.warning("**[과열 방어]**\n\n빅테크TOP7 37.5% / 모멘텀 25% / 동일가중 37.5%")
    else: 
        st.success("**[평상시]**\n\n빅테크TOP7 55% / 모멘텀 30% / 동일가중 15%")

st.markdown("---")

# [비서의 조언 요약 박스]
st.subheader("📋 비서의 전문 검증 및 조언 레이어")
with st.expander("상세 분석 결과 보기", expanded=True):
    st.markdown(f"""
    1. **시장 위험도:** 현재 하이일드 스프레드는 **{input_hy}%**입니다. {'금융 시스템 리스크가 감지되니 주의하십시오.' if input_hy >= 5.0 else '시스템 리스크는 낮으며 안정적입니다.'}
    2. **추세 분석 (125일선):** 나스닥 지수가 125일선 대비 **{'위' if ndx_close > ndx_125 else '아래'}**에 위치해 있으며, 거래량은 **{'폭발적(신뢰도 높음)' if vol_surge else '평이함'}** 수준입니다.
    3. **단기 선발대 (50일선):** 지수가 50일선({ndx_50:,.2f}) **{'위에서 지지받고 있어 공격적 선발대 투입이 유효합니다.' if ndx_close > ndx_50 else '아래에 있어 아직 선발대 투입은 권장하지 않습니다.'}**
    4. **최종 권고:** """)
    
    if ndx_rsi <= 30:
        st.error("나스닥 RSI 30 이하로 공포가 극대화되었습니다. **[액셀러 모드]**로 전환하여 모아둔 실탄으로 핵심 주식을 집중 매수하십시오.")
    elif is_break_3days:
        st.warning("125일선 추세 붕괴(브레이크)가 확인되었습니다. 주식 매수를 중단하고 안전 자산을 100% 적립하십시오.")
    elif ndx_rsi >= 70:
        st.warning("나스닥 RSI 70 이상으로 고점 부담이 증가한 과매수 구간입니다. **[과열 방어]** 모드로 전환하여 공격 자산을 축소하고 방어 자산을 선제 확보하십시오.")
    else:
        st.success("안정적 성장 추세입니다. **[평상시]** 모드로 기본 비중대로 투자금을 기계적으로 집행하십시오.")