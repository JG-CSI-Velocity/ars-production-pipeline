// Real-backend fetch wrapper for the redesigned UI at /preview.
// Single source of truth for which endpoints exist and how they're called.
// Phase 0 of the wiring plan -- not yet consumed by prototype.jsx.

window.api = (() => {
  const j = async (url, opts) => {
    const r = await fetch(url, opts);
    if (!r.ok) {
      const body = await r.text().catch(() => '');
      throw new Error(`${url} -> ${r.status} ${body.slice(0, 200)}`);
    }
    return r.json();
  };

  const qs = (obj) => {
    const entries = Object.entries(obj).filter(([, v]) => v !== '' && v != null);
    return entries.length ? '?' + new URLSearchParams(entries) : '';
  };

  return {
    getCsms:      ()                        => j('/api/csms'),
    getClients:   (csm = '', month = '')    => j('/api/clients' + qs({ csm, month })),
    getProducts:  ()                        => j('/api/products'),
    getMonths:    (source = 'all', csm = '') => j('/api/months' + qs({ source, csm })),
    getRecent:    ()                        => j('/api/recent'),
    getStats:     ()                        => j('/api/stats'),
    getSchedules: ()                        => j('/api/schedules'),
    getFiles:     (csm, month, id)          => j(`/api/files/${csm}/${month}/${id}`),
    getOutputs:   (csm, month, id)          => j(`/api/outputs/${csm}/${month}/${id}`),

    startRun: (csm, month, clientId, product) =>
      j('/api/run' + qs({ csm, month, client_id: clientId, product }), { method: 'POST' }),
    getRun: (runId) => j(`/api/run/${runId}`),

    createSchedule: (body) =>
      j('/api/schedules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }),
    deleteSchedule: (id) => j(`/api/schedules/${id}`, { method: 'DELETE' }),
    runScheduleNow: (id) => j(`/api/schedules/${id}/run`, { method: 'POST' }),

    downloadUrl: (path) => '/api/download?' + new URLSearchParams({ path }),
  };
})();
