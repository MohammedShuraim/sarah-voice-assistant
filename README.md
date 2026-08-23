# Sarah — Virtual Desktop Assistant

A hands-free desktop assistant. Speak to it and it will open your apps and
folders, search the web, tell you the time or the weather — and when you ask
something it has no command for, it just answers you conversationally.

Speech recognition and language understanding both run on [Groq](https://groq.com):
`whisper-large-v3-turbo` for transcription and `openai/gpt-oss-120b` for
conversation. Replies are spoken back through Google Text-to-Speech.

There are two ways to use it — a terminal voice loop, and a browser interface
with push-to-talk.

## Features

- **Wake word** — Sarah stays quiet until she hears "hey Sarah", so she is not
  reacting to every sound in the room.
- **Automatic recording length** — recording ends when you stop talking, instead
  of cutting you off at a fixed number of seconds.
- **34 built-in commands** — launch applications, open your user folders, search
  Google or YouTube, open a file by name, check the time, date, weather, or news.
- **Conversation fallback** — anything that is not a command goes to GPT-OSS 120B
  with a rolling memory of the last several turns.
- **Two front ends** — the CLI for everyday use, and a React web app that talks
  to a Flask API.
- **Typed mode** — `--text` skips the microphone entirely, which is handy on a
  machine with no working audio input.

## Requirements

- Python 3.10 or newer (tested through 3.13)
- Node.js 20.19+ or 22.12+, only if you want the web interface
- A working microphone and speakers
- A free Groq API key from [console.groq.com/keys](https://console.groq.com/keys)

## Setup

```bash
git clone <your-repo-url>
cd "Sarah Voice Assistant"
```

A virtual environment is recommended so these packages stay out of your global
Python install:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Then create your `.env` from the template and add your Groq key:

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

```ini
GROQ_API_KEY=gsk_your_key_here
```

`.env` is git-ignored. Nothing else is required — weather and news simply stay
switched off until you add their optional keys.

## Running the voice assistant

```bash
python -m sarah
```

Say "hey Sarah, what time is it", pause, and she will answer. Press `Ctrl+C` to
quit.

Useful flags:

| Flag | What it does |
| --- | --- |
| `--no-wake-word` | Reply to everything, no "hey Sarah" needed |
| `--text` | Type instead of speaking, no microphone required |
| `--list-commands` | Print every built-in command and exit |
| `--check-models` | Verify your configured Groq models are still served |

## Running the web interface

The web app needs both halves running. In one terminal:

```bash
python server.py
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Click the microphone, speak, then click again to
send. Vite proxies `/api` to Flask on port 5000, so there is no CORS setup to do
in development.

Your browser will ask for microphone permission, and will only grant it on
`localhost` or over HTTPS.

## Commands

Anything not listed here becomes a normal conversation.

| Say | What happens |
| --- | --- |
| "open chrome", "open notepad", "open spotify" | Launches the application |
| "open downloads", "open documents", "open pictures" | Opens that folder |
| "search for <anything>" | Google search in your browser |
| "play <song>" | YouTube search |
| "open file <name>" | Finds and opens a file in your user folders |
| "what time is it", "what's the date" | Spoken answer |
| "weather in <city>" | Current conditions (needs `WEATHER_API_KEY`) |
| "tell me the news" | Top headlines (needs `NEWS_API_KEY`) |

Application launching is Windows-only; folder and browser commands work
everywhere. Run `python -m sarah --list-commands` for the full list.

## Configuration

Every setting has a sensible default. The ones worth knowing about:

| Variable | Default | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | — | Required |
| `WAKE_WORD` | `hey sarah` | Phrase that activates Sarah |
| `REQUIRE_WAKE_WORD` | `true` | Set `false` to always listen |
| `SILENCE_THRESHOLD` | `0.015` | Raise it in a noisy room; lower it if recordings cut off while you are still talking |
| `SILENCE_SECONDS` | `1.2` | Quiet time that ends a recording |
| `CHAT_MODEL` | `openai/gpt-oss-120b` | Any Groq chat model |
| `REASONING_EFFORT` | `low` | `low`, `medium`, or `high`, for GPT-OSS models |
| `MAX_COMPLETION_TOKENS` | `1024` | Shared by reasoning and the reply |
| `WEATHER_API_KEY` | — | Optional, [openweathermap.org](https://openweathermap.org/api) |
| `NEWS_API_KEY` | — | Optional, [newsapi.org](https://newsapi.org) |

See `.env.example` for the complete list.

## A note on models

Groq retires models on a rolling schedule — `llama-3.3-70b-versatile`, which this
project originally used, was shut down on August 16, 2026. Both model IDs are
therefore environment variables rather than constants, so swapping one is a
`.env` edit and not a code change.

To check whether your configured models are still being served:

```bash
python -m sarah --check-models
```

That lists everything Groq is currently serving and tells you if either of your
configured IDs has disappeared. Groq's
[deprecation page](https://console.groq.com/docs/deprecations) is the
authoritative schedule.

GPT-OSS is a reasoning model: it thinks before it answers, and those reasoning
tokens are drawn from the same `MAX_COMPLETION_TOKENS` budget as the reply. If
answers start coming back empty, that budget is the first thing to raise. Sarah
requests `reasoning_effort=low` because a spoken assistant needs to be quick, and
discards the reasoning text, which is never read aloud.

## Project layout

```
sarah/              Python package — one module per responsibility
  config.py         Environment loading and validation
  audio.py          Microphone capture with silence detection, MP3 playback
  stt.py            Groq Whisper transcription
  tts.py            gTTS speech synthesis
  ai.py             Groq chat client with bounded history
  commands.py       Command recognition and execution
  services.py       Weather and news lookups
  assistant.py      Wake word, routing, conversational fallback
  cli.py            Terminal voice loop
server.py           Flask API for the web interface
frontend/           React + Vite web interface
tests/              pytest suite
```

The `Assistant` class holds no audio or HTTP concerns, which is why the same
logic serves both the microphone loop and the typed web interface.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Availability and which keys are configured |
| `GET` | `/api/commands` | The built-in command phrases |
| `POST` | `/api/command` | `{"command": "..."}` — send text, get a reply |
| `POST` | `/api/voice` | Multipart `audio` file — transcribe and reply |
| `POST` | `/api/speak` | `{"text": "..."}` — returns an MP3 |
| `POST` | `/api/reset` | Clear the conversation history |

The conversation lives in server memory, so this is built for one local user
rather than concurrent visitors.

## Development

```bash
pip install -r requirements-dev.txt
pytest          # 27 tests, no network access required
ruff check .
ruff format .
```

The suite patches out anything that would launch an application or open a
browser, so it is safe to run on your desktop.

## Troubleshooting

**"Could not open the microphone"** — another application may be holding the
input device. Close it, or use `python -m sarah --text`.

**Recording ends before you finish talking** — lower `SILENCE_THRESHOLD` in
`.env`, or raise `SILENCE_SECONDS` to allow longer pauses.

**Sarah never responds** — she is waiting for the wake word. Say "hey Sarah"
first, or start her with `--no-wake-word`.

**`ModuleNotFoundError: No module named 'sarah'`** — run the command from the
project root, not from inside a subfolder.

**Playback errors mentioning `audioop`** — you are on an old version of this
project that used `pydub` or `playsound`. Both break on Python 3.13, because the
`audioop` module they depend on was removed from the standard library in that
release. This version uses `pygame` instead; reinstall from
`requirements.txt`.

**Groq returns 429** — the free tier is rate limited. Wait a moment and retry.

## Security

Never commit your `.env`. If a key does end up in a commit, rotate it in the
provider's console rather than only deleting the file, since it stays readable in
the repository history.

## License

MIT — see [LICENSE](LICENSE).
