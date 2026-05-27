import requests


BASE_URL = "http://localhost:5000"
HEADERS_JSON = {"Content-Type": "application/json"}
TIMEOUT = 30


def test_userfeedbacksubmission():
    # First, create a valid prediction to obtain a prediction_id for feedback test
    predict_payload = {
        "N": 50,
        "P": 30,
        "K": 40,
        "ph": 6.5,
        "humidity": 70,
        "temperature": 25,
        "rainfall": 100,
    }

    prediction_id = None
    try:
        # Create prediction to get a valid prediction_id
        response = requests.post(
            f"{BASE_URL}/api/predict",
            json=predict_payload,
            headers=HEADERS_JSON,
            timeout=TIMEOUT,
        )
        assert response.status_code == 200, f"Failed to create prediction: {response.text}"
        data = response.json()
        assert "prediction_id" in data, f"Response missing prediction_id: {data}"
        prediction_id = data["prediction_id"]

        # Test valid feedback submission with prediction_id
        feedback_payload_valid = {
            "prediction_id": prediction_id,
            "correct": True,
            "actual_crop": "Wheat",
        }
        resp_valid = requests.post(
            f"{BASE_URL}/api/feedback",
            json=feedback_payload_valid,
            headers=HEADERS_JSON,
            timeout=TIMEOUT,
        )
        assert resp_valid.status_code == 200, (
            f"Valid feedback submission failed: {resp_valid.text}"
        )
        resp_json = resp_valid.json()
        assert resp_json.get("status") == "received", f"Expected status 'received', got {resp_json}"
        assert resp_json.get("prediction_id") == prediction_id, "Prediction ID mismatch in response"

        # Test feedback submission with missing prediction_id
        feedback_payload_missing_id = {
            "correct": False,
            "actual_crop": "Rice",
        }
        resp_missing_id = requests.post(
            f"{BASE_URL}/api/feedback",
            json=feedback_payload_missing_id,
            headers=HEADERS_JSON,
            timeout=TIMEOUT,
        )
        assert resp_missing_id.status_code == 422, (
            f"Expected 422 for missing prediction_id, got {resp_missing_id.status_code}"
        )
        resp_missing_json = resp_missing_id.json()
        assert "error" in resp_missing_json and "prediction_id" in resp_missing_json["error"].lower(), (
            f"Expected error about prediction_id, got {resp_missing_json}"
        )

        # Test feedback submission with invalid Content-Type
        invalid_content_payload = '{"prediction_id":"someid","correct":true}'
        resp_invalid_ct = requests.post(
            f"{BASE_URL}/api/feedback",
            data=invalid_content_payload,
            headers={"Content-Type": "text/plain"},
            timeout=TIMEOUT,
        )
        assert resp_invalid_ct.status_code == 400, (
            f"Expected 400 for invalid Content-Type, got {resp_invalid_ct.status_code}"
        )
        resp_invalid_ct_json = resp_invalid_ct.json()
        assert (
            "error" in resp_invalid_ct_json
            and "content-type must be application/json" in resp_invalid_ct_json["error"].lower()
        ), f"Unexpected error message: {resp_invalid_ct_json}"

        # Test feedback submission with malformed JSON - simulate by sending invalid JSON string with correct headers
        malformed_json = '{"prediction_id": "abc123", "correct": true'  # missing closing }
        resp_malformed = requests.post(
            f"{BASE_URL}/api/feedback",
            data=malformed_json,
            headers=HEADERS_JSON,
            timeout=TIMEOUT,
        )
        assert resp_malformed.status_code == 422, (
            f"Expected 422 for malformed JSON, got {resp_malformed.status_code}"
        )
        resp_malformed_json = resp_malformed.json()
        assert (
            "error" in resp_malformed_json
            and ("validation failed" in resp_malformed_json["error"].lower()
                 or "prediction_id" in resp_malformed_json["error"].lower()
                 or "invalid json" in resp_malformed_json["error"].lower())
        ), f"Unexpected error message for malformed JSON: {resp_malformed_json}"

    finally:
        # No cleanup needed as feedback does not create persistent resource to delete
        pass


test_userfeedbacksubmission()
