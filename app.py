import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="투자 내비게이션 V3.0", layout="wide")

# 가독성 및 레이아웃 CSS
st.markdown("""
    <style>
    .big-card { background:#1e293b; padding:15px; border-radius:8px; border:1px solid #334155; height:70px; display:flex; flex-direction:column; justify-content:center; }
    th { background-color: #1e293b !important; color: white !important; }
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
def get_market_data():
    try:
        ndx = yf.Ticker("^NDX").history(period="1y")
        sp500 = yf.Ticker("^GSPC").history(period="1y")
        vix = yf.Ticker("^VIX").history(period="1y")
        qqq = yf.Ticker("QQQ").history(period="1y")
        
        df = pd.DataFrame(index=ndx.index)
        df['NDX_Close'] = ndx['Close']
        df['SP500_Close'] = sp500['Close']
        df['VIX_Close'] = vix['Close']
        df['Volume'] = qqq['Volume']
        df = df.ffill().dropna()
        df['NDX_125EMA'] = df['NDX_Close'].ewm(span=125, adjust=False).mean()
        df['NDX_RSI'] = calculate_rsi(df['NDX_Close'])
        return df
    except:
        return pd.DataFrame()

df = get_market_data()

# 데이터 로드 에러 방어 구문
if df.empty:
    st.error("데이터 로드 중입니다. 잠시 후 새로고침 하십시오.")
    current = None
else:
    current = df.iloc[-1]

# 사이드바 입력
st.sidebar.title("🛠️ 지표 수동 입력")
input_fg = st.sidebar.number_input("공포와 탐욕 지수", 0, 100, 50)
input_pcr = st.sidebar.number_input("풋콜레이시오 (PCR)", 0.0, 3.0, 0.9, 0.01)
input_hy = st.sidebar.number_input("하이일드 스프레드 (%)", 0.0, 20.0, 4.0, 0.1)

# 메인 화면
st.title("🧭 통합 투자 내비게이션 V3.0")

if current is not None:
    ndx_rsi, vix = round(current['NDX_RSI'], 2), round(current['VIX_Close'], 2)
    
    # 4대 카드
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f'<div class="big-card">나스닥 RSI<br><b>{ndx_rsi}</b></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="big-card">VIX 지수<br><b>{vix}</b></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="big-card">공포 탐욕<br><b>{input_fg}</b></div>', unsafe_allow_html=True)
    col4.markdown(f'<div class="big-card">HY / PCR<br><b>{input_hy}% / {input_pcr}</b></div>', unsafe_allow_html=True)

    st.markdown("## 📊 1. 메인 감시 지표")
    trigger_data = pd.DataFrame({
        "지표": ["나스닥 RSI", "VIX 지수", "공포/탐욕", "풋콜", "HY스프레드"],
        "기준": ["30이하/70이상", "30이상", "25미만", "1.1이상", "5.0%이상"],
        "현재": [ndx_rsi, vix, input_fg, input_pcr, input_hy],
        "상태": ["정상", "정상", "정상", "정상", "안정"]
    })
    st.table(trigger_data)

# 수동 지표 확인
st.markdown("## 🔍 2. 심리 및 매크로 수동 지표 확인")
c1, c2, c3 = st.columns(3)
c1.link_button("CNN 공포탐욕 확인", "https://edition.cnn.com/markets/fear-and-greed")
c2.link_button("풋콜레이시오 (PCC) 확인", "https://kr.investing.com/indices/cboe-total-put-call-ratio")
c3.link_button("하이일드 스프레드 확인", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2")