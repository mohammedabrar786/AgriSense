import requests

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

def test_croppredictioninvalidcontenttype():
    url = f"{BASE_URL}/api/predict"

    # Case 1: Missing Content-Type header
    response1 = requests.post(url, data='{"N": 10, "P": 10, "K": 10, "ph": 6.5, "humidity": 50, "temperature": 25, "rainfall": 100}', timeout=TIMEOUT)
    assert response1.status_code == 400
    json1 = response1.json()
    assert "error" in json1
    assert json1["error"] == "Content-Type must be application/json"

    # Case 2: Content-Type is not application/json (e.g. text/plain)
    headers2 = {"Content-Type": "text/plain"}
    response2 = requests.post(url, data='{"N": 10, "P": 10, "K": 10, "ph": 6.5, "humidity": 50, "temperature": 25, "rainfall": 100}', headers=headers2, timeout=TIMEOUT)
    assert response2.status_code == 400
    json2 = response2.json()
    assert "error" in json2
    assert json2["error"] == "Content-Type must be application/json"

    # Case 3: Content-Type set correctly but payload is malformed JSON
    headers3 = {"Content-Type": "application/json"}
    malformed_json = '{"N":10, "P":10, "K":10, "ph":6.5, "humidity":50, "temperature":25, "rainfall":100'  # Missing closing brace
    response3 = requests.post(url, data=malformed_json, headers=headers3, timeout=TIMEOUT)
    assert response3.status_code == 400
    json3 = response3.json()
    assert "error" in json3
    assert json3["error"] == "Content-Type must be application/json"

test_croppredictioninvalidcontenttype()
