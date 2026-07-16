import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- 1. 페이지 설정 및 다크 그레이 디자인 ---
st.set_page_config(page_title="통합 내비게이션 V7.1 (Ultimate Dark)", layout="wide")

st.markdown("""
    <style>
    /* Ultimate Dark Grey Theme (#202024) */
    .stApp { background-color: #202024; color: #e1e1e6; }
    .block-container { padding-top: 2.5rem !important; padding-bottom: 1rem !important; }
    h1 { margin-top: 0px !important; margin-bottom: 5px !important; font-size: 26px !important; font-weight: 800; color: #ffffff !important; }
    h2 { border-left: 5px solid #00e5ff; padding-left: 10px; margin-top: 20px !important; margin-bottom: 5px !important; font-size: 18px !important; color: #00e5ff !important; }
    h3, h4 { color: #ffffff !important; margin-top: 0px !important; margin-bottom: 10px !important;}
    th { background-color: #161619 !important; color: #00e5ff !important; font-weight: bold !important; padding: 8px 12px !important; font-size: 13px !important; border: 1px solid #3a3a42 !important; }
    td { text-align: left !important; vertical-align: middle !important; padding: 8px 12px !important; font-size: 13px !important; border: 1px solid #3a3a42 !important; color: #ffffff !important; }
    div[data-testid="stTable"] table { width: 100% !important; margin-top: 0px !important; margin-bottom: 0px !important; }
    
    /* 통합 카드 UI 스타일 */
    .portfolio-card { background-color: #1a1a1e; border: 1px solid #3a3a42; border-radius: 8px; padding: 15px; margin-bottom: 10px; }
    .portfolio-card-header { font-size: 15px; font-weight: bold; margin-bottom: 5px; }
    .portfolio-card-desc { font-size: 12px; color: #94a3b8; margin-bottom: 12px; }
    .portfolio-card-content { background-color: #121214; padding: 10px 12px; border-radius: 6px; font-size: 14px; letter-spacing: 0.5px; }
    
    /* 시황 분석 전용 박스 */
    .context-box { background-color: #161619; border: 1px dashed #3a3a42; border-radius: 6px; padding: 12px 15px; margin-top: 8px; margin-bottom: 15px; font-size: 13.5px; line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

# 60초마다 화면을 자동으로 다시 불러와 실시간 지표 갱신
st.fragment(run_every=60)

def calculate_rsi(series, period=14):
    delta = series.diff()
    up, down = delta.copy(), delta.copy()
    up[up < 0] = 0
    down[down > 0] = 0
    _gain = up.ewm(com=(period - 1), min_periods=period).mean()
    _loss = down.abs().ewm(com=(period - 1), min_periods=period).mean()
    RS = _gain / _loss
    return 100 - (100 / (1 + RS))

# 데이터 무한 대기 방지를 위한 예외 처리 및 10초 타임아웃
@st.cache_data(ttl=10)
def get_market_data():
    try:
        ndx = yf.download("^NDX", period="1y", progress=False, group_by="column")
        sp500 = yf.download("^GSPC", period="1y", progress=False, group_by="column")
        vix = yf.download("^VIX", period="1y", progress=False, group_by="column")
        qqq = yf.download("QQQ", period="1y", progress=False, group_by="column")
        
        if ndx.empty or sp500.empty or vix.empty or qqq.empty:
            return None

        df = pd.DataFrame(index=ndx.index)
        df['NDX_Close'] = ndx['Close'].iloc[:, 0] if len(ndx['Close'].shape) > 1 else ndx['Close']
        df['SP500_Close'] = sp500['Close'].iloc[:, 0] if len(sp500['Close'].shape) > 1 else sp500['Close']
        df['VIX_Close'] = vix['Close'].iloc[:, 0] if len(vix['Close'].shape) > 1 else vix['Close']
        df['Volume'] = qqq['Volume'].iloc[:, 0] if len(qqq['Volume'].shape) > 1 else qqq['Volume']
        
        df = df.ffill().dropna()
        df['NDX_125EMA'] = df['NDX_Close'].ewm(span=125, adjust=False).mean()
        df['NDX_50EMA'] = df['NDX_Close'].ewm(span=50, adjust=False).mean()
        df['SP500_200EMA'] = df['SP500_Close'].ewm(span=200, adjust=False).mean()
        df['NDX_RSI'] = calculate_rsi(df['NDX_Close'])
        df['Vol_20MA'] = df['Volume'].rolling(window=20).mean()
        return df.dropna()
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

# --- 3. 사이드바 (지표 입력 및 계산기) ---
st.sidebar.title("🧪 매크로 지표 입력 및 시뮬레이터")
sim_mode = st.sidebar.checkbox("🚨 인위적 테스트 모드 (수동 조작)", value=fetch_error)

if sim_mode:
    st.sidebar.subheader("🕹️ 차트 데이터 강제 조작")
    ndx_rsi = st.sidebar.slider("나스닥100 일봉 RSI", 0.0, 100.0, 25.0, 0.1)
    vix = st.sidebar.slider("VIX 공포 지수", 0.0, 80.0, 32.0, 0.1)
    is_break_3days = st.sidebar.checkbox("나스닥100 125일선 3일 연속 하회 (브레이크)", value=False)
    ndx_close = 18000.0 if is_break_3days else 20000.0
    ndx_125, ndx_50 = 19000.0, 19500.0
else:
    ndx_rsi, vix, is_break_3days = real_ndx_rsi, real_vix, real_is_break_3days
    ndx_close, ndx_125, ndx_50 = real_ndx_close, real_ndx_125, real_ndx_50

st.sidebar.markdown("---")
st.sidebar.subheader("📉 필수 채권 지표 입력 (FRED)")
st.sidebar.caption("값을 자유롭게 입력하세요. 스위치를 켜기 전까지는 적용되지 않습니다.")

# 값을 입력받기만 하고 아직 시스템에 적용하지 않음 (temp 변수)
temp_hy = st.sidebar.number_input("1. 현재 하이일드 스프레드 (%)", 0.0, 20.0, 2.71, 0.01, key="hy_val")
temp_hy_max = st.sidebar.number_input("2. 최근 20일 내 최고점 수치 (%)", 0.0, 20.0, 4.26, 0.01, key="hy_max_val")

st.sidebar.markdown("---")
st.sidebar.subheader("📊 보조 감시 지표 (메인 신호 제외됨)")
temp_fg = st.sidebar.number_input("CNN 공포와 탐욕 지수", 0, 100, 47, key="fg_val")
temp_pcr = st.sidebar.number_input("CBOE 풋콜레이시오", 0.0, 3.0, 0.93, 0.01, key="pcr_val")

st.sidebar.markdown("---")
# [새롭게 설계된 의도 반영] ON/OFF 스위치
apply_macro_toggle = st.sidebar.toggle("🚀 위 수치들을 시스템에 일괄 적용 (ON/OFF)", value=False)

# 스위치가 ON일 때만 입력한 수치(temp)를 실제 계산용 수치(input)로 덮어씌움
if apply_macro_toggle:
    st.sidebar.success("✅ [적용됨] 입력하신 수치로 대시보드가 계산됩니다.")
    input_hy = temp_hy
    input_hy_max = temp_hy_max
    input_fg = temp_fg
    input_pcr = temp_pcr
# 스위치가 OFF일 때는 숫자를 아무리 바꿔도 대시보드가 꿈쩍 안 하도록 기본값으로 고정
else:
    st.sidebar.warning("⏸️ [대기 중] 스위치를 켜면 메인 화면에 적용됩니다.")
    input_hy = 2.71
    input_hy_max = 4.26
    input_fg = 47
    input_pcr = 0.93

st.sidebar.markdown("---")
st.sidebar.title("🧮 2종 자산 배분 계산기")
with st.sidebar.expander("계산기 열기 (클릭)", expanded=False):
    tab1, tab2 = st.tabs(["금액 ➔ 비중", "비중 ➔ 금액"])
    with tab1:
        cv1 = st.number_input("항목 1 금액", value=0, step=10000, key="c1_1")
        cv2 = st.number_input("항목 2 금액", value=0, step=10000, key="c1_2")
        tot_val = cv1 + cv2
        if tot_val > 0: st.info(f"항목 1: {(cv1/tot_val)*100:.1f}% / 항목 2: {(cv2/tot_val)*100:.1f}%")
    with tab2:
        t_asset = st.number_input("총 투자 금액", value=1000000, step=10000, key="c2_tot")
        cp1 = st.number_input("항목 1 비중 (%)", value=50.0, step=1.0, key="c2_1")
        cp2 = st.number_input("항목 2 비중 (%)", value=50.0, step=1.0, key="c2_2")
        if abs(cp1 + cp2 - 100.0) > 0.01: st.error("비중 합계 오류")
        else: st.success(f"항목 1: {t_asset*(cp1/100):,.0f} / 항목 2: {t_asset*(cp2/100):,.0f}")

# V7.1 핵심 로직 판정 엔진
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
    st.markdown("<p style='font-size:13px; margin-top:-8px; color:#a1a1aa;'>본업에 집중하십시오. 60초마다 실시간으로 동기화 중입니다.</p>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
card_css = "background-color:#161619; border:1px solid #3a3a42; border-left:4px solid #00e5ff; border-radius:4px; padding:10px 15px; display:flex; justify-content:space-between; align-items:center; height:45px;"

with col1: 
    st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">나스닥100 RSI</span><span style="font-size:16px; font-weight:bold; color:{"#ff4500" if ndx_rsi >= 70 else ("#00e5ff" if ndx_rsi <=30 else "#ffffff")};">{ndx_rsi:.2f}</span></div>', unsafe_allow_html=True)
    st.link_button("🔍 수동 확인 (Yahoo)", "https://finance.yahoo.com/quote/%5ENDX/chart", use_container_width=True)
    
with col2: 
    st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">VIX 지수</span><span style="font-size:16px; font-weight:bold; color:{"#00e5ff" if vix >= 30 else "#ffffff"};">{vix:.2f}</span></div>', unsafe_allow_html=True)
    st.link_button("🔍 수동 확인 (Yahoo)", "https://finance.yahoo.com/quote/%5EVIX/chart", use_container_width=True)
    
with col3: 
    st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">현재 스프레드</span><span style="font-size:16px; font-weight:bold; color:{"#ff9900" if input_hy >= 5.0 else "#ffffff"};">{input_hy}%</span></div>', unsafe_allow_html=True)
with col4: 
    hy_status = "✅ 매수 승인(Pass)" if hy_approved else "⛔ 대기(Wait)"
    st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">하이일드 판정</span><span style="font-size:14px; font-weight:bold; color:#00ff66;">{hy_status}</span></div>', unsafe_allow_html=True)

# --- 1. 시스템 확정 모드 및 실시간 동적 시황 해설 ---
st.markdown("## 🎯 1. V7.1 시스템 확정 모드 (Action Required)")

if current_mode == "액셀러":
    st.error("### 🔵 [액셀러 모드] 7:3 기동 타격 집행 (대바닥)")
    hy_reason = f"절대 기준선인 3.50% 이하({input_hy}%)이거나 피크아웃 조건(-0.20%p 꺾임)을 충족" if hy_approved else "조건 미달"
    explanation_html = f"""
    <div class="context-box">
        🔍 <b>실시간 지표 값 매칭 사유 및 시황 분석:</b><br>
        • <b>나스닥100 RSI ({ndx_rsi:.2f}):</b> 진바닥 임계치인 30 미만을 완벽하게 하회하여 극단적 과매도 국면임을 증명합니다.<br>
        • <b>VIX 공포 지수 ({vix:.2f}):</b> 패닉 셀링의 기준선인 30 이상으로 치솟아 시장에 공포 투매가 발생했음을 확증합니다.<br>
        • <b>하이일드 스프레드 ({input_hy}%):</b> 신용 위험이 통제되는 안정권({hy_reason})에 포지셔닝되어 있습니다.<br>
        💡 <b>종합 결론:</b> 주식 시장은 극단적 공포 발작을 일으켰으나 채권 시장이 보증하는 금융 시스템 붕괴 위험은 없는 <b>'역사적 진바닥 스나이핑 찬스'</b>이므로 시스템 매트릭스에 의거해 자금을 압축 투하(7:3 법칙)합니다.
    </div>
    """
elif current_mode == "브레이크":
    st.warning("### 🟡 [브레이크 모드] 전량 벙커 대피 (추세 붕괴)")
    explanation_html = f"""
    <div class="context-box">
        🔍 <b>실시간 지표 값 매칭 사유 및 시황 분석:</b><br>
        • <b>나스닥100 추세선:</b> 나스닥100 종가가 코어 기준선인 125일 이동평균선을 <b>3거래일 연속으로 확실하게 하회</b> 이탈했습니다.<br>
        • <b>매크로 리스크:</b> 단기 심리 지표(RSI, VIX)의 반등 여부와 관계없이 중장기 추세 축이 완전히 무너진 장기 하락장 초입 국면입니다.<br>
        💡 <b>종합 결론:</b> 레버리지 자산의 음의 복리 독성을 원천 차단해야 하는 타이밍입니다. 위험자산 집행을 전면 중단하고 절세 계좌 내 보유분은 <b>100% 시장가 청산하여 현금/금 벙커 영역으로 대피</b> 조치합니다.
    </div>
    """
elif current_mode == "과열 방어":
    st.error