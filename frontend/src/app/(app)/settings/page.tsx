'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

type Provider = {
  id: string;
  provider: string;
  default_model: string;
  enabled: boolean;
  has_api_key: boolean;
};

const LABELS: Record<string, string> = {
  anthropic: 'Anthropic API',
  openai: 'OpenAI',
  openrouter: 'OpenRouter',
  claude_cli: 'Claude CLI (terminal local)',
};

export default function SettingsPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    api<Provider[]>('/api/settings/providers').then(setProviders);
  }, []);

  async function save(p: Provider, apiKey: string | null) {
    setMsg(null);
    const body: Record<string, unknown> = {
      default_model: p.default_model,
      enabled: p.enabled,
    };
    if (apiKey !== null && p.provider !== 'claude_cli') body.api_key = apiKey;
    const updated = await api<Provider>(`/api/settings/providers/${p.provider}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
    setProviders(prev => prev.map(x => x.provider === updated.provider ? updated : x));
    setMsg(`${LABELS[p.provider]} atualizado`);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Configuracoes</h1>

      {msg && <p className="text-green-600 text-sm mb-4">{msg}</p>}

      <div className="space-y-4">
        {providers.map(p => (
          <ProviderCard key={p.provider} provider={p} onSave={save} />
        ))}
      </div>
    </div>
  );
}

function ProviderCard({ provider, onSave }: {
  provider: Provider;
  onSave: (p: Provider, apiKey: string | null) => Promise<void>;
}) {
  const [enabled, setEnabled] = useState(provider.enabled);
  const [model, setModel] = useState(provider.default_model);
  const [apiKey, setApiKey] = useState('');
  const [saving, setSaving] = useState(false);

  async function submit() {
    setSaving(true);
    try {
      await onSave(
        { ...provider, enabled, default_model: model },
        apiKey.trim() ? apiKey : null,
      );
      setApiKey('');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-medium">{LABELS[provider.provider] || provider.provider}</h3>
          {provider.has_api_key && <p className="text-xs text-green-600">API key configurada</p>}
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} />
          Ativado
        </label>
      </div>

      <div className="grid md:grid-cols-2 gap-3 mb-4">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Modelo default</label>
          <input
            value={model}
            onChange={e => setModel(e.target.value)}
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        {provider.provider !== 'claude_cli' && (
          <div>
            <label className="block text-xs text-slate-500 mb-1">API key (deixe vazio para manter)</label>
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder={provider.has_api_key ? '••••••••' : ''}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
            />
          </div>
        )}
      </div>

      <button onClick={submit} disabled={saving}
        className="bg-primary text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50">
        {saving ? 'Salvando...' : 'Salvar'}
      </button>
    </div>
  );
}
