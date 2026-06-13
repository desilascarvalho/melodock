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

  // rclone
  const rcEnabled = document.getElementById('rclone-enabled');
  const rcRemote  = document.getElementById('rclone-remote');
  const rcFlags   = document.getElementById('rclone-flags');
  if (rcEnabled) rcEnabled.checked = s.rclone_enabled !== false;
  if (rcRemote)  rcRemote.value   = s.rclone_remote || 'google:media/music';
  if (rcFlags)   rcFlags.value    = s.rclone_flags  || '';
}

async function stSave() {
  const btn = document.getElementById('save-settings');
  btn.disabled = true;
  btn.textContent = 'Salvando…';

  const rcEnabled = document.getElementById('rclone-enabled');
  const rcRemote  = document.getElementById('rclone-remote');
  const rcFlags   = document.getElementById('rclone-flags');

  const data = {
    arl: document.getElementById('arl').value.trim(),
    quality: document.getElementById('quality').value,
    release_types: [...document.querySelectorAll('#release-types input:checked')].map((cb) => cb.value),
    blocklist: stBlocklist.slice(),
    max_tracks: Math.max(0, parseInt(document.getElementById('max-tracks').value, 10) || 0),
    delay_min: parseFloat(document.getElementById('delay-min').value),
    delay_max: parseFloat(document.getElementById('delay-max').value),
    password: document.getElementById('access-password').value,
    rclone_enabled: rcEnabled ? rcEnabled.checked : undefined,
    rclone_remote:  rcRemote  ? rcRemote.value.trim() : undefined,
    rclone_flags:   rcFlags   ? rcFlags.value.trim()  : undefined,
  };
  // strip undefined
  Object.keys(data).forEach(k => data[k] === undefined && delete data[k]);

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

  document.getElementById('scan-library').addEventListener('click', async () => {
    await triggerScan();
    MD.toast('Scan da biblioteca iniciado');
  });
  document.getElementById('run-audit').addEventListener('click', async () => {
    await runAudit();
    MD.toast('Auditoria iniciada');
  });
});
