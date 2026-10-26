"""
utils/map_builder.py
--------------------
Constrói mapas base e camadas (FeatureGroups) para o st_folium sem perder o zoom.
"""

import io
import base64
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import folium
from PIL import Image

CORES_PERSISTENCIA = ["#f4f4f5", "#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]
CORES_PRIORIDADES  = ["#ffeb3b", "#ff9800", "#f44336"]

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
    """Converte array NumPy 2D para string Data URL (PNG Base64 RGBA)."""
    mask_valido = np.isfinite(arr)
    if not np.any(mask_valido):
        return ""

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

    arr_limpo = np.where(mask_valido, arr, vmin)
    rgba = cmap(norm(arr_limpo))
    rgba[~mask_valido] = [0.0, 0.0, 0.0, 0.0]

    rgba_uint8 = (rgba * 255).astype(np.uint8)
    img = Image.fromarray(rgba_uint8, mode="RGBA")
    output = io.BytesIO()
    img.save(output, format="PNG", compress_level=6)
    b64_str = base64.b64encode(output.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


@st.cache_data(show_spinner=False, max_entries=16)
def _hotspot_mask_para_b64(hotspot_mask: np.ndarray) -> str:
    """Converte máscara de hotspots em overlay PNG Base64."""
    mask_bool = (hotspot_mask > 0) & np.isfinite(hotspot_mask)
    if not np.any(mask_bool):
        return ""

    hot_rgba = np.zeros((*hotspot_mask.shape, 4), dtype=np.uint8)
    hot_rgba[mask_bool] = [220, 30, 30, 180]

    hot_img = Image.fromarray(hot_rgba, mode="RGBA")
    hot_buf = io.BytesIO()
    hot_img.save(hot_buf, format="PNG", compress_level=6)
    hot_b64 = base64.b64encode(hot_buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{hot_b64}"


def criar_mapa_base(centro: list, zoom: int, basemap: str) -> folium.Map:
    """
    Cria APENAS o mapa de fundo estático.
    Como ele não recebe o raster diretamente, o st_folium nunca reseta o zoom!
    """
    cfg = TILES_CONFIG.get(basemap, TILES_CONFIG["OpenStreetMap"])
    m = folium.Map(
        location=centro,
        zoom_start=zoom,
        tiles=cfg["tiles"],
        attr=cfg["attr"],
        control_scale=True,
    )
    return m


def construir_camadas(
    raster: np.ndarray,
    bounds,
    camada_nome: str,
    cmap: str = "viridis",
    opacidade: float = 0.7,
    vmin: float = None,
    vmax: float = None,
    simetrico: bool = False,
    n_cores: int = None,
    hotspot_mask: np.ndarray = None,
) -> tuple[folium.FeatureGroup, float, float]:
    """
    Constrói um FeatureGroup contendo o raster e os hotspots para injetar
    via `feature_group_to_add` no st_folium sem recarregar o mapa base.
    """
    valido = raster[np.isfinite(raster)]
    if valido.size > 0:
        if vmin is None:
            vmin = float(np.percentile(valido, 2))
        if vmax is None:
            vmax = float(np.percentile(valido, 98))
        if simetrico:
            lim = max(abs(vmin), abs(vmax))
            vmin, vmax = -lim, lim
    else:
        if vmin is None:
            vmin = 0.0
        if vmax is None:
            vmax = 1.0

    fg = folium.FeatureGroup(name=camada_nome)
    bounds_list = [
        [bounds.bottom, bounds.left],
        [bounds.top,    bounds.right],
    ]

    image_url = _raster_para_b64(
        raster, cmap, vmin=float(vmin), vmax=float(vmax), n_cores=n_cores
    )
    if image_url:
        folium.raster_layers.ImageOverlay(
            image=image_url,
            bounds=bounds_list,
            opacity=float(opacidade),
            name=camada_nome,
            zindex=1,
        ).add_to(fg)

    if hotspot_mask is not None:
        hot_url = _hotspot_mask_para_b64(hotspot_mask)
        if hot_url:
            folium.raster_layers.ImageOverlay(
                image=hot_url,
                bounds=bounds_list,
                opacity=0.85,
                name="Zonas Críticas (Hotspots)",
                zindex=2,
            ).add_to(fg)

    return fg, float(vmin), float(vmax)
