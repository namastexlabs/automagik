import { io, Socket } from 'socket.io-client';
import { WebSocketMessage } from '../types';

class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 3000;
  private listeners: Map<string, Function[]> = new Map();

  connect(url?: string): void {
    if (this.socket?.connected) {
      return;
    }

    const wsUrl = url || process.env.REACT_APP_WS_URL || 'ws://localhost:3001';
    
    // For demo purposes, we'll simulate WebSocket connection
    this.simulateConnection();
  }

  private simulateConnection(): void {
    // Simulate real-time data updates
    const simulateData = () => {
      const metrics = {
        type: 'metrics_update',
        payload: {
          activeUsers: Math.floor(Math.random() * 1000) + 500,
          revenue: Math.floor(Math.random() * 10000) + 50000,
          orders: Math.floor(Math.random() * 100) + 200,
        },
        timestamp: Date.now(),
      };

      this.emit('metrics_update', metrics);
      
      // Random notifications
      if (Math.random() > 0.8) {
        const notification = {
          type: 'notification',
          payload: {
            id: Date.now().toString(),
            title: 'New Order',
            message: `Order #${Math.floor(Math.random() * 10000)} received`,
            type: 'info',
          },
          timestamp: Date.now(),
        };
        this.emit('notification', notification);
      }
    };

    // Emit updates every 3 seconds
    setInterval(simulateData, 3000);
    
    // Initial data
    setTimeout(simulateData, 1000);
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  on(event: string, callback: (data: WebSocketMessage) => void): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)!.push(callback);

    if (this.socket) {
      this.socket.on(event, callback);
    }
  }

  off(event: string, callback?: Function): void {
    if (callback) {
      const eventListeners = this.listeners.get(event);
      if (eventListeners) {
        const index = eventListeners.indexOf(callback);
        if (index > -1) {
          eventListeners.splice(index, 1);
        }
      }
    } else {
      this.listeners.delete(event);
    }

    if (this.socket) {
      if (callback) {
        this.socket.off(event, callback);
      } else {
        this.socket.off(event);
      }
    }
  }

  emit(event: string, data: any): void {
    // For simulation, emit to local listeners
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.forEach(callback => callback(data));
    }

    if (this.socket) {
      this.socket.emit(event, data);
    }
  }

  send(message: WebSocketMessage): void {
    this.emit('message', message);
  }

  isConnected(): boolean {
    return this.socket?.connected || true; // Always true for simulation
  }
}

export const websocketService = new WebSocketService();