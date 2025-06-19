import { User } from '../types';
import { apiClient } from './apiClient';

export interface LoginResponse {
  user: User;
  token: string;
}

class AuthService {
  async login(email: string, password: string): Promise<LoginResponse> {
    try {
      const response = await apiClient.post<LoginResponse>('/auth/login', {
        email,
        password,
      });
      return response.data;
    } catch (error) {
      // Simulate login for demo purposes
      if (email === 'demo@example.com' && password === 'demo123') {
        return {
          user: {
            id: '1',
            email: 'demo@example.com',
            name: 'Demo User',
            role: 'admin',
            avatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=32&h=32&fit=crop&crop=face',
          },
          token: 'demo-jwt-token-' + Date.now(),
        };
      }
      throw new Error('Invalid credentials');
    }
  }

  async register(email: string, password: string, name: string): Promise<LoginResponse> {
    try {
      const response = await apiClient.post<LoginResponse>('/auth/register', {
        email,
        password,
        name,
      });
      return response.data;
    } catch (error) {
      // Simulate registration for demo purposes
      return {
        user: {
          id: Date.now().toString(),
          email,
          name,
          role: 'user',
        },
        token: 'demo-jwt-token-' + Date.now(),
      };
    }
  }

  async verifyToken(token: string): Promise<User | null> {
    try {
      const response = await apiClient.get<{ user: User }>('/auth/verify', {
        headers: { Authorization: `Bearer ${token}` },
      });
      return response.data.user;
    } catch (error) {
      // Simulate token verification for demo purposes
      if (token.startsWith('demo-jwt-token-')) {
        return {
          id: '1',
          email: 'demo@example.com',
          name: 'Demo User',
          role: 'admin',
          avatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=32&h=32&fit=crop&crop=face',
        };
      }
      return null;
    }
  }

  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout');
    } catch (error) {
      // Ignore logout errors for demo
    }
  }
}

export const authService = new AuthService();