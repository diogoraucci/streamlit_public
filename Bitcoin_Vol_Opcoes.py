import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go


# =============================================================================
# FUNÇÃO PRINCIPAL — COLETA BINANCE COM PROTEÇÃO REAL CONTRA 429 / -1003 / -1
# =============================================================================
def cotacao_binance(symbol, interval, start_str, end_str=None):

    base_url = "https://api.binance.com/api/v3/klines"
    data = []
    limit = 1000  # máximo que a Binance permite por requisição

    start_ts = int(datetime.strptime(start_str, "%Y-%m-%d").timestamp() * 1000)
    end_ts = (
        int(datetime.now().timestamp() * 1000)
        if end_str is None
        else int(datetime.strptime(end_str, "%Y-%m-%d").timestamp() * 1000)
    )

    while start_ts < end_ts:

        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ts,
            "limit": limit
        }

        # ---------------------------------------------------------------------
        # RETRIES — Tratamento de 429, -1003, -1, timeout, resposta quebrada
        # ---------------------------------------------------------------------
        for retry in range(10):

            try:
                r = requests.get(base_url, params=params, timeout=10)

                # Erro Binance típico
                if r.status_code == 429:
                    time.sleep(1.0 * (retry + 1))
                    continue

                # Erro -1003 ou -1
                j = r.json()
                if isinstance(j, dict) and j.get("code") in [-1003, -1]:
                    time.sleep(1.2 * (retry + 1))
                    continue

                # sucesso ⇒ sai do retry
                break

            except:
                time.sleep(1.0 * (retry + 1))

        # se falhar até o último retry
        if r.status_code != 200:
            raise Exception(f"Erro ao conectar na Binance: {r.status_code}")

        try:
            temp = r.json()
        except:
            break

        if not isinstance(temp, list) or len(temp) == 0:
            break  # acabou dados

        data.extend(temp)

        # avança timestamp
        start_ts = temp[-1][6] + 1

    # Montagem final
    df = montar_dataframe(data, start_str, end_str, symbol, interval)
    return df


# =============================================================================
# MONTA DATAFRAME FINAL
# =============================================================================
def montar_dataframe(data, start_str, end_str, symbol, interval):

    if len(data) == 0:
        return pd.DataFrame(columns=["open","high","low","close","volume"])

    df = pd.DataFrame(data, columns=[
        "timestamp","open","high","low","close","volume","close_time",
        "quote_asset_volume","number_of_trades",
        "taker_buy_base_asset_volume","taker_buy_quote_asset_volume","ignore"
    ])

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df[["open","high","low","close","volume"]].astype(float)

    # Ajuste final
    if end_str:
        end_date = pd.to_datetime(end_str) + timedelta(days=1)
        df = df[(df.index >= pd.to_datetime(start_str)) & (df.index < end_date)]

    # Garante candle inicial
    start_dt = pd.to_datetime(start_str)
    if start_dt not in df.index:

        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": int(start_dt.timestamp() * 1000),
            "limit": 1
        }

        r = requests.get(url, params=params)
        temp = r.json()

        if isinstance(temp, list) and len(temp) > 0:
            d2 = pd.DataFrame(temp, columns=df.columns.tolist() + [
                "close_time","quote_asset_volume","n","t1","t2","ignore"
            ])
            d2["timestamp"] = pd.to_datetime(d2.index, unit="ms")
            d2.set_index("timestamp", inplace=True)
            d2 = d2[df.columns]
            df = pd.concat([d2, df]).sort_index()

    df = df[~df.index.duplicated(keep="first")]

    return df


# =============================================================================
# CÁLCULOS DE VOLATILIDADE
# =============================================================================
def calculos_vol(symbol, end_str):

    df_a = cotacao_binance(symbol, "1d", "2021-01-01", end_str)
    df_d = cotacao_binance(symbol, "1h", "2022-01-01", end_str)
    df_h = cotacao_binance(symbol, "15m", "2024-01-01", end_str)

    if df_a.empty or df_d.empty or df_h.empty:
        return df_h, df_d, df_a

    for df in [df_a, df_d, df_h]:
        df["ret"] = np.log(df["close"] / df["close"].shift(1))

    df_a["vol"] = df_a["ret"].rolling(30).std() * np.sqrt(365)
    df_d["vol"] = df_d["ret"].rolling(24).std() * np.sqrt(24)
    df_h["vol"] = df_h["ret"].rolling(4).std() * np.sqrt(4)

    df_a.dropna(inplace=True)
    df_d.dropna(inplace=True)
    df_h.dropna(inplace=True)

    return df_h, df_d, df_a


# =============================================================================
# STREAMLIT
# =============================================================================
st.set_page_config(layout="wide")
st.title("📈 Dashboard BTC – Preço e Volatilidade (Binance)")

symbol = "BTCUSDT"
data_fim = datetime.today()

if st.sidebar.button("Atualizar Dados"):

    end_str = data_fim.strftime("%Y-%m-%d")
    st.info("⏳ Carregando dados da Binance... Aguarde...")

    try:
        df_h, df_d, df_a = calculos_vol(symbol, end_str)

    except Exception as e:
        st.error(f"Erro durante coleta: {e}")
        st.stop()

    if df_a.empty:
        st.error("❌ Dados vazios. Algo falhou na conexão com a Binance.")
        st.stop()

    col_preco, col_vol = st.columns([2, 1])

    # =========================================
    # GRÁFICO PREÇO
    # =========================================
    with col_preco:

        df_a["mm60"] = df_a["close"].rolling(60).mean()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_a.index, y=df_a["close"], mode="lines", name="Close"))
        fig.add_trace(go.Scatter(x=df_a.index, y=df_a["mm60"], mode="lines", name="MM60"))

        fig.update_layout(
            title="BTC — Preço Diário",
            height=650
        )

        st.plotly_chart(fig, use_container_width=True)

    # =========================================
    # VOLATILIDADES
    # =========================================
    with col_vol:

        st.subheader("Volatilidades")

        fig_a = go.Figure()
        fig_a.add_trace(go.Scatter(x=df_a.index, y=df_a["vol"], mode="lines"))
        fig_a.update_layout(title="Vol Anual", height=200)
        st.plotly_chart(fig_a, use_container_width=True)

        fig_d = go.Figure()
        fig_d.add_trace(go.Scatter(x=df_d.index, y=df_d["vol"], mode="lines"))
        fig_d.update_layout(title="Vol Diária", height=200)
        st.plotly_chart(fig_d, use_container_width=True)

        fig_h = go.Figure()
        fig_h.add_trace(go.Scatter(x=df_h.index, y=df_h["vol"], mode="lines"))
        fig_h.update_layout(title="Vol Horária", height=200)
        st.plotly_chart(fig_h, use_container_width=True)
