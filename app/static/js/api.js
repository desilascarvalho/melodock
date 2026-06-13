/* ============================================================
   Melodock — js/api.js
   Centraliza TODAS as chamadas fetch ao backend.
   Backend esperado em http://localhost:9014 (sem WebSocket).

   Se o backend estiver inacessível, as funções respondem com
   dados de demonstração (MelodockMock) para a UI continuar
   navegável durante o desenvolvimento.
   ============================================================ */

const API = window.location.origin + '/api';
window.BACKEND_ONLINE = null;

/* Evita spam de erros de rede no console: após uma falha,
   usa o mock direto por 15s antes de tentar o backend de novo. */
let _backendDownUntil = 0;

async function apiFetch(path, opts = {}) {
  if (Date.now() < _backendDownUntil) {
    window.BACKEND_ONLINE = false;
    return MelodockMock.handle(path, opts);
  }
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 1500);
    const res = await fetch(API + path, {
      headers: { 'Content-Type': 'application/json' },
      ...opts,
      signal: ctrl.signal,
    });
    clearTimeout(timer);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    window.BACKEND_ONLINE = true;
    return await res.json();
  } catch (err) {
    window.BACKEND_ONLINE = false;
    _backendDownUntil = Date.now() + 15000;
    return MelodockMock.handle(path, opts);
  }
}

/* ----------------------- Endpoints ----------------------- */

async function getLibraryStats()  { return apiFetch('/library'); }                      // GET  /api/library
async function searchArtists(q)   { return apiFetch('/artists/search', { method: 'POST', body: JSON.stringify({ query: q }) }); } // POST /api/artists/search
async function addArtist(deezer_id, opts = {}) { return apiFetch('/artists/add', { method: 'POST', body: JSON.stringify({ deezer_id, ...opts }) }); } // POST /api/artists/add
async function getArtists(page = 1, search = '') { return apiFetch('/artists?page=' + page + '&search=' + encodeURIComponent(search)); } // GET /api/artists
async function getArtist(id)          { return apiFetch('/artists/' + id); }                         // GET /api/artists/{id}
async function getArtistAlbums(id)    { return apiFetch('/artists/' + id + '/albums'); }              // GET /api/artists/{id}/albums
async function getAlbumDetail(id)     { return apiFetch('/library/albums/' + id); }                   // GET /api/library/albums/{id}
async function queueTrackDownload(deezer_id) { return apiFetch('/downloads/queue', { method: 'POST', body: JSON.stringify({ deezer_id, job_type: 'track' }) }); } // POST /api/downloads/queue (track)
async function getDownloads(status = '') { return apiFetch('/downloads' + (status ? '?status=' + status : '')); } // GET /api/downloads
async function getActiveJob()     { return apiFetch('/downloads/active'); }             // GET  /api/downloads/active
async function cancelJob(id)      { return apiFetch('/downloads/' + id, { method: 'DELETE' }); } // DELETE /api/downloads/{id}
async function clearCompleted()   { return apiFetch('/downloads/clear-completed', { method: 'POST' }); } // POST /api/downloads/clear-completed
async function getRelatedArtists(id) { return apiFetch('/explorer/related/' + id); }    // GET  /api/explorer/related/{id}
async function getSettings()           { return apiFetch('/settings'); }
async function saveSettings(data)      { return apiFetch('/settings', { method: 'PUT', body: JSON.stringify(data) }); }
async function testARL(arl)            { return apiFetch('/settings/test-arl', { method: 'POST', body: JSON.stringify({ arl }) }); }
async function getDeemixSettings()    { return apiFetch('/settings/deemix'); }
async function saveDeemixSettings(data){ return apiFetch('/settings/deemix', { method: 'PUT', body: JSON.stringify(data) }); }
async function getLogs()          { return apiFetch('/logs'); }                         // GET  /api/logs
async function triggerScan()      { return apiFetch('/library/scan', { method: 'POST' }); } // POST /api/library/scan
async function runAudit()         { return apiFetch('/library/audit', { method: 'POST' }); } // POST /api/library/audit

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
  const J = (id, artist, album, status, extra = {}) => ({ id, artist, album, status, quality: 'MP3 320kbps', ...extra });
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

  const settings = {
    arl: '',
    quality: 'MP3_320',
    release_types: ['album', 'ep'],
    blocklist: ['remix', 'karaoke'],
    max_tracks: 0,
    delay_min: 3,
    delay_max: 8,
    password: '',
  };

  /* ---------- logs ---------- */
  const logs = [];
  function ts(offsetSec = 0) {
    return new Date(Date.now() - offsetSec * 1000).toTimeString().slice(0, 8);
  }
  function log(level, msg, offsetSec = 0) {
    logs.push({ ts: ts(offsetSec), level, msg });
    if (logs.length > 500) logs.shift();
  }
  [
    [240, 'INFO', 'Melodock v1.0.0 iniciado'],
    [238, 'INFO', 'Biblioteca montada em /music'],
    [236, 'INFO', 'Biblioteca carregada: 318 álbuns · 4.231 tracks'],
    [234, 'INFO', 'Sessão Deezer autenticada (ARL válido por 89 dias)'],
    [150, 'INFO', 'Iniciando download: Neon Drift — Meia-Noite em Loop'],
    [140, 'INFO', 'Track 1/12 concluída (7.2 MB)'],
    [134, 'WARN', 'Delay aplicado: 4.2s'],
    [122, 'INFO', 'Track 2/12 concluída (9.1 MB)'],
    [113, 'ERROR', 'Falha na track 3: stream indisponível — retry 1/3'],
    [104, 'INFO', 'Track 3/12 concluída (8.4 MB)'],
    [95, 'WARN', 'Delay aplicado: 6.8s'],
    [82, 'INFO', 'Track 4/12 concluída (10.3 MB)'],
    [66, 'INFO', 'Track 5/12 concluída (6.9 MB)'],
  ].forEach(([o, lv, m]) => log(lv, m, o));

  /* ---------- simulação de progresso ---------- */
  function promote() {
    const next = jobs.find(j => j.status === 'queued');
    if (next) {
      next.status = 'running';
      next.progress = 0;
      next.tracks = next.tracks || 10;
      next.track = 1;
      log('INFO', 'Iniciando download: ' + next.artist + ' — ' + next.album);
    }
  }

  function tick() {
    const job = jobs.find(j => j.status === 'running');
    if (!job) { promote(); return; }
    job.progress = Math.min(100, Math.round(job.progress + 1 + Math.random() * 3));
    const newTrack = Math.max(1, Math.min(job.tracks, Math.ceil((job.progress / 100) * job.tracks)));
    if (newTrack > (job.track || 1)) {
      job.track = newTrack;
      log('INFO', 'Track ' + newTrack + '/' + job.tracks + ' concluída (' + (6 + Math.random() * 5).toFixed(1) + ' MB)');
      if (Math.random() < 0.35) {
        const d = settings.delay_min + Math.random() * Math.max(0, settings.delay_max - settings.delay_min);
        log('WARN', 'Delay aplicado: ' + d.toFixed(1) + 's');
      }
    }
    if (job.progress >= 100) {
      job.status = 'done';
      delete job.progress;
      log('INFO', 'Download concluído: ' + job.artist + ' — ' + job.album);
      promote();
    }
  }

  function stats() {
    const inLib = pool.filter(a => a.in_library).length;
    const recent = jobs.slice().sort((a, b) => b.id - a.id).slice(0, 10);
    return {
      artists: 32 + inLib,
      albums: 318,
      tracks: 4231,
      size_gb: 12.4,
      recent_albums: recent.map(j => ({ artist: j.artist, title: j.album, status: j.status })),
      recent_jobs: recent,
    };
  }

  /* ---------- roteador ---------- */
  function handle(path, opts = {}) {
    const method = (opts.method || 'GET').toUpperCase();
    let body = {};
    try { body = opts.body ? JSON.parse(opts.body) : {}; } catch (e) { /* noop */ }

    if (path === '/library') return stats();

    if (path === '/artists/search') {
      const q = (body.query || '').toLowerCase();
      return { results: pool.filter(a => a.name.toLowerCase().includes(q)) };
    }

    if (path === '/artists/add') {
      const a = pool.find(x => x.deezer_id === body.deezer_id);
      if (a && !a.in_library) {
        a.in_library = true;
        jobs.unshift(J(++jobSeq, a.name, 'Discografia (' + a.albums + ' álbuns)', 'queued', { tracks: a.albums * 10 }));
        log('INFO', 'Artista adicionado: ' + a.name + ' [' + (body.release_types || []).join(', ') + ']');
      }
      return { ok: true };
    }

    if (path.startsWith('/artists')) {
      const items = pool.filter(a => a.in_library);
      return { items, total: items.length, page: 1 };
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
      if (i >= 0) {
        log('INFO', 'Job cancelado: ' + jobs[i].artist + ' — ' + jobs[i].album);
        jobs.splice(i, 1);
      }
      return { ok: true };
    }

    if (path.startsWith('/downloads')) {
      const m = path.match(/status=(\w+)/);
      const items = m ? jobs.filter(j => j.status === m[1]) : jobs.slice();
      return { items, total: items.length };
    }

    if (path.startsWith('/explorer/related/')) {
      const id = parseInt(path.split('/').pop(), 10);
      const center = pool.find(a => a.deezer_id === id) || null;
      const related = pool.filter((a, i) => a.deezer_id !== id && (i + id) % 3 !== 0).slice(0, 8);
      return { artist: center, related };
    }

    if (path === '/settings' && method === 'GET') return JSON.parse(JSON.stringify(settings));
    if (path === '/settings' && method === 'PUT') {
      Object.assign(settings, body);
      log('INFO', 'Configurações salvas');
      return { ok: true };
    }
    if (path === '/settings/test-arl') {
      return { valid: !!(body.arl && body.arl.trim().length >= 32) };
    }

    if (path === '/logs') return { lines: logs.slice() };
    if (path === '/library/scan') { log('INFO', 'Scan da biblioteca iniciado'); return { started: true }; }
    if (path === '/library/audit') { log('INFO', 'Auditoria da biblioteca iniciada'); return { started: true }; }

    return {};
  }

  return { handle };
})();
