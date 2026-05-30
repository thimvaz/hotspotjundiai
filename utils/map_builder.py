"""
utils/map_builder.py
--------------------
Constrói mapas Leafmap interativos a partir de arrays NumPy.
"""

import io
import base64
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import leafmap.foliumap as leafmap
import folium
from PIL import Image

# Colormaps nomeados que o matplotlib não tem nativamente
CMAP_PERSISTENCIA = mcolors.ListedColormap(
    ["#f4f4f5", "#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]
)

# NOVO: Colormap categórico para as Zonas Prioritárias
CMAP_PRIORIDADES = mcolors.ListedColormap(
    ["#ffeb3b", "#ff9800", "#f44336"]  # 1=Amarelo, 2=Laranja, 3=Vermelho
)

BASEMAPS = {
    "OpenStreetMap":    "OpenStreetMap",
    "CartoDB Positron": "CartoDB.Positron",
    "Esri Satellite":   "Esri.WorldImagery",
}


def _raster_para_png(
    arr: np.ndarray,
    cmap_nome: str,
    vmin: float,
    vmax: float,
    n_cores: int = None,
) -> bytes:
    """
    Converte array NumPy para PNG RGBA com colormap aplicado.
    Pixels NaN ficam transparentes.
    """
    valido = arr[np.isfinite(arr)]
    if valido.size == 0:
        return b""

    # Normalização
    if cmap_nome == "persistencia":
        cmap = CMAP_PERSISTENCIA
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    elif cmap_nome == "prioridades":
        cmap = CMAP_PRIORIDADES
        norm = mcolors.Normalize(vmin=1, vmax=3) # Fixado nas 3 classes
    else:
        if n_cores:
            cmap = plt.get_cmap(cmap_nome, n_cores)
        else:
            cmap = plt.get_cmap(cmap_nome)
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    # Aplica máscara de NaNs para transparência
    rgba = cmap(norm(arr))
    rgba[~np.isfinite(arr)] = [0, 0, 0, 0]  # Transparente

    # Converte para uint8
    rgba_uint8 = (rgba * 255).astype(np.uint8)

    # Cria imagem PIL e exporta bytes PNG
    img = Image.fromarray(rgba_uint8, mode="RGBA")
    output = io.BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()


def construir_mapa(
    raster: np.ndarray,
    bounds,
    camada_nome: str,
    cmap: str = "viridis",
    opacidade: float = 0.7,
    centro: list = None,
    zoom: int = 12,
    basemap: str = "OpenStreetMap",
    vmin: float = None,
    vmax: float = None,
    simetrico: bool = False,
    n_cores: int = None,
    hotspot_mask: np.ndarray = None,
) -> leafmap.Map:
    """
    Gera um objeto leafmap.Map com o raster e os overlays configurados.
    Recebe as coordenadas de centro e zoom mantidas no estado do Streamlit.
    """
    if centro is None:
        centro = [-23.19, -46.89]

    # --- CÁLCULO DOS LIMITES (VMIN e VMAX) PARA A LEGENDA ---
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
        if vmin is None: vmin = 0
        if vmax is None: vmax = 1
    # --------------------------------------------------------

    # Inicializa o mapa recebendo as coordenadas estáticas exatas
    m = leafmap.Map(center=centro, zoom=zoom, draw_control=False, measure_control=False)

    # Configura mapa de fundo (Tile Provider)
    tile_provider = BASEMAPS.get(basemap, "OpenStreetMap")
    if tile_provider != "OpenStreetMap":
        folium.TileLayer(
            tiles=("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                   if "Positron" in tile_provider
                   else "https://server.arcgisonline.com/ArcGIS/rest/services/"
                        "World_Imagery/MapServer/tile/{z}/{y}/{x}"),
            name=basemap,
            attr="Tiles © " + basemap,
        ).add_to(m)

    # Overlay do raster principal
    png_bytes = _raster_para_png(
        raster, cmap, vmin=vmin, vmax=vmax, n_cores=n_cores
    )
    
    if png_bytes:
        b64_string = base64.b64encode(png_bytes).decode('utf-8')
        image_url = f"data:image/png;base64,{b64_string}"
        
        bounds_list = [
            [bounds.bottom, bounds.left],
            [bounds.top,    bounds.right],
        ]
        
        overlay = folium.raster_layers.ImageOverlay(
            image   = image_url,
            bounds  = bounds_list,
            opacity = opacidade,
            name    = camada_nome,
        )
        overlay.add_to(m)

    # Adiciona a legenda em gradiente (Colorbar) dinamicamente - Exceto nos mapas categóricos
    if cmap not in ["persistencia", "prioridades"]:
        try:
            m.add_colormap(cmap=cmap, vmin=vmin, vmax=vmax, label=camada_nome)
        except Exception:
            pass 

    # Overlay de hotspots (vermelho semi-transparente) se fornecido
    if hotspot_mask is not None:
        hot_rgba = np.zeros((*hotspot_mask.shape, 4), dtype=np.uint8)
        hot_rgba[hotspot_mask] = [220, 30, 30, 180]  # Vermelho com opacidade estável
        
        hot_img = Image.fromarray(hot_rgba, mode="RGBA")
        hot_buf = io.BytesIO()
        hot_img.save(hot_buf, format="PNG")
        
        hot_b64 = base64.b64encode(hot_buf.getvalue()).decode('utf-8')
        hot_url = f"data:image/png;base64,{hot_b64}"
        
        bounds_list = [
            [bounds.bottom, bounds.left],
            [bounds.top,    bounds.right],
        ]
        
        hotspot_overlay = folium.raster_layers.ImageOverlay(
            image   = hot_url,
            bounds  = bounds_list,
            opacity = 0.85,
            name    = "Zonas Críticas (Hotspots)",
        )
        hotspot_overlay.add_to(m)

    # Adiciona controle de camadas nativo do Folium
    folium.LayerControl(position="topright").add_to(m)

    return m
