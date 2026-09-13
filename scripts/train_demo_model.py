from pathlib import Path
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "models" / "voice_integrity_model.joblib"

rng = np.random.default_rng(42)
n = 1600
X = rng.normal(0, 1, (n, 42))
y = np.r_[np.zeros(n//2, dtype=int), np.ones(n//2, dtype=int)]

X[n//2:, 1] += 1.0
X[n//2:, 5] -= 0.8
X[n//2:, 16:29] -= 0.7
X[n//2:, 29:] += 0.6

Xt, Xv, yt, yv = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
model = Pipeline([
    ("scale", StandardScaler()),
    ("clf", RandomForestClassifier(n_estimators=250, random_state=42))
])
model.fit(Xt, yt)
pred = model.predict(Xv)

print("DEMO-ONLY validation accuracy:", round(accuracy_score(yv, pred), 3))
print(classification_report(yv, pred))
MODEL.parent.mkdir(exist_ok=True)
joblib.dump(model, MODEL)
print("Saved:", MODEL)
