/* ============================================================
   MELODOCK — Mock data + helpers
   ============================================================ */

/* ---------- Deterministic gradient art generator ---------- */
function hashStr(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) { h = (h << 5) - h + s.charCodeAt(i); h |= 0; }
  return Math.abs(h);
}
// Curated dark-premium hue pairs so placeholders stay cohesive
const ART_PAIRS = [
  [248, 268], [262, 290], [222, 248], [280, 320], [200, 232],
  [330, 358], [170, 200], [292, 262], [212, 188], [344, 312],
  [256, 226], [188, 220],
];
function artStyle(seed) {
  const h = hashStr(seed);
  const [a, b] = ART_PAIRS[h % ART_PAIRS.length];
  const angle = 110 + (h % 70);
  const sat1 = 58 + (h % 14);
  const sat2 = 48 + ((h >> 3) % 14);
  return `background: linear-gradient(${angle}deg, hsl(${a} ${sat1}% 52%), hsl(${b} ${sat2}% 34%));`;
}
function initials(name) {
  const parts = name.replace(/^The\s+/i, '').split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
// HTML for a cover element
function cover(seed, glyph, cls) {
  return `<div class="cover ${cls || ''}" style="${artStyle(seed)}"><span class="glyph">${glyph != null ? glyph : initials(seed)}</span></div>`;
}

/* ---------- Library stats ---------- */
const STATS = { artists: 248, albums: 1432, tracks: 18764, size_gb: 412.6 };

/* ---------- Artists ---------- */
const GENRES = ['Electronic', 'Indie Rock', 'Hip-Hop', 'Jazz', 'Ambient', 'Synthwave', 'Soul', 'House', 'Classical', 'Lo-fi', 'Funk', 'Dream Pop'];
const ARTIST_NAMES = [
  'Aurora Halls', 'Midnight Cartel', 'Selene Vox', 'The Paper Kites Co.', 'Neon District',
  'Cosmo Vega', 'Velvet Underground City', 'Echo & Iris', 'Marlowe Sage', 'Junglewood',
  'Polaris Drift', 'Sable Moon', 'The Lantern Society', 'Kairo', 'Indigo Sparrow',
  'Lowtide', 'Mirrorbloom', 'Glasswing', 'Otto & The Tides', 'Nova Lux',
  'Ceramic Animals', 'Halcyon Bay', 'The Wandering Hours', 'Saffron Wells',
];
const ALBUM_WORDS_A = ['Midnight', 'Golden', 'Paper', 'Electric', 'Velvet', 'Distant', 'Crystal', 'Hollow', 'Neon', 'Quiet', 'Wild', 'Slow'];
const ALBUM_WORDS_B = ['Cartography', 'Hours', 'Gardens', 'Echoes', 'Daydream', 'Currents', 'Lanterns', 'Mirage', 'Lullaby', 'Horizon', 'Tides', 'Bloom'];

function makeAlbums(seed, count) {
  const h = hashStr(seed);
  const albums = [];
  for (let i = 0; i < count; i++) {
    const a = ALBUM_WORDS_A[(h + i * 7) % ALBUM_WORDS_A.length];
    const b = ALBUM_WORDS_B[(h + i * 3 + 5) % ALBUM_WORDS_B.length];
    albums.push({
      id: `${seed}-${i}`,
      name: `${a} ${b}`,
      year: 2015 + ((h + i * 5) % 11),
      tracks: 8 + ((h + i) % 8),
    });
  }
  return albums.sort((x, y) => y.year - x.year);
}

const ARTISTS = ARTIST_NAMES.map((name, i) => {
  const albumsCount = 2 + (hashStr(name) % 6);
  return {
    id: 'a' + i,
    name,
    genre: GENRES[hashStr(name) % GENRES.length],
    genre2: GENRES[(hashStr(name) + 4) % GENRES.length],
    albums_count: albumsCount,
    tracks_count: albumsCount * (9 + (hashStr(name) % 5)),
    monthly: (1.2 + (hashStr(name) % 90) / 10).toFixed(1),
    albums: makeAlbums(name, albumsCount),
    rating: (3.8 + (hashStr(name) % 12) / 10).toFixed(1),
  };
});

function getArtist(id) { return ARTISTS.find(a => a.id === id) || ARTISTS[0]; }
function getAlbum(albumId) {
  for (const ar of ARTISTS) {
    const al = ar.albums.find(x => x.id === albumId);
    if (al) return { album: al, artist: ar };
  }
  const ar = ARTISTS[0];
  return { album: ar.albums[0], artist: ar };
}

/* ---------- Track name generator ---------- */
const TRACK_WORDS = ['Lanterns', 'Afterglow', 'Paper Moon', 'Ghost Light', 'Slow Burn', 'Tidalwave', 'Static', 'Reverie', 'Coastline', 'Nightcall', 'Embers', 'Polaroid', 'Undertow', 'Daybreak', 'Wildflower', 'Marble', 'Saffron', 'Lowlands', 'Halcyon', 'Driftwood'];
function makeTracks(seed, count) {
  const h = hashStr(seed);
  const out = [];
  for (let i = 0; i < count; i++) {
    const name = TRACK_WORDS[(h + i * 6) % TRACK_WORDS.length] + (((h + i) % 3 === 0) ? ' (Reprise)' : '');
    const mins = 2 + ((h + i) % 4);
    const secs = (h + i * 13) % 60;
    out.push({ n: i + 1, name, dur: `${mins}:${String(secs).padStart(2, '0')}` });
  }
  return out;
}

/* ---------- Downloads ---------- */
const DL_ACTIVE = [
  { id: 'd1', artist: 'Aurora Halls', album: 'Midnight Cartography', track: 'Paper Moon', quality: 'FLAC', size: '38.2 MB', progress: 64, speed: '4.1 MB/s' },
  { id: 'd2', artist: 'Neon District', album: 'Electric Daydream', track: 'Nightcall', quality: 'FLAC', size: '41.7 MB', progress: 28, speed: '3.6 MB/s' },
  { id: 'd3', artist: 'Selene Vox', album: 'Crystal Lullaby', track: 'Afterglow', quality: '320 MP3', size: '9.8 MB', progress: 87, speed: '5.2 MB/s' },
  { id: 'd4', artist: 'Junglewood', album: 'Wild Tides', track: 'Undertow', quality: 'FLAC', size: '44.1 MB', progress: 12, speed: '2.9 MB/s' },
  { id: 'd5', artist: 'Kairo', album: 'Slow Bloom', track: 'Embers', quality: 'FLAC', size: '36.5 MB', progress: 49, speed: '4.4 MB/s' },
];
const DL_COMPLETED = [
  { id: 'c1', artist: 'Polaris Drift', album: 'Distant Horizon', track: 'Coastline', quality: 'FLAC', size: '39.4 MB', when: '2 min ago' },
  { id: 'c2', artist: 'Sable Moon', album: 'Velvet Mirage', track: 'Reverie', quality: 'FLAC', size: '42.0 MB', when: '8 min ago' },
  { id: 'c3', artist: 'Glasswing', album: 'Quiet Lanterns', track: 'Static', quality: '320 MP3', size: '10.1 MB', when: '14 min ago' },
  { id: 'c4', artist: 'Nova Lux', album: 'Golden Echoes', track: 'Daybreak', quality: 'FLAC', size: '37.8 MB', when: '26 min ago' },
  { id: 'c5', artist: 'Indigo Sparrow', album: 'Hollow Currents', track: 'Driftwood', quality: 'FLAC', size: '40.3 MB', when: '41 min ago' },
  { id: 'c6', artist: 'Lowtide', album: 'Slow Tides', track: 'Lowlands', quality: '320 MP3', size: '9.2 MB', when: '1 hr ago' },
];
const DL_ERRORS = [
  { id: 'e1', artist: 'Mirrorbloom', album: 'Neon Bloom', track: 'Marble', quality: 'FLAC', reason: 'Source unavailable (404)' },
  { id: 'e2', artist: 'Otto & The Tides', album: 'Wild Daydream', track: 'Saffron', quality: 'FLAC', reason: 'Checksum mismatch' },
];

/* ---------- Logs ---------- */
const LOG_LEVELS = ['info', 'success', 'warn', 'error', 'debug'];
const LOG_TEMPLATES = [
  ['info', 'Queue worker picked up job #%d'],
  ['debug', 'Resolving source for "%t" via provider:soundgate'],
  ['success', 'Downloaded "%t" (%s) → /library/%a'],
  ['info', 'Tagging metadata: artist, album, track, year, cover'],
  ['debug', 'Embedding cover art 1400×1400 jpeg'],
  ['warn', 'Rate limit approaching for provider:soundgate (82%)'],
  ['success', 'Library scan complete — 18,764 tracks indexed'],
  ['error', 'Failed to fetch "%t": source unavailable (404)'],
  ['info', 'Moved 1 file to /library/%a/%al'],
  ['debug', 'Cache hit for artist lookup "%a"'],
  ['warn', 'Disk usage at 62% (255 GB / 412 GB)'],
  ['info', 'WebSocket client connected (id: ws_8f2a)'],
];
function nowTs(offsetSec) {
  const d = new Date(Date.now() - (offsetSec || 0) * 1000);
  return d.toTimeString().slice(0, 8);
}
function makeLog(i) {
  const [lvl, tmpl] = LOG_TEMPLATES[i % LOG_TEMPLATES.length];
  const ar = ARTISTS[hashStr('' + i) % ARTISTS.length];
  const tr = TRACK_WORDS[hashStr('t' + i) % TRACK_WORDS.length];
  const msg = tmpl
    .replace('%d', 1000 + (i % 900))
    .replace('%t', tr)
    .replace('%s', '39.4 MB')
    .replace('%al', 'Album')
    .replace('%a', ar.name);
  return { ts: nowTs((40 - i) * 7), level: lvl, message: msg };
}
const SEED_LOGS = Array.from({ length: 32 }, (_, i) => makeLog(i));

/* ---------- Settings defaults ---------- */
const SETTINGS = {
  quality: 'FLAC (Lossless)',
  download_path: '/data/library/incoming',
  library_path: '/data/library',
  auto_organize: true,
  delete_after: true,
  auto_scan: true,
  hide_plex: false,
  max_concurrent: 4,
  timeout: 30,
  cache: 512,
};
