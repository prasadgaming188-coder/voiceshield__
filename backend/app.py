from pathlib import Path
import json, os, tempfile
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from .detector import analyze_audio
from .db import init_db, log_event, recent_events

BASE = Path(__file__).resolve().parent.parent
FRONTEND = BASE / "frontend"
ALLOWED = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}

app = Flask(__name__, static_folder=str(FRONTEND), static_url_path="")
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
init_db()

@app.get("/")
def home():
    return send_from_directory(FRONTEND, "index.html")

@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "VoiceShield",
        "mode": "hackathon-prototype",
        "audio_retention": "temporary-processing"
    })

@app.get("/api/events")
def events():
    return jsonify(recent_events())

@app.post("/api/analyze")
def analyze():
    if "audio" not in request.files and "reference_audio" not in request.files:
        return jsonify({"error": "Record or upload at least one audio sample."}), 400

    uploaded = request.files.get("audio")
    reference = request.files.get("reference_audio")
    files = [("audio", uploaded), ("reference_audio", reference)]
    for label, item in files:
        if item is not None and item.filename:
            suffix = Path(item.filename).suffix.lower()
            if suffix not in ALLOWED:
                return jsonify({"error": "Supported: WAV, MP3, M4A, FLAC, OGG."}), 400

    try:
        context = json.loads(request.form.get("context", "{}"))
    except json.JSONDecodeError:
        return jsonify({"error": "Context must be valid JSON."}), 400

    tmp = {}
    try:
        for label, item in files:
            if item is None or not item.filename:
                continue
            suffix = Path(item.filename).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as t:
                item.save(t.name)
                tmp[label] = t.name
        result = analyze_audio(tmp.get("audio"), context, tmp.get("reference_audio"))
        log_event(result)
        result["privacy"] = {
            "raw_audio_retained": False,
            "feature_only_logging": True
        }
        return jsonify(result)
    except Exception as exc:
        app.logger.exception("Audio analysis failed")
        return jsonify({"error": str(exc)}), 500
    finally:
        for path in tmp.values():
            try:
                os.remove(path)
            except OSError:
                pass

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
