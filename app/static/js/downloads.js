/* ============================================================
   Melodock — js/downloads.js
   Polling 2s: job atual + fila.
   ============================================================ */

let dlLastActiveId = null;

function dlRenderActive(job) {
  const card = document.getElementById('active-card');

  if (!job) {
    dlLastActiveId = null;
    card.innerHTML =
      '<div class="bg-surface rounded-card border border-white/5 border-dashed p-8 text-center text-txt-muted text-sm">Nenhum download em andamento</div>';
    return;
  }

  const p = Math.round(job.progress || 0);

  /* mesmo job → só atualiza barra/percentual (transição suave) */
  if (job.id === dlLastActiveId) {
    const bar = document.getElementById('active-bar');
    const pct = document.getElementById('active-pct');
    const trk = document.getElementById('active-track');
    if (bar) bar.style.width = p + '%';
    if (pct) pct.textContent = p + '%';
    if (trk) trk.textContent = 'Track ' + (job.track || 1) + '/' + (job.tracks || '?');
    return;
  }

  dlLastActiveId = job.id;
  card.innerHTML =
    '<div class="relative bg-surface-2 border border-accent/40 rounded-card p-5 overflow-hidden">' +
      '<div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-accent to-accent-light"></div>' +
      '<div class="flex items-center gap-4">' +
        MD.cover(job.artist + ' ' + job.album, 'w-16 h-16 rounded-el text-sm') +
        '<div class="flex-1 min-w-0">' +
          '<div class="flex items-center justify-between gap-3">' +
            '<div class="font-semibold truncate"><span>' + MD.esc(job.artist) + '</span><span class="text-txt-sec font-normal"> — ' + MD.esc(job.album) + '</span></div>' +
            '<span class="font-mono text-[11px] text-txt-sec bg-white/5 px-2 py-1 rounded-md shrink-0">' + MD.esc(job.quality || 'MP3 320kbps') + '</span>' +
          '</div>' +
          '<div id="active-track" class="text-xs text-txt-sec mt-1">Track ' + (job.track || 1) + '/' + (job.tracks || '?') + '</div>' +
          '<div class="mt-3 flex items-center gap-3">' +
            '<div class="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">' +
              '<div id="active-bar" class="h-full bg-gradient-to-r from-accent to-accent-light rounded-full transition-all duration-500" style="width:' + p + '%"></div>' +
            '</div>' +
            '<span id="active-pct" class="font-mono text-sm text-accent-light tabular-nums w-11 text-right">' + p + '%</span>' +
          '</div>' +
        '</div>' +
      '</div>' +
    '</div>';
}

function dlQueueRow(job) {
  return (
    '<div class="flex items-center gap-3 px-4 py-3">' +
      MD.cover(job.artist + ' ' + job.album, 'w-10 h-10 rounded-el text-[10px]') +
      '<div class="flex-1 min-w-0">' +
        '<div class="text-sm truncate"><span class="font-medium">' + MD.esc(job.artist) + '</span><span class="text-txt-sec"> — ' + MD.esc(job.album) + '</span></div>' +
        (job.error ? '<div class="text-xs text-red-400/80 mt-0.5 truncate">⚠ ' + MD.esc(job.error) + '</div>' : '') +
      '</div>' +
      MD.badge(job.status) +
      (job.status === 'queued'
        ? '<button data-cancel="' + job.id + '" title="Cancelar" class="w-7 h-7 rounded-el flex items-center justify-center text-txt-sec hover:text-red-400 hover:bg-red-500/10 transition-colors">✕</button>'
        : '') +
    '</div>'
  );
}

function dlRenderQueue(items) {
  const list = document.getElementById('queue-list');
  const count = document.getElementById('queue-count');
  const order = { queued: 0, error: 1, done: 2 };
  const sorted = items.slice().sort((a, b) => (order[a.status] ?? 3) - (order[b.status] ?? 3) || b.id - a.id);

  const queuedN = items.filter((j) => j.status === 'queued').length;
  count.textContent = '(' + queuedN + (queuedN === 1 ? ' job)' : ' jobs)');

  list.innerHTML = sorted.length
    ? sorted.map(dlQueueRow).join('')
    : '<div class="text-center text-txt-muted text-sm py-10">Fila vazia</div>';
}

async function dlRefresh() {
  const [job, all] = await Promise.all([getActiveJob(), getDownloads()]);
  dlRenderActive(job);
  dlRenderQueue(((all && all.items) || []).filter((j) => j.status !== 'running'));
}

document.addEventListener('DOMContentLoaded', () => {
  dlRefresh();
  setInterval(dlRefresh, 2000);

  document.getElementById('queue-list').addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-cancel]');
    if (!btn) return;
    btn.disabled = true;
    await cancelJob(parseInt(btn.dataset.cancel, 10));
    MD.toast('Job cancelado');
    dlRefresh();
    pollGlobal();
  });

  document.getElementById('clear-completed').addEventListener('click', async () => {
    await clearCompleted();
    MD.toast('Jobs concluídos removidos');
    dlRefresh();
  });
});
