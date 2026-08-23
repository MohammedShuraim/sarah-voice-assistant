export default function StatusBar({ health, error }) {
  const offline = health === null
  const misconfigured = health !== null && !health.groq_configured

  let tone = 'ok'
  let text = `Connected · ${health?.chat_model ?? ''}`

  if (offline) {
    tone = 'down'
    text = 'Backend offline — run "python server.py"'
  } else if (misconfigured) {
    tone = 'warn'
    text = 'GROQ_API_KEY missing — add it to your .env file'
  }

  return (
    <div className="status-bar">
      <span className={`status-dot is-${tone}`} aria-hidden="true" />
      <span className="status-text">{error || text}</span>
    </div>
  )
}
