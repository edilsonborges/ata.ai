'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

type Job = {
  id: string;
  status: string;
  phase: string;
  progress_pct: number;
  input_filename: string;
  media_duration_s: number | null;
  whisper_model: string;
  llm_provider: string;
  created_at: string;
};

function statusBadge(status: string) {
  const map: Record<string, string> = {
    queued: 'bg-slate-100 text-slate-700',
    running: 'bg-blue-100 text-blue-700',
    done: 'bg-green-100 text-green-700',
    error: 'bg-red-100 text-red-700',
    canceled: 'bg-yellow-100 text-yellow-700',
  };
  return `px-2 py-0.5 rounded text-xs font-medium ${map[status] || ''}`;
}

export default function HomePage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<Job[]>('/api/jobs').then(setJobs).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-slate-500">Carregando...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Analises</h1>
        <Link href="/upload" className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium">
          Nova analise
        </Link>
      </div>

      {jobs.length === 0 ? (
        <div className="text-center py-16 text-slate-500">
          <p>Nenhuma analise ainda.</p>
          <Link href="/upload" className="text-primary underline">Fazer a primeira</Link>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="text-left px-4 py-3">Arquivo</th>
                <th className="text-left px-4 py-3">Duracao</th>
                <th className="text-left px-4 py-3">Modelo</th>
                <th className="text-left px-4 py-3">Provider</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-left px-4 py-3">Progresso</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(j => (
                <tr key={j.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link href={`/jobs/${j.id}`} className="text-primary hover:underline">
                      {j.input_filename}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{j.media_duration_s ? `${Math.floor(j.media_duration_s/60)}:${(j.media_duration_s%60).toString().padStart(2,'0')}` : '-'}</td>
                  <td className="px-4 py-3">{j.whisper_model}</td>
                  <td className="px-4 py-3">{j.llm_provider}</td>
                  <td className="px-4 py-3"><span className={statusBadge(j.status)}>{j.status}</span></td>
                  <td className="px-4 py-3">{j.progress_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
