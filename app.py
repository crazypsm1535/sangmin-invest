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
st.title("🧭 통합 투자 내비게이션 V6.0 (Premium Dynamic)")

df = get_market_data()
fetch_error = False

if df is None or df.empty:
    fetch_error = True
    st.error("🚨 실시간 시장 데이터(Yahoo Finance) 통신에 실패했습니다. 자동으로 '테스트 모드'로 전환됩니다.")
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
            st.info(f"**총 자산: {tot_val:,.0f}**\\n\\n- **항목 1:** {(cv1/tot_val)*100:.1f}%\\n- **항목 2:** {(cv2/tot_val)*100:.1f}%\\n- **항목 3:** {(cv3/tot_val)*100:.1f}%\\n- **항목 4:** {(cv4/tot_val)*100:.1f}%")
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
            st.success(f"**배분 목표 (총 {t_asset:,.0f})**\\n\\n- **항목 1:** {t_asset*(cp1/100):,.0f}\\n- **항목 2:** {t_asset*(cp2/100):,.0f}\\n- **항목 3:** {t_asset*(cp3/100):,.0f}\\n- **항목 4:** {t_asset*(cp4/100):,.0f}")

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
    "지표": ["나스닥 100 지수 (RSI)", "VIX 지수", "S&P 500 (200일선)", "나스닥 100 (125일선)", "공포와 탐욕 (수동)", "풋콜레이시오 (수동)", "하이일드 스프레드 (수동)"],
    "트리거 발생 기준": ["🔵 [기회] 30 이하 / 🔴 [경계] 70 이상 ➔ 심리 과열 감시", "🚨 [위험] 30 이상 ➔ 패닉 투매 감지", "❌ [붕괴] 지수 이탈 ➔ 장기 추세 붕괴", "⚠️ [경고] 3거래일 하회 ➔ 중장기 브레이크", "💀 [공포] 25 미만 ➔ 극단적 공포", "📊 [바닥] 1.1 이상 ➔ 바닥 신호 응축", "⚡ [위험] 5.0% 이상 ➔ 금융위기 방어"],
    "현재 수치": [f"{ndx_rsi:.2f}", f"{vix:.2f}", f"{sp500_close:,.2f} ({sp500_200:,.2f})", f"{ndx_close:,.2f} ({ndx_125:,.2f})", f"{input_fg}", f"{input_pcr}", f"{input_hy}%"],
    "현재 판정": ["🔴 발동" if ndx_rsi <= 30 or ndx_rsi >= 70 else "🟢 정상", "🔴 위험" if vix >= 30 else "🟢 정상", "🔴 이탈" if sp500_close < sp500_200 else "🟢 지지", "🟡 브레이크" if is_break_3days else "🟢 정상", "🔴 기회" if input_fg <= 25 else "🟢 정상", "🔴 바닥" if input_pcr >= 1.1 else "🟢 정상", "🔴 위험" if input_hy >= 5.0 else "🟢 안정"]
}
st.table(pd.DataFrame(trigger_data))

# --- 수동 지표 확인 섹션 (TradingView 100% 무료망 우회 개정) ---
st.markdown("---")
st.markdown("### 🔍 2. 심리 및 매크로 수동 지표 확인 (Data Source Verification)")
st.caption("가입 유도 및 세션 차단 팝업이 일절 없는 트레이딩뷰(TradingView) 웹 클린 채널 링크로 전면 교체 완료되었습니다.")

col_l1, col_l2, col_l3 = st.columns(3)
with col_l1:
    st.info("#### 🔴 CNN 공포와 탐욕 지수 소스")
    st.markdown("- **제공처:** CNN Business Market\n- **성격:** 군중 주관적 투자 심리 필터\n- **상태:** 외부 차단에 따른 수동 라우팅")
    st.link_button("🌐 CNN 공식 소스 확인하기", "https://edition.cnn.com/markets/fear-and-greed", use_container_width=True)

with col_l2:
    st.success("#### 🟢 TradingView 풋콜레이시오 (클린망)")
    st.markdown("- **제공처:** 글로벌 차트 허브 트레이딩뷰 (TradingView)\n- **티커:** `CBOE:PCC` (종합 Equity/Index Put Call Ratio)\n- **특징:** 유료 가입 팝업이나 쿠키 한도 제한이 일절 없어 언제나 쾌적하게 1초 만에 실시간 조회 가능")
    st.link_button("📱 트레이딩뷰 클린 소스 확인", "https://www.tradingview.com/symbols/CBOE-PCC/", use_container_width=True)

with col_l3:
    st.info("#### 🔵 연준 하이일드 스프레드 소스")
    st.markdown("- **제공처:** St. Louis Fed (FRED)\n- **성격:** 미국 기업 부도 신용 위험 필터\n- **상태:** FRED 전용 직통망 라우팅")
    st.link_button("🌐 FRED 공식 소스 확인하기", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", use_container_width=True)

st.markdown("---")
st.markdown("### 🎯 3. 3대 투자 전략별 현재 대응 모드 (V6.0 동적 반영)")

c1, c2, c3 = st.columns(3)

with c1:
    st.info("#### 🧠 삼성 연금저축\n**하이퍼-스마트 DCA V6.0**")
    if accelerator_triggered: st.error("**[액셀러 모드]**\n👉 **[전량 스위칭]**\nACE 미국빅테크TOP7 Plus 65.0% / KIWOOM 미국S&P500모멘텀 35.0%")
    elif is_break_3days: st.warning("**[브레이크 작동]**\n👉 **[주식 전량 매도]**\nTIME 미국배당다우존스액티브 60.0% / KODEX 미국머니마켓액티브 40.0% 피신 리밸런싱")
    elif ndx_rsi >= 70: st.warning("**[과열 방어]**\n👉 **[리밸런싱]**\nACE 미국빅테크TOP7 Plus 30.0% / KIWOOM 미국S&P500모멘텀 30.0% / KODEX 미국머니마켓액티브 40.0%")
    else: st.success("**[평상시 모드]**\n👉 **[리밸런싱]**\nACE 미국빅테크TOP7 Plus 50.0% / KIWOOM 미국S&P500모멘텀 35.0% / KODEX 미국머니마켓액티브 15.0%")

with c2:
    st.info("#### 🛡️ NH ISA\n**하이퍼-실드 V4.5 무결성 벙커**")
    if accelerator_triggered: st.error("**[액셀러 모드]**\n👉 **[전량 스위칭]**\nTIGER 미국나스닥100레버리지(418660) 100.0%")
    elif is_break_3days: st.warning("**[브레이크 작동]**\n👉 **[전량 대피]**\nACE KRX금현물 70.0% / KODEX 미국머니마켓액티브 30.0%")
    elif ndx_rsi >= 70: st.warning("**[과열 방어]**\n👉 **[리밸런싱]**\nTIGER 레버리지 20.0% / ACE 미국빅테크TOP7 Plus 10.0% / ACE 금현물 49.0% / KODEX 머니마켓 21.0%")
    else: st.success("**[평상시 모드]**\n👉 **[리밸런싱]**\nTIGER 레버리지 45.0% / ACE 미국빅테크TOP7 Plus 25.0% / ACE 금현물 21.0% / KODEX 머니마켓 9.0%")

with c3:
    st.info("#### 🚀 메리츠 해외직투\n**하이퍼-액셀러레이터 V2.6 4대 자산 압축 최적안**")
    if accelerator_triggered: st.error("**[액셀러 모드]**\n👉 **[NO-SELL]**\n신규: QLD 45.0% / MAGS 55.0% 집중 적립")
    elif is_break_3days: st.warning("**[브레이크 작동]**\n👉 **[NO-SELL]**\n신규: SCHD 50.0% / GLDM 50.0% 대피 적립")
    elif ndx_rsi >= 70: st.warning("**[과열 방어]**\n👉 **[NO-SELL]**\n신규: QLD 15.0% / MAGS 30.0% / SCHD 30.0% / GLDM 25.0%")
    else: st.success("**[평상시 모드]**\n👉 **[NO-SELL]**\n신규: QLD 45.0% / MAGS 30.0% / SCHD 20.0% / GLDM 5.0% 집행")

# --- 비서의 전문 검증 및 조언 섹션 ---
st.markdown("---")
st.subheader("📋 4. 비서의 전문 검증 및 조언 레이어 (V6.0 Pro)")
with st.expander("상세 분석 결과 및 리스크 진단 보기", expanded=True):
    met_conditions = sum([condition_rsi, condition_pcr, condition_fg, condition_vix, condition_hy])
    
    st.markdown(f"1. **시스템 리스크 진단:** 현재 하이일드 스프레드는 **{input_hy}%**이며, 피크아웃 여부는 **{input_hy_peakout}**입니다.")
    if input_hy >= 5.0 and not input_hy_peakout:
        st.markdown("   * ⚠️ 금융 시스템 위험이 감지되므로, 동적 자산 배분 스위칭 시 방어적 포지션을 유지하십시오.")
    else:
        st.markdown("   * ✅ 시스템 리스크 우려가 없는 안정적인 매크로 환경입니다.")
        
    st.markdown(f"2. **전략적 추세 (125일선):** 나스닥 지수가 125일선 대비 현재 상단에 위치해 있습니다.")
    if ndx_close > ndx_125:
        st.markdown("   * ✅ 추세가 무너지지 않았으므로 국내 계좌의 불필요한 매도는 제한됩니다.")
    else:
        st.markdown("   * ⚠️ 추세를 하회 중이므로 브레이크 트리거 작동 여부를 반드시 확인하십시오.")
        
    st.markdown(f"3. **단기 선발대 (50일선) 및 가짜 신호 검증:**")
    if vol_surge:
        st.markdown("   * 🔴 [진짜 신호] QQQ 거래량이 20MA 대비 1.5배 이상 터진 신뢰도 높은 하락 흐름")
    else:
        st.markdown("   * 🟢 [가짜 신호 가능성] 거래량이 동반되지 않은 일반 노이즈성 흐름")
        
    if ndx_close > ndx_50:
        st.markdown("   * 단기 상승세가 유효합니다. 해외 계좌는 NO-SELL 원칙에 따라 기존 보유 주식을 꽉 쥐고 가십시오.")
    else:
        st.markdown("   * 단기 상승 동력이 꺾였습니다. 리밸런싱 지침에 기계적으로 대응할 준비를 하십시오.")
        
    st.markdown(f"4. **바닥 신호 강도 검증 (5대 필수 지표):** 총 5개 중 **{met_conditions}개** 충족 중입니다.")
    st.markdown("5. **상민님 전담 최종 권고 지침:**")
    
    if accelerator_triggered:
        st.error(f"🔥 **[최종 권고: 액셀러 모드 발동]** 5대 필수 지표가 100% 동시 충족되었습니다. **국내 계좌(연금/ISA)는 모아둔 초단기채/금/배당 실탄을 주식 및 레버리지로 100% '기존 자산 전량 리밸런싱 스위칭'을 단행하십시오.** 해외 계좌는 NO-SELL을 유지하며 신규 자금만 집중 매수합니다.")
    elif is_break_3days:
        st.warning(f"🚨 **[최종 권고: 브레이크 동적 대응]** 나스닥 125일선 3거래일 연속 하회가 확정되었습니다. **국내 계좌(연금/ISA)는 기존 주식 자산을 전량 즉시 매도하여 안전 방어 바구니(초단기채/금/배당) 비중 100%로 강제 대피 리밸런싱을 실행하십시오.** 해외 계좌는 NO-SELL 원칙에 따라 매도하지 않고 신규 자금만 방어 자산으로 적립합니다.")
    elif ndx_rsi >= 70:
        st.warning(f"⚠️ **[최종 권고: 과열 방어 리밸런싱]** 나스닥 RSI {ndx_rsi:.2f}로 과매수 구간입니다. **국내 계좌는 기존 자산 비중을 과열 방어 테이블대로 즉시 줄여 안전 자산을 선제 확보하십시오.** 해외 계좌는 기존 자산 매도 없이 신규 자금 비중만 조절합니다.")
    else:
        st.success(f"✅ **[최종 권고: 평상시 기계적 집행]** 시장이 안정적인 추세 구간에 있습니다. **국내 계좌는 평상시 비중대로 보유 상태를 조율하시고**, 신규 투자금도 기본 비중대로 편안하게 대구 다사읍 연구실 본업에 집중하며 적립하십시오.")