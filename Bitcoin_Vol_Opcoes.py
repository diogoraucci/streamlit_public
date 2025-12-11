import requests
import pandas as pd
from datetime import datetime, timedelta
import time

def cotacao_binance(symbol, interval, start_str, end_str=None):
    base_url = "https://api.binance.com/api/v3/klines"
    data = []
    limit = 1000  # máximo permitido

    # ---------------------------
    # Tratamento das datas
    # ---------------------------
    start_time = int(datetime.strptime(start_str, "%Y-%m-%d").timestamp() * 1000)
    end_time = int(datetime.now().timestamp() * 1000) if end_str is None else int(datetime.strptime(end_str, "%Y-%m-%d").timestamp() * 1000)

    # ---------------------------
    # LOOP PRINCIPAL DE COLETA
    # ---------------------------
    while start_time < end_time:

        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "limit": limit
        }

        # -------------- RETRY SEGURO --------------
        retries = 0
        while True:
            try:
                response = requests.get(base_url, params=params, timeout=10)

                # Binance rejeita = -1
                if response.status_code != 200:
                    print(f"⚠️ Erro HTTP {response.status_code}. Tentando novamente...")
                    retries += 1
                    if retries > 5:
                        raise Exception(f"Erro persistente da API Binance ({response.status_code}). Abortado.")
                    time.sleep(1.5 * retries)
                    continue

                temp_data = response.json()

                # Se vier "-1" ou erro no json
                if isinstance(temp_data, dict) and temp_data.get("code") == -1:
                    print("⚠️ Binance devolveu -1 (erro genérico). Retentando...")
                    retries += 1
                    if retries > 5:
                        raise Exception("Erro -1 recorrente da Binance. Abortando.")
                    time.sleep(1.5 * retries)
                    continue

                # Se vier vazio, parar
                if not temp_data:
                    return montar_dataframe(data, start_str, end_str)

                break

            except requests.exceptions.Timeout:
                print("⚠️ Timeout. Retentando...")
                retries += 1
                time.sleep(1.5 * retries)

            except Exception as e:
                print(f"⚠️ Erro durante coleta: {e}")
                retries += 1
                if retries > 5:
                    raise
                time.sleep(1.5 * retries)

        # adiciona dados
        data.extend(temp_data)

        # atualizar start_time
        start_time = temp_data[-1][6] + 1

    return montar_dataframe(data, start_str, end_str)


# ================================
# MONTA DATAFRAME (MESMA LÓGICA DO SEU ORIGINAL)
# ================================
def montar_dataframe(data, start_str, end_str):
    df = pd.DataFrame(data, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
    ])

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df[["open", "high", "low", "close", "volume"]].astype(float)

    # Ajuste da data final
    if end_str:
        end_date = pd.to_datetime(end_str) + timedelta(days=1)
        df = df[(df.index >= pd.to_datetime(start_str)) & (df.index < end_date)]

    # ---- garantir a primeira linha ----
    start_datetime = pd.to_datetime(start_str)
    if start_datetime not in df.index:

        base_url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": int(start_datetime.timestamp() * 1000),
            "limit": 1
        }

        r = requests.get(base_url, params=params)
        temp_data = r.json()

        if temp_data:
            temp_df = pd.DataFrame(temp_data, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "number_of_trades",
                "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
            ])
            temp_df["timestamp"] = pd.to_datetime(temp_df["timestamp"], unit="ms")
            temp_df.set_index("timestamp", inplace=True)
            temp_df = temp_df[["open", "high", "low", "close", "volume"]].astype(float)
            df = pd.concat([temp_df, df]).sort_index()

    df = df[~df.index.duplicated(keep="first")]
    return df
