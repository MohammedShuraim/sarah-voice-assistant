// Thin wrapper around the Flask API. Every call resolves to a plain object and
// throws only for transport failures, so components handle one error shape.

const BASE = import.meta.env.VITE_API_BASE ?? ''

async function readJson(response) {
  const payload = await response.json().catch(() => ({}))
  if (!response.ok && !payload.message) {
    throw new Error(`Request failed with status ${response.status}`)
  }
  return payload
}

export async function getHealth() {
  const response = await fetch(`${BASE}/api/health`)
  return readJson(response)
}

export async function getCommands() {
  const response = await fetch(`${BASE}/api/commands`)
  return readJson(response)
}

export async function sendCommand(command) {
  const response = await fetch(`${BASE}/api/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command }),
  })
  return readJson(response)
}

export async function sendVoice(blob, filename = 'recording.webm') {
  const form = new FormData()
  form.append('audio', blob, filename)
  const response = await fetch(`${BASE}/api/voice`, { method: 'POST', body: form })
  return readJson(response)
}

export async function resetConversation() {
  const response = await fetch(`${BASE}/api/reset`, { method: 'POST' })
  return readJson(response)
}

// Returns an object URL for the synthesised MP3, or null if speech failed.
// Callers are responsible for revoking the URL once playback ends.
export async function fetchSpeech(text) {
  const response = await fetch(`${BASE}/api/speak`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  if (!response.ok) return null
  const blob = await response.blob()
  return URL.createObjectURL(blob)
}
