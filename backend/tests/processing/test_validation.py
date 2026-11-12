import json
from pathlib import Path
import pytest
from app.schemas.observation import Observation
from app.processing.validation import validate_compatibility

def get_fixture_observation(name: str) -> Observation:
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    with open(fixtures_dir / f"{name}.json", "r") as f:
        data = json.load(f)
    return Observation(**data)

def test_compatible_pair_validates_successfully():
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    with open(fixtures_dir / "aoi.geojson", "r") as f:
        aoi = json.load(f)

    obs_before = get_fixture_observation("syn_before")
    obs_after = get_fixture_observation("syn_after")

    res = validate_compatibility(obs_before, obs_after, aoi)
    assert res.compatible is True
    assert res.order.before_id == "syn_before"
    assert res.order.after_id == "syn_after"
    assert all(r.passed for r in res.rules if r.severity == "error")

def test_same_id_fails_validation():
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    with open(fixtures_dir / "aoi.geojson", "r") as f:
        aoi = json.load(f)

    obs = get_fixture_observation("syn_before")
    res = validate_compatibility(obs, obs, aoi)
    assert res.compatible is False
    v_same = next(r for r in res.rules if r.id == "V-SAME-ID")
    assert v_same.passed is False

def test_incompatible_units_fails_validation():
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    with open(fixtures_dir / "aoi.geojson", "r") as f:
        aoi = json.load(f)

    obs_before = get_fixture_observation("syn_before")
    obs_wrongunits = get_fixture_observation("syn_wrongunits")

    res = validate_compatibility(obs_before, obs_wrongunits, aoi)
    assert res.compatible is False
    v_units = next(r for r in res.rules if r.id == "V-UNITS")
    assert v_units.passed is False

def test_misaligned_grid_fails_validation():
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    with open(fixtures_dir / "aoi.geojson", "r") as f:
        aoi = json.load(f)

    obs_before = get_fixture_observation("syn_before")
    obs_misaligned = get_fixture_observation("syn_misaligned")

    res = validate_compatibility(obs_before, obs_misaligned, aoi)
    assert res.compatible is False
    v_grid = next(r for r in res.rules if r.id == "V-GRID")
    assert v_grid.passed is False


def _make_obs(**overrides) -> Observation:
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    with open(fixtures_dir / "syn_before.json", "r") as f:
        base = json.load(f)
    base.update(overrides)
    return Observation(**base)


def _load_demo_aoi():
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    with open(fixtures_dir / "aoi.geojson", "r") as f:
        return json.load(f)


def test_v_order_equal_dates_fails():
    aoi = _load_demo_aoi()
    obs1 = _make_obs(id="obs_a", acquisition_date="2026-01-01T00:00:00Z")
    obs2 = _make_obs(id="obs_b", acquisition_date="2026-01-01T00:00:00Z")
    res = validate_compatibility(obs1, obs2, aoi)
    assert res.compatible is False
    rule = next(r for r in res.rules if r.id == "V-ORDER")
    assert rule.passed is False
    assert rule.severity == "error"


def test_v_pol_mismatch_fails_and_missing_warns():
    aoi = _load_demo_aoi()
    obs1 = _make_obs(id="obs_a", acquisition_date="2026-01-01T00:00:00Z", polarization="HH")
    obs2 = _make_obs(id="obs_b", acquisition_date="2026-01-10T00:00:00Z", polarization="VV")
    res_mismatch = validate_compatibility(obs1, obs2, aoi)
    assert res_mismatch.compatible is False
    rule_mismatch = next(r for r in res_mismatch.rules if r.id == "V-POL")
    assert rule_mismatch.passed is False
    assert rule_mismatch.severity == "error"

    obs3 = _make_obs(id="obs_c", acquisition_date="2026-01-10T00:00:00Z", polarization=None)
    res_missing = validate_compatibility(obs1, obs3, aoi)
    assert res_missing.compatible is True
    rule_missing = next(r for r in res_missing.rules if r.id == "V-POL")
    assert rule_missing.passed is True
    assert rule_missing.severity == "warning"


def test_v_band_mismatch_fails():
    aoi = _load_demo_aoi()
    obs1 = _make_obs(id="obs_a", acquisition_date="2026-01-01T00:00:00Z", frequency_band="L")
    obs2 = _make_obs(id="obs_b", acquisition_date="2026-01-10T00:00:00Z", frequency_band="S")
    res = validate_compatibility(obs1, obs2, aoi)
    assert res.compatible is False
    rule = next(r for r in res.rules if r.id == "V-BAND")
    assert rule.passed is False
    assert rule.severity == "error"


def test_v_orbit_mismatch_fails_and_missing_warns():
    aoi = _load_demo_aoi()
    obs1 = _make_obs(id="obs_a", acquisition_date="2026-01-01T00:00:00Z", orbit_direction="ascending")
    obs2 = _make_obs(id="obs_b", acquisition_date="2026-01-10T00:00:00Z", orbit_direction="descending")
    res_mismatch = validate_compatibility(obs1, obs2, aoi)
    assert res_mismatch.compatible is False
    rule_mismatch = next(r for r in res_mismatch.rules if r.id == "V-ORBIT")
    assert rule_mismatch.passed is False
    assert rule_mismatch.severity == "error"

    obs3 = _make_obs(id="obs_c", acquisition_date="2026-01-10T00:00:00Z", orbit_direction=None)
    res_missing = validate_compatibility(obs1, obs3, aoi)
    assert res_missing.compatible is True
    rule_missing = next(r for r in res_missing.rules if r.id == "V-ORBIT")
    assert rule_missing.passed is True
    assert rule_missing.severity == "warning"


def test_v_level_mismatch_fails():
    aoi = _load_demo_aoi()
    obs1 = _make_obs(id="obs_a", acquisition_date="2026-01-01T00:00:00Z", processing_level="L2")
    obs2 = _make_obs(id="obs_b", acquisition_date="2026-01-10T00:00:00Z", processing_level="L1")
    res = validate_compatibility(obs1, obs2, aoi)
    assert res.compatible is False
    rule = next(r for r in res.rules if r.id == "V-LEVEL")
    assert rule.passed is False
    assert rule.severity == "error"


def test_v_crs_mismatch_fails():
    aoi = _load_demo_aoi()
    obs1 = _make_obs(id="obs_a", acquisition_date="2026-01-01T00:00:00Z", crs="EPSG:4326")
    obs2 = _make_obs(id="obs_b", acquisition_date="2026-01-10T00:00:00Z", crs="EPSG:32643")
    res = validate_compatibility(obs1, obs2, aoi)
    assert res.compatible is False
    rule = next(r for r in res.rules if r.id == "V-CRS")
    assert rule.passed is False
    assert rule.severity == "error"


def test_v_aoi_non_intersecting_fails():
    disjoint_aoi = {
        "type": "Polygon",
        "coordinates": [[[10.0, 10.0], [10.1, 10.0], [10.1, 10.1], [10.0, 10.1], [10.0, 10.0]]],
    }
    obs1 = get_fixture_observation("syn_before")
    obs2 = get_fixture_observation("syn_after")
    res = validate_compatibility(obs1, obs2, disjoint_aoi)
    assert res.compatible is False
    rule = next(r for r in res.rules if r.id == "V-AOI")
    assert rule.passed is False
    assert rule.severity == "error"


def test_v_valid_under_one_percent_fails():
    import numpy as np
    from rasterio.crs import CRS
    from rasterio.transform import from_origin
    from app.processing.raster_data import RasterData

    aoi = _load_demo_aoi()
    obs1 = get_fixture_observation("syn_before")
    obs2 = get_fixture_observation("syn_after")

    transform = from_origin(73.800, 18.560, 0.001, 0.001)
    bounds = (73.800, 18.496, 73.864, 18.560)
    # 64x64 = 4096 pixels; only 10 valid pixels (~0.24% < 1%)
    arr_b = np.full((64, 64), -9999.0, dtype=np.float32)
    arr_a = np.full((64, 64), -9999.0, dtype=np.float32)
    arr_b[0, 0:10] = -15.0
    arr_a[0, 0:10] = -15.0

    r_b = RasterData(arr_b, transform, CRS.from_epsg(4326), -9999.0, bounds, (0.001, 0.001), "dB")
    r_a = RasterData(arr_a, transform, CRS.from_epsg(4326), -9999.0, bounds, (0.001, 0.001), "dB")

    res = validate_compatibility(obs1, obs2, aoi, before_raster=r_b, after_raster=r_a)
    assert res.compatible is False
    rule = next(r for r in res.rules if r.id == "V-VALID")
    assert rule.passed is False
    assert rule.severity == "error"


def test_identical_dimensions_alone_do_not_pass_validation():
    import rasterio
    fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
    aoi = _load_demo_aoi()
    obs_before = get_fixture_observation("syn_before")
    obs_misaligned = get_fixture_observation("syn_misaligned")

    with rasterio.open(fixtures_dir / "syn_before.tif") as s1, rasterio.open(fixtures_dir / "syn_misaligned.tif") as s2:
        assert s1.shape == s2.shape == (64, 64)

    res = validate_compatibility(obs_before, obs_misaligned, aoi)
    assert res.compatible is False


def test_validation_single_source_of_truth():
    import app.services.validator as svc_validator
    assert not hasattr(svc_validator, "validate_compatibility")
