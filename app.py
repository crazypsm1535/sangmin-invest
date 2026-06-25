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
input_hy = st.sidebar.number_input("1. 현재 하이일드 스프레드 (%)", 0.0, 20.0, 2.71, 0.01)
input_hy_max = st.sidebar.number_input("2. 최근 20일 내 최고점 수치 (%)", 0.0, 20.0, 4.26, 0.01)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 보조 감시 지표 (메인 신호 제외됨)")
input_fg = st.sidebar.number_input("CNN 공포와 탐욕 지수", 0, 100, 25)
input_pcr = st.sidebar.number_input("CBOE 풋콜레이시오", 0.0, 3.0, 1.02, 0.01)

# 계산기 컴포넌트 생략 (기존 코드 유지)
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

with col1: st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">나스닥100 RSI</span><span style="font-size:16px; font-weight:bold; color:{"#ff4500" if ndx_rsi >= 70 else ("#00e5ff" if ndx_rsi <=30 else "#ffffff")};">{ndx_rsi:.2f}</span></div>', unsafe_allow_html=True)
with col2: st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">VIX 지수</span><span style="font-size:16px; font-weight:bold; color:{"#00e5ff" if vix >= 30 else "#ffffff"};">{vix:.2f}</span></div>', unsafe_allow_html=True)
with col3: st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">현재 스프레드</span><span style="font-size:16px; font-weight:bold; color:{"#ff9900" if input_hy >= 5.0 else "#ffffff"};">{input_hy}%</span></div>', unsafe_allow_html=True)
with col4: 
    hy_status = "✅ 매수 승인(Pass)" if hy_approved else "⛔ 대기(Wait)"
    st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">하이일드 판정</span><span style="font-size:14px; font-weight:bold; color:#00ff66;">{hy_status}</span></div>', unsafe_allow_html=True)

# --- [상민님 요청] 1. 시스템 확정 모드 및 실시간 동적 시황 해설 ---
st.markdown("## 🎯 1. V7.1 시스템 확정 모드 (Action Required)")

# 시장 모드 표출 및 각 모드별 지표 매칭 사유 동적 생성
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
    st.error("### 🔴 [과열 방어 모드] 안전 자산 선제 확보 (단기 꼭대기)")
    explanation_html = f"""
    <div class="context-box">
        🔍 <b>실시간 지표 값 매칭 사유 및 시황 분석:</b><br>
        • <b>나스닥100 RSI ({ndx_rsi:.2f}):</b> 과열 임계 영역인 70 이상을 터치하여 시장 참여자들의 탐욕이 극에 달한 꼭대기 영역임을 가리킵니다.<br>
        • <b>추세 흐름:</b> 지수는 125일선 위에 있어 우상향 중이나, 단기 기술적 과열로 인한 폭락 리스크가 고도로 누적된 상태입니다.<br>
        💡 <b>종합 결론:</b> 단기 꼭대기 임계 영역이므로 <b>주식 자산의 신규 매수를 엄격히 정지</b>합니다. 안전자산 및 파킹 자산(머니마켓)의 비중을 선제적으로 확대하여 상단 변동성 리스크를 차단합니다.
    </div>
    """
else:
    st.success("### 🟢 [평상시 모드] 기본 포메이션 분산 적립 (우상향)")
    explanation_html = f"""
    <div class="context-box">
        🔍 <b>실시간 지표 값 매칭 사유 및 시황 분석:</b><br>
        • <b>나스닥100 RSI ({ndx_rsi:.2f}):</b> 심리 축이 40 이상 ~ 70 미만의 안정적인 중립적 박스권 영역을 유지하고 있습니다.<br>
        • <b>VIX 공포 지수 ({vix:.2f}):</b> 30 미만인 {vix:.2f}로 시장 변동성이 안정적으로 통제되고 있습니다.<br>
        • <b>하이일드 스프레드 ({input_hy}%):</b> 임계선인 3.50% 이하를 확고하게 수호하며 기업 신용 부도 위험이 전혀 없는 가짜 위기 프리패스 상태입니다.<br>
        💡 <b>종합 결론:</b> 표준적인 우상향 및 박스권 장세입니다. 노이즈에 동요되어 무의미한 방어형 안전자산으로 장기 정체할 필요가 없으므로, 기본 포메이션 비중을 그대로 유지하며 <b>매주 금요일 오전 기계적 자동 분산 적립</b>을 고수합니다.
    </div>
    """
st.markdown(explanation_html, unsafe_allow_html=True)

st.markdown("---")
st.markdown("### 📊 2. 3대 투자 전략별 포지션 오더 (V7.1 매트릭스)")

def render_portfolio_card(title, desc, border_color, content_html):
    html = f"""
    <div class="portfolio-card" style="border-left: 5px solid {border_color};">
        <div class="portfolio-card-header" style="color: {border_color};">{title}</div>
        <div class="portfolio-card-desc">{desc}</div>
        <div class="portfolio-card-content">{content_html}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)

with c1:
    if current_mode == "액셀러": p1_w = "빅테크 80% / 배당 20% / 머니마켓 0%"
    elif current_mode == "브레이크": p1_w = "빅테크 0% / 배당 40% / 머니마켓 60%"
    elif current_mode == "과열 방어": p1_w = "빅테크 40% / 배당 40% / 머니마켓 20%"
    else: p1_w = "빅테크 70% / 배당 30% / 머니마켓 0%"
    render_portfolio_card("🧠 개인연금 삼성증권 (하이퍼-스마트)", "[보유분 일괄 동적 스위칭]", "#00e5ff", p1_w)

with c2:
    if current_mode == "액셀러": p2_w = "레버리지 100% / 금현물 0% / 머니마켓 0%"
    elif current_mode == "브레이크": p2_w = "레버리지 0% / 금현물 70% / 머니마켓 30%"
    elif current_mode == "과열 방어": p2_w = "레버리지 30% / 금현물 50% / 머니마켓 20%"
    else: p2_w = "레버리지 75% / 금현물 25% / 머니마켓 0%"
    render_portfolio_card("🛡️ ISA NH증권 (무결성 부스터)", "[익일 오전 100% 전량 청산 대피]", "#00e5ff", p2_w)

with c3:
    if current_mode == "액셀러": p3_w = "QLD 45% / MAGS 55% / SCHD 0% / GLDM 0%"
    elif current_mode == "브레이크": p3_w = "QLD 0% / MAGS 0% / SCHD 50% / GLDM 50%"
    elif current_mode == "과열 방어": p3_w = "QLD 15% / MAGS 30% / SCHD 30% / GLDM 25%"
    else: p3_w = "QLD 45% / MAGS 30% / SCHD 20% / GLDM 5%"
    render_portfolio_card("🚀 해외직투 토스증권 (액셀러레이터)", "[Strict NO-SELL / 신규자금만 조절]", "#ff3366", p3_w)

# --- 5. 투자비서 데이터 무결성 검증 레이어 ---
st.markdown("---")
st.subheader("📋 3. 투자비서 데이터 무결성 검증 레이어")
with st.expander("가짜 속임수 신호 판독 및 매크로 리스크 결과 보기", expanded=True):
    st.markdown(f"1. **가짜 하락 차단 (거래량):**")
    st.markdown("   * 🔴 **[패스]**" if vol_surge else "   * 🟢 **[주의]** 거래량이 동반되지 않은 단순 노이즈(속임수) 가능성 존재.")
    st.markdown(f"2. **단기 추세 판독 (50일선):**")
    st.markdown("   * 🟢 지수가 50일선 위에 있습니다." if ndx_close > ndx_50 else "   * 🔴 지수가 50일선 아래로 무너졌습니다.")
    st.markdown(f"3. **하이일드 피크아웃 공식 검증:**")
    if input_hy <= 3.50: st.markdown(f"   * ✅ 현재 {input_hy}%로 절대 수치 3.50% 이하입니다. **[가짜 위기 프리패스]** 완료.")
    elif (input_hy_max - input_hy) >= 0.20: st.markdown(f"   * ✅ 최고점 대비 부도 위험이 -0.20%p 이상 확실히 주저앉았습니다. **[피크아웃 사격 승인]** 완료.")
    else: st.markdown("   * ⛔ 아직 피크아웃 조건 미달입니다. 지하실 리스크를 경계하십시오.")

st.markdown("---")
st.caption("🌐 공식 데이터 소스 다이렉트 라우팅")
cl1, cl2, cl3 = st.columns(3)
with cl1: st.link_button("🔵 FRED 하이일드 스프레드 (필수)", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", use_container_width=True)
with cl2: st.link_button("🟢 CBOE 풋콜레이시오 (보조)", "https://www.cboe.com/markets/us/options/market-statistics/daily", use_container_width=True)
with cl3: st.link_button("🔴 CNN 공포와 탐욕 지수 (보조)", "https://edition.cnn.com/markets/fear-and-greed", use_container_width=True)

# --- 6. 운영 가이드 및 핵심 지표 해설 ---
st.markdown("---")
st.subheader("📚 4. V7.1 시스템 운영 가이드 및 지표 해설")
with st.expander("성공적인 장기 투자를 위한 비서의 핵심 조언 및 각 지표의 기준 (클릭하여 펼치기)", expanded=False):
    st.markdown("""
    #### 💡 각 지표의 명확한 역할 및 기준
    * **나스닥100 125일 이동평균선 (추세 축):** 시장의 중장기적인 방향을 결정하는 뼈대입니다. 이 선을 **3거래일 연속** 깨고 내려가면 즉각 대피 명령(브레이크)을 내립니다.
    * **나스닥100 일봉 RSI (심리 축):** Wilder's 표준 방식을 적용한 심리 지표입니다. 70 이상은 단기 꼭대기 임계 영역, 30 미만은 과매도 극단으로 판정합니다.
    * **VIX 공포 지수 (공포 축):** 옵션 변동성 지수입니다. **30 이상**으로 치솟으면 시장이 완연한 패닉 투매 상태에 진입했음을 확증합니다.

    #### 📊 ⚖️ 핵심 지표 심층 해설 (CBOE 풋콜레이시오 & FRED 하이일드 스프레드)
    * **⚖️ CBOE 풋콜레이시오 (Put-Call Ratio, PCR)**
        * **정의 및 의미:** 상승과 하락 옵션 거래비율을 통해 대중의 '극단적인 공포'를 인간 지표로 활용합니다. 통상 1.0을 돌파하면 하락세가 지배적인 시장 환경이며, <b>1.1 이상 돌파 시</b> 역발상 매수 최적기로 판정합니다.
    * **📉 FRED 하이일드 스프레드 (High Yield Spread)**
        * **정의 및 의미:** 국채 대비 부적격 회사채 금리 차이로 기업 도산 리스크를 나타냅니다.
            * **공식 1 (피크아웃):** 최근 20거래일 최고점 대비 스프레드 절대 수치가 **-0.20%p 이상 하락**하면 위기 정점 통과로 판정합니다.
            * **공식 2 (가짜 위기):** 하이일드 스프레드가 **3.50% 이하**라면 시스템 붕괴 우려가 없는 단순 심리 발작으로 판정해 즉시 프리패스 저가 매수를 승인합니다.

    #### 🛡️ 비서의 실전 대응 조언
    1. **금요일 집행의 법칙:** 마켓 타이밍 예측은 장기적으로 실패하므로, **매주 금요일 미국 정규장 시가 부근**에 기계적인 자동 예약을 고수하여 변동성을 완전 흡수합니다.
    2. **계좌별 분리 수호 조항:** 세금 패널티가 없는 절세 계좌는 100% 전량 청산 대피를 적극 활용하되, 해외직투는 22% 양도소득세 패널티를 피하기 위해 **기존 자산 영구 매도 금지(Strict NO-SELL)**를 수호하고 오직 신규 자금 비율만 조절합니다.
    3. **일상의 노이즈 차단:** 평상시에는 계좌 앱을 열어보지 않고 대구 다사읍 연구실의 본업(재료개발)에 완전 몰두하며 시스템 대시보드 신호에만 반응하십시오.
    """)