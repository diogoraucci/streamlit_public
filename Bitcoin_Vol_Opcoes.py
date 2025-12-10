# dashboard.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
from datetime import datetime

# ========================================
# CONFIGURAÇÃO
# ========================================
st.set_page_config(page_title="Dashboard Financeiro", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #1a1a1a; color: white; }
    h2 { color: #00cc96; text-align: center; margin: 0px 0; }
    .stTextInput > div > div > input {
        background-color: #2d2d2d; color: white; border-radius: 8px; border: 1px solid #444;
    }

    /* remove espaço extra do topo */
    header, .stAppViewContainer, .main {
    padding-top: 10000 !important;
    margin-top: 1000 !important;
    
    }
    
    /* remove margens entre componentes */
    section[data-testid="stVerticalBlock"] {
        padding-top: 0;
        padding-bottom: 0;
        margin: 0;
    }
    
    /* remove margens dos gráficos plotly */
    .js-plotly-plot, .plotly, .stPlotlyChart {
        margin: 0 !important;
        padding: 0 !important;
    }

</style>
""", unsafe_allow_html=True)

# ========================================
# ENTRADA
# ========================================
ticker = st.text_input("Digite o ticker (ex: SO, AAPL, PETR4.SA)", value="SO").upper().strip()
if not ticker:
    st.stop()

# ========================================
# FUNÇÃO: COLETAR DADOS
# ========================================
@st.cache_data(ttl=3600)
def coletar_dados(ticker):
    try:
        yf_ticker = yf.Ticker(ticker)

        # --- 1. RESULTADOS ANUAIS ---
        dados_anuais = []
        df_anual_raw = yf_ticker.financials
        if 'Net Income' in df_anual_raw.index:
            for data, valor in df_anual_raw.loc['Net Income'].dropna().items():
                dados_anuais.append({
                    'TICKER': ticker,
                    'Tipo': 'Anual',
                    'Período': data.strftime('%Y'),
                    'Data': data.strftime('%Y-%m-%d'),
                    'Resultado': valor
                })
        df_anual = pd.DataFrame(dados_anuais)

        # --- 2. RESULTADOS TRIMESTRAIS ---
        dados_trim = []
        df_trim_raw = yf_ticker.quarterly_financials
        if 'Net Income' in df_trim_raw.index:
            for data, valor in df_trim_raw.loc['Net Income'].dropna().items():
                trimestre = ((data.month - 1) // 3) + 1
                periodo = f"{data.year}-Q{trimestre}"
                dados_trim.append({
                    'TICKER': ticker,
                    'Tipo': 'Trimestral',
                    'Período': periodo,
                    'Data': data.strftime('%Y-%m-%d'),
                    'Resultado': valor
                })
        df_trim = pd.DataFrame(dados_trim)[:-1]  # remove último (incompleto)

        # --- 3. DESCRIÇÃO ---
        info = yf_ticker.info
        df_descricao = pd.DataFrame([{
            'TICKER': ticker,
            'Descrição': info.get('longBusinessSummary', 'N/A'),
            'País': info.get('country', 'N/A'),
            'Setor': info.get('sector', 'N/A')
        }])

        # --- 4. COTAÇÕES + MM ---
        data_hoje = datetime.today().strftime('%Y-%m-%d')
        df_raw = yf.download(
            ticker,
            start='2020-01-01',
            end=data_hoje,
            progress=False,
            auto_adjust=False
        )
        if df_raw.empty:
            st.error("Nenhuma cotação encontrada.")
            st.stop()

        close_col = df_raw['Close'].iloc[:, 0] if isinstance(df_raw.columns, pd.MultiIndex) else df_raw['Close']
        df_cot = pd.DataFrame({'Close': close_col})
        df_cot['mm'] = df_cot['Close'].rolling(60).mean()
        df_cot.dropna(inplace=True)

        return df_anual, df_trim, df_descricao, df_cot

    except Exception as e:
        st.error(f"Erro ao coletar dados: {e}")
        st.stop()

# ========================================
# EXECUTA
# ========================================
df_anual, df_trim, df_descricao, df = coletar_dados(ticker)

# Lucro em milhões
df_anual["Lucro_Milhoes"] = df_anual["Resultado"] / 1_000_000
df_trim["Lucro_Milhoes"]  = df_trim["Resultado"]  / 1_000_000
df_trim["Label"] = df_trim["Período"].str.replace("-Q", " Q")
df_anual["Label"] = df_anual["Período"]

ultimo_preco = df["Close"].iloc[-1]
ultima_data  = df.index[-1]

# ========================================
# TÍTULO + INFO
# ========================================
st.markdown(f"<h2>{ticker}</h2>", unsafe_allow_html=True)
st.markdown(
    f"<p style='text-align:center; color:#aaa; font-size:14px;'>"
    f"País: {df_descricao.iloc[0]['País']} | Setor: {df_descricao.iloc[0]['Setor']}</p>",
    unsafe_allow_html=True
)

# ========================================
# LINHA PRINCIPAL: PREÇO | ANUAL | TRIMESTRAL
# ========================================
col_price, col_anual, col_trim = st.columns([5, 2, 2])

# ---------- GRÁFICO DE PREÇO ----------
with col_price:
    fig_preco = go.Figure()
    fig_preco.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines", name="Close",
                                   line=dict(color="#3399ff", width=2)))
    fig_preco.add_trace(go.Scatter(x=df.index, y=df["mm"], mode="lines", name="Média Móvel 60",
                                   line=dict(color="#9933ff", width=2, dash="dash")))

    ref = 91.07 if ticker == "SO" else df["Close"].mean()
    fig_preco.add_hline(y=ref, line_dash="dot", line_color="#555",
                        annotation_text=f"Ref {ref:.2f}", annotation_position="bottom right")

    fig_preco.add_annotation(
        x=ultima_data, y=ultimo_preco,
        text=f"{ultimo_preco:.2f}",
        showarrow=True, arrowhead=2, ax=50, ay=-40,
        bgcolor="#00cc96", font=dict(color="black", size=11),
        bordercolor="#00cc96", borderwidth=2
    )
    fig_preco.update_layout(
        xaxis=dict(tickformat="%Y", gridcolor="#333"),
        yaxis=dict(title="Preço (USD)", gridcolor="#333"),
        plot_bgcolor="#1a1a1a", paper_bgcolor="#1a1a1a", font_color="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=20, t=40, b=20), height=380,
        hovermode="x unified"
    )
    st.plotly_chart(fig_preco, use_container_width=True, config={"displayModeBar": False})

# ---------- GRÁFICO ANUAL ----------
with col_anual:
    colors_anual = ['#00cc96' if x >= 0 else '#ff4444' for x in df_anual["Lucro_Milhoes"]]
    textpos_anual = ['outside' if x >= 0 else 'inside' for x in df_anual["Lucro_Milhoes"]]

    fig_anual = go.Figure()
    fig_anual.add_trace(go.Bar(
        x=df_anual["Lucro_Milhoes"], y=df_anual["Label"],
        orientation='h',
        text=[f"{v:,.0f}M" for v in df_anual["Lucro_Milhoes"]],
        textposition=textpos_anual,
        marker_color=colors_anual,
        textfont=dict(color='white', size=10)
    ))
    fig_anual.update_layout(
        title="Lucro Anual",
        title_font_size=14,
        xaxis=dict(showgrid=False, title="R$ (M)", title_font_size=11),
        yaxis=dict(showgrid=False),
        plot_bgcolor="#1a1a1a", paper_bgcolor="#1a1a1a", font_color="white",
        margin=dict(l=20, r=60, t=50, b=20), height=380
    )
    st.plotly_chart(fig_anual, use_container_width=True, config={"displayModeBar": False})

# ---------- GRÁFICO TRIMESTRAL ----------
with col_trim:
    colors_trim = ['#00cc96' if x >= 0 else '#ff4444' for x in df_trim["Lucro_Milhoes"]]
    textpos_trim = ['outside' if x >= 0 else 'inside' for x in df_trim["Lucro_Milhoes"]]

    fig_trim = go.Figure()
    fig_trim.add_trace(go.Bar(
        x=df_trim["Lucro_Milhoes"], y=df_trim["Label"],
        orientation='h',
        text=[f"{v:,.0f}M" for v in df_trim["Lucro_Milhoes"]],
        textposition=textpos_trim,
        marker_color=colors_trim,
        textfont=dict(color='white', size=9)
    ))
    fig_trim.update_layout(
        title="Lucro Trimestral",
        title_font_size=14,
        xaxis=dict(showgrid=False, title="R$ (M)", title_font_size=11),
        yaxis=dict(showgrid=False),
        plot_bgcolor="#1a1a1a", paper_bgcolor="#1a1a1a", font_color="white",
        margin=dict(l=20, r=60, t=50, b=20), height=380
    )
    st.plotly_chart(fig_trim, use_container_width=True, config={"displayModeBar": False})

# ========================================
# DESCRIÇÃO (LARGURA TOTAL)
# ========================================
st.markdown("---")
descricao = df_descricao.iloc[0]["Descrição"]
curta = descricao[:800] + ("..." if len(descricao) > 800 else "")
st.markdown(
    f"<div style='background-color:#2d2d2d; padding:18px; border-radius:10px; "
    f"font-size:13.5px; line-height:1.7; text-align:justify; margin-top:10px;'>"
    f"{curta}</div>",
    unsafe_allow_html=True
)