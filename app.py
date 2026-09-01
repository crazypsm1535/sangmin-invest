import datetime
import warnings
import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

# 불필요한 경고 메시지 억제
warnings.filterwarnings('ignore')

# ==========================================
# 1. 페이지 설정 및 다크 테마 디자인 (#202024)
# ==========================================
st.set_page_config(
    page_title="HYPER-INVEST V8.2 통합 마스터 내비게이션",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Ultimate Dark Grey Theme (#202024) */
    .stApp {
        background-color: #202024;
        color: #e1e1e6;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans KR', sans-serif;
    }
    .block-container {
        padding-top: 2.0rem !important;
        padding-bottom: 2rem !important;
        max-width: 96% !important;
    }
    h1 {
        margin-top: 0px !important;
        margin-bottom: 6px !important;
        font-size: 26px !important;
        font-weight: 800;
        color: #ffffff !important;
        letter-spacing: -0.5px;
    }
    h2 {
        border-left: 5px solid #00e5ff;
        padding-left: 12px;
        margin-top: 24px !important;
        margin-bottom: 12px !important;
        font-size: 19px !important;
        font-weight: 700;
        color: #00e5ff !important;
    }
    h3 {
        color: #ffffff !important;
        margin-top: 0px !important;
        margin-bottom: 8px !important;
        font-size: 16px !important;
    }
    
    /* 지표 카드 스타일 */
    .metric-card {
        background-color: #161619;
        border: 1px solid #3a3a42;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .metric-card-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }
    .metric-title {
        font-size: 13px;
        font-weight: 600;
        color: #94a3b8;
    }
    .metric-value {
        font-size: 22px;
        font-weight: 800;
        color: #ffffff;
    }
    .metric-sub {
        font-size: 11.5px;
        color: #64748b;
        margin-top: 4px;
    }
    
    /* 포트폴리오 카드 UI 스타일 */
    .portfolio-card {
        background-color: #1a1a1e;
        border: 1px solid #3a3a42;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }
    .portfolio-card-header {
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .portfolio-card-desc {
        font-size: 12px;
        color: #94a3b8;
        margin-bottom: 14px;
    }
    .portfolio-card-content {
        background-color: #121214;
        padding: 14px;
        border-radius: 8px;
        font-size: 13.5px;
        line-height: 1.6;
        border: 1px solid #2d2d34;
    }
    .portfolio-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 700;
    }

    /* 시황 분석 전용 박스 */
    .context-box {
        background-color: #161619;
        border: 1px dashed #3a3a42;
        border-radius: 8px;
        padding: 14px 18px;
        margin-top: 8px;
        margin-bottom: 16px;
        font-size: 14px;
        line-height: 1.7;
    }

    /* 배지 컬러 */
    .badge-normal { background-color: rgba(0, 229, 255, 0.15); color: #00e5ff; border: 1px solid #00e5ff; }
    .badge-break { background-color: rgba(255, 69, 0, 0.15); color: #ff4500; border: 1px solid #ff4500; }
    .badge-accel { background-color: rgba(0, 255, 102, 0.15); color: #00ff66; border: 1px solid #00ff66; }
    
    /* 링크 버튼 */
    div[data-testid="stLinkButton"] > a {
        background-color: #1e1e24 !important;
        color: #94a3b8 !important;
        border: 1px solid #3a3a42 !important;
        border-radius: 6px !important;
        font-size: 12px !important;
        padding: 4px 10px !important;
        transition: all 0.2s ease;
    }
    div[data-testid="stLinkButton"] > a:hover {
        background-color: #2a2a32 !important;
        color: #00e5ff !important;
        border-color: #00e5ff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# 2. 지표 연산 모듈 (Wilder's Smoothing RSI & 이격도)
# ==========================================
def calculate_wilder_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Wilder's Smoothing 방식(alpha = 1 / period)을 적용한 RSI(14) 연산
    """
    if series is None or len(series) < period:
        return pd.Series(index=series.index if series is not None else [], dtype=float)
    
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Wilder's Smoothing: ewm(alpha = 1/period, adjust=False)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


# ==========================================
# 3. 데이터 자동 수집 엔진 (FRED, CNN, yfinance)
# ==========================================
@st.cache_data(ttl=60)
def fetch_fred_high_yield():
    """FRED 미국 하이일드 스프레드 (BAMLH0A0HYM2) 자동 수집"""
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2"
        df = pd.read_csv(url, na_values='.')
        df['BAMLH0A0HYM2'] = pd.to_numeric(df['BAMLH0A0HYM2'], errors='coerce')
        df = df.dropna()
        if not df.empty:
            curr_val = float(df['BAMLH0A0HYM2'].iloc[-1])
            max_20d = float(df['BAMLH0A0HYM2'].iloc[-20:].max())
            last_date = str(df['DATE'].iloc[-1])
            return {
                "success": True,
                "current": curr_val,
                "max_20d": max_20d,
                "diff": curr_val - max_20d,
                "date": last_date
            }
    except Exception as e:
        pass
    # 통신 실패 시 기본값 폴백
    return {
        "success": False,
        "current": 2.70,
        "max_20d": 3.80,
        "diff": -1.10,
        "date": "Fallback"
    }


@st.cache_data(ttl=60)
def fetch_cnn_and_cboe_indicators():
    """CNN Fear & Greed Index 및 옵션 지표 (Put/Call Ratio) 수집"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://www.cnn.com/markets/fear-and-greed'
    }
    fg_score = 48.0
    fg_rating = "neutral"
    pcr_val = 0.85
    breadth_val = 65.0
    fetch_success = False

    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code == 200:
            data = r.json()
            if 'fear_and_greed' in data:
                fg_score = float(round(data['fear_and_greed'].get('score', 48.0), 1))
                fg_rating = str(data['fear_and_greed'].get('rating', 'neutral'))
            
            # Put/Call Options
            if 'put_call_options' in data:
                pco_data = data['put_call_options'].get('data', [])
                if pco_data and len(pco_data) > 0:
                    pcr_val = float(round(pco_data[-1].get('y', 0.85), 2))
                else:
                    pcr_score = data['put_call_options'].get('score', 50)
                    pcr_val = float(round(0.6 + (100 - pcr_score) * 0.008, 2))
            
            # Breadth
            if 'stock_price_breadth' in data:
                breadth_score = data['stock_price_breadth'].get('score', 65.0)
                breadth_val = float(round(breadth_score, 1))
            
            fetch_success = True
    except Exception:
        pass
    
    return {
        "success": fetch_success,
        "fg_score": fg_score,
        "fg_rating": fg_rating,
        "pcr_val": pcr_val,
        "breadth_val": breadth_val
    }


@st.cache_data(ttl=30)
def fetch_market_data():
    """yfinance를 통한 QQQ, ^NDX, ^VIX, ^TNX, DX-Y.NYB 실시간 시세 및 기술 지표 연산"""
    try:
        tickers = ['QQQ', '^NDX', '^VIX', '^TNX', 'DX-Y.NYB']
        data = yf.download(tickers, period='2y', progress=False, group_by='ticker', timeout=12)
        
        if data.empty:
            return None

        # 1. QQQ 데이터 가공
        qqq_df = data['QQQ'].dropna(subset=['Close']).copy()
        if qqq_df.empty:
            return None

        qqq_close = qqq_df['Close']
        qqq_volume = qqq_df['Volume']
        
        # 이동평균선
        qqq_200sma = qqq_close.rolling(window=200).mean()
        qqq_125sma = qqq_close.rolling(window=125).mean()
        
        # 125일 이평선 이격도 (%)
        qqq_125_disparity = ((qqq_close / qqq_125sma) - 1.0) * 100.0
        
        # Wilder RSI(14) 일봉
        qqq_daily_rsi = calculate_wilder_rsi(qqq_close, period=14)
        
        # Wilder RSI(14) 주봉
        qqq_weekly_close = qqq_close.resample('W-FRI').last().dropna()
        qqq_weekly_rsi = calculate_wilder_rsi(qqq_weekly_close, period=14)
        
        # 200일선 3거래일 연속 하회 판정 (QQQ 종가 기준)
        below_200 = (qqq_close < qqq_200sma)
        is_break_3days = bool(below_200.iloc[-3:].all()) if len(below_200) >= 3 else False

        # 거래량 20일 이평 대비 1.5배 폭발 여부
        vol_20ma = qqq_volume.rolling(window=20).mean()
        vol_surge = bool(qqq_volume.iloc[-1] > vol_20ma.iloc[-1] * 1.5) if not vol_20ma.empty else False

        # 2. NDX 일봉 RSI
        ndx_df = data['^NDX'].dropna(subset=['Close'])
        ndx_rsi = calculate_wilder_rsi(ndx_df['Close'], period=14) if not ndx_df.empty else qqq_daily_rsi

        # 3. VIX, TNX(10년물 금리), DXY(달러인덱스)
        vix_df = data['^VIX'].dropna(subset=['Close'])
        vix_val = float(vix_df['Close'].iloc[-1]) if not vix_df.empty else 16.0

        tnx_df = data['^TNX'].dropna(subset=['Close'])
        tnx_val = float(tnx_df['Close'].iloc[-1]) if not tnx_df.empty else 4.25

        dxy_df = data['DX-Y.NYB'].dropna(subset=['Close'])
        dxy_val = float(dxy_df['Close'].iloc[-1]) if not dxy_df.empty else 103.5

        return {
            "success": True,
            "qqq_close": float(qqq_close.iloc[-1]),
            "qqq_200sma": float(qqq_200sma.iloc[-1]),
            "qqq_125sma": float(qqq_125sma.iloc[-1]),
            "qqq_125_disparity": float(qqq_125_disparity.iloc[-1]),
            "qqq_daily_rsi": float(qqq_daily_rsi.iloc[-1]),
            "qqq_weekly_rsi": float(qqq_weekly_rsi.iloc[-1]),
            "ndx_daily_rsi": float(ndx_rsi.iloc[-1]),
            "is_break_3days": is_break_3days,
            "vol_surge": vol_surge,
            "vix": vix_val,
            "tnx": tnx_val,
            "dxy": dxy_val,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception:
        return None


# ==========================================
# 4. 사이드바 (수동 오버라이드 & 시뮬레이터 & 계산기)
# ==========================================
st.sidebar.title("🧭 HYPER-INVEST V8.2")
st.sidebar.caption("통합 마스터 백서 표준 관제탑")

st.sidebar.markdown("---")
st.sidebar.subheader("🧪 인위적 테스트 모드 (시뮬레이터)")
sim_mode = st.sidebar.checkbox("🚨 시뮬레이션 모드 활성화", value=False)

if sim_mode:
    st.sidebar.info("🕹️ **가상 시장 상황을 강제로 주입하여 시스템 반응을 검증합니다.**")
    sim_break = st.sidebar.selectbox(
        "1. QQQ 200일선 3거래일 연속 하회",
        [False, True],
        format_func=lambda x: "🚨 3일 연속 붕괴 (브레이크 발동)" if x else "✅ 정상 (200일선 상회)"
    )
    sim_rsi = st.sidebar.slider("2. QQQ/NDX 일봉 RSI", min_value=5.0, max_value=95.0, value=26.0, step=0.5)
    sim_vix = st.sidebar.slider("3. VIX 공포 지수", min_value=10.0, max_value=75.0, value=34.0, step=0.5)
    sim_hy = st.sidebar.number_input("4. FRED 하이일드 스프레드 (%)", value=3.20, step=0.05)
    sim_hy_max = st.sidebar.number_input("5. 하이일드 20일 최고치 (%)", value=4.50, step=0.05)
    sim_tnx = st.sidebar.number_input("6. 10년물 미국 국채 금리 (%)", value=4.45, step=0.01)
    sim_dxy = st.sidebar.number_input("7. 달러 인덱스 (DXY)", value=104.20, step=0.1)
    sim_pcr = st.sidebar.number_input("8. CBOE 풋콜비율 (PCR)", value=1.15, step=0.01)
    sim_fg = st.sidebar.slider("9. CNN 공포탐욕지수", 0, 100, 22)
else:
    sim_break, sim_rsi, sim_vix = None, None, None
    sim_hy, sim_hy_max, sim_tnx, sim_dxy, sim_pcr, sim_fg = None, None, None, None, None, None

st.sidebar.markdown("---")
st.sidebar.subheader("🧮 3대 계좌 실시간 자산 배분 계산기")
with st.sidebar.expander("💼 계좌별 투자금액 설정 (클릭)", expanded=False):
    st.caption("현재 자산을 입력하면 V8.2 포메이션에 따른 목표 매수/대피 금액을 자동 산출합니다.")
    user_pension_won = st.number_input("1. 개인연금(삼성) 원금/평가액 (원)", value=30000000, step=1000000, format="%d")
    user_isa_won = st.number_input("2. 국내 ISA(NH) 원금/평가액 (원)", value=20000000, step=1000000, format="%d")
    user_toss_usd = st.number_input("3. 해외직투(토스) 원금/평가액 (USD $)", value=20000, step=1000, format="%d")


# ==========================================
# 5. 메인 대시보드 렌더링 프래그먼트
# ==========================================
@st.fragment(run_every=60)
def render_master_dashboard():
    # 1. 데이터 수집
    market = fetch_market_data()
    fred = fetch_fred_high_yield()
    cnn = fetch_cnn_and_cboe_indicators()

    # 데이터 통신 폴백 처리
    if market is None:
        raw_qqq_close = 716.50
        raw_qqq_200sma = 654.00
        raw_qqq_125sma = 680.00
        raw_qqq_125_disp = 5.37
        raw_qqq_daily_rsi = 52.0
        raw_qqq_weekly_rsi = 58.0
        raw_ndx_rsi = 52.0
        raw_break_3days = False
        raw_vol_surge = False
        raw_vix = 15.80
        raw_tnx = 4.25
        raw_dxy = 103.50
        st.error("🚨 실시간 시장 시세 연동 지연으로 안전 기본값 모드로 표시 중입니다.")
    else:
        raw_qqq_close = market["qqq_close"]
        raw_qqq_200sma = market["qqq_200sma"]
        raw_qqq_125sma = market["qqq_125sma"]
        raw_qqq_125_disp = market["qqq_125_disparity"]
        raw_qqq_daily_rsi = market["qqq_daily_rsi"]
        raw_qqq_weekly_rsi = market["qqq_weekly_rsi"]
        raw_ndx_rsi = market["ndx_daily_rsi"]
        raw_break_3days = market["is_break_3days"]
        raw_vol_surge = market["vol_surge"]
        raw_vix = market["vix"]
        raw_tnx = market["tnx"]
        raw_dxy = market["dxy"]

    raw_hy_curr = fred["current"]
    raw_hy_max = fred["max_20d"]
    raw_pcr = cnn["pcr_val"]
    raw_fg = cnn["fg_score"]
    raw_breadth = cnn["breadth_val"]

    # 시뮬레이션 적용 여부
    active_break = sim_break if sim_mode else raw_break_3days
    active_rsi = sim_rsi if sim_mode else raw_qqq_daily_rsi
    active_vix = sim_vix if sim_mode else raw_vix
    active_hy_curr = sim_hy if sim_mode else raw_hy_curr
    active_hy_max = sim_hy_max if sim_mode else raw_hy_max
    active_tnx = sim_tnx if sim_mode else raw_tnx
    active_dxy = sim_dxy if sim_mode else raw_dxy
    active_pcr = sim_pcr if sim_mode else raw_pcr
    active_fg = sim_fg if sim_mode else raw_fg

    # ==========================================
    # 6. V8.2 핵심 모드 판정 엔진
    # ==========================================
    # 1) FRED 하이일드 사격 승인 필터 (20일 최고점 대비 -0.20%p 피크아웃 OR 3.50% 이하)
    hy_approved = (active_hy_curr <= 3.50) or (active_hy_curr <= (active_hy_max - 0.20))
    
    # 2) 엑셀러 모드 트리거 (일봉 RSI < 30 AND VIX >= 30 AND 하이일드 승인)
    accel_triggered = (active_rsi < 30.0) and (active_vix >= 30.0) and hy_approved
    
    # 3) 복귀 판정 트리거 (일봉 RSI >= 40 AND VIX < 25 동시 충족)
    return_triggered = (active_rsi >= 40.0) and (active_vix < 25.0)

    # 최종 시스템 모드 결정 (최우선 순위: QQQ 200일선 3거래일 연속 하회 브레이크)
    if active_break:
        current_mode = "브레이크"
        mode_badge = '<span class="portfolio-badge badge-break">🚨 브레이크 모드</span>'
    elif accel_triggered:
        current_mode = "엑셀러"
        mode_badge = '<span class="portfolio-badge badge-accel">⚡ 엑셀러 모드</span>'
    else:
        current_mode = "평상시"
        mode_badge = '<span class="portfolio-badge badge-normal">🛡️ 평상시 모드</span>'

    # 상단 헤더
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.markdown(f"<h1>🧭 HYPER-INVEST V8.2 마스터 관제 대시보드</h1>", unsafe_allow_html=True)
        if sim_mode:
            st.markdown("<p style='font-size:13px; color:#ff4500; font-weight:bold;'>⚠️ [인위적 시뮬레이터 작동 중] 가상 데이터로 시스템을 테스트하고 있습니다.</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='font-size:13px; color:#94a3b8;'>본업에 집중하십시오. 60초 주기로 전 세계 금융 네트워크를 실시간 동기화합니다.</p>", unsafe_allow_html=True)
    with header_col2:
        st.markdown(
            f"""
            <div style="text-align: right; padding: 6px 12px; background-color: #161619; border: 1px solid #3a3a42; border-radius: 6px;">
                <span style="font-size:11px; color:#94a3b8;">시스템 확정 상태</span><br>
                <span style="font-size:16px; font-weight:bold; color:{'#ff4500' if current_mode=='브레이크' else ('#00ff66' if current_mode=='엑셀러' else '#00e5ff')};">
                    {current_mode} 모드
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ==========================================
    # 7. Section 1: 핵심 매크로 & 기술적 지표 6구역 카드
    # ==========================================
    st.markdown("## 📊 1. 핵심 매크로 & 기술적 지표 종합 매트릭스")
    
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    
    with m1:
        trend_color = "#ff4500" if active_break else "#00ff66"
        trend_text = "붕괴 (Break)" if active_break else "정상 (Pass)"
        st.markdown(
            f"""
            <div class="metric-card" style="border-top: 3px solid {trend_color};">
                <div class="metric-card-top">
                    <span class="metric-title">QQQ 200일선 추세</span>
                </div>
                <div class="metric-value" style="color:{trend_color};">{trend_text}</div>
                <div class="metric-sub">QQQ ${raw_qqq_close:.1f} / 200MA ${raw_qqq_200sma:.1f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.link_button("🔍 QQQ 차트", "https://finance.yahoo.com/quote/QQQ/chart", use_container_width=True)

    with m2:
        rsi_color = "#ff4500" if active_rsi >= 70 else ("#00ff66" if active_rsi <= 30 else "#ffffff")
        st.markdown(
            f"""
            <div class="metric-card" style="border-top: 3px solid {rsi_color};">
                <div class="metric-card-top">
                    <span class="metric-title">Wilder RSI(14)</span>
                </div>
                <div class="metric-value" style="color:{rsi_color};">{active_rsi:.1f}</div>
                <div class="metric-sub">일봉 {active_rsi:.1f} | 주봉 {raw_qqq_weekly_rsi:.1f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.link_button("🔍 NDX 차트", "https://finance.yahoo.com/quote/%5ENDX/chart", use_container_width=True)

    with m3:
        disp_color = "#ff4500" if raw_qqq_125_disp < -10 else ("#00e5ff" if raw_qqq_125_disp >= 0 else "#eab308")
        st.markdown(
            f"""
            <div class="metric-card" style="border-top: 3px solid {disp_color};">
                <div class="metric-card-top">
                    <span class="metric-title">QQQ 125일선 이격도</span>
                </div>
                <div class="metric-value" style="color:{disp_color};">{raw_qqq_125_disp:+.2f}%</div>
                <div class="metric-sub">125SMA: ${raw_qqq_125sma:.1f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.link_button("🔍 이격도 확인", "https://finance.yahoo.com/quote/QQQ", use_container_width=True)

    with m4:
        vix_color = "#00ff66" if active_vix >= 30 else ("#eab308" if active_vix >= 20 else "#94a3b8")
        vix_status = "극단 공포(>=30)" if active_vix >= 30 else ("경계(20~30)" if active_vix >= 20 else "안정(<20)")
        st.markdown(
            f"""
            <div class="metric-card" style="border-top: 3px solid {vix_color};">
                <div class="metric-card-top">
                    <span class="metric-title">VIX 공포 지수</span>
                </div>
                <div class="metric-value" style="color:{vix_color};">{active_vix:.2f}</div>
                <div class="metric-sub">{vix_status}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.link_button("🔍 VIX 차트", "https://finance.yahoo.com/quote/%5EVIX/chart", use_container_width=True)

    with m5:
        hy_color = "#00ff66" if hy_approved else "#ff4500"
        hy_text = "✅ 사격 승인" if hy_approved else "⛔ 매수 대기"
        st.markdown(
            f"""
            <div class="metric-card" style="border-top: 3px solid {hy_color};">
                <div class="metric-card-top">
                    <span class="metric-title">FRED 하이일드</span>
                </div>
                <div class="metric-value" style="color:{hy_color};">{active_hy_curr:.2f}%</div>
                <div class="metric-sub">{hy_text} (20일高 {active_hy_max:.2f}%)</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.link_button("🔍 FRED 확인", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", use_container_width=True)

    with m6:
        st.markdown(
            f"""
            <div class="metric-card" style="border-top: 3px solid #00e5ff;">
                <div class="metric-card-top">
                    <span class="metric-title">금리 & 달러 인덱스</span>
                </div>
                <div class="metric-value" style="font-size:18px; color:#ffffff;">{active_tnx:.2f}% / {active_dxy:.1f}</div>
                <div class="metric-sub">10Y {active_tnx:.2f}% | DXY {active_dxy:.1f}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.link_button("🔍 10Y 금리", "https://finance.yahoo.com/quote/%5ETNX", use_container_width=True)

    # ==========================================
    # 8. Section 2: V8.2 시스템 확정 모드 및 전술 액션 가이드
    # ==========================================
    st.markdown("---")
    st.markdown("## 🎯 2. V8.2 시스템 확정 모드 (Action Directive)")

    if current_mode == "브레이크":
        st.error("### 🔴 [브레이크 모드 발동] 추세 붕괴 확정 ➔ 계좌별 방어/대피 포메이션 즉각 전환")
        st.markdown(
            f"""
            <div class="context-box" style="border-color: #ff4500;">
                <b>🔍 실시간 시스템 판독 결과:</b><br>
                • <b>추세선 붕괴 확정:</b> QQQ 종가가 200일 이동평균선(${raw_qqq_200sma:.1f})을 <b>3거래일 연속 하회</b>했습니다.<br>
                • <b>V8.2 마스터 규정:</b> 최우선 절대 규칙이 발동되었습니다. 1배수 기본 자산(HODL)을 제외한 레버리지/변동성 자산을 안전 자산(머니마켓/KIWOOM 고배당/SGOV)으로 전량 대피하여 시드를 방어하십시오.<br>
                💡 <b>실전 행동 지침:</b> 아래 3대 계좌별 [브레이크 모드] 매도/스위칭 오더를 즉시 집행하십시오.
            </div>
            """,
            unsafe_allow_html=True
        )
    elif current_mode == "엑셀러":
        st.success("### ⚡ [엑셀러 모드 발동] 대바닥 과매도 & 시스템 안전 승인 ➔ 분할 기동 타격 집행")
        st.markdown(
            f"""
            <div class="context-box" style="border-color: #00ff66;">
                <b>🔍 실시간 시스템 판독 결과:</b><br>
                • <b>극단 과매도 확증:</b> 나스닥/QQQ 일봉 RSI({active_rsi:.1f} < 30) 및 VIX({active_vix:.1f} ≥ 30) 패닉 투매 도달.<br>
                • <b>하이일드 사격 승인:</b> 현재 하이일드 스프레드({active_hy_curr:.2f}%)가 3.50% 이하이거나 최근 20일 최고치({active_hy_max:.2f}%) 대비 -0.20%p 이상 피크아웃되어 신용 경색 위험이 없습니다.<br>
                💡 <b>실전 행동 지침:</b> 시스템 붕괴 없는 진바닥입니다. 대피해 둔 머니마켓/달러 실탄으로 <b>2분할(1차 50% / 2차 50%)</b> 집중 사격을 개시하십시오.
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("### 🟢 [평상시 모드 유지] 정상 우상향 추세 ➔ 기본 포메이션 분산 적립 (HODL & 적립)")
        st.markdown(
            f"""
            <div class="context-box" style="border-color: #00e5ff;">
                <b>🔍 실시간 시스템 판독 결과:</b><br>
                • <b>추세 정상:</b> QQQ(${raw_qqq_close:.1f})가 200일선(${raw_qqq_200sma:.1f}) 상단에 안정적으로 위치하고 있습니다.<br>
                • <b>시장 상태:</b> RSI({active_rsi:.1f}), VIX({active_vix:.1f}), 125일선 이격도({raw_qqq_125_disp:+.2f}%)가 모두 정상 범위입니다.<br>
                💡 <b>실전 행동 지침:</b> 매주 금요일 정기 분할 매수 원칙을 준수하며 평상시 황금 비중을 유지하십시오.
            </div>
            """,
            unsafe_allow_html=True
        )

    # 엑셀러 탈출 및 평상시 복귀 판독기
    st.markdown("#### 🔄 엑셀러 탈출 및 평상시 복귀 판독기 (Exit / Recovery Protocol)")
    rec_c1, rec_c2 = st.columns([3, 1])
    with rec_c1:
        if return_triggered:
            st.markdown(
                f"""
                <div style="background-color:#122818; border:1px solid #00ff66; border-radius:6px; padding:10px 14px; color:#00ff66; font-size:13.5px;">
                    ✅ <b>[평상시 복귀 승인]</b> 일봉 RSI 40 이상({active_rsi:.1f}) 및 VIX 25 미만({active_vix:.2f}) 동시 충족(AND)!<br>
                    ➔ 다가오는 금요일을 기점으로 평상시 기본 포메이션으로 정식 복귀를 승인합니다.
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style="background-color:#261814; border:1px solid #7c2d12; border-radius:6px; padding:10px 14px; color:#fb923c; font-size:13.5px;">
                    ⏸️ <b>[복귀 조건 대기]</b> 현재 RSI({active_rsi:.1f} / 기준 40) 또는 VIX({active_vix:.2f} / 기준 25 미만)가 복귀 기준치를 동시 충족하지 못했습니다.
                </div>
                """,
                unsafe_allow_html=True
            )
    with rec_c2:
        st.caption("복귀 기준: RSI ≥ 40 AND VIX < 25 (동시 충족)")

    # ==========================================
    # 9. Section 3: 3대 계좌별 V8.2 실전 포지션 매트릭스 & 자산 계산표
    # ==========================================
    st.markdown("---")
    st.markdown("## 💼 3. 3대 계좌별 V8.2 실전 포지션 매트릭스")

    col_acc1, col_acc2, col_acc3 = st.columns(3)

    # 1. 개인연금 (삼성증권)
    with col_acc1:
        if current_mode == "브레이크":
            p1_state = "🚨 100% 대피 완료"
            p1_items = "• <b>KODEX 머니마켓액티브 (488770):</b> 100% 전량 대피<br>• 빅테크7 / 나스닥100: 0% (전량 매도)"
            p1_calc = f"• 머니마켓 대피액: <b>{user_pension_won:,.0f}원 (100%)</b>"
        elif current_mode == "엑셀러":
            p1_state = "⚡ 2분할 사격 집행"
            p1_items = "• <b>머니마켓 실탄으로 70:30 사격:</b><br>• ACE 빅테크TOP7 Plus: 70%<br>• KODEX 나스닥100: 30%<br>• 1차 50% 즉시 사격 / 2차 50% 분할 매수"
            p1_calc = f"• 1차 사격 (50%): <b>{user_pension_won*0.5:,.0f}원</b><br>&nbsp;&nbsp;- 빅테크7: {user_pension_won*0.5*0.7:,.0f}원 (70%)<br>&nbsp;&nbsp;- 나스닥100: {user_pension_won*0.5*0.3:,.0f}원 (30%)"
        else:
            p1_state = "🛡️ 평상시 포메이션"
            p1_items = "• <b>ACE 미국빅테크TOP7 Plus:</b> 70%<br>• <b>KODEX 미국나스닥100:</b> 30%"
            p1_calc = f"• 빅테크7 (70%): <b>{user_pension_won*0.7:,.0f}원</b><br>• 나스닥100 (30%): <b>{user_pension_won*0.3:,.0f}원</b>"

        st.markdown(
            f"""
            <div class="portfolio-card" style="border-top: 4px solid #00e5ff;">
                <div class="portfolio-card-header" style="color: #00e5ff;">
                    <span>🧠 1. 개인연금 (삼성)</span>
                    <span style="font-size:12px; color:#94a3b8;">[동적 대피형]</span>
                </div>
                <div class="portfolio-card-desc">원금 {user_pension_won:,.0f}원 기준 배분표</div>
                <div class="portfolio-card-content">
                    <div style="font-weight:bold; color:#00e5ff; margin-bottom:6px;">{p1_state}</div>
                    {p1_items}
                    <hr style="border-color:#2d2d34; margin:10px 0;">
                    <div style="font-size:12.5px; color:#cbd5e1;">
                        <b>💰 실전 매매 금액:</b><br>{p1_calc}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # 2. 국내 ISA (NH투자증권)
    with col_acc2:
        if current_mode == "브레이크":
            p2_state = "🚨 레버리지 40% 대피"
            p2_items = "• <b>KODEX 미국나스닥100:</b> 50% (HODL 유지)<br>• <b>KIWOOM 미국고배당&AI:</b> 50% (TIGER 40% 대피 합산)<br>• TIGER 나스닥레버리지: 0% (전량 매도)"
            p2_calc = f"• KODEX 나스닥100 (50%): <b>{user_isa_won*0.5:,.0f}원</b><br>• KIWOOM 고배당 (50%): <b>{user_isa_won*0.5:,.0f}원</b>"
        elif current_mode == "엑셀러":
            p2_state = "⚡ 레버리지 50% 집중 사격"
            p2_items = "• <b>대피 실탄(KIWOOM)으로 TIGER 50% 집중 사격</b><br>• KODEX 미국나스닥100: 50% (HODL)<br>• TIGER 나스닥레버리지: 50% 집중 매수"
            p2_calc = f"• KODEX 나스닥 (50%): <b>{user_isa_won*0.5:,.0f}원</b><br>• TIGER 레버리지 (50% 사격): <b>{user_isa_won*0.5:,.0f}원</b>"
        else:
            p2_state = "🛡️ 평상시 포메이션"
            p2_items = "• <b>KODEX 미국나스닥100:</b> 50% (HODL)<br>• <b>TIGER 미국나스닥100레버리지:</b> 40%<br>• <b>KIWOOM 미국고배당&AI:</b> 10%"
            p2_calc = f"• KODEX 나스닥 (50%): <b>{user_isa_won*0.5:,.0f}원</b><br>• TIGER 레버리지 (40%): <b>{user_isa_won*0.4:,.0f}원</b><br>• KIWOOM 고배당 (10%): <b>{user_isa_won*0.1:,.0f}원</b>"

        st.markdown(
            f"""
            <div class="portfolio-card" style="border-top: 4px solid #a855f7;">
                <div class="portfolio-card-header" style="color: #c084fc;">
                    <span>🛡️ 2. 국내 ISA (NH)</span>
                    <span style="font-size:12px; color:#94a3b8;">[하이브리드형]</span>
                </div>
                <div class="portfolio-card-desc">원금 {user_isa_won:,.0f}원 기준 배분표</div>
                <div class="portfolio-card-content">
                    <div style="font-weight:bold; color:#c084fc; margin-bottom:6px;">{p2_state}</div>
                    {p2_items}
                    <hr style="border-color:#2d2d34; margin:10px 0;">
                    <div style="font-size:12.5px; color:#cbd5e1;">
                        <b>💰 실전 매매 금액:</b><br>{p2_calc}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # 3. 해외직투 (토스증권)
    with col_acc3:
        if current_mode == "브레이크":
            p3_state = "🚨 QLD 40% SGOV 대피"
            p3_items = "• <b>QQQ:</b> 50% (HODL 유지)<br>• <b>SGOV:</b> 50% (QLD 40% 대피 합산)<br>• QLD: 0% (전량 매도)"
            p3_calc = f"• QQQ (50%): <b>${user_toss_usd*0.5:,.0f}</b><br>• SGOV (50%): <b>${user_toss_usd*0.5:,.0f}</b>"
        elif current_mode == "엑셀러":
            p3_state = "⚡ QLD 50% 집중 사격"
            p3_items = "• <b>SGOV 실탄으로 QLD 50% 집중 사격</b><br>• QQQ: 50% (HODL 유지)<br>• QLD: 50% 집중 매수"
            p3_calc = f"• QQQ (50%): <b>${user_toss_usd*0.5:,.0f}</b><br>• QLD (50% 사격): <b>${user_toss_usd*0.5:,.0f}</b>"
        else:
            p3_state = "🛡️ 평상시 포메이션"
            p3_items = "• <b>QQQ:</b> 50% (HODL)<br>• <b>QLD:</b> 40%<br>• <b>SGOV:</b> 10%"
            p3_calc = f"• QQQ (50%): <b>${user_toss_usd*0.5:,.0f}</b><br>• QLD (40%): <b>${user_toss_usd*0.4:,.0f}</b><br>• SGOV (10%): <b>${user_toss_usd*0.1:,.0f}</b>"

        st.markdown(
            f"""
            <div class="portfolio-card" style="border-top: 4px solid #ff3366;">
                <div class="portfolio-card-header" style="color: #ff3366;">
                    <span>🚀 3. 해외직투 (토스)</span>
                    <span style="font-size:12px; color:#94a3b8;">[초고수익형]</span>
                </div>
                <div class="portfolio-card-desc">원금 ${user_toss_usd:,.0f} 기준 배분표</div>
                <div class="portfolio-card-content">
                    <div style="font-weight:bold; color:#ff3366; margin-bottom:6px;">{p3_state}</div>
                    {p3_items}
                    <hr style="border-color:#2d2d34; margin:10px 0;">
                    <div style="font-size:12.5px; color:#cbd5e1;">
                        <b>💰 실전 매매 금액:</b><br>{p3_calc}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ==========================================
    # 10. Section 4: 투자비서 데이터 무결성 검증 레이어
    # ==========================================
    st.markdown("---")
    st.subheader("🛡️ 4. 데이터 무결성 및 가짜 속임수 검증 레이어")
    with st.expander("🔍 매크로 리스크 및 가짜 하락 속임수 스캐닝 결과 (클릭하여 확인)", expanded=True):
        col_v1, col_v2 = st.columns(2)
        
        with col_v1:
            st.markdown("##### 1. 가짜 하락 차단 (거래량 폭발 검증)")
            if raw_vol_surge:
                st.markdown("   * 🔴 **[검증 완료]** 거래량 20일 평균 대비 1.5배 이상 폭발. 진성 투매/손바뀜 진행 중.")
            else:
                st.markdown("   * 🟢 **[일반 노이즈]** 거래량 폭발 미발생. 단순 기간 조정 및 정상 변동성 구간.")
            
            st.markdown("##### 2. CBOE 풋콜레이시오 (PCR) 극단 공포 판독")
            if active_pcr >= 1.10:
                st.markdown(f"   * 🔴 **[역발상 매수 신호]** PCR 수치 <b>{active_pcr:.2f}</b> (1.10 이상). 시장 참여자 극단 패닉 풋 매수 도달.")
            else:
                st.markdown(f"   * 🟢 **[안정 수준]** 현재 PCR 수치 <b>{active_pcr:.2f}</b> (1.10 미만).")

        with col_v2:
            st.markdown("##### 3. FRED 하이일드 피크아웃 공식 검증")
            if active_hy_curr <= 3.50:
                st.markdown(f"   * ✅ 현재 {active_hy_curr:.2f}% (3.50% 이하). **[가짜 위기 프리패스]** 신용 위험 안전존.")
            elif (active_hy_max - active_hy_curr) >= 0.20:
                st.markdown(f"   * ✅ 최고점({active_hy_max:.2f}%) 대비 부도 위험 -{(active_hy_max - active_hy_curr):.2f}%p 하락. **[피크아웃 사격 승인]**.")
            else:
                st.markdown(f"   * ⛔ 피크아웃 조건 미달 (최고점 {active_hy_max:.2f}% 대비 현재 {active_hy_curr:.2f}%). 스프레드 확대 지속 경계.")

            st.markdown("##### 4. CNN 공포와 탐욕 지수 (Fear & Greed)")
            fg_label = "극단적 공포" if active_fg <= 25 else ("공포" if active_fg <= 45 else ("중립" if active_fg <= 55 else ("탐욕" if active_fg <= 75 else "극단적 탐욕")))
            st.markdown(f"   * 🧭 현재 지수: **{active_fg:.1f}점** ({fg_label}). 시장 폭(Breadth): **{raw_breadth:.1f}%**")

    # ==========================================
    # 11. Section 5: 공식 소스 다이렉트 라우팅 및 마스터 백서 요약
    # ==========================================
    st.markdown("---")
    st.caption("🌐 공식 데이터 소스 다이렉트 라우팅")
    dl1, dl2, dl3, dl4, dl5 = st.columns(5)
    with dl1:
        st.link_button("🔵 FRED 하이일드", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", use_container_width=True)
    with dl2:
        st.link_button("🟢 CBOE 옵션 통계", "https://www.cboe.com/markets/us/options/market-statistics/daily", use_container_width=True)
    with dl3:
        st.link_button("🔴 CNN Fear & Greed", "https://edition.cnn.com/markets/fear-and-greed", use_container_width=True)
    with dl4:
        st.link_button("🟣 Yahoo QQQ 차트", "https://finance.yahoo.com/quote/QQQ", use_container_width=True)
    with dl5:
        st.link_button("🟠 TradingView S5TH", "https://www.tradingview.com/symbols/INDEX-S5TH/", use_container_width=True)

    st.markdown("---")
    st.subheader("📚 5. [HYPER-INVEST V8.2 통합 마스터 백서] 핵심 운영 수칙")
    with st.expander("📖 V8.2 마스터 백서 핵심 알고리즘 가이드 (클릭하여 펼치기)", expanded=False):
        st.markdown(
            """
            #### 💡 V8.2 핵심 지표 및 절대 원칙
            1. **QQQ 200일선 기준선 (단일 나침반):**
               - 기존 QLD 기준을 완전히 폐지하고, 전 세계 표준 지수인 **QQQ 종가 기준 200일선 3거래일 연속 하회** 시 최우선 [브레이크 모드]를 발동합니다.
            2. **Wilder's Smoothing RSI(14) & 125MA 이격도:**
               - 웰스 와일더(Welles Wilder) 정통 스무딩($\\alpha = 1/14$)을 적용하여 일봉 및 주봉 RSI를 정밀 산출합니다.
               - 125일 이평선 이격도를 통해 중기 추세 왜곡 및 과열/침체를 즉시 판별합니다.
            3. **FRED 하이일드 사격 승인 필터 (신용 부도 위험 차단):**
               - 나스닥 RSI < 30 및 VIX >= 30이어도 하이일드 스프레드가 치솟는 리먼 브라더스형 금융위기 때는 사격을 금지합니다.
               - 스프레드가 3.50% 이하이거나, 20일 최고점 대비 -0.20%p 피크아웃(정점 통과) 시에만 [엑셀러 사격]을 공식 승인합니다.
            4. **3대 계좌별 맞춤 포메이션:**
               - **개인연금(삼성):** 평상시 [빅테크7 70% : 나스닥 30%] ➔ 브레이크 [머니마켓액티브 100% 대피] ➔ 엑셀러 [머니마켓 실탄으로 2분할 사격]
               - **국내 ISA(NH):** 평상시 [나스닥 50%(HODL) : TIGER레버 40% : KIWOOM 10%] ➔ 브레이크 [TIGER만 KIWOOM으로 전량 대피] ➔ 엑셀러 [TIGER 50% 집중 사격]
               - **해외직투(토스):** 평상시 [QQQ 50%(HODL) : QLD 40% : SGOV 10%] ➔ 브레이크 [QLD만 SGOV로 전량 대피] ➔ 엑셀러 [QLD 50% 집중 사격]
            5. **평상시 복귀 승인 기준:**
               - 일봉 RSI 40 이상 AND VIX 25 미만을 동시 충족(AND)할 때 평상시 모드로 정식 복귀합니다.
            """
        )


# ==========================================
# 12. 메인 프래그먼트 실행
# ==========================================
render_master_dashboard()