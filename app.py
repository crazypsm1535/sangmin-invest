import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. 페이지 설정 및 디자인 CSS ---
st.set_page_config(page_title="상민 전용 투자 내비게이션", layout="wide")

# 세련된 디자인을 위한 커스텀 스타일
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    h1 { color: #1e3a8a; font-weight: 800; }
    h2 { color: #1e3a8a; border-left: 5px solid #1e3a8a; padding-left: 10px; }
    .stTable { background-color: white; border-radius: 10px; overflow: hidden; }
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
ndx_rsi = round(float(current['NDX_RSI']), 2)
sp500_close = round(float(current['SP500_Close']), 2)
sp500_200 = round(float(current['SP500_200EMA']), 2)
vix = round(float(current['VIX_Close']), 2)
vol_surge = float(current['Volume']) > float(current['Vol_20MA']) * 1.5
is_break_3days = (prev_3days['NDX_Close'] < prev_3days['NDX_125EMA']).all() and (ndx_close < ndx_125)

# --- 3. 사이드바 수동 입력 ---
st.sidebar.title("🛠️ 지표 수동 입력")
st.sidebar.info("버튼을 눌러 확인한 최신 수치를 입력하세요.")
input_fg = st.sidebar.slider("1. 공포와 탐욕 지수", 0, 100, 50)
input_pcr = st.sidebar.number_input("2. 풋콜레이시오 (PCR)", 0.0, 3.0, 0.9, 0.01)
input_hy = st.sidebar.number_input("3. 하이일드 스프레드 (%)", 0.0, 20.0, 4.0, 0.1)

# --- 4. 메인 화면 레이아웃 ---
st.title("🧭 상민 전용 투자 내비게이션 V2.5")
st.markdown("---")

# [핵심 수치 요약 요약 레이아웃]
col1, col2, col3, col4 = st.columns(4)
col1.metric("나스닥 RSI", f"{ndx_rsi}", "과열" if ndx_rsi >= 70 else "공포" if ndx_rsi <= 30 else "정상")
col2.metric("VIX 지수", f"{vix}", "위험" if vix >= 30 else "안정", delta_color="inverse")
col3.metric("공포/탐욕", f"{input_fg}", "기회" if input_fg <= 25 else "정상")
col4.metric("HY 스프레드", f"{input_hy}%", "경고" if input_hy >= 5.0 else "안정", delta_color="inverse")

st.markdown("### 📊 2. 메인 감시 지표 (Primary Triggers)")

# 하이일드 스프레드가 추가된 데이터 테이블
trigger_data = {
    "분류": ["나스닥 RSI", "VIX 지수", "S&P 200일선", "나스닥 125일선", "공포탐욕지수", "풋콜레이시오(PCR)", "하이일드 스프레드"],
    "트리거 기준": ["30↓ / 70↑", "30↑", "지수 이탈", "3일 연속 하회", "25↓ (기회)", "1.1↑ (바닥)", "5.0%↑ (위험)"],
    "현재 수치": [
        f"{ndx_rsi}", f"{vix}", f"{sp500_close:,.2f}", f"{ndx_close:,.2f}", 
        f"{input_fg}", f"{input_pcr}", f"{input_hy}%"
    ],
    "현재 상태": [
        "🔴 트리거" if ndx_rsi <= 30 or ndx_rsi >= 70 else "🟢 안정",
        "🔴 위험" if vix >= 30 else "🟢 안정",
        "🔴 이탈" if sp500_close < sp500_200 else "🟢 유지",
        "🟡 브레이크" if is_break_3days else "🟢 정상",
        "🔴 기회" if input_fg <= 25 else "🟢 정상",
        "🔴 기회" if input_pcr >= 1.1 else "🟢 정상",
        "🔴 위험감지" if input_hy >= 5.0 else "🟢 안정"
    ]
}
st.table(pd.DataFrame(trigger_data))

# 직통 버튼
col_btn1, col_btn2, col_btn3 = st.columns(3)
with col_btn1: st.link_button("🔗 CNN 공포/탐욕", "https://edition.cnn.com/markets/fear-and-greed", use_container_width=True)
with col_btn2: st.link_button("🔗 CBOE 풋콜레이시오", "https://www.cboe.com/us/options/market_statistics/", use_container_width=True)
with col_btn3: st.link_button("🔗 연준 HY 스프레드", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", use_container_width=True)

st.markdown("---")

# [전략별 카드 레이아웃]
st.subheader("🎯 3대 전략별 대응 가이드")
c1, c2, c3 = st.columns(3)

with c1:
    st.info("#### 🛡️ Hyper-Shield")
    if ndx_rsi <= 30 or input_fg <= 25: st.error("**[액셀러] QLD 집중 매수**")
    elif is_break_3days: st.warning("**[브레이크] 매수 중단**")
    else: st.success("**[평상시] 기계적 매수**")

with c2:
    st.info("#### 🚀 Hyper-Accelerator")
    if ndx_rsi <= 30: st.error("**[액셀러] MAGS/MGK 집중**")
    elif is_break_3days: st.warning("**[브레이크] 방어자산 배분**")
    else: st.success("**[평상시] 4:4:1:1 매수**")

with c3:
    st.info("#### 🧠 스마트 DCA")
    if ndx_rsi <= 30 and input_fg <= 25: st.error("**[액셀러] 성장자산 집중**")
    elif ndx_rsi >= 70: st.warning("**[과열] 방어자산 확대**")
    else: st.success("**[평상시] 기본비중 매수**")

st.markdown("---")

# [비서의 조언]
st.subheader("📋 비서의 전문 검증 및 조언")
with st.expander("상세 분석 결과 보기", expanded=True):
    st.markdown(f"""
    1. **시장 위험도:** 현재 하이일드 스프레드는 **{input_hy}%**입니다. {'금융 시스템 리스크가 감지되니 주의하십시오.' if input_hy >= 5.0 else '시스템 리스크는 낮으며 안정적입니다.'}
    2. **추세 분석:** 나스닥 지수가 125일선 대비 **{'위' if ndx_close > ndx_125 else '아래'}**에 위치해 있으며, 거래량은 **{'폭발적(신뢰도 높음)' if vol_surge else '평이함'}** 수준입니다.
    3. **최종 권고:** """)
    if ndx_rsi <= 30 or input_fg <= 25:
        st.error("여러 지표가 '공포'를 가리키고 있습니다. **[액셀러 모드]**로 전환하여 매수량을 늘리십시오.")
    elif is_break_3days:
        st.warning("추세가 무너졌습니다. **[브레이크]** 매뉴얼에 따라 안전 자산을 확보하십시오.")
    else:
        st.success("시장 데이터가 평온합니다. 본업에 집중하시며 **기계적 적립**을 이어가십시오.")
