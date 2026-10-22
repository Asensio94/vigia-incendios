"""signals.json: the fires of the register in the sibling projects' common format."""
import json

from vigia import signals as S

ZEPA = {"codigo": "ES0000198", "nombre": "Liébana", "tipo": "ZEPA", "ha": 32.8}
ZEC = {"codigo": "ES1300001", "nombre": "Liébana", "tipo": "ZEC", "ha": 32.8}


def _fire(id: str = "IN-20260929-007", primera: str = "2026-09-29T02:56Z", **kw) -> dict:
    return {"id": id, "primera": primera, "ultima": primera, "n_focos": 2, "ha_focos": 32.8,
            "centro": [-4.65613, 43.05459], "natura": [ZEPA, ZEC],
            "lugar": {"municipio": "Vega de Liébana", "provincia": "Cantabria", "comunidad": "Cantabria"},
            "estado": "inactivo", **kw}


def _s2(natura: list[dict], definitivo: bool = False, ha: float = 284.7) -> dict:
    return {"clave": "v2|2|75f55cdf3f9c", "calculado": "2026-10-12T22:59Z", "definitivo": definitivo,
            "ha": ha, "natura": natura, "geometry": {"type": "Polygon", "coordinates": []}}


def test_sentinel2_burnt_area_crosses_the_sites():
    s = S.signal(_fire(perimetro=_s2([{**ZEPA, "ha": 283.1}, {**ZEC, "ha": 283.1}])))
    assert s["precision"] == "perimetro"
    assert s["sites"] == [{"code": "ES0000198", "ha": 283.1}, {"code": "ES1300001", "ha": 283.1}]
    assert s["value"] == {"amount": 284.7, "unit": "ha"}
    assert s["status"] == "provisional"


def test_without_sentinel2_the_hot_pixels_cross_the_sites():
    s = S.signal(_fire())
    assert s["precision"] == "focos" and s["status"] is None
    assert s["sites"] == [{"code": "ES0000198", "ha": 32.8}, {"code": "ES1300001", "ha": 32.8}]
    assert s["value"] == {"amount": 32.8, "unit": "ha"}


def test_a_measured_burnt_area_outside_natura_is_in_no_site():
    # Sentinel-2 saw the whole fire and none of it burnt inside a site: the hot pixels that
    # touched one no longer count.
    s = S.signal(_fire(perimetro=_s2([], definitivo=True, ha=3.2)))
    assert s["precision"] == "perimetro" and s["status"] == "definitivo"
    assert s["sites"] == [] and s["value"] == {"amount": 3.2, "unit": "ha"}


def test_under_clouds_the_hot_pixels_are_not_ruled_out():
    s = S.signal(_fire(perimetro={**_s2([{**ZEPA, "ha": 5.0}], ha=5.0), "nublado": True}))
    assert s["precision"] == "perimetro"
    assert s["sites"] == [{"code": "ES0000198", "ha": 5.0}, {"code": "ES1300001"}]


def test_a_perimeter_that_measured_nothing_leaves_the_hot_pixels():
    for per in ({**_s2([], ha=0.0), "nublado": True}, {**_s2([]), "ha": None}):
        s = S.signal(_fire(perimetro=per))
        assert s["precision"] == "focos" and s["status"] is None
        assert [x["code"] for x in s["sites"]] == ["ES0000198", "ES1300001"]
        assert s["value"] == {"amount": 32.8, "unit": "ha"}


def test_status_follows_the_perimeter():
    assert S.signal(_fire(perimetro=_s2([ZEPA], definitivo=True)))["status"] == "definitivo"
    assert S.signal(_fire(perimetro=_s2([ZEPA], definitivo=False)))["status"] == "provisional"
    # Cloudy or without a usable image: no hectares, so no value, but still provisional.
    s = S.signal(_fire(perimetro=_s2([ZEPA], ha=0.0)))
    assert s["status"] == "provisional" and s["value"] is None


def test_municipality_goes_by_name_with_its_province():
    s = S.signal(_fire())
    assert s["title"] == "Incendio en Vega de Liébana"
    assert s["municipalities"] == []
    assert s["municipality_names"] == ["Vega de Liébana"] and s["provinces"] == ["Cantabria"]
    assert s["details"] == {"province": "Cantabria", "point": [-4.65613, 43.05459]}
    assert s["url"] == "https://asensio94.github.io/vigia-incendios/#IN-20260929-007"


def test_fire_without_municipality():
    s = S.signal(_fire(natura=[], lugar={"municipio": None, "provincia": "Cáceres", "comunidad": "Extremadura"}))
    assert s["title"] == "Incendio en lugar sin identificar"
    assert s["municipality_names"] == [] and s["provinces"] == []
    assert s["sites"] == [] and s["details"]["province"] == "Cáceres"
    assert S.signal(_fire(lugar=None))["details"] == {"province": None, "point": [-4.65613, 43.05459]}


def test_document_keeps_a_year_sorted_by_date_then_id():
    fires = [_fire("IN-20261012-002", "2026-10-12T13:33Z"), _fire("IN-20261012-001", "2026-10-12T14:00Z"),
             _fire("IN-20251013-001", "2025-10-13T01:00Z"), _fire("IN-20251012-001", "2025-10-12T23:59Z")]
    doc = S.document(fires, "2026-10-13T07:02Z")
    assert [s["id"] for s in doc["signals"]] == ["IN-20251013-001", "IN-20261012-001", "IN-20261012-002"]
    assert {k: doc[k] for k in ("source", "version", "generated")} == \
        {"source": "vigia-incendios", "version": 2, "generated": "2026-10-13T07:02Z"}
    assert doc["coverage"]["ES"]["sites"] is None and "365 días" in doc["coverage"]["ES"]["note"]
    assert doc["coverage"]["FR"]["sites"] is None and "365 derniers jours" in doc["coverage"]["FR"]["note"]
    assert all(s["kind"] == "fire" and s["deadline"] is None for s in doc["signals"])
    # No source or regions per signal: the hub adds them.
    assert not any({"source", "regions"} & s.keys() for s in doc["signals"])
    assert json.loads(json.dumps(doc, ensure_ascii=False)) == doc


def _fire_fr(**kw) -> dict:
    kw = {"centro": [9.17, 42.24],
          "natura": [{"codigo": "FR9400578", "nombre": "Massif du Rotondo", "tipo": "ZSC", "ha": 19.0}],
          "lugar": {"municipio": "Venaco", "insee": "2B341", "provincia": "Haute-Corse", "comunidad": "Corse"},
          **kw}
    return _fire(id="FR-IN-20261014-001", primera="2026-10-14T01:40Z", **kw)


def test_every_signal_carries_its_country():
    assert S.signal(_fire())["country"] == "ES"
    assert S.signal(_fire_fr())["country"] == "FR"


def test_french_fire_goes_by_insee_code_with_a_french_title():
    s = S.signal(_fire_fr())
    assert s["municipalities"] == ["2B341"] and s["municipality_names"] == ["Venaco"]
    assert s["provinces"] == ["Haute-Corse"] and s["details"]["province"] == "Haute-Corse"
    assert s["title"] == "Incendie à Venaco"
    assert s["url"] == "https://asensio94.github.io/vigia-incendios/fr/#FR-IN-20261014-001"
    assert s["sites"] == [{"code": "FR9400578", "ha": 19.0}]
    s = S.signal(_fire_fr(lugar=None))
    assert s["title"] == "Incendie, lieu non identifié" and s["municipalities"] == []


def test_document_mixes_both_countries():
    doc = S.document([_fire(), _fire_fr()], "2026-10-15T07:00Z")
    assert [(s["id"], s["country"]) for s in doc["signals"]] == \
        [("IN-20260929-007", "ES"), ("FR-IN-20261014-001", "FR")]

