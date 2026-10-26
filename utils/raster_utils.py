"""
utils/raster_utils.py
---------------------
Processamento de rasters: hotspots, persistência, anomalia de LST.
"""

import numpy as np
import streamlit as st
from rasterio.crs import CRS
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds


def calcular_hotspots(lst: np.ndarray, manter_nan: bool = False) -> np.ndarray:
    """
    Método SIUHI: hotspot = LST > média + 2σ.

    Args:
        lst        : Matriz 2D de temperatura de superfície.
        manter_nan : Se True, retorna float32 (1.0, 0.0 e NaN fora do município).
                     Se False, retorna máscara booleana (True = hotspot).
    """
    valido = np.isfinite(lst)
    if not np.any(valido):
        return np.full_like(lst, np.nan, dtype=np.float32) if manter_nan else np.zeros_like(lst, dtype=bool)

     pixels_validos = lst[valido]
    media  = float(np.mean(pixels_validos))
    desvio = float(np.std(pixels_validos))
    limiar = media + 2.0 * desvio

    # Evita RuntimeWarning de comparação com NaN
    mask_hot = np.zeros_like(lst, dtype=bool)
    np.greater(lst, limiar, out=mask_hot, where=valido)

    if manter_nan:
        resultado = np.where(valido, mask_hot.astype(np.float32), np.nan)
        return resultado

    return mask_hot


def calcular_anomalia(lst: np.ndarray) -> np.ndarray:
    """
    LST_anomalia = LST - média_municipal.
    Remove sinal de macroclima, isola variação espacial.
    """
    valido = np.isfinite(lst)
    if not np.any(valido):
        return np.full_like(lst, np.nan, dtype=np.float32)
    return lst - float(np.mean(lst[valido]))


@st.cache_data(show_spinner=False)
def calcular_persistencia(mascaras: list, bounds_ref) -> tuple:
    """
    Soma pixel a pixel as máscaras de hotspot ao longo dos anos.
    Aceita máscaras booleanas ou float32 (com NaN fora do município).

    Retorna:
        persistencia : np.ndarray float32 (0 a N anos, com NaN fora do recorte)
        bounds_ref   : bounds de referência (do primeiro raster)
    """
    if not mascaras:
        return np.zeros((1, 1), dtype=np.float32), bounds_ref

    # Empilha todas as matrizes em um cubo 3D: (n_anos, altura, largura)
    cubo = np.stack([m.astype(np.float32) for m in mascaras], axis=0)

    # Identifica onde pelo menos um ano possui pixel válido (não-NaN)
    valido_total = np.any(np.isfinite(cubo), axis=0)

    # Soma ignorando NaNs e aplica máscara de contorno
    soma = np.nansum(cubo, axis=0).astype(np.float32)
    soma[~valido_total] = np.nan

    return soma, bounds_ref


def alinhar_para(fonte: np.ndarray, bounds_fonte,
                 alvo_shape: tuple, bounds_alvo,
                 crs_str: str = "EPSG:4326") -> np.ndarray:
    """
    Reprojeta `fonte` para a grade de `alvo_shape` com nearest neighbor,
    preservando valores NaN nas bordas externas.
    """
    h0, w0 = fonte.shape
    h1, w1 = alvo_shape
    b0, b1 = bounds_fonte, bounds_alvo

    tf_src = from_bounds(b0.left, b0.bottom, b0.right, b0.top, w0, h0)
    tf_dst = from_bounds(b1.left, b1.bottom, b1.right, b1.top, w1, h1)
    crs    = CRS.from_string(crs_str)

    dst = np.full((h1, w1), np.nan, dtype=np.float32)
    reproject(
        source        = fonte.astype(np.float32),
        destination   = dst,
        src_transform = tf_src,
        src_crs       = crs,
        dst_transform = tf_dst,
        dst_crs       = crs,
        resampling    = Resampling.nearest,
        src_nodata    = np.nan,
        dst_nodata    = np.nan,
    )
    return dst


def estatisticas_por_classe(lst: np.ndarray, classes: np.ndarray,
                            mapa_classes: dict) -> dict:
    """
    Calcula LST média por classe MapBiomas de forma vetorizada.

    Args:
        lst         : array 2D de LST
        classes     : array 2D de códigos MapBiomas
        mapa_classes: {código: nome}

    Retorna dict {nome_classe: (média, n_pixels)}
    """
    valido = np.isfinite(lst) & np.isfinite(classes)
    lst_val = lst[valido]
    cls_val = classes[valido]

    resultado = {}
    for codigo, nome in mapa_classes.items():
        mask_classe = (cls_val == codigo)
        n_pixels = int(np.count_nonzero(mask_classe))
        if n_pixels > 0:
            resultado[nome] = (float(np.mean(lst_val[mask_classe])), n_pixels)
    return resultado
