/* ============================================================
   Melodock — js/logs.js
   Polling 2s · filtro por nível · auto-scroll · limpar (visual).
   ============================================================ */

const LOG_COLORS = { INFO: '#34D399', WARN: '#FBBF24', ERROR: '#F87171' };

let lgAll = [];
let lgCleared = 0;

function lgLine(l) {
  const pad = '\u00A0'.repeat(Math.max(1, 6 - l.level.length));
  return (
    '<div class="whitespace-pre-wrap break-words">' +
      '<span style="color:#A855F7">' + MD.esc(l.ts) + '</span> ' +
      '<span style="color:' + (LOG_COLORS[l.level] || '#8E8E93') + '">[' + MD.esc(l.level) + ']</span>' + pad +
      '<span style="color:#D4D4D8">' + MD.esc(l.msg) + '</span>' +
    '</div>'
  );
}

function lgRender() {
  const view = document.getElementById('log-view');
  const level = document.getElementById('level-filter').value;
  const auto = document.getElementById('auto-scroll').checked;

  const prevScroll = view.scrollTop;
  const lines = lgAll.slice(lgCleared).filter((l) => level === 'ALL' || l.level === level);

  view.innerHTML = lines.length
    ? lines.map(lgLine).join('')
    : '<div style="color:#48484A">— sem entradas —</div>';

  view.scrollTop = auto ? view.scrollHeight : prevScroll;
}

async function lgPoll() {
  const data = await getLogs();
  lgAll = (data && data.lines) || [];
  if (lgCleared > lgAll.length) lgCleared = 0; /* buffer do servidor girou */
  lgRender();
}

document.addEventListener('DOMContentLoaded', () => {
  lgPoll();
  setInterval(lgPoll, 2000);

  document.getElementById('level-filter').addEventListener('change', lgRender);
  document.getElementById('auto-scroll').addEventListener('change', lgRender);
  document.getElementById('clear-logs').addEventListener('click', () => {
    lgCleared = lgAll.length; /* só limpa a visualização, não o servidor */
    lgRender();
  });
});
