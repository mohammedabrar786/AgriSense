import requests

BASE_URL = "http://localhost:5000"
TIMEOUT = 30
HEADERS = {"Content-Type": "application/json"}


def test_croppredictionvalidationerrors():
    url = f"{BASE_URL}/api/predict"
    invalid_payloads = [
        # Missing required fields: all required fields missing
        {},
        # Missing some required fields
        {"N": 10, "P": 20},
        # Out of range fields
        {"N": -1, "P": 20, "K": 30, "ph": 7.0, "humidity": 50, "temperature": 25, "rainfall": 100},
        {"N": 10, "P": 146, "K": 30, "ph": 7.0, "humidity": 50, "temperature": 25, "rainfall": 100},
        {"N": 10, "P": 20, "K": 206, "ph": 7.0, "humidity": 50, "temperature": 25, "rainfall": 100},
        {"N": 10, "P": 20, "K": 30, "ph": 3.4, "humidity": 50, "temperature": 25, "rainfall": 100},
        {"N": 10, "P": 20, "K": 30, "ph": 10.0, "humidity": 50, "temperature": 25, "rainfall": 100},
        {"N": 10, "P": 20, "K": 30, "ph": 7.0, "humidity": 13, "temperature": 25, "rainfall": 100},
        {"N": 10, "P": 20, "K": 30, "ph": 7.0, "humidity": 101, "temperature": 25, "rainfall": 100},
        {"N": 10, "P": 20, "K": 30, "ph": 7.0, "humidity": 50, "temperature": -1, "rainfall": 100},
        {"N": 10, "P": 20, "K": 30, "ph": 7.0, "humidity": 50, "temperature": 51, "rainfall": 100},
        {"N": 10, "P": 20, "K": 30, "ph": 7.0, "humidity": 50, "temperature": 25, "rainfall": -1},
        {"N": 10, "P": 20, "K": 30, "ph": 7.0, "humidity": 50, "temperature": 25, "rainfall": 301},
    ]

    for payload in invalid_payloads:
        response = requests.post(url, json=payload, headers=HEADERS, timeout=TIMEOUT)
        assert response.status_code == 422, f"Expected 422 but got {response.status_code} for payload: {payload}"
        data = response.json()
        assert "error" in data, f"Missing 'error' field in response for payload: {payload}"
        assert data["error"] == "Validation failed", f"Unexpected error message: {data['error']} for payload: {payload}"
        assert "details" in data, f"Missing 'details' field in response for payload: {payload}"
        assert isinstance(data["details"], list), f"'details' should be a list for payload: {payload}"
        assert len(data["details"]) > 0, f"'details' list should not be empty for payload: {payload}"


test_croppredictionvalidationerrors()