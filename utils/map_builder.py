"""
utils/map_builder.py
--------------------
Constrói mapas interativos a partir de arrays NumPy com cache de renderização PNG.
"""

import io
import base64
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import leafmap.foliumap as leafmap
import folium
from PIL import Image

# Paleta sequencial para Persistência (0 a 5 anos)
CORES_PERSISTENCIA = ["#f4f4f5", "#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]

# Paleta categórica para as Zonas Prioritárias (1=Amarelo, 2=Laranja, 3=Vermelho)
CORES_PRIORIDADES = ["#ffeb3b", "#ff9800", "#f44336"]

# Configuração direta de Tiles (evita carregar OpenStreetMap em duplicidade no fundo)
TILES_CONFIG = {
    "OpenStreetMap": {
        "tiles": "OpenStreetMap",
        "attr": "© OpenStreetMap contributors",
    },
    "CartoDB Positron": {
        "tiles": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        "attr": "© OpenStreetMap contributors © CARTO",
    },
    "Esri Satellite": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attr": "Tiles © Esri",
    },
}


@st.cache_data(show_spinner=False, max_entries=32)
def _raster_para_b64(
    arr: np.ndarray,
    cmap_nome: str,
    vmin: float,
    vmax: float,
    n_cores: int = None,
) -> str:
    """
    Converte array NumPy 2D para string Data URL (PNG Base64 RGBA).
    Cacheado para que alterações de opacidade, zoom ou basemap sejam instantâneas.
    """
    mask_valido = np.isfinite(arr)
    if not np.any(mask_valido):
        return ""

    # 1. Seleção de Colormap e Normalização (Discreta vs Contínua)
    if cmap_nome == "persistencia":
        n_classes = int(vmax) + 1
        cores_ativas = CORES_PERSISTENCIA[:n_classes]
        cmap = mcolors.ListedColormap(cores_ativas)
        limites = np.arange(-0.5, n_classes + 0.5, 1.0)
        norm = mcolors.BoundaryNorm(limites, cmap.N)

    elif cmap_nome == "prioridades":
        cmap = mcolors.ListedColormap(CORES_PRIORIDADES)
        limites = [0.5, 1.5, 2.5, 3.5]
        norm = mcolors.BoundaryNorm(limites, cmap.N)

    else:
        cmap = plt.get_cmap(cmap_nome, n_cores) if n_cores else plt.get_cmap(cmap_nome)
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax, clip=True)

    # 2. Mapeamento RGBA vetorizado sem warnings de NaN
    arr_limpo = np.where(mask_valido, arr, vmin)
    rgba = cmap(norm(arr_limpo))
    rgba[~mask_valido] = [0.0, 0.0, 0.0, 0.0]  # Transparente fora do município

    # 3. Exportação rápida para PNG em memória
    rgba_uint8 = (rgba * 255).astype(np.uint8)
    img = Image.
