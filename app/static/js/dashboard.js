/* ============================================================
   Melodock — js/dashboard.js
   ============================================================ */

function dbSetText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function dbAlbumCard(album) {
  const seed = album.artist + ' ' + album.title;
  const img = album.cover_url
    ? MD.img(album.cover_url, seed, 'absolute inset-0 w-full h-full text-2xl')
    : MD.cover(seed, 'absolute inset-0 text-2xl');
  return (
    '<div class="group relative aspect-square rounded-card overflow-hidden">' +
      img +
      '<div class="absolute inset-0 bg-gradient-to-t from-black/85 via-black/25 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex flex-col justify-end p-3">' +
        '<div class="text-sm font-semibold leading-tight">' + MD.esc(album.title) + '</div>' +
        '<div class="text-xs text-txt-sec mt-0.5">' + MD.esc(album.artist) + '</div>' +
        '<div class="mt-2">' + MD.badge(album.status) + '</div>' +
      '</div>' +
    '</div>'
  );
}

function dbJobRow(job) {
  return (
    '<div class="flex items-center gap-3 px-4 py-3">' +
      MD.cover(job.artist + ' ' + job.album, 'w-9 h-9 rounded-el text-[10px] shrink-0') +
      '<div class="flex-1 min-w-0">' +
        '<div class="text-sm truncate"><span class="font-medium">' + MD.esc(job.artist) + '</span><span class="text-txt-sec"> — ' + MD.esc(job.album) + '</span></div>' +
      '</div>' +
      (job.status === 'running' && job.progress != null
        ? '<span class="font-mono text-[11px] text-accent-light">' + Math.round(job.progress) + '%</span>'
        : '') +
      MD.badge(job.status) +
    '</div>'
  );
}

async function loadDashboard() {
  const lib = await getLibraryStats();
  if (!lib) return;

  dbSetText('stat-artists', lib.artists ?? '—');
  dbSetText('stat-albums', lib.albums ?? '—');
  dbSetText('stat-tracks', lib.tracks >= 1000 ? (lib.tracks / 1000).toFixed(1).replace('.', ',') + 'k' : lib.tracks);
  dbSetText('stat-size', (lib.size_gb ?? '—') + ' GB');

  const grid = document.getElementById('album-grid');
  const albums = (lib.recent_albums || []).slice(0, 10);
  grid.innerHTML = albums.length
    ? albums.map(dbAlbumCard).join('')
    : '<div class="col-span-full text-center text-txt-muted text-sm py-10">Nenhum álbum ainda — adicione um artista em Buscar</div>';

  const list = document.getElementById('job-list');
  const jobsRecent = (lib.recent_jobs || []).slice(0, 10);
  list.innerHTML = jobsRecent.length
    ? jobsRecent.map(dbJobRow).join('')
    : '<div class="text-center text-txt-muted text-sm py-10">Nenhum job recente</div>';
}

document.addEventListener('DOMContentLoaded', () => {
  loadDashboard();
  /* atualização leve para refletir progresso dos jobs */
  setInterval(loadDashboard, 10000);
});
