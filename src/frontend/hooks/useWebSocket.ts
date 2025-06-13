import { useEffect, useCallback } from 'react';
import { websocketService, WebSocketMessage, WebSocketCallbacks } from '../services/websocket';

export const useWebSocket = (callbacks?: WebSocketCallbacks) => {
  useEffect(() => {
    websocketService.connect(callbacks);
    return () => {
      websocketService.disconnect();
    };
  }, [callbacks]);

  const send = useCallback((message: WebSocketMessage) => {
    websocketService.send(message);
  }, []);

  const subscribe = useCallback((event: string, callback: (data: any) => void) => {
    websocketService.subscribe(event, callback);
    return () => websocketService.unsubscribe(event, callback);
  }, []);

  const isConnected = useCallback(() => {
    return websocketService.isConnected();
  }, []);

  return {
    send,
    subscribe,
    isConnected
  };
}; 