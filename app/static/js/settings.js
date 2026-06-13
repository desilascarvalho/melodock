/* ============================================================
   Melodock — js/settings.js
   Formulário de configurações + blocklist tags + sliders.
   ============================================================ */

let stBlocklist = [];

/* ---------- Blocklist tags ---------- */
function stRenderTags() {
  const root = document.getElementById('blocklist-tags');
  root.innerHTML = stBlocklist
    .map(
      (w) =>
        '<span class="flex items-center gap-1.5 bg-surface-2 border border-white/10 rounded-full pl-3 pr-1.5 py-1 font-mono text-[12px]">' +
        MD.esc(w) +
        '<button data-remove="' + MD.esc(w) + '" title="Remover" class="w-5 h-5 rounded-full flex items-center justify-center text-txt-sec hover:text-white hover:bg-white/10 transition-colors leading-none">×</button>' +
        '</span>'
    )
    .join('');
}

function stAddTag() {
  const input = document.getElementById('blocklist-input');
  const word = input.value.trim().toLowerCase();
  if (!word) return;
  if (!stBlocklist.includes(word)) {
    stBlocklist.push(word);
    stRenderTags();
  }
  input.value = '';
  input.focus();
}

/* ---------- Sliders (min <= max) ---------- */
function stSliderLabels() {
  document.getElementById('delay-min-val').textContent = parseFloat(document.getElementById('delay-min').value) + 's';
  document.getElementById('delay-max-val').textContent = parseFloat(document.getElementById('delay-max').value) + 's';
}

function stWireSliders() {
  const min = document.getElementById('delay-min');
  const max = document.getElementById('delay-max');
  min.addEventListener('input', () => {
    if (parseFloat(min.value) > parseFloat(max.value)) max.value = min.value;
    stSliderLabels();
  });
  max.addEventListener('input', () => {
    if (parseFloat(max.value) < parseFloat(min.value)) min.value = max.value;
    stSliderLabels();
  });
}

/* ---------- Carregar / salvar ---------- */
async function stLoad() {
  const s = await getSettings();
  if (!s) return;

  document.getElementById('arl').value = s.arl || '';
  document.getElementById('quality').value = s.quality || 'MP3_320';

  const types = s.release_types || [];
  document.querySelectorAll('#release-types input').forEach((cb) => {
    cb.checked = types.includes(cb.value);
  });

  stBlocklist = (s.blocklist || []).slice();
  stRenderTags();

  document.getElementById('max-tracks').value = s.max_tracks ?? 0;
  document.getElementById('delay-min').value = s.delay_min ?? 3;
  document.getElementById('delay-max').value = s.delay_max ?? 8;
  stSliderLabels();

  document.getElementById('access-password').value = s.password || '';
}

async function stSave() {
  const btn = document.getElementById('save-settings');
  btn.disabled = true;
  btn.textContent = 'Salvando…';

  const data = {
    arl: document.getElementById('arl').value.trim(),
    quality: document.getElementById('quality').value,
    release_types: [...document.querySelectorAll('#release-types input:checked')].map((cb) => cb.value),
    blocklist: stBlocklist.slice(),
    max_tracks: Math.max(0, parseInt(document.getElementById('max-tracks').value, 10) || 0),
    delay_min: parseFloat(document.getElementById('delay-min').value),
    delay_max: parseFloat(document.getElementById('delay-max').value),
    password: document.getElementById('access-password').value,
  };

  try {
    await saveSettings(data);
    MD.toast('Configurações salvas');
  } catch (err) {
    MD.toast('Erro ao salvar: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Salvar configurações';
  }
}

/* ---------- Testar ARL ---------- */
async function stTestARL() {
  const btn = document.getElementById('test-arl');
  const fb = document.getElementById('arl-feedback');
  const arl = document.getElementById('arl').value.trim();

  btn.disabled = true;
  btn.textContent = 'Testando…';
  fb.classList.add('hidden');

  const res = await testARL(arl);
  fb.classList.remove('hidden');
  if (res && res.valid) {
    fb.textContent = '✓ ARL válido';
    fb.className = 'text-xs mt-2 font-medium text-emerald-400';
  } else {
    fb.textContent = '✗ ARL inválido';
    fb.className = 'text-xs mt-2 font-medium text-red-400';
  }

  btn.disabled = false;
  btn.textContent = 'Testar ARL';
}

/* ============================================================
   Seção Deemix
   ============================================================ */

const DZ_BOOL_FIELDS = [
  'createArtistFolder', 'createAlbumFolder', 'createCDFolder',
  'createSingleFolder', 'saveArtwork', 'syncedLyrics',
  'createM3U8File',
];

const DZ_TEXT_FIELDS = [
  'artistNameTemplate', 'albumNameTemplate',
  'albumTracknameTemplate', 'tracknameTemplate',
  'coverImageTemplate', 'illegalCharacterReplacer',
];

const DZ_NUM_FIELDS = ['embeddedArtworkSize', 'localArtworkSize'];

const DZ_TAGS_LABELS = {
  title: 'Título', artist: 'Artista', artists: 'Artistas', album: 'Álbum',
  cover: 'Capa', trackNumber: 'Nº faixa', trackTotal: 'Total faixas',
  discNumber: 'Nº disco', discTotal: 'Total discos', albumArtist: 'Artista do álbum',
  genre: 'Gênero', year: 'Ano', date: 'Data', explicit: 'Explícito',
  isrc: 'ISRC', length: 'Duração', barcode: 'Barcode', bpm: 'BPM',
  replayGain: 'ReplayGain', label: 'Gravadora', lyrics: 'Letra',
  syncedLyrics: 'Letra sincronizada', copyright: 'Copyright', composer: 'Compositor',
};

let dzCfg = null;

function dzRenderTags(tags) {
  const root = document.getElementById('dz-tags');
  root.innerHTML = Object.entries(DZ_TAGS_LABELS).map(([key, label]) => {
    const checked = tags && tags[key] ? 'checked' : '';
    return (
      '<label class="flex items-center gap-2.5 cursor-pointer select-none">' +
        '<input type="checkbox" id="dztag-' + key + '" ' + checked + ' class="w-4 h-4 accent-[#7C3AED] cursor-pointer">' +
        '<span class="text-sm text-txt-sec">' + label + '</span>' +
      '</label>'
    );
  }).join('');
}

async function dzLoad() {
  const cfg = await getDeemixSettings();
  if (!cfg || cfg.error) return;
  dzCfg = cfg;

  DZ_BOOL_FIELDS.forEach(f => {
    const el = document.getElementById('dz-' + f);
    if (el) el.checked = !!cfg[f];
  });

  DZ_TEXT_FIELDS.forEach(f => {
    const el = document.getElementById('dz-' + f);
    if (el) el.value = cfg[f] ?? '';
  });

  DZ_NUM_FIELDS.forEach(f => {
    const el = document.getElementById('dz-' + f);
    if (el) el.value = cfg[f] ?? '';
  });

  // overwriteFile é "y"/"n" não boolean
  const owEl = document.getElementById('dz-overwriteFile');
  if (owEl) owEl.checked = cfg.overwriteFile === 'y';

  dzRenderTags(cfg.tags || {});
}

async function dzSave() {
  const btn = document.getElementById('save-deemix');
  btn.disabled = true;
  btn.textContent = 'Salvando…';

  const patch = {};

  DZ_BOOL_FIELDS.forEach(f => {
    const el = document.getElementById('dz-' + f);
    if (el) patch[f] = el.checked;
  });

  DZ_TEXT_FIELDS.forEach(f => {
    const el = document.getElementById('dz-' + f);
    if (el) patch[f] = el.value.trim();
  });

  DZ_NUM_FIELDS.forEach(f => {
    const el = document.getElementById('dz-' + f);
    if (el) patch[f] = parseInt(el.value, 10) || 0;
  });

  const owEl = document.getElementById('dz-overwriteFile');
  if (owEl) patch.overwriteFile = owEl.checked ? 'y' : 'n';

  // tags
  const tags = {};
  Object.keys(DZ_TAGS_LABELS).forEach(key => {
    const el = document.getElementById('dztag-' + key);
    if (el) tags[key] = el.checked;
  });
  patch.tags = { ...(dzCfg && dzCfg.tags ? dzCfg.tags : {}), ...tags };

  try {
    await saveDeemixSettings(patch);
    MD.toast('Config deemix salvo');
  } catch (err) {
    MD.toast('Erro ao salvar deemix: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Salvar';
  }
}

/* ---------- Wiring ---------- */
document.addEventListener('DOMContentLoaded', () => {
  stLoad();
  stWireSliders();

  document.getElementById('blocklist-add').addEventListener('click', stAddTag);
  document.getElementById('blocklist-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      stAddTag();
    }
  });
  document.getElementById('blocklist-tags').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-remove]');
    if (!btn) return;
    stBlocklist = stBlocklist.filter((w) => w !== btn.dataset.remove);
    stRenderTags();
  });

  document.getElementById('test-arl').addEventListener('click', stTestARL);
  document.getElementById('save-settings').addEventListener('click', stSave);
  document.getElementById('save-deemix').addEventListener('click', dzSave);

  dzLoad();

  document.getElementById('scan-library').addEventListener('click', async () => {
    await triggerScan();
    MD.toast('Scan da biblioteca iniciado');
  });
  document.getElementById('run-audit').addEventListener('click', async () => {
    await runAudit();
    MD.toast('Auditoria iniciada');
  });
});
