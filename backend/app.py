from pathlib import Path
import json
import os
import tempfile

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from .detector import analyze_audio
from .db import init_db, log_event, recent_events


# --------------------------------------------------
# PATHS
# --------------------------------------------------

BASE = Path(__file__).resolve().parent.parent
FRONTEND = BASE / "frontend"

ALLOWED = {
    ".wav",
    ".mp3",
    ".m4a",
    ".flac",
    ".ogg"
}


# --------------------------------------------------
# FLASK APP
# --------------------------------------------------

app = Flask(
    __name__,
    static_folder=str(FRONTEND),
    static_url_path=""
)

CORS(app)

# Maximum upload size = 20 MB
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

init_db()


# --------------------------------------------------
# FRONTEND
# --------------------------------------------------

@app.get("/")
def home():
    return send_from_directory(
        str(FRONTEND),
        "index.html"
    )


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "VoiceShield",
        "mode": "hackathon-prototype",
        "audio_retention": "temporary-processing"
    }), 200


# --------------------------------------------------
# RECENT EVENTS
# --------------------------------------------------

@app.get("/api/events")
def events():
    try:
        return jsonify(recent_events()), 200

    except Exception as exc:
        app.logger.exception("Could not load events")

        return jsonify({
            "error": "Could not load events",
            "details": str(exc)
        }), 500


# --------------------------------------------------
# AUDIO ANALYSIS
# --------------------------------------------------

@app.post("/api/analyze")
def analyze():

    # ----------------------------------------------
    # CHECK AUDIO
    # ----------------------------------------------

    uploaded = request.files.get("audio")
    reference = request.files.get("reference_audio")

    if uploaded is None and reference is None:
        return jsonify({
            "error": "Record or upload at least one audio sample."
        }), 400


    # ----------------------------------------------
    # CHECK FILE TYPES
    # ----------------------------------------------

    files = [
        ("audio", uploaded),
        ("reference_audio", reference)
    ]

    for label, item in files:

        if item is None:
            continue

        if not item.filename:
            continue

        suffix = Path(item.filename).suffix.lower()

        if suffix not in ALLOWED:
            return jsonify({
                "error": "Unsupported audio format.",
                "supported": [
                    "WAV",
                    "MP3",
                    "M4A",
                    "FLAC",
                    "OGG"
                ]
            }), 400


    # ----------------------------------------------
    # READ CONTEXT
    # ----------------------------------------------

    context_text = request.form.get("context", "{}")

    try:
        context = json.loads(context_text)

    except json.JSONDecodeError:
        return jsonify({
            "error": "Context must be valid JSON."
        }), 400


    # ----------------------------------------------
    # TEMPORARY FILES
    # ----------------------------------------------

    temporary_files = {}

    try:

        for label, item in files:

            if item is None:
                continue

            if not item.filename:
                continue

            suffix = Path(item.filename).suffix.lower()

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix
            ) as temp_file:

                item.save(temp_file.name)

                temporary_files[label] = temp_file.name


        # ------------------------------------------
        # ANALYZE AUDIO
        # ------------------------------------------

        result = analyze_audio(
            temporary_files.get("audio"),
            context,
            temporary_files.get("reference_audio")
        )


        # Make sure result is a dictionary
        if not isinstance(result, dict):

            result = {
                "analysis": result
            }


        # ------------------------------------------
        # PRIVACY INFORMATION
        # ------------------------------------------

        result["privacy"] = {
            "raw_audio_retained": False,
            "feature_only_logging": True
        }


        # ------------------------------------------
        # DATABASE LOG
        # ------------------------------------------

        try:
            log_event(result)

        except Exception:
            # Database failure should not destroy
            # an otherwise successful analysis.
            app.logger.exception(
                "Could not log analysis event"
            )


        # ------------------------------------------
        # RETURN JSON
        # ------------------------------------------

        return jsonify(result), 200


    except Exception as exc:

        app.logger.exception(
            "Audio analysis failed"
        )

        return jsonify({
            "error": "Audio analysis failed.",
            "details": str(exc)
        }), 500


    finally:

        # ------------------------------------------
        # DELETE TEMPORARY AUDIO
        # ------------------------------------------

        for path in temporary_files.values():

            try:
                os.remove(path)

            except OSError:
                pass


# --------------------------------------------------
# API 404 HANDLER
# --------------------------------------------------
# IMPORTANT:
# Without this, Flask may return an HTML 404 page.
# Your frontend then tries response.json()
# and gets:
#
# Unexpected token '<'
#
# --------------------------------------------------

@app.errorhandler(404)
def page_not_found(error):

    if request.path.startswith("/api/"):

        return jsonify({
            "error": "API endpoint not found.",
            "path": request.path
        }), 404

    return send_from_directory(
        str(FRONTEND),
        "index.html"
    )


# --------------------------------------------------
# API 405 HANDLER
# --------------------------------------------------

@app.errorhandler(405)
def method_not_allowed(error):

    if request.path.startswith("/api/"):

        return jsonify({
            "error": "HTTP method not allowed.",
            "path": request.path,
            "method": request.method
        }), 405

    return jsonify({
        "error": "Method not allowed."
    }), 405


# --------------------------------------------------
# FILE TOO LARGE
# --------------------------------------------------

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "error": "Audio file is too large.",
        "maximum_size": "20 MB"
    }), 413


# --------------------------------------------------
# GENERAL API ERROR
# --------------------------------------------------

@app.errorhandler(500)
def internal_server_error(error):

    if request.path.startswith("/api/"):

        return jsonify({
            "error": "Internal server error."
        }), 500

    return jsonify({
        "error": "Internal server error."
    }), 500


# --------------------------------------------------
# RUN SERVER
# --------------------------------------------------

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
