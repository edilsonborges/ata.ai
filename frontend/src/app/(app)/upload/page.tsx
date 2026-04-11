'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api, apiForm } from '@/lib/api';

type Provider = { id: string; provider: string; default_model: string; enabled: boolean; has_api_key: boolean };
type ModelOption = { name: string; eta_seconds: number; is_default: boolean };

function fmtEta(sec: number): string {
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return s ? `${m}m${s}s` : `${m}m`;
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [whisperModel, setWhisperModel] = useState('medium');
  const [providers, setProviders] = useState<Provider[]>([]);
  const [llmProvider, setLlmProvider] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    api<Provider[]>('/api/settings/providers').then(all => {
      const enabled = all.filter(p => p.enabled);
      setProviders(enabled);
      if (enabled[0]) setLlmProvider(enabled[0].provider);
    });
  }, []);

  async function onFile(f: File) {
    setFile(f); setDuration(null); setModels([]);
    // extrai duração no cliente usando HTMLMediaElement
    const url = URL.createObjectURL(f);
    const el = document.createElement('video');
    el.preload = 'metadata';
    el.src = url;
    el.onloadedmetadata = async () => {
      URL.revokeObjectURL(url);
      const d = Math.floor(el.duration);
      setDuration(d);
      const opts = await api<ModelOption[]>(`/api/whisper/models?duration_s=${d}`);
      setModels(opts);
      const def = opts.find(o => o.is_default);
      if (def) setWhisperModel(def.name);
    };
  }

  async function submit() {
    if (!file || !llmProvider) return;
    const provider = providers.find(p => p.provider === llmProvider);
    if (!provider) return;
    setBusy(true); setErr(null);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('whisper_model', whisperModel);
      form.append('llm_provider', llmProvider);
      form.append('llm_model', provider.default_model);
      const { id } = await apiForm<{id: string}>('/api/jobs', form);
      router.push(`/jobs/${id}`);
    } catch (e) {
      setErr(String(e));
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Nova analise</h1>

      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-6">
        <div>
          <label className="block text-sm font-medium mb-2">Arquivo (audio ou video)</label>
          <input
            type="file"
            accept=".mp4,.mov,.webm,.avi,.mkv,.wav,.mp3,.m4a,.ogg,.flac"
            onChange={e => e.target.files?.[0] && onFile(e.target.files[0])}
            className="block w-full text-sm"
          />
          {file && duration !== null && (
            <p className="text-xs text-slate-500 mt-2">
              {file.name} · {(file.size / 1024 / 1024).toFixed(1)} MB · {Math.floor(duration / 60)}:{(duration % 60).toString().padStart(2, '0')}
            </p>
          )}
        </div>

        {models.length > 0 && (
          <div>
            <label className="block text-sm font-medium mb-2">Modelo Whisper</label>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
              {models.map(m => (
                <button
                  key={m.name}
                  type="button"
                  onClick={() => setWhisperModel(m.name)}
                  className={`p-3 rounded-lg border text-sm text-left ${
                    whisperModel === m.name
                      ? 'border-primary bg-primary/5'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="font-medium">{m.name}</div>
                  <div className="text-xs text-slate-500 mt-1">~{fmtEta(m.eta_seconds)}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {providers.length > 0 && (
          <div>
            <label className="block text-sm font-medium mb-2">Provider de analise LLM</label>
            <select
              value={llmProvider ?? ''}
              onChange={e => setLlmProvider(e.target.value)}
              className="border border-slate-200 rounded-lg px-3 py-2"
            >
              {providers.map(p => (
                <option key={p.provider} value={p.provider}>
                  {p.provider} ({p.default_model})
                </option>
              ))}
            </select>
          </div>
        )}
        {providers.length === 0 && (
          <p className="text-sm text-red-600">Nenhum provider habilitado. Va em Configuracoes.</p>
        )}

        {err && <p className="text-red-600 text-sm">{err}</p>}

        <button
          onClick={submit}
          disabled={!file || !llmProvider || busy}
          className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
        >
          {busy ? 'Enviando...' : 'Processar'}
        </button>
      </div>
    </div>
  );
}
