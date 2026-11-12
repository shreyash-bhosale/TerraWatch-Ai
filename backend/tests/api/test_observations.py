import json
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_AOI = {
    "type": "Polygon",
    "coordinates": [
        [
            [73.8, 18.496],
            [73.864, 18.496],
            [73.864, 18.56],
            [73.8, 18.56],
            [73.8, 18.496],
        ]
    ],
}


def test_search_observations_success():
    payload = {"aoi": SAMPLE_AOI}
    response = client.post("/api/observations/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "observations" in data
    assert "warnings" in data
    assert isinstance(data["observations"], list)
    assert len(data["observations"]) >= 2
    ids = [o["id"] for o in data["observations"]]
    assert "syn_before" in ids
    assert "syn_after" in ids
    for o in data["observations"]:
        assert o["synthetic"] is True


def test_search_observations_with_date_filter():
    payload = {
        "aoi": SAMPLE_AOI,
        "start_date": "2026-01-01",
        "end_date": "2026-01-05",
    }
    response = client.post("/api/observations/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    ids = [o["id"] for o in data["observations"]]
    assert "syn_before" in ids
    assert "syn_after" not in ids


def test_search_observations_invalid_aoi():
    # Self-intersecting polygon (bowtie)
    invalid_aoi = {
        "type": "Polygon",
        "coordinates": [
            [
                [0.0, 0.0],
                [1.0, 1.0],
                [0.0, 1.0],
                [1.0, 0.0],
                [0.0, 0.0],
            ]
        ],
    }
    response = client.post("/api/observations/search", json={"aoi": invalid_aoi})
    assert response.status_code == 422
    err = response.json()
    assert "error" in err
    assert err["error"]["code"] == "INVALID_GEOMETRY"


def test_search_observations_area_too_large():
    # Huge polygon exceeding 50,000 km^2
    huge_aoi = {
        "type": "Polygon",
        "coordinates": [
            [
                [0.0, 0.0],
                [20.0, 0.0],
                [20.0, 20.0],
                [0.0, 20.0],
                [0.0, 0.0],
            ]
        ],
    }
    response = client.post("/api/observations/search", json={"aoi": huge_aoi})
    assert response.status_code == 422
    err = response.json()
    assert err["error"]["code"] == "INVALID_GEOMETRY"


def test_list_observations():
    response = client.get("/api/observations?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "observations" in data
    assert "total" in data
    assert data["total"] >= 2
    assert len(data["observations"]) <= 10


def test_get_observation_success():
    response = client.get("/api/observations/syn_before")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "syn_before"
    assert data["synthetic"] is True
    assert data["measurement_units"] == "dB"


def test_get_observation_not_found():
    response = client.get("/api/observations/non_existent_id_999")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "OBSERVATION_NOT_FOUND"
