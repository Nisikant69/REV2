import React, { useState } from 'react';
import Head from 'next/head';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, TrendingUp, AlertTriangle } from 'lucide-react';
import api from '@/lib/api';
import { MetricCard } from '@/components/MetricCard';
import { toast } from 'sonner';

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('7d');

  const {
    data: analytics,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['analytics', timeRange],
    queryFn: () => api.getAnalytics(timeRange),
  });

  React.useEffect(() => {
    if (error) {
      toast.error('Failed to load analytics');
    }
  }, [error]);

  return (
    <>
      <Head>
        <title>Analytics - REV2</title>
        <meta name="description" content="Code review analytics and insights" />
      </Head>

      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
          <p className="mt-2 text-gray-600">Detailed insights into your code review performance</p>
        </div>

        <div className="flex gap-2">
          {(['24h', '7d', '30d'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                timeRange === range
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {range === '24h' ? 'Last 24h' : range === '7d' ? 'Last 7d' : 'Last 30d'}
            </button>
          ))}
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-24 mb-4"></div>
                <div className="h-10 bg-gray-200 rounded w-32 mb-2"></div>
              </div>
            ))}
          </div>
        ) : analytics ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <MetricCard
                title="Total API Calls"
                value={analytics.total_api_calls}
                change={`${analytics.api_calls_trend}%`}
                icon={TrendingUp}
                positive={analytics.api_calls_trend >= 0}
              />
              <MetricCard
                title="Avg Response Time"
                value={`${analytics.avg_response_time_ms}ms`}
                change={`${Math.abs(analytics.response_time_trend)}%`}
                icon={TrendingUp}
                positive={analytics.response_time_trend <= 0}
              />
              <MetricCard
                title="Error Rate"
                value={`${analytics.error_rate}%`}
                change={`${Math.abs(analytics.error_rate_trend)}%`}
                icon={AlertTriangle}
                positive={analytics.error_rate_trend <= 0}
              />
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Model Performance
              </h2>

              <div className="space-y-4">
                {analytics.model_performance.map((model) => (
                  <div key={model.model_name} className="border-b border-gray-200 pb-4 last:border-0">
                    <div className="flex justify-between items-center mb-2">
                      <h3 className="font-medium text-gray-900">{model.model_name}</h3>
                      <span className="text-sm text-gray-600">{model.usage_count} reviews</span>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <p className="text-xs text-gray-600 mb-1">Avg Latency</p>
                        <p className="text-sm font-medium text-gray-900">{model.avg_latency_ms}ms</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-600 mb-1">Success Rate</p>
                        <p className="text-sm font-medium text-gray-900">{model.success_rate}%</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-600 mb-1">Avg Cost</p>
                        <p className="text-sm font-medium text-gray-900">${model.avg_cost_usd.toFixed(3)}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Top Repositories</h2>

              <div className="space-y-3">
                {analytics.top_repositories.map((repo) => (
                  <div key={repo.repo_name} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">{repo.repo_name}</p>
                      <p className="text-sm text-gray-600">{repo.review_count} reviews</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-900">{repo.avg_latency_ms}ms</p>
                      <p className="text-xs text-gray-600">{repo.success_rate}% success</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">API Usage Breakdown</h2>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-600 mb-1">Cache Hits</p>
                  <p className="text-2xl font-bold text-success-600">{analytics.cache_hits}</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-600 mb-1">Cache Misses</p>
                  <p className="text-2xl font-bold text-warning-600">{analytics.cache_misses}</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-600 mb-1">Rate Limited</p>
                  <p className="text-2xl font-bold text-danger-600">{analytics.rate_limited_requests}</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-600 mb-1">Total Cost</p>
                  <p className="text-2xl font-bold text-primary-600">${analytics.total_cost_usd.toFixed(2)}</p>
                </div>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </>
  );
}
