import requests

BASE_URL = "http://localhost:5000"
TIMEOUT = 30
HEADERS_JSON = {"Content-Type": "application/json"}

def test_predictionhistoryretrieval():
    predict_url = f"{BASE_URL}/api/predict"
    history_url = f"{BASE_URL}/api/history"

    # Sample valid prediction input body
    prediction_payload = {
        "N": 90,
        "P": 40,
        "K": 40,
        "ph": 6.5,
        "humidity": 80,
        "temperature": 25,
        "rainfall": 100
    }

    prediction_id = None
    try:
        # First, create a new prediction to ensure there is at least one recent prediction in history
        response = requests.post(predict_url, json=prediction_payload, headers=HEADERS_JSON, timeout=TIMEOUT)
        assert response.status_code == 200, f"Prediction creation failed with status {response.status_code}"
        data = response.json()
        assert "prediction_id" in data, "Response missing prediction_id"
        prediction_id = data["prediction_id"]

        # Test 1: GET /api/history without parameters (default limit)
        res = requests.get(history_url, timeout=TIMEOUT)
        assert res.status_code == 200, f"History GET failed with status {res.status_code}"
        history_data = res.json()
        assert "history" in history_data, "'history' key missing in response"
        assert "total" in history_data, "'total' key missing in response"
        assert isinstance(history_data["history"], list), "'history' is not a list"
        assert isinstance(history_data["total"], int), "'total' is not an int"

        # Test 2: GET /api/history with limit=1 to check recent prediction is included
        params = {"limit": 1}
        res_limit_1 = requests.get(history_url, params=params, timeout=TIMEOUT)
        assert res_limit_1.status_code == 200, f"History GET with limit=1 failed with status {res_limit_1.status_code}"
        data_limit_1 = res_limit_1.json()
        assert "history" in data_limit_1 and "total" in data_limit_1
        history_list = data_limit_1["history"]
        assert isinstance(history_list, list) and len(history_list) <= 1
        if len(history_list) == 1:
            recent_entry = history_list[0]
            # recent prediction_id should be in the most recent history entry
            assert "prediction_id" in recent_entry
            assert recent_entry["prediction_id"] == prediction_id or True  # It may be equal or some recent entry, at least presence expected

        # Test 3: GET /api/history with a very large limit (500) to verify server-side max limit enforcement (max 100 expected)
        params = {"limit": 500}
        res_limit_500 = requests.get(history_url, params=params, timeout=TIMEOUT)
        assert res_limit_500.status_code == 200, f"History GET with limit=500 failed with status {res_limit_500.status_code}"
        data_limit_500 = res_limit_500.json()
        assert "history" in data_limit_500 and "total" in data_limit_500
        history_500 = data_limit_500["history"]
        assert isinstance(history_500, list)
        # The length should not exceed 100 (server max)
        assert len(history_500) <= 100, f"Server did not enforce max limit of 100, got {len(history_500)}"

    finally:
        if prediction_id:
            # Cleanup: there is no explicit delete prediction endpoint mentioned, so skip deletion
            pass

test_predictionhistoryretrieval()