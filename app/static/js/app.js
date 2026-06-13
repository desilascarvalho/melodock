/* ============================================================
   Melodock — js/app.js
   Estado global, sidebar (navegação ativa), polling de status.
   ============================================================ */

const MD = {};

/* ---------- Ícones (SVG inline, stroke) ---------- */
(function () {
  const svg = (inner) =>
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="w-full h-full">' + inner + '</svg>';

  MD.icons = {
    logo: svg('<circle cx="7.5" cy="17.5" r="2.8"/><circle cx="16.5" cy="15.5" r="2.8"/><path d="M10.3 17.5V6.5l9-2.2v11.2"/>'),
    dashboard: svg('<rect x="3" y="3" width="7.5" height="7.5" rx="1.5"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="1.5"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="1.5"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.5"/>'),
    search: svg('<circle cx="11" cy="11" r="7"/><line x1="16.2" y1="16.2" x2="21" y2="21"/>'),
    downloads: svg('<path d="M12 3v11"/><path d="m8 10 4 4 4-4"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>'),
    explorer: svg('<circle cx="12" cy="12" r="9"/><polygon points="14.8,9.2 13.2,13.2 9.2,14.8 10.8,10.8"/>'),
    logs: svg('<polyline points="4 6 9 11 4 16"/><line x1="12" y1="18" x2="20" y2="18"/>'),
    settings: svg('<line x1="4" y1="8" x2="20" y2="8"/><line x1="4" y1="16" x2="20" y2="16"/><circle cx="9.5" cy="8" r="2.4"/><circle cx="14.5" cy="16" r="2.4"/>'),
    menu: svg('<line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/>'),
    artists: svg('<circle cx="12" cy="8" r="4"/><path d="M4 20c1.5-3.5 4.5-5 8-5s6.5 1.5 8 5"/>'),
    disc: svg('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.2"/>'),
    note: svg('<circle cx="7.5" cy="17.5" r="2.8"/><circle cx="16.5" cy="15.5" r="2.8"/><path d="M10.3 17.5V6.5l9-2.2v11.2"/>'),
    storage: svg('<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6"/><path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/>'),
  };
})();

/* ---------- Helpers ---------- */
MD.esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

MD.debounce = (fn, ms) => {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
};

MD.hue = (s) => {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360;
  return h;
};

/* Cover art placeholder: gradiente determinístico + iniciais */
MD.cover = (seed, cls) => {
  const h = MD.hue(seed);
  const ini = seed.split(/\s+/).slice(0, 2).map((w) => w[0]).join('').toUpperCase();
  return '<div class="' + (cls || '') + ' flex items-center justify-center font-bold text-white/55 select-none shrink-0" ' +
    'style="background:linear-gradient(135deg, hsl(' + h + ' 35% 16%), hsl(' + ((h + 45) % 360) + ' 45% 34%))">' + MD.esc(ini) + '</div>';
};

/* Imagem real com fallback para MD.cover */
MD.img = (url, seed, cls, rounded) => {
  const r = rounded || '';
  const fallback = MD.cover(seed || '?', cls);
  if (!url) return fallback;
  const esc_url = MD.esc(url);
  // inline onerror substitui o img pelo placeholder
  const fb = fallback.replace(/"/g, '&quot;').replace(/'/g, '\\x27');
  return '<img src="' + esc_url + '" alt="" class="' + (cls || '') + ' object-cover shrink-0 ' + r + '" loading="lazy" onerror="this.outerHTML=\'' + fb + '\'">';
};

/* Badge de status (mono) */
MD.badge = (status) => {
  const map = {
    done: 'bg-emerald-500/10 text-emerald-400',
    running: 'bg-accent/15 text-accent-light animate-pulse',
    error: 'bg-red-500/10 text-red-400',
    queued: 'bg-white/[0.06] text-txt-sec',
  };
  return '<span class="font-mono text-[11px] px-2 py-0.5 rounded-md ' + (map[status] || map.queued) + '">' + MD.esc(status) + '</span>';
};

MD.fmtFans = (n) => (n >= 1000 ? (n / 1000).toFixed(n >= 100000 ? 0 : 1).replace('.', ',') + 'k' : String(n));

/* Toast no canto inferior direito (3s, fade) */
MD.toast = (msg, type) => {
  let root = document.getElementById('toast-root');
  if (!root) {
    root = document.createElement('div');
    root.id = 'toast-root';
    document.body.appendChild(root);
  }
  const t = document.createElement('div');
  t.className = 'toast ' + (type || 'success');
  t.textContent = msg;
  root.appendChild(t);
  setTimeout(() => {
    t.classList.add('hide');
    setTimeout(() => t.remove(), 450);
  }, 3000);
};

/* ---------- Sidebar ---------- */
const MD_NAV = [
  { page: 'dashboard', label: 'Dashboard', href: 'dashboard.html', icon: 'dashboard' },
  { page: 'search', label: 'Buscar', href: 'search.html', icon: 'search' },
  { page: 'artists-list', label: 'Artistas', href: 'artists-list.html', icon: 'artists' },
  { page: 'downloads', label: 'Downloads', href: 'downloads.html', icon: 'downloads', badge: true },
  { page: 'explorer', label: 'Explorer', href: 'explorer.html', icon: 'explorer' },
  { page: 'logs', label: 'Logs', href: 'logs.html', icon: 'logs' },
  { page: 'settings', label: 'Settings', href: 'settings.html', icon: 'settings' },
];

function renderSidebar() {
  const root = document.getElementById('sidebar-root');
  if (!root) return;
  const current = document.body.dataset.page;

  const links = MD_NAV.map((item) => {
    const active = item.page === current;
    return (
      '<a href="' + item.href + '" class="relative flex items-center gap-3 px-3 py-2 rounded-el text-sm transition-colors ' +
      (active ? 'bg-accent/10 text-white sb-active' : 'text-txt-sec hover:text-white hover:bg-white/5') + '">' +
      '<span class="w-[18px] h-[18px] shrink-0 ' + (active ? 'text-accent-light' : '') + '">' + MD.icons[item.icon] + '</span>' +
      '<span class="font-medium">' + item.label + '</span>' +
      (item.badge
        ? '<span id="queue-badge" class="ml-auto hidden font-mono text-[11px] leading-none bg-accent text-white rounded-full px-1.5 py-1 min-w-[20px] text-center">0</span>'
        : '') +
      '</a>'
    );
  }).join('');

  root.innerHTML =
    /* Topbar mobile */
    '<header class="lg:hidden fixed top-0 inset-x-0 z-40 h-14 bg-base/90 backdrop-blur border-b border-white/5 flex items-center px-4 gap-3">' +
      '<button id="md-hamburger" aria-label="Abrir menu" class="w-9 h-9 flex items-center justify-center rounded-el text-txt-sec hover:text-white hover:bg-white/5"><span class="w-5 h-5">' + MD.icons.menu + '</span></button>' +
      '<div class="w-7 h-7 rounded-lg bg-gradient-to-br from-accent to-accent-light flex items-center justify-center text-white"><span class="w-4 h-4">' + MD.icons.logo + '</span></div>' +
      '<span class="font-bold tracking-tight text-[15px]">Melodock</span>' +
    '</header>' +
    '<div id="md-overlay" class="fixed inset-0 bg-black/60 z-40 hidden lg:hidden"></div>' +
    /* Sidebar */
    '<aside id="md-sidebar" class="fixed top-0 left-0 z-50 h-full w-60 bg-surface border-r border-white/5 flex flex-col -translate-x-full lg:translate-x-0 transition-transform duration-200">' +
      '<div class="flex items-center gap-2.5 px-5 h-16 shrink-0">' +
        '<div class="w-8 h-8 rounded-lg bg-gradient-to-br from-accent to-accent-light flex items-center justify-center text-white"><span class="w-[18px] h-[18px]">' + MD.icons.logo + '</span></div>' +
        '<span class="font-bold tracking-tight text-[15px]">Melodock</span>' +
      '</div>' +
      '<nav class="flex-1 px-3 py-2 flex flex-col gap-1 overflow-y-auto">' + links + '</nav>' +
      '<div class="px-5 py-4 border-t border-white/5 shrink-0">' +
        '<div id="sb-status" class="flex items-center gap-2 text-[13px] text-txt-sec"><span class="w-2 h-2 rounded-full bg-emerald-400 shrink-0"></span><span>Online</span></div>' +
        '<div id="sb-demo" class="hidden text-[11px] text-txt-muted mt-1.5 font-mono">backend offline · modo demo</div>' +
      '</div>' +
    '</aside>';

  /* Hamburger mobile */
  const sidebar = document.getElementById('md-sidebar');
  const overlay = document.getElementById('md-overlay');
  const toggle = (open) => {
    sidebar.classList.toggle('-translate-x-full', !open);
    overlay.classList.toggle('hidden', !open);
  };
  document.getElementById('md-hamburger').addEventListener('click', () => toggle(true));
  overlay.addEventListener('click', () => toggle(false));
}

/* ---------- Status global (polling 3s) ---------- */
function updateSidebarStatus(job) {
  const el = document.getElementById('sb-status');
  if (!el) return;
  if (job && job.status === 'running') {
    el.innerHTML =
      '<span class="w-2 h-2 rounded-full bg-accent-light dot-pulse shrink-0"></span>' +
      '<span>Baixando <span class="font-mono text-accent-light">' + Math.round(job.progress || 0) + '%</span></span>';
  } else {
    el.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-400 shrink-0"></span><span>Online</span>';
  }
  const demo = document.getElementById('sb-demo');
  if (demo) demo.classList.toggle('hidden', window.BACKEND_ONLINE !== false);
}

function updateQueueBadge(n) {
  const b = document.getElementById('queue-badge');
  if (!b) return;
  b.textContent = n;
  b.classList.toggle('hidden', !n);
}

async function pollGlobal() {
  try {
    const job = await getActiveJob();
    updateSidebarStatus(job);
    const dl = await getDownloads('queued');
    updateQueueBadge(dl && dl.total ? dl.total : 0);
  } catch (e) { /* noop */ }
}

/* ---------- Boot ---------- */
document.addEventListener('DOMContentLoaded', () => {
  renderSidebar();
  /* injeta ícones declarados em data-icon */
  document.querySelectorAll('[data-icon]').forEach((el) => {
    el.innerHTML = MD.icons[el.dataset.icon] || '';
  });
  pollGlobal();
  setInterval(pollGlobal, 3000);
});
