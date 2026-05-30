"""
utils/data_loader.py
--------------------
Carrega os GeoTIFFs diretamente da pasta local data/.
"""

import os
import numpy as np
import rasterio
import streamlit as st

DATA_DIR = "data"
ANOS     = [2017, 2019, 2021, 2023, 2025]

def listar_arquivos_disponiveis() -> list[int]:
    """Retorna lista de anos com TIF disponível em data/."""
    return [
        a for a in ANOS
        if os.path.exists(os.path.join(DATA_DIR, f"Jundiai_SUHI_{a}.tif"))
    ]

@st.cache_data(show_spinner=False)
def carregar_banda(ano: int, banda_num: int):
    """
    Carrega uma banda específica do GeoTIFF de um ano local.

    Bandas:
        1 = LST (°C)
        2 = NDVI
        3 = NDBI
        4 = MNDWI

    Retorna:
        data   : np.ndarray float32 (NaN onde não há dado)
        bounds : rasterio.coords.BoundingBox
        crs    : rasterio.crs.CRS
    """
    path = os.path.join(DATA_DIR, f"Jundiai_SUHI_{ano}.tif")
    
    if not os.path.exists(path):
        st.error(f"Ficheiro não encontrado: {path}")
        st.stop()

    with rasterio.open(path) as src:
        data   = src.read(banda_num).astype(np.float32)
        bounds = src.bounds
        crs    = src.crs

    # Mascara pixels inválidos para evitar distorções
    if banda_num == 1:  # LST
        data[(data <= 0) | (data > 65)] = np.nan
    else:  # índices espectrais (-1 a +1)
        data[np.abs(data) > 1.5] = np.nan

    return data, bounds, crs

@st.cache_data(show_spinner=False)
def carregar_mapbiomas(ano: int):
    """
    Carrega o TIF de classificação MapBiomas de um ano.
    Se a sua aplicação ainda o exigir para alguma visualização futura.
    """
    path = os.path.join(DATA_DIR, f"Jundiai_MapBiomas_{ano}.tif")
    
    if not os.path.exists(path):
        return None, None, None

    with rasterio.open(path) as src:
        data   = src.read(1).astype(np.float32)
        bounds = src.bounds
        crs    = src.crs

    return data, bounds, crs
