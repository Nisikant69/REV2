import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, TrendingUp, Clock } from 'lucide-react';
import api from '@/lib/api';
import { MetricCard } from '@/components/MetricCard';
import { ReviewsTable } from '@/components/ReviewsTable';
import { toast } from 'sonner';

export default function Dashboard() {
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('24h');

  const {
    data: metrics,
    isLoading: metricsLoading,
    error: metricsError,
  } = useQuery({
    queryKey: ['metrics', timeRange],
    queryFn: () => api.getMetrics(timeRange),
  });

  const {
    data: reviews,
    isLoading: reviewsLoading,
    error: reviewsError,
  } = useQuery({
    queryKey: ['reviews', 'recent'],
    queryFn: () => api.getReviews({ limit: 10 }),
  });

  useEffect(() => {
    if (metricsError) {
      toast.error('Failed to load metrics');
    }
  }, [metricsError]);

  useEffect(() => {
    if (reviewsError) {
      toast.error('Failed to load reviews');
    }
  }, [reviewsError]);

  return (
    <>
      <Head>
        <title>Dashboard - REV2</title>
        <meta name="description" content="AI-powered code review dashboard" />
      </Head>

      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-2 text-gray-600">Monitor your code reviews and analytics in real-time</p>
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

        {metricsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-24 mb-2"></div>
                <div className="h-8 bg-gray-200 rounded w-16"></div>
              </div>
            ))}
          </div>
        ) : metrics ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <MetricCard
              title="Total Reviews"
              value={metrics.total_reviews}
              change={`${metrics.review_trend}%`}
              icon={TrendingUp}
              positive={metrics.review_trend >= 0}
            />
            <MetricCard
              title="Avg Latency"
              value={`${metrics.avg_latency_ms}ms`}
              change={`${Math.abs(metrics.latency_trend)}%`}
              icon={Clock}
              positive={metrics.latency_trend <= 0}
            />
            <MetricCard
              title="Cache Hit Rate"
              value={`${metrics.cache_hit_rate}%`}
              change={`${metrics.cache_trend}%`}
              icon={TrendingUp}
              positive={metrics.cache_trend >= 0}
            />
            <MetricCard
              title="Success Rate"
              value={`${metrics.success_rate}%`}
              change={`${metrics.success_trend}%`}
              icon={TrendingUp}
              positive={metrics.success_trend >= 0}
            />
          </div>
        ) : null}

        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">Recent Reviews</h2>
            <Link href="/reviews" className="text-primary-600 hover:text-primary-700 font-medium">
              View All →
            </Link>
          </div>
          <ReviewsTable reviews={reviews || []} loading={reviewsLoading} />
        </div>

        {!reviewsLoading && (!reviews || reviews.length === 0) && (
          <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
            <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-700 mb-2">No reviews yet</h3>
            <p className="text-gray-600">
              Your code reviews will appear here once you configure the GitHub app
            </p>
          </div>
        )}
      </div>
    </>
  );
}
