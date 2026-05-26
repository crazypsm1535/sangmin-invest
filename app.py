import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="투자 내비게이션 V3.0 (Dynamic)", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem !important; }
    h1 { font-size: 26px !important; font-weight: 800; margin-bottom: 10px !important; }
    h2 { border-left: 5px solid #3b82f6; padding-left: 10px; margin-top: 25px !important; }
    
    /* 카드 사이즈 대폭 확대 (65px) 및 내부 정렬 */
    .big-card { 
        background-color:#1e293b; border:1px solid rgba(255,255,255,0.1); 
        border-radius:8px; padding:15px; display:flex; 
        flex-direction: column; justify-content:center; height:70px;
    }
    
    /* 표 한 줄 강제 고정 및 깔끔한 출력 */
    div[data-testid="stTable"] table { width: 100% !important; }
    th { background-color: #334155 !important; color: white !important; white-space: nowrap !important; }
    td { white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; }
    </style>
    """, unsafe_allow_html=True)

# (데이터 처리 로직 동일하므로 생략 - 이전 버전과 동일)
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
def get_market_data():
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

# (사이드바 및 데이터 계산 로직 포함...)
# [이 부분은 이전 코드와 동일하게 유지하세요]
df = get_market_data()
current = df.iloc[-1]
# ... (생략) ...
# [데이터 계산 로직]
ndx_rsi = round(current['NDX_RSI'], 2)
vix = round(current['VIX_Close'], 2)
input_fg = 50
input_pcr = 0.9
input_hy = 4.0

# --- 화면 출력부 ---
st.title("🧭 통합 투자 내비게이션 V3.0 (Premium Dynamic)")

# 🛠️ [확대된 카드]
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="big-card"><span style="color:#94a3b8; font-size:12px;">나스닥 RSI</span><span style="font-size:18px; font-weight:bold; color:#f87171;">{ndx_rsi}</span></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="big-card"><span style="color:#94a3b8; font-size:12px;">VIX 지수</span><span style="font-size:18px; font-weight:bold; color:#4ade80;">{vix}</span></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="big-card"><span style="color:#94a3b8; font-size:12px;">공포 탐욕</span><span style="font-size:18px; font-weight:bold; color:#e2e8f0;">{input_fg}</span></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="big-card"><span style="color:#94a3b8; font-size:12px;">HY / PCR</span><span style="font-size:18px; font-weight:bold; color:#38bdf8;">{input_hy}% / {input_pcr}</span></div>', unsafe_allow_html=True)

st.markdown("## 📊 1. 메인 감시 지표 (Primary Triggers)")
# (표 로직 동일...)
trigger_data = {
    "지표": ["나스닥 RSI", "VIX 지수", "S&P 200일선", "나스닥 125일선", "공포/탐욕", "풋콜", "HY스프레드"],
    "상태": ["정상", "정상", "지지 중", "정상", "정상", "정상", "안정"]
}
st.table(pd.DataFrame(trigger_data))