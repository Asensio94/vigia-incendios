"""Fire perimeter, active front and progression per overpass, after NASA's FEDS.

FEDS (Chen et al. 2022, Scientific Data 9:249) tracks each fire through the 12-hourly VIIRS
overpasses: at every step the perimeter is an alpha shape over all fire pixels seen so far,
merged with the previous perimeter so it never shrinks, and the active front is the stretch
of perimeter next to the newest pixels.

Here the same idea is written as fixed rules that can be redone by hand:

- Each VIIRS pixel is a disc of radius `PIXEL_RADIUS_FACTOR` × half its size. The pixel
  footprint over-estimates small fires (a 375 m pixel is 14 ha, often more than what burnt).
- Pixels seen within `STEP_MERGE_HOURS` of each other form one step (one overpass, or two
  satellites passing a few minutes apart).
- Perimeter at step k = closing(perimeter at k-1 ∪ discs up to k), where the morphological
  closing (buffer +d, then -d, with d = `CLOSING_KM`) fills gaps narrower than 2·d between
  pixels: the land the front crossed between two overpasses. It plays the alpha shape's role.
- Active front at step k = perimeter boundary within `FRONT_KM` of a pixel of step k.

The parameters were chosen on the 2023 season against EFFIS burnt areas and checked on
2024 (see docs/validacion.md), not tuned on the year they are reported for.
"""
from __future__ import annotations

import math

import numpy as np
from shapely import affinity
from shapely.geometry import MultiLineString, Point, mapping
from shapely.ops import unary_union

from . import config, focos as F

MAX_STEPS = 60  # progression rows kept per fire (the most recent)
FIELDS = ("perimeter_ha", "steps", "front_km", "front_t", "max_growth_ha_h", "progression",
          "perimeter", "front")


def _to_km(lat0: float):
    kx, ky = 111.32 * math.cos(math.radians(lat0)), 110.57
    return kx, ky


def _discs(fs: list[dict], kx: float, ky: float, factor: float):
    return [Point(f["lon"] * kx, f["lat"] * ky).buffer(factor * 0.5 * math.sqrt(f["scan"] * f["track"]), 16)
            for f in fs]


def _close(g, d: float):
    return g if d <= 0 else g.buffer(d, 16).buffer(-d, 16)


def _steps(fs: list[dict]) -> list[list[dict]]:
    """Pixels grouped into overpass steps, in time order."""
    fs = sorted(fs, key=lambda f: f["t"])
    out: list[list[dict]] = []
    for f in fs:
        if out and F.horas_entre(out[-1][0]["t"], f["t"]) <= config.STEP_MERGE_HOURS:
            out[-1].append(f)
        else:
            out.append([f])
    return out


def geometry(fs: list[dict], factor: float | None = None, closing_km: float | None = None):
    """Final perimeter in degrees (used by the validation to compare against EFFIS)."""
    return track(fs, factor, closing_km)["_geom"]


def track(fs: list[dict], factor: float | None = None, closing_km: float | None = None) -> dict:
    """Perimeter, front and progression of one fire. VIIRS pixels only, MODIS if there are none."""
    factor = config.PIXEL_RADIUS_FACTOR if factor is None else factor
    closing_km = config.CLOSING_KM if closing_km is None else closing_km
    px = [f for f in fs if f["sensor"] == "VIIRS"] or fs
    lat0 = float(np.mean([f["lat"] for f in px]))
    kx, ky = _to_km(lat0)

    perim = None
    rows = []
    front = None
    t_prev = None
    for step in _steps(px):
        discs = unary_union(_discs(step, kx, ky, factor))
        perim = _close(discs if perim is None else unary_union([perim, discs]), closing_km)
        near = discs.buffer(config.FRONT_KM, 16)
        line = perim.boundary.intersection(near)
        front = line if not line.is_empty else None
        ha = perim.area * 100
        t = step[0]["t"]
        row = {"t": t, "ha": round(ha, 1), "pixels": len(step),
               "frp": round(sum(f["frp"] for f in step), 1),
               "front_km": round(front.length, 2) if front is not None else 0.0}
        if t_prev is not None:
            h = F.horas_entre(t_prev["t"], t)
            row["growth_ha_h"] = round((ha - t_prev["ha"]) / h, 1) if h >= 1 else None
        rows.append(row)
        t_prev = {"t": t, "ha": ha}

    def to_deg(g):
        return affinity.scale(g, 1 / kx, 1 / ky, origin=(0, 0))

    perim_deg = to_deg(perim)
    growth = [r["growth_ha_h"] for r in rows if r.get("growth_ha_h") is not None]
    out = {
        "_geom": perim_deg,
        "perimeter_ha": round(perim.area * 100, 1),
        "steps": len(rows),
        "front_km": rows[-1]["front_km"],
        "front_t": rows[-1]["t"],
        "max_growth_ha_h": max(growth) if growth else None,
        "progression": rows[-MAX_STEPS:],
    }
    if front is not None:
        lines = front.geoms if hasattr(front, "geoms") else [front]
        lines = [l for l in lines if l.geom_type == "LineString"]
        if lines:
            out["_front"] = to_deg(MultiLineString(lines))
    return out


def describe(fs: list[dict]) -> dict | None:
    """Fields stored on the fire: perimeter and front as GeoJSON, plus the progression."""
    n_viirs = sum(f["sensor"] == "VIIRS" for f in fs)
    if n_viirs < config.PERIMETER_MIN_VIIRS:
        return None
    from .zonas import _redondear
    r = track(fs)
    if r["_geom"].is_empty:
        return None
    out = {k: v for k, v in r.items() if not k.startswith("_")}
    out["perimeter"] = _redondear(mapping(r["_geom"].simplify(0.0002)), 5)
    if "_front" in r:
        out["front"] = _redondear(mapping(r["_front"].simplify(0.0002)), 5)
    return out
