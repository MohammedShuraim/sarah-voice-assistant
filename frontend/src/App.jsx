import { useEffect, useState } from 'react'

export default function App() {
  const [online, setOnline] = useState(null)

  useEffect(() => {
    fetch('/api/health')
      .then((response) => response.json())
      .then((data) => setOnline(data.status === 'ok'))
      .catch(() => setOnline(false))
  }, [])

  return (
    <div className="app">
      <header>
        <h1>Sarah</h1>
        <p>Voice assistant</p>
      </header>
      <main>
        <p>
          {online === null && 'Checking the backend...'}
          {online === true && 'Backend connected.'}
          {online === false && 'Backend unreachable. Start server.py first.'}
        </p>
      </main>
    </div>
  )
}
