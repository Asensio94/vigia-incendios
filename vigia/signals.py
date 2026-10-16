"""Fires as signals, the common format of the sibling projects (signals.json).

Estado de las IBA reads site/signals.json to place each fire in its Natura 2000 sites,
municipalities and regions; the format is described in estado-iba's CONTRATO.md. Spanish and
French fires go in the same file, each with its "country"; French ones carry the INSEE code
of their commune. A fire
crosses the sites with its Sentinel-2 burnt area once there is one (see sites_of), and until
then with the extent of its hot pixels, which overstates small fires (a 1 ha fire lights a
14 ha VIIRS pixel).
"""
from __future__ import annotations

from datetime import date, timedelta

from . import config

SOURCE = "vigia-incendios"
WINDOW_DAYS = 365                 # the hub shows a year of fires, whoever sends them
COVERAGE = {"label": "España y Francia metropolitana", "sites": None,
            "note": f"Focos VIIRS de NASA FIRMS de los últimos {WINDOW_DAYS} días; "
                    "superficie quemada con Sentinel-2 cuando la hay."}


def sites_of(i: dict) -> tuple[list[dict], str, float | None, str | None]:
    """The sites a fire burns in, how they were found, its hectares and the state of its perimeter.

    As on the fire's page: once Sentinel-2 has measured the burnt area, the fire is in the sites
    that area reaches and in no other, even if its hot pixels touched one. Under clouds the area
    is only a lower bound, so the sites of the hot pixels are not ruled out and stay, without
    hectares. A perimeter with no area yet, or clouded out entirely, measured nothing: the hot
    pixels decide.
    """
    s2 = i.get("perimetro") or {}
    measured = s2.get("ha") is not None and not (s2.get("nublado") and not s2["ha"])
    if not measured:
        return [{"code": e["codigo"], "ha": e.get("ha")} for e in i.get("natura") or []], "focos", i.get("ha_focos"), None
    sites = [{"code": e["codigo"], "ha": e.get("ha")} for e in s2.get("natura") or []]
    if s2.get("nublado"):
        burnt = {x["code"] for x in sites}
        sites += [{"code": e["codigo"]} for e in i.get("natura") or [] if e["codigo"] not in burnt]
    return sites, "perimetro", s2["ha"], "definitivo" if s2.get("definitivo") else "provisional"


def country_of(i: dict) -> config.Country:
    """The country of a fire, from its id: French ones start with «FR-»."""
    return next((c for c in config.COUNTRIES.values() if c.id_prefix and i["id"].startswith(c.id_prefix)),
                config.ES)


def signal(i: dict) -> dict:
    """One fire of the register as a signal.

    In Spain the municipality goes by name, with its province: vigía has no INE codes and the
    hub resolves the names with the IGN layer. In France geo.api.gouv.fr gives the INSEE code
    of the commune (5 characters, 2A004 in Corsica), and the province is the département.
    """
    sites, precision, ha, status = sites_of(i)
    pais = country_of(i)
    place = i.get("lugar") or {}
    town, province = place.get("municipio"), place.get("provincia")
    if pais.code == "FR":
        title = f"Incendie à {town}" if town else "Incendie, lieu non identifié"
        codes = [place["insee"]] if town and place.get("insee") else []
    else:
        title, codes = f"Incendio en {town or 'lugar sin identificar'}", []
    return {"id": i["id"], "kind": "fire", "country": pais.code, "date": i["primera"][:10],
            "title": title,
            "url": f"{pais.web}#{i['id']}",
            "sites": sites,
            "municipalities": codes,
            "municipality_names": [town] if town else [],
            "provinces": [province] if town and province else [],
            "precision": precision, "deadline": None,
            "status": status,
            "value": {"amount": ha, "unit": "ha"} if ha else None,
            "details": {"province": province, "point": i.get("centro")}}


def document(fires: list[dict], now: str) -> dict:
    """signals.json for the fires first seen in the WINDOW_DAYS before `now` (the register's time)."""
    since = (date.fromisoformat(now[:10]) - timedelta(days=WINDOW_DAYS)).isoformat()
    signals = sorted((signal(i) for i in fires if i["primera"][:10] >= since), key=lambda s: (s["date"], s["id"]))
    return {"source": SOURCE, "version": 1, "generated": now, "coverage": COVERAGE, "signals": signals}
