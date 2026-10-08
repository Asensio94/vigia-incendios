"""Perimeter, front and progression on synthetic fires with known shapes."""
from vigia import config, perimeter as P

LAT, LON = 40.0, -3.0
KM_LAT, KM_LON = 1 / 110.57, 1 / (111.32 * 0.766)  # degrees per km at 40° N


def _px(x_km: float, y_km: float, t: str, sat: str = "N20") -> dict:
    return {"lat": LAT + y_km * KM_LAT, "lon": LON + x_km * KM_LON, "t": t, "sat": sat,
            "sensor": "VIIRS", "scan": 0.375, "track": 0.375, "frp": 10.0}


def _row(y_km: float, t: str, n: int = 4, sat: str = "N20") -> list[dict]:
    return [_px(0.375 * k, y_km, t, sat) for k in range(n)]


def test_steps_merge_satellites_minutes_apart():
    fs = _row(0, "2025-08-10T13:10Z", sat="N20") + _row(0.4, "2025-08-10T13:55Z", sat="N21") \
        + _row(1, "2025-08-11T01:30Z")
    assert [len(s) for s in P._steps(fs)] == [8, 4]


def test_perimeter_never_shrinks_and_fills_gaps():
    # A fire that runs north: rows of pixels 1 km apart, one row per overpass.
    fs = [p for k, t in enumerate(["2025-08-10T01:30Z", "2025-08-10T13:30Z", "2025-08-11T01:30Z"])
          for p in _row(k * 1.0, t)]
    r = P.track(fs)
    ha = [row["ha"] for row in r["progression"]]
    assert ha == sorted(ha) and r["steps"] == 3
    # Closing fills the 1 km gaps between rows: more than the discs alone, no holes.
    discs = P.track(fs, closing_km=0)
    assert r["perimeter_ha"] > discs["perimeter_ha"] * 1.5
    assert len(r["_geom"].interiors) == 0


def test_front_is_on_the_side_of_the_newest_pixels():
    fs = _row(0, "2025-08-10T01:30Z") + _row(1.0, "2025-08-10T13:30Z") + _row(2.0, "2025-08-11T01:30Z")
    r = P.track(fs)
    assert r["front_km"] > 0 and r["front_t"] == "2025-08-11T01:30Z"
    # Every point of the front is in the northern half of the fire.
    ys = [y for line in r["_front"].geoms for _, y in line.coords]
    assert min(ys) > LAT + 1.0 * KM_LAT


def test_growth_rate():
    fs = _row(0, "2025-08-10T01:30Z") + _row(1.0, "2025-08-10T13:30Z")
    r = P.track(fs)
    a, b = r["progression"]
    assert b["growth_ha_h"] == round((b["ha"] - a["ha"]) / 12, 1)
    assert r["max_growth_ha_h"] == b["growth_ha_h"]


def test_describe_needs_enough_viirs_pixels():
    few = _row(0, "2025-08-10T01:30Z", n=config.PERIMETER_MIN_VIIRS - 1)
    assert P.describe(few) is None
    d = P.describe(_row(0, "2025-08-10T01:30Z") + _row(1.0, "2025-08-10T13:30Z"))
    assert d["perimeter"]["type"] in ("Polygon", "MultiPolygon")
    assert set(d) <= set(P.FIELDS) and not any(k.startswith("_") for k in d)
