/**
 * API Client
 */

const BASE_URL = '/wos/counter-bot/1458/api';

export interface Timer {
  id: string;
  name: string;
  remaining_seconds: number;
  total_seconds: number;
  status: 'active' | 'completed' | 'deleted';
  discord_message_id?: string;
}

export interface TimerCreate {
  name: string;
  minutes: number;
  seconds: number;
}

export class ApiClient {
  async getTimers(): Promise<Timer[]> {
    const response = await fetch(`${BASE_URL}/timers`);
    if (!response.ok) {
      throw new Error('Failed to fetch timers');
    }
    return response.json();
  }

  async createTimer(data: TimerCreate): Promise<Timer> {
    const response = await fetch(`${BASE_URL}/timers`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create timer');
    }

    return response.json();
  }

  async adjustTimer(id: string, adjustSeconds: number): Promise<void> {
    const response = await fetch(`${BASE_URL}/timers/${id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ adjust_seconds: adjustSeconds }),
    });

    if (!response.ok) {
      throw new Error('Failed to adjust timer');
    }
  }

  async restartTimer(id: string): Promise<void> {
    const response = await fetch(`${BASE_URL}/timers/${id}/restart`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error('Failed to restart timer');
    }
  }

  async deleteTimer(id: string): Promise<void> {
    const response = await fetch(`${BASE_URL}/timers/${id}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error('Failed to delete timer');
    }
  }
}

export const api = new ApiClient();
