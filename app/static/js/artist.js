/* ============================================================
   Melodock — js/artist.js
   Página de detalhe de artista: discografia + faixas + download individual.
   ============================================================ */

let arArtistId = null;
let arAlbums = [];

/* ---------- Helpers ---------- */
function arFmtDuration(sec) {
  if (!sec) return '—';
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m + ':' + String(s).padStart(2, '0');
}

function arTypeBadge(type) {
  const labels = { album: 'Álbum', ep: 'EP', single: 'Single', compilation: 'Compilação' };
  const colors = { album: 'bg-accent/15 text-accent-light', ep: 'bg-blue-500/15 text-blue-400', single: 'bg-white/[0.06] text-txt-sec', compilation: 'bg-white/[0.06] text-txt-sec' };
  const t = (type || '').toLowerCase();
  return '<span class="font-mono text-[10px] px-1.5 py-0.5 rounded ' + (colors[t] || colors.single) + '">' + (labels[t] || type || '?') + '</span>';
}

function arStatusBadge(status) {
  return MD.badge(status);
}

function arQualityBadge(q) {
  if (!q) return '';
  const color = q === 'FLAC' ? 'bg-emerald-500/15 text-emerald-400' : q === 'MP3_320' ? 'bg-accent/15 text-accent-light' : 'bg-white/[0.06] text-txt-sec';
  return '<span class="font-mono text-[10px] px-1.5 py-0.5 rounded ' + color + '">' + MD.esc(q) + '</span>';
}

/* ---------- Render album card (collapsed) ---------- */
function arAlbumCard(album, idx) {
  const year = album.release_date ? album.release_date.slice(0, 4) : '—';
  const trackCount = album.tracks ? album.tracks.length : (album.nb_tracks || 0);
  const missingCount = album.tracks ? album.tracks.filter(t => !t.file_exists).length : 0;
  const missingBadge = missingCount > 0
    ? '<span class="ml-2 font-mono text-[10px] px-1.5 py-0.5 rounded bg-red-500/15 text-red-400">' + missingCount + ' faltando</span>'
    : '';

  return (
    '<div class="bg-surface rounded-card border border-white/5 overflow-hidden" data-album-idx="' + idx + '">' +
      '<button class="album-toggle w-full flex items-center gap-4 px-5 py-4 hover:bg-white/[0.03] transition-colors text-left" data-idx="' + idx + '">' +
        /* cover */
        MD.img(album.cover_url, album.title, 'w-12 h-12 text-xs shrink-0', 'rounded-el') +
        '<div class="flex-1 min-w-0">' +
          '<div class="flex items-center gap-2 flex-wrap">' +
            '<span class="font-semibold text-sm truncate">' + MD.esc(album.title) + '</span>' +
            arTypeBadge(album.album_type) +
            missingBadge +
          '</div>' +
          '<div class="text-xs text-txt-sec mt-0.5">' + year + ' · ' + trackCount + ' faixas</div>' +
        '</div>' +
        '<div class="flex items-center gap-3 shrink-0">' +
          arStatusBadge(album.status) +
          '<svg class="w-4 h-4 text-txt-sec chevron-icon transition-transform duration-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>' +
        '</div>' +
      '</button>' +
      '<div class="tracks-panel hidden border-t border-white/5">' +
        (album.tracks && album.tracks.length
          ? arTrackList(album)
          : '<div class="px-5 py-6 text-txt-sec text-sm text-center">Sem faixas registradas</div>') +
      '</div>' +
    '</div>'
  );
}

/* ---------- Render track list ---------- */
function arTrackList(album) {
  const rows = album.tracks.map(t => arTrackRow(t, album)).join('');
  return '<div class="divide-y divide-white/[0.04]">' + rows + '</div>';
}

function arTrackRow(track, album) {
  const num = track.track_number ? String(track.track_number).padStart(2, '0') : '—';
  const dur = arFmtDuration(track.duration);
  const exists = track.file_exists;

  const statusCol = exists
    ? '<div class="flex items-center gap-2">' + arQualityBadge(track.quality) + '</div>'
    : '<button class="dl-track-btn px-3 py-1 rounded-el bg-accent/15 text-accent-light text-xs font-semibold hover:bg-accent hover:text-white transition-colors flex items-center gap-1.5" ' +
        'data-track-deezer="' + track.deezer_id + '" data-track-id="' + track.id + '" data-track-title="' + MD.esc(track.title) + '">' +
        '<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v11"/><path d="m8 10 4 4 4-4"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg>' +
        'Baixar' +
      '</button>';

  return (
    '<div class="flex items-center gap-3 px-5 py-3 ' + (exists ? '' : 'opacity-70') + '" data-track-row="' + track.id + '">' +
      '<span class="font-mono text-xs text-txt-muted w-6 text-right shrink-0">' + MD.esc(num) + '</span>' +
      '<div class="flex-1 min-w-0">' +
        '<div class="text-sm truncate ' + (exists ? 'text-txt' : 'text-txt-sec') + '">' + MD.esc(track.title) + '</div>' +
      '</div>' +
      '<span class="font-mono text-xs text-txt-muted shrink-0">' + dur + '</span>' +
      '<div class="shrink-0 w-28 flex justify-end">' + statusCol + '</div>' +
    '</div>'
  );
}

/* ---------- Toggle album panel ---------- */
function arToggleAlbum(idx) {
  const card = document.querySelector('[data-album-idx="' + idx + '"]');
  if (!card) return;
  const panel = card.querySelector('.tracks-panel');
  const chevron = card.querySelector('.chevron-icon');
  const isOpen = !panel.classList.contains('hidden');
  panel.classList.toggle('hidden', isOpen);
  chevron.style.transform = isOpen ? '' : 'rotate(180deg)';
}

/* ---------- Queue single track download ---------- */
async function arDownloadTrack(btn) {
  const deezerTrackId = parseInt(btn.dataset.trackDeezer, 10);
  const trackId = parseInt(btn.dataset.trackId, 10);
  const title = btn.dataset.trackTitle;

  btn.disabled = true;
  btn.innerHTML = '<svg class="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.2-8.6"/></svg> Agendando…';

  try {
    await queueTrackDownload(deezerTrackId);
    MD.toast('Faixa adicionada à fila: ' + title);
    btn.innerHTML = '<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> Na fila';
    btn.classList.remove('bg-accent/15', 'text-accent-light', 'hover:bg-accent', 'hover:text-white');
    btn.classList.add('bg-white/[0.06]', 'text-txt-sec', 'cursor-default');
    pollGlobal();
  } catch (err) {
    MD.toast('Erro ao agendar faixa', 'error');
    btn.disabled = false;
    btn.innerHTML = '<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v11"/><path d="m8 10 4 4 4-4"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg> Baixar';
  }
}

/* ---------- Load page ---------- */
async function arLoad() {
  const params = new URLSearchParams(window.location.search);
  arArtistId = parseInt(params.get('id'), 10);
  if (!arArtistId) {
    document.getElementById('artist-name').textContent = 'Artista não encontrado';
    return;
  }

  /* load artist info and albums in parallel */
  const [artist, albums] = await Promise.all([
    getArtist(arArtistId),
    getArtistAlbums(arArtistId),
  ]);

  /* artist header */
  document.title = (artist.name || 'Artista') + ' · Melodock';
  document.getElementById('bc-name').textContent = artist.name || '';
  document.getElementById('artist-name').textContent = artist.name || '';

  const metaParts = [];
  if (artist.followers) metaParts.push(artist.followers.toLocaleString('pt-BR') + ' seguidores');
  if (artist.album_count) metaParts.push(artist.album_count + ' álbuns na biblioteca');
  document.getElementById('artist-meta').textContent = metaParts.join(' · ');

  const photoEl = document.getElementById('artist-photo');
  if (artist.id) {
    const img = document.createElement('img');
    img.src = '/api/artists/' + artist.id + '/picture';
    img.alt = artist.name || '';
    img.className = 'w-full h-full object-cover';
    img.onerror = () => { photoEl.innerHTML = MD.cover(artist.name || '?', 'w-24 h-24 rounded-full text-2xl'); };
    photoEl.innerHTML = '';
    photoEl.appendChild(img);
  }

  /* albums list */
  arAlbums = Array.isArray(albums) ? albums : [];
  const loadingEl = document.getElementById('albums-loading');
  const listEl = document.getElementById('albums-list');

  if (!arAlbums.length) {
    loadingEl.textContent = 'Nenhum álbum encontrado.';
    return;
  }

  loadingEl.classList.add('hidden');
  listEl.innerHTML = arAlbums.map((a, i) => arAlbumCard(a, i)).join('');

  /* event delegation */
  listEl.addEventListener('click', (e) => {
    /* toggle album */
    const toggleBtn = e.target.closest('.album-toggle');
    if (toggleBtn) {
      arToggleAlbum(parseInt(toggleBtn.dataset.idx, 10));
      return;
    }
    /* download track */
    const dlBtn = e.target.closest('.dl-track-btn');
    if (dlBtn && !dlBtn.disabled) {
      arDownloadTrack(dlBtn);
    }
  });

  /* sync button */
  document.getElementById('btn-sync').addEventListener('click', async () => {
    const btn = document.getElementById('btn-sync');
    btn.disabled = true;
    btn.textContent = 'Sincronizando…';
    try {
      const res = await apiFetch('/artists/' + arArtistId + '/sync', { method: 'POST' });
      const msg = (res.new_albums || 0) + ' álbum(ns) novo(s), ' + (res.new_jobs || 0) + ' job(s) criado(s)';
      MD.toast('Sync concluído: ' + msg);
      /* reload albums */
      const newAlbums = await getArtistAlbums(arArtistId);
      arAlbums = Array.isArray(newAlbums) ? newAlbums : [];
      listEl.innerHTML = arAlbums.map((a, i) => arAlbumCard(a, i)).join('');
    } catch (err) {
      MD.toast('Erro ao sincronizar', 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = '↻ Sincronizar';
    }
  });
}

/* ---------- Init ---------- */
document.addEventListener('DOMContentLoaded', () => {
  arLoad();
});
