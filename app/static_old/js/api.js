/* ============================================================
   Melodock — js/api.js
   Centraliza TODAS as chamadas fetch ao backend.
   Backend esperado em http://localhost:9014 (com WebSocket).
   ============================================================ */

const API = window.location.origin + '/api';
window.BACKEND_ONLINE = null;
// API key persisted in sessionStorage so it survives navigation but not a new session
window.MD_API_KEY = sessionStorage.getItem('md_key') || '';

let _backendDownUntil = 0;

function _setApiKey(key) {
  window.MD_API_KEY = key || '';
  if (key) sessionStorage.setItem('md_key', key);
  else sessionStorage.removeItem('md_key');
}

async function apiFetch(path, opts = {}) {
  if (Date.now() < _backendDownUntil) {
    window.BACKEND_ONLINE = false;
    return MelodockMock.handle(path, opts);
  }
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 5000);
    const headers = { 'Content-Type': 'application/json' };
    if (window.MD_API_KEY) headers['X-Melodock-Key'] = window.MD_API_KEY;
    const res = await fetch(API + path, {
      headers,
      ...opts,
      signal: ctrl.signal,
    });
    clearTimeout(timer);
    if (res.status === 401) {
      // Prompt for password once
      const key = prompt('Senha de acesso Melodock:');
      if (key) {
        _setApiKey(key);
        return apiFetch(path, opts);
      }
      window.BACKEND_ONLINE = false;
      return MelodockMock.handle(path, opts);
    }
    if (!res.ok) throw new Error('HTTP ' + res.status);
    window.BACKEND_ONLINE = true;
    return await res.json();
  } catch (err) {
    window.BACKEND_ONLINE = false;
    _backendDownUntil = Date.now() + 15000;
    return MelodockMock.handle(path, opts);
  }
}

/* ----------------------- Helpers de mapeamento ----------------------- */

function _mapArtist(r) {
  return {
    deezer_id: r.deezer_id,
    name: r.name,
    picture_url: r.picture_url || null,
    albums: r.nb_album ?? r.albums ?? 0,
    fans: r.followers ?? r.fans ?? 0,
    in_library: r.in_library || false,
  };
}

function _mapJob(j) {
  return {
    id: j.id,
    deezer_id: j.deezer_id,
    artist: j.artist_name || j.artist || '—',
    album: j.album_title || j.album || String(j.deezer_id),
    status: j.status,
    progress: j.progress || 0,
    quality: j.quality || null,
    error: j.error_message || j.error || null,
    artist_id: j.artist_id,
    album_id: j.album_id,
    created_at: j.created_at,
  };
}

/* ----------------------- Endpoints ----------------------- */

async function getLibraryStats()  { return apiFetch('/library'); }

async function searchArtists(q) {
  const data = await apiFetch('/artists/search', { method: 'POST', body: JSON.stringify({ query: q }) });
  // Backend returns array; wrap as { results: [...] } and map field names
  const list = Array.isArray(data) ? data : (data.results || []);
  return { results: list.map(_mapArtist) };
}

async function addArtist(deezer_id, opts = {}) {
  return apiFetch('/artists/add', { method: 'POST', body: JSON.stringify({ deezer_id, ...opts }) });
}

async function getArtists(page = 1, search = '') {
  return apiFetch('/artists?page=' + page + '&search=' + encodeURIComponent(search));
}

async function getDownloads(status = '') {
  const data = await apiFetch('/downloads' + (status ? '?status=' + status : ''));
  if (!data || !data.items) return data;
  return { ...data, items: data.items.map(_mapJob) };
}

async function getActiveJob() {
  const data = await apiFetch('/downloads/active');
  return data ? _mapJob(data) : null;
}

async function cancelJob(id) {
  return apiFetch('/downloads/' + id, { method: 'DELETE' });
}

async function clearCompleted() {
  return apiFetch('/downloads/clear-completed', { method: 'POST' });
}

async function retryUpload(id) {
  return apiFetch('/downloads/' + id + '/retry-upload', { method: 'POST' });
}

async function getRelatedArtists(id) {
  const data = await apiFetch('/explorer/related/' + id);
  if (!data) return { artist: null, related: [] };
  return {
    artist: data.artist ? _mapArtist(data.artist) : null,
    related: (data.related || []).map(_mapArtist),
  };
}

async function getSettings()       { return apiFetch('/settings'); }
async function saveSettings(data)  { return apiFetch('/settings', { method: 'PUT', body: JSON.stringify(data) }); }
async function testARL(arl)        { return apiFetch('/settings/test-arl', { method: 'POST', body: JSON.stringify({ arl }) }); }
async function getLogs()           { return apiFetch('/logs'); }
async function triggerScan()       { return apiFetch('/library/scan', { method: 'POST' }); }
async function runAudit()          { return apiFetch('/library/audit', { method: 'POST' }); }
async function getDriveStats()     { return apiFetch('/library/drive-stats'); }

/* ====================== WebSocket ====================== */

window.MD_WS = null;
const _wsListeners = {};

function wsOn(event, cb) {
  if (!_wsListeners[event]) _wsListeners[event] = [];
  _wsListeners[event].push(cb);
}

function _wsDispatch(event, data) {
  (_wsListeners[event] || []).forEach(cb => cb(data));
  (_wsListeners['*'] || []).forEach(cb => cb(event, data));
}

function wsConnect() {
  if (window.MD_WS && window.MD_WS.readyState <= 1) return;
  try {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(proto + '://' + location.host + '/ws');
    window.MD_WS = ws;

    ws.onopen = () => {
      window.BACKEND_ONLINE = true;
      _backendDownUntil = 0;
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type && msg.type !== 'ping') _wsDispatch(msg.type, msg.data || {});
      } catch (_) {}
    };

    ws.onclose = () => setTimeout(wsConnect, 5000);
    ws.onerror = () => ws.close();
  } catch (_) {}
}

/* ==========================================================
   Mock — modo demonstração (backend offline)
   ========================================================== */
const MelodockMock = (() => {
  const A = (deezer_id, name, albums, fans, in_library) => ({ deezer_id, name, albums, fans, in_library });

  const pool = [
    A(201, 'Neon Drift', 6, 84200, true),
    A(202, 'Vela Norte', 4, 12100, true),
    A(203, 'Glass Harbor', 8, 230400, true),
    A(204, 'Mono Cultura', 3, 9800, true),
    A(205, 'Sintaxe', 5, 45700, true),
    A(206, 'Rua Vermelha', 7, 156000, true),
    A(207, 'Ondas de Inverno', 2, 5400, true),
    A(208, 'Café Estéreo', 9, 310200, true),
    A(209, 'Baía Elétrica', 4, 27600, true),
    A(210, 'The Paper Lions', 6, 88100, true),
    A(211, 'Madrugada Livre', 5, 64300, false),
    A(212, 'Pixel Praia', 3, 18900, false),
    A(213, 'Verde Cobalto', 7, 201500, false),
    A(214, 'Sal Grosso', 4, 33200, false),
    A(215, 'Lumen', 10, 540800, false),
    A(216, 'Faro', 2, 7100, false),
    A(217, 'Quarto Minguante', 5, 92400, false),
    A(218, 'Trem Fantasma', 6, 47800, false),
    A(219, 'Aurora Synthetics', 8, 388000, false),
    A(220, 'Dona Resistência', 3, 15600, false),
  ];

  let jobSeq = 130;
  const J = (id, artist, album, status, extra = {}) =>
    ({ id, artist, album, status, quality: 'MP3_320', progress: 0, error: null, ...extra });
  const jobs = [
    J(124, 'Neon Drift', 'Meia-Noite em Loop', 'running', { progress: 45, track: 5, tracks: 12 }),
    J(125, 'Glass Harbor', 'Cartas ao Porto', 'queued', { tracks: 10 }),
    J(126, 'Sintaxe', 'Compilado de Erros', 'queued', { tracks: 8 }),
    J(127, 'Rua Vermelha', 'Sinal Fechado (EP)', 'queued', { tracks: 5 }),
    J(123, 'Café Estéreo', 'Expresso Duplo', 'done'),
    J(122, 'Mono Cultura', 'Mono Cultura', 'done'),
    J(121, 'Vela Norte', 'Rota de Fuga', 'done'),
    J(120, 'Ondas de Inverno', 'Geleira', 'done'),
    J(119, 'The Paper Lions', 'Crown of Paper', 'done'),
    J(118, 'Baía Elétrica', 'Maré Alta', 'error', { error: 'Track 3: stream indisponível' }),
    J(117, 'Glass Harbor', 'Harbor Lights', 'done'),
  ];

  const cfg = {
    arl: '', quality: 'MP3_320', release_types: ['album', 'ep'],
    blocklist: ['remix', 'karaoke'], max_tracks: 0,
    delay_min: 3, delay_max: 8, password: '',
    rclone_enabled: false, rclone_remote: 'google:media/music', rclone_flags: '',
  };

  const logs = [];
  function ts(o = 0) { return new Date(Date.now() - o * 1000).toTimeString().slice(0, 8); }
  function log(level, msg, o = 0) {
    logs.push({ ts: ts(o), level, msg });
    if (logs.length > 500) logs.shift();
  }
  [
    [240, 'INFO', 'Melodock v2.0.0 iniciado (modo demo)'],
    [238, 'INFO', 'Biblioteca montada em /music'],
    [236, 'INFO', 'Biblioteca carregada: 318 álbuns · 4.231 tracks'],
    [150, 'INFO', 'Iniciando download: Neon Drift — Meia-Noite em Loop'],
    [140, 'INFO', 'Track 1/12 concluída (7.2 MB)'],
    [113, 'ERROR', 'Falha na track 3: stream indisponível — retry 1/3'],
    [104, 'INFO', 'Track 3/12 concluída (8.4 MB)'],
    [66,  'INFO', 'Track 5/12 concluída (6.9 MB)'],
  ].forEach(([o, lv, m]) => log(lv, m, o));

  function promote() {
    const next = jobs.find(j => j.status === 'queued');
    if (next) { next.status = 'running'; next.progress = 0; next.tracks = next.tracks || 10; next.track = 1; }
  }

  function tick() {
    const job = jobs.find(j => j.status === 'running');
    if (!job) { promote(); return; }
    job.progress = Math.min(100, Math.round(job.progress + 1 + Math.random() * 3));
    const t = Math.max(1, Math.min(job.tracks, Math.ceil((job.progress / 100) * job.tracks)));
    if (t > (job.track || 1)) job.track = t;
    if (job.progress >= 100) { job.status = 'done'; promote(); }
  }

  function stats() {
    const inLib = pool.filter(a => a.in_library).length;
    const recent = jobs.slice().sort((a, b) => b.id - a.id).slice(0, 10);
    return {
      artists: 32 + inLib, albums: 318, tracks: 4231, size_gb: 12.4,
      recent_albums: recent.map(j => ({ artist: j.artist, title: j.album, status: j.status })),
      recent_jobs: recent,
    };
  }

  function handle(path, opts = {}) {
    const method = (opts.method || 'GET').toUpperCase();
    let body = {};
    try { body = opts.body ? JSON.parse(opts.body) : {}; } catch (_) {}

    if (path === '/library') return stats();

    if (path === '/artists/search') {
      const q = (body.query || '').toLowerCase();
      // return raw format — api.js wrapper will call _mapArtist
      return pool.filter(a => a.name.toLowerCase().includes(q));
    }

    if (path === '/artists/add') {
      const a = pool.find(x => x.deezer_id === body.deezer_id);
      if (a && !a.in_library) {
        a.in_library = true;
        jobs.unshift(J(++jobSeq, a.name, 'Discografia (' + a.albums + ' álbuns)', 'queued', { tracks: a.albums * 10 }));
      }
      return { ok: true };
    }

    if (path.startsWith('/artists')) {
      const items = pool.filter(a => a.in_library);
      return { items, total: items.length, page: 1, pages: 1 };
    }

    if (path === '/downloads/active') {
      tick();
      return jobs.find(j => j.status === 'running') || null;
    }

    if (path === '/downloads/clear-completed') {
      for (let i = jobs.length - 1; i >= 0; i--) {
        if (jobs[i].status === 'done') jobs.splice(i, 1);
      }
      return { ok: true };
    }

    if (method === 'DELETE' && path.startsWith('/downloads/')) {
      const id = parseInt(path.split('/').pop(), 10);
      const i = jobs.findIndex(j => j.id === id && j.status === 'queued');
      if (i >= 0) jobs.splice(i, 1);
      return { ok: true };
    }

    if (path.startsWith('/downloads')) {
      const m = path.match(/status=(\w+)/);
      const items = m ? jobs.filter(j => j.status === m[1]) : jobs.slice();
      return { items, total: items.length, running_count: 0, queued_count: items.filter(j => j.status === 'queued').length };
    }

    if (path.startsWith('/explorer/related/')) {
      const id = parseInt(path.split('/').pop(), 10);
      const center = pool.find(a => a.deezer_id === id) || null;
      const related = pool.filter((a, i) => a.deezer_id !== id && (i + id) % 3 !== 0).slice(0, 8);
      // return in backend format so _mapArtist wrapper works
      return {
        artist: center ? { ...center, nb_album: center.albums, followers: center.fans } : null,
        related: related.map(a => ({ ...a, nb_album: a.albums, followers: a.fans })),
      };
    }

    if (path === '/settings' && method === 'GET') return { ...cfg, arl_configured: !!cfg.arl, access_password_configured: !!cfg.password };
    if (path === '/settings' && method === 'PUT') { Object.assign(cfg, body); return { ...cfg }; }
    if (path === '/settings/test-arl') return { valid: !!(body.arl && body.arl.trim().length >= 32) };

    if (path === '/logs') return { lines: logs.slice() };
    if (path === '/library/scan' || path === '/library/audit') return { task: 'started' };
    if (path === '/library/drive-stats') return { total_uploaded: 0, total_local_only: 318, total_upload_error: 0, drive_path_base: 'google:media/music', rclone_enabled: false };

    return {};
  }

  return { handle };
})();
