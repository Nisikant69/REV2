import axios, { AxiosInstance } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_TIMEOUT = parseInt(process.env.NEXT_PUBLIC_API_TIMEOUT || '30000');

const axiosClient: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api`,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Review {
  id: string;
  installation_id: string;
  repo_name: string;
  pr_number: number;
  pr_url: string;
  commit_sha: string;
  files_reviewed: number;
  review_status: 'success' | 'partial_failure' | 'failure';
  total_comments: number;
  api_latency_ms: number;
  cache_hit: boolean;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface Metrics {
  total_reviews: number;
  success_rate: number;
  avg_latency_ms: number;
  cache_hit_rate: number;
  review_trend: number;
  latency_trend: number;
  cache_trend: number;
  success_trend: number;
}

export interface Analytics {
  total_api_calls: number;
  api_calls_trend: number;
  avg_response_time_ms: number;
  response_time_trend: number;
  error_rate: number;
  error_rate_trend: number;
  model_performance: Array<{
    model_name: string;
    usage_count: number;
    avg_latency_ms: number;
    success_rate: number;
    avg_cost_usd: number;
  }>;
  top_repositories: Array<{
    repo_name: string;
    review_count: number;
    avg_latency_ms: number;
    success_rate: number;
  }>;
  cache_hits: number;
  cache_misses: number;
  rate_limited_requests: number;
  total_cost_usd: number;
}

export interface Settings {
  default_model?: string;
  max_files_per_review?: number;
  max_lines_per_file?: number;
  enable_caching?: boolean;
  enable_parallel_processing?: boolean;
  enable_batch_processing?: boolean;
  rate_limit_per_hour?: number;
  request_timeout_seconds?: number;
}

export const api = {
  getMetrics: async (timeRange: '24h' | '7d' | '30d' = '24h'): Promise<Metrics> => {
    const response = await axiosClient.get('/metrics', { params: { time_range: timeRange } });
    return response.data;
  },

  getReviews: async (options?: {
    search?: string;
    status?: string;
    sort_by?: string;
    page?: number;
    limit?: number;
  }): Promise<Review[]> => {
    const params = new URLSearchParams();
    if (options?.search) params.append('search', options.search);
    if (options?.status) params.append('status', options.status);
    if (options?.sort_by) params.append('sort_by', options.sort_by);
    if (options?.page) params.append('page', options.page.toString());
    if (options?.limit) params.append('limit', options.limit.toString());

    const response = await axiosClient.get(`/reviews?${params}`);
    return response.data;
  },

  getAnalytics: async (timeRange: '24h' | '7d' | '30d' = '7d'): Promise<Analytics> => {
    const response = await axiosClient.get('/analytics', { params: { time_range: timeRange } });
    return response.data;
  },

  getSettings: async (): Promise<Settings> => {
    const response = await axiosClient.get('/settings');
    return response.data;
  },

  updateSettings: async (settings: Settings): Promise<Settings> => {
    const response = await axiosClient.put('/settings', settings);
    return response.data;
  },

  exportReviews: async (options: {
    format: 'csv' | 'json';
    status?: string;
  }): Promise<string> => {
    const params = new URLSearchParams();
    if (options.format) params.append('format', options.format);
    if (options.status) params.append('status', options.status);

    const response = await axiosClient.get(`/reviews/export?${params}`);
    return response.data;
  },
};

export default api;
