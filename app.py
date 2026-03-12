"""
AgriSense Flask Backend v2.0 — with OpenWeatherMap Integration
==============================================================
Endpoints:
  POST /api/predict                    — crop + yield + price prediction
  GET  /api/weather?city=Chennai       — live weather data
  GET  /api/weather/autofill?city=...  — weather shaped as form inputs
  GET  /api/crops                      — list supported crops
  GET  /api/health                     — health + weather key status
  GET  /api/history?limit=50           — prediction history
  POST /api/feedback                   — user feedback

Setup:
  export OPENWEATHER_API_KEY="your_free_key"
  Get key at: https://openweathermap.org/api (free tier)
"""

import os, uuid, pickle, logging, urllib.request, urllib.parse, json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import numpy as np

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = app.logger

# OpenWeatherMap — set via env or paste key here
WEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
OWM_BASE        = "https://api.openweathermap.org/data/2.5"

# ── Load ML models ─────────────────────────────────────────────────────────
def load_model(name):
    with open(os.path.join(MODELS_DIR, name), "rb") as f:
        return pickle.load(f)

try:
    crop_model    = load_model("crop_model.pkl")
    yield_model   = load_model("yield_model.pkl")
    price_model   = load_model("price_model.pkl")
    label_encoder = load_model("label_encoder.pkl")
    log.info("All ML models loaded.")
except FileNotFoundError as e:
    log.error(f"Model missing: {e} — run train_models.py first.")
    raise

# ── Crop metadata ──────────────────────────────────────────────────────────
CROP_META = {
    "Rice":      {"icon":"🌾","season":["Kharif"],            "insight":"Maintain 5-10 cm water depth during tillering for best yield."},
    "Wheat":     {"icon":"🌿","season":["Rabi"],               "insight":"First irrigation at CRI stage maximises root development."},
    "Maize":     {"icon":"🌽","season":["Kharif","Zaid"],      "insight":"Ensure well-drained loamy soil; avoid waterlogging."},
    "Cotton":    {"icon":"🌸","season":["Kharif"],             "insight":"Drip irrigation can improve lint quality by 18%."},
    "Sugarcane": {"icon":"🎋","season":["Kharif","Perennial"], "insight":"Ratoon cropping is economical after the first harvest."},
    "Chickpea":  {"icon":"🫘","season":["Rabi"],               "insight":"Inoculate seeds with Rhizobium to cut fertiliser costs."},
    "Lentil":    {"icon":"🟤","season":["Rabi"],               "insight":"Drought-tolerant; avoid excess nitrogen."},
    "Mango":     {"icon":"🥭","season":["Perennial"],          "insight":"A dry spell before flowering improves fruit set."},
    "Banana":    {"icon":"🍌","season":["Perennial"],          "insight":"Split fertiliser application boosts yields significantly."},
    "Grapes":    {"icon":"🍇","season":["Rabi","Zaid"],        "insight":"Regulated deficit irrigation improves berry quality."},
}

# Weather condition to farming advisory mapping
WEATHER_ADVISORIES = {
    "Rain":         "Heavy rain forecast — check drainage, delay fertiliser application.",
    "Drizzle":      "Light rain expected — good for seedbed moisture, hold off irrigation.",
    "Thunderstorm": "Thunderstorms ahead — secure equipment, avoid field operations.",
    "Snow":         "Cold snap detected — protect sensitive crops with covers.",
    "Clear":        "Clear skies — ideal for field operations and spraying.",
    "Clouds":       "Overcast — moderate evaporation, monitor soil moisture.",
    "Mist":         "Foggy conditions — watch for fungal disease pressure.",
    "Fog":          "Dense fog — delay pesticide application until clear.",
    "Haze":         "Hazy conditions — ensure ventilation in greenhouses.",
    "Dust":         "Dusty — protect crop surfaces from dust deposit.",
}

prediction_history = []

# ── Validation ─────────────────────────────────────────────────────────────
FIELD_RULES = {
    "N":           (0,   140,  "Nitrogen must be 0-140 kg/ha"),
    "P":           (0,   145,  "Phosphorus must be 0-145 kg/ha"),
    "K":           (0,   205,  "Potassium must be 0-205 kg/ha"),
    "ph":          (3.5, 9.5,  "pH must be 3.5-9.5"),
    "humidity":    (14,  100,  "Humidity must be 14-100 %"),
    "temperature": (0,   50,   "Temperature must be 0-50 C"),
    "rainfall":    (0,   300,  "Rainfall must be 0-300 mm"),
}

def validate_inputs(data):
    errors, values = [], {}
    for field, (lo, hi, msg) in FIELD_RULES.items():
        raw = data.get(field)
        if raw is None:
            errors.append(f"Missing: '{field}'")
            continue
        try:
            val = float(raw)
        except (TypeError, ValueError):
            errors.append(f"'{field}' must be a number")
            continue
        if not (lo <= val <= hi):
            errors.append(msg)
        else:
            values[field] = val
    return values, errors

# ── CORS ───────────────────────────────────────────────────────────────────
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"]  = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return resp

@app.after_request
def after(resp): return add_cors(resp)

@app.before_request
def preflight():
    if request.method == "OPTIONS":
        from flask import Response
        return add_cors(Response(status=204))

# ── Weather helper ─────────────────────────────────────────────────────────
def fetch_weather(city: str) -> dict:
    if not WEATHER_API_KEY:
        raise ValueError(
            "OPENWEATHER_API_KEY not set. "
            "Get a free key at https://openweathermap.org/api "
            "then: export OPENWEATHER_API_KEY=your_key"
        )
    params = urllib.parse.urlencode({"q": city, "appid": WEATHER_API_KEY, "units": "metric"})
    url    = f"{OWM_BASE}/weather?{params}"
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode() or "{}")
        code = e.code
        if code == 401: raise ValueError("Invalid API key — check OPENWEATHER_API_KEY.")
        if code == 404: raise ValueError(f"City '{city}' not found.")
        raise ValueError(f"Weather API error {code}: {body.get('message', 'unknown')}")
    except urllib.error.URLError as e:
        raise ConnectionError(f"Cannot reach weather API: {e.reason}")

    main      = data.get("main", {})
    wind      = data.get("wind", {})
    weather_d = data.get("weather", [{}])[0]
    condition = weather_d.get("main", "Clear")
    icon_code = weather_d.get("icon", "01d")
    rain_1h   = data.get("rain", {}).get("1h", 0)
    rain_3h   = data.get("rain", {}).get("3h", 0)
    rain_est  = min(round(rain_1h * 24 if rain_1h else rain_3h * 8, 1), 300)

    return {
        "city":        data.get("name", city),
        "country":     data.get("sys", {}).get("country", ""),
        "temperature": round(main.get("temp", 0), 1),
        "feels_like":  round(main.get("feels_like", 0), 1),
        "temp_min":    round(main.get("temp_min", 0), 1),
        "temp_max":    round(main.get("temp_max", 0), 1),
        "humidity":    main.get("humidity", 0),
        "pressure":    main.get("pressure", 0),
        "condition":   condition,
        "description": weather_d.get("description", "").capitalize(),
        "icon_code":   icon_code,
        "icon_url":    f"https://openweathermap.org/img/wn/{icon_code}@2x.png",
        "wind_speed":  round(wind.get("speed", 0), 1),
        "wind_deg":    wind.get("deg", 0),
        "clouds_pct":  data.get("clouds", {}).get("all", 0),
        "rainfall_mm": rain_est,
        "visibility":  data.get("visibility", 0),
        "sunrise":     datetime.utcfromtimestamp(data.get("sys",{}).get("sunrise",0)).strftime("%H:%M UTC"),
        "sunset":      datetime.utcfromtimestamp(data.get("sys",{}).get("sunset", 0)).strftime("%H:%M UTC"),
        "advisory":    WEATHER_ADVISORIES.get(condition, "Monitor field conditions regularly."),
        "fetched_at":  datetime.utcnow().isoformat() + "Z",
    }

# ══════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    html = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(html):
        return send_from_directory(STATIC_DIR, "index.html")
    return jsonify({
        "app": "AgriSense API", "version": "2.0",
        "weather_api": "ready" if WEATHER_API_KEY else "needs OPENWEATHER_API_KEY",
        "endpoints": {
            "POST /api/predict":                   "Crop + yield + price",
            "GET  /api/weather?city=Chennai":       "Live weather",
            "GET  /api/weather/autofill?city=...":  "Weather as form values",
            "GET  /api/crops":                      "Supported crops",
            "GET  /api/health":                     "Health check",
            "GET  /api/history":                    "Prediction log",
            "POST /api/feedback":                   "Feedback",
        }
    })


@app.route("/api/health")
def health():
    return jsonify({
        "status":      "ok",
        "models":      ["crop_model", "yield_model", "price_model"],
        "crops":       len(label_encoder.classes_),
        "weather_api": "configured" if WEATHER_API_KEY else "not configured",
        "time":        datetime.utcnow().isoformat() + "Z",
    })


@app.route("/api/crops")
def crops():
    return jsonify({"crops": [
        {"name": c, **{k: CROP_META.get(c, {}).get(k, v)
         for k, v in [("icon","🌱"),("seasons",[]),("insight","")]}}
        for c in sorted(label_encoder.classes_)
    ], "total": len(label_encoder.classes_)})


# ── Weather routes ─────────────────────────────────────────────────────────

@app.route("/api/weather")
def weather():
    """Full weather data for a city."""
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify({"error": "city param required. E.g. /api/weather?city=Chennai"}), 400
    try:
        w = fetch_weather(city)
        log.info(f"Weather: {city} -> {w['temperature']}C {w['condition']}")
        return jsonify({"weather": w}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 503


@app.route("/api/weather/autofill")
def weather_autofill():
    """
    Returns weather data shaped for form auto-fill.
    Frontend uses this to populate temperature, humidity, rainfall fields.
    """
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify({"error": "city param required"}), 400
    try:
        w = fetch_weather(city)
        log.info(f"Autofill: {city} -> temp={w['temperature']} hum={w['humidity']} rain={w['rainfall_mm']}")
        return jsonify({
            "city":    w["city"],
            "country": w["country"],
            "autofill": {
                "temperature": w["temperature"],
                "humidity":    w["humidity"],
                "rainfall":    w["rainfall_mm"],
            },
            "display": {
                "condition":   w["condition"],
                "description": w["description"],
                "icon_url":    w["icon_url"],
                "feels_like":  w["feels_like"],
                "temp_min":    w["temp_min"],
                "temp_max":    w["temp_max"],
                "wind_speed":  w["wind_speed"],
                "clouds_pct":  w["clouds_pct"],
                "advisory":    w["advisory"],
                "sunrise":     w["sunrise"],
                "sunset":      w["sunset"],
            },
            "fetched_at": w["fetched_at"],
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 503


# ── Predict route ──────────────────────────────────────────────────────────

@app.route("/api/predict", methods=["POST", "OPTIONS"])
def predict():
    """
    Main prediction.
    Optional weather merge: include "use_weather": true, "city": "Chennai"
    to auto-fill temperature/humidity/rainfall from live weather.
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json(silent=True) or {}

    # Auto-merge weather data if requested
    weather_data = None
    if data.get("use_weather") and data.get("city"):
        try:
            w = fetch_weather(data["city"])
            data["temperature"] = w["temperature"]
            data["humidity"]    = w["humidity"]
            data["rainfall"]    = w["rainfall_mm"]
            weather_data        = w
            log.info(f"Weather merged for '{data['city']}'")
        except Exception as e:
            log.warning(f"Weather merge failed: {e}")

    values, errors = validate_inputs(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 422

    feat = np.array([[values["N"], values["P"], values["K"],
                      values["ph"], values["humidity"],
                      values["temperature"], values["rainfall"]]])

    # Crop recommendation
    probas    = crop_model.predict_proba(feat)[0]
    top_idx   = int(np.argmax(probas))
    crop_name = label_encoder.inverse_transform([top_idx])[0]
    conf      = round(float(probas[top_idx]) * 100, 1)
    top3      = [
        {"crop": label_encoder.inverse_transform([i])[0],
         "probability": round(float(probas[i]) * 100, 1)}
        for i in np.argsort(probas)[::-1][:3]
    ]

    # Yield
    pred_yield = round(max(0.1, float(yield_model.predict(feat)[0])), 2)

    # Price
    pred_price = round(max(50, float(price_model.predict(feat)[0])))

    meta = CROP_META.get(crop_name, {})
    pid  = str(uuid.uuid4())[:8]

    result = {
        "prediction_id": pid,
        "crop":    {"name": crop_name, "icon": meta.get("icon","🌱"),
                    "insight": meta.get("insight",""), "seasons": meta.get("season",[])},
        "yield":   {"value": pred_yield, "unit": "tonnes/ha",
                    "range": [round(pred_yield*.9,2), round(pred_yield*1.1,2)]},
        "price":   {"value": pred_price, "unit": "Rs/quintal"},
        "confidence": conf,
        "top3":    top3,
        "inputs":  values,
        "region":  data.get("region",""),
        "season":  data.get("season",""),
        "weather": weather_data,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    prediction_history.insert(0, result)
    if len(prediction_history) > 100:
        prediction_history.pop()

    log.info(f"[{pid}] {crop_name} conf={conf}% yield={pred_yield} price=Rs.{pred_price}")
    return jsonify(result), 200


@app.route("/api/history")
def history():
    limit = min(int(request.args.get("limit", 50)), 100)
    return jsonify({"history": prediction_history[:limit], "total": len(prediction_history)})


@app.route("/api/feedback", methods=["POST"])
def feedback():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    data = request.get_json(silent=True) or {}
    pid  = data.get("prediction_id")
    if not pid:
        return jsonify({"error": "prediction_id required"}), 422
    log.info(f"Feedback [{pid}]: correct={data.get('correct')} actual={data.get('actual_crop','?')}")
    return jsonify({"status": "received", "prediction_id": pid}), 200


@app.errorhandler(404)
def not_found(e):    return jsonify({"error": "Not found"}), 404
@app.errorhandler(500)
def server_error(e): return jsonify({"error": "Server error"}), 500


if __name__ == "__main__":
    print(f"\n  AgriSense API v2.0")
    print(f"  Weather key : {'SET ✓' if WEATHER_API_KEY else 'NOT SET — get one free at openweathermap.org'}")
    print(f"  Server      : http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=True)