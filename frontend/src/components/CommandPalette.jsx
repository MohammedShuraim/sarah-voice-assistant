export default function CommandPalette({ commands, onPick, disabled }) {
  if (commands.length === 0) return null

  return (
    <aside className="palette">
      <h3>Try saying</h3>
      <p className="palette-hint">
        Anything not on this list becomes a normal conversation.
      </p>
      <div className="chips">
        {commands.map((command) => (
          <button
            key={command}
            type="button"
            className="chip"
            onClick={() => onPick(command)}
            disabled={disabled}
          >
            {command}
          </button>
        ))}
      </div>
    </aside>
  )
}
