"""
AgriSense — Model Training Script
Generates synthetic agricultural data and trains three ML models:
  1. Crop Recommendation  (RandomForestClassifier)
  2. Yield Prediction     (RandomForestRegressor)
  3. Price Forecast       (RandomForestRegressor)
Saves models + label encoder to /models/
"""

import numpy as np
import pandas as pd
import pickle, os
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error

np.random.seed(42)
N_SAMPLES = 2200
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# ── Crop profiles ──────────────────────────────────────────────────────────
CROP_PROFILES = {
    "Rice":      dict(N=(60,120),  P=(30,60),  K=(30,60),  ph=(5.5,7.0), hum=(80,95),  temp=(22,35), rain=(150,300), yield_r=(3.5,5.5),  base_price=2000),
    "Wheat":     dict(N=(60,120),  P=(40,80),  K=(40,80),  ph=(6.0,7.5), hum=(50,70),  temp=(10,25), rain=(30,90),   yield_r=(2.8,4.5),  base_price=2150),
    "Maize":     dict(N=(80,140),  P=(35,70),  K=(35,70),  ph=(5.5,7.0), hum=(55,80),  temp=(18,32), rain=(60,150),  yield_r=(4.0,7.5),  base_price=1875),
    "Cotton":    dict(N=(40,80),   P=(20,50),  K=(20,50),  ph=(6.0,8.0), hum=(50,75),  temp=(21,35), rain=(20,80),   yield_r=(1.5,2.8),  base_price=6350),
    "Sugarcane": dict(N=(80,140),  P=(30,60),  K=(60,120), ph=(6.0,7.5), hum=(70,90),  temp=(20,35), rain=(150,300), yield_r=(60,100),   base_price=302),
    "Chickpea":  dict(N=(10,40),   P=(40,80),  K=(20,50),  ph=(6.0,8.0), hum=(30,55),  temp=(8,26),  rain=(30,80),   yield_r=(0.9,1.8),  base_price=5400),
    "Lentil":    dict(N=(10,35),   P=(35,70),  K=(20,45),  ph=(6.0,8.0), hum=(30,55),  temp=(8,25),  rain=(25,75),   yield_r=(0.8,1.5),  base_price=6100),
    "Mango":     dict(N=(50,100),  P=(20,50),  K=(50,100), ph=(5.5,7.5), hum=(60,80),  temp=(24,35), rain=(80,200),  yield_r=(8,15),     base_price=3250),
    "Banana":    dict(N=(80,140),  P=(30,60),  K=(80,140), ph=(5.5,7.0), hum=(70,90),  temp=(22,35), rain=(150,250), yield_r=(25,45),    base_price=1200),
    "Grapes":    dict(N=(30,70),   P=(20,50),  K=(30,70),  ph=(5.5,7.5), hum=(60,80),  temp=(15,30), rain=(50,150),  yield_r=(12,22),    base_price=6000),
}

rows = []
per_crop = N_SAMPLES // len(CROP_PROFILES)

for crop, p in CROP_PROFILES.items():
    for _ in range(per_crop):
        N    = np.random.uniform(*p["N"])
        P    = np.random.uniform(*p["P"])
        K    = np.random.uniform(*p["K"])
        ph   = np.random.uniform(*p["ph"])
        hum  = np.random.uniform(*p["hum"])
        temp = np.random.uniform(*p["temp"])
        rain = np.random.uniform(*p["rain"])
        yld  = np.random.uniform(*p["yield_r"])
        # price varies ±15% around base
        price = p["base_price"] * np.random.uniform(0.85, 1.15)
        rows.append([N, P, K, ph, hum, temp, rain, crop, round(yld,3), round(price,1)])

df = pd.DataFrame(rows, columns=["N","P","K","ph","humidity","temperature","rainfall","crop","yield","price"])
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

# Save dataset
df.to_csv(os.path.join(MODELS_DIR, "crop_data.csv"), index=False)
print(f"Dataset: {len(df)} rows  |  Crops: {df['crop'].nunique()}")

# ── Label encode crop ──────────────────────────────────────────────────────
le = LabelEncoder()
df["crop_enc"] = le.fit_transform(df["crop"])

FEATURES = ["N","P","K","ph","humidity","temperature","rainfall"]
X = df[FEATURES].values
y_crop  = df["crop_enc"].values
y_yield = df["yield"].values
y_price = df["price"].values

X_tr, X_te, yc_tr, yc_te, yy_tr, yy_te, yp_tr, yp_te = train_test_split(
    X, y_crop, y_yield, y_price, test_size=0.2, random_state=42
)

# ── Train models ───────────────────────────────────────────────────────────
print("\nTraining Crop Recommendation model...")
clf = RandomForestClassifier(n_estimators=200, max_depth=15, random_state=42, n_jobs=-1)
clf.fit(X_tr, yc_tr)
acc = accuracy_score(yc_te, clf.predict(X_te))
print(f"  Accuracy : {acc*100:.1f}%")

print("Training Yield Prediction model...")
reg_yield = RandomForestRegressor(n_estimators=200, max_depth=15, random_state=42, n_jobs=-1)
reg_yield.fit(X_tr, yy_tr)
mae_y = mean_absolute_error(yy_te, reg_yield.predict(X_te))
print(f"  MAE      : {mae_y:.3f} t/ha")

print("Training Price Forecast model...")
reg_price = RandomForestRegressor(n_estimators=200, max_depth=15, random_state=42, n_jobs=-1)
reg_price.fit(X_tr, yp_tr)
mae_p = mean_absolute_error(yp_te, reg_price.predict(X_te))
print(f"  MAE      : Rs.{mae_p:.1f} /quintal")

# ── Save artefacts ─────────────────────────────────────────────────────────
with open(os.path.join(MODELS_DIR, "crop_model.pkl"),  "wb") as f: pickle.dump(clf, f)
with open(os.path.join(MODELS_DIR, "yield_model.pkl"), "wb") as f: pickle.dump(reg_yield, f)
with open(os.path.join(MODELS_DIR, "price_model.pkl"), "wb") as f: pickle.dump(reg_price, f)
with open(os.path.join(MODELS_DIR, "label_encoder.pkl"), "wb") as f: pickle.dump(le, f)

print("\nAll models saved to /models/")
print("Crops supported:", list(le.classes_))