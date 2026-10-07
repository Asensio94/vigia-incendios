"""Superficie quemada con Sentinel-2: dNBR entre antes y después del fuego, anclado a los focos.

El NBR, (NIR − SWIR) / (NIR + SWIR) con las bandas B8A y B12 a 20 m, baja mucho cuando
arde la vegetación: cae el infrarrojo cercano de las hojas y sube el de onda corta del
suelo y la ceniza. La diferencia entre antes y después (dNBR) es el índice estándar de
área quemada y de severidad.

- Antes: mediana de las escenas despejadas de las semanas previas al primer foco.
- Después: el segundo NBR más bajo de cada píxel desde el primer foco hasta unos días
  después del último (el único, si solo hay uno). Recoge todo el avance aunque cada escena
  tenga nubes distintas, y pide que el cambio se vea en dos pasadas: una cicatriz de
  incendio sigue ahí en la siguiente, una neblina o una sombra que la máscara de nubes no
  vio, no. Con el mínimo a secas, una sola escena turbia pintaba de quemado medio valle.
- Perímetro: píxeles con dNBR por encima del umbral, cerca de la huella de focos y
  unidos a ella. Sin ese anclaje entraría cualquier cosecha o labrado del mismo periodo,
  que también baja el NBR.

Son reglas fijas: umbrales en config.py, contrastados con los perímetros de EFFIS.
"""
from __future__ import annotations

import hashlib
import logging
import time
import warnings
from datetime import datetime, timedelta

import numpy as np
from odc.geo.geobox import GeoBox
from odc.geo.geom import Geometry
from odc.stac import configure_rio, load
from pystac_client import Client
from rasterio import features
from scipy import ndimage
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from . import config, focos as F, zonas

log = logging.getLogger(__name__)
logging.getLogger("rasterio").setLevel(logging.WARNING)   # un INFO por cada tesela leída
configure_rio(cloud_defaults=True, aws={"aws_unsigned": True})
_cliente: Client | None = None


# ── Escenas ─────────────────────────────────────────────────────────────────────────────

def _client() -> Client:
    global _cliente
    if _cliente is None:
        _cliente = Client.open(config.STAC_URL)
    return _cliente


def buscar(bbox_geo, inicio: datetime, fin: datetime, nubes_max: float) -> list:
    s = _client().search(
        collections=[config.STAC_COLECCION], bbox=list(bbox_geo),
        datetime=f"{inicio:%Y-%m-%dT%H:%M:%SZ}/{fin:%Y-%m-%dT%H:%M:%SZ}",
        query={"eo:cloud_cover": {"lt": nubes_max}}, max_items=None)
    # Earth Search publica a veces el mismo producto dos veces (reprocesados): se queda la
    # versión más reciente de cada tesela, fecha y satélite.
    mejores: dict[tuple, object] = {}
    for it in s.items():
        clave = (it.properties.get("grid:code"), it.datetime.date(), it.properties.get("platform"))
        prev = mejores.get(clave)
        if prev is None or str(it.properties.get("s2:processing_baseline")) > str(prev.properties.get("s2:processing_baseline")):
            mejores[clave] = it
    return sorted(mejores.values(), key=lambda i: i.datetime)


def desplazamiento_nd(item) -> int:
    """Niveles digitales que hay que restar a la reflectancia de una escena.

    Desde la baseline 04.00 (2022) los L2A suman 1000 a cada nivel digital; Earth Search
    lo resta y lo marca, salvo en algunos productos (Sentinel-2C en su puesta en marcha).
    Sin corregirlo, el NBR sale sesgado hacia cero. Igual que en el Centinela Natura.
    """
    p = item.properties
    if str(p.get("s2:processing_baseline", "00.00")) < "04.00" or p.get("earthsearch:boa_offset_applied"):
        return 0
    try:
        b = item.assets["nir08"].extra_fields["raster:bands"][0]
        return int(round(-b["offset"] / b["scale"]))
    except (KeyError, IndexError, TypeError, ZeroDivisionError):
        return 1000


def _serie_nbr(items: list, gb: GeoBox, clases: tuple[int, ...]) -> tuple[list[np.ndarray], list[str]]:
    """NBR de cada día de paso, con NaN donde la SCL no es una de `clases`."""
    grupos: dict[int, list] = {}
    for it in items:
        grupos.setdefault(desplazamiento_nd(it), []).append(it)
    capas, fechas = [], []
    for resta, grupo in grupos.items():
        ds = load(grupo, bands=["nir08", "swir22", "scl"], geobox=gb, groupby="solar_day",
                  resampling="nearest", fail_on_error=False)
        nir_nd, sw_nd, scl = (ds[b].values for b in ("nir08", "swir22", "scl"))
        nir = (nir_nd.astype("float32") - resta) * 1e-4
        sw = (sw_nd.astype("float32") - resta) * 1e-4
        ok = (nir_nd > resta) & (sw_nd > resta) & np.isin(scl, clases) & (nir + sw > 0.02)
        nbr = np.where(ok, (nir - sw) / np.maximum(nir + sw, 1e-6), np.nan)
        for k, t in enumerate(ds.time.values):
            if ok[k].any():
                capas.append(nbr[k])
                fechas.append(str(t)[:10])
    return capas, fechas


# ── Cálculo ─────────────────────────────────────────────────────────────────────────────

def crs_utm(lon: float) -> str:
    return f"EPSG:{32600 + int((lon + 180) // 6) + 1}"


def escenas(huella_geo, primera: datetime, ultima: datetime, hasta: datetime) -> dict:
    """Malla de cálculo y escenas de antes y después. Solo consulta el catálogo: es barato."""
    crs = crs_utm(huella_geo.centroid.x)
    g = Geometry(huella_geo, "EPSG:4326").to_crs(crs)
    x0, y0, x1, y1 = g.boundingbox
    m = config.PERIMETRO_MARGEN_M
    gb = GeoBox.from_bbox((x0 - m, y0 - m, x1 + m, y1 + m), crs=crs, resolution=config.PERIMETRO_RES_M)
    bbox_geo = gb.extent.to_crs("EPSG:4326").boundingbox

    pre_items = buscar(bbox_geo, primera - timedelta(days=config.PRE_DIAS), primera - timedelta(hours=12),
                       config.PRE_NUBES_MAX)[-config.PRE_ESCENAS_MAX:]
    fin = min(ultima + timedelta(days=config.POST_DIAS), hasta)
    post_items = buscar(bbox_geo, primera, fin, config.POST_NUBES_MAX)
    # Todas las de mientras arde (recogen el avance) y las primeras de después del último foco.
    tras = [it for it in post_items if it.datetime > ultima]
    post_items = [it for it in post_items if it.datetime <= ultima] + tras[:config.POST_ESCENAS_TRAS]
    return {"g": g, "gb": gb, "crs": crs, "pre": pre_items, "post": post_items}


def dnbr(huella_geo, primera: datetime, ultima: datetime, hasta: datetime, esc: dict | None = None) -> dict | None:
    """dNBR alrededor de la huella de focos y lo necesario para recortar el perímetro.

    None si falta imagen de antes o de después.
    """
    esc = esc or escenas(huella_geo, primera, ultima, hasta)
    g, gb, crs = esc["g"], esc["gb"], esc["crs"]
    if not esc["pre"] or not esc["post"]:
        return None
    pre, _ = _serie_nbr(esc["pre"], gb, config.SCL_PRE)
    post, fechas = _serie_nbr(esc["post"], gb, config.SCL_POST)
    if not pre or not post:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)       # píxeles sin ninguna observación
        nbr_pre = np.nanmedian(np.stack(pre), axis=0)
        pila = np.sort(np.stack(post), axis=0)              # los NaN quedan al final
        nbr_min = pila[0]
        n_obs = np.isfinite(pila).sum(axis=0)
        nbr_post = np.where(n_obs >= 2, pila[min(1, len(pila) - 1)], nbr_min)
    huella = features.rasterize([(g.geom, 1)], out_shape=gb.shape, transform=gb.affine,
                                all_touched=True, dtype="uint8").astype(bool)
    return {"dnbr": nbr_pre - nbr_post, "dnbr_min": nbr_pre - nbr_min, "huella": huella, "gb": gb, "crs": crs,
            "post_fechas": sorted(set(fechas)), "pre_escenas": len(pre)}


def recortar(d: dict, umbral: float = None, margen_m: float = None, capa: str = "dnbr") -> np.ndarray:
    """Máscara del área quemada: dNBR > umbral, a menos de `margen_m` de la huella de focos y
    en manchas que tocan la huella."""
    umbral = config.DNBR_UMBRAL if umbral is None else umbral
    margen_m = config.PERIMETRO_ANCLA_M if margen_m is None else margen_m
    # Distancia de cada píxel a la huella, una vez por incendio. Dilatar con un disco de
    # 150 píxeles de radio costaba minutos; la transformada de distancia es lineal.
    if "distancia_m" not in d:
        d["distancia_m"] = ndimage.distance_transform_edt(~d["huella"]) * config.PERIMETRO_RES_M
    zona = d["distancia_m"] <= margen_m
    cand = (np.nan_to_num(d[capa], nan=-1) > umbral) & zona
    cand = ndimage.binary_closing(cand, structure=np.ones((3, 3)), border_value=0) & zona
    lab, _ = ndimage.label(cand, structure=np.ones((3, 3)))
    keep = np.unique(lab[d["huella"] & cand])
    mask = np.isin(lab, keep[keep > 0])
    # Huecos de menos de media hectárea: ruido del índice, no islas sin quemar.
    huecos, n = ndimage.label(~mask)
    if n:
        tam = ndimage.sum(np.ones_like(huecos), huecos, index=np.arange(1, n + 1))
        pequenos = np.flatnonzero(tam * config.PERIMETRO_RES_M ** 2 < 5000) + 1
        mask |= np.isin(huecos, pequenos)
    return mask


def resultado(d: dict, mask: np.ndarray) -> dict:
    """Perímetro en WGS84, superficie, severidad y cobertura de la imagen de después."""
    px_ha = config.PERIMETRO_RES_M ** 2 / 10_000
    v = d["dnbr"][mask]
    sev = {nombre: round(float(((v >= lo) & (v < hi)).sum()) * px_ha, 1)
           for nombre, lo, hi in config.SEVERIDAD}
    polis = [shape(p) for p, val in features.shapes(mask.astype("uint8"), mask=mask,
                                                    transform=d["gb"].affine) if val]
    geom = None
    if polis:
        u = unary_union(polis).simplify(config.PERIMETRO_RES_M)
        geom = Geometry(u, d["crs"]).to_crs("EPSG:4326").geom
    zona = ndimage.binary_dilation(d["huella"], iterations=3)
    return {"ha": round(float(mask.sum()) * px_ha, 1), "severidad": sev, "geom": geom,
            "imagenes": d["post_fechas"],
            "cobertura": round(float((~np.isnan(d["dnbr"][zona])).mean()), 2)}


def calcular(huella_geo, primera: datetime, ultima: datetime, hasta: datetime) -> dict | None:
    d = dnbr(huella_geo, primera, ultima, hasta)
    if d is None:
        return None
    return resultado(d, recortar(d))


# ── Producción ──────────────────────────────────────────────────────────────────────────

def _candidato(inc: dict, ahora: str) -> bool:
    """Incendios que merecen perímetro: no aislados y aún dentro del plazo de imágenes."""
    if inc.get("estado") == "unido" or not inc.get("geometry"):
        return False
    if not (inc.get("n_focos", 0) >= config.PERIMETRO_MIN_FOCOS or inc.get("natura") or inc.get("effis")):
        return False
    # Dos días más que POST_DIAS, para dar tiempo a que el catálogo publique la última escena.
    return F.horas_entre(inc["ultima"], ahora) <= (config.POST_DIAS + 2) * 24


def actualizar(incendios: list[dict], ahora: str) -> dict:
    """Calcula o rehace el perímetro de Sentinel-2 de los incendios que lo necesitan.

    Cada incendio se revisa en el catálogo como mucho cada PERIMETRO_CADA_HORAS y solo se
    recalcula si cambiaron sus focos o sus escenas. Los más grandes van primero; lo que no
    quepa en PERIMETRO_PRESUPUESTO_S queda para la vuelta siguiente.
    """
    inicio = time.monotonic()
    cand = sorted((i for i in incendios if _candidato(i, ahora)), key=lambda i: -i.get("n_focos", 0))
    res = {"candidatos": len(cand), "revisados": 0, "calculados": 0, "pendientes": 0}
    for inc in cand:
        prev = inc.get("perimetro") or {}
        if prev.get("revisado") and F.horas_entre(prev["revisado"], ahora) < config.PERIMETRO_CADA_HORAS:
            continue
        if time.monotonic() - inicio > config.PERIMETRO_PRESUPUESTO_S:
            res["pendientes"] += 1
            continue
        t0, t1 = F._dt(inc["primera"]), F._dt(inc["ultima"])
        try:
            esc = escenas(shape(inc["geometry"]), t0, t1, F._dt(ahora))
        except Exception as e:                    # catálogo caído: se reintenta en otra vuelta
            log.warning("%s: sin catálogo de Sentinel-2 (%s)", inc["id"], e)
            continue
        res["revisados"] += 1
        ids = sorted(it.id for it in esc["pre"] + esc["post"])
        clave = f"{inc['n_focos']}|" + hashlib.sha1(",".join(ids).encode()).hexdigest()[:12]
        if prev.get("clave") == clave:
            prev["revisado"] = ahora
            continue
        try:
            d = dnbr(None, t0, t1, F._dt(ahora), esc=esc)
        except Exception as e:                    # una escena rota no tumba la vuelta
            log.warning("%s: perímetro fallido (%s)", inc["id"], str(e)[:200])
            continue
        res["calculados"] += 1
        tras = sum(it.datetime > t1 for it in esc["post"])
        nuevo = {"clave": clave, "revisado": ahora, "calculado": ahora,
                 # Definitivo cuando ya entraron todas las escenas de después que se usan.
                 "definitivo": tras >= config.POST_ESCENAS_TRAS or
                               F.horas_entre(inc["ultima"], ahora) > config.POST_DIAS * 24}
        if d is None:
            nuevo["sin_imagen"] = True
        else:
            r = resultado(d, recortar(d))
            g = r.pop("geom")
            nuevo.update(r)
            if r["cobertura"] < config.PERIMETRO_COBERTURA_MIN:
                # Sin cielo despejado sobre los focos no se da por cerrado mientras queden días.
                nuevo["nublado"] = True
                nuevo["definitivo"] = F.horas_entre(inc["ultima"], ahora) > config.POST_DIAS * 24
            nuevo["natura"] = [{k: e[k] for k in ("codigo", "nombre", "tipo", "ha") if k in e}
                               for e in zonas.natura_de(g)] if g is not None else []
            nuevo["geometry"] = zonas._redondear(mapping(g), 5) if g is not None else None
        inc["perimetro"] = nuevo
    res["segundos"] = round(time.monotonic() - inicio)
    return res
