import requests
import datetime

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

def test_weatherdataautofillfetch():
    city = "Mumbai"
    url = f"{BASE_URL}/api/weather/autofill"
    params = {"city": city}
    try:
        response = requests.get(url, params=params, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        data = response.json()

        # Validate required keys in response
        assert "city" in data and isinstance(data["city"], str) and data["city"].lower() == city.lower()
        assert "country" in data and isinstance(data["country"], str) and len(data["country"]) > 0

        assert "autofill" in data and isinstance(data["autofill"], dict)
        autofill = data["autofill"]
        # autofill should have temperature, humidity, rainfall as numbers
        for key in ("temperature", "humidity", "rainfall"):
            assert key in autofill
            assert isinstance(autofill[key], (int, float)), f"autofill.{key} not a number"

        assert "display" in data and isinstance(data["display"], dict)

        assert "fetched_at" in data and isinstance(data["fetched_at"], str)
        # Validate fetched_at is a valid ISO8601 datetime string and not empty
        try:
            fetched_at_dt = datetime.datetime.fromisoformat(data["fetched_at"].replace("Z", "+00:00"))
        except ValueError:
            assert False, "fetched_at is not a valid ISO8601 datetime string"

    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

test_weatherdataautofillfetch()