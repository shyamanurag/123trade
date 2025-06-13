import { useEffect, useRef } from 'react';

export default function useSocket(onMessage: (data: any) => void) {
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws');
    wsRef.current = ws;
    ws.onmessage = (evt) => onMessage(JSON.parse(evt.data));
    ws.onclose = () => setTimeout(() => useSocket(onMessage), 5000); // reconnect
    return () => ws.close();
  }, [onMessage]);
}
