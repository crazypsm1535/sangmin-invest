import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="투자 내비게이션 V6.0 (Dynamic)", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2.5rem !important; padding-bottom: 1rem !important; }
    h1 { margin-top: 0px !important; margin-bottom: 5px !important; font-size: 26px !important; font-weight: 800; }
    h2 { border-left: 5px solid #3b82f6; padding-left: 10px; margin-top: 20px !important; margin-bottom: 5px !important; font-size: 18px !important; }
    th { background-color: #1e293b !important; color: #ffffff !important; font-weight: bold !important; padding: 8px 12px !important; font-size: 13px !important; white-space: nowrap !important; }
    td { text-align: left !important; vertical-align: middle !important; padding: 8px 12px !important; font-size: 13px !important; white-space: nowrap !important; }
    div[data-testid="stTable"] table { width: 100% !important; margin-top: 0px !important; margin-bottom: 0px !important; }
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

# 데이터 무한 대기(블랙스크린) 방지를 위한 예외 처리 탑재
@st.cache_data(ttl=3600)
def get_market_data():
    try:
        # download 방식으로 변경하여 안정성 확보 (빈 데이터 반환 방지)
        ndx = yf.download("^NDX", period="1y", progress=False)
        sp500 = yf.download("^GSPC", period="1y", progress=False)
        vix = yf.download("^VIX", period="1y", progress=False)
        qqq = yf.download("QQQ", period="1y", progress=False)
        
        if ndx.empty or sp500.empty or vix.empty or qqq.empty:
            return None

        df = pd.DataFrame(index=ndx.index)
        
        # yfinance 최신 버전 MultiIndex 처리
        df['NDX_Close'] = ndx['Close'].iloc[:, 0] if isinstance(ndx.columns, pd.MultiIndex) else ndx['Close']
        df['SP500_Close'] = sp500['Close'].iloc[:, 0] if isinstance(sp500.columns, pd.MultiIndex) else sp500['Close']
        df['VIX_Close'] = vix['Close'].iloc[:, 0] if isinstance(vix.columns, pd.MultiIndex) else vix['Close']
        df['Volume'] = qqq['Volume'].iloc[:, 0] if isinstance(qqq.columns, pd.MultiIndex) else qqq['Volume']
        
        df = df.ffill().dropna()
        df['NDX_125EMA'] = df['NDX_Close'].ewm(span=125, adjust=False).mean()
        df['NDX_50EMA'] = df['NDX_Close'].ewm(span=50, adjust=False).mean()
        df['SP500_200EMA'] = df['SP500_Close'].ewm(span=200, adjust=False).mean()
        df['NDX_RSI'] = calculate_rsi(df['NDX_Close'])
        df['Vol_20MA'] = df['Volume'].rolling(window=20).mean()
        return df.dropna().tail(10)
    except Exception as e:
        return None

# --- 2. 데이터 처리 및 메인 화면 ---
st.title("🧭 통합 투자 내비게이션 V6.0 (Premium Dynamic)")

df = get_market_data()
fetch_error = False

# 통신 에러 시 안전하게 기본값 세팅
if df is None or df.empty:
    fetch_error = True
    st.error("🚨 실시간 시장 데이터(Yahoo Finance) 통신에 실패했습니다. 방화벽이 차단되었을 수 있습니다. 자동으로 '테스트 모드'로 전환됩니다.")
    real_ndx_close, real_ndx_125, real_ndx_50 = 20000.0, 19000.0, 19500.0
    real_ndx_rsi, real_vix = 50.0, 20.0
    real_sp500_close, real_sp500_200 = 5000.0, 4800.0
    vol_surge = False
    real_is_break_3days = False
else:
    current = df.iloc[-1]
    prev_3days = df.iloc[-4:-1]
    real_ndx_close = round(float(current['NDX_Close']), 2)
    real_ndx_125 = round(float(current['NDX_125EMA']), 2)
    real_ndx_50 = round(float(current['NDX_50EMA']), 2)
    real_ndx_rsi = round(float(current['NDX_RSI']), 2)
    real_vix = round(float(current['VIX_Close']), 2)
    real_sp500_close = round(float(current['SP500_Close']), 2)
    real_sp500_200 = round(float(current['SP500_200EMA']), 2)
    vol_surge = bool(current['Volume'] > current['Vol_20MA'] * 1.5)
    real_is_break_3days = bool((prev_3days['NDX_Close'] < prev_3days['NDX_125EMA']).all() and (real_ndx_close < real_ndx_125))

# --- 3. 사이드바 ---
st.sidebar.title("🧪 모드 설정 및 입력")
sim_mode = st.sidebar.checkbox("🚨 인위적 테스트 모드 활성화", value=fetch_error)

if sim_mode:
    st.sidebar.subheader("🕹️ 테스트용 데이터 조작")
    ndx_rsi = st.sidebar.slider("나스닥 RSI 설정", 0.0, 100.0, 25.0, 0.1)
    vix = st.sidebar.slider("VIX 지수 설정", 0.0, 60.0, 35.0, 0.1)
    is_break_3days = st.sidebar.checkbox("나스닥 125일선 3일 연속 하회 상황 가정", value=False)
    
    ndx_close = 18000.0 if is_break_3days else 20000.0
    ndx_125, ndx_50 = 19000.0, 19500.0
    sp500_close, sp500_200 = 5000.0, 4800.0
else:
    ndx_rsi, vix, is_break_3days = real_ndx_rsi, real_vix, real_is_break_3days
    ndx_close, ndx_125, ndx_50 = real_ndx_close, real_ndx_125, real_ndx_50
    sp500_close, sp500_200 = real_sp500_close, real_sp500_200

input_fg = st.sidebar.number_input("1. 공포와 탐욕 지수 (0~100)", 0, 100, 15 if sim_mode else 50)
input_pcr = st.sidebar.number_input("2. 풋콜레이시오 (PCR)", 0.0, 3.0, 1.20 if sim_mode else 0.9, 0.01)
input_hy = st.sidebar.number_input("3. 하이일드 스프레드 (%)", 0.0, 20.0, 4.0, 0.1)
input_hy_peakout = st.sidebar.checkbox("하이일드 스프레드 하락 전환(Peak-out) 확인됨", value=True)

condition_rsi = ndx_rsi <= 30
condition_pcr = input_pcr >= 1.1
condition_fg = input_fg <= 25
condition_vix = vix >= 30
condition_hy = input_hy_peakout
accelerator_triggered = condition_rsi and condition_pcr and condition_fg and condition_vix and condition_hy

st.sidebar.markdown("---")
st.sidebar.title("🧮 자산 배분 계산기")
with st.sidebar.expander("계산기 열기 (클릭)", expanded=False):
    tab1, tab2 = st.tabs(["금액 ➔ 비중", "비중 ➔ 금액"])
    with tab1:
        cv1 = st.number_input("항목 1 금액", value=0, step=10000, key="c1_1")
        cv2 = st.number_input("항목 2 금액", value=0, step=10000, key="c1_2")
        cv3 = st.number_input("항목 3 금액", value=0, step=10000, key="c1_3")
        cv4 = st.number_input("항목 4 금액", value=0, step=10000, key="c1_4")
        tot_val = cv1 + cv2 + cv3 + cv4
        if tot_val > 0:
            st.info(f"**총 자산: {tot_val:,.0f}**\n\n- **항목 1:** {(cv1/tot_val)*100:.1f}%\n- **항목 2:** {(cv2/tot_val)*100:.1f}%\n- **항목 3:** {(cv3/tot_val)*100:.1f}%\n- **항목 4:** {(cv4/tot_val)*100:.1f}%")
    with tab2:
        t_asset = st.number_input("총 투자 금액", value=1000000, step=10000, key="c2_tot")
        cp1 = st.number_input("항목 1 비중 (%)", value=40.0, step=1.0, key="c2_1")
        cp2 = st.number_input("항목 2 비중 (%)", value=30.0, step=1.0, key="c2_2")
        cp3 = st.number_input("항목 3 비중 (%)", value=20.0, step=1.0, key="c2_3")
        cp4 = st.number_input("항목 4 비중 (%)", value=10.0, step=1.0, key="c2_4")
        tot_pct = cp1 + cp2 + cp3 + cp4
        if abs(tot_pct - 100.0) > 0.01:
            st.error(f"⚠️ 비중 합계 오류! (현재: {tot_pct}%)")
        else:
            st.success(f"**배분 목표 (총 {t_asset:,.0f})**\n\n- **항목 1:** {t_asset*(cp1/100):,.0f}\n- **항목 2:** {t_asset*(cp2/100):,.0f}\n- **항목 3:** {t_asset*(cp3/100):,.0f}\n- **항목 4:** {t_asset*(cp4/100):,.0f}")

# --- 4. 메인 뷰 ---
if sim_mode and not fetch_error:
    st.error("⚠️ 현재 [인위적 테스트 모드]가 활성화 중입니다. 실제 시장 데이터가 아닙니다.")
elif not fetch_error:
    st.markdown("<p style='font-size:13px; margin-top:-8px; color:#94a3b8;'>본업에 집중하십시오. 국내 절세 계좌의 보유분 전량 스위칭 로직이 동기화된 코드입니다.</p>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
card_css = "background-color:#1e293b; border:1px solid rgba(255,255,255,0.1); border-radius:6px; padding:8px 12px; display:flex; justify-content:space-between; align-items:center; height:38px;"

with col1: st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#cbd5e1;">나스닥 RSI</span><span style="font-size:14px; font-weight:bold; color:#f87171;">{ndx_rsi:.2f}</span></div>', unsafe_allow_html=True)
with col2: st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#cbd5e1;">VIX 지수</span><span style="font-size:14px; font-weight:bold; color:#4ade80;">{vix:.2f}</span></div>', unsafe_allow_html=True)
with col3: st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#cbd5e1;">공포와 탐욕</span><span style="font-size:14px; font-weight:bold; color:#e2e8f0;">{input_fg}</span></div>', unsafe_allow_html=True)
with col4: st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#cbd5e1;">HY / PCR</span><span style="font-size:14px; font-weight:bold; color:#38bdf8;">{input_hy}% / {input_pcr:.2f}</span></div>', unsafe_allow_html=True)

st.markdown("## 📊 1. 메인 감시 지표 (Primary Triggers)")
trigger_data = {
    "지표": ["나스닥 100 지수 (RSI)", "VIX 지수", "S&P 500 (200일선)", "나스닥 100 (125일선)", "공포와 탐욕", "풋콜레이시오", "하이일드 스프레드"],
    "트리거 발생 기준": ["🔵 30 이하 / 🔴 70 이상 ➔ 심리 과열 감시", "🚨 30 이상 ➔ 패닉 투매 감지", "❌ 지수 이탈 ➔ 장기 추세 붕괴", "⚠️ 3거래일 하회 ➔ 중장기 브레이크", "💀 25 미만 ➔ 극단적 공포", "📊 1.1 이상 ➔ 바닥 신호 응축", "⚡ 5.0% 이상 ➔ 금융위기 방어"],
    "현재 수치": [f"{ndx_rsi:.2f}", f"{vix:.2f}", f"{sp500_close:,.2f} ({sp500_200:,.2f})", f"{ndx_close:,.2f} ({ndx_125:,.2f})", f"{input_fg}", f"{input_pcr}", f"{input_hy}%"],
    "현재 판정": ["🔴 발동" if ndx_rsi <= 30 or ndx_rsi >= 70 else "🟢 정상", "🔴 위험" if vix >= 30 else "🟢 정상", "🔴 이탈" if sp500_close < sp500_200 else "🟢 지지", "🟡 브레이크" if is_break_3days else "🟢 정상", "🔴 기회" if input_fg <= 25 else "🟢 정상", "🔴 바닥" if input_pcr >= 1.1 else "🟢 정상", "🔴 위험" if input_hy >= 5.0 else "🟢 안정"]
}
st.table(pd.DataFrame(trigger_data))

st.markdown("---")
st.markdown("### 🎯 3대 투자 전략별 현재 대응 모드 (V6.0 동적 반영)")
c1, c2, c3 = st.columns(3)

with c1:
    st.info("#### 🛡️ NH ISA\n**하이퍼-실드 V4.5**")
    if accelerator_triggered: st.error("**[액셀러 모드]**\n👉 **[전량 스위칭]**\n나스닥100레버리지(418660) 100%")
    elif is_break_3days: st.warning("**[브레이크 작동]**\n👉 **[전량 대피]**\nACE 금현물 70% / KODEX 머니마켓 30%")
    elif ndx_rsi >= 70: st.warning("**[과열 방어]**\n👉 **[리밸런싱]**\n레버리지 20% / 모멘텀 10% / 금현물 49% / 머니마켓 21%")
    else: st.success("**[평상시 모드]**\n👉 **[리밸런싱]**\n레버리지 45% / 모멘텀 25% / 금현물 21% / 머니마켓 9%")

with c2:
    st.info("#### 🚀 메리츠 해외직투\n**액셀러레이터 V2.6**")
    if accelerator_triggered: st.error("**[액셀러 모드]**\n👉 **[NO-SELL]**\n신규: MAGS 55% / QLD 45%")
    elif is_break_3days: st.warning("**[브레이크 작동]**\n👉 **[NO-SELL]**\n신규: SCHD 50% / GLDM 50%")
    elif ndx_rsi >= 70: st.warning("**[과열 방어]**\n👉 **[NO-SELL]**\n신규: MAGS 30% / QLD 15% / SCHD 30% / GLDM 25%")
    else: st.success("**[평상시 모드]**\n👉 **[NO-SELL]**\n신규: MAGS 45% / QLD 30% / SCHD 20% / GLDM 5%")

with c3:
    st.info("#### 🧠 삼성 연금저축\n**스마트 DCA V6.0**")
    if accelerator_triggered: st.error("**[액셀러 모드]**\n👉 **[전량 스위칭]**\nACE 빅테크TOP7 65% / KIWOOM 모멘텀 35%")
    elif is_break_3days: st.warning("**[브레이크 작동]**\n👉 **[주식 전량 매도]**\nTIME 배당다우존스 60% / KODEX 머니마켓 40%")
    elif ndx_rsi >= 70: st.warning("**[과열 방어]**\n👉 **[리밸런싱]**\n빅테크TOP7 30% / 모멘텀 30% / 머니마켓 40%")
    else: st.success("**[평상시 모드]**\n👉 **[리밸런싱]**\n빅테크TOP7 50% / 모멘텀 35% / 머니마켓 15%")