import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="투자 내비게이션 V3.0 (Dynamic)", layout="wide")

# 🛠️ [상민님 피드백 반영] 이미지2의 시원시원한 기존 크기 및 상하 간격을 100% 복원
st.markdown("""
    <style>
    .stMetric { padding: 10px; border-radius: 10px; border: 1px solid rgba(128, 128, 128, 0.2); }
    h1 { font-weight: 800; }
    h2 { border-left: 5px solid #1e293b; padding-left: 10px; margin-top: 30px; }
    .stAlert { border-left: 5px solid #334155 !important; }
    
    /* 기존 이미지2의 쾌적한 풀사이즈 레이아웃 스타일 */
    th { background-color: #f8fafc !important; font-weight: bold !important; padding: 10px 12px !important; }
    td { text-align: left !important; vertical-align: middle !important; padding: 10px 12px !important; }
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

# --- 2. 데이터 처리 ---
df = get_market_data()
current = df.iloc[-1]
prev_3days = df.iloc[-4:-1]

real_ndx_close, real_ndx_125, real_ndx_50 = round(current['NDX_Close'], 2), round(current['NDX_125EMA'], 2), round(current['NDX_50EMA'], 2)
real_ndx_rsi, real_vix = round(current['NDX_RSI'], 2), round(current['VIX_Close'], 2)
real_sp500_close, real_sp500_200 = round(current['SP500_Close'], 2), round(current['SP500_200EMA'], 2)
vol_surge = current['Volume'] > current['Vol_20MA'] * 1.5
real_is_break_3days = (prev_3days['NDX_Close'] < prev_3days['NDX_125EMA']).all() and (real_ndx_close < real_ndx_125)

# --- 3. 사이드바 (지표 입력 및 계산기 탑재) ---
st.sidebar.title("🧪 모드 설정 및 입력")

sim_mode = st.sidebar.checkbox("🚨 인위적 테스트 모드 활성화", value=False, help="체크 시 실시간 데이터 대신 사이드바 입력값으로 강제 테스트합니다.")

st.sidebar.markdown("---")

if sim_mode:
    st.sidebar.subheader("🕹️ 테스트용 데이터 조작")
    ndx_rsi = st.sidebar.slider("나스닥 RSI 설정", 0.0, 100.0, 25.0, 0.1)
    vix = st.sidebar.slider("VIX 지수 설정", 0.0, 60.0, 35.0, 0.1)
    is_break_3days = st.sidebar.checkbox("나스닥 125일선 3일 연속 하회 상황 가정", value=False)
    
    ndx_close = 25000.0 if is_break_3days else 29500.0
    ndx_125 = 25932.79
    ndx_50 = 26000.0
    sp500_close = 7473.47
    sp500_200 = 6787.59
else:
    ndx_rsi = real_ndx_rsi
    vix = real_vix
    is_break_3days = real_is_break_3days
    ndx_close = real_ndx_close
    ndx_125 = real_ndx_125
    ndx_50 = real_ndx_50
    sp500_close = real_sp500_close
    sp500_200 = real_sp500_200

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

# 자산 배분 계산기 UI
st.sidebar.title("🧮 자산 배분 계산기")
with st.sidebar.expander("계산기 열기 (클릭)", expanded=False):
    tab1, tab2 = st.tabs(["금액 ➔ 비중", "비중 ➔ 금액"])
    
    with tab1:
        st.caption("각 자산의 평가금액을 입력하면 비중이 자동 계산됩니다.")
        cv1 = st.number_input("항목 1 금액", value=0, step=10000, key="c1_1")
        cv2 = st.number_input("항목 2 금액", value=0, step=10000, key="c1_2")
        cv3 = st.number_input("항목 3 금액", value=0, step=10000, key="c1_3")
        cv4 = st.number_input("항목 4 금액", value=0, step=10000, key="c1_4")
        tot_val = cv1 + cv2 + cv3 + cv4
        
        if tot_val > 0:
            st.info(f"**총 자산: {tot_val:,.0f}**\n\n"
                    f"- **항목 1:** {(cv1/tot_val)*100:.1f}%\n\n"
                    f"- **항목 2:** {(cv2/tot_val)*100:.1f}%\n\n"
                    f"- **항목 3:** {(cv3/tot_val)*100:.1f}%\n\n"
                    f"- **항목 4:** {(cv4/tot_val)*100:.1f}%")
        else:
            st.info("금액을 입력해주세요.")

    with tab2:
        st.caption("총 자산과 목표 비중(%)을 입력하면 배분 금액이 계산됩니다.")
        t_asset = st.number_input("총 투자 금액", value=1000000, step=10000, key="c2_tot")
        cp1 = st.number_input("항목 1 비중 (%)", value=40.0, step=1.0, key="c2_1")
        cp2 = st.number_input("항목 2 비중 (%)", value=30.0, step=1.0, key="c2_2")
        cp3 = st.number_input("항목 3 비중 (%)", value=20.0, step=1.0, key="c2_3")
        cp4 = st.number_input("항목 4 비중 (%)", value=10.0, step=1.0, key="c2_4")
        tot_pct = cp1 + cp2 + cp3 + cp4
        
        if abs(tot_pct - 100.0) > 0.01:
            st.error(f"⚠️ 비중 합계 오류! (현재: {tot_pct}%)")
        else:
            st.success(f"**배분 목표 (총 {t_asset:,.0f})**\n\n"
                       f"- **항목 1:** {t_asset * (cp1/100):,.0f}\n\n"
                       f"- **항목 2:** {t_asset * (cp2/100):,.0f}\n\n"
                       f"- **항목 3:** {t_asset * (cp3/100):,.0f}\n\n"
                       f"- **항목 4:** {t_asset * (cp4/100):,.0f}")

# --- 4. 메인 화면 ---
st.title("🧭 통합 투자 내비게이션 V3.0 (Premium Dynamic)")
if sim_mode:
    st.error("⚠️ 현재 [인위적 테스트 모드]가 활성화 중입니다. 실제 시장 데이터가 아닙니다.")
else:
    st.markdown("본업에 집중하십시오. 국내 절세 계좌의 보유분 전량 스위칭 로직이 동기화된 코드입니다.")
st.markdown("---")

# 최상단 요약 카드
rsi_status = "-과열 (경계)" if ndx_rsi >= 70 else ("-공포 (기회)" if ndx_rsi <= 30 else "정상 구간")
vix_status = "-위험 구간" if vix >= 30 else "안정 구간"
fg_status = "-극단적 공포" if input_fg <= 25 else "정상 구간"
hy_status = "-위험 감지" if input_hy >= 5.0 else "안정 구간"
pcr_status = "-바닥 신호" if input_pcr >= 1.1 else "정상 구간"

col1, col2, col3, col4 = st.columns(4)
col1.metric("나스닥 RSI (실시간)", f"{ndx_rsi:.2f}", rsi_status)
col2.metric("VIX 지수 (실시간)", f"{vix:.2f}", vix_status)
col3.metric("공포와 탐욕 지수 (수동연동)", f"{input_fg}", fg_status)
col4.metric("HY 스프레드 / PCR (수동연동)", f"{input_hy}% / {input_pcr:.2f}", f"{hy_status} | {pcr_status}")

# --- 1. 메인 감시 지표 (이미지2 풀사이즈 크기 원상복구 버전) ---
st.markdown("---")
st.markdown("### 📊 1. 메인 감시 지표 (Primary Triggers)")

# 🛠️ [가시성 패치] 크기는 이미지2처럼 넓고 시원하게 복원하되, 이모지와 구분선 기호로 가시성 극대화
trigger_data = {
    "지표": [
        "나스닥 100 지수 (RSI)", 
        "VIX 지수", 
        "S&P 500 (200일선)", 
        "나스닥 100 (125일선)", 
        "공포와 탐욕 (수동)", 
        "풋콜레이시오 (수동)", 
        "하이일드 스프레드 (수동)"
    ],
    "트리거 발생 기준": [
        "[기회] 30 이하  /  [경계] 70 이상  ➔  (정밀 심리 지표 감시 구간)", 
        "🚨 30 이상  ➔  (시장 변동성 폭발 및 패닉 투매 상태 감지)", 
        "❌ 지수 이탈  ➔  (장기 우상향 추세 붕괴 및 거대 기관 자금 이탈)", 
        "⚠️ 3거래일 연속 하회  ➔  (중장기 추세 하락 확정 및 최종 브레이크 필터)", 
        "💀 25 미만  ➔  (역발상 타격 기회 - 군중 극단적 공포 Extreme Fear)", 
        "📊 1.1 이상  ➔  (하락 베팅 극대화 - 강한 반등을 위한 하방 힘 응축)", 
        "⚡ 5.0% 이상 또는 피크아웃 미확정  ➔  (거시 경제 신용 부도 위험 및 금융 시스템 리스크 추적)"
    ],
    "현재 수치 / 상태": [
        f"{ndx_rsi:.2f}", f"{vix:.2f}", f"{sp500_close:,.2f} (기준: {sp500_200:,.2f})", f"{ndx_close:,.2f} (기준: {ndx_125:,.2f})", 
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
# 이미지2처럼 스트림릿 본연의 컴팩트하고 넓은 정식 테이블 객체로 출력
st.table(pd.DataFrame(trigger_data))

# --- 2. 심리 및 매크로 수동 지표 확인 ---
st.markdown("---")
st.markdown("### 🔍 2. 심리 및 매크로 수동 지표 확인 (Data Source Verification)")
st.caption("자동 크롤링이 불가능한 핵심 지표들을 수동 검증하기 위한 데이터 소스 및 API 확인 라우터입니다.")

col_l1, col_l2, col_l3 = st.columns(3)
with col_l1:
    st.info("#### 🔴 CNN 공포와 탐욕 지수 소스")
    st.markdown("- **제공처:** CNN Business Market\n- **성격:** 군중 주관적 투자 심리 필터\n- **API 상태:** 외부 차단 (수동 조회 필수)")
    st.link_button("🌐 CNN 공식 소스 확인하기", "https://edition.cnn.com/markets/fear-and-greed", use_container_width=True)

with col_l2:
    st.info("#### 🟢 CBOE 토탈 풋콜레이시오 소스 (★오류 완벽 해결)")
    st.markdown("- **제공처:** 트레이딩뷰(TradingView) 금융 엔진\n- **성격:** 브라우저나 국가별 환경을 절대 타지 않는 글로벌 표준 지수 라이브러리\n- **특징:** 모바일 세로 화면에서도 잘림이나 404 에러 없이 실시간 Total P/C Ratio의 당일 확정 수치가 메