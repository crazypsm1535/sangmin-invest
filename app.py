import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# --- 세션 생성 함수 (Yahoo Finance 블로킹 방지) ---
def get_session():
    session = requests.Session()
    # 웹 브라우저 헤더 위장
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            )
        }
    )
    # 네트워크 에러 발생 시 자동 3회 재시도
    retries = Retry(
        total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


# --- 개선된 실시간 데이터 수집 엔진 ---
@st.cache_data(ttl=30)  # 캐시 주기를 30초로 설정하여 과도한 요청 방지
def get_market_data():
    try:
        session = get_session()
        # V8.1 기준 필수 티커 일괄 수집 (QLD 포함)
        tickers = ["QLD", "^NDX", "^GSPC", "^VIX", "QQQ"]

        # 단 한 번의 네트워크 요청으로 일괄 다운로드 (timeout 설정)
        data = yf.download(
            tickers,
            period="1y",
            progress=False,
            group_by="ticker",
            session=session,
            timeout=10,
        )

        if data.empty:
            return None

        # 데이터 프레임 정밀 추출
        df = pd.DataFrame(index=data.index)
        df["QLD_Close"] = data["QLD"]["Close"]
        df["NDX_Close"] = data["^NDX"]["Close"]
        df["SP500_Close"] = data["^GSPC"]["Close"]
        df["VIX_Close"] = data["^VIX"]["Close"]
        df["Volume"] = data["QQQ"]["Volume"]

        # 결측치 보정 (주말/공휴일 등)
        df = df.ffill().dropna()

        # 이동평균 및 RSI 수치 연산
        df["QLD_200SMA"] = df["QLD_Close"].rolling(window=200).mean()  # V8.1 기준
        df["NDX_125EMA"] = df["NDX_Close"].ewm(span=125, adjust=False).mean()
        df["NDX_50EMA"] = df["NDX_Close"].ewm(span=50, adjust=False).mean()
        df["SP500_200EMA"] = df["SP500_Close"].ewm(span=200, adjust=False).mean()
        df["NDX_RSI"] = calculate_rsi(df["NDX_Close"])
        df["Vol_20MA"] = df["Volume"].rolling(window=20).mean()

        return df.dropna()

    except Exception as e:
        # 에러 발생 시 콘솔 로그 출력 후 None 반환 (수동 모드 유연 전환)
        print(f"Data fetch error: {e}")
        return None