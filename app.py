import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. 페이지 및 기본 설정 ---
st.set_page_config(page_title="상민 전용 투자 내비게이션", layout="wide")

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
def get_exact_index_data():
    ndx = yf.Ticker("^NDX").history(period="1y")
    sp500 = yf.Ticker("^GSPC").history(period="1y")
    vix = yf.Ticker("^VIX").history(period="1y")
    qqq = yf.Ticker("QQQ").history(period="1y")
    
    for _df in [ndx, sp500, vix, qqq]:
        if _df.index.tz is not None:
            _df.index = _df.index.tz_localize(None)
            
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

# --- 2. 데이터 로드 및 변수 할당 ---
df = get_exact_index_data()
current = df.iloc[-1]
prev_3days = df.iloc[-4:-1]

ndx_close = round(float(current['NDX_Close']), 2)
ndx_125 = round(float(current['NDX_125EMA']), 2)
ndx_50 = round(float(current['NDX_50EMA']), 2)
ndx_rsi = round(float(current['NDX_RSI']), 2)
sp500_close = round(float(current['SP500_Close']), 2)
sp500_200 = round(float(current['SP500_200EMA']), 2)
vix = round(float(current['VIX_Close']), 2)

vol_surge = float(current['Volume']) > float(current['Vol_20MA']) * 1.5
is_break_3days = (prev_3days['NDX_Close'] < prev_3days['NDX_125EMA']).all() and (ndx_close < ndx_125)

# --- 3. UI 대시보드 구성 ---
st.title("🧭 상민 전용 투자 비서 시스템 V2.3")
st.markdown("본업에 집중하십시오. 감정에 휘둘리지 않는 데이터 무결성을 최우선으로 보고합니다.")
st.divider()

# --- [신규 기능] 사이드바: 보조 지표 수동 입력 칸 ---
st.sidebar.header("📝 보조 지표 수동 입력")
st.sidebar.markdown("사이트에서 확인한 수치를 아래에 입력하십시오.")

input_fg = st.sidebar.number_input("1. 공포와 탐욕 지수 (0~100)", min_value=0, max_value=100, value=50)
input_pcr = st.sidebar.number_input("2. 풋콜레이시오 (PCR)", min_value=0.0, max_value=3.0, value=0.9, step=0.01)
input_hy = st.sidebar.number_input("3. 하이일드 스프레드 (%)", min_value=0.0, max_value=20.0, value=4.0, step=0.1)

# 수동 입력 지표 해석 로직
fg_status = "극단적 공포 (기회)" if input_fg < 25 else "정상"
pcr_status = "극단적 공포 (바닥 신호)" if input_pcr >= 1.1 else "정상"
hy_status = "위험 감지" if input_hy > 5.0 else "안정"

# 상단: 메인 감시 지표
st.subheader("📊 2. 메인 감시 지표 (Primary Triggers)")
trigger_data = {
    "지표": ["나스닥 100 지수 (RSI)", "VIX 지수", "S&P 500 (200일선)", "나스닥 100 (125일선)", "공포와 탐욕 (수동)", "풋콜레이시오 (수동)"],
    "트리거 발생 기준": ["30 이하 / 70 이상", "30 이상", "지수 이탈", "3거래일 연속 하회", "25 미만", "1.1 이상"],
    "현재 수치 / 상태": [
        f"{ndx_rsi} ({'경계' if ndx_rsi>=70 else '기회' if ndx_rsi<=30 else '안정'})",
        f"{vix} ({'공포' if vix>=30 else '안정'})",
        f"{sp500_close:,.2f} (기준선: {sp500_200:,.2f})",
        f"{ndx_close:,.2f} (기준선: {ndx_125:,.2f})",
        f"{input_fg} ({fg_status})",
        f"{input_pcr} ({pcr_status})"
    ],
    "현재 판정": [
        "🔴 트리거 발동" if ndx_rsi <= 30 or ndx_rsi >= 70 else "🟢 정상 궤도",
        "🔴 트리거 발동" if vix >= 30 else "🟢 정상 궤도",
        "🔴 200일선 이탈" if sp500_close < sp500_200 else "🟢 지지 중",
        "🟡 브레이크 진입" if is_break_3days else "🟢 정상 궤도",
        "🔴 기회 포착" if input_fg < 25 else "🟢 정상",
        "🔴 바닥 확인" if input_pcr >= 1.1 else "🟢 정상"
    ]
}
st.table(pd.DataFrame(trigger_data))

# 직통 버튼
st.caption("※ 아래 버튼을 클릭하여 수치를 확인한 후 왼쪽 사이드바에 입력하십시오.")
col_btn1, col_btn2, col_btn3 = st.columns(3)
with col_btn1:
    st.link_button("🔗 CNN 공포와 탐욕 지수 확인", "https://edition.cnn.com/markets/fear-and-greed", use_container_width=True)
with col_btn2:
    st.link_button("🔗 CBOE 풋콜레이시오 (PCR) 확인", "https://www.cboe.com/us/options/market_statistics/", use_container_width=True)
with col_btn3:
    st.link_button("🔗 연준 하이일드 스프레드 확인", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", use_container_width=True)

st.divider()

# 중단: 3대 전략별 시장 대응 모드
st.subheader("🎯 3대 투자 전략별 현재 대응 모드")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🛡️ Hyper-Shield")
    if ndx_rsi <= 30 or input_fg < 25:
        st.error("**액셀러 모드 (Accel)**\n\nQLD 집중 매수 구간")
    elif is_break_3days:
        st.warning("**브레이크 (Break)**\n\n주식 매수 중단, 방어자산 적립")
    else:
        st.success("**평상시 (Normal)**\n\n기계적 비중 매수")

with col2:
    st.markdown("### 🚀 Hyper-Accelerator")
    if ndx_rsi <= 30:
        st.error("**액셀러 모드 (Accel)**\n\nMAGS/MGK 화력 집중")
    elif is_break_3days:
        st.warning("**브레이크 (Break)**\n\n매수 중단, 방어자산 배분")
    else:
        st.success("**평상시 (Normal)**\n\n4:4:1:1 기계적 매수")

with col3:
    st.markdown("### 🧠 스마트 DCA")
    if (ndx_rsi <= 30 and input_fg < 25):
        st.error("**액셀 (Accel)**\n\n성장 자산 집중 매수")
    elif ndx_rsi >= 70:
        st.info("**과열 방어 (Defense)**\n\n방어 자산 비중 확대")
    elif is_break_3days:
        st.warning("**브레이크 (Break)**\n\n성장 자산 매수 중단")
    else:
        st.success("**평상시 (Normal)**\n\n기본 배합비 매수")

st.divider()

# 하단: 비서의 전문 검증 및 조언
st.subheader("📋 비서의 전문 검증 및 조언 레이어 (보고 표준 양식)")

st.markdown(f"""
**1. 🚨 메인 신호 상황**
* 나스닥 RSI: **{ndx_rsi}** / 공포탐욕지수: **{input_fg}**
* 풋콜레이시오(PCR): **{input_pcr}** / VIX: **{vix}**

**2. 📊 데이터 무결성 결과**
* S&P 500 지수({sp500_close:,.2f})는 200일선 대비 **{'안착' if sp500_close > sp500_200 else '이탈'}** 상태입니다.
* 입력하신 보조 지표 수치를 바탕으로 분석을 완료했습니다.

**3. 🕵️ 비서의 검증 의견**
* **바닥 신호 중첩도:** RSI와 공포탐욕지수가 동시에 트리거를 보낼 경우 강력한 '액셀' 신호로 간주합니다. (현재 **{'강력 매수 구간' if (ndx_rsi <= 30 and input_fg < 25) else '분석 중'}**)
* **시스템 리스크:** 하이일드 스프레드가 {input_hy}%로 입력되었습니다. **{'안정적입니다.' if input_hy <= 5.0 else '급격한 상승 시 신용 위험에 대비하십시오.'}**

**4. 💡 최종 제언**
""")

if (ndx_rsi <= 30 and input_fg < 25) or input_pcr >= 1.1:
    st.error("현재 여러 지표에서 **'극단적 공포'**가 감지됩니다. 이는 가이드라인상 최적의 매수 기회인 **액셀러 모드**입니다. 망설이지 마시고 정해진 공격 자산에 화력을 집중하십시오.")
elif ndx_rsi >= 70:
    st.info("시장이 과열되었습니다. 스마트 DCA 전략에 따라 방어 자산을 늘리되, 기존 자산은 절대 매도하지 마십시오.")
elif is_break_3days:
    st.warning("추세 붕괴(브레이크)가 확인되었습니다. 수동 입력 지표가 호전될 때까지 주식 추가 매수를 멈추고 방어 자산 비중을 지키십시오.")
else:
    st.success("대부분의 지표가 정상 범위 내에 있습니다. 시장 노이즈를 무시하고 이번 달 정해진 금액을 기계적으로 배분하십시오.")