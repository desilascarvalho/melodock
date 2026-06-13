/* ============================================================
   Melodock — js/logs.js
   Polling 2s · filtro por nível · auto-scroll · limpar (visual).
   ============================================================ */

const LOG_COLORS = {
  INFO:    { text: '#D4D4D8', badge: '#3F3F46', label: '#A1A1AA' },
  WARNING: { text: '#FDE68A', badge: '#78350F', label: '#FCD34D' },
  WARN:    { text: '#FDE68A', badge: '#78350F', label: '#FCD34D' },
  ERROR:   { text: '#FCA5A5', badge: '#7F1D1D', label: '#F87171' },
  DEBUG:   { text: '#93C5FD', badge: '#1E3A5F', label: '#60A5FA' },
};

/* emoji por palavra-chave na mensagem */
const EMOJI_MAP = [
  [/^⬇️/, ''],   // já tem emoji
  [/^✅/, ''],
  [/^❌/, ''],
  [/^⚙️/, ''],
  [/^🎤/, ''],
  [/^🔄/, ''],
  [/^🗑️/, ''],
  [/^🔑/, ''],
  [/^📚/, ''],
  [/^🚀/, ''],
  [/^🧹/, ''],
  [/^➕/, ''],
];

function lgEmoji(msg) {
  for (const [re] of EMOJI_MAP) {
    if (re.test(msg)) return ''; // já tem emoji, não adiciona
  }
  // mensagens sem emoji — inferir pelo conteúdo
  if (/erro|error|falhou|failed|exception/i.test(msg)) return '❌ ';
  if (/aviso|warn/i.test(msg)) return '⚠️ ';
  if (/download|baixand/i.test(msg)) return '⬇️ ';
  if (/conclu|done|complete/i.test(msg)) return '✅ ';
  if (/artista|artist/i.test(msg)) return '🎤 ';
  if (/scan|biblioteca/i.test(msg)) return '📚 ';
  if (/config|setting/i.test(msg)) return '⚙️ ';
  if (/iniciado|start|startup/i.test(msg)) return '🚀 ';
  return '';
}

function lgLine(l) {
  const c = LOG_COLORS[l.level] || LOG_COLORS.INFO;
  const ts = l.ts ? new Date(l.ts).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '??:??:??';
  const emoji = lgEmoji(l.msg);
  const msg = emoji + MD.esc(l.msg);

  return (
    '<div class="flex gap-3 px-4 py-2 hover:bg-white/[0.02] rounded transition-colors">' +
      '<span class="font-mono text-[11px] shrink-0 mt-0.5" style="color:#52525B">' + ts + '</span>' +
      '<span class="font-mono text-[10px] shrink-0 mt-0.5 px-1.5 py-0.5 rounded self-start" style="background:' + c.badge + ';color:' + c.label + '">' + l.level + '</span>' +
      '<span class="text-[13px] leading-5 break-words min-w-0" style="color:' + c.text + '">' + msg + '</span>' +
    '</div>'
  );
}

let lgAll = [];
let lgCleared = 0;

function lgRender() {
  const view = document.getElementById('log-view');
  const level = document.getElementById('level-filter').value;
  const auto = document.getElementById('auto-scroll').checked;
  const search = (document.getElementById('log-search') || {}).value || '';

  const prevScroll = view.scrollTop;
  let lines = lgAll.slice(lgCleared);

  if (level !== 'ALL') {
    lines = lines.filter(l => (l.level || 'INFO') === level || (level === 'WARN' && l.level === 'WARNING'));
  }
  if (search.trim()) {
    const q = search.trim().toLowerCase();
    lines = lines.filter(l => l.msg.toLowerCase().includes(q));
  }

  if (!lines.length) {
    view.innerHTML = '<div class="px-4 py-8 text-center font-mono text-[13px]" style="color:#48484A">— sem entradas —</div>';
  } else {
    view.innerHTML = lines.map(lgLine).join('');
  }

  view.scrollTop = auto ? view.scrollHeight : prevScroll;
}

async function lgPoll() {
  const data = await getLogs();
  lgAll = (data && data.lines) || [];
  if (lgCleared > lgAll.length) lgCleared = 0;
  lgRender();
}

document.addEventListener('DOMContentLoaded', () => {
  lgPoll();
  setInterval(lgPoll, 2000);

  document.getElementById('level-filter').addEventListener('change', lgRender);
  document.getElementById('auto-scroll').addEventListener('change', lgRender);
  document.getElementById('clear-logs').addEventListener('click', () => {
    lgCleared = lgAll.length;
    lgRender();
  });

  const searchEl = document.getElementById('log-search');
  if (searchEl) searchEl.addEventListener('input', MD.debounce(lgRender, 200));
});
