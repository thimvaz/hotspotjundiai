"""
Ilhas de Calor Urbanas — Jundiaí/SP
Painel interativo para planejamento urbano
"""

import streamlit as st
import numpy as np
from streamlit_folium import st_folium
from utils.data_loader import carregar_banda, carregar_mapbiomas, listar_arquivos_disponiveis
from utils.raster_utils import calcular_hotspots, calcular_persistencia, calcular_anomalia
from utils.map_builder import construir_mapa

st.set_page_config(
    page_title="Ilhas de Calor — Jundiaí/SP",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS mínimo para ajuste visual
st.markdown("""
<style>
    header { background-color: transparent !important; }
    .block-container { padding-top: 2rem; }
    .stMetric label { font-size: 0.85rem; }
    h1 { font-size: 1.4rem !important; }
</style>
""", unsafe_allow_html=True)

# ── Constantes ────────────────────────────────────────────────────────────────
ANOS   = [2017, 2019, 2021, 2023, 2025]
BANDAS = {"LST (°C)": 1, "NDVI": 2, "NDBI": 3, "MNDWI": 4}
CENTRO_PADRAO = [-23.19, -46.89]
ZOOM_PADRAO   = 12

# ── Estado da Sessão (Preservação de Zoom e Centro) ───────────────────────────
if "map_center" not in st.session_state:
    st.session_state.map_center = CENTRO_PADRAO
if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = ZOOM_PADRAO

def resetar_visao_mapa():
    """Restaura o enquadramento padrão de Jundiaí."""
    st.session_state.map_center = CENTRO_PADRAO
    st.session_state.map_zoom = ZOOM_PADRAO

def renderizar_mapa_preservando_zoom(m, key_mapa: str):
    """Renderiza o mapa Folium e salva qualquer alteração de zoom/pan na sessão."""
    saida = st_folium(
        m,
        height=560,
        use_container_width=True,
        key=key_mapa,
        returned_objects=["center", "zoom"],
    )
    if saida:
        if saida.get("center"):
            novo_centro = [saida["center"]["lat"], saida["center"]["lng"]]
            # Atualiza apenas se houve mudança real para evitar loops
            if novo_centro != st.session_state.map_center:
                st.session_state.map_center = novo_centro
        if saida.get("zoom") is not None:
            if saida["zoom"] != st.session_state.map_zoom:
                st.session_state.map_zoom = saida["zoom"]

# ── Helpers Cacheados para Performance ────────────────────────────────────────
@st.cache_data(show_spinner=False)
def obter_persistencia_cacheada(anos_tupla: tuple):
    """Calcula e faz cache da persistência para evitar releitura de disco ao mexer em sliders."""
    mascaras = []
    bounds_ref = None
    for a in anos_tupla:
        lst_a, bounds, _ = carregar_banda(a, 1)
        mascaras.append(calcular_hotspots(lst_a))
    persistencia, bounds_ref = calcular_persistencia(mascaras, bounds)
    persistencia = persistencia.astype(np.float32)
    lst_ref, _, _ = carregar_banda(anos_tupla[-1], 1)
    persistencia[np.isnan(lst_ref)] = np.nan
    return persistencia, bounds_ref

def _cmap_para_banda(banda_num: int) -> str:
    return {1: "RdYlBu_r", 2: "RdYlGn", 3: "RdYlBu_r", 4: "Blues"}.get(banda_num, "viridis")

def _texto_interpretacao(camada: str):
    textos = {
        "LST (°C)": "Temperatura de superfície em graus Celsius. "
                    "Vermelho = mais quente, azul = mais frio. "
                    "Hotspots (overlay vermelho) = pixels acima de μ + 2σ do município.",
        "NDVI":     "Índice de vegetação (−1 a +1). Verde = vegetação densa, vermelho = "
                    "solo exposto ou área construída. NDVI > 0.4 indica vegetação saudável.",
        "NDBI":     "Índice de área construída (−1 a +1). Vermelho = alta densidade "
                    "de superfícies impermeáveis (concreto/asfalto), azul = vegetação.",
        "MNDWI":    "Índice de água modificado (−1 a +1). Azul escuro = água. "
                    "Identifica rios, represas e áreas alagadas.",
    }
    st.markdown(textos.get(camada, ""))

def _legenda_persistencia(n_anos: int) -> str:
    cores = ["#f4f4f5", "#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]
    itens = ""
    rotulos = ["Nunca hotspot", "1 ano", "2 anos", "3 anos",
               f"{n_anos-1} anos", f"{n_anos} anos (todos)"]
    for c, r in zip(cores[:n_anos+1], rotulos[:n_anos+1]):
        itens += (f'<span style="background:{c};display:inline-block;'
                  f'width:18px;height:18px;border-radius:3px;'
                  f'margin-right:6px;vertical-align:middle; border: 1px solid #ccc;"></span>{r}&nbsp;&nbsp;')
    return f"<div style='padding:8px 0'>{itens}</div>"

# ── Cabeçalho e Validação de Dados ────────────────────────────────────────────
arquivos_ok = listar_arquivos_disponiveis()
if not arquivos_ok:
    st.error("⚠️ Nenhum arquivo de dados encontrado na pasta `data/`. "
             "Consulte o README para instruções de download.")
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/"
             "Flag_of_Jundiaí.svg/200px-Flag_of_Jundiaí.svg.png", width=80)
    st.title("Ilhas de Calor\nJundiaí/SP")
    st.caption("Landsat 8 · 2017–2025")
    st.divider()

    pagina = st.radio(
        "Visualização",
        ["🌡️ Temperatura e Hotspots",
         "📍 Persistência de Hotspots",
         "🎯 Zonas Prioritárias"],
        label_visibility="collapsed"
    )
    st.divider()

    if pagina == "🌡️ Temperatura e Hotspots":
        ano = st.select_slider("Ano", options=ANOS, value=2025)
        camada = st.selectbox("Índice base", list(BANDAS.keys()))
        mostrar_hotspots = st.toggle("Sobrepor hotspots (LST > μ + 2σ)", value=True)
        opacidade = st.slider("Opacidade do raster", 0.1, 1.0, 0.75, 0.05)

    elif pagina == "📍 Persistência de Hotspots":
        anos_sel = st.multiselect(
            "Anos incluídos no cálculo",
            ANOS, default=ANOS,
            help="Selecione quais anos compõem o mapa de persistência"
        )
        opacidade = st.slider("Opacidade", 0.1, 1.0, 0.80, 0.05)

    elif pagina == "🎯 Zonas Prioritárias":
        st.info("Mapa gerencial de suporte à decisão para direcionamento de políticas públicas.")
        opacidade = st.slider("Opacidade", 0.1, 1.0, 0.85, 0.05)

    st.divider()
    basemap = st.selectbox(
        "Mapa base",
        ["OpenStreetMap", "CartoDB Positron", "Esri Satellite"],
    )
    st.button("🔄 Resetar Zoom do Mapa", on_click=resetar_visao_mapa, use_container_width=True)

# ── Página: Temperatura e Hotspots ────────────────────────────────────────────
if pagina == "🌡️ Temperatura e Hotspots":
    st.subheader(f"🌡️ {camada} — Jundiaí/SP · {ano}")

    with st.spinner("Carregando dados..."):
        banda_num = BANDAS[camada]
        dados, bounds, _ = carregar_banda(ano, banda_num)
        lst, _, _        = carregar_banda(ano, 1)

    lst_valido = lst[np.isfinite(lst)]
    media   = float(np.nanmean(lst_valido))
    desvio  = float(np.nanstd(lst_valido))
    limiar  = media + 2 * desvio
    n_hot   = int(np.sum(lst_valido > limiar))
    pct_hot = 100 * n_hot / len(lst_valido)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LST Média", f"{media:.1f} °C")
    c2.metric("LST Máxima", f"{float(np.nanmax(lst_valido)):.1f} °C")
    c3.metric("Limiar hotspot", f"{limiar:.1f} °C")
    c4.metric("Área de hotspot", f"{pct_hot:.1f}%")

    hotspot_mask = calcular_hotspots(lst) if mostrar_hotspots else None
    
    m = construir_mapa(
        raster       = dados,
        bounds       = bounds,
        camada_nome  = f"{camada} · {ano}",
        cmap         = _cmap_para_banda(banda_num),
        opacidade    = opacidade,
        centro       = st.session_state.map_center,
        zoom         = st.session_state.map_zoom,
        basemap      = basemap,
        hotspot_mask = hotspot_mask,
    )
    
    renderizar_mapa_preservando_zoom(m, key_mapa="mapa_temp_hotspots")

    with st.expander("ℹ️ Como interpretar"):
        _texto_interpretacao(camada)

# ── Página: Persistência ──────────────────────────────────────────────────────
elif pagina == "📍 Persistência de Hotspots":
    st.subheader("📍 Persistência Espacial de Hotspots · 2017–2025")

    if len(anos_sel) < 2:
        st.warning("Selecione pelo menos 2 anos para calcular persistência.")
        st.stop()

    with st.spinner("Calculando persistência..."):
        persistencia, bounds_ref = obter_persistencia_cacheada(tuple(sorted(anos_sel)))

    PIXEL_KM2 = (30 * 30) / 1e6
    n_anos = len(anos_sel)

    # Métricas dinâmicas consistentes com a quantidade de anos selecionados
    scores_unicos = sorted(list({max(2, n_anos - 1), n_anos}))
    cols = st.columns(len(scores_unicos) + 1)
    cols[0].metric("Anos analisados", n_anos)
    for idx, score in enumerate(scores_unicos):
        n_pixels = int(np.sum(persistencia >= score))
        label = f"≥ {score} anos" if score < n_anos else f"Crônico ({n_anos} anos)"
        cols[idx + 1].metric(label, f"{n_pixels * PIXEL_KM2:.1f} km²")

    m = construir_mapa(
        raster      = persistencia,
        bounds      = bounds_ref,
        camada_nome = "Persistência (anos)",
        cmap        = "persistencia",
        opacidade   = opacidade,
        centro      = st.session_state.map_center,
        zoom        = st.session_state.map_zoom,
        basemap     = basemap,
        vmin        = 0,
        vmax        = n_anos,
    )
    
    renderizar_mapa_preservando_zoom(m, key_mapa="mapa_persistencia")

    st.markdown(_legenda_persistencia(n_anos), unsafe_allow_html=True)

    with st.expander("ℹ️ Como interpretar"):
        st.markdown(
            "**0** — Nunca foi hotspot no período analisado  \n"
            "**1–2** — Hotspot emergente ou transitório (expansão urbana recente)  \n"
            "**3** — Hotspot intermitente  \n"
            f"**{n_anos-1}–{n_anos}** — Hotspot crônico estrutural "
            "(intervenção prioritária)"
        )

# ── Página: Zonas Prioritárias ────────────────────────────────────────────────
elif pagina == "🎯 Zonas Prioritárias":
    st.subheader("🎯 Zonas Prioritárias para Intervenção")
    st.markdown("Cruzamento da **Persistência de Calor** com o **Déficit de Vegetação (NDVI)** para direcionamento de recursos.")

    limiar_ndvi = st.slider(
        "Limiar Crítico de NDVI (Baseado na inflexão do SHAP)",
        min_value=0.0, max_value=0.8, value=0.40, step=0.05,
        help="Valores de NDVI abaixo deste limiar perdem a capacidade termodinâmica de mitigar a ilha de calor."
    )

    with st.spinner("Cruzando matrizes e calculando prioridades..."):
        # 1. Obtém persistência já em cache (instantâneo ao mover o slider de NDVI!)
        persistencia, bounds_ref = obter_persistencia_cacheada(tuple(ANOS))

        # 2. Carrega NDVI do ano mais recente (2025)
        ndvi_2025, _, _ = carregar_banda(2025, 2)

        # 3. Inicia matriz de prioridades vazia
        prioridade = np.full(persistencia.shape, np.nan, dtype=np.float32)

        # 4. Define as Condicionais Lógicas
        c_cronico       = persistencia >= 4
        c_intermitente  = (persistencia == 2) | (persistencia == 3)
        c_ndvi_baixo    = ndvi_2025 < limiar_ndvi
        c_ndvi_razoavel = ndvi_2025 >= limiar_ndvi

        # Aplica as regras de negócio
        prioridade[c_intermitente & c_ndvi_baixo] = 1   # Amarelo
        prioridade[c_cronico & c_ndvi_razoavel]   = 2   # Laranja
        prioridade[c_cronico & c_ndvi_baixo]      = 3   # Vermelho

        # Aplica máscara do contorno do município (já herdada de persistencia)
        prioridade[np.isnan(persistencia)] = np.nan

    # Estatísticas de Área
    PIXEL_KM2 = (30 * 30) / 1e6
    area_vermelha = np.sum(prioridade == 3) * PIXEL_KM2
    area_laranja  = np.sum(prioridade == 2) * PIXEL_KM2
    area_amarela  = np.sum(prioridade == 1) * PIXEL_KM2

    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 Intervenção Urgente", f"{area_vermelha:.1f} km²")
    c2.metric("🟠 Monitoramento", f"{area_laranja:.1f} km²")
    c3.metric("🟡 Prevenção", f"{area_amarela:.1f} km²")

    m = construir_mapa(
        raster      = prioridade,
        bounds      = bounds_ref,
        camada_nome = "Prioridade de Intervenção",
        cmap        = "prioridades",
        opacidade   = opacidade,
        centro      = st.session_state.map_center,
        zoom        = st.session_state.map_zoom,
        basemap     = basemap,
        vmin        = 1,
        vmax        = 3,
    )
    
    renderizar_mapa_preservando_zoom(m, key_mapa="mapa_prioridades")

    st.markdown("""
<div style='padding:16px; background-color:#f8f9fa; border-radius:8px; border-left: 5px solid #007bff; margin-top:10px;'>
<h4 style='margin-top:0; color:#333;'>Guia de Ação para o Gestor Público</h4>

<div style="margin-bottom:8px;">
<span style="background:#f44336;display:inline-block;width:18px;height:18px;border-radius:4px;vertical-align:middle;margin-right:8px; border:1px solid #ccc;"></span>
<strong>Intervenção Urgente (Vermelho):</strong> Hotspots crônicos (≥ 4 anos) com grave déficit de vegetação.<br>
<span style="color:#555; font-size:0.9em; margin-left:30px;"><em>Ação Recomendada:</em> Prioridade 1 para campanhas de arborização viária, incentivos a telhados verdes e exigência imediata de cota de permeabilidade em novos lotes.</span>
</div>

<div style="margin-bottom:8px;">
<span style="background:#ff9800;display:inline-block;width:18px;height:18px;border-radius:4px;vertical-align:middle;margin-right:8px; border:1px solid #ccc;"></span>
<strong>Monitorar (Laranja):</strong> Hotspots crônicos que já possuem vegetação razoável.<br>
<span style="color:#555; font-size:0.9em; margin-left:30px;"><em>Ação Recomendada:</em> A anomalia térmica aqui provavelmente não será resolvida com mais árvores. Investigar fatores omitidos como densidade de construção (cânion urbano) ou calor antropogênico.</span>
</div>

<div>
<span style="background:#ffeb3b;display:inline-block;width:18px;height:18px;border-radius:4px;vertical-align:middle;margin-right:8px; border:1px solid #ccc;"></span>
<strong>Prevenção (Amarelo):</strong> Áreas que aquecem de forma intermitente e possuem pouca vegetação.<br>
<span style="color:#555; font-size:0.9em; margin-left:30px;"><em>Ação Recomendada:</em> Foco preventivo do Plano Diretor para evitar que essas áreas se consolidem como ilhas de calor estruturais no médio prazo.</span>
</div>
</div>
""", unsafe_allow_html=True)
