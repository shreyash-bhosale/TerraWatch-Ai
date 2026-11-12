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
