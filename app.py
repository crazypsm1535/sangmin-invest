import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="투자 내비게이션 V3.0 (Dynamic)", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; }
    h1 { font-size: 24px !important; font-weight: 800; margin-bottom: 5px !important; }
    h2 { border-left: 5px solid #3b82f6; padding-left: 10px; margin-top: 15px !important; font-size: 18px !important; }
    
    /* 🛠️ [중요] 표 높이를 1줄로 강제 고정하고 흰색 칸 버그 해결 */
    .compact-table { width: 100%; border-collapse: collapse; background-color: #0f172a; }
    .compact-table th { background-color: #1e293b !important; color: #ffffff !important; padding: 6px !important; white-space: nowrap !important; }
    .compact-table td { padding: 4px 8px !important; white-space: nowrap !important; border-bottom: 1px solid #334155; }
    </style>
    """, unsafe_allow_html=True)

# (데이터 계산 로직 동일)
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
    df = pd.DataFrame(index=ndx.index)
    df['NDX_Close'], df['SP500_Close'], df['VIX_Close'] = ndx['Close'], sp500['Close'], vix['Close']
    df['Volume'] = qqq['Volume']
    df = df.ffill().dropna()
    df['NDX_125EMA'] = df['NDX_Close'].ewm(span=125, adjust=False).mean()
    df['NDX_RSI'] = calculate_rsi(df['NDX_Close'])
    return df.dropna().tail(10)

df = get_market_data()
current = df.iloc[-1]
ndx_close, ndx_125, ndx_rsi, vix = round(current['NDX_Close'], 2), round(current['NDX_125EMA'], 2), round(current['NDX_RSI'], 2), round(current['VIX_Close'], 2)

# --- 2. 메인 화면 출력 ---
st.title("🧭 통합 투자 내비게이션 V3.0")

# 카드 바인딩 및 출력
col1, col2, col3, col4 = st.columns(4)
card_style = "background:#1e293b; padding:10px; border-radius:6px; height:60px;"
col1.markdown(f'<div style="{card_style}">나스닥 RSI<br><b>{ndx_rsi}</b></div>', unsafe_allow_html=True)
col2.markdown(f'<div style="{card_style}">VIX 지수<br><b>{vix}</b></div>', unsafe_allow_html=True)
col3.markdown(f'<div style="{card_style}">공포 탐욕<br><b>50</b></div>', unsafe_allow_html=True)
col4.markdown(f'<div style="{card_style}">HY / PCR<br><b>4.0% / 0.9</b></div>', unsafe_allow_html=True)

st.markdown("## 📊 1. 메인 감시 지표")

# 🛠️ [정상 복구] 표 데이터 바인딩 로직
trigger_table = f"""
<table class="compact-table">
    <thead>
        <tr><th>지표</th><th>트리거 발생 기준</th><th>현재 수치</th><th>현재 판정</th></tr>
    </thead>
    <tbody>
        <tr><td>나스닥 RSI</td><td>[기회] 30이하 / [경계] 70이상</td><td>{ndx_rsi}</td><td>{'🔴 트리거' if ndx_rsi<=30 or ndx_rsi>=70 else '🟢 정상'}</td></tr>
        <tr><td>VIX 지수</td><td>30 이상</td><td>{vix}</td><td>{'🔴 위험' if vix>=30 else '🟢 정상'}</td></tr>
        <tr><td>나스닥 125일선</td><td>3거래일 연속 하회</td><td>{ndx_close}</td><td>🟡 브레이크</td></tr>
    </tbody>
</table>
"""
st.markdown(trigger_table, unsafe_allow_html=True)

# 수동 지표 확인 링크
st.markdown("## 🔍 2. 심리 및 매크로 수동 지표 확인")
col_l1, col_l2, col_l3 = st.columns(3)
col_l1.link_button("CNN 공포탐욕", "https://edition.cnn.com/markets/fear-and-greed", use_container_width=True)
col_l2.link_button("풋콜레이시오 (PCC)", "https://ycharts.com/indicators/total_putcall_ratio", use_container_width=True)
col_l3.link_button("하이일드 스프레드", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", use_container_width=True)