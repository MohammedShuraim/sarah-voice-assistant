export default function MicButton({ isRecording, level, disabled, onClick }) {
  // The ring scales with live input level so the button visibly reacts to speech.
  const ringScale = 1 + level * 0.6

  return (
    <div className="mic-wrap">
      <span
        className="mic-ring"
        style={{ transform: `scale(${ringScale})`, opacity: isRecording ? 0.35 + level * 0.5 : 0 }}
        aria-hidden="true"
      />
      <button
        type="button"
        className={`mic-button ${isRecording ? 'is-recording' : ''}`}
        onClick={onClick}
        disabled={disabled}
        aria-pressed={isRecording}
        aria-label={isRecording ? 'Stop recording' : 'Start recording'}
      >
        {isRecording ? (
          <svg viewBox="0 0 24 24" width="30" height="30" aria-hidden="true">
            <rect x="6" y="6" width="12" height="12" rx="2.5" fill="currentColor" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" width="30" height="30" aria-hidden="true">
            <path
              fill="currentColor"
              d="M12 15a3.5 3.5 0 0 0 3.5-3.5V6a3.5 3.5 0 1 0-7 0v5.5A3.5 3.5 0 0 0 12 15Z"
            />
            <path
              fill="currentColor"
              d="M18 11.5a1 1 0 1 0-2 0 4 4 0 0 1-8 0 1 1 0 1 0-2 0 6 6 0 0 0 5 5.91V20H9a1 1 0 1 0 0 2h6a1 1 0 1 0 0-2h-2v-2.59a6 6 0 0 0 5-5.91Z"
            />
          </svg>
        )}
      </button>
    </div>
  )
}
