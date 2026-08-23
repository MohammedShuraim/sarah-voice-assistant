import { useCallback, useEffect, useRef, useState } from 'react'

import CommandPalette from './components/CommandPalette'
import MessageList from './components/MessageList'
import MicButton from './components/MicButton'
import StatusBar from './components/StatusBar'
import { useRecorder } from './hooks/useRecorder'
import {
  fetchSpeech,
  getCommands,
  getHealth,
  resetConversation,
  sendCommand,
  sendVoice,
} from './api'

let messageId = 0
const nextId = () => {
  messageId += 1
  return messageId
}

export default function App() {
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [health, setHealth] = useState(null)
  const [commands, setCommands] = useState([])
  const [error, setError] = useState('')
  const [autoSpeak, setAutoSpeak] = useState(true)

  const audioRef = useRef(null)

  const append = useCallback((role, text, source) => {
    setMessages((current) => [...current, { id: nextId(), role, text, source }])
  }, [])

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(null))
    getCommands()
      .then((payload) => setCommands(payload.commands ?? []))
      .catch(() => setCommands([]))
  }, [])

  const play = useCallback(async (text) => {
    const url = await fetchSpeech(text).catch(() => null)
    if (!url) return

    // Only one reply plays at a time; a new one interrupts the last.
    audioRef.current?.pause()
    const audio = new Audio(url)
    audioRef.current = audio
    audio.addEventListener('ended', () => URL.revokeObjectURL(url), { once: true })
    audio.play().catch(() => URL.revokeObjectURL(url))
  }, [])

  const present = useCallback(
    (payload) => {
      const reply = payload.message || 'Something went wrong.'
      append('sarah', reply, payload.source ?? 'error')
      if (autoSpeak && payload.speak) play(reply)
    },
    [append, autoSpeak, play],
  )

  const submitText = useCallback(
    async (text) => {
      const trimmed = text.trim()
      if (!trimmed || busy) return

      append('user', trimmed, 'typed')
      setDraft('')
      setBusy(true)
      setError('')
      try {
        present(await sendCommand(trimmed))
      } catch {
        setError('Could not reach the backend. Is server.py running?')
      } finally {
        setBusy(false)
      }
    },
    [append, busy, present],
  )

  const submitVoice = useCallback(
    async (blob, filename) => {
      setBusy(true)
      setError('')
      try {
        const payload = await sendVoice(blob, filename)
        if (payload.transcript) append('user', payload.transcript, 'voice')
        present(payload)
      } catch {
        setError('Could not reach the backend. Is server.py running?')
      } finally {
        setBusy(false)
      }
    },
    [append, present],
  )

  const recorder = useRecorder(submitVoice)

  const clear = useCallback(async () => {
    audioRef.current?.pause()
    setMessages([])
    setError('')
    await resetConversation().catch(() => {})
  }, [])

  return (
    <div className="app">
      <div className="aurora" aria-hidden="true">
        <span className="blob blob-a" />
        <span className="blob blob-b" />
        <span className="blob blob-c" />
      </div>

      <header className="header">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            S
          </span>
          <div>
            <h1>Sarah</h1>
            <p>Voice assistant · Whisper + GPT-OSS on Groq</p>
          </div>
        </div>

        <div className="header-actions">
          <label className="toggle">
            <input
              type="checkbox"
              checked={autoSpeak}
              onChange={(event) => setAutoSpeak(event.target.checked)}
            />
            <span>Speak replies</span>
          </label>
          <button
            type="button"
            className="ghost-button"
            onClick={clear}
            disabled={messages.length === 0 && !busy}
          >
            Clear chat
          </button>
        </div>
      </header>

      <main className="stage">
        <section className="chat-card">
          <MessageList messages={messages} busy={busy} chatModel={health?.chat_model} />

          <div className="composer">
            <MicButton
              isRecording={recorder.isRecording}
              level={recorder.level}
              disabled={busy}
              onClick={recorder.toggle}
            />

            <form
              className="composer-form"
              onSubmit={(event) => {
                event.preventDefault()
                submitText(draft)
              }}
            >
              <input
                type="text"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder={
                  recorder.isRecording ? 'Listening — tap the square to stop' : 'Type a message…'
                }
                disabled={busy || recorder.isRecording}
                aria-label="Message"
              />
              <button type="submit" className="send-button" disabled={busy || !draft.trim()}>
                Send
              </button>
            </form>
          </div>

          <StatusBar health={health} error={error || recorder.error} />
        </section>

        <CommandPalette commands={commands} onPick={submitText} disabled={busy} />
      </main>
    </div>
  )
}
