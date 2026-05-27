import requests

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

def test_croplistingretrieval():
    url = f"{BASE_URL}/api/crops"
    headers = {
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request to {url} failed with exception: {e}"

    if response.status_code == 200:
        try:
            data = response.json()
        except ValueError:
            assert False, "Response is not valid JSON"
        # Validate "crops" key exists and is a list
        assert "crops" in data, "'crops' key missing in response JSON"
        assert isinstance(data["crops"], list), "'crops' is not a list"
        # Validate "total" key exists and matches length of crops list
        assert "total" in data, "'total' key missing in response JSON"
        assert isinstance(data["total"], int), "'total' is not an integer"
        assert data["total"] == len(data["crops"]), "'total' does not match length of 'crops' list"
        # Validate crop metadata fields in at least one crop if present
        if data["crops"]:
            crop = data["crops"][0]
            # Check expected metadata fields
            for field in ["name", "icon", "seasons", "insight"]:
                assert field in crop, f"Crop metadata missing '{field}' field"
    else:
        # For service unavailability, expect error response from server
        # Status codes for service unavailable may be 503 or could be other 5xx
        assert response.status_code >= 400, f"Unexpected status code {response.status_code} for error case"
        try:
            data = response.json()
        except ValueError:
            assert False, "Error response is not valid JSON"
        # Expect error message in response
        assert "error" in data, "'error' key missing in error response JSON"

test_croplistingretrieval()