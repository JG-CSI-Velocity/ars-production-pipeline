// Velocity — Working Prototype
// Single-file React app. Click through Dashboard → Run → In-Progress → Done.
// Library has Schedules (Calendar/Gantt toggle) and History. Runs animate
// through 5 stages in ~17s for demo. Multi-run supported.

// ─── DESIGN TOKENS ─────────────────────────────────────────────────────
const FONT = "'Montserrat', system-ui, sans-serif";
const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const C = {
  bg: '#f4f3f0', bgDeep: '#ecebe7',
  card: '#ffffff', cardSoft: '#fbfaf7',
  border: '#e6e3dd', borderStrong: '#d4d0c8',
  text: '#1A1A1A', muted: '#7d7870', faint: '#b7b1a8',
  navy: '#00274C', navyDeep: '#001a35',
  orange: '#F15D22', orangeDark: '#d14e1a', orangeSoft: '#fef0e8',
  green: '#2A8B3E', greenSoft: '#e8f5e9',
  red: '#c0392b', redSoft: '#fdecea',
  amber: '#B5651D', amberSoft: '#fff4e0',
};

// Demo-compressed stage durations (real-world: minutes; here: seconds).
const STAGE_MS = { read: 2000, prep: 3000, analyze: 8000, deck: 3000, finalize: 1000 };
const STAGE_REAL = { read: 24, prep: 38, analyze: 540, deck: 84, finalize: 18 };
const STAGE_CUM = (() => {
  const out = {};
  let acc = 0;
  for (const s of MockData.stages) { acc += STAGE_MS[s.id]; out[s.id] = acc; }
  return out;
})();
const TOTAL_MS = STAGE_CUM.finalize;

function runState(run, now) {
  // LIVE-mode runs carry a liveState filled by per-run polling. When present,
  // ignore the elapsed-time simulation and project the polled stage directly.
  if (run.liveState) {
    const ls = run.liveState;
    const stageIdx = Math.max(0, MockData.stages.findIndex((s) => s.id === ls.stage));
    if (ls.status === 'complete') return { stageIdx: MockData.stages.length, progress: 1, stageId: 'finalize', status: 'done' };
    if (ls.status === 'error')    return { stageIdx, progress: ls.stageProg || 0.5, stageId: ls.stage, status: 'error' };
    return { stageIdx, progress: ls.stageProg || 0, stageId: ls.stage, status: 'running' };
  }
  if (run.status === 'queued') return { stageIdx: -1, progress: 0, stageId: null, status: 'queued' };
  if (run.status === 'done') return { stageIdx: 5, progress: 1, stageId: 'finalize', status: 'done' };
  if (run.status === 'error') return { stageIdx: run.errorAt ?? 0, progress: 0.5, stageId: MockData.stages[run.errorAt ?? 0].id, status: 'error' };
  const elapsed = now - run.startedAt;
  for (let i = 0; i < MockData.stages.length; i++) {
    const s = MockData.stages[i];
    const end = STAGE_CUM[s.id];
    if (elapsed < end) {
      const start = i === 0 ? 0 : STAGE_CUM[MockData.stages[i-1].id];
      return { stageIdx: i, progress: (elapsed - start) / (end - start), stageId: s.id, status: 'running' };
    }
  }
  return { stageIdx: 5, progress: 1, stageId: 'finalize', status: 'done' };
}

// ─── APP STATE / CONTEXT ───────────────────────────────────────────────
const AppCtx = React.createContext(null);

function genId() { return 'r-' + Math.random().toString(16).slice(2, 9); }

function App() {
  const D = MockData;

  // LIVE mode (Phase 1+): fetch CSMs/clients/products from /api/* on mount
  // and mutate MockData in place so the existing components -- all of which
  // read D.csms / D.clients / D.products -- pick up the real data on next
  // render. When window.LIVE is false (e.g. design preview) we leave the
  // seed data alone.
  const [bootstrapped, setBootstrapped] = React.useState(!window.LIVE);
  const [bootError, setBootError] = React.useState(null);
  React.useEffect(() => {
    if (!window.LIVE) return;
    let cancelled = false;
    (async () => {
      try {
        const [csms, clients, products, recent, stats, schedules] = await Promise.all([
          window.api.getCsms(),
          window.api.getClients(),
          window.api.getProducts(),
          window.api.getRecent().catch(() => []),
          window.api.getStats().catch(() => ({})),
          window.api.getSchedules().catch(() => []),
        ]);
        if (cancelled) return;
        const recentByClient   = window.adapters.latestPerClient(recent);
        const scheduleByClient = window.adapters.indexBy(schedules, 'client_id');
        D.csms      = (csms     || []).map(window.adapters.enrichCsm);
        D.clients   = (clients  || []).map((c) =>
          window.adapters.enrichClient(c, recentByClient, scheduleByClient));
        D.products  = window.adapters.enrichProducts(products);
        D.recent    = recent    || [];
        D.stats     = stats     || {};
        D.schedules = schedules || [];
        setBootstrapped(true);
      } catch (e) {
        console.error('[velocity] live bootstrap failed:', e);
        if (!cancelled) setBootError(e.message || String(e));
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // In LIVE mode we don't seed phantom in-flight runs -- runs come from the
  // backend (Phase 2 wires /api/recent for live indicators).
  const initialRuns = React.useMemo(() => {
    if (window.LIVE) return [];
    const now = Date.now();
    return [
      { id: genId(), clientId: '1226', product: 'ars_full', csm: 'JamesG', status: 'running', startedAt: now - 6500 },
      { id: genId(), clientId: '2034', product: 'combined',  csm: 'Jordan', status: 'running', startedAt: now - 12200 },
    ];
  }, []);

  const [page, setPage] = React.useState('dashboard'); // dashboard | run | in-progress | library
  const [libTab, setLibTab] = React.useState('schedules'); // schedules | history
  const [schedView, setSchedView] = React.useState('gantt'); // gantt | calendar
  const [runs, setRuns] = React.useState(initialRuns);
  const [focusedRunId, setFocusedRunId] = React.useState(initialRuns[0]?.id ?? null);
  const [prefill, setPrefill] = React.useState(null); // {clientId, product} for Run Studio prefill
  const [now, setNow] = React.useState(Date.now());
  const [paletteOpen, setPaletteOpen] = React.useState(false);
  const [bulkOpen, setBulkOpen] = React.useState(false);
  const [toast, setToast] = React.useState(null);

  // Tick -- in non-LIVE mode drives simulated stage progress + auto-completion.
  // In LIVE mode the tick only refreshes `now` so clocks update; real run
  // status comes from per-run polling further down.
  React.useEffect(() => {
    const id = setInterval(() => {
      setNow(Date.now());
      if (window.LIVE) return;
      setRuns((rs) => rs.map((r) => {
        if (r.status === 'running') {
          const elapsed = Date.now() - r.startedAt;
          if (r.simulateFail && elapsed > STAGE_CUM.prep + 1800) {
            return { ...r, status: 'error', errorAt: 2, finishedAt: r.startedAt + STAGE_CUM.prep + 1800 };
          }
          if (elapsed >= TOTAL_MS) return { ...r, status: 'done', finishedAt: r.startedAt + TOTAL_MS };
        }
        return r;
      }));
    }, 200);
    return () => clearInterval(id);
  }, []);

  // Per-run polling -- one setInterval per in-flight LIVE run that has a
  // backend run_id. Stops itself when the run reaches a terminal state.
  React.useEffect(() => {
    if (!window.LIVE) return;
    const intervals = {};
    runs.forEach((r) => {
      if (!r.runId || intervals[r.id]) return;
      if (r.status !== 'running') return;
      intervals[r.id] = setInterval(async () => {
        try {
          const data = await window.api.getRun(r.runId);
          const ls = window.adapters.mapRun(data);
          setRuns((rs) => rs.map((x) => {
            if (x.id !== r.id) return x;
            const next = { ...x, liveState: ls };
            if (ls.status === 'complete') { next.status = 'done';  next.finishedAt = Date.now(); }
            if (ls.status === 'error')    { next.status = 'error'; next.finishedAt = Date.now(); }
            return next;
          }));
        } catch (e) {
          console.error('[velocity] poll failed for', r.runId, e);
        }
      }, 1000);
    });
    return () => Object.values(intervals).forEach(clearInterval);
  // We intentionally re-run on every runs change so new runs start polling
  // and finished runs stop. React handles cleanup of stale intervals.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runs.map((r) => r.id + ':' + r.status).join('|')]);

  // ⌘K / Ctrl+K opens the command palette globally.
  React.useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Map a prototype product id (or backend product id) to the canonical id
  // the backend's /api/run accepts. Falls back to whatever was given.
  const _backendProductId = (p) => {
    const m = { ars_full: 'ars', combined: 'ars', deposits: 'dep', txn: 'txn', dep: 'dep', ars: 'ars' };
    return m[p] || p;
  };

  // Helpers exposed via context
  const startRun = async (clientId, product) => {
    const client = D.clients.find(c => c.id === clientId) || { id: clientId, csm: '' };
    const id = genId();
    if (window.LIVE) {
      // Spawn a "pending" run immediately so the UI flips to In-Progress;
      // backend run_id arrives via the awaited POST.
      const pending = {
        id, clientId, product, csm: client.csm, status: 'running',
        startedAt: Date.now(), liveState: { stage: 'read', stageProg: 0, themeNow: '—', moduleNow: '—', status: 'running', log: [] },
      };
      setRuns((rs) => [...rs, pending]);
      setFocusedRunId(id);
      setPage('in-progress');
      try {
        const csm = client.csm || (D.csms[0]?.id) || '';
        const month = new Date().toISOString().slice(0, 7).replace('-', '.');
        const body = await window.api.startRun(csm, month, clientId, _backendProductId(product));
        setRuns((rs) => rs.map((r) => r.id === id ? { ...r, runId: body.run_id } : r));
      } catch (e) {
        console.error('[velocity] startRun failed:', e);
        setRuns((rs) => rs.map((r) => r.id === id ? { ...r, status: 'error', liveState: { ...r.liveState, status: 'error', log: [String(e.message || e)] } } : r));
      }
      return;
    }
    const newRun = { id, clientId, product, csm: client.csm, status: 'running', startedAt: Date.now(),
                     simulateFail: client.status === 'error' };
    setRuns((rs) => [...rs, newRun]);
    setFocusedRunId(id);
    setPage('in-progress');
  };

  const queueAnother = () => { setPrefill(null); setPage('run'); };
  const runAgain = (clientId, product) => { setPrefill({ clientId, product }); setPage('run'); };

  // Command palette action dispatcher.
  const handlePaletteAction = (a) => {
    if (a.type === 'goto') setPage(a.page);
    else if (a.type === 'bulk') setBulkOpen(true);
    else if (a.type === 'pickClient') { setPrefill({ clientId: a.clientId }); setPage('run'); }
    else if (a.type === 'run') startRun(a.clientId, a.product);
  };

  const handleBulkConfirm = (cfg) => {
    setToast(`Scheduled ${cfg.count} clients to auto-run on the ${ordinal(cfg.day)} of every month, starting ${cfg.startMonth}.`);
  };

  const activeRuns = runs.filter(r => r.status === 'running');
  const finishedRuns = runs.filter(r => r.status === 'done' || r.status === 'error');

  const ctx = { D, now, runs, activeRuns, finishedRuns, focusedRunId, setFocusedRunId,
                startRun, queueAnother, runAgain, page, setPage,
                libTab, setLibTab, schedView, setSchedView, prefill, setPrefill,
                paletteOpen, setPaletteOpen, bulkOpen, setBulkOpen };

  if (!bootstrapped) {
    return (
      <div style={{ width: '100%', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: C.bg, color: C.muted, fontFamily: FONT }}>
        {bootError
          ? <div style={{ maxWidth: 480, textAlign: 'center' }}>
              <div style={{ fontWeight: 700, color: C.text, marginBottom: 8 }}>Couldn't reach the backend.</div>
              <div style={{ fontSize: 13, fontFamily: MONO }}>{bootError}</div>
              <div style={{ fontSize: 12, marginTop: 12 }}>The legacy UI at <code>/</code> may still work.</div>
            </div>
          : <div>Loading Velocity…</div>}
      </div>
    );
  }

  return (
    <AppCtx.Provider value={ctx}>
      <div style={{ width: '100%', minHeight: '100vh', display: 'flex', flexDirection: 'column', background: C.bg }}>
        <Header />
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {page === 'dashboard'   && <Dashboard />}
          {page === 'run'         && <RunStudio />}
          {page === 'in-progress' && <InProgress />}
          {page === 'library'     && <Library />}
        </div>
        <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} onAction={handlePaletteAction} />
        <BulkScheduleModal open={bulkOpen} onClose={() => setBulkOpen(false)} onConfirm={handleBulkConfirm} />
        <Toast message={toast} onDismiss={() => setToast(null)} />
      </div>
    </AppCtx.Provider>
  );
}

function ordinal(n) {
  const s = ['th','st','nd','rd'], v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

const useApp = () => React.useContext(AppCtx);

// ─── HEADER ────────────────────────────────────────────────────────────
function Header() {
  const { activeRuns, setFocusedRunId, page, setPage, setPaletteOpen } = useApp();
  const tabs = [['dashboard','Dashboard'], ['run','Run'], ['library','Library']];

  return (
    <div style={{ background: C.navy, color: '#fff', display: 'flex', alignItems: 'center', padding: '0 24px', height: 56, flex: '0 0 auto', position: 'sticky', top: 0, zIndex: 50 }}>
      <div style={{ fontWeight: 800, fontSize: 18, letterSpacing: -0.3, marginRight: 32 }}>Velocity</div>
      <div style={{ display: 'flex', gap: 4, flex: 1 }}>
        {tabs.map(([id, name]) => (
          <button key={id} onClick={() => setPage(id)}
            style={{ padding: '7px 14px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', border: 'none',
              color: (page===id || (id === 'run' && (page === 'in-progress'))) ? '#fff' : 'rgba(255,255,255,0.55)',
              background: (page===id || (id === 'run' && page === 'in-progress')) ? 'rgba(255,255,255,0.08)' : 'transparent',
              transition: 'background .15s, color .15s' }}>
            {name}
          </button>
        ))}
      </div>

      {activeRuns.length > 0 && (
        <button onClick={() => { setFocusedRunId(activeRuns[0].id); setPage('in-progress'); }}
          style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: 'rgba(241,93,34,0.2)', border: '1px solid rgba(241,93,34,0.45)', borderRadius: 100, padding: '5px 12px 5px 8px', fontSize: 12, color: '#fff', cursor: 'pointer', marginRight: 12 }}>
          <span style={{ width: 6, height: 6, borderRadius: 99, background: C.orange, animation: 'pulse 1.6s ease-in-out infinite' }} />
          <span style={{ fontWeight: 700 }}>{activeRuns.length} running</span>
          <span style={{ opacity: 0.7, fontFamily: MONO, fontSize: 11 }}>
            {activeRuns.slice(0, 2).map(r => r.clientId).join(', ')}{activeRuns.length > 2 ? '…' : ''}
          </span>
        </button>
      )}

      {/* (Search pill removed per request — Ctrl+K still opens the command palette globally.) */}
    </div>
  );
}

// ─── SHARED UI ─────────────────────────────────────────────────────────
function PageHead({ kicker, title, sub, right }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 18, gap: 16, flexWrap: 'wrap' }}>
      <div>
        {kicker && <Kicker>{kicker}</Kicker>}
        <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: -0.4, lineHeight: 1.1, marginTop: 4 }}>{title}</div>
        {sub && <div style={{ fontSize: 13, color: C.muted, marginTop: 6 }}>{sub}</div>}
      </div>
      {right}
    </div>
  );
}

function Kicker({ children, color }) {
  return <div style={{ fontSize: 10, fontWeight: 700, color: color ?? C.muted, textTransform: 'uppercase', letterSpacing: 1.5 }}>{children}</div>;
}

function Btn({ kind='primary', onClick, children, disabled, style }) {
  const styles = {
    primary: { background: C.orange, color: '#fff', border: 'none' },
    dark:    { background: C.navy,   color: '#fff', border: 'none' },
    ghost:   { background: '#fff',   color: C.text, border: `1px solid ${C.border}` },
    danger:  { background: '#fff',   color: C.red,  border: `1px solid ${C.red}` },
  };
  return (
    <button onClick={disabled ? null : onClick} disabled={disabled}
      style={{ padding: '9px 16px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.5 : 1, display: 'inline-flex', alignItems: 'center', gap: 6, transition: 'transform .08s, background .15s', ...styles[kind], ...style }}
      onMouseDown={(e) => !disabled && (e.currentTarget.style.transform = 'translateY(1px)')}
      onMouseUp={(e) => (e.currentTarget.style.transform = '')}
      onMouseLeave={(e) => (e.currentTarget.style.transform = '')}>
      {children}
    </button>
  );
}

function Card({ children, style, padding=24 }) {
  return <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding, ...style }}>{children}</div>;
}

function Avatar({ csm, size=28 }) {
  return (
    <div style={{ width: size, height: size, borderRadius: 99, background: csm.color, color: '#fff', fontSize: Math.round(size*0.36), fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
      {csm.initials}
    </div>
  );
}

function StatusPill({ kind, children }) {
  const m = statusMeta[kind] || statusMeta.ready;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '2px 8px', borderRadius: 4, background: m.bg, color: m.fg, fontSize: 10, fontWeight: 700, fontFamily: MONO, textTransform: 'uppercase', letterSpacing: 0.6 }}>
      <span style={{ width: 5, height: 5, borderRadius: 99, background: m.fg }} />
      {children || m.label}
    </span>
  );
}

function fmtMmss(ms) {
  const s = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;
}

// Page wrapper — applies padding + scroll.
function Page({ children }) {
  return <div style={{ flex: 1, overflow: 'auto', padding: '24px 28px' }}>{children}</div>;
}

// ─── DASHBOARD ─────────────────────────────────────────────────────────
function Dashboard() {
  const { D, runs, activeRuns, now, setPage, startRun } = useApp();
  // Default to "all" in LIVE mode -- a single CSM ('JamesG' hardcoded before)
  // may not exist in the operator's actual config.
  const defaultCsm = window.LIVE ? 'all' : 'JamesG';
  const [dashCsm, setDashCsm] = React.useState(defaultCsm);

  const csmObj = D.csms.find(c => c.id === dashCsm);
  const inScope = (csmId) => dashCsm === 'all' || csmId === dashCsm;
  const scopedActive = activeRuns.filter(r => inScope(r.csm));
  const scopedClients = D.clients.filter(c => inScope(c.csm));

  // Today's scheduled list -- live mode uses real schedules filtered to
  // today's day-of-month; non-live mode keeps the demo seed.
  const today = React.useMemo(() => {
    if (window.LIVE) {
      const todayDay = new Date().getDate();
      return (D.schedules || [])
        .filter((s) => Number(s.day) === todayDay)
        .map((s) => {
          const c = D.clients.find((c) => c.id === String(s.client_id)) || {
            id: s.client_id, name: `Client ${s.client_id}`, csm: s.csm, product: s.product,
          };
          return { c, st: 'queued', t: '06:00' };
        })
        .filter(({ c }) => inScope(c.csm))
        .slice(0, 5);
    }
    const seeded = [
      { c: D.clients[1],  st: 'running', t: '06:00' },
      { c: D.clients[3],  st: 'running', t: '06:01' },
      { c: D.clients[5],  st: 'queued',  t: '06:02' },
      { c: D.clients[7],  st: 'queued',  t: '06:03' },
      { c: D.clients[10], st: 'queued',  t: '06:04' },
      { c: D.clients[0],  st: 'queued',  t: '06:05' },
      { c: D.clients[2],  st: 'queued',  t: '06:06' },
    ];
    return seeded.filter(({ c }) => c && inScope(c.csm)).slice(0, 5);
  }, [D.schedules, D.clients, dashCsm]);

  // Attention items -- live mode derives from recent runs with status=error|warning;
  // non-live uses the seed.
  const attention = React.useMemo(() => {
    if (window.LIVE) {
      return (D.recent || [])
        .filter((r) => r.status === 'error' || r.status === 'warning')
        .map((r) => {
          const c = D.clients.find((c) => c.id === String(r.client_id)) || {
            id: r.client_id, name: r.client_name || `Client ${r.client_id}`, csm: r.csm, product: r.product,
          };
          return {
            kind: r.status === 'error' ? 'error' : 'warning',
            client: c,
            msg: r.status === 'error' ? 'Last run failed -- check log.' : 'Last run had warnings.',
            cta: 'Review run',
          };
        })
        .filter((a) => inScope(a.client.csm));
    }
    const seeded = [
      { kind: 'error',   client: D.clients[9],  msg: 'Missing "Product Code" column in raw dump.', cta: 'Re-fetch data' },
      { kind: 'warning', client: D.clients[6],  msg: 'Last run had 3 no-chart-data slides.',       cta: 'Review warnings' },
      { kind: 'pending', client: D.clients[4],  msg: 'Raw dump not yet uploaded for May.',         cta: 'Notify Jordan' },
    ];
    return seeded.filter((a) => a.client && inScope(a.client.csm));
  }, [D.recent, D.clients, dashCsm]);

  // "Done this month" KPI -- real number when available.
  const doneThisMonth = window.LIVE
    ? (D.stats?.reports_generated ?? 0)
    : 47;
  const avgTime = window.LIVE ? (D.stats?.avg_time || '--') : '11m 42s';
  const successRate = window.LIVE ? (D.stats?.success_rate || '--') : '96%';

  const totalThisMonth = dashCsm === 'all' ? doneThisMonth + activeRuns.length : scopedClients.length;
  const titleText = dashCsm === 'all'
    ? `${totalThisMonth} reports queued this month`
    : `${csmObj ? csmObj.name.split(' ')[0] : dashCsm}'s ${scopedClients.length} clients`;
  const subText = dashCsm === 'all'
    ? `${doneThisMonth} done · ${scopedActive.length} running · ${today.length} scheduled today · ${attention.length} needing attention`
    : `${scopedActive.length} running · ${today.length} scheduled today · ${attention.length} needing attention`;

  return (
    <Page>
      <PageHead
        kicker={`Mission Control · May 2026`}
        title={titleText}
        sub={subText}
        right={<div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <CsmFilter value={dashCsm} onChange={setDashCsm} />
          <Btn kind="ghost" onClick={() => setPage('run')}>+ Run ad-hoc</Btn>
          <Btn onClick={() => setPage('library')}>Review schedule</Btn>
        </div>}
      />

      {/* KPI strip — replaces the month strip + 3-column block. Single scannable row. */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
        <KpiTile dotColor={C.orange} value={scopedActive.length} label="Running now"
          sub={scopedActive.length ? `${scopedActive.map(r => r.clientId).slice(0,2).join(', ')}${scopedActive.length>2?'…':''}` : 'idle'}
          onClick={scopedActive.length ? () => setPage('in-progress') : null} />
        <KpiTile dotColor={C.navy} value={today.length} label="Scheduled today"
          sub="auto-runs from 06:00" />
        <KpiTile dotColor={attention.length ? C.red : C.green} value={attention.length} label="Needs attention"
          sub={attention.length ? 'click to review' : 'all clear'}
          highlight={attention.length > 0} />
        <KpiTile dotColor={C.green} value={doneThisMonth} label="Done this month"
          sub={`avg ${avgTime} · success ${successRate}`} onClick={() => setPage('library')} />
      </div>

      {/* Attention banner — only when there are items */}
      {attention.length > 0 && (
        <Card padding={0} style={{ marginBottom: 16, borderColor: C.red, background: '#fff' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 16px', borderBottom: `1px solid ${C.border}`, background: C.redSoft }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 18, height: 18, borderRadius: 99, background: C.red, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Icon.warn size={11} />
              </div>
              <div style={{ fontSize: 13, fontWeight: 700, color: C.red }}>{attention.length} item{attention.length === 1 ? '' : 's'} need a look</div>
            </div>
            <div style={{ fontFamily: MONO, fontSize: 11, color: C.muted }}>before scheduled runs fire</div>
          </div>
          <div>
            {attention.map((a, i, arr) => {
              const csm = D.csms.find(x => x.id === a.client.csm);
              const accent = a.kind === 'error' ? C.red : C.amber;
              return (
                <div key={i} style={{ display: 'grid', gridTemplateColumns: '24px 28px 1fr auto auto', gap: 12, alignItems: 'center', padding: '10px 16px', borderBottom: i < arr.length-1 ? `1px solid ${C.border}` : 'none' }}>
                  <div style={{ width: 18, height: 18, borderRadius: 99, background: accent === C.red ? C.redSoft : C.amberSoft, color: accent, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {a.kind === 'error' ? <Icon.x size={10} /> : <Icon.warn size={10} />}
                  </div>
                  <Avatar csm={csm} size={24} />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 600 }}>{a.client.name} <span style={{ color: C.muted, fontWeight: 500 }}>— {a.msg}</span></div>
                    <div style={{ fontFamily: MONO, fontSize: 10, color: C.muted, marginTop: 2 }}>{a.client.id} · {a.client.product}</div>
                  </div>
                  <button style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 11, fontWeight: 700, color: accent }}>{a.cta} →</button>
                  <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: C.faint, padding: 4, display: 'flex' }} title="Dismiss"><Icon.x size={10} /></button>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Roster (CSM client list) — Run Studio's row treatment, dashboard-scaled */}
      <Card padding={0} style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: `1px solid ${C.border}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ fontSize: 14, fontWeight: 700 }}>
              {dashCsm === 'all' ? 'All clients' : `${csmObj.name.split(' ')[0]}'s roster`}
            </div>
            <span style={{ fontFamily: MONO, fontSize: 11, color: C.muted }}>{scopedClients.length} client{scopedClients.length === 1 ? '' : 's'}</span>
          </div>
          <button onClick={() => setPage('run')}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600, color: C.orange }}>
            Pick + configure in Run Studio →
          </button>
        </div>
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: '32px 1fr 110px 110px 110px 90px', gap: 14, alignItems: 'center', padding: '10px 20px', borderBottom: `1px solid ${C.border}`, background: C.cardSoft, fontSize: 10, fontWeight: 700, color: C.muted, textTransform: 'uppercase', letterSpacing: 1.2 }}>
            <div></div><div>Client</div><div>Last run</div><div>Next sched</div><div>Status</div><div></div>
          </div>
          {scopedClients.length === 0 && (
            <div style={{ padding: '32px 20px', textAlign: 'center', color: C.muted, fontSize: 13 }}>No clients for this CSM.</div>
          )}
          {scopedClients.map((c, i, arr) => {
            const csm = D.csms.find(x => x.id === c.csm);
            return (
              <div key={c.id}
                style={{ display: 'grid', gridTemplateColumns: '32px 1fr 110px 110px 110px 90px', gap: 14, alignItems: 'center', padding: '12px 20px', borderBottom: i < arr.length-1 ? `1px solid ${C.border}` : 'none' }}>
                <Avatar csm={csm} size={28} />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 600 }}>{c.name}</div>
                  <div style={{ fontFamily: MONO, fontSize: 11, color: C.muted, marginTop: 2 }}>{c.id} · {c.product} · {c.accounts.toLocaleString()} accounts · {c.branches} branches</div>
                </div>
                <div style={{ fontFamily: MONO, fontSize: 11, color: C.muted }}>{c.lastRun}</div>
                <div style={{ fontFamily: MONO, fontSize: 11, color: C.muted }}>{c.nextSched}</div>
                <div><StatusPill kind={c.status} /></div>
                <div style={{ textAlign: 'right' }}>
                  <button onClick={() => startRun(c.id, productIdFor(c.product))}
                    style={{ padding: '6px 12px', borderRadius: 5, fontSize: 11, fontWeight: 700, cursor: 'pointer', background: C.orange, color: '#fff', border: 'none', display: 'inline-flex', alignItems: 'center', gap: 5, fontFamily: FONT }}>
                    <Icon.bolt size={10} /> Run
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Recent runs */}
      <Card padding={0}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 14, fontWeight: 700 }}>Recently completed</div>
          <button onClick={() => setPage('library')} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600, color: C.orange }}>View history →</button>
        </div>
        <RecentRunsTable />
      </Card>
    </Page>
  );
}

// CSM filter pill — used on the Dashboard.
function CsmFilter({ value, onChange }) {
  const D = MockData;
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef(null);
  React.useEffect(() => {
    const onClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    window.addEventListener('click', onClick);
    return () => window.removeEventListener('click', onClick);
  }, []);

  const selected = value === 'all'
    ? { name: 'All CSMs', initials: 'ALL', color: C.navy }
    : D.csms.find(c => c.id === value);

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button onClick={() => setOpen(o => !o)}
        style={{ display: 'inline-flex', alignItems: 'center', gap: 10, padding: '6px 12px 6px 6px', borderRadius: 99, background: '#fff', border: `1px solid ${C.border}`, cursor: 'pointer', fontFamily: FONT }}>
        <div style={{ width: 24, height: 24, borderRadius: 99, background: selected.color, color: '#fff', fontSize: 9, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{selected.initials}</div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', lineHeight: 1.1 }}>
          <div style={{ fontFamily: MONO, fontSize: 9, color: C.muted, textTransform: 'uppercase', letterSpacing: 1.2 }}>CSM</div>
          <div style={{ fontSize: 12.5, fontWeight: 700, color: C.text }}>{selected.name}{value === 'JamesG' ? ' (you)' : ''}</div>
        </div>
        <span style={{ color: C.muted, marginLeft: 4 }}><Icon.chev /></span>
      </button>
      {open && (
        <div style={{ position: 'absolute', top: '100%', right: 0, marginTop: 6, background: '#fff', border: `1px solid ${C.border}`, borderRadius: 8, boxShadow: '0 8px 24px rgba(0,0,0,0.08)', minWidth: 220, zIndex: 20, padding: 4 }}>
          {[{ id: 'all', name: 'All CSMs', initials: 'ALL', color: C.navy }, ...D.csms].map((opt) => {
            const on = opt.id === value;
            const cs = opt.id === 'all' ? D.clients : D.clients.filter(c => c.csm === opt.id);
            return (
              <button key={opt.id} onClick={() => { onChange(opt.id); setOpen(false); }}
                style={{ width: '100%', display: 'grid', gridTemplateColumns: '24px 1fr auto', gap: 10, alignItems: 'center', padding: '8px 10px', borderRadius: 6, cursor: 'pointer', background: on ? C.orangeSoft : 'transparent', border: 'none', textAlign: 'left' }}>
                <div style={{ width: 22, height: 22, borderRadius: 99, background: opt.color, color: '#fff', fontSize: 8, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT }}>{opt.initials}</div>
                <div style={{ fontSize: 13, fontWeight: on ? 700 : 500, color: C.text }}>
                  {opt.name}{opt.id === 'JamesG' ? ' (you)' : ''}
                </div>
                <div style={{ fontFamily: MONO, fontSize: 11, color: C.muted }}>{cs.length}</div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Helper — name → product id (mirrors prototype-extras).
function productIdFor(name) {
  if (!name) return MockData.products[0]?.id || 'ars';
  // Prefer a match against the loaded product list (works for both LIVE backend
  // ids like 'ars' / 'txn' / 'dep' and the prototype's seed ids).
  const hit = MockData.products.find((p) => p.id === name || p.name === name);
  if (hit) return hit.id;
  return ({ 'ARS Full Suite': 'ars_full', 'Transaction': 'txn', 'Combined': 'combined', 'Deposits': 'deposits' })[name]
    || MockData.products[0]?.id || 'ars';
}

function LegendDot({ color, children }) {
  return <span><span style={{ display: 'inline-block', width: 8, height: 8, background: color, borderRadius: 2, marginRight: 5, verticalAlign: '-1px' }} />{children}</span>;
}

// KPI tile — single scannable metric. Optional onClick.
function KpiTile({ dotColor, value, label, sub, onClick, highlight }) {
  return (
    <div onClick={onClick}
      style={{ background: C.card, border: `1px solid ${highlight ? C.red : C.border}`, borderRadius: 10, padding: '14px 18px', cursor: onClick ? 'pointer' : 'default',
        transition: 'border-color .15s, transform .08s' }}
      onMouseEnter={(e) => { if (onClick) e.currentTarget.style.borderColor = C.orange; }}
      onMouseLeave={(e) => { if (onClick) e.currentTarget.style.borderColor = highlight ? C.red : C.border; }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{ width: 8, height: 8, borderRadius: 99, background: dotColor }} />
        <span style={{ fontSize: 10, fontWeight: 700, color: C.muted, textTransform: 'uppercase', letterSpacing: 1.4 }}>{label}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ fontFamily: MONO, fontSize: 30, fontWeight: 700, lineHeight: 1, color: C.text }}>{value}</div>
        <div style={{ fontFamily: MONO, fontSize: 11, color: C.muted, textAlign: 'right' }}>{sub}</div>
      </div>
    </div>
  );
}

function LiveRunCard({ run }) {
  const { D, now, setFocusedRunId, setPage } = useApp();
  const client = D.clients.find(c => c.id === run.clientId);
  const st = runState(run, now);
  const stage = st.stageIdx >= 0 ? D.stages[st.stageIdx] : null;
  const elapsed = now - run.startedAt;
  const eta = Math.max(0, TOTAL_MS - elapsed);
  return (
    <div onClick={() => { setFocusedRunId(run.id); setPage('in-progress'); }}
      style={{ padding: '12px 14px', borderRadius: 8, margin: '4px', background: C.cardSoft, border: `1px solid ${C.border}`, cursor: 'pointer', transition: 'border-color .15s' }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = C.orange)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = C.border)}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 8 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, lineHeight: 1.2 }}>{client.name}</div>
          <div style={{ fontFamily: MONO, fontSize: 10, color: C.muted, marginTop: 2 }}>{run.clientId} · {productName(run.product)} · {run.csm}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontFamily: MONO, fontSize: 13, fontWeight: 700, color: C.orange }}>{fmtMmss(elapsed)}</div>
          <div style={{ fontFamily: MONO, fontSize: 9, color: C.muted, marginTop: 2 }}>≈ {fmtMmss(eta)} left</div>
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 6 }}>
        {D.stages.map((s, i) => {
          const state = i < st.stageIdx ? 'done' : i === st.stageIdx ? 'active' : 'idle';
          const bg = state === 'done' ? C.green : state === 'active' ? C.orange : C.border;
          return (
            <div key={s.id} style={{ flex: 1, height: 4, background: bg, borderRadius: 2, position: 'relative' }}>
              {state === 'active' && (
                <div style={{ position: 'absolute', inset: 0, background: `linear-gradient(90deg, ${C.orange} ${st.progress*100}%, rgba(241,93,34,0.25) ${st.progress*100}%)`, borderRadius: 2 }} />
              )}
            </div>
          );
        })}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
        <div><span style={{ color: C.muted }}>Stage {Math.max(1, st.stageIdx+1)}/5 ·</span> <span style={{ fontWeight: 600 }}>{stage?.name ?? 'queued'}</span></div>
        <div style={{ fontFamily: MONO, color: C.muted, fontSize: 10 }}>{stage?.desc}</div>
      </div>
    </div>
  );
}

function productName(id) {
  const p = MockData.products.find(p => p.id === id);
  return p?.name ?? id;
}

function AttentionRow({ kind, client, msg, cta, first }) {
  const accent = kind === 'error' ? { fg: C.red, bg: C.redSoft } : { fg: C.amber, bg: C.amberSoft };
  return (
    <div style={{ padding: '12px 18px', borderTop: first ? 'none' : `1px solid ${C.border}` }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 6 }}>
        <div style={{ width: 20, height: 20, borderRadius: 99, background: accent.bg, color: accent.fg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          {kind === 'error' ? <Icon.x size={10} /> : <Icon.warn size={11} />}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12.5, fontWeight: 700, lineHeight: 1.2 }}>{client.name}</div>
          <div style={{ fontFamily: MONO, fontSize: 10, color: C.muted, marginTop: 1 }}>{client.id} · {client.product}</div>
        </div>
      </div>
      <div style={{ fontSize: 11.5, color: C.muted, marginBottom: 8, lineHeight: 1.4 }}>{msg}</div>
      <div style={{ fontSize: 11, fontWeight: 700, color: accent.fg, cursor: 'pointer' }}>{cta} →</div>
    </div>
  );
}

function MonthStrip() {
  const days = Array.from({ length: 31 }, (_, i) => {
    const d = i + 1;
    if (d === 15) return { d, state: 'today', count: 5 };
    if (d < 15) {
      if (d === 6) return { d, state: 'failed', count: 1 };
      if (d === 4) return { d, state: 'done', count: 4 };
      if (d === 13) return { d, state: 'running', count: 2 };
      return { d, state: d % 4 === 0 || d % 3 === 0 ? 'done' : 'past-empty', count: d % 4 === 0 ? 3 : 0 };
    }
    if (d % 7 === 0 || d % 5 === 0) return { d, state: 'scheduled', count: 2 + (d % 3) };
    if (d === 22 || d === 28) return { d, state: 'scheduled', count: 4 };
    return { d, state: 'future', count: 0 };
  });
  const color = (s) => ({ done: C.green, failed: C.red, running: C.orange, scheduled: C.navy, today: C.orange, 'past-empty': C.faint, future: C.border }[s] || C.border);
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(31, 1fr)', gap: 4 }}>
      {days.map(({ d, state, count }) => (
        <div key={d}>
          <div style={{ height: 36, background: C.cardSoft, borderRadius: 4, display: 'flex', flexDirection: 'column-reverse', overflow: 'hidden', border: state === 'today' ? `1.5px solid ${C.orange}` : 'none' }}>
            {count > 0 && <div style={{ height: `${Math.min(100, count * 18)}%`, background: color(state), opacity: state === 'past-empty' ? 0.25 : 1 }} />}
          </div>
          <div style={{ fontFamily: MONO, fontSize: 9, textAlign: 'center', color: state === 'today' ? C.orange : C.muted, fontWeight: state === 'today' ? 700 : 400, marginTop: 4 }}>{d}</div>
        </div>
      ))}
    </div>
  );
}

function RecentRunsTable() {
  const { D, finishedRuns, runAgain } = useApp();
  // Parse "30m 24s" / "1h 5m" into seconds for the formatter; fall back to 0.
  const parseDur = (s) => {
    if (!s || typeof s !== 'string') return 0;
    let secs = 0;
    const h = s.match(/(\d+)\s*h/); if (h) secs += +h[1] * 3600;
    const m = s.match(/(\d+)\s*m/); if (m) secs += +m[1] * 60;
    const sec = s.match(/(\d+)\s*s/); if (sec) secs += +sec[1];
    return secs;
  };
  const relTime = (ts) => {
    const m = String(ts || '').match(/(\d{4})[-_.](\d{2})[-_.](\d{2})/);
    if (!m) return ts || '—';
    const d = new Date(`${m[1]}-${m[2]}-${m[3]}`);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  };

  let merged;
  if (window.LIVE) {
    merged = (D.recent || []).map((r) => ({
      client: D.clients.find((c) => c.id === String(r.client_id)) || { id: r.client_id, name: r.client_name || `Client ${r.client_id}`, csm: r.csm },
      product: r.product || (r.file ? '' : ''),
      duration: parseDur(r.duration),
      finished: relTime(r.timestamp),
      status: r.status === 'error' ? 'error' : r.status === 'warning' ? 'warning' : 'done',
    }));
  } else {
    const sample = [
      { client: D.clients[1], product: 'ars_full',  duration: 705, finished: '2h ago',  status: 'done' },
      { client: D.clients[7], product: 'ars_full',  duration: 728, finished: '3h ago',  status: 'done' },
      { client: D.clients[6], product: 'txn',       duration: 374, finished: '4h ago',  status: 'warning' },
      { client: D.clients[9], product: 'deposits',  duration: 38,  finished: '5h ago',  status: 'error' },
      { client: D.clients[12], product: 'ars_full', duration: 711, finished: '6h ago',  status: 'done' },
    ];
    merged = [
      ...finishedRuns.map((r) => ({ client: D.clients.find((c) => c.id === r.clientId), product: r.product, duration: Math.floor((r.finishedAt - r.startedAt)/1000), finished: 'just now', status: 'done' })),
      ...sample,
    ];
  }
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '80px 1.5fr 1fr 100px 90px 90px 90px', padding: '8px 20px', borderBottom: `1px solid ${C.border}`, background: C.cardSoft, fontSize: 10, fontWeight: 700, color: C.muted, textTransform: 'uppercase', letterSpacing: 1 }}>
        <div>Status</div><div>Client</div><div>Product</div><div>CSM</div><div>Duration</div><div>Finished</div><div></div>
      </div>
      {merged.slice(0, 6).map((r, i, all) => (
        <div key={i} className={r.finished === 'just now' ? 'flash-in' : ''}
          style={{ display: 'grid', gridTemplateColumns: '80px 1.5fr 1fr 100px 90px 90px 90px', alignItems: 'center', padding: '12px 20px', borderBottom: i < all.length-1 ? `1px solid ${C.border}` : 'none', fontSize: 13 }}>
          <div><StatusPill kind={r.status === 'done' ? 'done' : r.status === 'warning' ? 'warning' : 'error'}>{r.status}</StatusPill></div>
          <div><div style={{ fontWeight: 600 }}>{r.client?.name}</div><div style={{ fontFamily: MONO, fontSize: 11, color: C.muted, marginTop: 2 }}>{r.client?.id}</div></div>
          <div style={{ fontSize: 12, color: C.muted }}>{productName(r.product)}</div>
          <div style={{ fontFamily: MONO, fontSize: 12, color: C.muted }}>{r.client?.csm}</div>
          <div style={{ fontFamily: MONO, fontSize: 12 }}>{fmtMmss(r.duration*1000)}</div>
          <div style={{ fontFamily: MONO, fontSize: 12, color: C.muted }}>{r.finished}</div>
          <div style={{ textAlign: 'right' }}>
            <button onClick={() => runAgain(r.client?.id, r.product)}
              style={{ background: 'none', border: `1px solid ${C.border}`, padding: '4px 10px', borderRadius: 4, fontSize: 11, color: C.text, cursor: 'pointer', fontFamily: MONO }}>↻ rerun</button>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── RUN STUDIO ────────────────────────────────────────────────────────
function RunStudio() {
  const { D, startRun, prefill, setPrefill } = useApp();
  // Pick safe defaults: first CSM, first client (filtered by CSM), first product.
  const _firstCsm = D.csms[0]?.id || 'JamesG';
  const _firstClient = D.clients.find((c) => c.csm === _firstCsm) || D.clients[0];
  const _firstProduct = D.products[0]?.id || 'ars_full';
  const [csmFilter, setCsmFilter] = React.useState(_firstCsm);
  const [pickId, setPickId] = React.useState(prefill?.clientId || _firstClient?.id || '1776');
  const [product, setProduct] = React.useState(prefill?.product || _firstProduct);
  const [customPath, setCustomPath] = React.useState(null); // null = use default; string = override path
  const [editingPath, setEditingPath] = React.useState(false);
  const [pathDraft, setPathDraft] = React.useState('');
  // Clear prefill after first render
  React.useEffect(() => { if (prefill) setPrefill(null); }, []);

  const csmClients = D.clients.filter(c => c.csm === csmFilter);
  // If user switches CSM and current pick no longer applies, snap to that CSM's first client.
  React.useEffect(() => {
    if (!csmClients.find(c => c.id === pickId)) setPickId(csmClients[0]?.id);
  }, [csmFilter]);

  const pick = D.clients.find(c => c.id === pickId) || D.clients[0];
  const csm = D.csms.find(c => c.id === pick.csm);
  const product_ = D.products.find(p => p.id === product);

  // Default source path mirrors ars_config.json csm_sources.sources
  const defaultPath = `M:\\${csmFilter}\\OD Data Dumps\\2026.05`;
  const activePath = customPath ?? defaultPath;

  return (
    <Page>
      <PageHead
        kicker="Run · ad-hoc"
        title="Queue an ad-hoc run"
        sub="Pick a client, confirm the product, run. Scheduled runs go through Library → Schedules."
      />

      {/* Top filter row */}
      <Card padding="14px 18px" style={{ marginBottom: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1.6fr', gap: 14, alignItems: 'end' }}>
          <Field label="CSM">
            <NativeSelect value={csmFilter} onChange={setCsmFilter}
              options={D.csms.map(c => [c.id, c.name + (c.id === 'JamesG' ? ' (you)' : '')])} />
          </Field>
          <Field label="Period">
            <NativeSelect value="2026.05" onChange={() => {}} options={[['2026.05','2026.05 — May 2026'],['2026.04','2026.04 — April 2026']]} />
          </Field>
          <Field label={`Client · ${csmClients.length} for this CSM`}>
            <NativeSelect value={pickId} onChange={setPickId}
              options={csmClients.map(c => [c.id, `${c.id} — ${c.name}`])} />
          </Field>
        </div>

        {/* Data source row */}
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px dashed ${C.border}` }}>
          {!editingPath ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12 }}>
              <span style={{ fontSize: 10, fontWeight: 700, color: C.muted, textTransform: 'uppercase', letterSpacing: 1.5 }}>Data source</span>
              <span style={{ color: C.muted, display: 'flex' }}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M1.5 4.5V11.5C1.5 12.05 1.95 12.5 2.5 12.5H11.5C12.05 12.5 12.5 12.05 12.5 11.5V5.5C12.5 4.95 12.05 4.5 11.5 4.5H7L5.5 3H2.5C1.95 3 1.5 3.45 1.5 4V4.5Z"
                    stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
                </svg>
              </span>
              <span style={{ fontFamily: MONO, fontSize: 12, color: customPath ? C.orange : C.text, fontWeight: 500 }}>
                {activePath}
              </span>
              {customPath && (
                <span style={{ fontFamily: MONO, fontSize: 10, color: C.orange, background: C.orangeSoft, padding: '2px 8px', borderRadius: 99, fontWeight: 700 }}>
                  ad-hoc override
                </span>
              )}
              <span style={{ flex: 1 }} />
              <button onClick={() => { setPathDraft(activePath); setEditingPath(true); }}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: C.orange, fontWeight: 600 }}>
                {customPath ? 'Edit path' : 'Use a different path'} →
              </button>
              {customPath && (
                <button onClick={() => setCustomPath(null)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: C.muted, fontWeight: 600 }}>
                  Reset to default
                </button>
              )}
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 10, fontWeight: 700, color: C.muted, textTransform: 'uppercase', letterSpacing: 1.5, flexShrink: 0 }}>Ad-hoc path</span>
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 6, padding: '7px 12px', background: '#fff', border: `1px solid ${C.border}`, borderRadius: 6 }}>
                <input value={pathDraft} onChange={(e) => setPathDraft(e.target.value)} autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') { setCustomPath(pathDraft.trim() || null); setEditingPath(false); }
                    if (e.key === 'Escape') { setEditingPath(false); }
                  }}
                  placeholder="M:\some\folder\path or \\server\share\dump.zip"
                  style={{ flex: 1, border: 'none', outline: 'none', fontFamily: MONO, fontSize: 12, color: C.text, background: 'transparent' }} />
                <span style={{ fontFamily: MONO, fontSize: 10, color: C.faint }}>↵ apply · esc cancel</span>
              </div>
              <button onClick={() => { setCustomPath(pathDraft.trim() || null); setEditingPath(false); }}
                style={{ padding: '8px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer', background: C.orange, color: '#fff', border: 'none', fontFamily: FONT }}>
                Apply
              </button>
              <button onClick={() => setEditingPath(false)}
                style={{ padding: '8px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer', background: '#fff', color: C.text, border: `1px solid ${C.border}`, fontFamily: FONT }}>
                Cancel
              </button>
            </div>
          )}
        </div>
      </Card>

      {/* Product picker — chosen up front, applies to the run */}
      <Card padding="14px 18px" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: C.muted, textTransform: 'uppercase', letterSpacing: 1.5 }}>Product</div>
          <div style={{ fontFamily: MONO, fontSize: 11, color: C.muted }}>Applies to whichever client you select below.</div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
          {D.products.map((p) => {
            const on = product === p.id;
            return (
              <div key={p.id} onClick={() => setProduct(p.id)}
                style={{ padding: '12px 14px', borderRadius: 8, border: `1.5px solid ${on ? C.orange : C.border}`, background: on ? C.orangeSoft : '#fff', cursor: 'pointer', position: 'relative' }}>
                {on && <div style={{ position: 'absolute', top: 8, right: 8, width: 14, height: 14, borderRadius: 99, background: C.orange, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon.check size={9} /></div>}
                <div style={{ fontSize: 13, fontWeight: 700, color: on ? C.orange : C.text }}>{p.name}</div>
                <div style={{ fontFamily: MONO, fontSize: 10, color: C.muted, marginTop: 4 }}>{p.modules} modules · ~{p.time} · {p.slides} slides</div>
              </div>
            );
          })}
        </div>
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, alignItems: 'start' }}>
        {/* Selected client profile */}
        <Card padding="18px 22px">
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginBottom: 14 }}>
            <Avatar csm={csm} size={48} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 18, fontWeight: 700, lineHeight: 1.15, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{pick.name}</div>
              <div style={{ fontFamily: MONO, fontSize: 11, color: C.muted, marginTop: 4 }}>{pick.id} · {pick.csm} · {pick.accounts.toLocaleString()} accounts · {pick.branches} branches</div>
              <div style={{ marginTop: 8 }}><StatusPill kind={pick.status} /></div>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 12 }}>
            <Meta label="IC rate" value="0.62%" />
            <Meta label="NSF fee" value="$32" />
            <Meta label="Reg E" value="Y" />
            <Meta label="Products" value="4 codes" />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <Meta label="Last run" value={pick.lastRun} />
            <Meta label="Next sched" value={pick.nextSched} />
          </div>
        </Card>

        {/* Pre-flight */}
        <Card padding="18px 22px" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Pre-flight</div>
          <div style={{ flex: 1, marginBottom: 12 }}>
            {[
              ['Raw dump present for May', true],
              ['Config valid (codes, mapping)', true],
              ['Workers free — 3/4 available', true],
            ].map(([label, ok], i, arr) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: i === arr.length-1 ? 'none' : `1px solid ${C.border}` }}>
                <div style={{ width: 20, height: 20, borderRadius: 99, background: ok ? C.greenSoft : C.amberSoft, color: ok ? C.green : C.amber, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  {ok ? <Icon.check size={11} /> : <Icon.warn size={11} />}
                </div>
                <div style={{ fontSize: 13 }}>{label}</div>
              </div>
            ))}
          </div>
          <div style={{ paddingTop: 12, borderTop: `1px solid ${C.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontFamily: MONO, fontSize: 9, color: C.muted, textTransform: 'uppercase', letterSpacing: 1.2 }}>Estimated</div>
              <div style={{ fontFamily: MONO, fontSize: 20, fontWeight: 700 }}>~{product_.time}</div>
            </div>
            <Btn onClick={() => startRun(pickId, product)}>
              <Icon.bolt size={12} /> Run now
            </Btn>
          </div>
        </Card>
      </div>
    </Page>
  );
}

function Field({ label, children }) {
  return <div><div style={{ fontSize: 10, fontWeight: 700, color: C.muted, textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 6 }}>{label}</div>{children}</div>;
}

function NativeSelect({ value, onChange, options }) {
  return (
    <div style={{ position: 'relative' }}>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        style={{ width: '100%', padding: '9px 30px 9px 12px', background: C.cardSoft, border: `1px solid ${C.border}`, borderRadius: 6, fontSize: 13, fontFamily: FONT, color: C.text, fontWeight: 500, appearance: 'none', cursor: 'pointer', outline: 'none' }}>
        {options.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
      </select>
      <span style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', color: C.muted, pointerEvents: 'none' }}><Icon.chev /></span>
    </div>
  );
}

function SearchInput({ value, onChange, placeholder }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', background: '#fff', border: `1px solid ${C.border}`, borderRadius: 6 }}>
      <span style={{ color: C.muted, display: 'flex', flexShrink: 0 }}><Icon.search size={13} /></span>
      <input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
        style={{ flex: 1, minWidth: 0, border: 'none', outline: 'none', background: 'transparent', fontSize: 13, color: C.text }} />
      {value && <button onClick={() => onChange('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: C.muted, display: 'flex' }}><Icon.x size={10} /></button>}
    </div>
  );
}

function Meta({ label, value }) {
  return (
    <div style={{ padding: '8px 10px', background: C.bg, borderRadius: 6 }}>
      <div style={{ fontSize: 9, fontWeight: 700, color: C.muted, textTransform: 'uppercase', letterSpacing: 1.2 }}>{label}</div>
      <div style={{ fontFamily: MONO, fontSize: 13, fontWeight: 600, marginTop: 2 }}>{value}</div>
    </div>
  );
}

// ─── IN-PROGRESS ───────────────────────────────────────────────────────
function InProgress() {
  const { D, runs, focusedRunId, setFocusedRunId, now, queueAnother, runAgain, activeRuns, setPage } = useApp();
  const run = runs.find(r => r.id === focusedRunId) || runs[runs.length - 1];

  if (!run) {
    return <Page><div style={{ padding: 60, textAlign: 'center', color: C.muted }}>No runs yet. <button onClick={() => setPage('run')} style={{ background: 'none', border: 'none', color: C.orange, fontWeight: 700, cursor: 'pointer' }}>Start one →</button></div></Page>;
  }

  const st = runState(run, now);
  const client = D.clients.find(c => c.id === run.clientId);
  const elapsed = now - run.startedAt;
  const eta = Math.max(0, TOTAL_MS - elapsed);

  // Branch into Done / Failure states once the run finishes
  if (st.status === 'done')  return <DoneState run={run} client={client} />;
  if (st.status === 'error') return <FailureDoneState run={run} client={client}
    onQueueAnother={queueAnother} onRunAgain={runAgain} onBack={() => setPage('dashboard')} />;

  return (
    <Page>
      {/* Run tabs (multi-run switcher) */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
        {[...activeRuns, ...runs.filter(r => r.status === 'done' && r.id === focusedRunId)].map((r) => {
          const on = r.id === run.id;
          const csm = D.csms.find(c => c.id === r.csm);
          const rc = D.clients.find(c => c.id === r.clientId);
          return (
            <button key={r.id} onClick={() => setFocusedRunId(r.id)}
              style={{ padding: '8px 12px', borderRadius: 8, background: on ? '#fff' : C.bgDeep, border: `1px solid ${on ? C.border : 'transparent'}`, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10, minWidth: 220 }}>
              <Avatar csm={csm} size={24} />
              <div style={{ textAlign: 'left', flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12.5, fontWeight: 700, lineHeight: 1.2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{rc.name}</div>
                <div style={{ fontFamily: MONO, fontSize: 10, color: C.muted, marginTop: 1 }}>{r.clientId} · {fmtMmss((r.finishedAt ?? now) - r.startedAt)}</div>
              </div>
              {on && r.status === 'running' && <span style={{ width: 6, height: 6, borderRadius: 99, background: C.orange, animation: 'pulse 1.6s ease-in-out infinite' }} />}
            </button>
          );
        })}
        <button onClick={queueAnother}
          style={{ padding: '8px 12px', borderRadius: 8, background: 'transparent', border: `1px dashed ${C.borderStrong}`, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, color: C.muted, fontSize: 12, fontWeight: 600 }}>
          + Queue another
        </button>
      </div>

      {/* Title + pipeline rail */}
      <Card padding="20px 24px" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20, gap: 16 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
              <StatusPill kind="running">Building</StatusPill>
              <div style={{ fontFamily: MONO, fontSize: 11, color: C.muted }}>{run.id}</div>
            </div>
            <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: -0.4, lineHeight: 1.1 }}>{client.name}</div>
            <div style={{ fontSize: 13, color: C.muted, marginTop: 5 }}>
              {run.clientId} · {productName(run.product)} · triggered by james.gilmore · started {fmtMmss(elapsed)} ago
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontFamily: MONO, fontSize: 10, color: C.muted, letterSpacing: 1.2, textTransform: 'uppercase' }}>Elapsed</div>
              <div style={{ fontFamily: MONO, fontSize: 28, fontWeight: 700, color: C.text, lineHeight: 1 }}>{fmtMmss(elapsed)}</div>
              <div style={{ fontFamily: MONO, fontSize: 10, color: C.muted, marginTop: 4 }}>≈ {fmtMmss(eta)} remaining</div>
            </div>
            <Btn kind="danger">Cancel run</Btn>
          </div>
        </div>

        <StageRail stages={D.stages} st={st} />
      </Card>

      {/* Activity timeline — full width (modules card folded into this) */}
      <Card padding={0} style={{ overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 14, fontWeight: 700 }}>Activity</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontFamily: MONO, fontSize: 11, color: C.muted }}>
            <ModuleCounter st={st} />
            <span>·</span>
            <span>Live · what's happening now</span>
          </div>
        </div>
        <BuildLog run={run} st={st} />
      </Card>
    </Page>
  );
}

function StageRail({ stages, st }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', width: '100%' }}>
      {stages.map((s, i) => {
        const state = i < st.stageIdx ? 'done' : i === st.stageIdx ? 'active' : 'idle';
        const c = state === 'done' ? C.green : state === 'active' ? C.orange : C.borderStrong;
        return (
          <React.Fragment key={s.id}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0, minWidth: 130 }}>
              <div style={{ position: 'relative', width: 30, height: 30 }}>
                <div style={{ position: 'absolute', inset: 0, borderRadius: 99, background: state === 'idle' ? '#fff' : c, border: `1.5px solid ${c}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
                  {state === 'done' && <Icon.check size={14} />}
                  {state === 'active' && <span style={{ width: 9, height: 9, borderRadius: 99, background: '#fff' }} />}
                  {state === 'idle' && <span style={{ fontFamily: MONO, fontSize: 12, color: C.muted }}>{i + 1}</span>}
                </div>
                {state === 'active' && (
                  <span style={{ position: 'absolute', inset: -4, borderRadius: 99, border: `1.5px solid ${c}`, animation: 'pulse 1.6s ease-in-out infinite' }} />
                )}
              </div>
              <div style={{ marginTop: 10, textAlign: 'center', maxWidth: 140, padding: '0 6px' }}>
                <div style={{ fontSize: 12.5, fontWeight: state === 'active' ? 700 : 600, color: state === 'idle' ? C.muted : C.text, lineHeight: 1.2 }}>{s.name}</div>
                <div style={{ fontFamily: MONO, fontSize: 10, color: state === 'done' ? C.green : state === 'active' ? C.orange : C.muted, marginTop: 4 }}>
                  {state === 'done' ? `${formatSec(STAGE_REAL[s.id])} ✓` : state === 'active' ? `${Math.round(st.progress * 100)}%` : `~ ${formatSec(STAGE_REAL[s.id])}`}
                </div>
              </div>
            </div>
            {i < stages.length - 1 && (
              <div style={{ flex: 1, height: 3, background: C.bgDeep, borderRadius: 2, marginTop: 14, overflow: 'hidden' }}>
                <div style={{
                  width: i < st.stageIdx ? '100%' : i === st.stageIdx ? `${st.progress * 100}%` : '0%',
                  height: '100%',
                  background: i < st.stageIdx ? C.green : C.orange,
                  transition: 'width .25s',
                }} />
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

function formatSec(s) { return s >= 60 ? `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}` : `${s}s`; }

// Module progress is faked from the analyze stage progress.
function moduleCount(st) {
  if (st.stageIdx < 2) return 0;
  if (st.stageIdx > 2) return 25;
  return Math.min(25, Math.round(st.progress * 25));
}

function ModuleCounter({ st }) {
  const done = moduleCount(st);
  return <div style={{ fontFamily: MONO, fontSize: 11, color: C.muted }}>{done} / 25 · {Math.round(done/25*100)}%</div>;
}

function ModuleList({ st }) {
  const D = MockData;
  const done = moduleCount(st);
  let runningTheme = null;
  let cum = 0;
  for (const t of D.themes) { cum += t.count; if (done < cum) { runningTheme = t.id; break; } }
  return D.themes.map((t, i) => {
    const start = D.themes.slice(0, i).reduce((s, x) => s + x.count, 0);
    const end = start + t.count;
    const themeState = done >= end ? 'done' : done > start ? 'active' : 'idle';
    const ic = themeState === 'done' ? C.green : themeState === 'active' ? C.orange : C.faint;
    return (
      <div key={t.id} style={{ display: 'grid', gridTemplateColumns: '14px 1fr 80px 60px', gap: 10, alignItems: 'center', padding: '10px 12px', borderRadius: 6, marginBottom: 4, background: themeState === 'idle' ? 'transparent' : C.cardSoft, border: `1px solid ${themeState === 'idle' ? 'transparent' : C.border}` }}>
        <div style={{ width: 10, height: 10, borderRadius: 99, background: ic, position: 'relative' }}>
          {themeState === 'active' && <div style={{ position: 'absolute', inset: -3, borderRadius: 99, border: `1.5px solid ${ic}`, opacity: 0.4, animation: 'pulse 1.6s ease-in-out infinite' }} />}
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>{t.name}</div>
          {themeState === 'active' && <div style={{ fontFamily: MONO, fontSize: 10.5, color: C.orange, marginTop: 2 }}>{t.id}_response_rate</div>}
        </div>
        <div style={{ fontFamily: MONO, fontSize: 11, color: C.muted }}>{t.count} mods</div>
        <div style={{ fontFamily: MONO, fontSize: 10, fontWeight: 700, color: ic, textAlign: 'right', textTransform: 'uppercase', letterSpacing: 0.8 }}>
          {themeState === 'done' ? '✓ done' : themeState === 'active' ? '● run' : 'queued'}
        </div>
      </div>
    );
  });
}

// Humanized timeline of milestones — non-technical operators read this.
// The raw technical log sits behind a disclosure below.
function BuildLog({ run, st }) {
  const D = MockData;
  const t = (offsetMs) => {
    const d = new Date(run.startedAt + offsetMs);
    let h = d.getHours(); const m = d.getMinutes();
    const ampm = h >= 12 ? 'PM' : 'AM';
    h = h % 12 || 12;
    return `${h}:${String(m).padStart(2, '0')} ${ampm}`;
  };

  // ── Build a humanized event list keyed off the current stage progress.
  const events = [];
  events.push({ k: 'start', time: t(0), title: 'Started the run', subtitle: `${MockData.products.find(p => p.id === run.product)?.name} · client ${run.clientId}`, status: 'done' });

  // Stage 1 — read
  if (st.stageIdx >= 1 || (st.stageIdx === 0 && st.progress > 0.85)) {
    events.push({ k: 'read-done', time: t(STAGE_CUM.read), title: 'Loaded your data', subtitle: '4 files · 2.1 GB · 4,218 accounts', status: 'done' });
  } else if (st.stageIdx === 0) {
    events.push({ k: 'read', time: t(0), title: 'Reading your data files', subtitle: '4 files · 2.1 GB', status: 'active' });
  }

  // Stage 2 — prep
  if (st.stageIdx >= 2) {
    events.push({ k: 'prep-done', time: t(STAGE_CUM.prep), title: 'Pipeline ready', subtitle: 'Validated codes and branch mapping', status: 'done' });
  } else if (st.stageIdx === 1) {
    events.push({ k: 'prep', time: t(STAGE_CUM.read), title: 'Setting up the analyses', subtitle: 'Validating client config', status: 'active' });
  }

  // Stage 3 — analyze (themes complete as modules pass)
  if (st.stageIdx >= 2) {
    const done = moduleCount(st);
    events.push({ k: 'analyze-start', time: t(STAGE_CUM.prep + 50), title: 'Running 25 analytics modules', subtitle: 'Across 7 themes', status: st.stageIdx > 2 ? 'done' : 'active', strong: true });

    // Emit a milestone for each completed theme
    let cum = 0;
    for (const theme of D.themes) {
      cum += theme.count;
      if (done >= cum) {
        events.push({ k: `theme-${theme.id}`, time: t(STAGE_CUM.prep + 100 + (cum / 25) * STAGE_MS.analyze), title: `${theme.name} — done`, subtitle: `${theme.count} module${theme.count === 1 ? '' : 's'}`, status: 'done' });
      } else if (done > cum - theme.count) {
        events.push({ k: `theme-${theme.id}-active`, time: t(Date.now() - run.startedAt - 1500), title: `Working on ${theme.name}`, subtitle: `Module ${done} of 25`, status: 'active' });
        break; // only the current theme is active
      }
    }
  }

  // Stage 4 — deck
  if (st.stageIdx >= 4) {
    events.push({ k: 'deck-done', time: t(STAGE_CUM.deck), title: 'Built your PowerPoint', subtitle: '78 slides · 142 charts', status: 'done' });
  } else if (st.stageIdx === 3) {
    events.push({ k: 'deck', time: t(STAGE_CUM.analyze + 50), title: 'Composing the PowerPoint', subtitle: 'Placing slides and charts', status: 'active' });
  }

  // Stage 5 — finalize
  if (st.status === 'done') {
    events.push({ k: 'finalize-done', time: t(STAGE_CUM.finalize), title: 'All done — files are ready', subtitle: 'Saved to network drive', status: 'done', strong: true });
  } else if (st.stageIdx === 4) {
    events.push({ k: 'finalize', time: t(STAGE_CUM.deck + 30), title: 'Saving your files', subtitle: 'Writing to the network drive', status: 'active' });
  }

  // Auto-scroll on new events
  const ref = React.useRef(null);
  React.useEffect(() => { if (ref.current) ref.current.scrollTop = ref.current.scrollHeight; }, [events.length, st.progress]);

  // ── Build the raw technical log (kept behind a disclosure)
  let rawLines = [];
  const ts = (offsetMs) => new Date(run.startedAt + offsetMs).toTimeString().slice(0, 8);
  if (window.LIVE && run.liveState?.log) {
    // Real backend log lines. Color-code by simple keyword heuristic.
    const classify = (line) => {
      const l = line.toLowerCase();
      if (/error|failed|exception|traceback/.test(l)) return 'err';
      if (/warn/.test(l)) return 'warn';
      if (/complete|done|saved|ok/.test(l)) return 'ok';
      if (/module\s+\d+\/\d+/.test(l)) return 'run';
      return 'dim';
    };
    rawLines = run.liveState.log.map((line) => {
      // Try to lift the timestamp out of "2026-05-15 17:59:09.769 | INFO ..." style;
      // otherwise fall back to relative elapsed.
      const m = String(line).match(/(\d{2}:\d{2}:\d{2})/);
      return [m ? m[1] : ts(Date.now() - run.startedAt), classify(line), line];
    });
  } else {
    rawLines.push([ts(0), 'info', `Run ${run.id} dispatched · client=${run.clientId} product=${run.product}`]);
    rawLines.push([ts(50), 'ok', `stage[read] reading 4 ODD files (2.1 GB)…`]);
    if (st.stageIdx >= 1 || (st.stageIdx === 0 && st.progress > 0.9)) {
      rawLines.push([ts(STAGE_CUM.read), 'ok', `stage[read] complete · 4,218 accounts loaded`]);
      rawLines.push([ts(STAGE_CUM.read + 10), 'ok', `stage[prep] starting retrieve_data`]);
    }
    if (st.stageIdx >= 2) {
      rawLines.push([ts(STAGE_CUM.prep), 'ok', `stage[prep] complete`]);
      rawLines.push([ts(STAGE_CUM.prep + 10), 'ok', `stage[analyze] starting · 25 modules across 7 themes`]);
      const done = moduleCount(st);
      for (let i = 0; i < Math.min(done, 5); i++) {
        rawLines.push([ts(STAGE_CUM.prep + 200 + i * 600), 'dim', `Module ${String(i+1).padStart(2,'0')}/25: overview_${['summary','account','branch','behavior'][i % 4]} · ok (${Math.round(80 + Math.random()*350)}ms)`]);
      }
      if (done > 5 && done < 25) {
        rawLines.push([ts(STAGE_CUM.prep + 3500), 'dim', `… ${done - 5} more modules complete …`]);
        rawLines.push([ts(Date.now() - run.startedAt - 1000), 'run', `Module ${String(done).padStart(2,'0')}/25: mailer_response_rate · in progress`]);
      }
      if (done >= 25) rawLines.push([ts(STAGE_CUM.analyze), 'ok', `stage[analyze] complete · 25 modules`]);
    }
    if (st.stageIdx >= 3) {
      rawLines.push([ts(STAGE_CUM.analyze + 10), 'ok', `stage[deck] starting · composing slides`]);
      if (st.stageIdx > 3) rawLines.push([ts(STAGE_CUM.deck), 'ok', `stage[deck] complete · 78 slides, 142 charts`]);
    }
    if (st.stageIdx >= 4) {
      rawLines.push([ts(STAGE_CUM.deck + 10), 'ok', `stage[finalize] writing outputs`]);
      if (st.status === 'done') rawLines.push([ts(STAGE_CUM.finalize), 'ok', `Run complete · 4 files saved`]);
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', maxHeight: 420 }}>
      {/* Humanized timeline */}
      <div ref={ref} style={{ flex: 1, overflow: 'auto', padding: '8px 20px 4px' }}>
        {events.map((ev, i) => <TimelineEvent key={ev.k} ev={ev} isLast={i === events.length - 1} />)}
      </div>

      {/* Technical disclosure */}
      <details style={{ borderTop: `1px solid ${C.border}`, padding: '12px 20px', background: C.cardSoft }}>
        <summary style={{ cursor: 'pointer', fontSize: 12, fontWeight: 600, color: C.muted, listStyle: 'none', display: 'flex', alignItems: 'center', gap: 8, userSelect: 'none' }}
          onMouseEnter={(e) => (e.currentTarget.style.color = C.text)}
          onMouseLeave={(e) => (e.currentTarget.style.color = C.muted)}>
          <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 18, height: 18, borderRadius: 99, background: C.bgDeep, color: C.muted, fontFamily: MONO, fontSize: 11, fontWeight: 700 }}>›</span>
          <span>For the curious — show the technical log</span>
        </summary>
        <div style={{ marginTop: 12, padding: '12px 14px', background: '#1A1A1A', borderRadius: 6, fontFamily: MONO, fontSize: 11, lineHeight: 1.7, color: '#c4bfb0', maxHeight: 220, overflow: 'auto' }}>
          {rawLines.map(([t, lvl, msg], i) => <LogLine key={i} t={t} lvl={lvl}>{msg}</LogLine>)}
        </div>
      </details>
    </div>
  );
}

// One row of the humanized timeline.
function TimelineEvent({ ev, isLast }) {
  const accent = ev.status === 'done' ? C.green : ev.status === 'active' ? C.orange : ev.status === 'failed' ? C.red : C.faint;
  const bg     = ev.status === 'done' ? C.greenSoft : ev.status === 'active' ? C.orangeSoft : C.bgDeep;
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '24px 1fr', gap: 14, paddingBottom: isLast ? 8 : 0 }}>
      {/* Rail */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative' }}>
        <div style={{ position: 'relative', width: 18, height: 18, marginTop: 4 }}>
          <div style={{ position: 'absolute', inset: 0, borderRadius: 99, background: ev.status === 'idle' ? C.card : accent, border: `2px solid ${accent}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {ev.status === 'done' && <span style={{ color: '#fff', display: 'flex' }}><Icon.check size={9} /></span>}
            {ev.status === 'active' && <span style={{ width: 5, height: 5, borderRadius: 99, background: '#fff' }} />}
          </div>
          {ev.status === 'active' && (
            <span style={{ position: 'absolute', inset: -3, borderRadius: 99, border: `1.5px solid ${accent}`, animation: 'pulse 1.6s ease-in-out infinite', opacity: 0.5 }} />
          )}
        </div>
        {!isLast && <div style={{ flex: 1, width: 2, background: ev.status === 'done' ? C.green : C.border, marginTop: 2, marginBottom: 2, minHeight: 16 }} />}
      </div>

      {/* Content */}
      <div style={{ paddingBottom: isLast ? 0 : 16, paddingTop: 2 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, marginBottom: 3 }}>
          <div style={{ fontSize: ev.strong ? 14 : 13.5, fontWeight: ev.strong ? 700 : 600, color: ev.status === 'idle' ? C.muted : C.text, lineHeight: 1.25 }}>
            {ev.title}
          </div>
          <div style={{ fontFamily: MONO, fontSize: 10.5, color: C.muted, flexShrink: 0 }}>{ev.time}</div>
        </div>
        {ev.subtitle && (
          <div style={{ fontSize: 12, color: C.muted, lineHeight: 1.4 }}>{ev.subtitle}</div>
        )}
        {ev.status === 'active' && (
          <div style={{ display: 'inline-block', marginTop: 6, padding: '2px 8px', background: bg, borderRadius: 99, fontFamily: MONO, fontSize: 10, fontWeight: 700, color: accent, textTransform: 'uppercase', letterSpacing: 0.8 }}>
            in progress
          </div>
        )}
      </div>
    </div>
  );
}

function now() { return Date.now(); }

function LogLine({ t, lvl, children }) {
  const color = lvl === 'ok' ? C.green : lvl === 'run' ? C.orange : lvl === 'warn' ? C.amber : lvl === 'error' ? C.red : C.text;
  const prefix = lvl === 'ok' ? '✓' : lvl === 'run' ? '▶' : lvl === 'warn' ? '⚠' : lvl === 'error' ? '✗' : ' ';
  return (
    <div style={{ display: 'flex', gap: 10 }}>
      <span style={{ color: C.faint, flexShrink: 0 }}>{t}</span>
      <span style={{ color, width: 12, textAlign: 'center', fontWeight: lvl === 'run' ? 700 : 400, flexShrink: 0 }}>{prefix}</span>
      <span style={{ color: lvl === 'dim' ? C.muted : C.text, flex: 1 }}>{children}</span>
    </div>
  );
}

// ─── DONE STATE ────────────────────────────────────────────────────────
function DoneState({ run, client }) {
  const { queueAnother, runAgain, setPage, now } = useApp();
  const duration = run.finishedAt - run.startedAt;
  const st = runState(run, now);

  // Outputs: real backend listing in LIVE mode.
  const [outputs, setOutputs] = React.useState(null);
  React.useEffect(() => {
    if (!window.LIVE) return;
    const csm = run.csm || (MockData.csms[0]?.id) || '';
    const month = new Date().toISOString().slice(0, 7).replace('-', '.');
    window.api.getOutputs(csm, month, run.clientId).then(setOutputs).catch((e) => {
      console.error('[velocity] getOutputs failed:', e);
      setOutputs([]);
    });
  }, []);

  // Group outputs by category for the download grid.
  const downloads = React.useMemo(() => {
    if (!window.LIVE) {
      return [
        { ext: 'PPTX', name: `${client.id}_${productName(run.product)}_2026.05.pptx`, size: '14.2 MB' },
        { ext: 'XLSX', name: `${client.id}_data_2026.05.xlsx`, size: '3.8 MB' },
        { ext: 'PDF',  name: `${client.id}_run_report_2026.05.pdf`, size: '412 KB' },
      ];
    }
    if (!outputs) return [];
    // Surface PPTX and XLSX/JSON files; skip per-chart PNGs (too noisy here).
    return outputs
      .filter((f) => f.type === 'pptx' || f.type === 'xlsx' || f.type === 'json')
      .map((f) => ({ ext: f.type.toUpperCase(), name: f.name, size: `${f.size_mb} MB`, href: window.api.downloadUrl(f.path) }));
  }, [outputs]);

  // Slide count derived from manifest if available; otherwise unknown.
  const slideCount = window.LIVE ? '—' : '78';
  const sheetCount = window.LIVE ? (outputs?.filter((f) => f.type === 'xlsx').length ?? '—') : '6';

  return (
    <Page>
      <Card padding={0} style={{ overflow: 'hidden', marginBottom: 16 }}>
        <div style={{ padding: '32px 36px', background: 'linear-gradient(180deg, #fff 0%, #fafaf6 100%)', borderBottom: `1px solid ${C.border}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 6 }}>
            <div style={{ width: 60, height: 60, borderRadius: 99, background: C.green, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Icon.check size={32} />
            </div>
            <div>
              <Kicker color={C.green}>Run complete</Kicker>
              <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: -0.4, marginTop: 4 }}>Report ready — {client.name}</div>
              <div style={{ fontSize: 13, color: C.muted, marginTop: 4 }}>Generated in {fmtMmss(duration)} · {productName(run.product)}</div>
            </div>
          </div>
        </div>
        <div style={{ padding: '24px 36px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 14, marginBottom: 24 }}>
            <DoneStat color={C.green}   label="Slides succeeded" value={String(slideCount)} icon="✓" />
            <DoneStat color={C.amber}   label="No-chart slides"  value="0"  icon="⚠" />
            <DoneStat color={C.red}     label="Slides failed"    value="0"  icon="✗" />
            <DoneStat color={C.text}    label="Excel sheets"     value={String(sheetCount)} />
            <DoneStat color={C.text}    label="Total time"       value={fmtMmss(duration)} />
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>Downloads</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 24 }}>
            {downloads.length === 0 && window.LIVE && outputs == null && (
              <div style={{ gridColumn: '1 / -1', color: C.muted, fontSize: 12, padding: '12px 0' }}>Loading files…</div>
            )}
            {downloads.length === 0 && window.LIVE && outputs != null && (
              <div style={{ gridColumn: '1 / -1', color: C.muted, fontSize: 12, padding: '12px 0' }}>No output files found yet.</div>
            )}
            {downloads.map((d, i) => <DownloadCard key={i} {...d} />)}
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <Btn onClick={queueAnother}>+ Run another report</Btn>
            <Btn kind="ghost" onClick={() => setPage('dashboard')}>Back to dashboard</Btn>
            <Btn kind="ghost" onClick={() => runAgain(run.clientId, run.product)}>↻ Run this again</Btn>
          </div>
        </div>
      </Card>

      {/* Activity timeline for the completed run */}
      <Card padding={0} style={{ overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 14, fontWeight: 700 }}>Activity</div>
          <div style={{ fontFamily: MONO, fontSize: 11, color: C.muted }}>Full timeline · technical log below</div>
        </div>
        <BuildLog run={run} st={st} />
      </Card>
    </Page>
  );
}

function DoneStat({ color, label, value, icon }) {
  return (
    <div style={{ background: C.cardSoft, borderRadius: 8, padding: '12px 14px', borderLeft: `3px solid ${color}` }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
        <div style={{ fontFamily: MONO, fontSize: 24, fontWeight: 700, color, lineHeight: 1 }}>{value}</div>
        {icon && <span style={{ color, fontSize: 14 }}>{icon}</span>}
      </div>
      <div style={{ fontSize: 10, fontWeight: 700, color: C.muted, textTransform: 'uppercase', letterSpacing: 1, marginTop: 6 }}>{label}</div>
    </div>
  );
}

function DownloadCard({ ext, name, size, href }) {
  const Tag = href ? 'a' : 'div';
  const linkProps = href ? { href, target: '_blank', rel: 'noopener noreferrer' } : {};
  return (
    <Tag {...linkProps}
      style={{ background: C.cardSoft, border: `1px solid ${C.border}`, borderRadius: 8, padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer', transition: 'border-color .15s', textDecoration: 'none', color: 'inherit' }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = C.orange)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = C.border)}>
      <div style={{ fontFamily: MONO, fontSize: 11, fontWeight: 700, color: C.orange, background: C.orangeSoft, padding: '6px 10px', borderRadius: 6 }}>{ext}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12.5, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</div>
        <div style={{ fontFamily: MONO, fontSize: 10, color: C.muted, marginTop: 2 }}>{size}</div>
      </div>
      <span style={{ color: C.muted, display: 'flex' }}><Icon.download size={14} /></span>
    </Tag>
  );
}

// ─── LIBRARY ───────────────────────────────────────────────────────────
function Library() {
  const { libTab, setLibTab, schedView, setSchedView, setBulkOpen, D } = useApp();
  const monthLabel = React.useMemo(() => {
    const d = new Date();
    return d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  }, []);
  const schedCount = window.LIVE ? (D.schedules?.length || 0) : 13;
  const recentCount = window.LIVE ? (D.recent?.length || 0) : null;
  const scheduleSub = window.LIVE
    ? `${schedCount} active schedule${schedCount === 1 ? '' : 's'} · auto-fires daily at 06:00`
    : '13 active schedules · 71 runs queued · auto-fires daily at 06:00';
  const historySub = window.LIVE
    ? `All runs across all CSMs · ${recentCount} record${recentCount === 1 ? '' : 's'}`
    : 'All runs across all CSMs · last 30 days';
  return (
    <Page>
      <PageHead
        kicker={`Library · ${libTab === 'schedules' ? 'Schedules' : 'History'}`}
        title={libTab === 'schedules' ? monthLabel : 'Run history'}
        sub={libTab === 'schedules' ? scheduleSub : historySub}
        right={<div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <div style={{ display: 'inline-flex', padding: 3, background: C.bgDeep, borderRadius: 7, border: `1px solid ${C.border}`, marginRight: 8 }}>
            <SegBtn on={libTab==='schedules'} onClick={() => setLibTab('schedules')}><Icon.calendar size={11} /> Schedules</SegBtn>
            <SegBtn on={libTab==='history'}   onClick={() => setLibTab('history')}>History</SegBtn>
          </div>
          {libTab === 'schedules' && <React.Fragment>
            <div style={{ display: 'inline-flex', padding: 3, background: C.bgDeep, borderRadius: 7, border: `1px solid ${C.border}` }}>
              <SegBtn on={schedView==='calendar'} onClick={() => setSchedView('calendar')}>Calendar</SegBtn>
              <SegBtn on={schedView==='gantt'}    onClick={() => setSchedView('gantt')}>Gantt</SegBtn>
            </div>
            <Btn kind="ghost" onClick={() => setBulkOpen(true)}><Icon.bolt size={11} /> Bulk schedule</Btn>
            <Btn kind="ghost">+ New schedule</Btn>
          </React.Fragment>}
        </div>}
      />

      {libTab === 'schedules' ? (schedView === 'gantt' ? <ScheduleGantt /> : <ScheduleCalendar />) : <HistoryView />}
    </Page>
  );
}

function SegBtn({ on, onClick, children }) {
  return (
    <button onClick={onClick}
      style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '5px 11px', borderRadius: 5, border: 'none',
        background: on ? '#fff' : 'transparent', color: on ? C.text : C.muted,
        fontFamily: FONT, fontSize: 11.5, fontWeight: 600, cursor: 'pointer',
        boxShadow: on ? '0 1px 2px rgba(0,0,0,0.06)' : 'none' }}>
      {children}
    </button>
  );
}

function ScheduleCalendar() {
  const D = MockData;
  // Derive month layout from today's actual date.
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth();
  const todayDay = today.getDate();
  const firstDow = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const cells = Array.from({ length: firstDow }, () => null).concat(days);
  while (cells.length % 7 !== 0) cells.push(null);

  // Day -> [client...] from real schedules in LIVE mode, falling back to
  // the nextSched string ("Jun 5") parsed off enriched clients otherwise.
  const schedFor = (d) => {
    if (window.LIVE) {
      const ids = (D.schedules || []).filter((s) => Number(s.day) === d).map((s) => String(s.client_id));
      return ids.map((id) => D.clients.find((c) => c.id === id))
        .filter(Boolean);
    }
    return D.clients.filter((c) => {
      const m = String(c.nextSched || '').match(/(\d+)/);
      return m && Number(m[1]) === d;
    });
  };
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 16, alignItems: 'start' }}>
      <Card padding={16} style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', marginBottom: 10 }}>
          {['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map(d => (
            <div key={d} style={{ fontSize: 10, fontWeight: 700, color: C.muted, textTransform: 'uppercase', letterSpacing: 1.4, padding: '0 6px 10px', borderBottom: `1px solid ${C.border}` }}>{d}</div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 5, gridAutoRows: 'minmax(96px, 1fr)' }}>
          {cells.map((d, i) => {
            if (!d) return <div key={i} />;
            const runs = schedFor(d);
            const isToday = d === todayDay;
            return (
              <div key={i} style={{ background: C.cardSoft, borderRadius: 6, padding: 8, border: isToday ? `1.5px solid ${C.orange}` : `1px solid ${C.border}`, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 5 }}>
                  <div style={{ fontFamily: MONO, fontSize: 11, fontWeight: 700, color: isToday ? C.orange : C.muted }}>{d}</div>
                  {runs.length > 0 && <div style={{ fontFamily: MONO, fontSize: 9, color: C.muted }}>{runs.length}</div>}
                </div>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 3, minHeight: 0 }}>
                  {runs.slice(0, 3).map((c) => {
                    const csm = D.csms.find(x => x.id === c.csm);
                    return (
                      <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '3px 6px', borderRadius: 3, background: '#fff', border: `1px solid ${C.border}`, fontSize: 10 }}>
                        <div style={{ width: 5, height: 5, borderRadius: 99, background: csm?.color || C.muted, flexShrink: 0 }} />
                        <div style={{ fontFamily: MONO, color: C.muted, flexShrink: 0 }}>{c.id}</div>
                      </div>
                    );
                  })}
                  {runs.length > 3 && <div style={{ fontFamily: MONO, fontSize: 9, color: C.muted, padding: '2px 4px' }}>+{runs.length - 3} more</div>}
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <Card padding={16}>
        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>By CSM</div>
        {D.csms.map((csm) => {
          const cs = D.clients.filter(c => c.csm === csm.id);
          return (
            <div key={csm.id} style={{ padding: '10px 0', borderBottom: `1px solid ${C.border}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                <Avatar csm={csm} size={24} />
                <div style={{ flex: 1, fontSize: 13, fontWeight: 700 }}>{csm.name}</div>
                <div style={{ fontFamily: MONO, fontSize: 11, color: C.muted }}>{cs.length}</div>
              </div>
              <div style={{ display: 'flex', gap: 3 }}>
                {cs.map(c => (
                  <div key={c.id} style={{ flex: 1, height: 4, background: csm.color, opacity: 0.4 + 0.15 * (c.id.charCodeAt(2) % 4), borderRadius: 1 }} />
                ))}
              </div>
            </div>
          );
        })}
        <div style={{ paddingTop: 14, marginTop: 8 }}>
          <Btn kind="ghost" style={{ width: '100%', justifyContent: 'center' }}>
            <Icon.calendar size={13} /> Schedule all of CSM's clients
          </Btn>
        </div>
      </Card>
    </div>
  );
}

function ScheduleGantt() {
  const D = MockData;
  const today = new Date();
  const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();
  const todayDay = today.getDate();
  // In LIVE mode pull day from real schedules; otherwise fall back to client.nextSched.
  const scheduleDayFor = (clientId) => {
    if (window.LIVE) {
      const s = (D.schedules || []).find((s) => String(s.client_id) === String(clientId));
      return s ? Number(s.day) : null;
    }
    const c = D.clients.find((c) => c.id === clientId);
    const m = String(c?.nextSched || '').match(/(\d+)/);
    return m ? Number(m[1]) : null;
  };
  // In LIVE mode only show clients that actually have schedules; otherwise show all.
  const visibleClients = window.LIVE
    ? D.clients.filter((c) => scheduleDayFor(c.id) != null)
    : D.clients;
  return (
    <Card padding={0} style={{ overflow: 'hidden' }}>
      <div style={{ padding: '12px 18px', borderBottom: `1px solid ${C.border}`, display: 'grid', gridTemplateColumns: `220px repeat(${daysInMonth}, 1fr)`, alignItems: 'center', background: C.cardSoft }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: C.muted, textTransform: 'uppercase', letterSpacing: 1.4 }}>Client</div>
        {Array.from({ length: daysInMonth }, (_, i) => (
          <div key={i} style={{ fontFamily: MONO, fontSize: 10, color: (i + 1) === todayDay ? C.orange : C.muted, textAlign: 'center', fontWeight: (i + 1) === todayDay ? 700 : 500 }}>{i + 1}</div>
        ))}
      </div>
      {visibleClients.length === 0 && (
        <div style={{ padding: '40px 20px', textAlign: 'center', color: C.muted, fontSize: 13 }}>
          No schedules yet. Use <strong>+ New schedule</strong> to add one.
        </div>
      )}
      <div style={{ maxHeight: 540, overflow: 'auto' }}>
        {visibleClients.map((c) => {
          const day = scheduleDayFor(c.id);
          const csm = D.csms.find(x => x.id === c.csm);
          return (
            <div key={c.id} style={{ display: 'grid', gridTemplateColumns: `220px repeat(${daysInMonth}, 1fr)`, alignItems: 'center', borderBottom: `1px solid ${C.border}`, paddingLeft: 18, paddingRight: 18, minHeight: 48 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingRight: 12 }}>
                {csm && <Avatar csm={csm} size={22} />}
                <div style={{ overflow: 'hidden' }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.name}</div>
                  <div style={{ fontFamily: MONO, fontSize: 10, color: C.muted, marginTop: 1 }}>{c.id} · {c.product || '—'}</div>
                </div>
              </div>
              {Array.from({ length: daysInMonth }, (_, i) => {
                const d = i + 1;
                const isRun = d === day;
                const isToday = d === todayDay;
                return (
                  <div key={i} style={{ height: '100%', borderLeft: `1px solid ${C.border}`, position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', background: isToday ? 'rgba(241,93,34,0.05)' : 'transparent' }}>
                    {isRun && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '3px 8px', background: csm?.color || C.muted, color: '#fff', borderRadius: 99, fontFamily: MONO, fontSize: 9.5, fontWeight: 700 }}>
                        {(c.product || '?').split(' ')[0].slice(0, 3).toUpperCase()}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function HistoryView() {
  const { D, runAgain, finishedRuns } = useApp();
  const parseDur = (s) => {
    if (!s || typeof s !== 'string') return 0;
    let secs = 0;
    const h = s.match(/(\d+)\s*h/); if (h) secs += +h[1] * 3600;
    const m = s.match(/(\d+)\s*m/); if (m) secs += +m[1] * 60;
    const sec = s.match(/(\d+)\s*s/); if (sec) secs += +sec[1];
    return secs * 1000;
  };
  const relTime = (ts) => {
    const m = String(ts || '').match(/(\d{4})[-_.](\d{2})[-_.](\d{2})/);
    if (!m) return ts || '—';
    return new Date(`${m[1]}-${m[2]}-${m[3]}`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  };

  let all;
  if (window.LIVE) {
    all = (D.recent || []).map((r) => ({
      client: D.clients.find((c) => c.id === String(r.client_id)) || { id: r.client_id, name: r.client_name || `Client ${r.client_id}`, csm: r.csm },
      product: r.product || '',
      duration: parseDur(r.duration),
      finished: relTime(r.timestamp),
      status: r.status === 'error' ? 'error' : r.status === 'warning' ? 'warning' : 'done',
    }));
  } else {
    all = [
      ...finishedRuns.map(r => ({ client: D.clients.find(c => c.id === r.clientId), product: r.product, duration: r.finishedAt - r.startedAt, finished: 'just now', status: 'done' })),
      { client: D.clients[1],  product: 'ars_full', duration: 705*1000, finished: '2h ago',  status: 'done' },
      { client: D.clients[7],  product: 'ars_full', duration: 728*1000, finished: '3h ago',  status: 'done' },
      { client: D.clients[6],  product: 'txn',      duration: 374*1000, finished: '4h ago',  status: 'warning' },
      { client: D.clients[9],  product: 'deposits', duration: 38*1000,  finished: '5h ago',  status: 'error' },
      { client: D.clients[12], product: 'ars_full', duration: 711*1000, finished: '6h ago',  status: 'done' },
      { client: D.clients[5],  product: 'ars_full', duration: 692*1000, finished: '8h ago',  status: 'done' },
      { client: D.clients[11], product: 'combined', duration: 542*1000, finished: '9h ago',  status: 'done' },
      { client: D.clients[3],  product: 'combined', duration: 538*1000, finished: '11h ago', status: 'done' },
      { client: D.clients[2],  product: 'txn',      duration: 368*1000, finished: '1d ago',  status: 'done' },
      { client: D.clients[8],  product: 'deposits', duration: 234*1000, finished: '1d ago',  status: 'done' },
    ];
  }
  return (
    <Card padding={0}>
      <div style={{ display: 'grid', gridTemplateColumns: '90px 1.5fr 1fr 100px 100px 100px 90px', padding: '10px 22px', borderBottom: `1px solid ${C.border}`, background: C.cardSoft, fontSize: 10, fontWeight: 700, color: C.muted, textTransform: 'uppercase', letterSpacing: 1 }}>
        <div>Status</div><div>Client</div><div>Product</div><div>CSM</div><div>Duration</div><div>Finished</div><div></div>
      </div>
      {all.map((r, i, arr) => (
        <div key={i} className={r.finished === 'just now' ? 'flash-in' : ''}
          style={{ display: 'grid', gridTemplateColumns: '90px 1.5fr 1fr 100px 100px 100px 90px', alignItems: 'center', padding: '12px 22px', borderBottom: i < arr.length-1 ? `1px solid ${C.border}` : 'none', fontSize: 13 }}>
          <div><StatusPill kind={r.status === 'done' ? 'done' : r.status === 'warning' ? 'warning' : 'error'}>{r.status}</StatusPill></div>
          <div><div style={{ fontWeight: 600 }}>{r.client?.name}</div><div style={{ fontFamily: MONO, fontSize: 11, color: C.muted, marginTop: 2 }}>{r.client?.id}</div></div>
          <div style={{ fontSize: 12, color: C.muted }}>{productName(r.product)}</div>
          <div style={{ fontFamily: MONO, fontSize: 12, color: C.muted }}>{r.client?.csm}</div>
          <div style={{ fontFamily: MONO, fontSize: 12 }}>{fmtMmss(r.duration)}</div>
          <div style={{ fontFamily: MONO, fontSize: 12, color: C.muted }}>{r.finished}</div>
          <div style={{ textAlign: 'right' }}>
            <button onClick={() => runAgain(r.client?.id, r.product)}
              style={{ background: 'none', border: `1px solid ${C.border}`, padding: '5px 11px', borderRadius: 4, fontSize: 11, color: C.text, cursor: 'pointer', fontFamily: MONO }}>↻ rerun</button>
          </div>
        </div>
      ))}
    </Card>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
