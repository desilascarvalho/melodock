/* ============================================================
   Melodock — js/search.js
   Busca com debounce 400ms + modal de adição.
   ============================================================ */

let scCurrentArtist = null;
let scLastQuery = '';

function scArtistPhoto(artist, cls) {
  if (artist.library_id) return MD.artistImg(artist.library_id, artist.name, cls);
  if (artist.picture_url) {
    const fallbackHtml = MD.cover(artist.name, cls).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '&quot;');
    return '<div class="' + cls + ' overflow-hidden shrink-0"><img src="' + MD.esc(artist.picture_url) + '" class="w-full h-full object-cover rounded-full" loading="lazy" onerror="this.parentElement.outerHTML=\'' + fallbackHtml + '\'"></div>';
  }
  return MD.cover(artist.name, cls);
}

function scCard(artist) {
  const action = artist.in_library
    ? '<span class="block w-full py-2 rounded-el bg-white/[0.04] text-txt-sec text-xs font-medium text-center">✓ Na biblioteca</span>'
    : '<button data-add="' + artist.deezer_id + '" class="w-full py-2 rounded-el bg-accent hover:bg-accent-hover text-white text-xs font-semibold transition-colors">+ Adicionar</button>';
  return (
    '<div class="bg-surface rounded-card border border-white/5 p-5 flex flex-col items-center text-center" data-card="' + artist.deezer_id + '">' +
      scArtistPhoto(artist, 'w-20 h-20 rounded-full text-lg') +
      '<div class="mt-3 font-semibold text-sm leading-tight">' + MD.esc(artist.name) + '</div>' +
      '<div class="text-xs text-txt-sec mt-1">' + (artist.nb_album || 0) + ' álbuns · ' + MD.fmtFans(artist.followers || 0) + ' fãs</div>' +
      '<div class="mt-4 w-full">' + action + '</div>' +
    '</div>'
  );
}

async function scSearch() {
  const input = document.getElementById('search-input');
  const stateEl = document.getElementById('search-state');
  const results = document.getElementById('results');
  const q = input.value.trim();
  scLastQuery = q;

  if (q.length < 2) {
    results.innerHTML = '';
    stateEl.textContent = 'Digite ao menos 2 caracteres para buscar';
    stateEl.classList.remove('hidden');
    return;
  }

  stateEl.textContent = 'Buscando…';
  stateEl.classList.remove('hidden');

  const data = await searchArtists(q);
  if (q !== scLastQuery) return; /* resposta antiga, descarta */

  const list = (data && data.results) || [];
  if (!list.length) {
    results.innerHTML = '';
    stateEl.textContent = 'Nenhum artista encontrado para “' + q + '”';
    return;
  }
  stateEl.classList.add('hidden');
  results.innerHTML = list.map(scCard).join('');
  scCurrentResults = list;
}

let scCurrentResults = [];

/* ---------- Modal ---------- */
function scOpenModal(artist) {
  scCurrentArtist = artist;
  const modal = document.getElementById('add-modal');
  document.getElementById('modal-photo').innerHTML = scArtistPhoto(artist, 'w-14 h-14 rounded-full text-base');
  document.getElementById('modal-name').textContent = artist.name;
  document.getElementById('modal-meta').textContent = artist.albums + ' álbuns · ' + MD.fmtFans(artist.fans) + ' fãs no Deezer';

  /* reset: Album + EP marcados, auto on */
  document.querySelectorAll('#modal-types input').forEach((cb) => {
    cb.checked = cb.value === 'album' || cb.value === 'ep';
  });
  document.getElementById('modal-auto').checked = true;
  scSetModalError('');
  const confirm = document.getElementById('modal-confirm');
  confirm.disabled = false;
  confirm.textContent = 'Adicionar à biblioteca';

  modal.classList.remove('hidden');
  modal.classList.add('flex');
}

function scCloseModal() {
  const modal = document.getElementById('add-modal');
  modal.classList.add('hidden');
  modal.classList.remove('flex');
  scCurrentArtist = null;
}

function scSetModalError(msg) {
  const el = document.getElementById('modal-error');
  el.textContent = msg;
  el.classList.toggle('hidden', !msg);
}

async function scConfirmAdd() {
  if (!scCurrentArtist) return;
  const types = [...document.querySelectorAll('#modal-types input:checked')].map((cb) => cb.value);
  if (!types.length) {
    scSetModalError('Selecione ao menos um tipo de release.');
    return;
  }
  scSetModalError('');

  const confirm = document.getElementById('modal-confirm');
  confirm.disabled = true;
  confirm.textContent = 'Adicionando…';

  try {
    const res = await addArtist(scCurrentArtist.deezer_id, {
      release_types: types,
      auto_download: document.getElementById('modal-auto').checked,
    });
    if (res && res.ok === false) throw new Error(res.error || 'Falha ao adicionar');

    /* atualiza card para "Na biblioteca" */
    const card = document.querySelector('[data-card="' + scCurrentArtist.deezer_id + '"] [data-add]');
    if (card) {
      card.outerHTML = '<span class="block w-full py-2 rounded-el bg-white/[0.04] text-txt-sec text-xs font-medium text-center">✓ Na biblioteca</span>';
    }
    const found = scCurrentResults.find((a) => a.deezer_id === scCurrentArtist.deezer_id);
    if (found) found.in_library = true;

    MD.toast(scCurrentArtist.name + ' adicionado à biblioteca');
    scCloseModal();
    pollGlobal(); /* atualiza badge da fila */
  } catch (err) {
    scSetModalError('Erro: ' + err.message);
    confirm.disabled = false;
    confirm.textContent = 'Adicionar à biblioteca';
  }
}

/* ---------- Wiring ---------- */
document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('search-input');
  input.addEventListener('input', MD.debounce(scSearch, 400));
  input.focus();

  document.getElementById('results').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-add]');
    if (!btn) return;
    const artist = scCurrentResults.find((a) => a.deezer_id === parseInt(btn.dataset.add, 10));
    if (artist) scOpenModal(artist);
  });

  document.getElementById('modal-cancel').addEventListener('click', scCloseModal);
  document.getElementById('modal-backdrop').addEventListener('click', scCloseModal);
  document.getElementById('modal-confirm').addEventListener('click', scConfirmAdd);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') scCloseModal();
  });
});
