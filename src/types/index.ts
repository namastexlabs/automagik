export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  avatar?: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface DashboardMetrics {
  totalUsers: number;
  activeUsers: number;
  revenue: number;
  orders: number;
  growthRate: number;
}

export interface ChartData {
  name: string;
  value: number;
  date?: string;
}

export interface ApiResponse<T> {
  data: T;
  message: string;
  status: number;
}

export interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp: number;
}

export interface LoadingState {
  isLoading: boolean;
  error: string | null;
}

export interface Theme {
  primary: string;
  secondary: string;
  background: string;
  surface: string;
  text: string;
  textSecondary: string;
  border: string;
  success: string;
  warning: string;
  error: string;
}