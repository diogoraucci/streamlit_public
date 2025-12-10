import streamlit as st
import requests
import time
import random
from requests.exceptions import HTTPError

# ===========================================================
#  FUNÇÃO ROBUSTA DE COLETA — RESISTENTE A ERRO 429
# ===========================================================

def coletar_dados(ticker: str, tentativas=6):
    """
    Coleta dados do Yahoo Finance com controle de erros 429.
    Faz tentativas com backoff exponencial + jitter.
    """

    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
    params = {
        "modules": "financialData,quoteType,defaultKeyStatistics,assetProfile,summaryDetail",
        "corsDomain": "finance.yahoo.com",
        "formatted": "false",
        "symbol": ticker,
    }

    for tentativa in range(1, tentativas + 1):
        try:
            resposta = requests.get(url, params=params, timeout=10)

            # Se for erro 429
            if resposta.status_code == 429:
                espera = (2 ** tentativa) + random.uniform(0, 1)
                st.warning(f"⚠️ Yahoo devolveu 429 (Too Many Requests). Tentando novamente em {espera:.1f}s...")
                time.sleep(espera)
                continue

            resposta.raise_for_status()
            dados = resposta.json()

            return dados  # Retorno bem sucedido

        except HTTPError as e:
            if "429" in str(e):
                espera = (2 ** tentativa) + random.uniform(0, 1)
                st.warning(f"⚠️ Erro 429 detectado. Aguardando {espera:.1f}s...")
                time.sleep(espera)
                continue
            else:
                st.error(f"Erro HTTP inesperado: {e}")
                return None

        except Exception as e:
            st.error(f"Erro inesperado: {e}")
            return None

    st.error("❌ Não foi possível coletar os dados após várias tentativas.")
    return None


# ===========================================================
#  CACHE STREAMLIT — evita rodar a coleta repetidas vezes
# ===========================================================

@st.cache_data(show_spinner=True, ttl=60)
def coletar_dados_cache(ticker):
    return coletar_dados(ticker)


# ===========================================================
#  INTERFACE STREAMLIT
# ===========================================================

st.title("📊 Dashboard — Dados do Yahoo Finance")

ticker = st.text_input("Digite o ticker (ex: AAPL, TSLA, SO):", value="SO")

if st.button("Coletar dados"):
    with st.spinner("Baixando dados, aguarde..."):
        dados = coletar_dados_cache(ticker)

    if dados:
        st.success("Dados coletados com sucesso!")
        st.json(dados)
    else:
        st.error("Falha ao obter os dados.")


st.info("Este app usa proteção contra erro 429 com backoff exponencial + cache.")
