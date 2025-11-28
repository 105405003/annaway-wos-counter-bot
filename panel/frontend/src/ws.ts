/**
 * WebSocket 客戶端
 */

import { Timer } from './api';

type MessageHandler = (timers: Timer[]) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: MessageHandler[] = [];
  private reconnectTimer: number | null = null;
  private reconnectDelay = 1000;

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    console.log('正在連接 WebSocket:', wsUrl);

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket 已連接');
        this.reconnectDelay = 1000;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'state_update' && data.timers) {
            this.handlers.forEach(handler => handler(data.timers));
          }
        } catch (error) {
          console.error('解析 WebSocket 消息失敗:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket 錯誤:', error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket 已斷開，嘗試重新連接...');
        this.scheduleReconnect();
      };
    } catch (error) {
      console.error('WebSocket 連接失敗:', error);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) {
      return;
    }

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
      this.connect();
    }, this.reconnectDelay);
  }

  onMessage(handler: MessageHandler) {
    this.handlers.push(handler);
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const wsClient = new WebSocketClient();

