import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go


# =====================================================================
# COLETA BINANCE – COMPLETAMENTE PROTEGIDA CONTRA ERROS E RETORNOS VAZIOS
# =====================================================================
def cotacao_binance(symbol, interval, '2024-01-01", end_str=None):

    base_url = "https://api.binance.com/api/v3/klines"
    data = []
    limit = 1000

    start_time = int(datetime.strptime(start_str, "%Y-%m-%d").timestamp() * 1000)
    end_ts = (
        int(datetime.now().timestamp() * 1000)
        if end_str is None
        else int(datetime.strptime(end_str, "%Y-%m-%d").timestamp() * 1000)
    )

    while start_time < end_ts:

        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "limit": limit
        }

        # Proteção contra 429
        for tentativa in range(6):
            resp = requests.get(base_url, params=params)
            if resp.status_code != 429:
                break
            time.sleep(1.2 * (tentativa + 1))

        try:
            temp_data = resp.json()
        except:
            break

        # Se vier vazio, paramos
        if not isinstance(temp_data, list) or len(temp_data) == 0:
            break

        data.extend(temp_data)

        # Proteção contra listas inesperadas
        try:
            start_time = temp_data[-1][6] + 1
        except Exception:
            break

    # Criação do DataFrame
    if len(data) == 0:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "close_time",
        "quote_asset_volume", "trades", "taker_base", "taker_quote", "ignore"
    ])

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)

    df = df[["open", "high", "low", "close", "volume"]].astype(float)

    # Ajuste final de período
    if end_str:
        end_limit = pd.to_datetime(end_str) + timedelta(days=1)
        df = df[(df.index >= pd.to_datetime(start_str)) & (df.index < end_limit)]

    return df



# =====================================================================
# CÁLCULO DAS VOLATILIDADES
# =====================================================================
def calculos_volatilidade(symbol, end_str):

    df_a = cotacao_binance(symbol, "1d", "2024-01-01", end_str)
    df_d = cotacao_binance(symbol, "1h", "2024-01-01", end_str)
    df_h = cotacao_binance(symbol, "15m", "2025-10-01", end_str)

    # Se algum DF vier vazio, evita crash
    if df_a.empty or df_d.empty or df_h.empty:
        return df_h, df_d, df_a

    for df in [df_a, df_d, df_h]:
        df["retornos"] = np.log(df["close"] / df["close"].shift(1))

    df_a["vol"] = df_a["retornos"].rolling(30).std() * np.sqrt(365)
    df_d["vol"] = df_d["retornos"].rolling(24).std() * np.sqrt(24)
    df_h["vol"] = df_h["retornos"].rolling(4).std() * np.sqrt(4)

    df_a.dropna(inplace=True)
    df_d.dropna(inplace=True)
    df_h.dropna(inplace=True)

    return df_h, df_d, df_a



# =====================================================================
# STREAMLIT DASHBOARD
# =====================================================================
st.set_page_config(layout="wide")

st.title("📊 Dashboard BTC – Preço e Volatilidade (Binance)")

symbol = "BTCUSDT"
data_fim =  datetime.today())
btn = st.sidebar.button("Atualizar Dados")

if btn:

    end_str = data_fim.strftime("%Y-%m-%d")

    df_h, df_d, df_a = calculos_volatilidade(symbol, end_str)

    if df_a.empty:
        st.error("Erro ao carregar dados da Binance. Pode ser período inválido ou símbolo incorreto.")
        st.stop()

    # ================================
    # C O L U N A S
    # ================================
    col_preco, col_vol = st.columns([2, 1])


    # --------------------------
    # GRÁFICO DE PREÇO (ESQUERDA)
    # --------------------------
    with col_preco:

        df_a["mm60"] = df_a["close"].rolling(60).mean()

        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(
            x=df_a.index,
            y=df_a["close"],
            mode="lines",
            name="Close",
            line=dict(color="#2ca02c", width=2)
        ))
        fig_price.add_trace(go.Scatter(
            x=df_a.index,
            y=df_a["mm60"],
            mode="lines",
            name="MM60",
            line=dict(color="#ff7f0e", width=2, dash="dash")
        ))

        fig_price.update_layout(
            title=f"{symbol} – Preço Diário",
            height=650,
            plot_bgcolor="#111",
            paper_bgcolor="#111",
            font_color="white"
        )

        st.plotly_chart(fig_price, use_container_width=True)


    # --------------------------
    # VOLATILIDADE (DIREITA)
    # --------------------------
    with col_vol:

        st.subheader("Volatilidades")

        # anual
        fig_a = go.Figure()
        fig_a.add_trace(go.Scatter(x=df_a.index, y=df_a["vol"], mode="lines"))
        fig_a.update_layout(title="Vol Anual", height=200, margin=dict(l=5, r=5, t=30, b=5))
        st.plotly_chart(fig_a, use_container_width=True)

        # diária
        fig_d = go.Figure()
        fig_d.add_trace(go.Scatter(x=df_d.index, y=df_d["vol"], mode="lines"))
        fig_d.update_layout(title="Vol Diária", height=200, margin=dict(l=5, r=5, t=30, b=5))
        st.plotly_chart(fig_d, use_container_width=True)

        # horária
        fig_h = go.Figure()
        fig_h.add_trace(go.Scatter(x=df_h.index, y=df_h["vol"], mode="lines"))
        fig_h.update_layout(title="Vol Horária", height=200, margin=dict(l=5, r=5, t=30, b=5))
        st.plotly_chart(fig_h, use_container_width=True)
