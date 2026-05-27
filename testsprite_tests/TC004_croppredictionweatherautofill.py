import requests

BASE_URL = "http://localhost:5000"
TIMEOUT = 30


def test_croppredictionweatherautofill():
    city = "Mumbai"
    headers = {"Content-Type": "application/json"}

    # Step 1: GET /api/weather/autofill?city=<city>
    autofill_url = f"{BASE_URL}/api/weather/autofill"
    params = {"city": city}
    try:
        autofill_resp = requests.get(autofill_url, params=params, timeout=TIMEOUT)
    except Exception as e:
        assert False, f"Request to /api/weather/autofill failed: {e}"
    assert autofill_resp.status_code == 200, f"Expected 200 from /api/weather/autofill, got {autofill_resp.status_code}"
    autofill_json = autofill_resp.json()
    assert "city" in autofill_json and "country" in autofill_json and "autofill" in autofill_json
    autofill_data = autofill_json.get("autofill", {})
    temperature = autofill_data.get("temperature")
    humidity = autofill_data.get("humidity")
    rainfall = autofill_data.get("rainfall")
    # Validate autofill values presence and type
    assert temperature is not None and isinstance(temperature, (int, float))
    assert humidity is not None and isinstance(humidity, (int, float))
    assert rainfall is not None and isinstance(rainfall, (int, float))

    # Step 2: POST /api/predict with use_weather=true and city
    predict_url = f"{BASE_URL}/api/predict"
    # Provide required base soil inputs plus use_weather=true, city=city
    payload = {
        "N": 80,
        "P": 40,
        "K": 60,
        "ph": 6.5,
        "use_weather": True,
        "city": city
    }
    try:
        predict_resp = requests.post(predict_url, json=payload, headers=headers, timeout=TIMEOUT)
    except Exception as e:
        assert False, f"Request to /api/predict failed: {e}"

    assert predict_resp.status_code == 200, f"Expected 200 from /api/predict, got {predict_resp.status_code}"
    pred_json = predict_resp.json()
    # Validate required keys in response
    expected_keys = {
        "prediction_id", "crop", "yield", "price", "confidence", "top3", "inputs", "weather", "timestamp"
    }
    assert all(key in pred_json for key in expected_keys)

    # Validate crop object keys
    crop = pred_json["crop"]
    assert "name" in crop and "icon" in crop and "insight" in crop and "seasons" in crop

    # Validate yield object keys
    yld = pred_json["yield"]
    assert "value" in yld and "unit" in yld and "range" in yld

    # Validate price object keys
    price = pred_json["price"]
    assert "value" in price and "unit" in price

    # Validate confidence is a number
    confidence = pred_json["confidence"]
    assert isinstance(confidence, (int, float))

    # Validate top3 is list with 3 elements at most
    top3 = pred_json["top3"]
    assert isinstance(top3, list)
    assert len(top3) > 0

    # Validate inputs matches at least keys sent (N, P, K, ph)
    inputs = pred_json["inputs"]
    for key in ("N", "P", "K", "ph"):
        assert key in inputs

    # Validate weather is present and matches autofill data (partial check)
    weather = pred_json["weather"]
    assert weather is not None
    # The weather object should have temperature, humidity, rainfall keys
    assert "temperature" in weather and "humidity" in weather and "rainfall" in weather

    # Optionally validate that returned weather matches or is close to autofill values
    # (Allow minor float difference)
    def approx_equal(a, b, tol=0.1):
        return abs(a - b) <= tol

    assert approx_equal(weather["temperature"], temperature), "Returned weather temperature differs from autofill"
    assert approx_equal(weather["humidity"], humidity), "Returned weather humidity differs from autofill"
    assert approx_equal(weather["rainfall"], rainfall), "Returned weather rainfall differs from autofill"

    # Validate timestamp is a string
    timestamp = pred_json["timestamp"]
    assert isinstance(timestamp, str)


test_croppredictionweatherautofill()
