"""Fires as signals, the common format of the sibling projects (signals.json).

Estado de las IBA reads site/signals.json to place each fire in its Natura 2000 sites,
municipalities and regions; the format is described in estado-iba's CONTRATO.md. A fire
crosses the sites with its Sentinel-2 burnt area when that area touches one, and otherwise
with the extent of its hot pixels, which overstates small fires (a 1 ha fire lights a 14 ha
VIIRS pixel).
"""
from __future__ import annotations

from datetime import date, timedelta

from . import config

SOURCE = "vigia-incendios"
WINDOW_DAYS = 365                 # the hub shows a year of fires, whoever sends them
COVERAGE = {"label": "Toda España", "sites": None,
            "note": f"Focos VIIRS de NASA FIRMS de los últimos {WINDOW_DAYS} días; "
                    "superficie quemada con Sentinel-2 cuando la hay."}


def signal(i: dict) -> dict:
    """One fire of the register as a signal.

    The municipality goes by name, with its province: vigía has no INE codes and the hub
    resolves the names with the IGN layer.
    """
    s2 = i.get("perimetro") or {}
    natura, precision = (s2["natura"], "perimetro") if s2.get("natura") else (i.get("natura") or [], "focos")
    ha = s2.get("ha") if s2.get("natura") else i.get("ha_focos")
    place = i.get("lugar") or {}
    town, province = place.get("municipio"), place.get("provincia")
    return {"id": i["id"], "kind": "fire", "date": i["primera"][:10],
            "title": f"Incendio en {town or 'lugar sin identificar'}",
            "url": f"{config.WEB}#{i['id']}",
            "sites": [{"code": e["codigo"], "ha": e.get("ha")} for e in natura],
            "municipalities": [],
            "municipality_names": [town] if town else [],
            "provinces": [province] if town and province else [],
            "precision": precision, "deadline": None,
            "status": "definitivo" if s2.get("definitivo") else "provisional" if s2 else None,
            "value": {"amount": ha, "unit": "ha"} if ha else None,
            "details": {"province": province, "point": i.get("centro")}}


def document(fires: list[dict], now: str) -> dict:
    """signals.json for the fires first seen in the WINDOW_DAYS before `now` (the register's time)."""
    since = (date.fromisoformat(now[:10]) - timedelta(days=WINDOW_DAYS)).isoformat()
    signals = sorted((signal(i) for i in fires if i["primera"][:10] >= since), key=lambda s: (s["date"], s["id"]))
    return {"source": SOURCE, "version": 1, "generated": now, "coverage": COVERAGE, "signals": signals}
