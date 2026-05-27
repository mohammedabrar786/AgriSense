# AgriSense v2.0 — Flask Backend + Weather API

## Project Structure
```
agrisense/
├── app.py                          ← Flask API (v2 with weather)
├── train_models.py                 ← ML model training script
├── requirements.txt                ← Python dependencies
├── models/                         ← Saved .pkl model files
│   ├── crop_model.pkl
│   ├── yield_model.pkl
│   ├── price_model.pkl
│   └── label_encoder.pkl
└── static/
    └── index.html                  ← Place frontend HTML here
```

---

## Quick Start (3 steps)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Train ML models (run once)
python train_models.py

# 3. Set weather API key and start server
export OPENWEATHER_API_KEY="your_free_key_here"
python app.py
```

Server runs at: **http://localhost:5000**

---

## Getting a Free Weather API Key

1. Go to https://openweathermap.org/api
2. Click **Sign Up** (free)
3. After confirming email, go to **API Keys** tab
4. Copy your default key (or create a new one)
5. Wait ~10 minutes for key to activate

Free tier includes:
- 1,000 API calls/day
- Current weather data
- Global city coverage

---

## API Endpoints

### POST /api/predict
Crop recommendation + yield + price prediction.

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "N": 90, "P": 42, "K": 43, "ph": 6.5,
    "humidity": 82, "temperature": 27, "rainfall": 200,
    "region": "South India", "season": "Kharif"
  }'
```

**With live weather auto-merge:**
```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "N": 90, "P": 42, "K": 43, "ph": 6.5,
    "use_weather": true, "city": "Chennai"
  }'
```

**Response:**
```json
{
  "prediction_id": "a1b2c3d4",
  "crop": { "name": "Rice", "icon": "🌾", "insight": "...", "seasons": ["Kharif"] },
  "yield":  { "value": 4.23, "unit": "tonnes/ha", "range": [3.81, 4.65] },
  "price":  { "value": 2050, "unit": "Rs/quintal" },
  "confidence": 87.4,
  "top3": [
    { "crop": "Rice",      "probability": 87.4 },
    { "crop": "Maize",     "probability": 8.2  },
    { "crop": "Sugarcane", "probability": 4.4  }
  ],
  "weather": { ... },
  "timestamp": "2025-03-08T10:30:00Z"
}
```

---

### GET /api/weather?city=Chennai
Returns full live weather for any city.

```bash
curl http://localhost:5000/api/weather?city=Chennai
```

**Response:**
```json
{
  "weather": {
    "city": "Chennai", "country": "IN",
    "temperature": 32.4, "feels_like": 38.1,
    "humidity": 78, "pressure": 1008,
    "condition": "Clear", "description": "Clear sky",
    "icon_url": "https://openweathermap.org/img/wn/01d@2x.png",
    "wind_speed": 4.2, "clouds_pct": 10,
    "rainfall_mm": 0.0,
    "advisory": "Clear skies — ideal for field operations and spraying.",
    "sunrise": "06:14 UTC", "sunset": "12:28 UTC"
  }
}
```

---

### GET /api/weather/autofill?city=Chennai
Returns weather shaped as form input values (used by the frontend).

```bash
curl http://localhost:5000/api/weather/autofill?city=Mumbai
```

**Response:**
```json
{
  "city": "Mumbai", "country": "IN",
  "autofill": {
    "temperature": 29.5,
    "humidity": 85,
    "rainfall": 0.0
  },
  "display": {
    "condition": "Clouds",
    "description": "Broken clouds",
    "icon_url": "...",
    "feels_like": 34.2,
    "temp_min": 27.1, "temp_max": 31.0,
    "wind_speed": 5.1,
    "advisory": "Overcast — moderate evaporation, monitor soil moisture."
  }
}
```

---

### GET /api/health
```json
{
  "status": "ok",
  "models": ["crop_model", "yield_model", "price_model"],
  "crops": 10,
  "weather_api": "configured",
  "time": "2025-03-08T10:30:00Z"
}
```

### GET /api/crops
List all 10 supported crops with metadata.

### GET /api/history?limit=50
Server-side prediction log.

### POST /api/feedback
```json
{ "prediction_id": "a1b2c3d4", "correct": false, "actual_crop": "Maize" }
```

---

## How Weather Integration Works

```
User types city name
        ↓
Frontend calls GET /api/weather/autofill?city=Chennai
        ↓
Flask calls OpenWeatherMap API
        ↓
Returns: temperature=32°C, humidity=78%, rainfall=0mm
        ↓
Frontend auto-fills those 3 form fields (highlighted in blue)
        ↓
User fills remaining soil fields (N, P, K, pH)
        ↓
Frontend calls POST /api/predict with all values
        ↓
ML models return: Crop=Rice, Yield=4.3t, Price=Rs.2000, Confidence=87%
```

---

## Input Ranges
| Field       | Min  | Max  | Unit     |
|-------------|------|------|----------|
| N           | 0    | 140  | kg/ha    |
| P           | 0    | 145  | kg/ha    |
| K           | 0    | 205  | kg/ha    |
| ph          | 3.5  | 9.5  | —        |
| humidity    | 14   | 100  | %        |
| temperature | 0    | 50   | °C       |
| rainfall    | 0    | 300  | mm       |

## Supported Crops
Rice, Wheat, Maize, Cotton, Sugarcane, Chickpea, Lentil, Mango, Banana, Grapes