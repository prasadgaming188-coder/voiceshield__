# SIH26104 VoiceShield — Complete Hackathon Prototype

This is a demo-ready MVP for the SIH26104 problem statement:
AI-Powered Real-Time Detection and Prevention of Voice Cloning Impersonation Attacks.

## Included
- Browser microphone recording
- Audio upload
- Acoustic, spectral and prosodic feature extraction
- ML voice-integrity scoring
- Context-aware fraud risk scoring
- LOW / MEDIUM / HIGH risk
- Callback / MFA / escalation recommendations
- Privacy-by-design processing
- SQLite feature/result-only audit events
- REST API
- Hackathon dashboard

## IMPORTANT LIMITATION
The bundled model is a DEMO model trained on synthetic feature distributions so the application works immediately. It is NOT a validated real-world voice-cloning detector. Do not present its demo accuracy as real detection accuracy.

For production/research, train and evaluate on licensed real/synthetic speech datasets, with speaker-disjoint testing, calibration, multilingual/accent evaluation and proper security review.

## Run
From this folder:
    source venv/bin/activate
    pip install -r requirements.txt
    python scripts/train_demo_model.py
    python -m backend.app

Open http://127.0.0.1:5000

## API
GET  /api/health
GET  /api/events
POST /api/analyze
POST /api/analyze accepts multipart field "audio" and optional "context" JSON.

## Demo flow
1. Record 8-15 seconds or upload audio.
2. Enter caller/transaction context.
3. Analyze.
4. Demonstrate the multi-layer evidence and contextual risk.
5. Explain that high risk triggers secondary verification.
6. Explain that raw audio is deleted after processing and only derived results are logged.

## Architecture
Microphone/upload -> Flask API -> temporary audio processing -> MFCC/spectral/pitch features -> ML classifier -> contextual risk engine -> alert/recommendation -> feature/result-only event log.

## Production roadmap
- Real anti-spoofing datasets such as ASVspoof plus Indian-language/accent data
- Deep-learning anti-spoofing model
- Speaker-verification embeddings and cross-session consistency
- Streaming inference on short audio windows
- Edge/on-device inference
- Enterprise authentication, encrypted logs and model monitoring
- Approved telecom/VoIP media integration


## V2 speaker-consistency demo
This version accepts two samples: a microphone recording (`audio`) and a reference/second recording (`reference_audio`). It compares acoustic/prosodic/MFCC-derived features and reports a prototype speaker-similarity score. This is a demo consistency layer, not biometric speaker verification or proof that a clone is genuine.

For a same-speaker demonstration, record 8–15 seconds in a quiet place, choose another recording of the same speaker, and run analysis. If the overall score remains elevated, inspect the context fields: a high-value transaction and sensitive action intentionally add risk even when speaker consistency is high.
