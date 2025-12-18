import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { QueueStatsCard } from '@/components/QueueStatsCard';
import { EventTimeline } from '@/components/EventRow';
import { useQueues, useQueueJobs, useRecentEvents } from './hooks';
import { useState } from 'react';

export function OpsMetricsPage() {
  const { data: metrics, isLoading: metricsLoading } = useQueues();
  const { data: jobs } = useQueueJobs();
  const { data: events } = useRecentEvents({ limit: 50 });
  const [activeTab, setActiveTab] = useState('overview');

  if (metricsLoading) {
    return <LoadingState message="Loading metrics..." />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Metrics</h1>
          <p className="text-gray-600">System observability and performance metrics</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-4">
          <h2 className="text-lg font-medium">Queue Health</h2>
          {metrics && metrics.length > 0 ? (
            <QueueStatsCard stats={metrics} />
          ) : (
            <EmptyState title="No queue data available" />
          )}
        </div>

        <div className="space-y-4">
          <h2 className="text-lg font-medium">Recent Activity</h2>
          {events && events.length > 0 ? (
            <EventTimeline events={events.slice(0, 10)} />
          ) : (
            <EmptyState title="No recent events" />
          )}
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-lg font-medium">System Summary</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-500">Total Jobs</div>
            <div className="text-2xl font-semibold text-gray-900">
              {jobs?.length || 0}
            </div>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-500">Active Queues</div>
            <div className="text-2xl font-semibold text-gray-900">
              {metrics?.length || 0}
            </div>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-500">Recent Events</div>
            <div className="text-2xl font-semibold text-gray-900">
              {events?.length || 0}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}