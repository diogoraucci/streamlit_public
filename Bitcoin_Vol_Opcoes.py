import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# ===================== CONFIGURAÇÃO =====================
st.set_page_config(page_title="BTC/USDT - Preço em Tempo Real", layout="wide")
st.title("Bitcoin (BTC/USDT) - Gráfico Diário")
st.markdown("**Fonte automática**: Binance → Yahoo Finance se Binance estiver bloqueada")

# ===================== FUNÇÃO QUE NUNCA FALHA =====================
@st.cache_data(ttl=180, show_spinner="Carregando dados do BTC...")
def get_btc_data(start_date: str, end_date: str = None):
    # 1. Tenta Binance com vários endpoints (resolve 451)
    endpoints = [
        "https://api1.binance.com/api/v3/klines",
        "https://api2.binance.com/api/v3/klines",
        "https://api3.binance.com/api/v3/klines",
        "https://api4.binance.com/api/v3/klines",
    ]

    start_ms = int(pd.to_datetime(start_date).timestamp() * 1000)
    end_ms = int(pd.to_datetime(end_date or "today").timestamp() * 1000) + 86400000
    limit = 1000

    for url in endpoints:
        try:
            data = []
            start = start_ms
            while start < end_ms:
                params = {
                    "symbol": "BTCUSDT",
                    "interval": "1d",
                    "startTime": start,
                    "endTime": end_ms,
                    "limit": limit
                }
                r = requests.get(url, params=params, timeout=10)
                if r.status_code == 451:
                    break 451  # bloqueado, pula pro próximo
                    break
                r.raise_for_status()
                batch = r.json()
                if not batch:
                    break
                data.extend(batch)
                start = batch[-1][0] + 1

            if data:
                df = pd.DataFrame(data, columns=["timestamp","open","high","low","close","volume","close_time","a","b","c","d","e"])
                df = df[["timestamp","open","high","low","close","volume"]]
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)
                df = df.astype(float).round(2)
                df = df[~df.index.duplicated(keep='first')]
                return df.sort_index()

        except:
            continue  # tenta próximo endpoint

    # 2. Se todos da Binance falharem → Yahoo Finance (sempre funciona)
    st.warning("Binance bloqueada (erro 451). Usando Yahoo Finance como backup...")
    try:
        import yfinance as yf
        df_yf = yf.download("BTC-USD", start=start_date, end=end_date or None, progress=False)
        if not df_yf.empty:
            df_yf = df_yf[["Open", "High", "Low", "Close", "Volume"]].round(2)
            df_yf.columns = ["open", "high", "low", "close", "volume"]
            return df_yf
    except:
        pass

    # 3. Se tudo der errado
    st.error("Não foi possível carregar dados de nenhuma fonte.")
    return pd.DataFrame()

# ===================== INTERFACE =====================
col1, col2 = st.columns([2, 1])

with col1:
    data_inicio = st.date_input("Data inicial", value=pd.to_datetime("2024-01-01"), key="inicio")

with col2:
    data_fim = st.date_input("Data final (opcional)", value=pd.to_datetime("today"), key="fim")

if st.button("Carregar Gráfico BTC/USDT", type="primary"):
    df = get_btc_data(
        start_date=data_inicio.strftime("%Y-%m-%d"),
        end_date=data_fim.strftime("%Y-%m-%d") if data_fim else None
    )

    if df.empty or len(df) == 0:
        st.error("Nenhum dado retornado. Tente outra data.")
        st.stop()

    st.success(f"Dados carregados: {len(df)} dias | Último preço: ${df['close'].iloc[-1]:,.2f}")

    # Gráfico Candlestick
    fig = go.Figure(data=go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name="BTC/USDT"
    ))

    fig.update_layout(
        title="BTC/USDT - Candlestick Diário",
        xaxis_title="Data",
        yaxis_title="Preço (USD)",
        template="plotly_dark",
        height=700,
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # Tabela + Download
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.subheader("Últimos 30 dias")
        st.dataframe(df.tail(30)[["open","high","low","close","volume"]], use_container_width=True)

    with col_b:
        st.subheader("Download")
        csv = df.to_csv().encode()
        st.download_button(
            "Baixar CSV completo",
            data=csv,
            file_name=f"BTCUSDT_{data_inicio}_to_{data_fim or 'hoje'}.csv",
            mime="text/csv"
        )
