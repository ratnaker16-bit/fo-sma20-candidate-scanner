import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="F&O SMA20 Candidate Scanner",
    page_icon="📊",
    layout="wide"
)

st.title("📊 F&O SMA20 Candidate Scanner")

st.caption(
    "2-Minute & 5-Minute Candle Breakout / Breakdown Scanner"
)

# ============================================================
# F&O STOCK LIST
# ============================================================

FO_STOCKS = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT",
    "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE",
    "BEL", "BHARTIARTL", "BOSCHLTD", "BPCL",
    "BRITANNIA", "CIPLA", "COALINDIA", "COLPAL",
    "DRREDDY", "EICHERMOT", "ETERNAL", "EXIDEIND",
    "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE",
    "HEROMOTOCO", "HINDALCO", "HINDPETRO", "HINDUNILVR",
    "ICICIBANK", "ICICIGI", "ICICIPRULI", "INDHOTEL",
    "INDUSINDBK", "INFY", "IOC", "ITC",
    "JINDALSTEL", "JIOFIN", "JSWSTEEL", "KOTAKBANK",
    "LAURUSLABS", "LICHSGFIN", "LT", "LTIM",
    "M&M", "MANAPPURAM", "MARUTI", "MAXHEALTH",
    "MCX", "METROPOLIS", "MFSL", "MGL",
    "MOTHERSON", "MUTHOOTFIN", "NATIONALUM", "NAUKRI",
    "NESTLEIND", "NHPC", "NMDC", "NTPC",
    "NYKAA", "ONGC", "PAGEIND", "PATANJALI",
    "PAYTM", "PEL", "PERSISTENT", "PETRONET",
    "PFC", "PHOENIXLTD", "PIDILITIND", "PIIND",
    "PNB", "POLYCAB", "POWERGRID", "PRESTIGE",
    "RBLBANK", "RECLTD", "RELIANCE", "SAIL",
    "SBICARD", "SBILIFE", "SBIN", "SHREECEM",
    "SHRIRAMFIN", "SIEMENS", "SOLARINDS", "SONACOMS",
    "SRF", "SUNPHARMA", "SUPREMEIND", "SYNGENE",
    "TATACHEM", "TATACONSUM", "TATAELXSI", "TATAMOTORS",
    "TATAPOWER", "TATASTEEL", "TCS", "TECHM",
    "TIINDIA", "TITAN", "TORNTPHARM", "TORNTPOWER",
    "TRENT", "TVSMOTOR", "ULTRACEMCO", "UNOMINDA",
    "UPL", "VEDL", "VOLTAS", "WIPRO",
    "YESBANK", "ZYDUSLIFE"
]

# ============================================================
# SETTINGS
# ============================================================

MIN_BODY_PERCENT = 50.0

# ============================================================
# SAFE TICKER
# ============================================================

def get_ticker(symbol):
    return f"{symbol}.NS"


# ============================================================
# DOWNLOAD DATA
# ============================================================

@st.cache_data(ttl=60, show_spinner=False)
def download_data(symbol, interval):

    ticker = get_ticker(symbol)

    try:
        df = yf.download(
            ticker,
            period="5d",
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False
        )

        if df is None or df.empty:
            return pd.DataFrame()

        # -----------------------------------------
        # Handle MultiIndex columns
        # -----------------------------------------
        if isinstance(df.columns, pd.MultiIndex):

            try:
                df.columns = df.columns.get_level_values(0)
            except Exception:
                df.columns = [
                    col[0] if isinstance(col, tuple) else col
                    for col in df.columns
                ]

        # -----------------------------------------
        # Standardize column names
        # -----------------------------------------
        df.columns = [
            str(col).strip().capitalize()
            for col in df.columns
        ]

        required = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        for col in required:
            if col not in df.columns:
                return pd.DataFrame()

        df = df[required].copy()

        # -----------------------------------------
        # Numeric conversion
        # -----------------------------------------
        for col in required:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        df = df.dropna(
            subset=[
                "Open",
                "High",
                "Low",
                "Close"
            ]
        )

        return df

    except Exception:
        return pd.DataFrame()


# ============================================================
# SMA20 CALCULATION
# ============================================================

def calculate_sma20(df):

    df = df.copy()

    df["SMA20_High"] = (
        df["High"]
        .rolling(20)
        .mean()
    )

    df["SMA20_Low"] = (
        df["Low"]
        .rolling(20)
        .mean()
    )

    return df


# ============================================================
# BODY PERCENTAGE
# ============================================================

def candle_body_percent(row):

    candle_range = row["High"] - row["Low"]

    if candle_range <= 0:
        return 0.0

    body = abs(
        row["Close"] - row["Open"]
    )

    return (
        body / candle_range
    ) * 100.0


# ============================================================
# SCAN TIMEFRAME
# ============================================================

def scan_timeframe(symbol, interval):

    df = download_data(
        symbol,
        interval
    )

    if df.empty:
        return None

    if len(df) < 21:
        return None

    df = calculate_sma20(df)

    # -----------------------------------------
    # Latest completed candle
    # -----------------------------------------
    row = df.iloc[-1]

    if pd.isna(row["SMA20_High"]) or pd.isna(
        row["SMA20_Low"]
    ):
        return None

    open_price = float(row["Open"])
    high_price = float(row["High"])
    low_price = float(row["Low"])
    close_price = float(row["Close"])

    sma20_high = float(row["SMA20_High"])
    sma20_low = float(row["SMA20_Low"])

    body_percent = candle_body_percent(row)

    # ========================================================
    # BREAKOUT
    # Candle closes above SMA20 High
    # ========================================================

    breakout = (
        close_price > sma20_high
        and body_percent >= MIN_BODY_PERCENT
    )

    # ========================================================
    # BREAKDOWN
    # Candle closes below SMA20 Low
    # ========================================================

    breakdown = (
        close_price < sma20_low
        and body_percent >= MIN_BODY_PERCENT
    )

    # ========================================================
    # NO SIGNAL
    # ========================================================

    if not breakout and not breakdown:
        return None

    # ========================================================
    # SIGNAL
    # ========================================================

    if breakout:

        signal = "BUY"
        level = sma20_high

        distance_percent = (
            (close_price - sma20_high)
            / sma20_high
        ) * 100

    else:

        signal = "SELL"
        level = sma20_low

        distance_percent = (
            (sma20_low - close_price)
            / sma20_low
        ) * 100

    # ========================================================
    # CANDLE TIME
    # ========================================================

    candle_time = df.index[-1]

    # Convert timezone-aware timestamp safely
    try:

        if hasattr(candle_time, "tz") and candle_time.tz is not None:
            candle_time = candle_time.tz_convert(
                "Asia/Kolkata"
            )

    except Exception:
        pass

    # ========================================================
    # SIGNAL KEY
    # ========================================================

    signal_key = (
        f"{symbol}_{interval}_"
        f"{candle_time}_{signal}"
    )

    # ========================================================
    # RESULT
    # ========================================================

    return {
        "Symbol": symbol,
        "Timeframe": interval,
        "Signal": signal,
        "Candle Time": candle_time,
        "Open": round(open_price, 2),
        "High": round(high_price, 2),
        "Low": round(low_price, 2),
        "Close": round(close_price, 2),
        "SMA20 High": round(sma20_high, 2),
        "SMA20 Low": round(sma20_low, 2),
        "Body %": round(body_percent, 2),
        "Breakout/Breakdown %": round(
            distance_percent,
            2
        ),
        "Signal Key": signal_key
    }


# ============================================================
# SCAN ALL STOCKS
# ============================================================

def run_scan(interval):

    signals = []

    progress = st.progress(
        0,
        text=f"Scanning {interval}..."
    )

    total = len(FO_STOCKS)

    for i, symbol in enumerate(FO_STOCKS):

        result = scan_timeframe(
            symbol,
            interval
        )

        if result is not None:
            signals.append(result)

        progress.progress(
            (i + 1) / total,
            text=f"{interval}: {symbol}"
        )

    progress.empty()

    return signals


# ============================================================
# DISPLAY SIGNALS
# ============================================================

def display_signals(signals, title):

    st.subheader(title)

    if not signals:

        st.info(
            "अभी कोई नया candidate नहीं मिला।"
        )

        return

    df = pd.DataFrame(signals)

    # -----------------------------------------
    # Candle Time - SAFE FORMAT
    # -----------------------------------------

    if "Candle Time" in df.columns:

        df["Candle Time"] = pd.to_datetime(
            df["Candle Time"],
            errors="coerce"
        )

        # Series के लिए .dt जरूरी है
        df["Candle Time"] = (
            df["Candle Time"]
            .dt.strftime("%d-%m-%Y %H:%M")
        )

    # -----------------------------------------
    # Latest signal first
    # -----------------------------------------

    if "Candle Time" in df.columns:

        df = df.sort_values(
            by="Candle Time",
            ascending=False
        )

    # -----------------------------------------
    # Internal column hide
    # -----------------------------------------

    if "Signal Key" in df.columns:

        df = df.drop(
            columns=["Signal Key"]
        )

    # -----------------------------------------
    # Display
    # -----------------------------------------

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    # -----------------------------------------
    # CSV Download
    # -----------------------------------------

    csv = df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="⬇️ Download CSV",
        data=csv,
        file_name=(
            f"{title.replace(' ', '_')}.csv"
        ),
        mime="text/csv",
        key=(
            f"download_"
            f"{title.replace(' ', '_')}"
        )
    )


# ============================================================
# MAIN CONTROLS
# ============================================================

st.sidebar.header("⚙️ Scanner Settings")

min_body = st.sidebar.number_input(
    "Minimum Candle Body %",
    min_value=1.0,
    max_value=100.0,
    value=50.0,
    step=1.0
)

MIN_BODY_PERCENT = min_body

st.sidebar.write(
    f"F&O Stocks: {len(FO_STOCKS)}"
)

st.sidebar.write(
    "2m + 5m SMA20 Breakout / Breakdown"
)

# ============================================================
# SCAN BUTTON
# ============================================================

if st.button(
    "🔄 Run Scanner",
    use_container_width=True
):

    # ========================================================
    # 2 MINUTE
    # ========================================================

    with st.spinner(
        "2-Minute scan चल रहा है..."
    ):

        signals_2m = run_scan(
            "2m"
        )

    display_signals(
        signals_2m,
        "⏱️ 2-Minute Signals"
    )

    st.divider()

    # ========================================================
    # 5 MINUTE
    # ========================================================

    with st.spinner(
        "5-Minute scan चल रहा है..."
    ):

        signals_5m = run_scan(
            "5m"
        )

    display_signals(
        signals_5m,
        "⏱️ 5-Minute Signals"
    )

else:

    st.info(
        "Scanner शुरू करने के लिए "
        "ऊपर **🔄 Run Scanner** button दबाएँ।"
    )
