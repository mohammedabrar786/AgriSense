"""
AgriSense Flask Backend
=======================
Endpoints:
  POST /api/predict      — main prediction (crop + yield + price)
  GET  /api/crops        — list all supported crops
  GET  /api/health       — health check
  GET  /api/history      — server-side prediction history (last 50)
  POST /api/feedback     — store user feedback on a prediction
  GET  /                 — serves the frontend HTML
"""

import os, json, uuid, pickle, logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import numpy as np

# ── App setup ──────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = app.logger

# ── Load models ────────────────────────────────────────────────────────────
def load_model(name):
    path = os.path.join(MODELS_DIR, name)
    with open(path, "rb") as f:
        return pickle.load(f)

try:
    crop_model    = load_model("crop_model.pkl")
    yield_model   = load_model("yield_model.pkl")
    price_model   = load_model("price_model.pkl")
    label_encoder = load_model("label_encoder.pkl")
    log.info("All ML models loaded successfully.")
except FileNotFoundError as e:
    log.error(f"Model file missing: {e}. Run train_models.py first.")
    raise

# ── Crop metadata (icons, insights, seasons) ──────────────────────────────
CROP_META = {
    "Rice":      {"icon":"🌾","season":["Kharif"],"insight":"Maintain 5-10 cm water depth during tillering for best yield."},
    "Wheat":     {"icon":"🌿","season":["Rabi"],  "insight":"First irrigation at CRI stage maximises root development."},
    "Maize":     {"icon":"🌽","season":["Kharif","Zaid"],"insight":"Ensure well-drained loamy soil; avoid waterlogging."},
    "Cotton":    {"icon":"☁", "season":["Kharif"],"insight":"Drip irrigation can improve lint quality by 18%."},
    "Sugarcane": {"icon":"🎋","season":["Kharif","Perennial"],"insight":"Ratoon cropping is economical after the first harvest."},
    "Chickpea":  {"icon":"🫘","season":["Rabi"],  "insight":"Inoculate seeds with Rhizobium to cut fertiliser costs."},
    "Lentil":    {"icon":"🟤","season":["Rabi"],  "insight":"Drought-tolerant; avoid excess nitrogen."},
    "Mango":     {"icon":"🥭","season":["Perennial"],"insight":"A dry spell before flowering improves fruit set."},
    "Banana":    {"icon":"🍌","season":["Perennial"],"insight":"Split fertiliser application boosts yields significantly."},
    "Grapes":    {"icon":"🍇","season":["Rabi","Zaid"],"insight":"Regulated deficit irrigation improves berry quality."},
}

# ── In-memory prediction history (replace with DB in production) ───────────
prediction_history = []

# ── Input validation ───────────────────────────────────────────────────────
FIELD_RULES = {
    "N":           (0,   140,  "Nitrogen (N) must be between 0–140 kg/ha"),
    "P":           (0,   145,  "Phosphorus (P) must be between 0–145 kg/ha"),
    "K":           (0,   205,  "Potassium (K) must be between 0–205 kg/ha"),
    "ph":          (3.5, 9.5,  "pH must be between 3.5–9.5"),
    "humidity":    (14,  100,  "Humidity must be between 14–100 %"),
    "temperature": (0,   50,   "Temperature must be between 0–50 °C"),
    "rainfall":    (0,   300,  "Rainfall must be between 0–300 mm"),
}

def validate_inputs(data):
    errors = []
    values = {}
    for field, (lo, hi, msg) in FIELD_RULES.items():
        raw = data.get(field)
        if raw is None:
            errors.append(f"Missing field: '{field}'")
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

# ── CORS helper (no flask-cors needed) ────────────────────────────────────
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

@app.after_request
def after(response):
    return add_cors(response)

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        from flask import Response
        return add_cors(Response(status=204))

# ══════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Serve frontend HTML if present, otherwise show API info."""
    html_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(html_path):
        return send_from_directory(STATIC_DIR, "index.html")
    return jsonify({
        "app": "AgriSense API",
        "version": "1.0",
        "status": "running",
        "endpoints": {
            "POST /api/predict":  "Get crop recommendation + yield + price",
            "GET  /api/crops":    "List supported crops",
            "GET  /api/health":   "Health check",
            "GET  /api/history":  "Prediction history (last 50)",
            "POST /api/feedback": "Submit feedback on a prediction",
        }
    })


@app.route("/api/health")
def health():
    """Health check — confirms models are loaded."""
    return jsonify({
        "status":  "ok",
        "models":  ["crop_model", "yield_model", "price_model"],
        "crops":   len(label_encoder.classes_),
        "time":    datetime.utcnow().isoformat() + "Z",
    })


@app.route("/api/crops")
def crops():
    """Return list of all supported crops with metadata."""
    result = []
    for crop in sorted(label_encoder.classes_):
        meta = CROP_META.get(crop, {})
        result.append({
            "name":    crop,
            "icon":    meta.get("icon", "🌱"),
            "seasons": meta.get("season", []),
            "insight": meta.get("insight", ""),
        })
    return jsonify({"crops": result, "total": len(result)})


@app.route("/api/predict", methods=["POST", "OPTIONS"])
def predict():
    """
    Main prediction endpoint.

    Request body (JSON):
    {
        "N": 90, "P": 42, "K": 43, "ph": 6.5,
        "humidity": 82, "temperature": 27, "rainfall": 200,
        "region": "South India",   // optional
        "season": "Kharif"         // optional
    }

    Response:
    {
        "prediction_id": "...",
        "crop":     { "name", "icon", "insight", "seasons" },
        "yield":    { "value": 4.23, "unit": "tonnes/ha", "range": [3.5,5.5] },
        "price":    { "value": 2050, "unit": "Rs/quintal" },
        "confidence": 87.4,
        "top3":     [ {crop, probability}, ... ],
        "inputs":   { ...validated inputs },
        "timestamp": "..."
    }
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json(silent=True) or {}
    values, errors = validate_inputs(data)

    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 422

    # Build feature vector
    feat = np.array([[
        values["N"], values["P"], values["K"],
        values["ph"], values["humidity"],
        values["temperature"], values["rainfall"],
    ]])

    # ── 1. Crop recommendation ──
    probas      = crop_model.predict_proba(feat)[0]
    top_idx     = int(np.argmax(probas))
    crop_name   = label_encoder.inverse_transform([top_idx])[0]
    confidence  = round(float(probas[top_idx]) * 100, 1)

    # Top-3 alternatives
    top3_indices = np.argsort(probas)[::-1][:3]
    top3 = [
        {"crop": label_encoder.inverse_transform([i])[0],
         "probability": round(float(probas[i]) * 100, 1)}
        for i in top3_indices
    ]

    # ── 2. Yield prediction ──
    pred_yield = float(yield_model.predict(feat)[0])
    pred_yield = round(max(0.1, pred_yield), 2)

    # Yield range = ±10% of prediction
    yield_lo = round(pred_yield * 0.90, 2)
    yield_hi = round(pred_yield * 1.10, 2)

    # ── 3. Price forecast ──
    pred_price = float(price_model.predict(feat)[0])
    pred_price = round(max(50, pred_price))

    # ── Crop metadata ──
    meta = CROP_META.get(crop_name, {})

    # ── Build response ──
    prediction_id = str(uuid.uuid4())[:8]
    result = {
        "prediction_id": prediction_id,
        "crop": {
            "name":    crop_name,
            "icon":    meta.get("icon", "🌱"),
            "insight": meta.get("insight", ""),
            "seasons": meta.get("season", []),
        },
        "yield": {
            "value": pred_yield,
            "unit":  "tonnes/ha",
            "range": [yield_lo, yield_hi],
        },
        "price": {
            "value": pred_price,
            "unit":  "Rs/quintal",
        },
        "confidence":   confidence,
        "top3":         top3,
        "inputs":       values,
        "region":       data.get("region", ""),
        "season":       data.get("season", ""),
        "timestamp":    datetime.utcnow().isoformat() + "Z",
    }

    # Save to history
    prediction_history.insert(0, result)
    if len(prediction_history) > 100:
        prediction_history.pop()

    log.info(f"[{prediction_id}] {crop_name} | conf={confidence}% | yield={pred_yield} | price=Rs.{pred_price}")
    return jsonify(result), 200


@app.route("/api/history")
def history():
    """Return last 50 predictions (server-side log)."""
    limit = min(int(request.args.get("limit", 50)), 100)
    return jsonify({
        "history": prediction_history[:limit],
        "total":   len(prediction_history),
    })


@app.route("/api/feedback", methods=["POST"])
def feedback():
    """
    Accept user feedback on a prediction.
    Body: { "prediction_id": "...", "correct": true/false, "actual_crop": "Rice" }
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    data = request.get_json(silent=True) or {}
    pred_id = data.get("prediction_id")
    if not pred_id:
        return jsonify({"error": "prediction_id is required"}), 422
    # In production: persist to DB for model retraining
    log.info(f"Feedback received for [{pred_id}]: correct={data.get('correct')} actual={data.get('actual_crop','?')}")
    return jsonify({"status": "received", "prediction_id": pred_id}), 200


# ── Error handlers ─────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)