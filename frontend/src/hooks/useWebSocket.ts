import { useEffect, useRef } from 'react'
import { useIncidentStore } from '../store/incidentStore'

const _base = import.meta.env.VITE_API_BASE_URL || window.location.origin
const WS_URL = _base.replace(/^http/, 'ws') + '/ws/incidents/'

export function useWebSocket() {
  const updateIncident = useIncidentStore((s) => s.updateIncident)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    let retryTimeout: ReturnType<typeof setTimeout>

    function connect() {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'incident.update') {
            updateIncident(data)
          }
        } catch {
          // ignore malformed messages
        }
      }

      ws.onclose = () => {
        retryTimeout = setTimeout(connect, 3000)
      }
    }

    connect()

    return () => {
      clearTimeout(retryTimeout)
      wsRef.current?.close()
    }
  }, [updateIncident])
}
