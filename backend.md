# AgriSense — Flask Backend

## Project Structure
```
agrisense/
├── app.py              ← Flask API server
├── train_models.py     ← ML model training script
├── requirements.txt    ← Python dependencies
├── models/             ← Saved ML model files (auto-created)
│   ├── crop_model.pkl
│   ├── yield_model.pkl
│   ├── price_model.pkl
│   ├── label_encoder.pkl
│   └── crop_data.csv
└── static/
    └── index.html      ← Place your frontend HTML here
```

---

## Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Train ML models (run once)
```bash
python train_models.py
```
This generates a synthetic dataset and trains 3 Random Forest models with ~88% accuracy.

### 3. Start the Flask server
```bash
python app.py
```
Server runs at: `http://localhost:5000`

---

## API Endpoints

### POST /api/predict
**Get crop recommendation, yield estimate, and price forecast.**

Request:
```json
{
  "N": 90,
  "P": 42,
  "K": 43,
  "ph": 6.5,
  "humidity": 82,
  "temperature": 27,
  "rainfall": 200,
  "region": "South India",
  "season": "Kharif"
}
```

Response:
```json
{
  "prediction_id": "a1b2c3d4",
  "crop": {
    "name": "Rice",
    "icon": "🌾",
    "insight": "Maintain 5-10 cm water depth during tillering.",
    "seasons": ["Kharif"]
  },
  "yield": {
    "value": 4.23,
    "unit": "tonnes/ha",
    "range": [3.81, 4.65]
  },
  "price": {
    "value": 2050,
    "unit": "Rs/quintal"
  },
  "confidence": 87.4,
  "top3": [
    {"crop": "Rice", "probability": 87.4},
    {"crop": "Maize", "probability": 8.2},
    {"crop": "Sugarcane", "probability": 4.4}
  ],
  "inputs": {"N": 90, "P": 42, ...},
  "timestamp": "2025-03-08T10:30:00Z"
}
```

### GET /api/health
Returns server status and model info.

### GET /api/crops
Returns all 10 supported crops with metadata.

### GET /api/history?limit=50
Returns server-side prediction log.

### POST /api/feedback
Submit feedback on a prediction result.
```json
{ "prediction_id": "a1b2c3d4", "correct": false, "actual_crop": "Maize" }
```

---

## Connecting the Frontend

In your `static/index.html`, replace the mock `setTimeout` in `runPrediction()` with:

```javascript
async function runPrediction() {
  const payload = {
    N: parseFloat(document.getElementById('nitrogen').value),
    P: parseFloat(document.getElementById('phosphorus').value),
    K: parseFloat(document.getElementById('potassium').value),
    ph: parseFloat(document.getElementById('ph').value),
    humidity: parseFloat(document.getElementById('humidity').value),
    temperature: parseFloat(document.getElementById('temperature').value),
    rainfall: parseFloat(document.getElementById('rainfall').value),
    region: document.getElementById('region').value,
    season: document.getElementById('season').value,
  };

  const response = await fetch('http://localhost:5000/api/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const result = await response.json();

  if (!response.ok) {
    alert('Error: ' + (result.details || result.error));
    return;
  }

  // Use result.crop.name, result.yield.value, result.price.value, result.confidence
  showResult(result);
}
```

---

## Supported Crops
Rice, Wheat, Maize, Cotton, Sugarcane, Chickpea, Lentil, Mango, Banana, Grapes

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