"""Per-fire page: isochrones, overpasses and key moments on a synthetic fire."""
import json
import re

import pytest

from vigia import config, ficha, i18n, web

LAT, LON = 40.0, -3.0
KM_LAT, KM_LON = 1 / 110.57, 1 / (111.32 * 0.766)


def _row(y_km: float, t: str, n: int = 4, sat: str = "N20", sensor: str = "VIIRS", frp: float = 10.0) -> list[dict]:
    return [{"lat": LAT + y_km * KM_LAT, "lon": LON + 0.375 * k * KM_LON, "t": t, "sat": sat, "sensor": sensor,
             "scan": 0.375, "track": 0.375, "frp": frp} for k in range(n)]


# A fire that runs north for two days, a MODIS-only overpass in between and a 30 h gap.
FOCOS = (_row(0, "2025-08-10T01:30Z") + _row(0.5, "2025-08-10T10:40Z", n=1, sat="Terra", sensor="MODIS")
         + _row(1, "2025-08-10T13:30Z", n=8, frp=80) + _row(3, "2025-08-11T01:30Z", n=6)
         + _row(3.5, "2025-08-12T07:30Z", n=2))
INC = {"id": "IN-20250810-001", "primera": FOCOS[0]["t"], "ultima": FOCOS[-1]["t"], "estado": "inactivo",
       "lugar": {"municipio": "Villanueva", "provincia": "Ávila"}}


@pytest.fixture(autouse=True)
def sin_natura(monkeypatch):
    monkeypatch.setattr(ficha, "_natura", lambda g, pais: {"type": "FeatureCollection", "features": []})


def _datos():
    return ficha.datos(INC, FOCOS, config.COUNTRIES["ES"])


def test_one_isochrone_per_viirs_step_and_never_shrinks():
    d = _datos()
    isos = d["isocronas"]["features"]
    assert len(isos) == 4                          # MODIS does not move the perimeter
    ha = [f["properties"]["ha"] for f in isos]
    assert ha == sorted(ha) and ha[-1] == d["perimeter_ha"]
    assert [f["properties"]["k"] for f in isos] == list(range(4))


def test_overpasses_include_modis_and_point_to_the_last_isochrone():
    p = _datos()["pasadas"]
    assert len(p) == 5
    assert [x["viirs"] for x in p] == [True, False, True, True, True]
    assert [x["iso"] for x in p] == [0, 0, 1, 2, 3]
    assert p[4]["h"] == 30.0 and "h" not in p[0]


def test_key_moments():
    m = {x["tipo"]: x for x in _datos()["momentos"]}
    assert m["inicio"]["k"] == 0 and m["ultimo"]["k"] == 4
    assert m["potencia"]["k"] == 2                 # the 8 pixels at 80 MW
    # 30 h without pixels and then the perimeter grows again: a flare-up, not just a gap.
    assert m["reactivacion"]["k"] == 4 and m["reactivacion"]["horas"] == 30 and "hueco" not in m
    assert m["salto"]["k"] in (2, 3) and m["salto"]["ha"] > 0
    ks = [x["k"] for x in _datos()["momentos"]]
    assert ks == sorted(ks)


def test_eligibility():
    assert ficha.elegible({"perimeter_ha": 150, "steps": 3, "estado": "activo"})
    assert not ficha.elegible({"perimeter_ha": 50, "steps": 3})
    assert not ficha.elegible({"perimeter_ha": 500, "steps": 1})
    assert not ficha.elegible({"perimeter_ha": 500, "steps": 4, "estado": "unido"})


@pytest.mark.parametrize("code", ["ES", "FR"])
def test_page_has_no_markers_left(code):
    pais = config.COUNTRIES[code]
    d = _datos()
    out = ficha.html(INC, d, pais, web.PLANTILLA)
    assert not re.search(r"@@\w+@@|__[A-Z_]+__", out)
    assert f'<html lang="{pais.lang}">' in out
    cfg = json.loads(re.search(r"const CFG = (.*?);</script>", out).group(1))
    assert cfg["datos"] == "IN-20250810-001.json" and cfg["t"]["js_play"]
    assert out.count("<li data-k=") == len(d["momentos"])


def test_ficha_texts_exist_in_both_languages():
    assert set(i18n.FICHA["es"]) == set(i18n.FICHA["fr"])
    plantilla = ficha.PLANTILLA + ficha.FICHA_JS + ficha.LISTA
    for k in set(re.findall(r"@@(\w+)@@", plantilla)) | set(re.findall(r"T\.(js_\w+)", plantilla)):
        assert k in i18n.FICHA["es"], k
    for tipo in ("inicio", "salto", "potencia", "frente", "mitad", "noventa", "natura", "hueco", "reactivacion",
                 "ultimo", "s2"):
        assert f"m_{tipo}" in i18n.FICHA["es"]


def _fila(id_, titulo, t, ha, region="Extremadura", vivo=False):
    return {"id": id_, "titulo": titulo, "t": t, "dias": 3.5, "ha": ha, "pasadas": 20, "natura": 2,
            "region": region, "provincia": "Cáceres", "vivo": vivo}


@pytest.mark.parametrize("code", ["ES", "FR"])
def test_list_page(code):
    pais = config.COUNTRIES[code]
    filas = [_fila("a", "Pequeño", "2023-07-01T12:00Z", 1500.0), _fila("b", "Grande", "2025-08-10T13:30Z", 21449.0,
                                                                         vivo=True)]
    out = ficha.lista(filas, pais, web.PLANTILLA)
    assert not re.search(r"@@\w+@@|__[A-Z_]+__", out)
    assert out.index('href="b.html"') < out.index('href="a.html"')          # largest first
    assert '<option value="2025">' in out and '<option value="2023">' in out
    assert 'aria-current="page">' + i18n.FICHA[pais.lang]["tab_lista"] in out
    assert out.count("<tr data-") == 2


def test_auto_title_uses_place_of_origin():
    inc = {"primera": "2025-08-10T13:30Z", "lugar": {"municipio": "Cabezabellosa", "provincia": "Cáceres"},
           "origen": {"municipio": "Jarilla", "provincia": "Cáceres"}}
    assert ficha.titulo_auto(inc, "es") == "Jarilla (Cáceres), agosto de 2025"
    inc["origen"] = {"municipio": "Landiras", "provincia": "Gironde"}
    inc["primera"] = "2022-07-12T13:00Z"
    assert ficha.titulo_auto(inc, "fr") == "Landiras (Gironde), juillet 2022"
    assert ficha._slug("Baugé-en-Anjou") == "bauge-en-anjou"


def test_tabs_mark_the_current_page():
    t = ficha.tabs("es", "mapa", "")
    assert '<a href="./" aria-current="page">Mapa en directo</a>' in t and 'href="incendio/"' in t
    assert "aria-current" not in ficha.tabs("es", "", "../")


def test_historical_page_data_is_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    (tmp_path / "historicos").mkdir()
    pais = config.COUNTRIES["ES"]
    n = []
    real = ficha.datos
    monkeypatch.setattr(ficha, "datos", lambda *a: n.append(1) or real(*a))
    a = ficha._datos_historico(INC, FOCOS, pais)
    b = ficha._datos_historico(INC, FOCOS, pais)
    assert a == b and len(n) == 1
    monkeypatch.setattr(ficha, "DATOS_V", ficha.DATOS_V + 1)           # method changed: recomputed
    ficha._datos_historico(INC, FOCOS, pais)
    assert len(n) == 2
