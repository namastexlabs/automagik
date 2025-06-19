import { DashboardMetrics, ChartData } from '../types';
import { apiClient } from './apiClient';

class DashboardService {
  async getMetrics(): Promise<DashboardMetrics> {
    try {
      const response = await apiClient.get<DashboardMetrics>('/dashboard/metrics');
      return response.data;
    } catch (error) {
      // Simulate API response for demo
      return {
        totalUsers: Math.floor(Math.random() * 10000) + 15000,
        activeUsers: Math.floor(Math.random() * 1000) + 500,
        revenue: Math.floor(Math.random() * 100000) + 250000,
        orders: Math.floor(Math.random() * 500) + 1200,
        growthRate: Math.floor(Math.random() * 20) + 5,
      };
    }
  }

  async getChartData(type: 'revenue' | 'users' | 'orders'): Promise<ChartData[]> {
    try {
      const response = await apiClient.get<ChartData[]>(`/dashboard/charts/${type}`);
      return response.data;
    } catch (error) {
      // Simulate chart data for demo
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
      return months.map((month, index) => ({
        name: month,
        value: Math.floor(Math.random() * 1000) + 500 + (index * 100),
        date: `2024-${(index + 1).toString().padStart(2, '0')}-01`,
      }));
    }
  }

  async getRecentActivity(): Promise<any[]> {
    try {
      const response = await apiClient.get<any[]>('/dashboard/activity');
      return response.data;
    } catch (error) {
      // Simulate recent activity for demo
      return [
        {
          id: '1',
          type: 'order',
          message: 'New order #12345 received',
          timestamp: Date.now() - 300000,
          user: 'John Doe',
        },
        {
          id: '2',
          type: 'user',
          message: 'New user registered',
          timestamp: Date.now() - 600000,
          user: 'Jane Smith',
        },
        {
          id: '3',
          type: 'payment',
          message: 'Payment processed successfully',
          timestamp: Date.now() - 900000,
          user: 'Mike Johnson',
        },
        {
          id: '4',
          type: 'system',
          message: 'System backup completed',
          timestamp: Date.now() - 1200000,
          user: 'System',
        },
      ];
    }
  }

  async getAnalytics(period: '7d' | '30d' | '90d'): Promise<any> {
    try {
      const response = await apiClient.get(`/dashboard/analytics?period=${period}`);
      return response.data;
    } catch (error) {
      // Simulate analytics data for demo
      return {
        visitors: {
          total: Math.floor(Math.random() * 50000) + 25000,
          change: Math.floor(Math.random() * 20) - 10,
        },
        pageViews: {
          total: Math.floor(Math.random() * 100000) + 50000,
          change: Math.floor(Math.random() * 30) - 15,
        },
        bounceRate: {
          total: Math.floor(Math.random() * 40) + 30,
          change: Math.floor(Math.random() * 10) - 5,
        },
        avgSession: {
          total: Math.floor(Math.random() * 300) + 120,
          change: Math.floor(Math.random() * 60) - 30,
        },
      };
    }
  }
}

export const dashboardService = new DashboardService();