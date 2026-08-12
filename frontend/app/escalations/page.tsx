'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, Clock3, MapPinned, RefreshCw, ShieldAlert } from 'lucide-react';

type Escalation = {
  reference_id: string;
  name: string;
  situation: string;
  checked: string;
  urgency: string;
  language: string;
  follow_up: string;
  status: string;
  created_at: string;
};

export default function EscalationsPage() {
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);

  const loadEscalations = async () => {
    setLoading(true);
    const response = await fetch('/api/escalations', { cache: 'no-store' });
    const data = await response.json();
    setEscalations(data.escalations ?? []);
    setLoading(false);
  };

  useEffect(() => {
    void loadEscalations();
  }, []);

  return (
    <main className="min-h-svh bg-[#f5f0e8] px-5 py-12 text-[#173c39] dark:bg-[#102523] dark:text-[#eff8ed] sm:px-10">
      <div className="mx-auto max-w-5xl">
        <header className="flex flex-col justify-between gap-6 border-b border-[#c2d7c9] pb-8 sm:flex-row sm:items-end dark:border-[#315c54]">
          <div>
            <p className="font-mono text-xs font-bold tracking-[0.22em] text-[#b8623d] uppercase">
              Aapda Sahaayak / Human help desk
            </p>
            <h1 className="mt-3 text-4xl font-semibold tracking-[-0.05em]">Open requests</h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-[#5d8178] dark:text-[#a6c9bd]">
              Consent-based summaries for callers who need urgent local support. This page is a
              local reviewer view, not an emergency dispatch system.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadEscalations()}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-[#9ebfb0] px-5 font-mono text-xs font-bold tracking-wider uppercase transition-colors hover:bg-[#e1eee3] dark:border-[#477a6b] dark:hover:bg-[#183a35]"
          >
            <RefreshCw className={loading ? 'size-4 animate-spin' : 'size-4'} />
            Refresh
          </button>
        </header>

        <section className="mt-8 space-y-4" aria-live="polite">
          {!loading && escalations.length === 0 && (
            <div className="rounded-3xl border border-dashed border-[#9ebfb0] p-12 text-center dark:border-[#477a6b]">
              <ShieldAlert className="mx-auto size-8 text-[#b8623d]" />
              <p className="mt-4 font-semibold">No human-help requests yet</p>
              <p className="mt-2 text-sm text-[#5d8178] dark:text-[#a6c9bd]">
                Requests will appear here after a caller gives permission to share a summary.
              </p>
            </div>
          )}

          {escalations.map((request) => (
            <article
              key={request.reference_id}
              className="rounded-3xl border border-[#c2d7c9] bg-[#f8fbf6] p-6 shadow-sm dark:border-[#315c54] dark:bg-[#15302d]"
            >
              <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="rounded-full bg-[#f6dfc2] px-3 py-1 font-mono text-xs font-bold text-[#8d4a2e] dark:bg-[#4a3228] dark:text-[#ffc3ad]">
                      {request.reference_id}
                    </span>
                    <span className="rounded-full bg-[#d8eee3] px-3 py-1 text-xs font-semibold text-[#277a68] dark:bg-[#1d453e] dark:text-[#8bd9bb]">
                      {request.status}
                    </span>
                  </div>
                  <h2 className="mt-4 text-xl font-semibold">{request.name}</h2>
                </div>
                <div className="flex items-center gap-2 text-xs text-[#6c9288] dark:text-[#9bc0b2]">
                  <Clock3 className="size-4" />
                  {request.created_at}
                </div>
              </div>

              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl bg-[#edf4ed] p-4 dark:bg-[#1d453e]">
                  <p className="flex items-center gap-2 text-xs font-bold tracking-wider text-[#b8623d] uppercase">
                    <AlertTriangle className="size-4" /> Situation / urgency
                  </p>
                  <p className="mt-2 text-sm leading-6">{request.situation}</p>
                  <p className="mt-2 text-xs font-semibold uppercase">{request.urgency}</p>
                </div>
                <div className="rounded-2xl bg-[#edf4ed] p-4 dark:bg-[#1d453e]">
                  <p className="flex items-center gap-2 text-xs font-bold tracking-wider text-[#277a68] uppercase">
                    <MapPinned className="size-4" /> Follow-up
                  </p>
                  <p className="mt-2 text-sm leading-6">{request.follow_up}</p>
                  <p className="mt-2 text-xs text-[#5d8178] dark:text-[#a6c9bd]">{request.language}</p>
                </div>
              </div>

              <div className="mt-4 border-t border-[#d5e4d6] pt-4 text-sm leading-6 dark:border-[#315c54]">
                <strong>Already checked:</strong> {request.checked}
              </div>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
