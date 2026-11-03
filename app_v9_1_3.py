import datetime
import warnings
import numpy as np
import pandas as pd
import requests
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False
    class _DummyStreamlit:
        def __getattr__(self, name):
            if name in ("cache_data", "fragment"):
                return lambda *a, **kw: (lambda fn: fn)
            return lambda *a, **kw: None
    st = _DummyStreamlit()

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    yf = None

# 불필요한 경고 메시지 억제
warnings.filterwarnings("ignore")

# ==============================================================================
# 1. 페이지 설정 및 다크 테마 디자인 (#202024) - HYPER-INVEST V9.1.3 (Plan 3:4:5)
# ==============================================================================
st.set_page_config(
    page_title="HYPER-INVEST V9.1.3 마스터 관제 내비게이션 (Plan 3:4:5)",
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
        padding-top: 4.0rem !important;
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
        margin-top: 22px !important;
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
        font-size: 21px;
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
    .badge-brake { background-color: rgba(255, 69, 0, 0.15); color: #ff4500; border: 1px solid #ff4500; }
    .badge-defense { background-color: rgba(234, 179, 8, 0.15); color: #eab308; border: 1px solid #eab308; }
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


# ==============================================================================
# 2. V9.1.3 공식 지표 연산 및 상태 머신 모듈 (engine_baseline.py 100% 동기화)
# ==============================================================================
def calculate_wilder_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    V9.1.3 공식 백테스트 엔진(run_real_data_reproduction.py) 규격 Wilder's RSI(14) 연산
    """
    if series is None or len(series) == 0:
        return pd.Series(dtype=float)

    s = pd.Series(series, dtype=float)
    delta = s.diff().fillna(0.0)
    avg_g = pd.Series(np.where(delta > 0, delta, 0.0), index=s.index).ewm(alpha=1.0 / period, adjust=False).mean()
    avg_l = pd.Series(np.where(delta < 0, -delta, 0.0), index=s.index).ewm(alpha=1.0 / period, adjust=False).mean()
    rs = np.where(avg_l == 0, 100.0, avg_g / np.where(avg_l == 0, 1e-9, avg_l))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return pd.Series(rsi, index=s.index)


def calculate_roll_vol21(close_series: pd.Series, window: int = 21) -> pd.Series:
    """
    V9.1.3 공식 백테스트 엔진 규격 21일 실현변동성(RollVol21, 연율화 %) 연산
    산식: 일간수익률 21거래일 표준편차 * sqrt(252) * 100.0
    """
    if close_series is None or len(close_series) == 0:
        return pd.Series(dtype=float)

    s = pd.Series(close_series, dtype=float)
    ret = s.pct_change().fillna(0.0)
    vol = ret.rolling(window, min_periods=5).std().fillna(0.0) * np.sqrt(252.0) * 100.0
    return vol


def compute_consecutive_sma_counts(close_series: pd.Series, sma_series: pd.Series) -> tuple[int, int]:
    """
    QQQ 확정 종가와 SMA200 시계열에서 최신 시점의 연속 하회(below_cnt) 및 연속 상회(above_cnt) 일수 산출
    """
    below_cnt = 0
    above_cnt = 0
    for c, m in zip(close_series, sma_series):
        if pd.notna(m) and pd.notna(c):
            if float(c) < float(m):
                below_cnt += 1
                above_cnt = 0
            else:
                above_cnt += 1
                below_cnt = 0
    return below_cnt, above_cnt


def evaluate_v9_1_3_state_machine(
    prev_state: str,
    is_yr16: bool,
    close_q: float,
    sma_q: float,
    below_cnt: int,
    above_cnt: int,
    rsi_q: float,
    vol_q: float,
) -> dict:
    """
    HYPER-INVEST V9.1.3 공식 상태 머신 (PATCH A & D 완벽 반영, MECE 분기)
    - 입력된 직전 상태(prev_state)와 당일 확정 일봉 지표를 바탕으로
      익일 시가(Open[d+1])에 집행할 예약 액션(pending_action)과 전환 후 목표 상태(target_state)를 반환합니다.
    """
    valid_states = {"NORMAL", "BRAKE", "DEFENSE", "ACCELERATOR"}
    assert prev_state in valid_states, f"Invalid prev_state: {prev_state}"
    assert np.isfinite(close_q) and np.isfinite(sma_q), "Close and SMA200 must be finite"
    assert np.isfinite(rsi_q) and (0.0 <= rsi_q <= 100.0), f"RSI out of bounds: {rsi_q}"
    assert np.isfinite(vol_q) and (vol_q >= 0.0), f"RollVol21 must be non-negative: {vol_q}"
    assert below_cnt >= 0 and above_cnt >= 0, "Counters must be non-negative"

    pending_action = None

    # 1. [PATCH A] 16년 차 방어 승격 전이: 이미 BRAKE 상태에서 16년 차 진입 및 200MA 하회 지속 시
    if is_yr16 and prev_state == "BRAKE" and (close_q < sma_q):
        pending_action = "TO_DEFENSE"
    # 2. NORMAL 하락 전이: 200MA 3거래일 연속 하회 시
    elif prev_state == "NORMAL" and below_cnt >= 3:
        pending_action = "TO_DEFENSE" if is_yr16 else "TO_BRAKE"
    # 3. BRAKE / DEFENSE 상태에서 대바닥 사격(TO_ACCEL) 또는 정상 복귀(TO_NORMAL) 판정
    elif prev_state in ("BRAKE", "DEFENSE"):
        if (rsi_q < 30.0) and (vol_q >= 25.0):
            pending_action = "TO_ACCEL"
        elif (above_cnt >= 3) and (rsi_q >= 40.0):
            pending_action = "TO_NORMAL"
        else:
            pending_action = None
    # 4. ACCELERATOR 상태에서 과매도 해소(RSI >= 40.0) 시 복귀 판정
    elif prev_state == "ACCELERATOR":
        if rsi_q >= 40.0:
            if (close_q >= sma_q) and (above_cnt >= 3):
                pending_action = "TO_NORMAL"
            else:
                pending_action = "TO_DEFENSE" if is_yr16 else "TO_BRAKE"
        else:
            pending_action = None
    else:
        pending_action = None

    action_to_state = {
        None: prev_state,
        "TO_NORMAL": "NORMAL",
        "TO_BRAKE": "BRAKE",
        "TO_DEFENSE": "DEFENSE",
        "TO_ACCEL": "ACCELERATOR",
    }
    target_state = action_to_state[pending_action]

    return {
        "prev_state": prev_state,
        "pending_action": pending_action if pending_action is not None else "HOLD",
        "target_state": target_state,
        "is_transition": pending_action is not None,
    }


def compute_monthly_contribution_guide(active_state: str, monthly_total_krw: float = 1_200_000.0) -> dict:
    """
    Plan 3:4:5 월 정기 적립금(기본 120만 원: 연금 25% / ISA 33.33% / 직투 41.67%)의
    시장 상태별(NORMAL vs BRAKE vs DEFENSE) 월간 및 주간(4회 분할) 매수 금액 산출 (13-3절 코드 기준)
    """
    assert active_state in {"NORMAL", "BRAKE", "DEFENSE", "ACCELERATOR"}, f"Invalid state: {active_state}"
    assert monthly_total_krw > 0, "Monthly contribution must be positive"

    pmt_pen = round(monthly_total_krw * (300_000.0 / 1_200_000.0), 2)
    pmt_isa = round(monthly_total_krw * (400_000.0 / 1_200_000.0), 2)
    pmt_ov = monthly_total_krw - pmt_pen - pmt_isa

    if active_state in ("BRAKE", "DEFENSE"):
        pen_alloc = {"ACE 미국빅테크TOP7 Plus (465580)": 0.0, "KODEX 미국나스닥100 (379810)": 0.0, "KODEX 머니마켓액티브 (488770)": pmt_pen}
        w_isa_1x = 0.20 if active_state == "DEFENSE" else 0.50
        w_isa_ca = 0.80 if active_state == "DEFENSE" else 0.50
        isa_alloc = {
            "KODEX 미국나스닥100 [1배] (379810)": pmt_isa * w_isa_1x,
            "TIGER 미국나스닥100레버리지 [2배] (418660)": 0.0,
            "KODEX 머니마켓액티브/현금 (488770)": pmt_isa * w_isa_ca,
        }
        ov_alloc = {
            "Invesco QQQ [1배 코어]": pmt_ov * 0.50,
            "ProShares QLD [2배 알파]": 0.0,
            "외화예수금(USD 달러)/SGOV": pmt_ov * 0.50,
        }
    else:
        # NORMAL 또는 ACCELERATOR 중 정기 적립은 기본 50:40:10 (연금 70:30)
        pen_alloc = {
            "ACE 미국빅테크TOP7 Plus (465580)": pmt_pen * 0.70,
            "KODEX 미국나스닥100 (379810)": pmt_pen * 0.30,
            "KODEX 머니마켓액티브 (488770)": 0.0,
        }
        isa_alloc = {
            "KODEX 미국나스닥100 [1배] (379810)": pmt_isa * 0.50,
            "TIGER 미국나스닥100레버리지 [2배] (418660)": pmt_isa * 0.40,
            "KODEX 머니마켓액티브/현금 (488770)": pmt_isa * 0.10,
        }
        ov_alloc = {
            "Invesco QQQ [1배 코어]": pmt_ov * 0.50,
            "ProShares QLD [2배 알파]": pmt_ov * 0.40,
            "외화예수금(USD 달러)/SGOV": pmt_ov * 0.10,
        }

    # 수지 균형 검증식 (부동소수점 오차 < 1e-6)
    assert abs(sum(pen_alloc.values()) - pmt_pen) < 1e-6, "Pension contribution sum mismatch"
    assert abs(sum(isa_alloc.values()) - pmt_isa) < 1e-6, "ISA contribution sum mismatch"
    assert abs(sum(ov_alloc.values()) - pmt_ov) < 1e-6, "Overseas contribution sum mismatch"

    return {
        "pmt_pen": pmt_pen,
        "pmt_isa": pmt_isa,
        "pmt_ov": pmt_ov,
        "pen_alloc": pen_alloc,
        "isa_alloc": isa_alloc,
        "ov_alloc": ov_alloc,
    }


def compute_account_rebalance_plan(
    target_state: str,
    pen_eq: float,
    pen_ca: float,
    isa_1x: float,
    isa_2x: float,
    isa_ca: float,
    ov_q: float,
    ov_qld: float,
    ov_s: float,
) -> dict:
    """
    V9.1.3 공식 코드(execute_action, PATCH E & 항목 D) 기준 계좌별 목표 잔액 및 매매 주문 산출
    - TO_NORMAL: ISA 1배수(50%) 우선 복원 후 잔여 현금 한도 내 2배수(40%) 순차 네팅(Netting) 복원
    - TO_ACCEL: 각 계좌 보유 현금/달러 실탄의 70% 일괄 사격 (잔여 30% 보존)
    - TO_BRAKE: 연금 전량 현금화, ISA 2배수 전량 현금화(1배수 HODL), 직투 QLD 전량 달러화(QQQ 영구 HODL)
    - TO_DEFENSE: 연금 전량 현금화, ISA 1배수 20%로 축소 + 2배수 전량 현금화(현금 80%), 직투 QLD 전량 달러화(QQQ 영구 HODL)
    """
    for val in (pen_eq, pen_ca, isa_1x, isa_2x, isa_ca, ov_q, ov_qld, ov_s):
        assert np.isfinite(val) and val >= 0.0, f"Asset balance must be finite and non-negative: {val}"

    t_pen = pen_eq + pen_ca
    t_isa = isa_1x + isa_2x + isa_ca
    t_ov = ov_q + ov_qld + ov_s

    if target_state == "BRAKE":
        n_pen_eq, n_pen_ca = 0.0, t_pen
        n_isa_1x, n_isa_2x, n_isa_ca = isa_1x, 0.0, isa_ca + isa_2x
        n_ov_q, n_ov_qld, n_ov_s = ov_q, 0.0, ov_s + ov_qld
        order_desc = {
            "pen": f"주식 전량({pen_eq:,.0f}원) 매도 ➔ 머니마켓 100%({n_pen_ca:,.0f}원) 대피",
            "isa": f"1배수({isa_1x:,.0f}원) HODL 유지 / 2배수({isa_2x:,.0f}원) 전량 매도 ➔ 머니마켓/현금({n_isa_ca:,.0f}원) 대피",
            "ov": f"QQQ(${ov_q:,.1f}) 영구 HODL / QLD(${ov_qld:,.1f}) 전량 매도 ➔ 외화예수금/SGOV(${n_ov_s:,.1f}) 대피",
        }
    elif target_state == "DEFENSE":
        n_pen_eq, n_pen_ca = 0.0, t_pen
        sell_1x = max(0.0, isa_1x - t_isa * 0.20)
        n_isa_1x = isa_1x - sell_1x
        n_isa_2x = 0.0
        n_isa_ca = isa_ca + isa_2x + sell_1x
        n_ov_q, n_ov_qld, n_ov_s = ov_q, 0.0, ov_s + ov_qld
        order_desc = {
            "pen": f"주식 전량({pen_eq:,.0f}원) 매도 ➔ 머니마켓 100%({n_pen_ca:,.0f}원) 요새화",
            "isa": f"1배수 초과분({sell_1x:,.0f}원) 및 2배수 전량({isa_2x:,.0f}원) 매도 ➔ 1배수 20%({n_isa_1x:,.0f}원) : 현금성 80%({n_isa_ca:,.0f}원) 요새화",
            "ov": f"QQQ(${ov_q:,.1f}) 영구 HODL(매도 금지) / QLD(${ov_qld:,.1f}) 전량 매도 ➔ 외화예수금/SGOV(${n_ov_s:,.1f}) 대피",
        }
    elif target_state == "ACCELERATOR":
        pb = pen_ca * 0.70
        n_pen_eq, n_pen_ca = pen_eq + pb, pen_ca - pb

        ib = isa_ca * 0.70
        n_isa_1x, n_isa_2x, n_isa_ca = isa_1x, isa_2x + ib, isa_ca - ib

        ob = ov_s * 0.70
        n_ov_q, n_ov_qld, n_ov_s = ov_q, ov_qld + ob, ov_s - ob
        order_desc = {
            "pen": f"보유 현금의 70%({pb:,.0f}원) 주식 일괄 사격 [빅테크7 {pb*0.70:,.0f}원 + 나스닥100 {pb*0.30:,.0f}원] / 잔여 현금 30%({n_pen_ca:,.0f}원) 보존",
            "isa": f"보유 현금의 70%({ib:,.0f}원) TIGER 2배 레버리지 집중 사격 / 잔여 현금 30%({n_isa_ca:,.0f}원) 보존",
            "ov": f"보유 달러의 70%(${ob:,.1f}) QLD 2X 집중 사격 / 잔여 달러 30%(${n_ov_s:,.1f}) 보존",
        }
    else:
        # NORMAL (PATCH E & 항목 D: 순차 네팅 복원 리밸런싱)
        n_pen_eq, n_pen_ca = t_pen, 0.0

        target_1x = t_isa * 0.50
        target_2x = t_isa * 0.40
        buy_1x = min(isa_ca, max(0.0, target_1x - isa_1x))
        buy_2x = min(max(0.0, isa_ca - buy_1x), max(0.0, target_2x - isa_2x))
        n_isa_1x = isa_1x + buy_1x
        n_isa_2x = isa_2x + buy_2x
        n_isa_ca = max(0.0, isa_ca - buy_1x - buy_2x)

        target_qld = t_ov * 0.40
        ob = min(ov_s, max(0.0, target_qld - ov_qld))
        n_ov_q = ov_q
        n_ov_qld = ov_qld + ob
        n_ov_s = ov_s - ob
        order_desc = {
            "pen": f"머니마켓 현금 전량({pen_ca:,.0f}원) 주식 매수 ➔ 빅테크7 70%({n_pen_eq*0.70:,.0f}원) + 나스닥100 30%({n_pen_eq*0.30:,.0f}원)",
            "isa": f"[PATCH E 순차 복원] 1배수 우선 매수({buy_1x:,.0f}원) 후 잔여 현금으로 2배수 매수({buy_2x:,.0f}원) ➔ 1배 {n_isa_1x:,.0f}원 / 2배 {n_isa_2x:,.0f}원 / 현금 {n_isa_ca:,.0f}원",
            "ov": f"달러 실탄에서 QLD 목표비중(40%)까지 매수(${ob:,.1f}) ➔ QQQ ${n_ov_q:,.1f} / QLD ${n_ov_qld:,.1f} / 달러 ${n_ov_s:,.1f}",
        }

    # 수지 균형 검증식 (부동소수점 오차 < 1e-6)
    assert abs((n_pen_eq + n_pen_ca) - t_pen) < 1e-6, "Pension rebalance conservation failed"
    assert abs((n_isa_1x + n_isa_2x + n_isa_ca) - t_isa) < 1e-6, "ISA rebalance conservation failed"
    assert abs((n_ov_q + n_ov_qld + n_ov_s) - t_ov) < 1e-6, "Overseas rebalance conservation failed"

    return {
        "pen": {"eq": n_pen_eq, "ca": n_pen_ca, "total": t_pen},
        "isa": {"1x": n_isa_1x, "2x": n_isa_2x, "ca": n_isa_ca, "total": t_isa},
        "ov": {"q": n_ov_q, "qld": n_ov_qld, "s": n_ov_s, "total": t_ov},
        "order_desc": order_desc,
    }


# ==============================================================================
# 3. 데이터 자동 수집 엔진 (FRED, CNN, yfinance)
# ==============================================================================
@st.cache_data(ttl=60)
def fetch_fred_high_yield() -> dict:
    """FRED 미국 하이일드 스프레드 (BAMLH0A0HYM2) 자동 수집 및 최근 20영업일 최고점 연산"""
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2"
        df = pd.read_csv(url, na_values=".")
        date_col = "observation_date" if "observation_date" in df.columns else ("DATE" if "DATE" in df.columns else df.columns[0])
        val_col = "BAMLH0A0HYM2" if "BAMLH0A0HYM2" in df.columns else df.columns[1]

        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
        df = df.dropna(subset=[date_col, val_col]).sort_values(date_col).reset_index(drop=True)

        if not df.empty:
            last_20 = df.tail(20)
            curr_val = float(last_20[val_col].iloc[-1])
            max_20d = float(last_20[val_col].max())
            last_date = last_20[date_col].iloc[-1].strftime("%Y-%m-%d")
            diff = curr_val - max_20d
            return {
                "success": True,
                "current": curr_val,
                "max_20d": max_20d,
                "diff": diff,
                "date": last_date,
            }
    except Exception as exc:
        err_msg = str(exc)
    else:
        err_msg = "Empty dataframe"

    return {
        "success": False,
        "current": 2.65,
        "max_20d": 2.85,
        "diff": -0.20,
        "date": f"Fallback ({err_msg[:30]})",
    }


@st.cache_data(ttl=60)
def fetch_cnn_and_cboe_indicators() -> dict:
    """CNN Fear & Greed Index 및 옵션 지표 (Put/Call Ratio) 수집 (보조 확인 지표)"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.cnn.com/markets/fear-and-greed",
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
            if "fear_and_greed" in data:
                fg_score = float(round(data["fear_and_greed"].get("score", 48.0), 1))
                fg_rating = str(data["fear_and_greed"].get("rating", "neutral"))
            if "put_call_options" in data:
                pco_data = data["put_call_options"].get("data", [])
                if pco_data and len(pco_data) > 0:
                    pcr_val = float(round(pco_data[-1].get("y", 0.85), 2))
                else:
                    pcr_score = data["put_call_options"].get("score", 50)
                    pcr_val = float(round(0.6 + (100 - pcr_score) * 0.008, 2))
            if "stock_price_breadth" in data:
                breadth_score = data["stock_price_breadth"].get("score", 65.0)
                breadth_val = float(round(breadth_score, 1))
            fetch_success = True
    except Exception as exc:
        fetch_success = False

    return {
        "success": fetch_success,
        "fg_score": fg_score,
        "fg_rating": fg_rating,
        "pcr_val": pcr_val,
        "breadth_val": breadth_val,
    }


@st.cache_data(ttl=30)
def fetch_market_data() -> dict | None:
    """yfinance를 통한 QQQ, ^NDX, ^VIX, ^TNX, DX-Y.NYB 시세 및 V9.1.3 공식 기술 지표(SMA200, RSI14, RollVol21) 연산"""
    try:
        tickers = ["QQQ", "^NDX", "^VIX", "^TNX", "DX-Y.NYB"]
        data = yf.download(tickers, period="5y", progress=False, group_by="ticker", timeout=15)
        if data.empty:
            return None

        qqq_df = data["QQQ"].dropna(subset=["Close"]).copy()
        if len(qqq_df) < 205:
            return None

        qqq_close = qqq_df["Close"]
        qqq_volume = qqq_df["Volume"]

        # 1. QQQ 이동평균선 및 이격도
        qqq_200sma = qqq_close.rolling(window=200, min_periods=200).mean()
        qqq_125sma = qqq_close.rolling(window=125, min_periods=125).mean()
        qqq_200_disparity = ((qqq_close / qqq_200sma) - 1.0) * 100.0
        qqq_125_disparity = ((qqq_close / qqq_125sma) - 1.0) * 100.0

        # 2. 연속 하회(below_cnt) 및 연속 상회(above_cnt) 카운트
        below_cnt, above_cnt = compute_consecutive_sma_counts(qqq_close, qqq_200sma)

        # 3. V9.1.3 공식 QQQ Wilder RSI(14) 및 주봉 RSI(14)
        qqq_daily_rsi_series = calculate_wilder_rsi(qqq_close, period=14)
        qqq_weekly_close = qqq_close.resample("W-FRI").last().dropna()
        qqq_weekly_rsi_series = calculate_wilder_rsi(qqq_weekly_close, period=14)

        # 4. V9.1.3 공식 QQQ 21일 실현변동성 (RollVol21, 연율화 %)
        qqq_roll_vol21_series = calculate_roll_vol21(qqq_close, window=21)

        # 거래량 20일 이평 대비 1.5배 폭발 여부
        vol_20ma = qqq_volume.rolling(window=20).mean()
        vol_surge = bool(qqq_volume.iloc[-1] > vol_20ma.iloc[-1] * 1.5) if not vol_20ma.empty else False

        # 보조: ^NDX 지수 RSI(14) 병기용
        ndx_df = data["^NDX"].dropna(subset=["Close"]).copy()
        if not ndx_df.empty:
            ndx_close = ndx_df["Close"]
            ndx_d_rsi_val = float(calculate_wilder_rsi(ndx_close, period=14).iloc[-1])
            ndx_curr_close = float(ndx_close.iloc[-1])
        else:
            ndx_d_rsi_val = float(qqq_daily_rsi_series.iloc[-1])
            ndx_curr_close = 20000.0

        vix_df = data["^VIX"].dropna(subset=["Close"])
        vix_val = float(vix_df["Close"].iloc[-1]) if not vix_df.empty else 16.0

        tnx_df = data["^TNX"].dropna(subset=["Close"])
        tnx_val = float(tnx_df["Close"].iloc[-1]) if not tnx_df.empty else 4.25

        dxy_df = data["DX-Y.NYB"].dropna(subset=["Close"])
        dxy_val = float(dxy_df["Close"].iloc[-1]) if not dxy_df.empty else 103.5

        last_trade_date = qqq_df.index[-1].strftime("%Y-%m-%d")

        return {
            "success": True,
            "last_trade_date": last_trade_date,
            "qqq_close": float(qqq_close.iloc[-1]),
            "qqq_200sma": float(qqq_200sma.iloc[-1]),
            "qqq_125sma": float(qqq_125sma.iloc[-1]),
            "qqq_200_disparity": float(qqq_200_disparity.iloc[-1]),
            "qqq_125_disparity": float(qqq_125_disparity.iloc[-1]),
            "below_cnt": int(below_cnt),
            "above_cnt": int(above_cnt),
            "qqq_daily_rsi": float(qqq_daily_rsi_series.iloc[-1]),
            "qqq_weekly_rsi": float(qqq_weekly_rsi_series.iloc[-1]),
            "roll_vol21": float(qqq_roll_vol21_series.iloc[-1]),
            "ndx_close": ndx_curr_close,
            "ndx_daily_rsi": ndx_d_rsi_val,
            "vol_surge": vol_surge,
            "vix": vix_val,
            "tnx": tnx_val,
            "dxy": dxy_val,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception:
        return None


# ==============================================================================
# 4. 사이드바 (운용 연차/직전 상태 설정, 시뮬레이터, 3:4:5 계산기)
# ==============================================================================
def render_master_app():
    st.sidebar.title("🧭 HYPER-INVEST V9.1.3")
    st.sidebar.caption("실전 운용 백서 슬림판 (Plan 3:4:5) 공식 관제탑")

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ 1. 내 계좌 상태 및 투자 연차 설정")
    is_yr16_user = st.sidebar.checkbox(
        "🛡️ 16년 차 이후 수확기 (d ≥ 3,780거래일)",
        value=False,
        help="체크 시 하락장 진입 또는 BRAKE 유지 상태에서 수확기 DEFENSE(ISA 1배수 20% : 현금성 80%) 규칙이 자동 적용됩니다.",
    )
    prev_state_user = st.sidebar.selectbox(
        "현재(직전 주간) 내 계좌 상태",
        options=["NORMAL", "BRAKE", "DEFENSE", "ACCELERATOR"],
        index=0,
        help="현재 내 계좌가 유지 중인 상태를 선택하면, 오늘 확정 종가 지표를 바탕으로 다음 거래일 시가(Open[d+1])에 전환해야 할 액션을 판정합니다.",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("🧪 2. 인위적 테스트 모드 (시뮬레이터)")
    sim_mode = st.sidebar.checkbox("🚨 시뮬레이션 모드 활성화", value=False)

    if sim_mode:
        st.sidebar.info("🕹️ **가상 시장 지표를 주입하여 V9.1.3 상태 전이를 검증합니다.**")
        sim_close = st.sidebar.number_input("1. QQQ 당일 확정 종가 ($)", value=460.0, step=5.0)
        sim_sma200 = st.sidebar.number_input("2. QQQ 200일 이동평균선 ($)", value=480.0, step=5.0)
        sim_consec_days = st.sidebar.slider("3. 200MA 연속 하회(-)/상회(+) 거래일수", min_value=-10, max_value=10, value=-3, step=1)
        sim_rsi = st.sidebar.slider("4. QQQ Wilder 일봉 RSI(14)", min_value=5.0, max_value=95.0, value=27.5, step=0.5)
        sim_vol21 = st.sidebar.slider("5. 21일 실현변동성 RollVol21 (%)", min_value=5.0, max_value=80.0, value=28.0, step=0.5)
        sim_vix = st.sidebar.slider("6. CBOE VIX 지수 (보조)", min_value=10.0, max_value=75.0, value=32.0, step=0.5)
        sim_hy = st.sidebar.number_input("7. FRED 하이일드 스프레드 (%, 보조)", value=3.20, step=0.05)
        sim_hy_max = st.sidebar.number_input("8. 하이일드 20일 최고치 (%)", value=3.60, step=0.05)
        sim_tnx = st.sidebar.number_input("9. 10년물 국채 금리 (%)", value=4.30, step=0.05)
        sim_dxy = st.sidebar.number_input("10. 달러 인덱스 (DXY)", value=104.0, step=0.2)
        sim_pcr = st.sidebar.number_input("11. CBOE 풋콜비율 (PCR)", value=1.15, step=0.05)
        sim_fg = st.sidebar.slider("12. CNN 공포탐욕지수", 0, 100, 20)
    else:
        sim_close = sim_sma200 = sim_consec_days = sim_rsi = sim_vol21 = sim_vix = None
        sim_hy = sim_hy_max = sim_tnx = sim_dxy = sim_pcr = sim_fg = None

    st.sidebar.markdown("---")
    st.sidebar.subheader("🧮 3. 3:4:5 월 적립 & 리밸런싱 계산기")
    with st.sidebar.expander("💵 월 정기 적립금 설정 (기본 120만)", expanded=False):
        monthly_budget_krw = st.number_input("월 총 적립금 (원, 3:4:5 자동 배분)", value=1200000, step=100000, format="%d")

    with st.sidebar.expander("💼 계좌별 현재 보유 잔액 설정 (리밸런싱용)", expanded=False):
        st.caption("상태 전이(TO_BRAKE / TO_DEFENSE / TO_ACCEL / TO_NORMAL) 발생 시 계좌별 정확한 매수·매도 금액을 산출합니다.")
        user_pen_eq = st.number_input("1-A. 개인연금 주식 평가액 (원)", value=21000000, step=1000000, format="%d")
        user_pen_ca = st.number_input("1-B. 개인연금 머니마켓/현금 (원)", value=9000000, step=1000000, format="%d")
        user_isa_1x = st.number_input("2-A. 국내 ISA 1배수(나스닥100) (원)", value=10000000, step=1000000, format="%d")
        user_isa_2x = st.number_input("2-B. 국내 ISA 2배수(TIGER레버) (원)", value=8000000, step=1000000, format="%d")
        user_isa_ca = st.number_input("2-C. 국내 ISA 머니마켓/현금 (원)", value=2000000, step=500000, format="%d")
        user_ov_q = st.number_input("3-A. 해외직투 QQQ 평가액 ($)", value=10000, step=500, format="%d")
        user_ov_qld = st.number_input("3-B. 해외직투 QLD 평가액 ($)", value=8000, step=500, format="%d")
        user_ov_s = st.number_input("3-C. 해외직투 외화예수금/SGOV ($)", value=2000, step=500, format="%d")

    # ==============================================================================
    # 5. 메인 대시보드 렌더링 프래그먼트
    # ==============================================================================
    @st.fragment(run_every=60)
    def render_master_dashboard():
        market = fetch_market_data()
        fred = fetch_fred_high_yield()
        cnn = fetch_cnn_and_cboe_indicators()

        if market is None:
            raw_qqq_close = 500.00
            raw_qqq_200sma = 475.00
            raw_qqq_125sma = 488.00
            raw_qqq_200_disp = 5.26
            raw_qqq_125_disp = 2.46
            raw_below_cnt = 0
            raw_above_cnt = 15
            raw_qqq_daily_rsi = 54.0
            raw_qqq_weekly_rsi = 57.5
            raw_roll_vol21 = 16.2
            raw_ndx_daily_rsi = 54.2
            raw_vol_surge = False
            raw_vix = 15.80
            raw_tnx = 4.25
            raw_dxy = 103.50
            last_trade_date = "Fallback"
            st.error("🚨 실시간 시장 시세 연동 지연으로 안전 기본값 모드로 표시 중입니다.")
        else:
            raw_qqq_close = market["qqq_close"]
            raw_qqq_200sma = market["qqq_200sma"]
            raw_qqq_125sma = market["qqq_125sma"]
            raw_qqq_200_disp = market["qqq_200_disparity"]
            raw_qqq_125_disp = market["qqq_125_disparity"]
            raw_below_cnt = market["below_cnt"]
            raw_above_cnt = market["above_cnt"]
            raw_qqq_daily_rsi = market["qqq_daily_rsi"]
            raw_qqq_weekly_rsi = market["qqq_weekly_rsi"]
            raw_roll_vol21 = market["roll_vol21"]
            raw_ndx_daily_rsi = market["ndx_daily_rsi"]
            raw_vol_surge = market["vol_surge"]
            raw_vix = market["vix"]
            raw_tnx = market["tnx"]
            raw_dxy = market["dxy"]
            last_trade_date = market["last_trade_date"]

        raw_hy_curr = fred["current"]
        raw_hy_max = fred["max_20d"]
        raw_pcr = cnn["pcr_val"]
        raw_fg = cnn["fg_score"]
        raw_breadth = cnn["breadth_val"]

        # 시뮬레이션 오버라이드 처리
        if sim_mode:
            active_close = float(sim_close)
            active_sma200 = float(sim_sma200)
            active_200_disp = ((active_close / active_sma200) - 1.0) * 100.0 if active_sma200 > 0 else 0.0
            if sim_consec_days < 0:
                active_below_cnt = abs(int(sim_consec_days))
                active_above_cnt = 0
                if active_close >= active_sma200:
                    active_close = active_sma200 * 0.98
            else:
                active_below_cnt = 0
                active_above_cnt = int(sim_consec_days)
                if active_close < active_sma200:
                    active_close = active_sma200 * 1.02
            active_rsi = float(sim_rsi)
            active_vol21 = float(sim_vol21)
            active_vix = float(sim_vix)
            active_hy_curr = float(sim_hy)
            active_hy_max = float(sim_hy_max)
            active_tnx = float(sim_tnx)
            active_dxy = float(sim_dxy)
            active_pcr = float(sim_pcr)
            active_fg = float(sim_fg)
        else:
            active_close = raw_qqq_close
            active_sma200 = raw_qqq_200sma
            active_200_disp = raw_qqq_200_disp
            active_below_cnt = raw_below_cnt
            active_above_cnt = raw_above_cnt
            active_rsi = raw_qqq_daily_rsi
            active_vol21 = raw_roll_vol21
            active_vix = raw_vix
            active_hy_curr = raw_hy_curr
            active_hy_max = raw_hy_max
            active_tnx = raw_tnx
            active_dxy = raw_dxy
            active_pcr = raw_pcr
            active_fg = raw_fg

        # ==============================================================================
        # 6. V9.1.3 핵심 상태 머신 판정 (PATCH A, D, E)
        # ==============================================================================
        sm_result = evaluate_v9_1_3_state_machine(
            prev_state=prev_state_user,
            is_yr16=is_yr16_user,
            close_q=active_close,
            sma_q=active_sma200,
            below_cnt=active_below_cnt,
            above_cnt=active_above_cnt,
            rsi_q=active_rsi,
            vol_q=active_vol21,
        )
        pending_action = sm_result["pending_action"]
        target_state = sm_result["target_state"]

        # 보조 지표 판정 (공식 트리거를 대체하지 않음)
        hy_approved = (active_hy_curr <= 3.50) or (active_hy_curr <= (active_hy_max - 0.20))
        vix_auxiliary_panic = active_vix >= 30.0

        state_color_map = {
            "NORMAL": "#00e5ff",
            "BRAKE": "#ff4500",
            "DEFENSE": "#eab308",
            "ACCELERATOR": "#00ff66",
        }
        active_color = state_color_map.get(target_state, "#00e5ff")

        # 상단 헤더
        header_col1, header_col2 = st.columns([3, 1])
        with header_col1:
            st.markdown("<h1>🧭 HYPER-INVEST V9.1.3 마스터 관제 대시보드 (Plan 3:4:5)</h1>", unsafe_allow_html=True)
            if sim_mode:
                st.markdown(
                    "<p style='font-size:13px; color:#ff4500; font-weight:bold;'>⚠️ [시뮬레이터 작동 중] 가상 주입 데이터로 V9.1.3 상태 머신을 검증하고 있습니다.</p>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<p style='font-size:13px; color:#94a3b8;'>기준일(확정봉): {last_trade_date} | 평소에는 본업에 몰입하고 금요일 분할 매수 및 공식 신호 발생 시에만 행동합니다.</p>",
                    unsafe_allow_html=True,
                )
        with header_col2:
            yr_label = "16~20년 차 (수확기)" if is_yr16_user else "1~15년 차 (적립기)"
            st.markdown(
                f"""
                <div style="text-align: right; padding: 8px 14px; background-color: #161619; border: 1px solid {active_color}; border-radius: 6px;">
                    <span style="font-size:11px; color:#94a3b8;">{yr_label} | 현재: {prev_state_user}</span><br>
                    <span style="font-size:16px; font-weight:800; color:{active_color};">
                        ➔ 목표: {target_state} ({pending_action})
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ==============================================================================
        # 7. Section 1: V9.1.3 공식 3대 트리거 + 3대 보조 매크로 지표 카드
        # ==============================================================================
        st.markdown("## 📊 1. V9.1.3 공식 시그널 & 매크로 감시 매트릭스")
        tv_chart_url = "https://kr.tradingview.com/chart/BiZbytg1/?symbol=NASDAQ%3AQQQ"

        m1, m2, m3, m4, m5, m6 = st.columns(6)

        with m1:
            is_below_3d = active_below_cnt >= 3
            trend_color = "#ff4500" if is_below_3d else ("#eab308" if active_below_cnt > 0 else "#00ff66")
            if active_below_cnt > 0:
                streak_str = f"하회 {active_below_cnt}일 연속"
            else:
                streak_str = f"상회 {active_above_cnt}일 연속"
            st.markdown(
                f"""
                <div class="metric-card" style="border-top: 3px solid {trend_color};">
                    <div class="metric-card-top">
                        <span class="metric-title">① QQQ SMA200 [메인 신호]</span>
                    </div>
                    <div style="font-size:11px; color:#94a3b8; margin-top:-4px; margin-bottom:8px; min-height:30px; line-height:1.4;">
                        🛡️ 3거래일 연속 하회 시 BRAKE<br>3일 연속 상회(&amp; RSI≥40) 복귀
                    </div>
                    <div class="metric-value" style="color:{trend_color};">{streak_str}</div>
                    <div class="metric-sub">종가 ${active_close:.2f} / 200MA ${active_sma200:.2f} ({active_200_disp:+.2f}%)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.link_button("🔍 QQQ 일봉 차트", tv_chart_url, use_container_width=True)

        with m2:
            rsi_color = "#00ff66" if active_rsi < 30.0 else ("#00e5ff" if active_rsi >= 40.0 else "#eab308")
            st.markdown(
                f"""
                <div class="metric-card" style="border-top: 3px solid {rsi_color};">
                    <div class="metric-card-top">
                        <span class="metric-title">② QQQ Wilder RSI(14) [공식]</span>
                    </div>
                    <div style="font-size:11px; color:#94a3b8; margin-top:-4px; margin-bottom:8px; min-height:30px; line-height:1.4;">
                        🎯 &lt;30.0 엑셀러 필수 조건 1<br>&ge;40.0 엑셀러 종료 및 NORMAL 복귀
                    </div>
                    <div class="metric-value" style="color:{rsi_color};">{active_rsi:.1f}</div>
                    <div class="metric-sub">주봉 RSI {raw_qqq_weekly_rsi:.1f} | ^NDX 일봉 {raw_ndx_daily_rsi:.1f}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.link_button("🔍 RSI 확인", tv_chart_url, use_container_width=True)

        with m3:
            vol_color = "#00ff66" if active_vol21 >= 25.0 else "#ffffff"
            vol_status = "⚡ 사격 조건 충족(≥25%)" if active_vol21 >= 25.0 else "평시 변동성(<25%)"
            st.markdown(
                f"""
                <div class="metric-card" style="border-top: 3px solid {vol_color};">
                    <div class="metric-card-top">
                        <span class="metric-title">③ RollVol21 [공식 변동성]</span>
                    </div>
                    <div style="font-size:11px; color:#94a3b8; margin-top:-4px; margin-bottom:8px; min-height:30px; line-height:1.4;">
                        ⚡ 21일 연율화 실현변동성<br>(&ge;25.0% &amp; RSI&lt;30 시 엑셀러 사격)
                    </div>
                    <div class="metric-value" style="color:{vol_color};">{active_vol21:.2f}%</div>
                    <div class="metric-sub">{vol_status}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.link_button("🔍 변동성 점검", tv_chart_url, use_container_width=True)

        with m4:
            vix_color = "#00ff66" if vix_auxiliary_panic else ("#eab308" if active_vix >= 20 else "#94a3b8")
            vix_status = "극단 공포(≥30)" if vix_auxiliary_panic else ("경계(20~30)" if active_vix >= 20 else "안정(<20)")
            st.markdown(
                f"""
                <div class="metric-card" style="border-top: 3px solid {vix_color};">
                    <div class="metric-card-top">
                        <span class="metric-title">④ CBOE VIX [보조 확인]</span>
                    </div>
                    <div style="font-size:11px; color:#94a3b8; margin-top:-4px; margin-bottom:8px; min-height:30px; line-height:1.4;">
                        🔍 공포 국면 교차 확인 보조지표<br>(공식 RSI+RollVol 트리거 대체 불가)
                    </div>
                    <div class="metric-value" style="color:{vix_color};">{active_vix:.2f}</div>
                    <div class="metric-sub">{vix_status} | 125MA 이격 {raw_qqq_125_disp:+.1f}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.link_button("🔍 VIX 차트", "https://finance.yahoo.com/quote/%5EVIX/chart", use_container_width=True)

        with m5:
            hy_color = "#00ff66" if hy_approved else "#ff4500"
            hy_text = "✅ 신용 안전/피크아웃" if hy_approved else "⛔ 스프레드 확대 경계"
            st.markdown(
                f"""
                <div class="metric-card" style="border-top: 3px solid {hy_color};">
                    <div class="metric-card-top">
                        <span class="metric-title">⑤ FRED 하이일드 [보조]</span>
                    </div>
                    <div style="font-size:11px; color:#94a3b8; margin-top:-4px; margin-bottom:8px; min-height:30px; line-height:1.4;">
                        🛑 부도 위험 보조 확인 지표<br>(20일 고점 대비 -0.20%p OR ≤3.50%)
                    </div>
                    <div class="metric-value" style="color:{hy_color};">{active_hy_curr:.2f}%</div>
                    <div class="metric-sub">{hy_text} (20일高 {active_hy_max:.2f}%)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.link_button("🔍 FRED 확인", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", use_container_width=True)

        with m6:
            st.markdown(
                f"""
                <div class="metric-card" style="border-top: 3px solid #00e5ff;">
                    <div class="metric-card-top">
                        <span class="metric-title">⑥ 금리 · 달러 · 심리 [보조]</span>
                    </div>
                    <div style="font-size:11px; color:#94a3b8; margin-top:-4px; margin-bottom:8px; min-height:30px; line-height:1.4;">
                        🌐 10Y 금리 · DXY · PCR · F&amp;G<br>(거시 유동성 및 패닉 보조 지표)
                    </div>
                    <div class="metric-value" style="font-size:18px; color:#ffffff;">{active_tnx:.2f}% / {active_dxy:.1f}</div>
                    <div class="metric-sub">PCR {active_pcr:.2f} | F&amp;G {active_fg:.0f}점</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.link_button("🔍 10Y 금리", "https://finance.yahoo.com/quote/%5ETNX", use_container_width=True)

        # ==============================================================================
        # 8. Section 2: V9.1.3 공식 상태 판정 및 3단계 표준 보고서 (Action Directive)
        # ==============================================================================
        st.markdown("---")
        st.markdown("## 🎯 2. V9.1.3 시스템 상태 판정 및 실전 행동 지침 (Action Directive)")

        if target_state == "BRAKE":
            st.error(f"### 🔴 [BRAKE 모드 (1~15년 차 하락 방어) | 예약 액션: {pending_action}]")
            st.markdown(
                f"""
                <div class="context-box" style="border-color: #ff4500;">
                    <b>1단계 [현재 지표 상태]:</b> QQQ 종가(${active_close:.2f})가 200일선(${active_sma200:.2f}) 아래에 위치 (연속 하회 {active_below_cnt}거래일, RSI {active_rsi:.1f}, RollVol21 {active_vol21:.2f}%).<br>
                    <b>2단계 [교차 검증 결과]:</b> 1~15년 차 적립기 하락장 방어 모드입니다. 대바닥 사격 조건(RSI &lt; 30 &amp; RollVol21 &ge; 25%) 및 정상 복귀 조건(200MA 3일 연속 상회 &amp; RSI &ge; 40) 미충족.<br>
                    <b>3단계 [3:4:5 계좌별 행동]:</b><br>
                    • <b>개인연금(월 30만):</b> 보유 주식 전량 매도 ➔ <b>KODEX 머니마켓액티브 100%</b> 대피 (하락장 중 신규 납입금도 머니마켓 100% 매수)<br>
                    • <b>국내 ISA(월 40만):</b> <b>1배수(50%) HODL 유지</b>, 2배수(TIGER 레버리지 40%) 전량 매도 ➔ 머니마켓/현금 50% 대피 (신규 납입금도 1배 50% : 현금 50%)<br>
                    • <b>해외직투(월 50만):</b> 22% 양도세 방어를 위해 <b>QQQ(50%)는 단 1주도 팔지 않고 영구 HODL</b>, 오직 QLD(40%)만 전량 매도하여 달러/SGOV 50% 대피
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif target_state == "DEFENSE":
            st.warning(f"### 🟡 [DEFENSE 모드 (16~20년 차 수확기 절대 요새화) | 예약 액션: {pending_action}]")
            st.markdown(
                f"""
                <div class="context-box" style="border-color: #eab308;">
                    <b>1단계 [현재 지표 상태]:</b> 16년 차 이후 수확기 구간(d &ge; 3,780)에서 QQQ 종가(${active_close:.2f})가 200일선(${active_sma200:.2f}) 하회 (연속 하회 {active_below_cnt}일).<br>
                    <b>2단계 [교차 검증 결과]:</b> [PATCH A 작동] 은퇴 직전 시퀀스 리스크 차단을 위해 절세 계좌를 20/80 방어 요새로 전환합니다.<br>
                    <b>3단계 [3:4:5 계좌별 행동]:</b><br>
                    • <b>개인연금(월 30만):</b> 보유 주식 전량 매도 ➔ <b>KODEX 머니마켓액티브 100%</b> 요새화<br>
                    • <b>국내 ISA(월 40만):</b> <b>1배수를 계좌의 20%로 긴급 축소</b>, 2배수 0% 전량 매도 ➔ <b>머니마켓/현금성 80%</b> 절대 요새화 (신규 납입금도 1배 20% : 현금 80%)<br>
                    • <b>해외직투(월 50만):</b> 양도세 조기 유출 차단을 위해 <b>QQQ(50%) 영구 HODL 유지</b>, QLD(40%)만 전량 달러/SGOV로 대피
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif target_state == "ACCELERATOR":
            st.success(f"### ⚡ [ACCELERATOR 모드 (대바닥 70% 집중 사격) | 예약 액션: {pending_action}]")
            st.markdown(
                f"""
                <div class="context-box" style="border-color: #00ff66;">
                    <b>1단계 [현재 지표 상태]:</b> Wilder 일봉 RSI(<b>{active_rsi:.1f}</b> &lt; 30.0) AND 21일 실현변동성 RollVol21(<b>{active_vol21:.2f}%</b> &ge; 25.0%) 공식 트리거 동시 충족!<br>
                    <b>2단계 [교차 검증 결과]:</b> 보조 지표 VIX({active_vix:.2f}) 및 하이일드 스프레드({active_hy_curr:.2f}%, {'승인' if hy_approved else '경계'}) 확인. RSI 40 이상 회복 전까지 가속 상태를 유지합니다.<br>
                    <b>3단계 [3:4:5 계좌별 행동]:</b><br>
                    • <b>공식 실행 원칙:</b> 신호 발생 <b>익일 시가(Open[d+1])에 각 계좌 보유 현금/달러 실탄의 70%를 일괄 사격</b>합니다 (잔여 30% 현금은 추가 하락 대비 보존).<br>
                    • <b>개인연금:</b> 머니마켓 현금 잔액의 70%로 연금 주식(빅테크7 70 : 나스닥100 30) 재매수<br>
                    • <b>국내 ISA:</b> 현금성 잔액의 70%로 <b>TIGER 미국나스닥100레버리지(2배)</b> 집중 매수<br>
                    • <b>해외직투:</b> 외화예수금/SGOV 잔액의 70%로 <b>QLD(2배)</b> 집중 매수
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info(f"### 🟢 [NORMAL 모드 (평상시 정률 적립 & 포메이션 유지) | 예약 액션: {pending_action}]")
            st.markdown(
                f"""
                <div class="context-box" style="border-color: #00e5ff;">
                    <b>1단계 [현재 지표 상태]:</b> QQQ 종가(${active_close:.2f})가 200일선(${active_sma200:.2f}) 상단 유지 (연속 상회 {active_above_cnt}일, RSI {active_rsi:.1f}, RollVol21 {active_vol21:.2f}%).<br>
                    <b>2단계 [교차 검증 결과]:</b> 정상 상승 추세입니다. {('하락장에서 정상 복귀(TO_NORMAL) 조건이 충족되어 익일 시가에 50:40:10 포메이션을 정밀 복원합니다.' if pending_action == 'TO_NORMAL' else '신호 알림이 올 때까지 계좌 앱을 끄고 본업에 몰입하십시오.')}<br>
                    <b>3단계 [3:4:5 계좌별 행동]:</b><br>
                    • <b>평상시 정기 적립:</b> 매월 25일 총 120만 원(30/40/50만) 이체 후 <b>매주 금요일 4회 분할 매수</b>.<br>
                    • <b>TO_NORMAL 복귀 시 [PATCH E]:</b> 개인연금 현금 전량 주식 매수 / 국내 ISA는 <b>1배수(50%)까지 우선 복원한 뒤 잔여 현금으로 2배수(40%) 복원</b> / 해외직투는 달러에서 QLD 40%까지 재매수.
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ==============================================================================
        # 9. Section 3: 3:4:5 계좌별 월간/주간 정기 적립 주문표 & 리밸런싱 계산기
        # ==============================================================================
        st.markdown("---")
        st.markdown("## 💼 3. Plan 3:4:5 계좌별 정기 적립 주문표 & 리밸런싱 실전 계산기")

        contrib_guide = compute_monthly_contribution_guide(target_state, float(monthly_budget_krw))
        rebal_plan = compute_account_rebalance_plan(
            target_state=target_state,
            pen_eq=float(user_pen_eq),
            pen_ca=float(user_pen_ca),
            isa_1x=float(user_isa_1x),
            isa_2x=float(user_isa_2x),
            isa_ca=float(user_isa_ca),
            ov_q=float(user_ov_q),
            ov_qld=float(user_ov_qld),
            ov_s=float(user_ov_s),
        )

        col_acc1, col_acc2, col_acc3 = st.columns(3)

        with col_acc1:
            pen_m = contrib_guide["pmt_pen"]
            pen_items_html = "".join(
                [f"• <b>{k}:</b> 월 {v:,.0f}원 (금요일 주간 <b>{v/4.0:,.0f}원</b>)<br>" for k, v in contrib_guide["pen_alloc"].items()]
            )
            st.markdown(
                f"""
                <div class="portfolio-card" style="border-top: 4px solid #00e5ff;">
                    <div class="portfolio-card-header" style="color: #00e5ff;">
                        <span>① 개인연금 (삼성증권)</span>
                        <span style="font-size:12px; color:#94a3b8;">월 {pen_m:,.0f}원 (25.0%)</span>
                    </div>
                    <div class="portfolio-card-desc">현재 총 평가액: {rebal_plan['pen']['total']:,.0f}원 (주식 {user_pen_eq:,.0f} / 현금 {user_pen_ca:,.0f})</div>
                    <div class="portfolio-card-content">
                        <div style="font-weight:bold; color:#00e5ff; margin-bottom:6px;">📅 [{target_state}] 월간/금요일 적립 가이드</div>
                        {pen_items_html}
                        <hr style="border-color:#2d2d34; margin:10px 0;">
                        <div style="font-size:12.5px; color:#cbd5e1;">
                            <b>🔄 상태 전환 리밸런싱 지침:</b><br>
                            • {rebal_plan['order_desc']['pen']}<br>
                            • <b>목표 잔액:</b> 주식 <b>{rebal_plan['pen']['eq']:,.0f}원</b> / 머니마켓 <b>{rebal_plan['pen']['ca']:,.0f}원</b>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_acc2:
            isa_m = contrib_guide["pmt_isa"]
            isa_items_html = "".join(
                [f"• <b>{k}:</b> 월 {v:,.0f}원 (금요일 주간 <b>{v/4.0:,.0f}원</b>)<br>" for k, v in contrib_guide["isa_alloc"].items()]
            )
            st.markdown(
                f"""
                <div class="portfolio-card" style="border-top: 4px solid #a855f7;">
                    <div class="portfolio-card-header" style="color: #c084fc;">
                        <span>② 중개형 ISA (NH투자증권)</span>
                        <span style="font-size:12px; color:#94a3b8;">월 {isa_m:,.0f}원 (33.3%)</span>
                    </div>
                    <div class="portfolio-card-desc">현재 총 평가액: {rebal_plan['isa']['total']:,.0f}원 (1배 {user_isa_1x:,.0f} / 2배 {user_isa_2x:,.0f} / 현금 {user_isa_ca:,.0f})</div>
                    <div class="portfolio-card-content">
                        <div style="font-weight:bold; color:#c084fc; margin-bottom:6px;">📅 [{target_state}] 월간/금요일 적립 가이드</div>
                        {isa_items_html}
                        <hr style="border-color:#2d2d34; margin:10px 0;">
                        <div style="font-size:12.5px; color:#cbd5e1;">
                            <b>🔄 상태 전환 리밸런싱 지침:</b><br>
                            • {rebal_plan['order_desc']['isa']}<br>
                            • <b>목표 잔액:</b> 1배 <b>{rebal_plan['isa']['1x']:,.0f}원</b> / 2배 <b>{rebal_plan['isa']['2x']:,.0f}원</b> / 현금성 <b>{rebal_plan['isa']['ca']:,.0f}원</b>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_acc3:
            ov_m = contrib_guide["pmt_ov"]
            ov_items_html = "".join(
                [f"• <b>{k}:</b> 월 {v:,.0f}원 (금요일 주간 <b>{v/4.0:,.0f}원</b>)<br>" for k, v in contrib_guide["ov_alloc"].items()]
            )
            st.markdown(
                f"""
                <div class="portfolio-card" style="border-top: 4px solid #ff3366;">
                    <div class="portfolio-card-header" style="color: #ff3366;">
                        <span>③ 해외직투 (토스증권)</span>
                        <span style="font-size:12px; color:#94a3b8;">월 {ov_m:,.0f}원 (41.7%)</span>
                    </div>
                    <div class="portfolio-card-desc">현재 총 평가액: ${rebal_plan['ov']['total']:,.1f} (QQQ ${user_ov_q:,.0f} / QLD ${user_ov_qld:,.0f} / 달러 ${user_ov_s:,.0f})</div>
                    <div class="portfolio-card-content">
                        <div style="font-weight:bold; color:#ff3366; margin-bottom:6px;">📅 [{target_state}] 월간/금요일 적립 가이드</div>
                        {ov_items_html}
                        <hr style="border-color:#2d2d34; margin:10px 0;">
                        <div style="font-size:12.5px; color:#cbd5e1;">
                            <b>🔄 상태 전환 리밸런싱 지침:</b><br>
                            • {rebal_plan['order_desc']['ov']}<br>
                            • <b>목표 잔액:</b> QQQ <b>${rebal_plan['ov']['q']:,.1f}</b> / QLD <b>${rebal_plan['ov']['qld']:,.1f}</b> / 달러 <b>${rebal_plan['ov']['s']:,.1f}</b>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ==============================================================================
        # 10. Section 4: 보조 지표 상세 및 공식 데이터 소스 다이렉트 라우팅
        # ==============================================================================
        st.markdown("---")
        st.subheader("🛡️ 4. 보조 확인 지표 스캐닝 및 원천 데이터 교차 검증 (Cross-Check)")
        with st.expander("🔍 보조 지표 상세 판독 (공식 상태 전이 규칙을 대체하지 않음)", expanded=True):
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                st.markdown("##### 1. 공식 엑셀러 트리거 vs 보조 지표 교차 대사")
                accel_official_ok = (active_rsi < 30.0) and (active_vol21 >= 25.0)
                st.markdown(
                    f"   * **공식 시스템 트리거 (`RSI < 30` & `RollVol21 ≥ 25%`):** "
                    f"{'🟢 **충족 (사격 조건 성립)**' if accel_official_ok else '⚪ **미충족 (대기)**'} "
                    f"(현재 RSI `{active_rsi:.1f}`, RollVol21 `{active_vol21:.2f}%`)"
                )
                st.markdown(
                    f"   * **보조 지표 1 (`CBOE VIX ≥ 30`):** "
                    f"{'🟢 공포 확인' if vix_auxiliary_panic else '⚪ 평시 수준'} (현재 VIX `{active_vix:.2f}`)"
                )
                st.markdown(
                    f"   * **보조 지표 2 (`풋콜레이시오 PCR ≥ 1.10`):** "
                    f"{'🟢 극단 풋 쏠림 확인' if active_pcr >= 1.10 else '⚪ 안정 수준'} (현재 PCR `{active_pcr:.2f}`)"
                )
            with col_v2:
                st.markdown("##### 2. 신용 스프레드 및 거시 유동성 보조 확인")
                if active_hy_curr <= 3.50:
                    st.markdown(f"   * ✅ **FRED 하이일드:** 현재 `{active_hy_curr:.2f}%` (≤ 3.50% 신용 안전존).")
                elif (active_hy_max - active_hy_curr) >= 0.20:
                    st.markdown(
                        f"   * ✅ **FRED 하이일드:** 20일 고점(`{active_hy_max:.2f}%`) 대비 `-{(active_hy_max - active_hy_curr):.2f}%p` 피크아웃 확인."
                    )
                else:
                    st.markdown(
                        f"   * ⚠️ **FRED 하이일드:** 현재 `{active_hy_curr:.2f}%` (20일 고점 `{active_hy_max:.2f}%` 대비 피크아웃 미확인)."
                    )
                fg_label = (
                    "극단적 공포(<25)"
                    if active_fg < 25
                    else ("공포" if active_fg <= 45 else ("중립" if active_fg <= 55 else "탐욕"))
                )
                st.markdown(f"   * 🧭 **CNN Fear & Greed:** `{active_fg:.1f}점` ({fg_label}) | **QQQ 거래량 폭발(1.5x):** `{'발생' if raw_vol_surge else '미발생'}`")

        dl1, dl2, dl3, dl4, dl5 = st.columns(5)
        with dl1:
            st.link_button("🔵 FRED 하이일드", "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", use_container_width=True)
        with dl2:
            st.link_button("🟢 CBOE 옵션 통계", "https://www.cboe.com/markets/us/options/market-statistics/daily", use_container_width=True)
        with dl3:
            st.link_button("🔴 CNN Fear & Greed", "https://edition.cnn.com/markets/fear-and-greed", use_container_width=True)
        with dl4:
            st.link_button("🟣 Yahoo QQQ 시세", "https://finance.yahoo.com/quote/QQQ", use_container_width=True)
        with dl5:
            st.link_button("🟠 TradingView 차트", tv_chart_url, use_container_width=True)

        st.markdown("---")
        with st.expander("📖 [HYPER-INVEST V9.1.3 실전 운용 백서 · 슬림판] 핵심 규칙 및 검증 경계 요약", expanded=False):
            st.markdown(
                """
                #### 1. V9.1.3 (Plan 3:4:5) 확정 규칙 요약
                - **월 적립 구조:** 매월 25일 120만 원 이체 (개인연금 30만 / 중개형 ISA 40만 / 해외직투 50만), 매주 금요일 분할 매수.
                - **메인 신호 (QQQ 일봉 SMA200):** 확정 종가가 3거래일 연속 하회 시 `BRAKE` (16년 차 `d ≥ 3780` 이후는 `DEFENSE`).
                - **ACCELERATOR (대바닥 사격):** `BRAKE`/`DEFENSE` 상태 중 `Wilder RSI(14) < 30.0 AND RollVol21 ≥ 25.0%` 충족 시 익일 시가에 각 계좌 보유 현금/달러 실탄의 **70%** 투입.
                - **ACCELERATOR 종료 및 NORMAL 복귀:** `RSI(14) ≥ 40.0` 도달 시 가속 종료. 이때 `QQQ 종가 ≥ SMA200` 3거래일 연속 마감이면 `NORMAL` 복귀(ISA 1배수 50% 우선 복원 후 2배수 40% 순차 복원), 아니면 `BRAKE`(`16년 차~ DEFENSE`) 복귀.
                - **기준선 재현 수치 (2006-06-21 ~ 2026-09-04, 5,069거래일, 원금 2.904억 원):** 세전 평가액 `2,591,785,477원` (세전 XIRR `18.70%`), 세후 청산 순자산 `2,358,463,750원` (세후 XIRR `17.95%`), TWR CAGR `16.07%`, TWR MDD `-41.45%`, 매매 이벤트 `192회`.
                - **주의사항:** 위 성과 수치는 단순화된 모델 가정 아래 재현된 과거 참고치이며, 미래 수익이나 세법상 확정 신고세액·은퇴자금 30년 충분성을 보증하지 않습니다.
                """
            )

    render_master_dashboard()


if __name__ == "__main__":
    if HAS_STREAMLIT:
        render_master_app()
