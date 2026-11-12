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


def test_validate_compatible_pair():
    payload = {
        "before_id": "syn_before",
        "after_id": "syn_after",
        "aoi": SAMPLE_AOI,
    }
    response = client.post("/api/analysis/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["compatible"] is True
    assert data["order"]["before_id"] == "syn_before"
    assert data["order"]["after_id"] == "syn_after"
    rule_ids = {r["id"]: r for r in data["rules"]}
    assert rule_ids["V-SAME-ID"]["passed"] is True
    assert rule_ids["V-ORDER"]["passed"] is True
    assert rule_ids["V-UNITS"]["passed"] is True
    assert rule_ids["V-POL"]["passed"] is True
    assert rule_ids["V-BAND"]["passed"] is True
    assert rule_ids["V-ORBIT"]["passed"] is True
    assert rule_ids["V-LEVEL"]["passed"] is True
    assert rule_ids["V-CRS"]["passed"] is True
    assert rule_ids["V-GRID"]["passed"] is True
    assert rule_ids["V-AOI"]["passed"] is True


def test_validate_reversed_order():
    # If client passes after first, validator establishes correct chronological order
    payload = {
        "before_id": "syn_after",
        "after_id": "syn_before",
        "aoi": SAMPLE_AOI,
    }
    response = client.post("/api/analysis/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["compatible"] is True
    assert data["order"]["before_id"] == "syn_before"
    assert data["order"]["after_id"] == "syn_after"


def test_validate_same_id_error():
    payload = {
        "before_id": "syn_before",
        "after_id": "syn_before",
        "aoi": SAMPLE_AOI,
    }
    response = client.post("/api/analysis/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["compatible"] is False
    rule_map = {r["id"]: r for r in data["rules"]}
    assert rule_map["V-SAME-ID"]["passed"] is False
    assert rule_map["V-SAME-ID"]["severity"] == "error"


def test_validate_wrong_units_error():
    payload = {
        "before_id": "syn_before",
        "after_id": "syn_wrongunits",
        "aoi": SAMPLE_AOI,
    }
    response = client.post("/api/analysis/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["compatible"] is False
    rule_map = {r["id"]: r for r in data["rules"]}
    assert rule_map["V-UNITS"]["passed"] is False
    assert rule_map["V-UNITS"]["severity"] == "error"


def test_validate_misaligned_grid_error():
    payload = {
        "before_id": "syn_before",
        "after_id": "syn_misaligned",
        "aoi": SAMPLE_AOI,
    }
    response = client.post("/api/analysis/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["compatible"] is False
    rule_map = {r["id"]: r for r in data["rules"]}
    assert rule_map["V-GRID"]["passed"] is False
    assert rule_map["V-GRID"]["severity"] == "error"


def test_validate_unknown_observation():
    payload = {
        "before_id": "syn_before",
        "after_id": "unknown_id_404",
        "aoi": SAMPLE_AOI,
    }
    response = client.post("/api/analysis/validate", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "OBSERVATION_NOT_FOUND"


def test_validate_invalid_aoi():
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
    payload = {
        "before_id": "syn_before",
        "after_id": "syn_after",
        "aoi": invalid_aoi,
    }
    response = client.post("/api/analysis/validate", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "INVALID_GEOMETRY"
