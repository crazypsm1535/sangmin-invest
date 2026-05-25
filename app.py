import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(page_title="투자 내비게이션 V3.0 (Dynamic)", layout="wide")

st.markdown("""
    <style>
    .stMetric { padding: 10px; border-radius: 10px; border: 1px solid rgba(128, 128, 128, 0.2); }
    h1 { font-weight: 800; }
    h2 { border-left: 5px solid #1e293b; padding-left: 10px; margin-top: 30px; }
    .stAlert { border-left: 5px solid #334155 !important; }
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

ndx_close, ndx_125, ndx_50 = round(current['NDX_Close'], 2), round(current['NDX_125EMA'], 2), round(current['NDX_50EMA'], 2)
ndx_rsi, vix = round(current['NDX_RSI'], 2), round(current['VIX_Close'], 2)
sp500_close, sp500_200 = round(current['SP500_Close'], 2), round(current['SP500_200EMA'], 2)
vol_surge = current['Volume'] > current['Vol_20MA'] * 1.5
is_break_3days = (prev_3days['NDX_Close'] < prev_3days['NDX_125EMA']).all() and (ndx_close < ndx_125)

# --- 3. 사이드바 (지표 입력 및 계산기 탑재) ---
st.sidebar.title("🛠️ 지표 수동 입력")
input_fg = st.sidebar.number_input("1. 공포와 탐욕 지수 (0~100)", 0, 100, 50)
input_pcr = st.sidebar.number_input("2. 풋콜레이시오 (PCR)", 0.0, 3.0, 0.9, 0.01)
input_hy = st.sidebar.number_input("3. 하이일드 스프레드 (%)", 0.0, 20.0, 4.0, 0.1)
input_hy_peakout = st.sidebar.checkbox("하이일드 스프레드 하락 전환(Peak-out) 확인됨", value=True)

# 바닥 확인 5대 필수 지표 연동 로직
condition_rsi = ndx_rsi <= 30
condition_pcr = input_pcr >= 1.1
condition_fg = input_fg <= 25
condition_vix = vix >= 30
condition_hy = input_hy_peakout  # 하이일드 스프레드 피크아웃 여부

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
st.markdown("본업에 집중하십시오. 국내 절세 계좌의 보유분 전량 스위칭 로직이 동기화된 코드입니다.")
st.markdown("---")

# 요약 카드
rsi_status = "-과열 (경계)" if ndx_rsi >= 70 else ("-공포 (기회)" if ndx_rsi <= 30 else "정상 구간")
vix_status = "-위험 구간" if vix >= 30 else "안정 구간"
fg_status = "-기회 포착" if input_fg <= 25 else "정상 구간"
hy_status = "-위험 감지" if input_hy >= 5.0 else "안정 구간"

col1, col2, col3, col4 = st.columns(4)
col1.metric("나스닥 RSI", f"{ndx_rsi}", rsi_status)
col2.metric("VIX 지수", f"{vix}", vix_status)
col3.metric("공포와 탐욕", f"{input_fg}", fg_status)
col4.metric("HY 스프레드", f"{input_hy}%", hy_status)

st.markdown("### 📊 2. 메인 감시 지표 (Primary Triggers)")

trigger_data = {
    "지표": ["나스닥 100 지수 (RSI)", "VIX 지수", "S&P 500 (200일선)", "나스닥 100 (125일선)", "공포와 탐욕 (수동)", "풋콜레이시오 (수동)", "하이일드 스프레드 (수동)"],
    "트리거 발생 기준": ["30 이하 / 70 이상", "30 이상", "지수 이탈", "3거래일 연속 하회", "25 미만", "1.1 이상", "5.0% 이상 또는 피크아웃 검증"],
    "현재 수치 / 상태": [
        f"{ndx_rsi}", f"{vix}", f"{sp500_close:,.2f} (기준: {sp500_200:,.2f})", f"{ndx_close:,.2f} (기준: {ndx_125:,.2f})", 
        f"{input_fg}", f"{input_pcr}", f"{input_hy}% (Peak-out: {input_hy_peakout})"
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
st.table(pd.DataFrame(trigger_data))

st.caption("※ 아래 버튼을 클릭하여 수치를 확인한 후 왼쪽 사이드바에 입력하십시오.")
col_btn1, col_btn2, col_btn3 = st.columns(3)
with col_btn1: st.link_button("🔗 CNN 공포와 탐욕 지수 확인", "https://edition.cnn.com/markets/fear-and-greed", use_container_width=True)
with col_btn2: st.link_button("🔗 CBOE 풋콜레이시오 (PCR) 확인", "https://www.cboe.com/us/options/market_statistics/", use_container_width=True)
with col_btn3: st.link_button("🔗 연준 하이일드 스프레드 확인", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", use_container_width=True)

st.markdown("---")

# 3대 전략 섹션 (V6.0 리밸런싱 로직 완벽 반영)
st.markdown("### 🎯 3대 투자 전략별 현재 대응 모드 (V6.0 하이브리드 동적 반영)")
c1, c2, c3 = st.columns(3)

with c1:
    st.info("#### 🛡️ NH ISA\n**하이퍼-실드 V4.5 (Dynamic Enhanced)**")
    if accelerator_triggered: 
        st.error("**[액셀러 모드]**\n5대 바닥 지표 전원 충족 완료\n\n👉 **[기존 보유분 전량 스위칭]**\n나스닥2x 레버리지 100% 올인")
    elif is_break_3days: 
        st.warning("**[브레이크 작동]**\n나스닥 125일선 3일 하회 확정\n\n👉 **[기존 보유분 전량 매도 대피]**\n미국30년국채 50% / KRX금현물 50%")
    elif ndx_rsi >= 70: 
        st.warning("**[과열 방어 모드]**\n나스닥 RSI 70 이상 과매수\n\n👉 **[기존 보유분 일괄 리밸런싱]**\n나스닥2x 20% / 모멘텀 10% / 국채 35% / 금 35%")
    else: 
        st.success("**[평상시 모드]**\n안정적 추세 추종 구간\n\n👉 **[기존 보유분 일괄 리밸런싱]**\n나스닥2x 45% / 모멘텀 25% / 국채 15% / 금 15%")

with c2:
    st.info("#### 🚀 메리츠 해외직투\n**하이퍼-액셀러레이터 V1.3 (Strict NO-SELL)**")
    if accelerator_triggered: 
        st.error("**[액셀러 모드]**\n5대 바닥 지표 충족 완료\n\n👉 **[Strict NO-SELL 원칙]**\n기존 보유분 매도 금지, 신규 자금만 MAGS 50% / MGK 50% 몰빵 적립")
    elif is_break_3days: 
        st.warning("**[브레이크 작동]**\n나스닥 125일선 3일 하회 확정\n\n👉 **[Strict NO-SELL 원칙]**\n기존 보유분 매도 금지, 신규 자금만 TLT 50% / GLDM 50% 대피 적립")
    elif ndx_rsi >= 70: 
        st.warning("**[과열 방어 모드]**\n나스닥 RSI 70 이상 과매수\n\n👉 **[Strict NO-SELL 원칙]**\n기존 보유분 매도 금지, 신규 자금 비중만 MAGS 30% / MGK 30% / TLT 20% / GLDM 20% 집행")
    else: 
        st.success("**[평상시 모드]**\n안정적 추세 추종 구간\n\n👉 **[Strict NO-SELL 원칙]**\n기존 보유분 유지, 신규 자금만 MAGS 40% / MGK 40% / TLT 10% / GLDM 10% 집행")

with c3:
    st.info("#### 🧠 삼성 연금저축\n**하이퍼-스마트 DCA (Dynamic V6.0)**")
    if accelerator_triggered: 
        st.error("**[액셀러 모드]**\n5대 바닥 지표 전원 충족 완료\n\n👉 **[기존 보유분 전량 스위칭]**\n빅테크TOP7 62.5% / 모멘텀 37.5%")
    elif is_break_3days: 
        st.warning("**[브레이크 작동]**\n나스닥 125일선 3일 하회 확정\n\n👉 **[기존 보유분 주식 전량 매도]**\nS&P500모멘텀 35% / 동일가중 65% 피신 리밸런싱")
    elif ndx_rsi >= 70: 
        st.warning("**[과열 방어 모드]**\n나스닥 RSI 70 이상 과매수\n\n👉 **[기존 보유분 일괄 리밸런싱]**\n빅테크TOP7 37.5% / 모멘텀 25% / 동일가중 37.5%")
    else: 
        st.success("**[평상시 모드]**\n안정적 추세 추종 구간\n\n👉 **[기존 보유분 일괄 리밸런싱]**\n빅테크TOP7 55% / 모멘텀 30% / 동일가중 15%")

st.markdown("---")

# [비서의 조언 요약 박스 V3.0]
st.subheader("📋 비서의 전문 검증 및 조언 레이어 (V3.0 Pro)")
with st.expander("상세 분석 결과 및 리스크 진단 보기", expanded=True):
    # 5대 지표 충족 개수 카운트
    met_conditions = sum([condition_rsi, condition_pcr, condition_fg, condition_vix, condition_hy])
    
    st.markdown(f"""
    1. **시스템 리스크 진단:** 현재 하이일드 스프레드는 **{input_hy}%**이며, 피크아웃 여부는 **{input_hy_peakout}**입니다. 
       * {'⚠️ 금융 시스템 위험이 감지되므로, 동적 자산 배분 스위칭 시 방어적 포지션을 유지하십시오.' if input_hy >= 5.0 and not input_hy_peakout else '✅ 시스템 리스크 우려가 없는 안정적인 매크로 환경입니다.'}
    2. **전략적 추세 (125일선):** 나스닥 지수가 125일선 대비 **{'위'}**에 위치해 있습니다. 
       * {'추세가 무너지지 않았으므로 국내 계좌의 불필요한 매도는 제한됩니다.' if ndx_close > ndx_125 else '⚠️ 추세를 하회 중이므로 브레이크 트리거 작동 여부를 반드시 확인하십시오.'}
    3. **단기 선발대 (50일선) 및 가짜 신호 검증:** 지수가 50일선({ndx_50:,.2f}) **{'위에 있습니다.' if ndx_close > ndx_50 else '아래에 있습니다.'}** * QQQ 거래량 폭발 여부: **{'🔴 [진짜 신호] 거래량이 20MA 대비 1.5배 이상 터진 신뢰도 높은 하락 흐름' if vol_surge else '🟢 [가짜 신호 가능성] 거래량이 동반되지 않은 일반 노이즈성 흐름'}**
       * 단기 선발대 의견: {'지수가 50일선 위에 있으므로 단기 상승세가 유효합니다. 해외 계좌는 NO-SELL 원칙에 따라 기존 보유 주식을 꽉 쥐고 가십시오.' if ndx_close > ndx_50 else '단기 상승 동력이 꺾였습니다. 리밸런싱 지침에 기계적으로 대응할 준비를 하십시오.'}
    4. **바닥 신호 강도 검증 (5대 필수 지표):** 총 5개 중 **{met_conditions}개** 충족 중입니다.
    5. **상민님 전담 최종 권고 지침:** """)
    
    if accelerator_triggered:
        st.error(f"🔥 **[최종 권고: 액셀러 모드 발동]** 5대 필수 지표가 100% 동시 충족되었습니다. **국내 계좌(연금/ISA)는 모아둔 채권/금 실탄을 주식 및 레버리지로 100% '기존 자산 전량 리밸런싱 스위칭'을 단행하십시오.** 해외 계좌는 NO-SELL을 유지하며 신규 자금만 집중 매수합니다.")
    elif is_break_3days:
        st.warning(f"🚨 **[최종 권고: 브레이크 동적 대응]** 나스닥 125일선 3거래일 연속 하회가 확정되었습니다. **국내 계좌(연금/ISA)는 기존 주식 자산을 전량 즉시 매도하여 안전 자산(국채/금/동일가중) 비중 100%로 강제 대피 리밸런싱을 실행하십시오.** 해외 계좌는 NO-SELL 원칙에 따라 매도하지 않고 신규 자금만 안전자산으로 적립합니다.")
    elif ndx_rsi >= 70:
        st.warning(f"⚠️ **[최종 권고: 과열 방어 리밸런싱]** 나스닥 RSI {ndx_rsi}로 과매수 구간입니다. **국내 계좌는 기존 자산 비중을 과열 방어 테이블대로 즉시 줄여 현금을 선제 확보하십시오.** 해외 계좌는 기존 자산 매도 없이 신규 자금 비중만 조절합니다.")
    else:
        st.success(f"✅ **[최종 권고: 평상시 기계적 집행]** 시장이 안정적인 추세 구간에 있습니다. **국내 계좌는 평상시 비중대로 보유 상태를 조율하시고**, 신규 투자금도 기본 비중대로 편안하게 본업에 집중하며 적립하십시오.")

st.markdown("---")

# 하단 표: 통합 4단계 대응 시스템
st.subheader("⚙️ 통합 4단계 대응 시스템 및 트리거 정의")

system_df = pd.DataFrame({
    "모드": ["평상시", "과열 방어", "브레이크", "액셀러"],
    "트리거 조건 (Trigger Condition)": [
        "나스닥 125일선 상단 AND RSI 40~69",
        "나스닥 RSI 70 이상 (과매수 구간)",
        "나스닥 125일선 3일 연속 종가 하회",
        "★ 5대 필수 바닥 지표 전원 동시 충족 (RSI 30이하 + PCR 1.1이상 + 공탐 25미만 + VIX 30이상 + HY 스프레드 피크아웃)"
    ],
    "계좌별 자산배분 및 조절 방식 (V6.0 하이브리드)": [
        "안정적 성장 추세. 전 계좌 기본 비중대로 자산 배분 유지.",
        "고점 부담 증가. [국내계좌: 기존 자산 즉시 축소 리밸런싱] / [해외계좌: 신규 자금만 방어 자산 배분]",
        "추세 붕괴 확정. [국내계좌: 기존 주식/레버리지 전량 매도 후 안전자산 100% 대피] / [해외계좌: Strict NO-SELL]",
        "역발상 타격 구간. [국내계좌: 대피시킨 안전자산 전량을 주식/레버리지로 올인 스위칭] / [해외계좌: 신규 자금 몰빵]"
    ]
})

st.table(system_df)

# 📚 지표 백과사전 및 가이드
st.markdown("---")
st.subheader("📚 지표별 상세 정의 및 트리거 가이드")
with st.expander("📖 각 지표가 무엇을 의미하고, 언제 움직여야 하는지 확인하려면 클릭하세요", expanded=False):
    st.markdown("""
    ### 1. 심리 및 추세 지표
    * **나스닥 RSI (심리):** 시장의 매수세가 얼마나 강한지 나타냅니다. 70 이상은 '과열(신규 매수 축소 및 국내 보유분 축소)', 30 이하는 '공포(적극 매수 기회)'를 뜻합니다.
    * **나스닥 125일선 (전략적 추세):** 약 6개월간의 평균 가격입니다. 3일 연속 이탈 시 추세가 무너진 것으로 보고 국내 자산은 전량 매도 대피, 해외 자산은 매수 중단(브레이크)합니다.
    * **나스닥 50일선 (전술적 보조):** 약 2.5개월간의 평균 가격으로 단기 흐름을 봅니다. 지수가 50일선 위에 있다면, 단기 상승세가 유효하므로 해외 계좌의 NO-SELL 원칙을 더욱 견고하게 유지하는 근거가 됩니다.

    ### 2. 시장 위험 및 공포 지표
    * **VIX 지수 (변동성):** 30 이상으로 치솟으면 시장이 패닉 상태임을 의미하며 바닥이 멀지 않았음을 시사합니다.
    * **공포와 탐욕 지수:** 25 미만은 비이성적 매도가 나오는 '극심한 공포(Extreme Fear)' 상태로, 오히려 좋은 역발상 매수 기회로 작용합니다.
    * **풋콜레이시오:** 1.1 이상이면 하락을 두려워하는 프리미엄 베팅이 압도적으로 많다는 뜻으로, 반등 펀치력이 장전되는 바닥 신호로 해석합니다.

    ### 3. 시스템 리스크 및 필터링 지표
    * **QQQ 거래량 (휩소 필터):** 트리거 발생 시 20일 평균 거래량 대비 1.5배 이상 터졌는지를 보고 가짜 신호(Whipsaw) 여부를 교차 판정합니다.
    * **하이일드 스프레드 피크아웃 (최종 안전장치):** 5.0% 이상 벌어지면 신용 위험 금융 위기 전조입니다. 액셀러 모드로 자산을 통째로 주식 스위칭할 때는 반드시 이 스프레드가 고점을 찍고 꺾이는(Peak-out) 흐름을 확인해야 시스템 위험 분쇄가 가능합니다.
    """)
}