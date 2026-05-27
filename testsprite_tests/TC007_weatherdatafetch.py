import requests

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

def test_weatherdatafetch():
    url = f"{BASE_URL}/api/weather"
    params = {"city": "Chennai"}
    try:
        response = requests.get(url, params=params, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    data = response.json()
    # Validate main top-level key
    assert "weather" in data, "'weather' key missing in response"
    weather = data["weather"]

    # Check presence and types of required weather data fields
    expected_keys = ["temperature", "humidity", "rainfall", "advisory", "sunrise", "sunset"]
    for key in expected_keys:
        assert key in weather, f"'{key}' key missing in weather data"
    # Basic value type checks
    assert isinstance(weather["temperature"], (int, float)), "temperature should be a number"
    assert isinstance(weather["humidity"], (int, float)), "humidity should be a number"
    assert isinstance(weather["rainfall"], (int, float)), "rainfall should be a number"
    assert isinstance(weather["advisory"], str), "advisory should be a string"
    # Sunrise and sunset should be string or number (timestamp or formatted)
    assert isinstance(weather["sunrise"], (str, int, float)), "sunrise should be string or timestamp"
    assert isinstance(weather["sunset"], (str, int, float)), "sunset should be string or timestamp"

test_weatherdatafetch()