import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. 페이지 설정 및 다크 그레이 디자인 ---
st.set_page_config(page_title="통합 내비게이션 V7.1 (Ultimate Dark)", layout="wide")

st.markdown("""
    <style>
    /* Ultimate Dark Grey Theme (#202024) */
    .stApp { background-color: #202024; color: #e1e1e6; }
    .block-container { padding-top: 2.5rem !important; padding-bottom: 1rem !important; }
    h1 { margin-top: 0px !important; margin-bottom: 5px !important; font-size: 26px !important; font-weight: 800; color: #ffffff !important; }
    h2 { border-left: 5px solid #00e5ff; padding-left: 10px; margin-top: 20px !important; margin-bottom: 5px !important; font-size: 18px !important; color: #00e5ff !important; }
    h3, h4 { color: #ffffff !important; }
    th { background-color: #161619 !important; color: #00e5ff !important; font-weight: bold !important; padding: 8px 12px !important; font-size: 13px !important; border: 1px solid #3a3a42 !important; }
    td { text-align: left !important; vertical-align: middle !important; padding: 8px 12px !important; font-size: 13px !important; border: 1px solid #3a3a42 !important; color: #ffffff !important; }
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

# 데이터 무한 대기 방지를 위한 예외 처리 탑재
@st.cache_data(ttl=3600)
def get_market_data():
    try:
        ndx = yf.download("^NDX", period="1y", progress=False)
        sp500 = yf.download("^GSPC", period="1y", progress=False)
        vix = yf.download("^VIX", period="1y", progress=False)
        qqq = yf.download("QQQ", period="1y", progress=False)
        
        if ndx.empty or sp500.empty or vix.empty or qqq.empty:
            return None

        df = pd.DataFrame(index=ndx.index)
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
st.title("🧭 HYPER-INVEST 통합 내비게이션 V7.1")

df = get_market_data()
fetch_error = False

if df is None or df.empty:
    fetch_error = True
    st.error("🚨 실시간 시장 데이터 통신에 실패했습니다. 수동 '테스트 모드'로 전환됩니다.")
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
st.sidebar.title("🧪 매크로 지표 입력 및 시뮬레이터")
sim_mode = st.sidebar.checkbox("🚨 인위적 테스트 모드 (수동 조작)", value=fetch_error)

if sim_mode:
    st.sidebar.subheader("🕹️ 차트 데이터 강제 조작")
    ndx_rsi = st.sidebar.slider("나스닥 일봉 RSI", 0.0, 100.0, 25.0, 0.1)
    vix = st.sidebar.slider("VIX 공포 지수", 0.0, 80.0, 32.0, 0.1)
    is_break_3days = st.sidebar.checkbox("나스닥 125일선 3일 연속 하회 (브레이크)", value=False)
    ndx_close = 18000.0 if is_break_3days else 20000.0
    ndx_125, ndx_50 = 19000.0, 19500.0
else:
    ndx_rsi, vix, is_break_3days = real_ndx_rsi, real_vix, real_is_break_3days
    ndx_close, ndx_125, ndx_50 = real_ndx_close, real_ndx_125, real_ndx_50

st.sidebar.markdown("---")
st.sidebar.subheader("📉 필수 채권 지표 입력 (FRED)")
input_hy = st.sidebar.number_input("1. 현재 하이일드 스프레드 (%)", 0.0, 20.0, 3.20, 0.01)
input_hy_max = st.sidebar.number_input("2. 최근 20일 내 최고점 수치 (%)", 0.0, 20.0, 3.40, 0.01)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 보조 감시 지표 (메인 신호 제외됨)")
input_fg = st.sidebar.number_input("CNN 공포와 탐욕 지수", 0, 100, 45)
input_pcr = st.sidebar.number_input("CBOE 풋콜레이시오", 0.0, 3.0, 0.9, 0.01)

# V7.1 핵심 로직 판정 엔진 (배타적 독립 실행)
hy_approved = (input_hy <= 3.50) or (input_hy <= (input_hy_max - 0.20))
accel_triggered = (ndx_rsi < 30) and (vix >= 30)

if accel_triggered and hy_approved:
    current_mode = "액셀러"
elif is_break_3days:
    current_mode = "브레이크"
elif ndx_rsi >= 70:
    current_mode = "과열 방어"
else:
    current_mode = "평상시"

# --- 4. 메인 뷰 대시보드 ---
if sim_mode and not fetch_error:
    st.error("⚠️ 현재 [인위적 테스트 모드]가 활성화 중입니다. 실제 시장 데이터가 아닙니다.")
elif not fetch_error:
    st.markdown("<p style='font-size:13px; margin-top:-8px; color:#a1a1aa;'>본업에 집중하십시오. 매주 금요일 오전 9시 기준 V7.1 마스터 레이어 동기화 코드입니다.</p>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
card_css = "background-color:#161619; border:1px solid #3a3a42; border-left:4px solid #00e5ff; border-radius:4px; padding:10px 15px; display:flex; justify-content:space-between; align-items:center; height:45px;"

with col1: 
    st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">나스닥 RSI</span><span style="font-size:16px; font-weight:bold; color:{"#ff4500" if ndx_rsi >= 70 else ("#00e5ff" if ndx_rsi <=30 else "#ffffff")};">{ndx_rsi:.2f}</span></div>', unsafe_allow_html=True)
with col2: 
    st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">VIX 지수</span><span style="font-size:16px; font-weight:bold; color:{"#00e5ff" if vix >= 30 else "#ffffff"};">{vix:.2f}</span></div>', unsafe_allow_html=True)
with col3: 
    st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">현재 스프레드</span><span style="font-size:16px; font-weight:bold; color:{"#ff9900" if input_hy >= 5.0 else "#ffffff"};">{input_hy}%</span></div>', unsafe_allow_html=True)
with col4: 
    hy_status = "✅ 매수 승인(Pass)" if hy_approved else "⛔ 대기(Wait)"
    st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">하이일드 판정</span><span style="font-size:14px; font-weight:bold; color:#00ff66;">{hy_status}</span></div>', unsafe_allow_html=True)

st.markdown("## 🎯 1. V7.1 시스템 확정 모드 (Action Required)")
if current_mode == "액셀러":
    st.error("### 🔵 [액셀러 모드] 7:3 기동 타격 집행 (대바닥)")
elif current_mode == "브레이크":
    st.warning("### 🟡 [브레이크 모드] 전량 벙커 대피 (추세 붕괴)")
elif current_mode == "과열 방어":
    st.error("### 🔴 [과열 방어 모드] 안전 자산 선제 확보 (단기 꼭대기)")
else:
    st.success("### 🟢 [평상시 모드] 기본 포메이션 분산 적립 (우상향)")

st.markdown("---")
st.markdown("### 📊 2. 3대 투자 전략별 포지션 오더 (V7.1 매트릭스)")

c1, c2, c3 = st.columns(3)

with c1:
    st.info("#### 🧠 연금저축 (하이퍼-스마트)\n**[보유분 일괄 동적 스위칭]**")
    if current_mode == "액셀러": st.write("• 빅테크 80%\n• 배당 20%\n• 머니마켓 0%")
    elif current_mode == "브레이크": st.write("• 빅테크 0%\n• 배당 40%\n• 머니마켓 60%")
    elif current_mode == "과열 방어": st.write("• 빅테크 40%\n• 배당 40%\n• 머니마켓 20%")
    else: st.write("• 빅테크 70%\n• 배당 30%\n• 머니마켓 0%")

with c2:
    st.info("#### 🛡️ NH ISA (무결성 부스터)\n**[100% 전량 청산 대피 적용]**")
    if current_mode == "액셀러": st.write("• 나스닥 2배 레버 100%\n• 금현물 0%\n• 머니마켓 0%")
    elif current_mode == "브레이크": st.write("• 레버리지 0%\n• 금현물 70%\n• 머니마켓 30%")
    elif current_mode == "과열 방어": st.write("• 레버리지 30%\n• 금현물 50%\n• 머니마켓 20%")
    else: st.write("• 레버리지 75%\n• 금현물 25%\n• 머니마켓 0%")

with c3:
    st.info("#### 🚀 메리츠 직투 (액셀러레이터)\n**[Strict NO-SELL / 신규자금만]**")
    if current_mode == "액셀러": st.write("• QLD 45%\n• MAGS 55%\n• SCHD 0%\n• GLDM 0%")
    elif current_mode == "브레이크": st.write("• QLD 0%\n• MAGS 0%\n• SCHD 50%\n• GLDM 50%")
    elif current_mode == "과열 방어": st.write("• QLD 15%\n• MAGS 30%\n• SCHD 30%\n• GLDM 25%")
    else: st.write("• QLD 45%\n• MAGS 30%\n• SCHD 20%\n• GLDM 5%")

# --- 비서의 전문 검증 및 조언 섹션 ---
st.markdown("---")
st.subheader("📋 3. 투자비서 데이터 무결성 검증 레이어")
with st.expander("가짜 속임수 신호 판독 및 매크로 리스크 결과 보기", expanded=True):
    
    st.markdown(f"1. **가짜 하락 차단 (거래량):**")
    if vol_surge:
        st.markdown("   * 🔴 **[패스]** QQQ 거래량이 20일 평균 대비 1.5배 이상 터진 '진짜 하락'입니다.")
    else:
        st.markdown("   * 🟢 **[주의]** 거래량이 동반되지 않은 단순 노이즈(속임수)일 확률이 높습니다.")
        
    st.markdown(f"2. **단기 추세 판독 (50일선):**")
    if ndx_close > ndx_50:
        st.markdown("   * 🟢 지수가 50일선 위에 있습니다. 단기 상승 불씨가 완전히 꺼지지 않았으므로 섣부른 뇌동매매를 삼가십시오.")
    else:
        st.markdown("   * 🔴 지수가 50일선 아래로 뚫렸습니다. 하락 에너지가 강해지고 있습니다.")
        
    st.markdown(f"3. **하이일드 피크아웃 공식 검증:**")
    hy_diff = input_hy_max - input_hy
    if input_hy <= 3.50:
        st.markdown(f"   * ✅ 현재 {input_hy}%로 절대 수치 3.50% 이하입니다. **[가짜 위기 프리패스]** 조건이 충족되었습니다.")
    elif hy_diff >= 0.20:
        st.markdown(f"   * ✅ 최고점({input_hy_max}%) 대비 현재 {input_hy}%로 정확히 **{-hy_diff:.2f}%p 꺾였습니다.** **[피크아웃 확정]** 조건이 충족되었습니다.")
    else:
        st.markdown(f"   * ⛔ 최고점 대비 꺾임 폭이 {-hy_diff:.2f}%p에 불과합니다(-0.20%p 미달). 지하실 리스크가 있으므로 아직 매수 금지입니다.")

# 링크 섹션
st.markdown("---")
st.caption("🌐 공식 데이터 소스 다이렉트 라우팅")
cl1, cl2 = st.columns(2)
with cl1: st.link_button("FRED 하이일드 스프레드 확인", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", use_container_width=True)
with cl2: st.link_button("CNN 공포와 탐욕 지수 (보조)", "https://edition.cnn.com/markets/fear-and-greed", use_container_width=True)