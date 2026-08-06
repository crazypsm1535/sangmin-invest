import streamlit as st
import yfinance as yf
import pandas as pd
import warnings

# 불필요한 터미널 경고 메시지 숨김
warnings.filterwarnings('ignore')

# --- 1. 페이지 설정 및 다크 그레이 디자인 ---
st.set_page_config(page_title="통합 내비게이션 V8.1 (Ultimate Dark)", layout="wide")

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

# 지표 연산 로직
def calculate_rsi(series, period=14):
    delta = series.diff()
    up, down = delta.copy(), delta.copy()
    up[up < 0] = 0
    down[down > 0] = 0
    _gain = up.ewm(com=(period - 1), min_periods=period).mean()
    _loss = down.abs().ewm(com=(period - 1), min_periods=period).mean()
    RS = _gain / _loss
    return 100 - (100 / (1 + RS))

# --- 데이터 통신 엔진 (캐시 및 에러 헨들링 강화) ---
@st.cache_data(ttl=30)
def get_market_data():
    try:
        tickers = ["QLD", "^NDX", "^GSPC", "^VIX", "QQQ"]
        
        # 순정 yfinance 다운로드 사용 (커스텀 세션 억제, 최대 10초 타임아웃)
        data = yf.download(tickers, period="1y", progress=False, group_by="ticker", timeout=10)
        
        if data.empty:
            return None

        df = pd.DataFrame(index=data.index)
        df['QLD_Close'] = data['QLD']['Close']
        df['NDX_Close'] = data['^NDX']['Close']
        df['SP500_Close'] = data['^GSPC']['Close']
        df['VIX_Close'] = data['^VIX']['Close']
        df['Volume'] = data['QQQ']['Volume']
        
        df = df.ffill().dropna()
        df['QLD_200SMA'] = df['QLD_Close'].rolling(window=200).mean()
        df['NDX_50EMA'] = df['NDX_Close'].ewm(span=50, adjust=False).mean()
        df['SP500_200EMA'] = df['SP500_Close'].ewm(span=200, adjust=False).mean()
        df['NDX_RSI'] = calculate_rsi(df['NDX_Close'])
        df['Vol_20MA'] = df['Volume'].rolling(window=20).mean()
        
        return df.dropna()
    except Exception:
        return None

# --- 2. 사이드바 (지표 입력 및 수동 조작계) ---
st.sidebar.title("🧪 매크로 지표 입력 및 시뮬레이터")
sim_mode = st.sidebar.checkbox("🚨 인위적 테스트 모드 (수동 조작)", value=False)

if sim_mode:
    st.sidebar.subheader("🕹️ 차트 데이터 강제 조작")
    sim_ndx_rsi = st.sidebar.slider("나스닥100 일봉 RSI", 0.0, 100.0, 25.0, 0.1)
    sim_vix = st.sidebar.slider("VIX 공포 지수", 0.0, 80.0, 32.0, 0.1)
    sim_is_break = st.sidebar.checkbox("QLD 200일선 3일 연속 하회 (브레이크 발동)", value=False)
else:
    sim_ndx_rsi, sim_vix, sim_is_break = None, None, None

st.sidebar.markdown("---")
st.sidebar.subheader("📉 필수 채권 지표 입력 (FRED)")
temp_hy = st.sidebar.number_input("1. 현재 하이일드 스프레드 (%)", 0.0, 20.0, 2.71, 0.01, key="hy_val")
temp_hy_max = st.sidebar.number_input("2. 최근 20일 내 최고점 수치 (%)", 0.0, 20.0, 4.26, 0.01, key="hy_max_val")

st.sidebar.markdown("---")
st.sidebar.subheader("📊 보조 감시 지표 (메인 신호 제외됨)")
temp_breadth = st.sidebar.number_input("시장 폭 (S&P500 200일선 상회 비율 %)", 0, 100, 52, key="br_val")
temp_fg = st.sidebar.number_input("CNN 공포와 탐욕 지수", 0, 100, 47, key="fg_val")
temp_pcr = st.sidebar.number_input("CBOE 풋콜레이시오", 0.0, 3.0, 0.93, 0.01, key="pcr_val")

st.sidebar.markdown("---")
apply_macro_toggle = st.sidebar.toggle("🚀 위 수치들을 시스템에 일괄 적용 (ON/OFF)", value=False)

if apply_macro_toggle:
    st.sidebar.success("✅ [적용됨] 입력하신 수치로 대시보드가 계산됩니다.")
    input_hy, input_hy_max = temp_hy, temp_hy_max
    input_breadth, input_fg, input_pcr = temp_breadth, temp_fg, temp_pcr
else:
    st.sidebar.warning("⏸️ [대기 중] 스위치를 켜면 메인 화면에 적용됩니다.")
    input_hy, input_hy_max = 2.71, 4.26
    input_breadth, input_fg, input_pcr = 52, 47, 0.93

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

# --- 3. 메인 화면 렌더링 (60초 자동 갱신 데코레이터 적용) ---
@st.fragment(run_every=60)
def render_main_dashboard():
    st.title("🧭 HYPER-INVEST 통합 내비게이션 V8.1")
    
    df = get_market_data()
    fetch_error = False

    if df is None or df.empty:
        fetch_error = True
        st.error("🚨 실시간 시장 데이터 통신에 실패했습니다. 수동 '테스트 모드' 데이터를 표시합니다.")
        real_ndx_rsi, real_vix = 50.0, 20.0
        vol_surge = False
        real_is_break_3days = False
    else:
        current = df.iloc[-1]
        prev_3days = df.iloc[-3:]
        real_ndx_rsi = round(float(current['NDX_RSI']), 2)
        real_vix = round(float(current['VIX_Close']), 2)
        vol_surge = bool(current['Volume'] > current['Vol_20MA'] * 1.5)
        real_is_break_3days = bool((prev_3days['QLD_Close'] < prev_3days['QLD_200SMA']).all())
    
    # 시뮬레이션 모드 덮어쓰기 로직
    active_rsi = sim_ndx_rsi if sim_mode else real_ndx_rsi
    active_vix = sim_vix if sim_mode else real_vix
    active_break = sim_is_break if sim_mode else real_is_break_3days

    # 판독 엔진
    hy_approved = (input_hy <= 3.50) or (input_hy <= (input_hy_max - 0.20))
    accel_triggered = (active_rsi < 30) and (active_vix >= 30)
    return_triggered = (active_rsi >= 40) and (active_vix < 25)

    if active_break:
        current_mode = "브레이크"
    elif accel_triggered and hy_approved:
        current_mode = "엑셀러"
    else:
        current_mode = "평상시"

    if sim_mode and not fetch_error:
        st.error("⚠️ 현재 [인위적 테스트 모드]가 활성화 중입니다. 실제 시장 데이터가 아닙니다.")
    elif not fetch_error:
        st.markdown("<p style='font-size:13px; margin-top:-8px; color:#a1a1aa;'>본업에 집중하십시오. 60초마다 실시간으로 동기화 중입니다.</p>", unsafe_allow_html=True)

    # 상단 4구역 지표 요약 및 버튼 복구
    col1, col2, col3, col4 = st.columns(4)
    card_css = "background-color:#161619; border:1px solid #3a3a42; border-left:4px solid #00e5ff; border-radius:4px; padding:10px 15px; display:flex; justify-content:space-between; align-items:center; height:45px;"

    with col1: 
        st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">QLD 200일선 추세</span><span style="font-size:16px; font-weight:bold; color:{"#ff4500" if active_break else "#00ff66"};">{"붕괴(Break)" if active_break else "정상(Pass)"}</span></div>', unsafe_allow_html=True)
        st.link_button("🔍 수동 확인 (Yahoo)", "https://finance.yahoo.com/quote/QLD/chart", use_container_width=True)
    with col2: 
        st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">나스닥100 RSI</span><span style="font-size:16px; font-weight:bold; color:{"#ff4500" if active_rsi >= 70 else ("#00e5ff" if active_rsi <=30 else "#ffffff")};">{active_rsi:.2f}</span></div>', unsafe_allow_html=True)
        st.link_button("🔍 수동 확인 (Yahoo)", "https://finance.yahoo.com/quote/%5ENDX/chart", use_container_width=True)
    with col3: 
        st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">VIX 지수</span><span style="font-size:16px; font-weight:bold; color:{"#00e5ff" if active_vix >= 30 else "#ffffff"};">{active_vix:.2f}</span></div>', unsafe_allow_html=True)
        st.link_button("🔍 수동 확인 (Yahoo)", "https://finance.yahoo.com/quote/%5EVIX/chart", use_container_width=True)
    with col4: 
        hy_status = "✅ 매수 승인(Pass)" if hy_approved else "⛔ 대기(Wait)"
        st.markdown(f'<div style="{card_css}"><span style="font-size:13px; color:#a1a1aa;">하이일드 판정</span><span style="font-size:14px; font-weight:bold; color:#00ff66;">{hy_status}</span></div>', unsafe_allow_html=True)
        st.link_button("🔍 수동 확인 (FRED)", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", use_container_width=True)

    # 1. 시스템 모드 액션
    st.markdown("## 🎯 1. V8.1 시스템 확정 모드 (Action Required)")
    if current_mode == "브레이크":
        st.warning("### 🟡 [브레이크 모드] 전량 벙커 대피 (추세 붕괴 최우선 발동)")
        st.markdown('<div class="context-box">🔍 <b>실시간 지표 분석:</b><br>• <b>추세 붕괴 확정:</b> QLD 종가가 200일선을 <b>3거래일 연속 하회</b>했습니다.<br>💡 <b>결론:</b> 위험자산을 100% 매도하고 방어 자산(0107F0/SCHD)으로 대피하십시오.</div>', unsafe_allow_html=True)
    elif current_mode == "엑셀러":
        st.error("### 🔵 [엑셀러 모드] 7:3 기동 타격 집행 (대바닥)")
        st.markdown(f'<div class="context-box">🔍 <b>실시간 지표 분석:</b><br>• <b>RSI ({active_rsi:.2f}) & VIX ({active_vix:.2f}):</b> 과매도 및 패닉 투매 확증.<br>💡 <b>결론:</b> 시스템 붕괴 위험이 없는 진바닥입니다. 7:3 법칙으로 매수하십시오.</div>', unsafe_allow_html=True)
    else:
        st.success("### 🟢 [평상시 모드] 기본 포메이션 분산 적립 (우상향)")
        st.markdown('<div class="context-box">🔍 <b>실시간 지표 분석:</b><br>• <b>추세 정상:</b> QLD가 200일선 상단에 위치.<br>💡 <b>결론:</b> 기본 포메이션 비중을 고수하며 금요일 오전 기계적 매수를 진행하십시오.</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🔍 엑셀러 모드 탈출(복귀) 판독기")
    if return_triggered: 
        st.markdown("   * ✅ **[복귀 승인]** RSI 40 이상 및 VIX 25 미만을 동시 충족했습니다. 다가오는 금요일 평상시 모드로 정식 복귀합니다.")
    else: 
        st.markdown(f"   * ⛔ **[조건 미달]** 현재 RSI({active_rsi:.2f})와 VIX({active_vix:.2f})가 복귀 기준치를 동시 충족하지 못했습니다.")

    # 2. 계좌별 포지션 오더
    st.markdown("---")
    st.markdown("### 📊 2. 3대 투자 전략별 실전 포지션 오더 (V8.1 매트릭스)")
    c1, c2, c3 = st.columns(3)
    with c1:
        p1_w = "KIWOOM 배당&AI (0107F0) 100% 대피" if current_mode == "브레이크" else "ACE 미국빅테크TOP7 Plus 100%" if current_mode == "엑셀러" else "<b>ACE 빅테크7 12주 / KIWOOM 배당&AI 8주</b>"
        st.markdown(f'<div class="portfolio-card" style="border-left: 5px solid #00e5ff;"><div class="portfolio-card-header" style="color: #00e5ff;">🧠 개인연금 (삼성)</div><div class="portfolio-card-desc">[동적 스위칭]</div><div class="portfolio-card-content">{p1_w}</div></div>', unsafe_allow_html=True)
    with c2:
        p2_w = "KIWOOM 배당&AI (0107F0) 100% 대피" if current_mode == "브레이크" else "나스닥100레버 75% / 빅테크7레버 25%" if current_mode == "엑셀러" else "<b>나스닥2배 4주 / 빅테크2배 2주 / KIWOOM 배당&AI 12주</b>"
        st.markdown(f'<div class="portfolio-card" style="border-left: 5px solid #00e5ff;"><div class="portfolio-card-header" style="color: #00e5ff;">🛡️ ISA (NH)</div><div class="portfolio-card-desc">[전량 청산형]</div><div class="portfolio-card-content">{p2_w}</div></div>', unsafe_allow_html=True)
    with c3:
        p3_w = "SCHD 100% 청산 대피" if current_mode == "브레이크" else "QLD 100% 스위칭" if current_mode == "엑셀러" else "<b>QLD 80% / SCHD 20%</b>"
        st.markdown(f'<div class="portfolio-card" style="border-left: 5px solid #ff3366;"><div class="portfolio-card-header" style="color: #ff3366;">🚀 해외직투 (토스)</div><div class="portfolio-card-desc">[대피형]</div><div class="portfolio-card-content">{p3_w}</div></div>', unsafe_allow_html=True)

    # 3. 무결성 검증 레이어 (UI 컬럼 분할 및 수동 확인 버튼 100% 복구)
    st.markdown("---")
    st.subheader("📋 3. 투자비서 데이터 무결성 검증 레이어")
    with st.expander("가짜 속임수 신호 판독 및 매크로 리스크 결과 보기", expanded=True):
        st.markdown("1. **가짜 하락 차단 (거래량):**")
        v_col1, v_col2 = st.columns([5, 1])
        with v_col1:
            st.markdown("   * 🔴 **[패스]** 거래량 폭발 조건 충족." if vol_surge else "   * 🟢 **[주의]** 거래량이 동반되지 않은 노이즈 가능성.")
        with v_col2:
            st.link_button("🔍 수동 확인", "https://finance.yahoo.com/quote/QQQ/history", use_container_width=True)
            
        st.markdown("2. **시장 폭 내부 체력 스캐닝 (Breadth):**")
        b_col1, b_col2 = st.columns([5, 1])
        with b_col1:
            st.markdown(f"   * 🟢 현재 {input_breadth}%로 양호합니다." if input_breadth >= 50 else f"   * 🔴 현재 {input_breadth}%로 50%를 하회합니다. (소수 빅테크 쏠림 착시 경계)")
        with b_col2:
            st.link_button("🔍 수동 확인", "https://stockcharts.com/freecharts/", use_container_width=True)
            
        st.markdown("3. **CBOE 풋콜레이시오 (PCR) 극단 공포 판독:**")
        p_col1, p_col2 = st.columns([5, 1])
        with p_col1:
            st.markdown(f"   * 🔴 극단 공포 도달 ({input_pcr}). 역발상 매수 최적기 가능성." if input_pcr >= 1.1 else f"   * 🟢 현재 {input_pcr}로 안정 수준.")
        with p_col2:
            st.link_button("🔍 수동 확인", "https://www.cboe.com/markets/us/options/market-statistics/daily", use_container_width=True)
            
        st.markdown("4. **하이일드 피크아웃 공식 검증:**")
        h_col1, h_col2 = st.columns([5, 1])
        with h_col1:
            if input_hy <= 3.50: 
                st.markdown(f"   * ✅ 현재 {input_hy}% (3.50% 이하). **[가짜 위기 프리패스]** 완료.")
            elif (input_hy_max - input_hy) >= 0.20: 
                st.markdown(f"   * ✅ 최고점 대비 부도 위험이 -0.20%p 이상 하락. **[피크아웃 사격 승인]** 완료.")
            else: 
                st.markdown("   * ⛔ 피크아웃 조건 미달. 지하실 리스크를 경계하십시오.")
        with h_col2:
            st.link_button("🔍 수동 확인", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", use_container_width=True)

    # 4. 공식 데이터 소스 다이렉트 라우팅 (V7.2 푸터 복구)
    st.markdown("---")
    st.caption("🌐 공식 데이터 소스 다이렉트 라우팅")
    cl1, cl2, cl3 = st.columns(3)
    with cl1: st.link_button("🔵 FRED 하이일드 스프레드 (필수)", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", use_container_width=True)
    with cl2: st.link_button("🟢 CBOE 풋콜레이시오 (보조)", "https://www.cboe.com/markets/us/options/market-statistics/daily", use_container_width=True)
    with cl3: st.link_button("🔴 CNN 공포와 탐욕 지수 (보조)", "https://edition.cnn.com/markets/fear-and-greed", use_container_width=True)

    # 5. 운영 가이드
    st.markdown("---")
    st.subheader("📚 4. V8.1 시스템 운영 가이드 및 지표 해설")
    with st.expander("성공적인 장기 투자를 위한 비서의 핵심 조언 및 각 지표의 기준 (클릭하여 펼치기)", expanded=False):
        st.markdown("""
        #### 💡 핵심 지표 기준 (V8.1 단일화)
        * **QLD 200일 이동평균선:** 중장기 방향을 결정하는 단일 뼈대. 3거래일 연속 하회 시 브레이크.
        * **나스닥100 RSI:** 30 미만은 과매도 극단.
        * **VIX 공포 지수:** 30 이상으로 치솟으면 패닉 투매 상태.
        * **CBOE 풋콜레이시오 (PCR):** 1.1 이상 돌파 시 역발상 매수 최적기.
        * **시장 폭 (Breadth):** 200일선 상회 종목 비율 50% 하회 시 착시 장세 경계.
        * **엑셀러 복귀 조건:** RSI 40 이상 및 VIX 25 미만 동시 충족 (AND 연산).
        """)

# 함수 실행 (여기서 화면이 렌더링되며, 60초마다 이 함수 안쪽만 재실행됨)
render_main_dashboard()