/* ============================================================
   MELODOCK — View renderers
   Each returns an HTML string mounted into #content
   ============================================================ */

const icon = (n, cls) => `<span class="material-symbols-rounded ${cls || ''}">${n}</span>`;

/* ============================================================
   1. LIBRARY DASHBOARD
   ============================================================ */
function viewDashboard() {
  const statCards = [
    { icon: 'artist', val: STATS.artists, label: 'Artists', trend: '+12 this month', cls: '' },
    { icon: 'album', val: STATS.albums.toLocaleString(), label: 'Albums', trend: '+48 this month', cls: 'green' },
    { icon: 'music_note', val: STATS.tracks.toLocaleString(), label: 'Tracks', trend: '+612 this month', cls: 'amber' },
    { icon: 'database', val: STATS.size_gb, label: 'Library Size', suffix: 'GB', trend: '62% of 665 GB', cls: 'red' },
  ].map((s, i) => `
    <div class="stat-card ${s.cls}" style="animation-delay:${i * 60}ms">
      <div class="stat-icon">${icon(s.icon, 'ms-fill')}</div>
      <div class="stat-value">${s.val}${s.suffix ? `<small>${s.suffix}</small>` : ''}</div>
      <div class="stat-label">${s.label}</div>
      <div class="stat-trend ${s.cls === 'red' ? 'muted-trend' : 'up'}">${s.cls === 'red' ? `<span class="muted">${s.trend}</span>` : `${icon('trending_up')} ${s.trend}`}</div>
    </div>`).join('');

  return `
  <div class="view" data-screen-label="Dashboard">
    <div class="content-inner">
      <div class="page-head">
        <div class="page-head-row">
          <div>
            <h1>Your Library</h1>
            <p>A complete overview of everything Melodock has collected and organized for you.</p>
          </div>
          <button class="btn btn-secondary" onclick="go('explorer')">${icon('travel_explore')} Discover artists</button>
        </div>
      </div>

      <div class="stat-grid stagger">${statCards}</div>

      <div class="section">
        <div class="tabs" id="lib-tabs">
          <button class="tab active" data-tab="all">All Artists <span class="count">${ARTISTS.length}</span></button>
          <button class="tab" data-tab="recent">Recently Added</button>
          <button class="tab" data-tab="top">Top Charts</button>
        </div>
        <div style="margin-top:24px" id="artist-grid">${artistGrid(ARTISTS.slice(0, 12))}</div>
      </div>

      ${pagination(1, 21)}
    </div>
  </div>`;
}

function artistGrid(list) {
  if (!list.length) return `<div class="empty-hint">${icon('search_off')}<div>No artists match your search.</div></div>`;
  return `<div class="card-grid stagger">${list.map((a, i) => `
    <div class="artist-card" style="animation-delay:${i * 40}ms" onclick="go('artist','${a.id}')">
      <div class="artist-cover-wrap">
        ${cover(a.name)}
        <div class="artist-overlay">
          <button class="overlay-btn" onclick="event.stopPropagation();toast('accent','play_circle','Playing','Now playing ${a.name}')" aria-label="Play">${icon('play_arrow', 'ms-fill')}</button>
          <button class="overlay-btn play" onclick="event.stopPropagation();go('artist','${a.id}')" aria-label="View">${icon('visibility')}</button>
          <button class="overlay-btn" onclick="event.stopPropagation();toast('accent','favorite','Favorited','${a.name} added to favorites')" aria-label="Favorite">${icon('favorite')}</button>
        </div>
      </div>
      <div class="artist-name">${a.name}</div>
      <div class="artist-meta">${a.albums_count} albums • ${a.tracks_count} tracks</div>
    </div>`).join('')}</div>`;
}

function pagination(active, total) {
  const pages = [1, 2, 3, 4, 5];
  return `<div class="pagination">
    <button class="page-btn" ${active === 1 ? 'disabled' : ''} aria-label="Previous">${icon('chevron_left')}</button>
    ${pages.map(p => `<button class="page-btn ${p === active ? 'active' : ''}">${p}</button>`).join('')}
    <span style="color:var(--text-muted);padding:0 6px">…</span>
    <button class="page-btn">${total}</button>
    <button class="page-btn" aria-label="Next">${icon('chevron_right')}</button>
  </div>`;
}

/* ============================================================
   2. DOWNLOADS QUEUE
   ============================================================ */
function viewDownloads() {
  return `
  <div class="view" data-screen-label="Downloads">
    <div class="content-inner">
      <div class="page-head">
        <h1>Download Queue</h1>
        <p>Live status of everything currently being fetched, tagged, and filed into your library.</p>
      </div>

      <div class="stat-grid" style="grid-template-columns:repeat(3,1fr);margin-bottom:26px">
        <div class="stat-card"><div class="stat-icon">${icon('downloading', 'ms-fill')}</div><div class="stat-value" id="dl-active-count">${DL_ACTIVE.length}</div><div class="stat-label">Active downloads</div></div>
        <div class="stat-card green"><div class="stat-icon">${icon('task_alt', 'ms-fill')}</div><div class="stat-value" id="dl-done-count">${DL_COMPLETED.length}</div><div class="stat-label">Completed today</div></div>
        <div class="stat-card red"><div class="stat-icon">${icon('error', 'ms-fill')}</div><div class="stat-value" id="dl-err-count">${DL_ERRORS.length}</div><div class="stat-label">Failed</div></div>
      </div>

      <div class="queue-widget">
        <div class="qw-icon">${icon('bolt', 'ms-fill')}</div>
        <div class="qw-body">
          <div class="qw-top">
            <span class="qw-title">Processing queue</span>
            <span class="qw-pct" id="qw-pct">—</span>
          </div>
          <div class="progress"><div class="fill shimmer" id="qw-fill" style="width:0%"></div></div>
          <div class="qw-sub">
            <span><b id="qw-items">0</b> of ${DL_ACTIVE.length + DL_COMPLETED.length} items</span>
            <span>Est. <b id="qw-eta">~4 min</b> remaining</span>
            <span>Avg <b>4.0 MB/s</b></span>
          </div>
        </div>
      </div>

      <div class="tabs" id="dl-tabs">
        <button class="tab active" data-tab="active">Active <span class="count" id="t-active">${DL_ACTIVE.length}</span></button>
        <button class="tab" data-tab="completed">Completed <span class="count">${DL_COMPLETED.length}</span></button>
        <button class="tab" data-tab="errors">Errors <span class="count">${DL_ERRORS.length}</span></button>
      </div>

      <div style="margin-top:20px" id="dl-table-mount">${dlActiveTable()}</div>
    </div>
  </div>`;
}

function dlActiveTable() {
  return `<div class="table-wrap"><table class="dl-table">
    <thead><tr><th>Track</th><th>Quality</th><th>Progress</th><th>Speed</th><th style="text-align:right">Actions</th></tr></thead>
    <tbody id="dl-active-body">
    ${DL_ACTIVE.map(d => dlActiveRow(d)).join('')}
    </tbody></table></div>`;
}
function dlActiveRow(d) {
  return `<tr data-id="${d.id}" onclick="openLogs('${d.track}')">
    <td><div class="track-cell">${cover(d.album, null, 'track-thumb')}<div><div class="track-title">${d.track}</div><div class="track-sub">${d.artist} • ${d.album}</div></div></div></td>
    <td><span class="badge badge-neutral">${d.quality}</span></td>
    <td style="min-width:200px"><div style="display:flex;align-items:center;gap:10px"><div class="progress thin" style="flex:1"><div class="fill shimmer" style="width:${d.progress}%"></div></div><span class="tnum" style="font-size:12px;color:var(--text-secondary);min-width:34px">${d.progress}%</span></div></td>
    <td class="tnum" style="color:var(--text-secondary)">${d.speed}</td>
    <td><div class="row-actions">
      <button class="row-act" onclick="event.stopPropagation();openLogs('${d.track}')" aria-label="Logs">${icon('terminal')}</button>
      <button class="row-act" onclick="event.stopPropagation();toast('accent','pause','Paused','${d.track} paused')" aria-label="Pause">${icon('pause')}</button>
      <button class="row-act danger" onclick="event.stopPropagation();toast('error','delete','Removed','${d.track} removed from queue')" aria-label="Cancel">${icon('close')}</button>
    </div></td>
  </tr>`;
}
function dlCompletedTable() {
  return `<div class="table-wrap"><table class="dl-table">
    <thead><tr><th>Track</th><th>Quality</th><th>Size</th><th>Status</th><th style="text-align:right">Actions</th></tr></thead>
    <tbody>${DL_COMPLETED.map(d => `<tr onclick="openLogs('${d.track}')">
      <td><div class="track-cell">${cover(d.album, null, 'track-thumb')}<div><div class="track-title">${d.track}</div><div class="track-sub">${d.artist} • ${d.album}</div></div></div></td>
      <td><span class="badge badge-neutral">${d.quality}</span></td>
      <td class="tnum" style="color:var(--text-secondary)">${d.size}</td>
      <td><span class="badge badge-success">${icon('check')} Done · ${d.when}</span></td>
      <td><div class="row-actions">
        <button class="row-act" onclick="event.stopPropagation();toast('accent','folder_open','Revealed','Opened in library')" aria-label="Open">${icon('folder_open')}</button>
        <button class="row-act danger" onclick="event.stopPropagation();toast('error','delete','Deleted','File removed')" aria-label="Delete">${icon('delete')}</button>
      </div></td></tr>`).join('')}</tbody></table></div>`;
}
function dlErrorsTable() {
  if (!DL_ERRORS.length) return `<div class="empty-hint">${icon('verified')}<div>No failed downloads. Everything's healthy.</div></div>`;
  return `<div class="table-wrap"><table class="dl-table">
    <thead><tr><th>Track</th><th>Quality</th><th>Reason</th><th style="text-align:right">Actions</th></tr></thead>
    <tbody>${DL_ERRORS.map(d => `<tr onclick="openLogs('${d.track}')">
      <td><div class="track-cell">${cover(d.album, null, 'track-thumb')}<div><div class="track-title">${d.track}</div><div class="track-sub">${d.artist} • ${d.album}</div></div></div></td>
      <td><span class="badge badge-neutral">${d.quality}</span></td>
      <td><span class="badge badge-error">${icon('warning')} ${d.reason}</span></td>
      <td><div class="row-actions">
        <button class="row-act" onclick="event.stopPropagation();toast('accent','refresh','Retrying','Retrying ${d.track}…')" aria-label="Retry">${icon('refresh')}</button>
        <button class="row-act" onclick="event.stopPropagation();openLogs('${d.track}')" aria-label="Logs">${icon('terminal')}</button>
        <button class="row-act danger" onclick="event.stopPropagation();toast('error','delete','Dismissed','Error dismissed')" aria-label="Dismiss">${icon('close')}</button>
      </div></td></tr>`).join('')}</tbody></table></div>`;
}

/* ============================================================
   3. ARTIST DETAILS
   ============================================================ */
function viewArtist(id) {
  const a = getArtist(id);
  const recentTracks = makeTracks(a.name, 6);
  return `
  <div class="view" data-screen-label="Artist">
    <div class="content-inner">
      <div class="artist-hero">
        <div class="hero-bg" style="${artStyle(a.name)}"></div>
        <div class="hero-content">
          <div class="hero-eyebrow">${icon('verified', 'ms-fill')} Verified Artist · ${a.genre}</div>
          <h1>${a.name}</h1>
          <div class="hero-stats">
            <span class="chip chip-stat">${icon('album')} <b>${a.albums_count}</b> Albums</span>
            <span class="chip chip-stat">${icon('music_note')} <b>${a.tracks_count}</b> Tracks</span>
            <span class="chip chip-stat">${icon('download')} <b>${a.tracks_count}</b> Downloaded</span>
            <span class="chip chip-stat">${icon('star', 'ms-fill')} <b>${a.rating}</b> Rating</span>
            <span class="chip chip-stat">${icon('group')} <b>${a.monthly}M</b> Monthly</span>
          </div>
          <div class="hero-actions">
            <button class="btn btn-primary" onclick="toast('accent','play_circle','Playing','Playing all of ${a.name}')">${icon('play_arrow', 'ms-fill')} Play All</button>
            <button class="btn btn-secondary" onclick="toast('accent','favorite','Favorited','${a.name} added to favorites')">${icon('favorite')} Favorite</button>
            <button class="btn btn-secondary" onclick="toast('accent','download','Queued','Downloading full discography')">${icon('download')} Download All</button>
          </div>
        </div>
      </div>

      <div class="section" style="margin-top:8px">
        <div class="section-head"><h2>Discography</h2><a class="link" onclick="toast('accent','sort','Sorted','Sorted by newest')">Newest first ${icon('expand_more')}</a></div>
        <div class="card-grid stagger">${a.albums.map((al, i) => albumCard(al, i)).join('')}</div>
      </div>

      <div class="section">
        <div class="section-head"><h2>Popular Tracks</h2></div>
        <div class="table-wrap"><table class="dl-table tracklist">
          <tbody>${recentTracks.map((t, i) => `<tr onclick="toast('accent','play_circle','Playing','Now playing ${t.name}')">
            <td class="col-num"><span class="track-index">${i + 1}</span></td>
            <td><div class="track-cell">${cover(a.albums[i % a.albums.length].name, null, 'track-thumb')}<div><div class="track-title">${t.name}</div><div class="track-sub">${a.albums[i % a.albums.length].name}</div></div></div></td>
            <td class="tnum hide-sm" style="color:var(--text-muted)">${(hashStr(t.name) % 900 + 100)}K plays</td>
            <td class="tnum" style="color:var(--text-secondary)">${t.dur}</td>
            <td><div class="row-actions">
              <button class="row-act" onclick="event.stopPropagation();toast('accent','play_arrow','Playing','${t.name}')">${icon('play_arrow')}</button>
              <button class="row-act" onclick="event.stopPropagation();toast('accent','download','Queued','${t.name} added to queue')">${icon('download')}</button>
            </div></td></tr>`).join('')}</tbody></table></div>
      </div>
    </div>
  </div>`;
}

function albumCard(al, i) {
  return `<div class="album-card" style="animation-delay:${i * 40}ms" onclick="go('album','${al.id}')">
    <div class="album-art-wrap">
      ${cover(al.name)}
      <div class="album-overlay">
        <button class="overlay-btn play" onclick="event.stopPropagation();toast('accent','play_circle','Playing','${al.name}')" aria-label="Play">${icon('play_arrow', 'ms-fill')}</button>
        <button class="overlay-btn" onclick="event.stopPropagation();toast('accent','download','Queued','${al.name} queued')" aria-label="Download">${icon('download')}</button>
      </div>
    </div>
    <div class="album-info"><div class="album-title">${al.name}</div><div class="album-year">${al.year} • ${al.tracks} tracks</div></div>
  </div>`;
}

/* ============================================================
   4. ALBUM DETAILS
   ============================================================ */
function viewAlbum(id) {
  const { album, artist } = getAlbum(id);
  const tracks = makeTracks(album.name, album.tracks);
  const totalSec = tracks.reduce((s, t) => { const [m, sec] = t.dur.split(':').map(Number); return s + m * 60 + sec; }, 0);
  const dur = `${Math.floor(totalSec / 60)} min`;
  return `
  <div class="view" data-screen-label="Album">
    <div class="content-inner">
      <div class="album-header">
        <div class="album-cover-lg">${cover(album.name)}</div>
        <div class="album-header-info">
          <div class="eyebrow">Album</div>
          <h1>${album.name}</h1>
          <div class="album-byline">by <a onclick="go('artist','${artist.id}')">${artist.name}</a> · ${album.year}</div>
          <div class="album-meta-row">
            <span class="badge badge-accent">${artist.genre}</span>
            <span class="badge badge-neutral">${artist.genre2}</span>
            <span class="chip chip-stat">${icon('music_note')} <b>${album.tracks}</b> tracks</span>
            <span class="chip chip-stat">${icon('schedule')} <b>${dur}</b></span>
            <span class="chip chip-stat">${icon('star', 'ms-fill')} <b>${artist.rating}</b></span>
          </div>
          <div class="hero-actions">
            <button class="btn btn-primary" onclick="toast('accent','play_circle','Playing','${album.name}')">${icon('play_arrow', 'ms-fill')} Play All</button>
            <button class="btn btn-secondary" onclick="toast('accent','download','Queued','${album.name} added to queue')">${icon('download')} Download All</button>
            <button class="btn btn-secondary" onclick="toast('accent','favorite','Favorited','Added to favorites')">${icon('favorite')}</button>
            <button class="btn btn-secondary" onclick="toast('accent','ios_share','Shared','Link copied')">${icon('ios_share')}</button>
          </div>
        </div>
      </div>

      <div class="table-wrap"><table class="dl-table tracklist">
        <thead><tr><th class="col-num">#</th><th>Title</th><th class="hide-sm">Plays</th><th>Time</th><th style="text-align:right">Actions</th></tr></thead>
        <tbody>${tracks.map((t, i) => `<tr onclick="toast('accent','play_circle','Playing','${t.name}')">
          <td class="col-num"><span class="track-index">${t.n}</span></td>
          <td><div class="track-cell"><div><div class="track-title">${t.name}</div><div class="track-sub">${artist.name}</div></div></div></td>
          <td class="tnum hide-sm" style="color:var(--text-muted)">${(hashStr(t.name + i) % 800 + 80)}K</td>
          <td class="tnum" style="color:var(--text-secondary)">${t.dur}</td>
          <td><div class="row-actions">
            <button class="row-act" onclick="event.stopPropagation();toast('accent','play_arrow','Playing','${t.name}')">${icon('play_arrow')}</button>
            <button class="row-act" onclick="event.stopPropagation();toast('accent','download','Queued','${t.name} queued')">${icon('download')}</button>
            <button class="row-act" onclick="event.stopPropagation();toast('accent','playlist_add','Added','Added to playlist')">${icon('playlist_add')}</button>
          </div></td></tr>`).join('')}</tbody></table></div>
    </div>
  </div>`;
}

/* ============================================================
   5. SETTINGS
   ============================================================ */
function viewSettings() {
  return `
  <div class="view" data-screen-label="Settings">
    <div class="content-inner">
      <div class="page-head"><h1>Settings</h1><p>Configure how Melodock downloads, organizes, and protects your music library.</p></div>
      <div class="settings-layout">
        <div class="settings-nav">
          <button class="active" onclick="scrollSetting('s-download',this)">${icon('download')} Downloads</button>
          <button onclick="scrollSetting('s-library',this)">${icon('library_music')} Library</button>
          <button onclick="scrollSetting('s-privacy',this)">${icon('shield')} Privacy</button>
          <button onclick="scrollSetting('s-advanced',this)">${icon('tune')} Advanced</button>
        </div>
        <div class="settings-panels">
          <div class="settings-card" id="s-download">
            <h2>${icon('download')} Download Settings</h2>
            <p class="desc">Control audio quality and where finished files are placed.</p>
            <div class="setting-row"><div class="sr-info"><div class="sr-label">Audio quality</div><div class="sr-desc">Preferred format when multiple sources exist</div></div>
              <div class="sr-control grow"><select class="select"><option>FLAC (Lossless)</option><option>320 kbps MP3</option><option>128 kbps MP3</option></select></div></div>
            <div class="setting-row"><div class="sr-info"><div class="sr-label">Download folder</div><div class="sr-desc">Temporary location before organizing</div></div>
              <div class="sr-control grow"><div class="input-group"><input class="input" readonly value="${SETTINGS.download_path}"><button class="btn btn-secondary btn-sm">${icon('folder_open')} Browse</button></div></div></div>
            <div class="setting-row"><div class="sr-info"><div class="sr-label">Auto-organize</div><div class="sr-desc">Sort into Artist / Album / Track folders automatically</div></div>
              <div class="sr-control">${toggle('auto_organize', true)}</div></div>
            <div class="setting-row"><div class="sr-info"><div class="sr-label">Delete after processing</div><div class="sr-desc">Remove temp files once tagged and filed</div></div>
              <div class="sr-control">${toggle('delete_after', true)}</div></div>
          </div>

          <div class="settings-card" id="s-library">
            <h2>${icon('library_music')} Library Settings</h2>
            <p class="desc">Where your organized music lives and how it stays in sync.</p>
            <div class="setting-row"><div class="sr-info"><div class="sr-label">Library folder</div><div class="sr-desc">Root of your organized collection</div></div>
              <div class="sr-control grow"><div class="input-group"><input class="input" readonly value="${SETTINGS.library_path}"><button class="btn btn-secondary btn-sm">${icon('folder_open')} Browse</button></div></div></div>
            <div class="setting-row"><div class="sr-info"><div class="sr-label">Auto-scan on startup</div><div class="sr-desc">Re-index the library when Melodock launches</div></div>
              <div class="sr-control">${toggle('auto_scan', true)}</div></div>
            <div class="setting-row"><div class="sr-info"><div class="sr-label">Manual rescan</div><div class="sr-desc">Last scan: 41 minutes ago · 18,764 tracks</div></div>
              <div class="sr-control"><button class="btn btn-secondary btn-sm" onclick="toast('accent','sync','Rescanning','Library scan started…')">${icon('sync')} Rescan now</button></div></div>
          </div>

          <div class="settings-card" id="s-privacy">
            <h2>${icon('shield')} Privacy &amp; Security</h2>
            <p class="desc">Manage visibility and API access to your instance.</p>
            <div class="setting-row"><div class="sr-info"><div class="sr-label">Hide from Plex</div><div class="sr-desc">Exclude this library from Plex media scans</div></div>
              <div class="sr-control">${toggle('hide_plex', false)}</div></div>
            <div class="setting-row"><div class="sr-info"><div class="sr-label">API token</div><div class="sr-desc">Used by clients and integrations</div></div>
              <div class="sr-control grow"><div class="token-display"><span class="tk" id="api-token">••••••••••••••••••••••••</span>
                <button class="row-act" onclick="toggleToken()" aria-label="Reveal">${icon('visibility')}</button>
                <button class="row-act" onclick="toast('success','content_copy','Copied','API token copied to clipboard')" aria-label="Copy">${icon('content_copy')}</button></div></div></div>
            <div class="setting-row"><div class="sr-info"><div class="sr-label">Rotate token</div><div class="sr-desc">Invalidate the current token and generate a new one</div></div>
              <div class="sr-control"><button class="btn btn-secondary btn-sm" onclick="toast('accent','key','Rotated','A new API token was generated')">${icon('autorenew')} Rotate</button></div></div>
          </div>

          <div class="settings-card" id="s-advanced">
            <h2>${icon('tune')} Advanced</h2>
            <p class="desc">Fine-tune performance and resource usage.</p>
            <div class="setting-row"><div class="sr-info"><div class="sr-label">Max concurrent downloads</div><div class="sr-desc">Higher uses more bandwidth and CPU</div></div>
              <div class="sr-control"><input class="input" type="number" value="4" min="1" max="16" style="width:90px;text-align:center"></div></div>
            <div class="setting-row"><div class="sr-info"><div class="sr-label">Connection timeout</div><div class="sr-desc">Seconds before a stalled source is dropped</div></div>
              <div class="sr-control"><input class="input" type="number" value="30" style="width:90px;text-align:center"></div></div>
            <div class="setting-row"><div class="sr-info"><div class="sr-label">Cache size</div><div class="sr-desc"><span id="cache-val">512</span> MB reserved for artwork &amp; metadata</div></div>
              <div class="sr-control grow"><input class="slider" type="range" min="128" max="2048" step="128" value="512" oninput="document.getElementById('cache-val').textContent=this.value"></div></div>
            <div class="setting-row"><div class="sr-info"><div class="sr-label">Clear cache</div><div class="sr-desc">Free up disk used by thumbnails and lookups</div></div>
              <div class="sr-control"><button class="btn btn-ghost-danger btn-sm" onclick="toast('error','cleaning_services','Cache cleared','318 MB freed')">${icon('delete_sweep')} Clear cache</button></div></div>
          </div>

          <div class="settings-actions">
            <button class="btn btn-tertiary" onclick="toast('accent','restart_alt','Reset','Settings reset to defaults')">Reset to defaults</button>
            <button class="btn btn-secondary" onclick="toast('accent','done','Applied','Changes applied')">Apply</button>
            <button class="btn btn-primary" onclick="toast('success','check_circle','Saved','Your settings have been saved')">${icon('save')} Save changes</button>
          </div>
        </div>
      </div>
    </div>
  </div>`;
}
function toggle(id, on) {
  return `<label class="switch"><input type="checkbox" ${on ? 'checked' : ''}><span class="track"></span></label>`;
}

/* ============================================================
   6. EXPLORER / DISCOVERY
   ============================================================ */
function viewExplorer() {
  const trending = ARTISTS.slice(12, 20);
  const results = ARTISTS.slice(4, 12);
  const collections = [
    { name: 'Late Night Coding', sub: '64 tracks · Lo-fi & Ambient', seeds: ['Kairo', 'Lowtide', 'Glasswing', 'Halcyon Bay'] },
    { name: 'Synthwave Drive', sub: '48 tracks · Retro Electronic', seeds: ['Neon District', 'Polaris Drift', 'Nova Lux', 'Sable Moon'] },
    { name: 'Indie Discoveries', sub: '92 tracks · Fresh finds', seeds: ['Aurora Halls', 'Marlowe Sage', 'Mirrorbloom', 'Saffron Wells'] },
  ];
  return `
  <div class="view" data-screen-label="Explorer">
    <div class="content-inner">
      <div class="explore-hero">
        <h1>Discover new music</h1>
        <p>Search across providers and add artists straight into your Melodock library.</p>
        <div class="big-search">${icon('search')}<input placeholder="Search artists, albums, or paste a link…" aria-label="Search"><button class="btn btn-primary btn-sm">Search</button></div>
        <div class="trend-tags">
          ${['Synthwave', 'Lo-fi beats', 'Indie 2026', 'Jazz revival', 'Dream pop', 'Deep house'].map(t => `<button class="chip">${icon('trending_up')} ${t}</button>`).join('')}
        </div>
      </div>

      <div class="section" style="margin-top:0">
        <div class="section-head"><h2>Trending this week</h2><a class="link">See all ${icon('chevron_right')}</a></div>
        <div class="hscroll stagger">${trending.map((a, i) => `
          <div class="artist-card" style="animation-delay:${i * 40}ms" onclick="go('artist','${a.id}')">
            <div class="artist-cover-wrap">${cover(a.name)}<div class="artist-overlay"><button class="overlay-btn play" onclick="event.stopPropagation();toast('accent','play_circle','Playing','${a.name}')">${icon('play_arrow', 'ms-fill')}</button></div></div>
            <div class="artist-name">${a.name}</div><div class="artist-meta">${a.genre}</div>
          </div>`).join('')}</div>
      </div>

      <div class="section">
        <div class="section-head"><h2>Search results</h2><span style="color:var(--text-muted);font-size:13px">${results.length} artists</span></div>
        <div class="card-grid stagger">${results.map((a, i) => {
          const added = i % 3 === 0;
          return `<div class="artist-card" style="position:relative;animation-delay:${i * 40}ms" onclick="go('artist','${a.id}')">
            ${added ? `<span class="badge badge-success added-badge">${icon('check')} In library</span>` : ''}
            <div class="artist-cover-wrap">${cover(a.name)}<div class="artist-overlay"><button class="overlay-btn play" onclick="event.stopPropagation();go('artist','${a.id}')">${icon('visibility')}</button></div></div>
            <div class="artist-name">${a.name}</div><div class="artist-meta">${a.genre}</div>
            <button class="btn ${added ? 'btn-secondary' : 'btn-primary'} btn-sm" style="margin-top:14px;width:100%" onclick="event.stopPropagation();${added ? `toast('accent','library_add_check','Already added','${a.name} is in your library')` : `toast('success','library_add','Added','${a.name} added to library')`}">${added ? icon('library_add_check') + ' Added' : icon('add') + ' Add to library'}</button>
          </div>`;
        }).join('')}</div>
      </div>

      <div class="section">
        <div class="section-head"><h2>Curated collections</h2></div>
        <div class="collection-grid stagger">${collections.map((c, i) => `
          <div class="collection-card" style="animation-delay:${i * 60}ms" onclick="toast('accent','queue_music','Opening','${c.name}')">
            <div class="cc-bg" style="${artStyle(c.name)}"></div>
            <div class="cc-mini">${c.seeds.map(s => cover(s, '')).join('')}</div>
            <h3>${c.name}</h3><p>${c.sub}</p>
          </div>`).join('')}</div>
      </div>
    </div>
  </div>`;
}

/* ============================================================
   7. LOGS / TERMINAL
   ============================================================ */
function viewLogs() {
  return `
  <div class="view" data-screen-label="Logs">
    <div class="content-inner">
      <div class="page-head"><div class="page-head-row"><div><h1>System Logs</h1><p>Real-time activity from the download workers, tagger, and library indexer.</p></div></div></div>
      <div class="logs-toolbar">
        <select class="select" style="width:auto" id="log-filter" onchange="renderTerminal()">
          <option value="all">All logs</option><option value="success">Downloads</option><option value="info">System</option><option value="error">Errors</option>
        </select>
        <span class="spacer"></span>
        <button class="btn btn-secondary btn-sm" id="live-toggle" onclick="toggleLive()">${icon('radio_button_checked')} <span>Live</span></button>
        <button class="btn btn-secondary btn-sm" onclick="toast('accent','download','Exported','logs-2026-06-07.txt')">${icon('file_download')} Export</button>
        <button class="btn btn-ghost-danger btn-sm" onclick="clearLogs()">${icon('delete')} Clear</button>
      </div>
      <div class="terminal-head"><span class="dot r"></span><span class="dot y"></span><span class="dot g"></span><span class="tt">melodock@server: ~/logs/worker.log</span><span class="live" id="live-ind">${icon('sensors')} streaming</span></div>
      <div class="terminal attached" id="terminal"></div>
    </div>
  </div>`;
}
function logLineHTML(l) {
  return `<div class="log-line ${l.level}"><span class="ts">${l.ts}</span><span class="lv">${l.level.toUpperCase()}</span><span class="msg">${l.message}</span></div>`;
}
