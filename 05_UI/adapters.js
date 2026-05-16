// Normalizers that turn real-backend shapes into the shapes prototype.jsx
// currently expects from MockData. Lets us wire the UI piece-by-piece without
// rewriting every component.
// Phase 0 of the wiring plan -- not yet consumed by prototype.jsx.

window.adapters = (() => {
  // ---------- CSM ----------
  const COLORS = [
    '#F15D22', '#2A8B3E', '#00274C', '#7B4FB8',
    '#C77F3C', '#1B6CA8', '#B5651D', '#388E3C',
  ];
  const _hashStr = (s) => {
    let h = 0;
    for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
    return Math.abs(h);
  };
  const _initialsOf = (name) => {
    const parts = name.replace(/[^a-zA-Z ]/g, '').trim().split(/\s+/);
    if (parts.length === 0) return '??';
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };
  const enrichCsm = (name) => ({
    id: name,
    name,
    initials: _initialsOf(name),
    color: COLORS[_hashStr(name) % COLORS.length],
  });

  // ---------- Product ----------
  const PRODUCT_ID = {
    'ARS Full Suite': 'ars_full',
    'Transaction':    'txn',
    'Combined':       'combined',
    'Deposits':       'deposits',
  };
  const enrichProduct = (p) => ({
    id: p.id || PRODUCT_ID[p.name] || (p.name || '').toLowerCase().replace(/\s+/g, '_'),
    name: p.name || p.id,
    slides: p.slides || p.slide_count || p.count || 0,
    modules: p.modules || p.module_count || (p.groups ? p.groups.reduce((a, g) => a + (g.count || 0), 0) : 0),
    time: p.time || p.est_time || '—',
    desc: p.desc || p.description || (p.groups ? p.groups.map((g) => g.name).join(' · ') : ''),
  });

  // /api/products returns { id: {...} } -- normalize to array.
  const enrichProducts = (resp) => {
    if (Array.isArray(resp)) return resp.map(enrichProduct);
    if (resp && typeof resp === 'object') {
      return Object.entries(resp).map(([id, p]) => enrichProduct({ id, ...p }));
    }
    return [];
  };

  // ---------- Client ----------
  // `recentByClient` and `scheduleByClient` are lookups keyed by client id.
  // Both are optional -- if missing we fill with sensible empties.
  const enrichClient = (c, recentByClient = {}, scheduleByClient = {}) => {
    const recent = recentByClient[c.id];
    const sched = scheduleByClient[c.id];
    const cfg = c.config || {};
    const branchCount = cfg.branch_mapping
      ? (Array.isArray(cfg.branch_mapping) ? cfg.branch_mapping.length : Object.keys(cfg.branch_mapping).length)
      : 0;
    const fmtDate = (iso) => {
      if (!iso) return '—';
      try { return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }); }
      catch { return '—'; }
    };
    return {
      id: c.id,
      name: c.name,
      csm: recent?.csm || sched?.csm || '',
      accounts: recent?.account_count || 0,
      branches: branchCount,
      lastRun: fmtDate(recent?.finished_at || recent?.started_at),
      nextSched: sched?.next_run || sched?.day ? (sched.next_run || `Day ${sched.day}`) : '—',
      product: recent?.product || sched?.product || '',
      status: (() => {
        if (!recent) return 'ready';
        if (recent.status === 'error')    return 'error';
        if (recent.status === 'running')  return 'running';
        if (recent.status === 'complete') return 'ready';
        return 'ready';
      })(),
    };
  };

  // ---------- Run lifecycle (log -> prototype state) ----------
  // Ordered stage list matches the prototype's 5-stage checklist.
  const STAGES = ['read', 'prep', 'analyze', 'deck', 'finalize'];

  // Stage classifier -- backend log line -> {stage, done}
  // Patterns derived from the existing legacy UI's _classifyStage logic and
  // the analysis pipeline's emitted log strings.
  const _STAGE_PATTERNS = [
    { re: /Step\s*1\s*complete|formatting complete|formatted ODD/i, stage: 'read',     done: true  },
    { re: /Loading|Reading|Read your data/i,                        stage: 'read',     done: false },
    { re: /retrieve_data|Pipeline setup|Prepare/i,                  stage: 'prep',     done: false },
    { re: /Module\s+\d+\/\d+/i,                                     stage: 'analyze',  done: false },
    { re: /generate_output|Building deck|Composing slide/i,         stage: 'deck',     done: false },
    { re: /deck built|presentation saved/i,                         stage: 'deck',     done: true  },
    { re: /Step\s*2\s*complete|run complete|all done/i,             stage: 'finalize', done: true  },
  ];
  const classifyStage = (line) => {
    for (const p of _STAGE_PATTERNS) {
      if (p.re.test(line)) return { stage: p.stage, done: p.done };
    }
    return null;
  };

  // Parse "Module 16/25: mailer_response_rate"
  const _MODULE_RE = /Module\s+(\d+)\s*\/\s*(\d+)\s*[:\-]?\s*([A-Za-z0-9_.]+)?/i;
  const parseModuleProgress = (line) => {
    const m = line.match(_MODULE_RE);
    if (!m) return null;
    return { current: +m[1], total: +m[2], moduleId: m[3] || '' };
  };

  // Map module-id prefix -> human theme name shown in the Activity timeline.
  const MODULE_THEME = {
    overview:    'Account overview',
    dctr:        'Debit performance',
    rege:        'Reg E compliance',
    value:       'Value to members',
    attrition:   'At-risk accounts',
    mailer:      'Mailer effectiveness',
    insights:    'Strategic insights',
    competition: 'Competitor insights',
    payroll:     'Payroll & direct deposit',
    balance:     'Balance trends',
    financial:   'Financial services',
  };
  const themeFor = (moduleId) => {
    if (!moduleId) return '—';
    const prefix = moduleId.split(/[_.]/)[0].toLowerCase();
    return MODULE_THEME[prefix] || moduleId;
  };

  // Given the polling response {status, progress, current_step, log[]},
  // produce {stage, stageProg, themeNow, moduleNow, status, log}.
  const mapRun = (run) => {
    let stage = 'read';
    let stageProg = 0;
    let themeNow = '—';
    let moduleNow = '—';
    const log = run.log || [];

    for (const line of log) {
      const cls = classifyStage(line);
      if (cls) {
        const fromIdx = STAGES.indexOf(stage);
        const toIdx = STAGES.indexOf(cls.stage);
        if (toIdx > fromIdx) {
          // advancing to a later stage -- close out earlier ones
          stage = cls.stage;
          stageProg = cls.done ? 1 : 0.1;
        } else if (toIdx === fromIdx && cls.done) {
          stageProg = 1;
        }
      }
      const mp = parseModuleProgress(line);
      if (mp && mp.total > 0) {
        stage = 'analyze';
        stageProg = Math.min(1, mp.current / mp.total);
        moduleNow = mp.moduleId;
        themeNow = themeFor(mp.moduleId);
      }
    }

    if (run.status === 'complete') { stage = 'finalize'; stageProg = 1; }
    // status === 'error' -- leave stage/stageProg at last-known so the failing
    // step is visually flagged by the UI.

    return { stage, stageProg, themeNow, moduleNow, status: run.status || 'running', log };
  };

  // ---------- Recent runs / schedules indexing ----------
  // Helpers to build the lookups enrichClient expects.
  const indexBy = (arr, key) => {
    const out = {};
    for (const item of arr || []) {
      const k = item?.[key];
      if (k != null) out[String(k)] = item;
    }
    return out;
  };
  // Pick the most-recent run per client_id from a recent-runs array.
  const latestPerClient = (recentArr) => {
    const out = {};
    for (const r of recentArr || []) {
      const cid = String(r.client_id || r.client || '');
      if (!cid) continue;
      const prev = out[cid];
      const t = r.finished_at || r.started_at || '';
      const prevT = prev?.finished_at || prev?.started_at || '';
      if (!prev || t > prevT) out[cid] = r;
    }
    return out;
  };

  return {
    enrichCsm,
    enrichProduct,
    enrichProducts,
    enrichClient,
    classifyStage,
    parseModuleProgress,
    themeFor,
    mapRun,
    indexBy,
    latestPerClient,
    STAGES,
    MODULE_THEME,
  };
})();
