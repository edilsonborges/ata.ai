'use client';

import { fetchEventSource } from '@microsoft/fetch-event-source';
import { useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { getAccessToken } from '@/lib/auth';

type Job = {
  id: string;
  status: string;
  phase: string;
  progress_pct: number;
  input_filename: string;
  folder_name: string | null;
  error_message: string | null;
};

type Event = {
  job_id: string;
  phase: string;
  progress_pct: number;
  message: string;
  level: 'info' | 'warn' | 'error';
};

const PHASE_LABEL: Record<string, string> = {
  validating: 'Validando',
  extracting_audio: 'Extraindo audio',
  transcribing: 'Transcrevendo',
  analyzing: 'Analisando com LLM',
  rendering: 'Gerando artefatos',
  done: 'Concluido',
};

export default function JobPage({ params }: { params: { id: string } }) {
  const [job, setJob] = useState<Job | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api<Job>(`/api/jobs/${params.id}`).then(setJob);

    const abort = new AbortController();
    const token = getAccessToken();
    fetchEventSource(`/api/jobs/${params.id}/events`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: abort.signal,
      onmessage(ev) {
        try {
          const data = JSON.parse(ev.data) as Event;
          setEvents(prev => [...prev, data]);
          setJob(prev => prev ? { ...prev, phase: data.phase, progress_pct: data.progress_pct } : prev);
          if (data.phase === 'done' || data.level === 'error') {
            api<Job>(`/api/jobs/${params.id}`).then(setJob);
          }
        } catch {}
      },
      onerror(err) { console.error(err); throw err; },
    }).catch(() => {});

    return () => abort.abort();
  }, [params.id]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [events]);

  if (!job) return <p className="text-slate-500">Carregando...</p>;

  const isDone = job.status === 'done';
  const isError = job.status === 'error';

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">{job.input_filename}</h1>
      <p className="text-sm text-slate-500 mb-6">
        {PHASE_LABEL[job.phase] || job.phase} — {job.progress_pct}%
      </p>

      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <div className="h-3 bg-slate-100 rounded-full overflow-hidden mb-4">
          <div
            className={`h-full ${isError ? 'bg-red-500' : 'bg-primary'} transition-all`}
            style={{ width: `${job.progress_pct}%` }}
          />
        </div>

        {isError && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg text-sm">
            <strong>Erro:</strong> {job.error_message}
          </div>
        )}

        <div ref={logRef} className="mt-4 h-48 overflow-y-auto bg-slate-50 rounded-lg p-3 text-xs font-mono">
          {events.map((e, i) => (
            <div key={i} className={e.level === 'error' ? 'text-red-600' : 'text-slate-700'}>
              [{e.progress_pct}%] {e.phase}: {e.message}
            </div>
          ))}
        </div>
      </div>

      {isDone && job.folder_name && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
          <div className="flex gap-3">
            <a href={`/api/jobs/${job.id}/artifacts/transcricao.vtt`}
               className="text-sm text-primary underline">Baixar transcricao.vtt</a>
            <a href={`/api/jobs/${job.id}/artifacts/analise.md`}
               className="text-sm text-primary underline">Baixar analise.md</a>
            <a href={`/api/jobs/${job.id}/artifacts/dashboard.html`}
               target="_blank" rel="noreferrer"
               className="text-sm text-primary underline">Abrir dashboard</a>
          </div>
          <iframe
            src={`/api/jobs/${job.id}/artifacts/dashboard.html`}
            className="w-full h-[80vh] border border-slate-200 rounded-lg"
          />
        </div>
      )}
    </div>
  );
}
