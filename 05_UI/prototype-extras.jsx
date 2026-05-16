// prototype-extras.jsx — Command palette, bulk schedule modal, failure done state.
// Components are exposed on window so prototype.jsx can mount them. Load AFTER
// shared.jsx but BEFORE prototype.jsx in prototype.html.

const xC = {
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
const xFONT = "'Montserrat', system-ui, sans-serif";
const xMONO = "'IBM Plex Mono', ui-monospace, monospace";

// Map a client-config product NAME → product id for runs.
function productIdFor(name) {
  return ({ 'ARS Full Suite': 'ars_full', 'Transaction': 'txn', 'Combined': 'combined', 'Deposits': 'deposits' })[name] || 'ars_full';
}

// Inject modal overlay keyframes once.
if (typeof document !== 'undefined' && !document.getElementById('xExtraKf')) {
  const s = document.createElement('style');
  s.id = 'xExtraKf';
  s.textContent = `
    @keyframes xFadeIn { from { opacity: 0; } to { opacity: 1; } }
    @keyframes xSlideIn { from { opacity: 0; transform: translateY(-8px) scale(.97); } to { opacity: 1; transform: translateY(0) scale(1); } }
    .x-overlay { animation: xFadeIn .15s ease-out; }
    .x-modal   { animation: xSlideIn .18s cubic-bezier(.2,.7,.3,1); }
  `;
  document.head.appendChild(s);
}

// ─── COMMAND PALETTE ───────────────────────────────────────────────────
window.CommandPalette = function CommandPalette({ open, onClose, onAction }) {
  const [query, setQuery] = React.useState('');
  const [cursor, setCursor] = React.useState(0);
  const inputRef = React.useRef(null);
  const listRef = React.useRef(null);

  React.useEffect(() => {
    if (open) {
      setQuery(''); setCursor(0);
      // Wait a tick for the input to mount, then focus
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  // Keep cursor in view
  React.useEffect(() => {
    if (!listRef.current) return;
    const el = listRef.current.children[cursor];
    if (el) el.scrollIntoView({ block: 'nearest' });
  }, [cursor]);

  if (!open) return null;

  const D = MockData;
  const allCommands = [
    { id: 'go-dash', label: 'Go to Dashboard',     sub: 'Mission Control',                       group: 'Navigate', icon: '⌂', action: { type: 'goto', page: 'dashboard' } },
    { id: 'go-run',  label: 'Go to Run Studio',    sub: 'Queue an ad-hoc run',                   group: 'Navigate', icon: '▶', action: { type: 'goto', page: 'run' } },
    { id: 'go-lib',  label: 'Go to Library',       sub: 'Schedules and history',                 group: 'Navigate', icon: '☰', action: { type: 'goto', page: 'library' } },
    { id: 'bulk',    label: 'Bulk schedule a roster…', sub: 'Subscribe a CSM\'s whole client list', group: 'Actions',  icon: '⚡', action: { type: 'bulk' } },
    ...D.clients.map(c => ({
      id: `run-${c.id}`,
      label: `Run ${c.name}`,
      sub: `${c.id} · ${c.product} · ${c.csm} · last ${c.lastRun}`,
      group: 'Run',
      iconNode: <xCsmDot id={c.csm} />,
      action: { type: 'run', clientId: c.id, product: productIdFor(c.product) },
    })),
    ...D.clients.map(c => ({
      id: `open-${c.id}`,
      label: `Open ${c.name} in Run Studio`,
      sub: `${c.id} · pick options before running`,
      group: 'Clients',
      iconNode: <xCsmDot id={c.csm} />,
      action: { type: 'pickClient', clientId: c.id },
    })),
  ];

  const q = query.trim().toLowerCase();
  const matches = (cmd) => {
    if (!q) return cmd.group === 'Navigate' || cmd.id === 'bulk' || cmd.group === 'Run';
    const hay = `${cmd.label} ${cmd.sub || ''} ${cmd.id}`.toLowerCase();
    return hay.includes(q);
  };
  const filtered = allCommands.filter(matches).slice(0, 9);

  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setCursor(c => Math.min(filtered.length - 1, c + 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setCursor(c => Math.max(0, c - 1)); }
    else if (e.key === 'Enter')   { e.preventDefault(); const cmd = filtered[cursor]; if (cmd) { onAction(cmd.action); onClose(); } }
    else if (e.key === 'Escape')  { e.preventDefault(); onClose(); }
  };

  return (
    <div className="x-overlay" onClick={onClose}
      style={{ position: 'fixed', inset: 0, background: 'rgba(20,18,14,0.55)', backdropFilter: 'blur(8px)', zIndex: 1000, display: 'flex', justifyContent: 'center', paddingTop: '12vh' }}>
      <div className="x-modal" onClick={(e) => e.stopPropagation()} onKeyDown={onKeyDown}
        style={{ width: 620, maxHeight: '70vh', background: xC.card, borderRadius: 14, boxShadow: '0 24px 60px rgba(0,0,0,0.25), 0 0 0 1px rgba(0,0,0,0.05)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {/* Search input */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px', borderBottom: `1px solid ${xC.border}` }}>
          <span style={{ color: xC.muted, display: 'flex' }}><Icon.search size={16} /></span>
          <input ref={inputRef} type="text" value={query} onChange={(e) => { setQuery(e.target.value); setCursor(0); }}
            placeholder="Run a client, jump somewhere, schedule a roster…"
            style={{ flex: 1, border: 'none', outline: 'none', fontFamily: xFONT, fontSize: 15, color: xC.text, background: 'transparent' }} />
          <span style={{ fontFamily: xMONO, fontSize: 10, color: xC.faint, padding: '3px 8px', background: xC.bgDeep, borderRadius: 4 }}>esc</span>
        </div>

        {/* Results */}
        <div ref={listRef} style={{ flex: 1, overflow: 'auto', padding: 6 }}>
          {filtered.length === 0 && (
            <div style={{ padding: 24, textAlign: 'center', color: xC.muted, fontSize: 13 }}>
              No matches for "<span style={{ color: xC.text, fontWeight: 600 }}>{query}</span>". Try a client name, ID, or "schedule".
            </div>
          )}
          {filtered.map((cmd, i) => {
            const on = i === cursor;
            return (
              <div key={cmd.id} onClick={() => { onAction(cmd.action); onClose(); }} onMouseEnter={() => setCursor(i)}
                style={{ display: 'grid', gridTemplateColumns: '28px 1fr auto', gap: 12, alignItems: 'center', padding: '10px 14px', borderRadius: 8, cursor: 'pointer', background: on ? xC.orangeSoft : 'transparent' }}>
                <div style={{ display: 'flex', justifyContent: 'center', color: on ? xC.orange : xC.muted, fontSize: 14 }}>
                  {cmd.iconNode || <span>{cmd.icon}</span>}
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 600, color: xC.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{cmd.label}</div>
                  {cmd.sub && <div style={{ fontFamily: xMONO, fontSize: 11, color: xC.muted, marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{cmd.sub}</div>}
                </div>
                <div style={{ fontFamily: xMONO, fontSize: 10, color: on ? xC.orange : xC.faint, fontWeight: on ? 700 : 400, textTransform: 'uppercase', letterSpacing: 0.8 }}>
                  {cmd.group}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', gap: 14, padding: '10px 18px', borderTop: `1px solid ${xC.border}`, background: xC.cardSoft, fontFamily: xMONO, fontSize: 10, color: xC.muted }}>
          <span><span style={{ background: xC.card, padding: '1px 5px', borderRadius: 3, border: `1px solid ${xC.border}`, marginRight: 4 }}>↑↓</span>navigate</span>
          <span><span style={{ background: xC.card, padding: '1px 5px', borderRadius: 3, border: `1px solid ${xC.border}`, marginRight: 4 }}>↵</span>select</span>
          <span><span style={{ background: xC.card, padding: '1px 5px', borderRadius: 3, border: `1px solid ${xC.border}`, marginRight: 4 }}>esc</span>close</span>
          <span style={{ marginLeft: 'auto', opacity: 0.7 }}>{filtered.length} result{filtered.length === 1 ? '' : 's'}</span>
        </div>
      </div>
    </div>
  );
};

function xCsmDot({ id }) {
  const csm = MockData.csms.find(c => c.id === id);
  if (!csm) return null;
  return <div style={{ width: 16, height: 16, borderRadius: 99, background: csm.color, color: '#fff', fontSize: 8, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: xFONT }}>{csm.initials}</div>;
}

// ─── BULK SCHEDULE MODAL ───────────────────────────────────────────────
window.BulkScheduleModal = function BulkScheduleModal({ open, onClose, onConfirm }) {
  const D = MockData;
  const [csmId, setCsmId] = React.useState('JamesG');
  const [day, setDay] = React.useState(5);
  const [cadence, setCadence] = React.useState('monthly');
  const [startMonth, setStartMonth] = React.useState('Jun 2026');
  const [product, setProduct] = React.useState('client_default');

  React.useEffect(() => {
    if (open) { setCsmId('JamesG'); setDay(5); setCadence('monthly'); setStartMonth('Jun 2026'); setProduct('client_default'); }
  }, [open]);

  if (!open) return null;

  const targetClients = csmId === 'all' ? D.clients : D.clients.filter(c => c.csm === csmId);
  const csm = D.csms.find(c => c.id === csmId);

  return (
    <div className="x-overlay" onClick={onClose}
      style={{ position: 'fixed', inset: 0, background: 'rgba(20,18,14,0.55)', backdropFilter: 'blur(8px)', zIndex: 1000, display: 'flex', justifyContent: 'center', alignItems: 'flex-start', paddingTop: '8vh' }}>
      <div className="x-modal" onClick={(e) => e.stopPropagation()}
        style={{ width: 720, maxHeight: '84vh', background: xC.card, borderRadius: 14, boxShadow: '0 24px 60px rgba(0,0,0,0.25), 0 0 0 1px rgba(0,0,0,0.05)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', padding: '22px 26px 18px', borderBottom: `1px solid ${xC.border}` }}>
          <div>
            <div style={{ fontFamily: xMONO, fontSize: 10, fontWeight: 700, color: xC.muted, textTransform: 'uppercase', letterSpacing: 1.4, marginBottom: 4 }}>Schedules · bulk</div>
            <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: -0.3, color: xC.text }}>Subscribe a roster</div>
            <div style={{ fontSize: 13, color: xC.muted, marginTop: 4 }}>Stand up monthly auto-runs for all of a CSM's clients in one shot.</div>
          </div>
          <button onClick={onClose}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: xC.muted, display: 'flex', padding: 6, borderRadius: 6 }}>
            <Icon.x size={16} />
          </button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflow: 'auto', padding: '22px 26px' }}>
          {/* Step 1 — CSM */}
          <xStep n="01" title="Who to subscribe" sub="Pick a CSM — or all of them.">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
              {[{ id: 'all', name: 'All CSMs', initials: 'ALL', color: xC.navy }, ...D.csms].map((opt) => {
                const on = csmId === opt.id;
                const cs = opt.id === 'all' ? D.clients : D.clients.filter(c => c.csm === opt.id);
                return (
                  <div key={opt.id} onClick={() => setCsmId(opt.id)}
                    style={{ padding: '12px 14px', borderRadius: 8, border: `1.5px solid ${on ? xC.orange : xC.border}`, background: on ? xC.orangeSoft : xC.card, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ width: 28, height: 28, borderRadius: 99, background: opt.color, color: '#fff', fontSize: 10, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: xFONT }}>{opt.initials}</div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{opt.name}</div>
                      <div style={{ fontFamily: xMONO, fontSize: 10, color: xC.muted, marginTop: 1 }}>{cs.length} client{cs.length === 1 ? '' : 's'}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </xStep>

          {/* Step 2 — Day of month */}
          <xStep n="02" title="Day of the month" sub="Runs auto-fire at 06:00 local time on this day, every month.">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(14, 1fr)', gap: 4, marginBottom: 8 }}>
              {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => {
                const on = day === d;
                return (
                  <div key={d} onClick={() => setDay(d)}
                    style={{ padding: '8px 0', textAlign: 'center', borderRadius: 5, cursor: 'pointer',
                      background: on ? xC.orange : xC.cardSoft,
                      color: on ? '#fff' : xC.text,
                      fontFamily: xMONO, fontSize: 12, fontWeight: on ? 700 : 500,
                      border: `1px solid ${on ? xC.orange : xC.border}` }}>
                    {d}
                  </div>
                );
              })}
            </div>
            <div style={{ fontSize: 11, color: xC.muted, fontFamily: xMONO }}>
              Tip: pick a day after raw dumps are typically available (e.g. 5th–8th).
            </div>
          </xStep>

          {/* Step 3 — Cadence + product + start */}
          <xStep n="03" title="Cadence & product" sub="Inherit each client's current product, or override for the whole batch.">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
              <xField label="Cadence">
                <xSel value={cadence} onChange={setCadence} options={[['monthly','Monthly'],['biweekly','Every 2 weeks'],['quarterly','Quarterly']]} />
              </xField>
              <xField label="Start">
                <xSel value={startMonth} onChange={setStartMonth} options={[['Jun 2026','Jun 2026'],['Jul 2026','Jul 2026'],['Aug 2026','Aug 2026']]} />
              </xField>
              <xField label="Product">
                <xSel value={product} onChange={setProduct} options={[['client_default','Each client\'s current'],['ars_full','ARS Full Suite for all'],['txn','Transaction only'],['combined','Combined'],['deposits','Deposits']]} />
              </xField>
            </div>
          </xStep>

          {/* Preview */}
          <div style={{ marginTop: 22, padding: '18px 20px', background: xC.cardSoft, borderRadius: 10, border: `1px solid ${xC.border}` }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: xC.muted, textTransform: 'uppercase', letterSpacing: 1.4 }}>Summary</div>
              <div style={{ fontFamily: xMONO, fontSize: 11, color: xC.muted }}>{targetClients.length} schedules will be created</div>
            </div>
            <div style={{ fontSize: 15, fontWeight: 500, color: xC.text, lineHeight: 1.6 }}>
              Schedule <strong style={{ color: xC.orange }}>{targetClients.length} client{targetClients.length === 1 ? '' : 's'}</strong>
              {csm && <> from <strong>{csm.name}</strong>'s roster</>}
              {csmId === 'all' && <> across <strong>all 6 CSMs</strong></>}
              {' '}to auto-run every <strong>{cadence}</strong> on day <strong>{day}</strong>, starting <strong>{startMonth}</strong>.
            </div>
            {/* Client chips */}
            <div style={{ marginTop: 14, display: 'flex', flexWrap: 'wrap', gap: 5, maxHeight: 76, overflow: 'auto' }}>
              {targetClients.slice(0, 30).map((c) => {
                const csm = D.csms.find(x => x.id === c.csm);
                return (
                  <div key={c.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 8px', background: xC.card, border: `1px solid ${xC.border}`, borderRadius: 99, fontSize: 11 }}>
                    <div style={{ width: 5, height: 5, borderRadius: 99, background: csm.color }} />
                    <span style={{ fontFamily: xMONO, color: xC.muted }}>{c.id}</span>
                    <span style={{ color: xC.text, fontWeight: 500 }}>{c.name.split(' ').slice(0, 2).join(' ')}</span>
                  </div>
                );
              })}
              {targetClients.length > 30 && <div style={{ fontSize: 11, color: xC.muted, padding: '3px 8px' }}>+{targetClients.length - 30} more</div>}
            </div>
          </div>
        </div>

        {/* Footer actions */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 26px', borderTop: `1px solid ${xC.border}`, background: xC.cardSoft }}>
          <div style={{ fontFamily: xMONO, fontSize: 11, color: xC.muted }}>
            Existing schedules for these clients will be replaced.
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={onClose}
              style={{ padding: '9px 16px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', background: '#fff', border: `1px solid ${xC.border}`, color: xC.text, fontFamily: xFONT }}>
              Cancel
            </button>
            <button onClick={() => { onConfirm({ csmId, day, cadence, startMonth, product, count: targetClients.length }); onClose(); }}
              style={{ padding: '9px 18px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', background: xC.orange, color: '#fff', border: 'none', fontFamily: xFONT, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <Icon.bolt size={11} /> Schedule {targetClients.length} clients
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

function xStep({ n, title, sub, children }) {
  return (
    <div style={{ marginBottom: 22 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 4 }}>
        <div style={{ fontFamily: xMONO, fontSize: 11, color: xC.faint, fontWeight: 600 }}>{n}</div>
        <div style={{ fontSize: 14, fontWeight: 700, color: xC.text }}>{title}</div>
      </div>
      <div style={{ fontSize: 12, color: xC.muted, marginBottom: 10, marginLeft: 26 }}>{sub}</div>
      <div style={{ marginLeft: 26 }}>{children}</div>
    </div>
  );
}

function xField({ label, children }) {
  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: xC.muted, textTransform: 'uppercase', letterSpacing: 1.2, marginBottom: 5 }}>{label}</div>
      {children}
    </div>
  );
}

function xSel({ value, onChange, options }) {
  return (
    <div style={{ position: 'relative' }}>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        style={{ width: '100%', padding: '9px 30px 9px 12px', background: xC.card, border: `1px solid ${xC.border}`, borderRadius: 6, fontSize: 13, fontFamily: xFONT, color: xC.text, fontWeight: 500, appearance: 'none', cursor: 'pointer', outline: 'none' }}>
        {options.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
      </select>
      <span style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', color: xC.muted, pointerEvents: 'none' }}><Icon.chev /></span>
    </div>
  );
}

// ─── FAILURE DONE STATE ────────────────────────────────────────────────
// Plain-English translation of common pipeline failures.
const xErrorMap = {
  'product-code-missing': {
    title: 'Missing "Product Code" column in the May raw dump.',
    why: 'CSI sometimes exports without this column when the report variant is set wrong on their side. We need it to tell which accounts are eligible.',
    nextStep: 'Check the dump file in the source folder. If the Product Code column is missing, ask CSI to re-export with the standard ARS template.',
    cta: 'Open source folder',
  },
  'not-enough-months': {
    title: 'Not enough months of data for trend analysis.',
    why: 'Several modules need at least 2 months of historical data to compute trends.',
    nextStep: 'Wait until next month\'s dump is available, or run with the Transaction-only product which doesn\'t need historical trends.',
    cta: 'Switch product',
  },
  'data-range': {
    title: 'Data range issue — a column has unexpected values.',
    why: 'Usually means an account status code is missing or a date value is malformed.',
    nextStep: 'Open the run report PDF below to see which row caused the issue.',
    cta: 'Open run report',
  },
};

window.FailureDoneState = function FailureDoneState({ run, client, onQueueAnother, onRunAgain, onBack }) {
  const D = MockData;
  const err = xErrorMap['product-code-missing']; // fixed for demo; real version uses run.errorKey
  const duration = (run.finishedAt ?? Date.now()) - run.startedAt;
  // Failure happened at analyze (stage idx 2)
  const stagesDone = 2;

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '24px 28px' }}>
      <div style={{ background: xC.card, border: `1px solid ${xC.border}`, borderRadius: 10, overflow: 'hidden' }}>
        {/* Hero */}
        <div style={{ padding: '32px 36px', background: `linear-gradient(180deg, ${xC.redSoft} 0%, ${xC.card} 100%)`, borderBottom: `1px solid ${xC.border}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 6 }}>
            <div style={{ width: 60, height: 60, borderRadius: 99, background: xC.red, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 30, fontWeight: 700 }}>
              !
            </div>
            <div>
              <div style={{ fontFamily: xMONO, fontSize: 10, fontWeight: 700, color: xC.red, textTransform: 'uppercase', letterSpacing: 1.4 }}>Run did not complete</div>
              <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: -0.4, marginTop: 4, color: xC.text }}>Couldn't finish {client.name}'s report</div>
              <div style={{ fontSize: 13, color: xC.muted, marginTop: 4 }}>Stopped after {Math.floor(duration/1000)}s · failed at stage 3 of 5 (Run analytics)</div>
            </div>
          </div>
        </div>

        {/* Plain-English explanation */}
        <div style={{ padding: '24px 36px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 28 }}>
          <div>
            <div style={{ fontFamily: xMONO, fontSize: 10, fontWeight: 700, color: xC.muted, textTransform: 'uppercase', letterSpacing: 1.4, marginBottom: 6 }}>What went wrong</div>
            <div style={{ fontSize: 16, fontWeight: 600, lineHeight: 1.35, marginBottom: 10, color: xC.text }}>{err.title}</div>
            <div style={{ fontSize: 13, color: xC.muted, lineHeight: 1.55, marginBottom: 14 }}>{err.why}</div>

            <div style={{ fontFamily: xMONO, fontSize: 10, fontWeight: 700, color: xC.muted, textTransform: 'uppercase', letterSpacing: 1.4, marginBottom: 6 }}>What to do</div>
            <div style={{ fontSize: 13.5, color: xC.text, lineHeight: 1.5, marginBottom: 14 }}>{err.nextStep}</div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button style={{ padding: '9px 16px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', background: xC.orange, color: '#fff', border: 'none', fontFamily: xFONT, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                {err.cta} →
              </button>
              <button style={{ padding: '9px 16px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', background: '#fff', color: xC.text, border: `1px solid ${xC.border}`, fontFamily: xFONT, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                Notify {client.csm}
              </button>
            </div>
          </div>

          {/* Stats */}
          <div>
            <div style={{ fontFamily: xMONO, fontSize: 10, fontWeight: 700, color: xC.muted, textTransform: 'uppercase', letterSpacing: 1.4, marginBottom: 10 }}>What completed</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <xStat color={xC.green} label="Stages completed"   value={`${stagesDone} / 5`} icon="✓" />
              <xStat color={xC.green} label="Modules before fail" value="12 / 25" icon="✓" />
              <xStat color={xC.text}  label="Time elapsed"        value={`${Math.floor(duration/1000)}s`} />
              <xStat color={xC.red}   label="Files produced"      value="0" icon="✗" />
            </div>

            <div style={{ marginTop: 14, padding: '12px 14px', background: xC.cardSoft, borderRadius: 8, border: `1px solid ${xC.border}` }}>
              <div style={{ fontFamily: xMONO, fontSize: 10, fontWeight: 700, color: xC.muted, textTransform: 'uppercase', letterSpacing: 1.4, marginBottom: 6 }}>For the curious</div>
              <details>
                <summary style={{ cursor: 'pointer', fontSize: 12, color: xC.text, fontWeight: 500, listStyle: 'none' }}>
                  ▸ View the technical error
                </summary>
                <div style={{ marginTop: 10, padding: '10px 12px', background: xC.bgDeep, borderRadius: 6, fontFamily: xMONO, fontSize: 11, color: xC.text, lineHeight: 1.6 }}>
                  <div style={{ color: xC.red, fontWeight: 700 }}>KeyError: 'Product Code'</div>
                  <div style={{ color: xC.muted, marginTop: 6 }}>at retrieve_data.py:142</div>
                  <div style={{ color: xC.muted }}>in compute_eligibility() ← analyze_overview() ← stage_analyze()</div>
                </div>
              </details>
            </div>
          </div>
        </div>

        {/* Footer actions */}
        <div style={{ padding: '16px 36px', borderTop: `1px solid ${xC.border}`, background: xC.cardSoft, display: 'flex', gap: 10 }}>
          <button onClick={() => onRunAgain(run.clientId, run.product)}
            style={{ padding: '10px 18px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', background: xC.orange, color: '#fff', border: 'none', fontFamily: xFONT, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            ↻ Try again
          </button>
          <button onClick={onQueueAnother}
            style={{ padding: '10px 18px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', background: '#fff', color: xC.text, border: `1px solid ${xC.border}`, fontFamily: xFONT }}>
            Run another report
          </button>
          <button onClick={onBack}
            style={{ padding: '10px 18px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', background: '#fff', color: xC.text, border: `1px solid ${xC.border}`, fontFamily: xFONT }}>
            Back to dashboard
          </button>
        </div>
      </div>
    </div>
  );
};

function xStat({ color, label, value, icon }) {
  return (
    <div style={{ background: xC.cardSoft, borderRadius: 8, padding: '12px 14px', borderLeft: `3px solid ${color}` }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
        <div style={{ fontFamily: xMONO, fontSize: 22, fontWeight: 700, color, lineHeight: 1 }}>{value}</div>
        {icon && <span style={{ color, fontSize: 13 }}>{icon}</span>}
      </div>
      <div style={{ fontSize: 10, fontWeight: 700, color: xC.muted, textTransform: 'uppercase', letterSpacing: 1, marginTop: 6 }}>{label}</div>
    </div>
  );
}

// ─── TOAST ─────────────────────────────────────────────────────────────
// Lightweight bottom-right notification used after bulk schedule.
window.Toast = function Toast({ message, onDismiss }) {
  React.useEffect(() => {
    if (!message) return;
    const t = setTimeout(onDismiss, 4500);
    return () => clearTimeout(t);
  }, [message]);
  if (!message) return null;
  return (
    <div style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 1100, background: xC.text, color: '#fff', padding: '12px 18px', borderRadius: 8, boxShadow: '0 8px 24px rgba(0,0,0,0.2)', display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, animation: 'xSlideIn .2s ease-out' }}>
      <span style={{ color: xC.green, display: 'flex' }}><Icon.check size={14} /></span>
      <span>{message}</span>
      <button onClick={onDismiss} style={{ background: 'transparent', border: 'none', color: 'rgba(255,255,255,0.6)', cursor: 'pointer', display: 'flex', padding: 4 }}><Icon.x size={11} /></button>
    </div>
  );
};
