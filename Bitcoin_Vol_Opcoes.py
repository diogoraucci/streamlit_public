import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go


# =====================================================================
# COLETA BINANCE – PROTEÇÃO COMPLETA CONTRA ERROS, 429 E RESPOSTA INVÁLIDA
# =====================================================================
def cotacao_binance(symbol, interval, start_str='2020-01-01', end_str=None):

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

        # ==========================
        # Proteção contra erro 429
        # ==========================
        for tentativa in range(6):
            resp = requests.get(base_url, params=params)
            if resp.status_code != 429:
                break
            time.sleep(1.2 * (tentativa + 1))

        try:
            temp_data = resp.json()
        except:
            break

        # Resposta inesperada (Binance pode devolver dict com erro)
        if not isinstance(temp_data, list):
            break

        # Resposta vazia → fim dos candles válidos
        if len(temp_data) == 0:
            break

        data.extend(temp_data)

        # Avança para próximo bloco
        try:
            next_start = temp_data[-1][6] + 1     # close_time + 1 ms
        except:
            break

        # Evita loop infinito se Binance der 1 candle repetido
        if next_start <= start_time:
            start_time += 60_000   # avança 1 min só para quebrar dead loop
        else:
            start_time = next_start

        # Pequena pausa anti-ban
        time.sleep(0.15)

    # ============================================================
    # Transformação em DataFrame
    # ============================================================
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

    df_a = cotacao_binance(symbol, "1d", "2020-01-01", end_str)
    df_d = cotacao_binance(symbol, "1h", "2020-01-01", end_str)
    df_h = cotacao_binance(symbol, "15m", "2020-01-01", end_str)   # << CORRIGIDO

    # Se vazio, devolve mesmo assim para evitar crash
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
data_fim = datetime.today()
btn = st.sidebar.button("Atualizar Dados")

if btn:

    end_str = data_fim.strftime("%Y-%m-%d")

    df_h, df_d, df_a = calculos_volatilidade(symbol, end_str)

    if df_a.empty:
        st.error("Erro ao carregar dados da Binance. Pode ser período inválido ou símbolo incorreto.")
        st.stop()

    col_preco, col_vol = st.columns([2, 1])

    # ==========================================================================
    # GRÁFICO DE PREÇO
    # ==========================================================================
    with col_preco:

        df_a["mm60"] = df_a["close"].rolling(60).mean()

        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(
            x=df_a.index,
            y=df_a["close"],
            mode="lines",
            name="Close",
        ))
        fig_price.add_trace(go.Scatter(
            x=df_a.index,
            y=df_a["mm60"],
            mode="lines",
            name="MM60",
            line=dict(dash="dash")
        ))

        fig_price.update_layout(
            title=f"{symbol} – Preço Diário",
            height=650,
        )

        st.plotly_chart(fig_price, use_container_width=True)

    # ==========================================================================
    # VOLATILIDADES
    # ==========================================================================
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
