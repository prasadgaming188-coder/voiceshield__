from pathlib import Path
import joblib
import numpy as np
from .features import extract_features, FEATURE_NAMES
from .risk import combine_risk

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "voice_integrity_model.joblib"

# These are prototype speaker-consistency weights, not a validated biometric model.
COMPARE_NAMES = [
    "pitch_mean", "pitch_std", "pitch_range",
    "spectral_centroid_mean", "spectral_bandwidth_mean", "spectral_rolloff_mean",
    "spectral_flatness_mean",
] + [f"mfcc_{i}_mean" for i in range(1, 14)]

SCALES = {
    "pitch_mean": 80.0, "pitch_std": 60.0, "pitch_range": 120.0,
    "spectral_centroid_mean": 1200.0, "spectral_bandwidth_mean": 1500.0,
    "spectral_rolloff_mean": 2500.0, "spectral_flatness_mean": 0.08,
}
for i in range(1, 14):
    SCALES[f"mfcc_{i}_mean"] = 25.0

def _vector(features):
    vals = []
    for name in COMPARE_NAMES:
        value = float(features.get(name, 0.0))
        scale = SCALES.get(name, 1.0)
        vals.append(value / scale)
    return np.asarray(vals, dtype=float)

def speaker_similarity(a, b):
    va, vb = _vector(a), _vector(b)
    # Blend cosine similarity and normalized feature distance for a stable demo score.
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    cosine = float(np.dot(va, vb) / (na * nb + 1e-9))
    cosine = max(-1.0, min(1.0, cosine))
    cosine_score = (cosine + 1.0) / 2.0
    distance = float(np.mean(np.abs(va - vb)))
    distance_score = 1.0 / (1.0 + distance)
    score = 100.0 * (0.65 * cosine_score + 0.35 * distance_score)
    return round(max(0.0, min(100.0, score)), 1)

def analyze_audio(path, context=None, reference_path=None):
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Model not found. Run: python scripts/train_demo_model.py"
        )
    if not path and not reference_path:
        raise ValueError("At least one audio sample is required.")

    context = context or {}
    model = joblib.load(MODEL_PATH)
    target_path = path or reference_path
    features = extract_features(target_path)
    x = np.array([[features[n] for n in FEATURE_NAMES]], dtype=float)

    pred = int(model.predict(x)[0])
    proba = model.predict_proba(x)[0]
    classes = list(model.classes_)
    model_voice_risk = (
        float(proba[classes.index(1)]) * 100
        if 1 in classes else float(pred) * 100
    )

    similarity = None
    comparison_adjustment = 0.0
    comparison_status = "Single-sample analysis"
    reference_features = None
    if path and reference_path:
        reference_features = extract_features(reference_path)
        similarity = speaker_similarity(features, reference_features)
        # High consistency lowers speaker-mismatch risk, while preserving some model signal.
        mismatch_risk = 100.0 - similarity
        adjusted_voice_risk = 0.35 * model_voice_risk + 0.65 * mismatch_risk
        comparison_adjustment = adjusted_voice_risk - model_voice_risk
        voice_risk = adjusted_voice_risk
        if similarity >= 80:
            comparison_status = "High speaker consistency"
        elif similarity >= 60:
            comparison_status = "Moderate speaker consistency"
        else:
            comparison_status = "Low speaker consistency"
    else:
        voice_risk = model_voice_risk

    final, level, recommendation, adjustment, reasons = combine_risk(
        voice_risk, context
    )

    if voice_risk >= 70:
        prediction = "SUSPICIOUS_VOICE"
    elif voice_risk >= 40:
        prediction = "SUSPICIOUS_VOICE"
    else:
        prediction = "LIKELY_GENUINE"

    spectral = min(100, max(0, voice_risk + features["spectral_flatness_mean"] * 100 - 5))
    prosody = min(100, max(0, voice_risk + features["pitch_std"] * 0.05))
    acoustic = min(100, max(0, voice_risk + features["rms_std"] * 30))

    return {
        "prediction": prediction,
        "voice_risk": round(voice_risk, 1),
        "model_voice_risk": round(model_voice_risk, 1),
        "contextual_risk": round(final, 1),
        "risk_score": round(final, 1),
        "authenticity_score": round(100 - final, 1),
        "risk_level": level,
        "recommendation": recommendation,
        "context_adjustment": round(adjustment, 1),
        "comparison_adjustment": round(comparison_adjustment, 1),
        "speaker_similarity": similarity,
        "comparison_status": comparison_status,
        "reasons": reasons,
        "layers": {
            "acoustic": round(acoustic, 1),
            "spectral": round(spectral, 1),
            "prosody": round(prosody, 1)
        },
        "features": features
    }
