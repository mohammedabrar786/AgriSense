import requests
import time

BASE_URL = "http://localhost:5000"
TIMEOUT = 30  # seconds


def test_healthcheckapiresponsevalidation():
    url = f"{BASE_URL}/api/health"
    try:
        response = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request to {url} failed: {e}"

    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    # Validate required keys in response
    for key in ("status", "models", "crops", "weather_api", "time"):
        assert key in data, f"Response JSON missing key: {key}"

    # Validate types and contents
    assert isinstance(data["status"], str), "status should be a string"
    assert isinstance(data["models"], list), "models should be a list"
    for model_name in data["models"]:
        assert isinstance(model_name, str), "each model name should be a string"
    assert isinstance(data["crops"], int), "crops should be an integer"
    assert isinstance(data["weather_api"], str), "weather_api should be a string"
    assert isinstance(data["time"], str), "time should be a string"

    # Further validations of values
    assert data["status"].lower() in ("ok", "healthy", "healthy", "running", "up"), f"Unexpected status value: {data['status']}"
    assert data["crops"] >= 0, f"crops count should be non-negative, got {data['crops']}"
    # weather_api could be any string showing configured/misconfigured state, so no strict check here

    # Validate time is ISO 8601 or at least parseable by time.strptime fallback
    time_str = data["time"]
    parsed_time = None
    # try ISO8601 with or without timezone
    time_formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in time_formats:
        try:
            parsed_time = time.strptime(time_str, fmt)
            break
        except (ValueError, TypeError):
            continue
    assert parsed_time is not None, f"time field is not a valid datetime string: {time_str}"


test_healthcheckapiresponsevalidation()