import { useCallback, useEffect, useRef, useState } from 'react'

// Groq infers the audio container from the uploaded filename, so each candidate
// MIME type is paired with the extension it must be saved under.
const CANDIDATES = [
  { mimeType: 'audio/webm;codecs=opus', extension: 'webm' },
  { mimeType: 'audio/webm', extension: 'webm' },
  { mimeType: 'audio/ogg;codecs=opus', extension: 'ogg' },
  { mimeType: 'audio/mp4', extension: 'm4a' },
]

function pickFormat() {
  if (typeof MediaRecorder === 'undefined') return null
  return CANDIDATES.find((candidate) => MediaRecorder.isTypeSupported(candidate.mimeType)) ?? null
}

const MAX_SECONDS = 20

/**
 * Push-to-talk recording with a live input level for the mic visualiser.
 *
 * `onComplete` receives the finished blob and the filename to upload it as.
 * Recording stops itself after MAX_SECONDS so a forgotten session cannot run on
 * indefinitely.
 */
export function useRecorder(onComplete) {
  const [isRecording, setIsRecording] = useState(false)
  const [level, setLevel] = useState(0)
  const [error, setError] = useState('')

  const recorderRef = useRef(null)
  const streamRef = useRef(null)
  const audioContextRef = useRef(null)
  const frameRef = useRef(null)
  const timeoutRef = useRef(null)
  const chunksRef = useRef([])
  const onCompleteRef = useRef(onComplete)

  useEffect(() => {
    onCompleteRef.current = onComplete
  }, [onComplete])

  const teardown = useCallback(() => {
    if (frameRef.current) cancelAnimationFrame(frameRef.current)
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    frameRef.current = null
    timeoutRef.current = null

    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null

    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => {})
    }
    audioContextRef.current = null
    recorderRef.current = null
    setLevel(0)
  }, [])

  useEffect(() => teardown, [teardown])

  const stop = useCallback(() => {
    const recorder = recorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
    }
    setIsRecording(false)
  }, [])

  const start = useCallback(async () => {
    setError('')

    if (!navigator.mediaDevices?.getUserMedia) {
      setError('This browser cannot access the microphone.')
      return
    }

    const format = pickFormat()
    if (!format) {
      setError('This browser cannot record audio in a supported format.')
      return
    }

    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      })
    } catch {
      setError('Microphone access was denied. Allow it in your browser settings.')
      return
    }

    streamRef.current = stream
    chunksRef.current = []

    // Drive the visualiser from the raw stream rather than the encoded output.
    const AudioContextClass = window.AudioContext ?? window.webkitAudioContext
    if (AudioContextClass) {
      const context = new AudioContextClass()
      const analyser = context.createAnalyser()
      analyser.fftSize = 512
      context.createMediaStreamSource(stream).connect(analyser)
      audioContextRef.current = context

      const samples = new Uint8Array(analyser.frequencyBinCount)
      const tick = () => {
        analyser.getByteTimeDomainData(samples)
        let sum = 0
        for (const sample of samples) {
          const centred = (sample - 128) / 128
          sum += centred * centred
        }
        setLevel(Math.min(1, Math.sqrt(sum / samples.length) * 3))
        frameRef.current = requestAnimationFrame(tick)
      }
      tick()
    }

    const recorder = new MediaRecorder(stream, { mimeType: format.mimeType })
    recorderRef.current = recorder

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data)
    }

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: format.mimeType })
      teardown()
      setIsRecording(false)
      if (blob.size > 0) {
        onCompleteRef.current?.(blob, `recording.${format.extension}`)
      }
    }

    recorder.start()
    setIsRecording(true)
    timeoutRef.current = setTimeout(stop, MAX_SECONDS * 1000)
  }, [stop, teardown])

  const toggle = useCallback(() => {
    if (isRecording) stop()
    else start()
  }, [isRecording, start, stop])

  return { isRecording, level, error, start, stop, toggle }
}
