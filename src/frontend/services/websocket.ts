export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

export interface WebSocketCallbacks {
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
  onBatchMessage?: (messages: WebSocketMessage[]) => void;
}

interface WebSocketConfig {
  url: string;
  reconnectAttempts: number;
  reconnectDelay: number;
  heartbeatInterval: number;
  batchSize: number;
  batchInterval: number;
}

class WebSocketService extends EventTarget {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private heartbeatInterval = 30000;
  private batchSize = 50;
  private batchInterval = 100;
  private messageQueue: WebSocketMessage[] = [];
  private batchTimer: ReturnType<typeof setInterval> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private url: string;
  private isConnecting = false;

  constructor(config?: Partial<WebSocketConfig>) {
    super();
    this.url = config?.url || import.meta.env.VITE_WS_URL || 'wss://algoauto-ua2iq.ondigitalocean.app/ws';
    this.maxReconnectAttempts = config?.reconnectAttempts || 5;
    this.reconnectDelay = config?.reconnectDelay || 1000;
    this.heartbeatInterval = config?.heartbeatInterval || 30000;
    this.batchSize = config?.batchSize || 50;
    this.batchInterval = config?.batchInterval || 100;
  }

  connect(callbacks?: WebSocketCallbacks): void {
    if (this.isConnecting) return;
    this.isConnecting = true;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.startHeartbeat();
        this.startBatchTimer();
        callbacks?.onConnect?.();
        this.dispatchEvent(new Event('connect'));
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.isConnecting = false;
        this.stopHeartbeat();
        this.stopBatchTimer();
        callbacks?.onDisconnect?.();
        this.dispatchEvent(new Event('disconnect'));
        this.handleReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.isConnecting = false;
        callbacks?.onError?.(error);
        this.dispatchEvent(new Event('error'));
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          // Handle batch messages
          if (message.type === 'batch' && Array.isArray(message.messages)) {
            callbacks?.onBatchMessage?.(message.messages);
            message.messages.forEach(msg => {
              this.dispatchEvent(new CustomEvent(`message:${msg.type}`, { detail: msg }));
            });
          } else {
            callbacks?.onMessage?.(message);
            this.dispatchEvent(new CustomEvent('message', { detail: message }));
            this.dispatchEvent(new CustomEvent(`message:${message.type}`, { detail: message }));
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
    } catch (error) {
      console.error('Error connecting to WebSocket:', error);
      this.isConnecting = false;
      this.handleReconnect();
    }
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
      setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('Max reconnection attempts reached');
      this.dispatchEvent(new Event('reconnect_failed'));
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected()) {
        this.send({ type: 'heartbeat', data: null, timestamp: new Date().toISOString() });
      }
    }, this.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private startBatchTimer(): void {
    this.stopBatchTimer();
    this.batchTimer = setInterval(() => {
      this.flushMessageQueue();
    }, this.batchInterval);
  }

  private stopBatchTimer(): void {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
      this.batchTimer = null;
    }
  }

  private flushMessageQueue(): void {
    if (this.messageQueue.length > 0 && this.isConnected()) {
      const messages = this.messageQueue.splice(0, this.batchSize);
      this.ws?.send(JSON.stringify({
        type: 'batch',
        messages,
        timestamp: new Date().toISOString()
      }));
    }
  }

  disconnect(): void {
    this.stopHeartbeat();
    this.stopBatchTimer();
    this.flushMessageQueue();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(message: WebSocketMessage): void {
    if (!this.isConnected()) {
      console.error('WebSocket is not connected');
      return;
    }

    // Add to message queue for batching
    this.messageQueue.push(message);

    // Send immediately if queue is full
    if (this.messageQueue.length >= this.batchSize) {
      this.flushMessageQueue();
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  getReconnectAttempts(): number {
    return this.reconnectAttempts;
  }

  getMessageQueueSize(): number {
    return this.messageQueue.length;
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();

// Export hook for React components
export const useWebSocket = () => {
  return websocketService;
}; 