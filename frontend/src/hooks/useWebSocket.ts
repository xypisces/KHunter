import { useEffect, useRef, useState, useCallback } from 'react'
import { io, Socket } from 'socket.io-client'

type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'reconnecting'

interface WebSocketOptions {
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Error) => void
}

export function useWebSocket(options: WebSocketOptions = {}) {
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const socketRef = useRef<Socket | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 3

  useEffect(() => {
    const socket = io({
      reconnection: true,
      reconnectionAttempts: maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 4000,
      timeout: 10000,
    })

    socketRef.current = socket

    socket.on('connect', () => {
      setStatus('connected')
      reconnectAttempts.current = 0
      options.onConnect?.()
    })

    socket.on('disconnect', () => {
      setStatus('disconnected')
      options.onDisconnect?.()
    })

    socket.on('connect_error', (error) => {
      setStatus('reconnecting')
      reconnectAttempts.current++
      options.onError?.(error)
    })

    socket.io.on('reconnect_failed', () => {
      setStatus('disconnected')
      console.warn('WebSocket 重连失败，降级为轮询模式')
    })

    return () => {
      socket.disconnect()
    }
  }, [])

  const on = useCallback(<T,>(event: string, handler: (data: T) => void) => {
    const socket = socketRef.current
    if (!socket) return

    socket.on(event, handler)
    return () => {
      socket.off(event, handler)
    }
  }, [])

  const off = useCallback((event: string, handler?: (...args: unknown[]) => void) => {
    const socket = socketRef.current
    if (!socket) return

    if (handler) {
      socket.off(event, handler)
    } else {
      socket.off(event)
    }
  }, [])

  return {
    status,
    on,
    off,
    socket: socketRef.current,
  }
}
