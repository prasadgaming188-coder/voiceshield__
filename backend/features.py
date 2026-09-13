import numpy as np
import librosa

FEATURE_NAMES = (
    ["duration", "rms_mean", "rms_std", "zcr_mean", "zcr_std",
     "spectral_centroid_mean", "spectral_centroid_std",
     "spectral_bandwidth_mean", "spectral_bandwidth_std",
     "spectral_rolloff_mean", "spectral_rolloff_std",
     "spectral_flatness_mean", "spectral_flatness_std",
     "pitch_mean", "pitch_std", "pitch_range"]
    + [f"mfcc_{i+1}_mean" for i in range(13)]
    + [f"mfcc_{i+1}_std" for i in range(13)]
)

def _stats(x):
    return float(np.mean(x)), float(np.std(x))

def extract_features(path):
    y, sr = librosa.load(path, sr=16000, mono=True)
    if y.size == 0:
        raise ValueError("Audio file is empty.")
    y, _ = librosa.effects.trim(y, top_db=30)
    if y.size < int(sr * 0.25):
        raise ValueError("Audio is too short. Please provide at least 1 second.")

    duration = len(y) / sr
    rms = librosa.feature.rms(y=y)[0]
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    flatness = librosa.feature.spectral_flatness(y=y)[0]

    f0, _, _ = librosa.pyin(
        y, fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"), sr=sr
    )
    pitch = f0[np.isfinite(f0)]
    pitch_mean = float(np.mean(pitch)) if pitch.size else 0.0
    pitch_std = float(np.std(pitch)) if pitch.size else 0.0
    pitch_range = float(np.ptp(pitch)) if pitch.size else 0.0

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)

    values = [
        duration, *_stats(rms), *_stats(zcr), *_stats(centroid),
        *_stats(bandwidth), *_stats(rolloff), *_stats(flatness),
        pitch_mean, pitch_std, pitch_range,
        *list(np.mean(mfcc, axis=1)), *list(np.std(mfcc, axis=1))
    ]
    return {n: float(v) for n, v in zip(FEATURE_NAMES, values)}
