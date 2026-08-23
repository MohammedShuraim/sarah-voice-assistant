"""HTTP API that backs the Sarah web interface.

Endpoints
    GET  /api/health    availability and configuration status
    GET  /api/commands  the built-in command phrases
    POST /api/command   send typed text, get Sarah's reply
    POST /api/voice     upload recorded audio, get transcript and reply
    POST /api/speak     synthesise a reply to MP3 for the browser to play
    POST /api/reset     clear the conversation history

The conversation lives in module state, so this server is intended for a single
local user rather than concurrent visitors.
"""

from __future__ import annotations

import os

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

from sarah import assistant as assistant_module
from sarah import commands, config, stt, tts

app = Flask(__name__)
CORS(app, origins=os.getenv("CORS_ORIGINS", "*").split(","))

# The browser drives its own push-to-talk button, so the wake word only makes
# sense for the microphone loop in the CLI.
sarah = assistant_module.Assistant(require_wake_word=False)

MAX_AUDIO_BYTES = int(os.getenv("MAX_AUDIO_BYTES", str(25 * 1024 * 1024)))
app.config["MAX_CONTENT_LENGTH"] = MAX_AUDIO_BYTES


def _reply_payload(reply: assistant_module.Reply) -> dict:
    return {
        "status": "error" if reply.source == "error" else "ok",
        "transcript": reply.transcript,
        "message": reply.text,
        "source": reply.source,
        "speak": reply.should_speak,
    }


@app.get("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "groq_configured": bool(config.GROQ_API_KEY),
            "weather_configured": bool(config.WEATHER_API_KEY),
            "news_configured": bool(config.NEWS_API_KEY),
            "chat_model": config.CHAT_MODEL,
            "transcribe_model": config.TRANSCRIBE_MODEL,
        }
    )


@app.get("/api/commands")
def list_commands():
    return jsonify({"status": "ok", "commands": commands.available_commands()})


@app.post("/api/command")
def handle_command():
    data = request.get_json(silent=True) or {}
    user_input = str(data.get("command", "")).strip()

    if not user_input:
        return jsonify({"status": "error", "message": "No command provided."}), 400

    return jsonify(_reply_payload(sarah.handle(user_input, wake_word_required=False)))


@app.post("/api/voice")
def handle_voice():
    upload = request.files.get("audio")
    if upload is None:
        return jsonify({"status": "error", "message": "No audio uploaded."}), 400

    payload = upload.read()
    if not payload:
        return jsonify({"status": "error", "message": "The recording was empty."}), 400

    try:
        transcript = stt.transcribe_bytes(payload, upload.filename or "recording.webm")
    except stt.TranscriptionError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 502

    if not transcript:
        return jsonify(
            {
                "status": "ok",
                "transcript": "",
                "message": "I could not make that out. Try again?",
                "source": "error",
                "speak": False,
            }
        )

    return jsonify(_reply_payload(sarah.handle(transcript, wake_word_required=False)))


@app.post("/api/speak")
def speak():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify({"status": "error", "message": "No text provided."}), 400

    try:
        buffer = tts.synthesize_to_bytes(text)
    except tts.SpeechError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 502

    return send_file(buffer, mimetype="audio/mpeg", download_name="reply.mp3")


@app.post("/api/reset")
def reset():
    sarah.reset()
    return jsonify({"status": "ok", "message": "Conversation cleared."})


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"status": "error", "message": "That recording is too large."}), 413


def main() -> None:
    if not config.GROQ_API_KEY:
        print("Warning: GROQ_API_KEY is not set. Requests will fail until you add it to .env.")

    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in {"1", "true", "yes"}
    print(f"Sarah API listening on http://127.0.0.1:{port}")
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=port, debug=debug)


if __name__ == "__main__":
    main()
