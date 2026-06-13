/* ============================================================
   Melodock — js/explorer.js
   Artista central → relacionados (4 colunas).
   ============================================================ */

let exRelated = [];

function exArtistPhoto(artist, cls) {
  if (artist.library_id) return MD.artistImg(artist.library_id, artist.name, cls);
  if (artist.picture_url) {
    const fallbackHtml = MD.cover(artist.name, cls).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '&quot;');
    return '<div class="' + cls + ' overflow-hidden shrink-0"><img src="' + MD.esc(artist.picture_url) + '" class="w-full h-full object-cover rounded-full" loading="lazy" onerror="this.parentElement.outerHTML=\'' + fallbackHtml + '\'"></div>';
  }
  return MD.cover(artist.name, cls);
}

function exCard(artist) {
  const action = artist.in_library
    ? '<span class="block w-full py-2 rounded-el bg-white/[0.04] text-txt-sec text-xs font-medium text-center">✓ Na biblioteca</span>'
    : '<button data-add="' + artist.deezer_id + '" class="w-full py-2 rounded-el bg-accent hover:bg-accent-hover text-white text-xs font-semibold transition-colors">+ Adicionar</button>';
  return (
    '<div class="bg-surface rounded-card border border-white/5 p-5 flex flex-col items-center text-center" data-card="' + artist.deezer_id + '">' +
      exArtistPhoto(artist, 'w-20 h-20 rounded-full text-lg') +
      '<div class="mt-3 font-semibold text-sm leading-tight">' + MD.esc(artist.name) + '</div>' +
      '<div class="text-xs text-txt-sec mt-1">' + (artist.nb_album || 0) + ' álbuns</div>' +
      '<div class="mt-4 w-full">' + action + '</div>' +
    '</div>'
  );
}

async function exLoadRelated(id) {
  const grid = document.getElementById('related-grid');
  const title = document.getElementById('related-title');
  const stateEl = document.getElementById('explorer-state');

  stateEl.textContent = 'Buscando relacionados…';
  stateEl.classList.remove('hidden');
  grid.innerHTML = '';
  title.classList.add('hidden');

  const data = await getRelatedArtists(id);
  exRelated = (data && data.related) || [];

  if (!exRelated.length) {
    stateEl.textContent = 'Nenhum artista relacionado encontrado';
    return;
  }
  stateEl.classList.add('hidden');
  title.classList.remove('hidden');
  grid.innerHTML = exRelated.map(exCard).join('');
}

async function exInit() {
  const select = document.getElementById('artist-select');
  const stateEl = document.getElementById('explorer-state');

  const data = await getArtists(1, '');
  const items = (data && data.items) || [];

  if (!items.length) {
    stateEl.textContent = 'Sua biblioteca está vazia — adicione artistas em Buscar';
    return;
  }

  select.innerHTML = items
    .map((a) => '<option value="' + a.deezer_id + '">' + MD.esc(a.name) + '</option>')
    .join('');

  select.addEventListener('change', () => exLoadRelated(parseInt(select.value, 10)));
  exLoadRelated(items[0].deezer_id);
}

document.addEventListener('DOMContentLoaded', () => {
  exInit();

  document.getElementById('related-grid').addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-add]');
    if (!btn) return;
    const artist = exRelated.find((a) => a.deezer_id === parseInt(btn.dataset.add, 10));
    if (!artist) return;

    btn.disabled = true;
    btn.textContent = 'Adicionando…';
    await addArtist(artist.deezer_id, { release_types: ['album', 'ep'], auto_download: true });
    artist.in_library = true;
    btn.outerHTML = '<span class="block w-full py-2 rounded-el bg-white/[0.04] text-txt-sec text-xs font-medium text-center">✓ Na biblioteca</span>';
    MD.toast(artist.name + ' adicionado à biblioteca');
    pollGlobal();
  });
});
