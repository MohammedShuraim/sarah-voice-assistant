import { useEffect, useRef } from 'react'

const SOURCE_LABELS = {
  command: 'system command',
  chat: 'llama 3.3',
  wake: 'wake word',
  error: 'error',
}

function Bubble({ message }) {
  const isUser = message.role === 'user'
  const label = SOURCE_LABELS[message.source]

  return (
    <li className={`bubble-row ${isUser ? 'from-user' : 'from-sarah'}`}>
      <div className={`bubble ${message.source === 'error' ? 'is-error' : ''}`}>
        <p>{message.text}</p>
        {!isUser && label && <span className="bubble-tag">{label}</span>}
      </div>
    </li>
  )
}

export default function MessageList({ messages, busy }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, busy])

  if (messages.length === 0 && !busy) {
    return (
      <div className="empty-state">
        <div className="empty-orb" aria-hidden="true" />
        <h2>Hi, I&apos;m Sarah</h2>
        <p>
          Tap the microphone and speak, or type below. I can open apps and folders,
          search the web, check the time, or just talk.
        </p>
      </div>
    )
  }

  return (
    <ul className="messages">
      {messages.map((message) => (
        <Bubble key={message.id} message={message} />
      ))}
      {busy && (
        <li className="bubble-row from-sarah">
          <div className="bubble is-typing" aria-label="Sarah is thinking">
            <span />
            <span />
            <span />
          </div>
        </li>
      )}
      <li ref={endRef} aria-hidden="true" />
    </ul>
  )
}
