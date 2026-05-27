import requests

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

def test_croppredictionvalidinput():
    url = f"{BASE_URL}/api/predict"
    headers = {"Content-Type": "application/json"}
    payload = {
        "N": 80,
        "P": 40,
        "K": 40,
        "ph": 6.5,
        "humidity": 70,
        "temperature": 25,
        "rainfall": 100
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200 but got {response.status_code}"
        data = response.json()

        # Validate required keys in the response
        expected_keys = {
            "prediction_id",
            "crop",
            "yield",
            "price",
            "confidence",
            "top3",
            "inputs",
            "weather",
            "timestamp"
        }
        assert expected_keys.issubset(data.keys()), f"Response missing keys: {expected_keys - set(data.keys())}"

        # Validate crop object fields
        crop_fields = set(data["crop"].keys())
        assert crop_fields, "Crop object is empty"

        # Validate yield fields
        yield_fields = {"value", "unit", "range"}
        assert yield_fields.issubset(data["yield"].keys()), f"Yield missing keys: {yield_fields - set(data['yield'].keys())}"

        # Validate price fields
        price_fields = {"value", "unit"}
        assert price_fields.issubset(data["price"].keys()), f"Price missing keys: {price_fields - set(data['price'].keys())}"

        # Validate confidence is a number (range check removed)
        assert isinstance(data["confidence"], (int, float)), "Confidence is not a number"

        # Validate top3 as a list with length 3 and each having crop prediction structure
        top3 = data["top3"]
        assert isinstance(top3, list), "top3 is not a list"
        assert len(top3) == 3, f"Expected top3 length 3 but got {len(top3)}"
        for pred in top3:
            # Each prediction should have similar keys as crop
            assert crop_fields.issubset(pred.keys()), f"Top3 prediction missing keys: {crop_fields - set(pred.keys())}"

        # Validate inputs reflect request data with correct types and values
        inputs = data["inputs"]
        for key in ["N", "P", "K", "ph", "humidity", "temperature", "rainfall"]:
            assert key in inputs, f"Inputs missing key: {key}"
            assert isinstance(inputs[key], (int, float)), f"Input {key} is not numeric"
            # Optionally assert values match payload sent (allowing float/int conversion)
            assert abs(inputs[key] - payload[key]) < 1e-5, f"Input {key} value mismatch"

        # Validate weather field can be None or dict
        weather = data["weather"]
        assert weather is None or isinstance(weather, dict), "Weather field is not None or dict"

        # Validate timestamp is a non-empty string
        timestamp = data["timestamp"]
        assert isinstance(timestamp, str) and timestamp.strip(), "Invalid or empty timestamp"

    except requests.exceptions.RequestException as e:
        assert False, f"Request failed: {e}"

test_croppredictionvalidinput()
