# app.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go
from functools import wraps

# -------------------------
# Wrapper de requests com retry (não altera sua lógica)
# -------------------------
def requests_get_with_retry(url, params=None, max_retries=5, backoff=1.2, timeout=10):
    """Tenta fazer requests.get com retries em caso de 429 ou falha temporária."""
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
        except Exception as e:
            # Erro de rede — espera e tenta novamente
            if attempt == max_retries:
                raise
            time.sleep(backoff * attempt)
            continue

        # Se 429, espera e tenta novamente
        if resp.status_code == 429:
            if attempt == max_retries:
                return resp
            time.sleep(backoff * attempt)
            continue

        # Retorna qualquer outro status (200 ou erro) para tratamento posterior
        return resp

    # fallback (não deve chegar aqui)
    return resp


# =====================================================================
# SUA FUNÇÃO FUNCIONAL — mantive idêntica, só troquei requests.get por wrapper
# =====================================================================
def cotacao_binance(symbol, interval, start_str, end_str=None):
    base_url = "https://api.binance.com/api/v3/klines"
    data = []
    limit = 1000  # Máximo de candles por requisição

    start_time = int(datetime.strptime(start_str, "%Y-%m-%d").timestamp() * 1000)
    end_time = int(datetime.now().timestamp() * 1000) if end_str is None else int(datetime.strptime(end_str, "%Y-%m-%d").timestamp() * 1000)

    while start_time < end_time:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "limit": limit
        }

        # usa wrapper para retries (mantém comportamento funcional)
        response = requests_get_with_retry(base_url, params=params, max_retries=6, backoff=1.0)

        # se veio resposta inválida, tenta extrair .json com proteção
        try:
            temp_data = response.json()
        except Exception:
            # se não for possível decodificar json, interrompe (igual ao comportamento original)
            break

        if not temp_data:
            break

        data.extend(temp_data)
        # aqui mantemos exatamente sua lógica
        start_time = temp_data[-1][6] + 1  # Próximo timestamp

    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "close_time", 
        "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume", 
        "taker_buy_quote_asset_volume", "ignore"
    ])

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df[["open", "high", "low", "close", "volume"]].astype(float)

    # Ajusta intervalo final
    if end_str:
        end_date = pd.to_datetime(end_str) + timedelta(days=1)
        df = df[(df.index >= pd.to_datetime(start_str)) & (df.index < end_date)]

    # Garantir data inicial
    start_datetime = pd.to_datetime(start_str)
    if start_datetime not in df.index:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": int(start_datetime.timestamp() * 1000),
            "limit": 1
        }
        response = requests_get_with_retry(base_url, params=params, max_retries=4, backoff=0.8)
        try:
            temp_data = response.json()
        except Exception:
            temp_data = None

        if temp_data:
            temp_df = pd.DataFrame(temp_data, columns=[
                "timestamp", "open", "high", "low", "close", "volume", "close_time", 
                "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume", 
                "taker_buy_quote_asset_volume", "ignore"
            ])
            temp_df["timestamp"] = pd.to_datetime(temp_df["timestamp"], unit="ms")
            temp_df.set_index("timestamp", inplace=True)
            temp_df = temp_df[["open", "high", "low", "close", "volume"]].astype(float)
            df = pd.concat([temp_df, df]).sort_index()

    df = df[~df.index.duplicated(keep="first")]
    return df


# =====================================================================
# Função para cálculo de volatilidade (usa sua cotacao_binance)
# =====================================================================
def calculos_volatilidade(symbol="BTCUSDT",
                          start_a="2024-01-01",
                          start_d="2024-01-01",
                          start_h="2025-10-01",
                          end_str=None):
    if end_str is None:
        end_str = datetime.today().strftime('%Y-%m-%d')

    # Obtemos os dados chamando sua função
    df_a = cotacao_binance(symbol, "1d", start_a, end_str)
    df_d = cotacao_binance(symbol, "1h", start_d, end_str)
    df_h = cotacao_binance(symbol, "15m", start_h, end_str)

    # Se algum DF veio vazio, devolve e sinaliza
    if df_a.empty or df_d.empty or df_h.empty:
        return df_h, df_d, df_a

    # Calcular retornos
    for df in [df_a, df_d, df_h]:
        df['retornos'] = np.log(df['close'] / df['close'].shift(1))

    # Volatilidade anualizada / diária / horária
    df_a["vol"] = df_a["retornos"].rolling(window=30).std() * np.sqrt(365)
    df_d["vol"] = df_d['retornos'].rolling(window=24).std() * np.sqrt(24)
    df_h["vol"] = df_h['retornos'].rolling(window=4).std() * np.sqrt(4)  # 15m

    # Remover NaN
    df_a.dropna(inplace=True)
    df_d.dropna(inplace=True)
    df_h.dropna(inplace=True)

    return df_h, df_d, df_a


# =====================================================================
# STREAMLIT APP
# =====================================================================
st.set_page_config(layout="wide", page_title="BTC Volatilidade")
st.title("📊 Dashboard BTC – Preço e Volatilidade (Binance)")

# Opções
symbol = st.sidebar.text_input("Ticker", "BTCUSDT")
# Data final (por padrão hoje)
data_fim = st.sidebar.date_input("Data Final", datetime.today())
start_a = st.sidebar.text_input("Start Diário (AAAA-MM-DD)", "2024-01-01")
start_d = st.sidebar.text_input("Start Horário (AAAA-MM-DD)", "2024-01-01")
start_h = st.sidebar.text_input("Start 15m (AAAA-MM-DD)", "2025-10-01")  # mantenha se quiser

# Botão de atualizar
if st.sidebar.button("Atualizar Dados"):

    end_str = data_fim.strftime("%Y-%m-%d")

    with st.spinner("Coletando dados da Binance (pode demorar um pouco)..."):
        try:
            df_h, df_d, df_a = calculos_volatilidade(symbol=symbol,
                                                    start_a=start_a,
                                                    start_d=start_d,
                                                    start_h=start_h,
                                                    end_str=end_str)
        except Exception as e:
            st.error(f"Erro durante coleta: {e}")
            st.stop()

    # Se algum dataframe veio vazio, mostra mensagem com detalhes
    if df_a.empty or df_d.empty or df_h.empty:
        st.error("Um dos DataFrames retornou vazio. Verifique:\n\n"
                 "- Se o símbolo está correto (ex.: BTCUSDT)\n"
                 "- Se as datas de início/fim são válidas\n"
                 "- Se o timeframe pedido tem dados para o período\n\n"
                 "Detalhes:\n"
                 f" df_a (daily) empty: {df_a.empty}\n"
                 f" df_d (1h) empty: {df_d.empty}\n"
                 f" df_h (15m) empty: {df_h.empty}")
        st.stop()

    # Layout: colunas 2/3 e 1/3
    col_preco, col_vol = st.columns([2, 1])

    # --------------------------
    # Coluna esquerda: Preço + MM
    # --------------------------
    with col_preco:
        df_a["mm60"] = df_a["close"].rolling(60).mean()

        ultima_data = df_a.index[-1]
        ultimo_preco = df_a["close"].iloc[-1]

        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(x=df_a.index, y=df_a["close"], mode="lines", name="Close"))
        fig_price.add_trace(go.Scatter(x=df_a.index, y=df_a["mm60"], mode="lines", name="MM60", line=dict(dash="dash")))

        # anotação do último preço
        fig_price.add_annotation(x=ultima_data, y=ultimo_preco,
                                 text=f"{ultimo_preco:.2f}", showarrow=True, arrowhead=2,
                                 ax=40, ay=-40, bgcolor="#00cc96", font=dict(color="black"))

        fig_price.update_layout(title=f"{symbol} — Preço Diário", height=650, showlegend=True)
        st.plotly_chart(fig_price, use_container_width=True, config={"displayModeBar": False})

    # --------------------------
    # Coluna direita: 3 gráficos de volatilidade empilhados
    # --------------------------
    with col_vol:
        st.subheader("Volatilidades")

        fig_a = go.Figure()
        fig_a.add_trace(go.Scatter(x=df_a.index, y=df_a["vol"], mode="lines", name="Vol Anual"))
        fig_a.update_layout(title="Vol Anual", height=200, margin=dict(t=30))
        st.plotly_chart(fig_a, use_container_width=True, config={"displayModeBar": False})

        fig_d = go.Figure()
        fig_d.add_trace(go.Scatter(x=df_d.index, y=df_d["vol"], mode="lines", name="Vol Diária"))
        fig_d.update_layout(title="Vol Diária", height=200, margin=dict(t=30))
        st.plotly_chart(fig_d, use_container_width=True, config={"displayModeBar": False})

        fig_h = go.Figure()
        fig_h.add_trace(go.Scatter(x=df_h.index, y=df_h["vol"], mode="lines", name="Vol Horária"))
        fig_h.update_layout(title="Vol Horária", height=200, margin=dict(t=30))
        st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})

    st.success("Gráficos atualizados ✔")
