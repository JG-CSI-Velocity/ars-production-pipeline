// Shared mock data + tiny helpers for all three directions.
// Realistic-feeling data based on the actual codebase (CSMs, client IDs,
// products, modules, stages).

window.MockData = {
  csms: [
    { id: 'JamesG', name: 'James Gilmore',  initials: 'JG', color: '#F15D22' },
    { id: 'Jordan', name: 'Jordan Hayes',    initials: 'JH', color: '#2A8B3E' },
    { id: 'Aaron',  name: 'Aaron Liu',       initials: 'AL', color: '#00274C' },
    { id: 'Gregg',  name: 'Gregg Mendoza',   initials: 'GM', color: '#7B4FB8' },
    { id: 'Dan',    name: 'Dan Park',        initials: 'DP', color: '#C77F3C' },
    { id: 'Max',    name: 'Max Reilly',      initials: 'MR', color: '#1B6CA8' },
  ],

  clients: [
    { id: '1776', name: 'American Heritage CU',          csm: 'JamesG', accounts: 47821, branches: 13, lastRun: 'May 8',  nextSched: 'Jun 5',  product: 'ARS Full Suite', status: 'ready'   },
    { id: '1226', name: 'Connecticut State Employees',   csm: 'JamesG', accounts: 89234, branches: 8,  lastRun: 'May 8',  nextSched: 'Jun 5',  product: 'ARS Full Suite', status: 'ready'   },
    { id: '1746', name: 'Lompoc Federal CU',             csm: 'JamesG', accounts: 12483, branches: 5,  lastRun: 'May 9',  nextSched: 'Jun 9',  product: 'Transaction',    status: 'ready'   },
    { id: '2034', name: 'Pacific Northwest FCU',         csm: 'Jordan', accounts: 67120, branches: 11, lastRun: 'May 7',  nextSched: 'Jun 7',  product: 'Combined',       status: 'ready'   },
    { id: '2118', name: 'Mountain View Savings',         csm: 'Jordan', accounts: 23456, branches: 6,  lastRun: 'May 10', nextSched: 'Jun 10', product: 'Deposits',       status: 'pending' },
    { id: '3041', name: 'Lakeside Community Bank',       csm: 'Aaron',  accounts: 18902, branches: 4,  lastRun: 'May 11', nextSched: 'Jun 11', product: 'ARS Full Suite', status: 'ready'   },
    { id: '3087', name: 'Riverbend Trust',               csm: 'Aaron',  accounts: 34112, branches: 7,  lastRun: 'May 4',  nextSched: 'Jun 4',  product: 'Transaction',    status: 'warning' },
    { id: '4221', name: 'Cascade FCU',                   csm: 'Gregg',  accounts: 51200, branches: 9,  lastRun: 'May 12', nextSched: 'Jun 12', product: 'ARS Full Suite', status: 'ready'   },
    { id: '4308', name: 'Summit Heritage Bank',          csm: 'Gregg',  accounts: 14210, branches: 4,  lastRun: 'May 2',  nextSched: 'Jun 2',  product: 'Deposits',       status: 'ready'   },
    { id: '5012', name: 'First Heritage Bank',           csm: 'Dan',    accounts: 9821,  branches: 3,  lastRun: 'May 6',  nextSched: 'Jun 6',  product: 'Deposits',       status: 'error'   },
    { id: '5188', name: 'Tidewater FCU',                 csm: 'Dan',    accounts: 41203, branches: 8,  lastRun: 'May 3',  nextSched: 'Jun 3',  product: 'Combined',       status: 'ready'   },
    { id: '6450', name: 'Northwoods Credit Union',       csm: 'Max',    accounts: 28710, branches: 6,  lastRun: 'May 13', nextSched: 'Jun 13', product: 'Combined',       status: 'ready'   },
    { id: '6502', name: 'Ironbridge Savings',            csm: 'Max',    accounts: 22115, branches: 5,  lastRun: 'May 1',  nextSched: 'Jun 1',  product: 'ARS Full Suite', status: 'ready'   },
  ],

  products: [
    { id: 'ars_full',  name: 'ARS Full Suite', slides: 78, modules: 25, time: '12 min', desc: 'Complete suite — transaction, deposits, Reg E, mailer effectiveness, strategic insights.' },
    { id: 'txn',       name: 'Transaction',    slides: 32, modules: 12, time: '6 min',  desc: 'Debit card and transaction performance only.' },
    { id: 'combined',  name: 'Combined',       slides: 54, modules: 18, time: '9 min',  desc: 'Transaction + deposits analyses combined.' },
    { id: 'deposits',  name: 'Deposits',       slides: 24, modules: 8,  time: '4 min',  desc: 'Deposit account behavior and value to members.' },
  ],

  stages: [
    { id: 'read',     name: 'Read your data',       desc: 'Loading formatted ODD files',     est: 24  },
    { id: 'prep',     name: 'Prepare analyses',     desc: 'Pipeline setup and retrieval',    est: 38  },
    { id: 'analyze',  name: 'Run analytics',        desc: '25 modules across 7 themes',      est: 540 },
    { id: 'deck',     name: 'Build PowerPoint',     desc: 'Composing slides and charts',     est: 84  },
    { id: 'finalize', name: 'Save and deliver',     desc: 'Writing outputs to network drive',est: 18  },
  ],

  themes: [
    { id: 'overview',  name: 'Account overview',     count: 4 },
    { id: 'dctr',      name: 'Debit performance',    count: 6 },
    { id: 'rege',      name: 'Reg E compliance',     count: 3 },
    { id: 'value',     name: 'Value to members',     count: 4 },
    { id: 'attrition', name: 'At-risk accounts',     count: 3 },
    { id: 'mailer',    name: 'Mailer effectiveness', count: 3 },
    { id: 'insights',  name: 'Strategic insights',   count: 2 },
  ],

  // For the In-Progress views
  liveRuns: [
    { client: '1776', name: 'American Heritage CU',        csm: 'JamesG', product: 'ARS Full Suite', stage: 'analyze', stageProg: 0.64, themeNow: 'Mailer effectiveness', moduleNow: 'mailer_response_rate', elapsed: 372, eta: 195 },
    { client: '2034', name: 'Pacific Northwest FCU',       csm: 'Jordan', product: 'Combined',       stage: 'deck',    stageProg: 0.30, themeNow: '—',                    moduleNow: '—',                    elapsed: 489, eta: 78  },
    { client: '5012', name: 'First Heritage Bank',         csm: 'Dan',    product: 'Deposits',       stage: 'read',    stageProg: 0.55, themeNow: '—',                    moduleNow: '—',                    elapsed: 12,  eta: 240 },
  ],

  brand: {
    navy: '#00274C',
    navyDeep: '#001a35',
    orange: '#F15D22',
    orangeDark: '#d14e1a',
    orangeSoft: '#fef0e8',
    green: '#2A8B3E',
    greenSoft: '#e8f5e9',
    red: '#c0392b',
    redSoft: '#fdecea',
    gold: '#FBAE40',
    goldSoft: '#fff4e0',
  },
};

// Helper — pad numbers
window.fmt = {
  mmss: (s) => `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`,
  num: (n) => n.toLocaleString('en-US'),
  k: (n) => n >= 1000 ? `${(n/1000).toFixed(n>=10000?0:1)}k` : String(n),
};

// Small reusable SVG icon set — line-style, currentColor.
// All icons accept a props object: <Icon.foo size={12} /> or <Icon.chev rot={180} />.
window.Icon = {
  chev: ({ rot=0, size=12 }={}) => (
    <svg width={size} height={size} viewBox="0 0 12 12" style={{ transform: `rotate(${rot}deg)`, transition: 'transform .15s' }}>
      <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  check: ({ size=12 }={}) => (
    <svg width={size} height={size} viewBox="0 0 12 12"><path d="M2.5 6.2L4.8 8.5L9.5 3.5" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
  ),
  x: ({ size=12 }={}) => (
    <svg width={size} height={size} viewBox="0 0 12 12"><path d="M3 3L9 9M9 3L3 9" stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinecap="round"/></svg>
  ),
  dot: ({ size=8 }={}) => (<svg width={size} height={size} viewBox="0 0 8 8"><circle cx="4" cy="4" r="3" fill="currentColor"/></svg>),
  warn: ({ size=12 }={}) => (
    <svg width={size} height={size} viewBox="0 0 12 12"><path d="M6 1.5L11 10.5H1L6 1.5Z" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinejoin="round"/><path d="M6 5V7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><circle cx="6" cy="8.6" r="0.7" fill="currentColor"/></svg>
  ),
  play: ({ size=10 }={}) => (<svg width={size} height={size} viewBox="0 0 10 10"><path d="M3 2L8 5L3 8Z" fill="currentColor"/></svg>),
  pause: ({ size=10 }={}) => (<svg width={size} height={size} viewBox="0 0 10 10"><rect x="2.5" y="2" width="2" height="6" fill="currentColor"/><rect x="5.5" y="2" width="2" height="6" fill="currentColor"/></svg>),
  search: ({ size=14 }={}) => (
    <svg width={size} height={size} viewBox="0 0 14 14"><circle cx="6" cy="6" r="4" stroke="currentColor" strokeWidth="1.5" fill="none"/><path d="M9 9L12 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
  ),
  calendar: ({ size=14 }={}) => (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none"><rect x="1.5" y="2.5" width="11" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.3"/><path d="M1.5 5.5H12.5M4 1V3.5M10 1V3.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>
  ),
  user: ({ size=14 }={}) => (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none"><circle cx="7" cy="5" r="2.3" stroke="currentColor" strokeWidth="1.3"/><path d="M2.5 12c.5-2.2 2.3-3.5 4.5-3.5s4 1.3 4.5 3.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>
  ),
  download: ({ size=14 }={}) => (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none"><path d="M7 2v8M3.5 7L7 10.5L10.5 7M2 12h10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>
  ),
  bolt: ({ size=12 }={}) => (<svg width={size} height={size} viewBox="0 0 12 12"><path d="M7 1L2 7H6L5 11L10 5H6L7 1Z" fill="currentColor"/></svg>),
};

// Status pill primitive used across directions.
window.statusMeta = {
  ready:    { label: 'Ready',    fg: '#2A8B3E', bg: '#e8f5e9' },
  pending:  { label: 'Awaiting data', fg: '#B5651D', bg: '#fff4e0' },
  warning:  { label: 'Last run had warnings', fg: '#B5651D', bg: '#fff4e0' },
  error:    { label: 'Last run failed', fg: '#c0392b', bg: '#fdecea' },
  queued:   { label: 'Queued',   fg: '#00274C', bg: '#dfe8f3' },
  running:  { label: 'Running',  fg: '#F15D22', bg: '#fef0e8' },
  done:     { label: 'Done',     fg: '#2A8B3E', bg: '#e8f5e9' },
};
