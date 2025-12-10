import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go

# ============================================================
# FUNÇÃO SEGURO PARA COLETAR DADOS DA BINANCE
# ============================================================
def cotacao_binance(symbol, interval, start_str, end_str=None):

    base_url = "https://api.binance.com/api/v3/klines"
    data = []
    limit = 1000  

    start_time = int(datetime.strptime(start_str, "%Y-%m-%d").timestamp() * 1000)
    end_time = int(datetime.now().timestamp() * 1000) if end_str is None else int(
        datetime.strptime(end_str, "%Y-%m-%d").timestamp() * 1000
    )

    while start_time < end_time:

        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "limit": limit
        }

        # PROTEÇÃO CONTRA ERRO 429 – Too Many Requests
        for tentativa in range(5):
            resp = requests.get(base_url, params=params)
            if resp.status_code != 429:
                break
            time.sleep(1.5 * (tentativa + 1))

        temp_data = resp.json()

        if not temp_data:
            break

        data.extend(temp_data)
        start_time = temp_data[-1][6] + 1

    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "close_time",
        "quote_asset_volume", "trades", "taker_base", "taker_quote", "ignore"
    ])

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df[["open", "high", "low", "close", "volume"]].astype(float)

    if end_str:
        end_date = pd.to_datetime(end_str) + timedelta(days=1)
        df = df[(df.index >= pd.to_datetime(start_str)) & (df.index < end_date)]

    return df


# ============================================================
# CÁLCULO COMPLETO DE VOLATILIDADES
# ============================================================
def calculos_volatilidade(symbol="BTCUSDT",
                           start_a="2024-01-01",
                           start_d="2024-01-01",
                           start_h="2025-10-01",
                           end_str=None):

    if end_str is None:
        end_str = datetime.today().strftime('%Y-%m-%d')

    df_a = cotacao_binance(symbol, "1d", start_a, end_str)
    df_d = cotacao_binance(symbol, "1h", start_d, end_str)
    df_h = cotacao_binance(symbol, "15m", start_h, end_str)

    # Retornos
    for df in [df_a, df_d, df_h]:
        df["retornos"] = np.log(df["close"] / df["close"].shift(1))

    df_a["vol"] = df_a["retornos"].rolling(30).std() * np.sqrt(365)
    df_d["vol"] = df_d["retornos"].rolling(24).std() * np.sqrt(24)
    df_h["vol"] = df_h["retornos"].rolling(4).std() * np.sqrt(4)

    df_a.dropna(inplace=True)
    df_d.dropna(inplace=True)
    df_h.dropna(inplace=True)

    return df_h, df_d, df_a


# ============================================================
# STREAMLIT DASHBOARD
# ============================================================
st.set_page_config(layout="wide")
st.title("📊 Dashboard de Volatilidade e Preço — Binance")


symbol = st.sidebar.text_input("Ticker", "BTCUSDT")
end_str = st.sidebar.date_input("Data Final", datetime.today()).strftime("%Y-%m-%d")

st.sidebar.write("Clique para atualizar:")
atualizar = st.sidebar.button("Atualizar Dados")

if atualizar:

    df_h, df_d, df_a = calculos_volatilidade(symbol=symbol, end_str=end_str)

    # ============================================================
    # COLUNAS PRINCIPAIS
    # ============================================================
    col_preco, col_vol = st.columns([2, 1])

    # ------------------------------------------------------------
    # GRÁFICO DE PREÇOS (ESQUERDA)
    # ------------------------------------------------------------
    with col_preco:

        df_a["mm"] = df_a["close"].rolling(60).mean()

        ultima_data = df_a.index[-1]
        ultimo_preco = df_a["close"].iloc[-1]

        fig_preco = go.Figure()
        fig_preco.add_trace(go.Scatter(
            x=df_a.index, y=df_a["close"],
            mode="lines", name="Preço", line=dict(width=2, color="#3399ff")
        ))
        fig_preco.add_trace(go.Scatter(
            x=df_a.index, y=df_a["mm"],
            mode="lines", name="MM60", line=dict(width=2, color="#9933ff", dash="dash")
        ))

        fig_preco.update_layout(
            title=f"{symbol} — Preço Diário",
            height=600,
            margin=dict(l=20, r=20, t=50, b=20),
            plot_bgcolor="#111",
            paper_bgcolor="#111",
            font_color="white"
        )

        st.plotly_chart(fig_preco, use_container_width=True)


    # ------------------------------------------------------------
    # GRÁFICOS DE VOLATILIDADE (DIREITA)
    # ------------------------------------------------------------
    with col_vol:

        st.subheader("Volatilidades")

        # 1 — Vol Anual
        fig_a = go.Figure()
        fig_a.add_trace(go.Scatter(x=df_a.index, y=df_a["vol"],
                                   mode="lines", name="Vol Anual"))
        fig_a.update_layout(height=200, margin=dict(l=10, r=10, t=40, b=20))
        st.plotly_chart(fig_a, use_container_width=True)

        # 2 — Vol Diária
        fig_d = go.Figure()
        fig_d.add_trace(go.Scatter(x=df_d.index, y=df_d["vol"],
                                   mode="lines", name="Vol Diária"))
        fig_d.update_layout(height=200, margin=dict(l=10, r=10, t=40, b=20))
        st.plotly_chart(fig_d, use_container_width=True)

        # 3 — Vol Horária
        fig_h = go.Figure()
        fig_h.add_trace(go.Scatter(x=df_h.index, y=df_h["vol"],
                                   mode="lines", name="Vol Horária"))
        fig_h.update_layout(height=200, margin=dict(l=10, r=10, t=40, b=20))
        st.plotly_chart(fig_h, use_container_width=True)
