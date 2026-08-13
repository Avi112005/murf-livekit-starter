'use client';

import { useEffect, useState } from 'react';

type Metrics = {
  total: number;
  successful: number;
  failed: number;
  success_rate: number;
  failure_categories: { category: string; count: number }[];
};

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    fetch('/api/analytics', { cache: 'no-store' })
      .then((response) => response.json())
      .then(setMetrics)
      .catch(() => undefined);
  }, []);

  return (
    <main className="min-h-svh bg-[#102523] px-6 py-16 text-[#eff8ed]">
      <div className="mx-auto max-w-5xl">
        <p className="font-mono text-xs tracking-[0.2em] text-[#8bd9bb] uppercase">
          Aapda Sahaayak / Call analytics
        </p>
        <h1 className="mt-4 text-5xl font-semibold tracking-[-0.05em]">How calls are performing</h1>
        <p className="mt-4 max-w-xl text-[#a6c9bd]">
          Success means the caller completed a meaningful Disaster Response conversation and received a response.
        </p>
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          <Metric label="Total calls" value={metrics?.total} />
          <Metric label="Successful calls" value={metrics?.successful} accent />
          <Metric label="Failed calls" value={metrics?.failed} danger />
        </div>
        <div className="mt-6 grid gap-5 md:grid-cols-[0.8fr_1.2fr]">
          <section className="rounded-3xl border border-[#315c54] bg-[#15302d] p-7">
            <p className="text-sm text-[#a6c9bd]">Success rate</p>
            {metrics ? (
              <p className="mt-4 text-6xl font-semibold text-[#8bd9bb]">{metrics.success_rate}%</p>
            ) : (
              <div className="mt-5 h-16 w-32 animate-pulse rounded-xl bg-[#315c54]" />
            )}
          </section>
          <OutcomeChart metrics={metrics} />
        </div>
        <div className="mt-6">
          <FailureTypes categories={metrics?.failure_categories} />
        </div>
      </div>
    </main>
  );
}

function OutcomeChart({ metrics }: { metrics: Metrics | null }) {
  const total = metrics?.total ?? 0;
  const successPercent = total ? (metrics!.successful / total) * 100 : 0;

  return (
    <section className="rounded-3xl border border-[#315c54] bg-[#15302d] p-7">
      <p className="text-sm text-[#a6c9bd]">Call outcomes</p>
      {!metrics ? (
        <div className="mt-5 h-32 animate-pulse rounded-2xl bg-[#315c54]" />
      ) : total === 0 ? (
        <p className="mt-6 text-sm text-[#a6c9bd]">No calls recorded yet.</p>
      ) : (
        <div className="mt-5 grid gap-6 sm:grid-cols-[180px_1fr] sm:items-center">
          <div
            className="mx-auto size-40 rounded-full"
            style={{
              background: `conic-gradient(#8bd9bb 0 ${successPercent}%, #f0a27c ${successPercent}% 100%)`,
            }}
            aria-label="Successful and failed calls pie chart"
          />
          <div className="space-y-4">
            <OutcomeLegend label="Successful calls" count={metrics.successful} color="bg-[#8bd9bb]" />
            <OutcomeLegend label="Failed calls" count={metrics.failed} color="bg-[#f0a27c]" />
          </div>
        </div>
      )}
    </section>
  );
}

function OutcomeLegend({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div className="flex items-center justify-between text-sm text-[#c6ddd4]">
      <span className="flex items-center gap-3">
        <span className={`size-3 rounded-full ${color}`} />
        {label}
      </span>
      <strong>{count}</strong>
    </div>
  );
}

function FailureTypes({ categories }: { categories?: { category: string; count: number }[] }) {
  const total = categories?.reduce((sum, item) => sum + item.count, 0) ?? 0;

  return (
    <section className="rounded-3xl border border-[#315c54] bg-[#15302d] p-7">
      <p className="text-sm text-[#a6c9bd]">Failure types</p>
      {!categories ? (
        <div className="mt-5 h-24 animate-pulse rounded-2xl bg-[#315c54]" />
      ) : total === 0 ? (
        <p className="mt-5 text-sm text-[#a6c9bd]">No failed calls recorded.</p>
      ) : (
        <div className="mt-5 grid gap-x-8 gap-y-5 sm:grid-cols-2">
          {categories.map((item) => (
            <div key={item.category}>
              <div className="mb-2 flex justify-between text-xs text-[#c6ddd4]">
                <span>{item.category}</span>
                <strong>{item.count}</strong>
              </div>
              <div className="h-2 rounded-full bg-[#315c54]">
                <div
                  className="h-2 rounded-full bg-[#f0a27c]"
                  style={{ width: `${Math.max((item.count / total) * 100, 5)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function Metric({ label, value, accent, danger }: { label: string; value?: number; accent?: boolean; danger?: boolean }) {
  return (
    <div className="rounded-3xl border border-[#315c54] bg-[#15302d] p-7">
      <p className="text-sm text-[#a6c9bd]">{label}</p>
      {value === undefined ? (
        <div className="mt-5 h-16 w-24 animate-pulse rounded-xl bg-[#315c54]" aria-label="Loading" />
      ) : (
        <p className={`mt-4 text-6xl font-semibold ${accent ? 'text-[#8bd9bb]' : danger ? 'text-[#f0a27c]' : ''}`}>
          {value}
        </p>
      )}
    </div>
  );
}
