"""
utils/raster_utils.py
---------------------
Processamento de rasters: hotspots, persistência, anomalia de LST.
"""

import numpy as np
import streamlit as st
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds


def calcular_hotspots(lst: np.ndarray) -> np.ndarray:
    """
    Método SIUHI: hotspot = LST > média + 2σ.

    Retorna máscara booleana (True = hotspot).
    """
    valido = np.isfinite(lst)
    media  = float(np.nanmean(lst[valido]))
    desvio = float(np.nanstd(lst[valido]))
    return (lst > media + 2 * desvio) & valido


def calcular_anomalia(lst: np.ndarray) -> np.ndarray:
    """
    LST_anomalia = LST - média_municipal.
    Remove sinal de macroclima, isola variação espacial.
    """
    return lst - np.nanmean(lst)


@st.cache_data(show_spinner=False)
def calcular_persistencia(mascaras: list, bounds_ref) -> tuple:
    """
    Soma pixel a pixel as máscaras binárias de hotspot.

    Retorna:
        persistencia : np.ndarray int (0 a N anos)
        bounds_ref   : bounds de referência (do primeiro raster)
    """
    if not mascaras:
        return np.zeros((1, 1)), bounds_ref

    # Todas as máscaras devem ter o mesmo shape (grade de 2025)
    base  = mascaras[0].astype(np.float32)
    soma  = np.zeros_like(base, dtype=np.float32)
    valido_total = np.zeros_like(base, dtype=bool)

    for mask in mascaras:
        arr = mask.astype(np.float32)
        soma         += np.where(np.isfinite(arr), arr, 0)
        valido_total |= np.isfinite(arr)

    # Onde nenhum ano tinha dado, mantém NaN
    resultado = soma.copy()
    resultado[~valido_total] = np.nan

    return resultado, bounds_ref


def alinhar_para(fonte: np.ndarray, bounds_fonte,
                  alvo_shape: tuple, bounds_alvo,
                  crs_str: str = "EPSG:4326") -> np.ndarray:
    """
    Reprojeta `fonte` para a grade de `alvo_shape` com nearest neighbor.
    Útil para alinhar rasters de anos diferentes.
    """
    from rasterio.crs import CRS
    h0, w0 = fonte.shape
    h1, w1 = alvo_shape
    b0, b1 = bounds_fonte, bounds_alvo

    tf_src = from_bounds(b0.left, b0.bottom, b0.right, b0.top, w0, h0)
    tf_dst = from_bounds(b1.left, b1.bottom, b1.right, b1.top, w1, h1)
    crs    = CRS.from_string(crs_str)

    dst = np.full((h1, w1), np.nan, dtype=np.float32)
    reproject(
        source      = fonte.astype(np.float32),
        destination = dst,
        src_transform  = tf_src, src_crs = crs,
        dst_transform  = tf_dst, dst_crs = crs,
        resampling  = Resampling.nearest,
    )
    return dst


def estatisticas_por_classe(lst: np.ndarray, classes: np.ndarray,
                              mapa_classes: dict) -> dict:
    """
    Calcula LST média por classe MapBiomas.

    Args:
        lst         : array 2D de LST
        classes     : array 2D de códigos MapBiomas
        mapa_classes: {código: nome}

    Retorna dict {nome_classe: (média, n_pixels)}
    """
    resultado = {}
    for codigo, nome in mapa_classes.items():
        mask = (classes == codigo) & np.isfinite(lst)
        if np.sum(mask) > 0:
            resultado[nome] = (float(np.nanmean(lst[mask])), int(np.sum(mask)))
    return resultado
