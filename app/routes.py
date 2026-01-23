from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify, send_from_directory, send_file
from .services.logger import sys_logger
from .services.scanner import LibraryScanner
import requests
import shutil 
import os 
import threading 
import math
import time
from collections import defaultdict

main_bp = Blueprint('main', __name__)

# --- HELPERS ---
def get_db(): return current_app.config['DB']
def get_metadata(): return current_app.config['METADATA'] 
def get_downloader(): return current_app.config['DOWNLOADER']
def get_explorer(): return current_app.config['EXPLORER']

# --- PÁGINAS ---
@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    db = get_db()
    stats = {
        'artists': db.query("SELECT COUNT(*) as c FROM artists", one=True)['c'],
        'queue': db.query("SELECT COUNT(*) as c FROM queue WHERE status IN ('pending', 'high_priority', 'downloading')", one=True)['c'],
        'completed': db.query("SELECT COUNT(*) as c FROM queue WHERE status='completed'", one=True)['c'],
    }
    try:
        total, used, free = shutil.disk_usage("/music")
        stats['disk_percent'] = int((used / total) * 100)
        stats['disk_free'] = free // (2**30)
    except:
        stats['disk_percent'] = 0; stats['disk_free'] = 0

    page = request.args.get('page', 1, type=int)
    per_page = 20 
    offset = (page - 1) * per_page
    
    total_artists = stats['artists']
    total_pages = math.ceil(total_artists / per_page)
    
    sort_mode = request.args.get('sort', 'date')
    order_sql = "ORDER BY name ASC" if sort_mode == 'name' else "ORDER BY added_at DESC"
    
    artists_list = db.query(f"SELECT * FROM artists {order_sql} LIMIT ? OFFSET ?", (per_page, offset))
    
    return render_template('dashboard.html', 
                           stats=stats, 
                           artists=artists_list, 
                           current_sort=sort_mode, 
                           current_page=page, 
                           total_pages=total_pages)

@main_bp.route('/downloads')
def downloads():
    db = get_db()
    active = db.query("SELECT * FROM queue WHERE status='downloading'", one=True)
    raw_queue = db.query("SELECT * FROM queue WHERE status IN ('pending', 'high_priority', 'error') ORDER BY CASE WHEN status='high_priority' THEN 1 ELSE 2 END, id ASC")
    
    grouped_queue = defaultdict(list)
    artist_priority = {}
    
    for item in raw_queue:
        grouped_queue[item['artist']].append(item)
        if item['status'] == 'high_priority':
            artist_priority[item['artist']] = True
            
    return render_template('downloads.html', active=active, grouped_queue=grouped_queue, artist_priority=artist_priority)

@main_bp.route('/artist/<path:artist_name>')
def artist_profile(artist_name):
    db = get_db()
    artist = db.query("SELECT * FROM artists WHERE name=?", (artist_name,), one=True)
    if not artist: return "Artista não encontrado", 404
    
    albums = db.query("SELECT * FROM queue WHERE artist=? ORDER BY title", (artist_name,))
    
    albums_data = []
    for alb in albums:
        track_stats = db.query("""
            SELECT 
                COUNT(*) as total, 
                SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as downloaded 
            FROM tracks WHERE queue_id=?
        """, (alb['id'],), one=True)
        
        alb_dict = dict(alb)
        alb_dict['total_tracks'] = track_stats['total'] or 0
        alb_dict['downloaded_tracks'] = track_stats['downloaded'] or 0
        
        if alb_dict['total_tracks'] > 0 and alb_dict['total_tracks'] == alb_dict['downloaded_tracks']:
            alb_dict['visual_status'] = 'completed'
        elif alb['status'] == 'error':
            alb_dict['visual_status'] = 'error'
        else:
            alb_dict['visual_status'] = 'partial'
            
        albums_data.append(alb_dict)

    return render_template('artist_details.html', artist=artist, albums=albums_data)

@main_bp.route('/album/<int:queue_id>')
def album_details(queue_id):
    db = get_db()
    album = db.query("SELECT * FROM queue WHERE id=?", (queue_id,), one=True)
    if not album: return "Album não encontrado", 404
    tracks = db.query("SELECT * FROM tracks WHERE queue_id=? ORDER BY track_number", (queue_id,))
    total = len(tracks)
    completed = sum(1 for t in tracks if t['status'] == 'completed')
    return render_template('album_details.html', album=album, tracks=tracks, progress={'total': total, 'completed': completed})

# --- WORKER: IMPORTAÇÃO PROFUNDA ---
def background_full_import(app, data):
    with app.app_context():
        db = get_db()
        metadata = get_metadata()
        downloader = get_downloader()
        
        valid_items = [x for x in data if x.get('deezer_id')]
        total_valid = len(valid_items)
        
        sys_logger.log("IMPORT", f"🚀 Iniciando importação de {total_valid} artistas válidos...")

        for idx, item in enumerate(valid_items):
            deezer_id = item.get('deezer_id')
            raw_name = item.get('name') or item.get('folder') 
            
            try:
                db.execute("""
                    INSERT INTO artists (deezer_id, name, genre) VALUES (?, ?, 'Library')
                    ON CONFLICT(deezer_id) DO UPDATE SET name=excluded.name
                """, (deezer_id, raw_name))
                
                safe_artist_folder = downloader.sanitize(raw_name)
                artist_path = os.path.join("/music", safe_artist_folder)

                discography = metadata.get_discography(deezer_id, target_artist_id=raw_name)
                
                for album in discography:
                    safe_album_folder = downloader.sanitize(album['title'])
                    album_path = os.path.join(artist_path, safe_album_folder)
                    
                    if os.path.exists(album_path):
                        existing_q = db.query("SELECT id FROM queue WHERE deezer_id=?", (album['deezer_id'],), one=True)
                        if existing_q:
                            queue_id = existing_q['id']
                            db.execute("UPDATE queue SET status='completed', cover_url=? WHERE id=?", (album['cover'], queue_id))
                        else:
                            cur = db.execute("""
                                INSERT INTO queue (deezer_id, title, artist, type, status, cover_url) 
                                VALUES (?, ?, ?, 'album', 'completed', ?)
                            """, (album['deezer_id'], album['title'], raw_name, album['cover']))
                            queue_id = cur.lastrowid
                        
                        tracks = metadata.get_album_tracks(album['deezer_id'], fallback_artist=raw_name)
                        for t in tracks:
                            safe_title = downloader.sanitize(t['title'])
                            possible_filenames = [
                                f"{str(t['track_num']).zfill(2)} - {safe_title}.mp3",
                                f"{str(t['track_num'])} - {safe_title}.mp3",
                                f"{safe_title}.mp3"
                            ]
                            is_file_present = False
                            for fname in possible_filenames:
                                if os.path.exists(os.path.join(album_path, fname)):
                                    is_file_present = True
                                    break
                            
                            status = 'completed' if is_file_present else 'pending'
                            track_exists = db.query("SELECT id, status FROM tracks WHERE queue_id=? AND track_number=?", (queue_id, t['track_num']), one=True)

                            if not track_exists:
                                db.execute("""
                                    INSERT INTO tracks (queue_id, title, artist, track_number, status, duration)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (queue_id, t['title'], t['artist'], t['track_num'], status, t.get('duration', 0)))
                            else:
                                if track_exists['status'] != status:
                                    db.execute("UPDATE tracks SET status=? WHERE id=?", (status, track_exists['id']))

                sys_logger.log("IMPORT", f"✅ Processado: {raw_name}")
            except Exception as e:
                sys_logger.log("ERROR", f"Falha ao importar {raw_name}: {e}")

        sys_logger.log("IMPORT", "🏁 Importação em background finalizada.")

@main_bp.route('/api/scan_library_preview')
def scan_library_preview():
    scanner = LibraryScanner(get_metadata())
    results = scanner.scan_folders()
    return jsonify(results)

@main_bp.route('/api/import_library', methods=['POST'])
def import_library():
    data = request.json
    valid_count = sum(1 for x in data if x.get('deezer_id'))
    app_obj = current_app._get_current_object()
    thread = threading.Thread(target=background_full_import, args=(app_obj, data))
    thread.start()
    return jsonify({'success': True, 'count': valid_count, 'message': 'Iniciado'})

# --- WORKER: ADICIONAR ARTISTA (COM FILTROS) ---
def background_add_artist(app, chosen_id, artist_name_input):
    with app.app_context():
        meta = get_metadata(); db = get_db(); dl = get_downloader()
        sys_logger.log("SYSTEM", f"🔄 Processando {artist_name_input}...")
        
        # Carrega Filtros
        keywords_str = db.get_setting('ignored_keywords') or "playback,karaoke,instrumental,backing track"
        BLACKLIST = [k.strip().lower() for k in keywords_str.split(',')]
        max_tracks_val = int(db.get_setting('max_tracks') or 40)

        artist_data = meta.get_artist_by_id(chosen_id) if chosen_id else meta.search_artist(artist_name_input)
        if not artist_data: return

        art_id = artist_data['id']; art_name = artist_data['name']
        db.execute("INSERT OR IGNORE INTO artists (deezer_id, name, genre) VALUES (?, ?, ?)", (art_id, art_name, artist_data['genre']))
        dl.save_artist_image(art_name, artist_data['image'])

        albums = meta.get_discography(art_id, target_artist_id=art_name)
        cnt = 0
        
        for album in albums:
            title_lower = album['title'].lower()
            
            # Filtro 1: Palavras-chave
            if any(bad in title_lower for bad in BLACKLIST): continue
            
            # Filtro 2: Tamanho
            if album.get('track_count', 0) > max_tracks_val:
                sys_logger.log("SKIP", f"⏭️ Ignorado (>{max_tracks_val} faixas): {album['title']}")
                continue

            if not db.query("SELECT id FROM queue WHERE deezer_id=?", (album['deezer_id'],), one=True):
                cur = db.execute("INSERT INTO queue (deezer_id, title, artist, type, status, cover_url) VALUES (?, ?, ?, ?, 'pending', ?)", 
                    (album['deezer_id'], album['title'], art_name, 'album', album['cover']))
                qid = cur.lastrowid; cnt += 1
                tracks = meta.get_album_tracks(album['deezer_id'], fallback_artist=art_name)
                for t in tracks:
                    db.execute("INSERT INTO tracks (queue_id, title, artist, track_number, status, duration) VALUES (?, ?, ?, ?, 'pending', ?)", 
                        (qid, t['title'], t['artist'], t['track_num'], t.get('duration', 0)))
        
        sys_logger.log("SUCCESS", f"✅ {art_name}: {cnt} álbuns adicionados.")

@main_bp.route('/add_artist', methods=['POST'])
def add_artist():
    app_obj = current_app._get_current_object()
    threading.Thread(target=background_add_artist, args=(app_obj, request.form.get('chosen_id'), request.form.get('artist_name'))).start()
    return redirect(url_for('main.downloads'))

@main_bp.route('/delete_artist', methods=['POST'])
def delete_artist():
    db = get_db(); dl = get_downloader(); artist_name = request.form.get('artist_name')
    db.execute("DELETE FROM artists WHERE name=?", (artist_name,))
    db.execute("DELETE FROM queue WHERE artist=?", (artist_name,))
    safe = dl.sanitize(artist_name)
    try: shutil.rmtree(os.path.join("/downloads", safe))
    except: pass
    try: shutil.rmtree(os.path.join("/music", safe))
    except: pass
    return redirect(url_for('main.dashboard'))

@main_bp.route('/queue/delete_item/<int:item_id>', methods=['POST'])
def delete_queue_item(item_id):
    get_db().execute("DELETE FROM tracks WHERE queue_id=?", (item_id,))
    get_db().execute("DELETE FROM queue WHERE id=?", (item_id,))
    return redirect(url_for('main.downloads'))

@main_bp.route('/queue/prioritize/<path:artist_name>', methods=['POST'])
def prioritize_artist(artist_name):
    get_db().execute("UPDATE queue SET status='high_priority' WHERE artist=? AND status='pending'", (artist_name,))
    return redirect(url_for('main.downloads'))

@main_bp.route('/logs')
def logs(): return render_template('logs.html')

@main_bp.route('/explorer', methods=['GET', 'POST'])
def explorer():
    db = get_db(); explorer = get_explorer(); recs = []; search = ""
    if request.method == 'POST':
        search = request.form.get('artist_name')
        if search: recs = explorer.get_recommendations(search)
    else:
        rand = db.query("SELECT name FROM artists ORDER BY RANDOM() LIMIT 1", one=True)
        if rand: search = rand['name']; recs = explorer.get_recommendations(search)
    
    local_set = {r['name'].lower().strip() for r in db.query("SELECT name FROM artists")}
    for r in recs: r['in_library'] = r['name'].lower().strip() in local_set
    return render_template('explorer.html', recommendations=recs, search_term=search)

@main_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    db = get_db()
    DEFAULT_KEYWORDS = "playback,karaoke,instrumental,backing track,performance track,accompaniment track,demo,soundtrack,remix suite,compilation,best of,greatest hits"
    
    if request.method == 'POST':
        # Configs Gerais
        if request.form.get('scan_time'):
            db.set_setting('scan_time', request.form.get('scan_time'))
            db.set_setting('spider_enabled', request.form.get('spider_enabled'))
            db.set_setting('spider_schedule_time', request.form.get('spider_schedule_time'))
            db.set_setting('spider_growth_percent', request.form.get('spider_growth_percent'))
            db.set_setting('spider_min_fans', request.form.get('spider_min_fans'))
        
        # Configs de Filtro
        if request.form.get('ignored_keywords'):
            raw_keywords = request.form.get('ignored_keywords')
            clean_keywords = ",".join([k.strip().lower() for k in raw_keywords.split(',') if k.strip()])
            db.set_setting('ignored_keywords', clean_keywords)
            
        if request.form.get('max_tracks'):
            db.set_setting('max_tracks', request.form.get('max_tracks'))
        
        return redirect(url_for('main.settings'))
    
    return render_template('settings.html', 
                           scan_time=db.get_setting('scan_time') or "03:00",
                           spider_enabled=db.get_setting('spider_enabled') or "false",
                           spider_schedule_time=db.get_setting('spider_schedule_time') or "12:00",
                           spider_growth=db.get_setting('spider_growth_percent') or "20",
                           spider_min_fans=db.get_setting('spider_min_fans') or "5000",
                           ignored_keywords=db.get_setting('ignored_keywords') or DEFAULT_KEYWORDS,
                           max_tracks=db.get_setting('max_tracks') or "40"
                           )

@main_bp.route('/api/search_live')
def search_live():
    q = request.args.get('q', '').strip()
    return jsonify(get_metadata().find_potential_artists(q) if len(q) > 1 else [])
    
@main_bp.route('/api/manage_queue', methods=['POST'])
def manage_queue():
    action = request.form.get('action')
    db = get_db()
    
    try:
        if action == 'clear_pending':
            db.execute("DELETE FROM tracks WHERE status='pending' AND queue_id IN (SELECT id FROM queue WHERE status='pending')")
            db.execute("DELETE FROM queue WHERE status='pending'")
            sys_logger.log("USER", "🧹 Fila de pendentes limpa.")
            
        elif action == 'clear_errors':
            db.execute("DELETE FROM tracks WHERE queue_id IN (SELECT id FROM queue WHERE status='error')")
            db.execute("DELETE FROM queue WHERE status='error'")
            sys_logger.log("USER", "🧹 Itens com erro removidos.")

        elif action == 'clear_all':
            db.execute("DELETE FROM tracks WHERE status != 'completed'")
            db.execute("DELETE FROM queue WHERE status != 'completed'")
            sys_logger.log("USER", "☢️ Fila completamente zerada.")

        elif action == 'reset_stuck':
            count = db.query("SELECT count(*) as c FROM queue WHERE status='downloading'", one=True)['c']
            if count > 0:
                db.execute("UPDATE tracks SET status='pending' WHERE status='downloading'")
                db.execute("UPDATE queue SET status='pending' WHERE status='downloading'")
                sys_logger.log("SYSTEM", f"🔄 {count} álbuns travados foram resetados para a fila.")
            else:
                sys_logger.log("SYSTEM", "Nenhum download travado encontrado.")

        # --- NOVA AÇÃO: LIMPEZA RETROATIVA ---
        elif action == 'purge_filtered':
            keywords_str = db.get_setting('ignored_keywords') or ""
            blacklist = [k.strip().lower() for k in keywords_str.split(',') if k.strip()]
            max_tracks = int(db.get_setting('max_tracks') or 40)
            
            candidates = db.query("""
                SELECT q.id, q.title, COUNT(t.id) as track_count 
                FROM queue q 
                LEFT JOIN tracks t ON q.id = t.queue_id 
                WHERE q.status != 'completed'
                GROUP BY q.id
            """)
            
            ids_to_remove = []
            
            for item in candidates:
                title = item['title'].lower()
                track_count = item['track_count']
                
                if any(bad in title for bad in blacklist):
                    ids_to_remove.append(item['id'])
                    continue
                
                if track_count > max_tracks:
                    ids_to_remove.append(item['id'])
                    continue
            
            if ids_to_remove:
                chunk_size = 500
                for i in range(0, len(ids_to_remove), chunk_size):
                    chunk = ids_to_remove[i:i + chunk_size]
                    placeholders = ','.join('?' for _ in chunk)
                    db.execute(f"DELETE FROM tracks WHERE queue_id IN ({placeholders})", tuple(chunk))
                    db.execute(f"DELETE FROM queue WHERE id IN ({placeholders})", tuple(chunk))
            
            sys_logger.log("USER", f"🧹 Filtro Retroativo: {len(ids_to_remove)} álbuns indesejados removidos da fila.")

        return jsonify({'success': True})
        
    except Exception as e:
        sys_logger.log("ERROR", f"Erro ao gerenciar fila: {e}")
        return jsonify({'success': False, 'error': str(e)})

@main_bp.route('/api/clear_pending', methods=['POST'])
def clear_pending():
    get_db().execute("DELETE FROM queue WHERE status IN ('pending', 'high_priority')")
    return jsonify({'status': 'ok'})

@main_bp.route('/api/queue_data')
def api_queue():
    return jsonify({'active': [dict(r) for r in get_db().query("SELECT * FROM queue WHERE status='downloading'")], 'pending': [], 'history': []})

@main_bp.route('/api/logs_data')
def api_logs(): return jsonify(sys_logger.get_logs())

# --- WORKER: SINCRONIZAÇÃO COMPLETA ---
def background_sync_all(app):
    with app.app_context():
        db = get_db()
        metadata = get_metadata()
        downloader = get_downloader()
        
        sys_logger.log("SYNC", "🔄 Sincronização manual completa iniciada...")
        
        keywords_str = db.get_setting('ignored_keywords') or "playback,karaoke,instrumental,backing track"
        BLACKLIST = [k.strip().lower() for k in keywords_str.split(',')]
        max_tracks_val = int(db.get_setting('max_tracks') or 40)
        
        artists = db.query("SELECT * FROM artists")
        count_queued = 0
        
        for art in artists:
            try:
                discography = metadata.get_discography(art['deezer_id'], target_artist_id=art['name'])
                
                for item in discography:
                    if any(bad in item['title'].lower() for bad in BLACKLIST): continue
                    if item.get('nb_tracks', 0) > max_tracks_val: continue

                    exists = db.query("SELECT 1 FROM queue WHERE deezer_id=?", (item['deezer_id'],), one=True)
                    
                    if not exists:
                        safe_artist = downloader.sanitize(art['name'])
                        safe_album = downloader.sanitize(item['title'])
                        
                        album_path = os.path.join("/music", safe_artist, safe_album)
                        initial_status = 'pending'
                        
                        if os.path.exists(album_path):
                            local_files = [f for f in os.listdir(album_path) if f.endswith(('.mp3', '.flac', '.m4a'))]
                            if len(local_files) >= item.get('nb_tracks', 0):
                                initial_status = 'completed'
                        
                        cur = db.execute("""
                            INSERT INTO queue (deezer_id, title, artist, type, status, cover_url) 
                            VALUES (?, ?, ?, 'album', ?, ?)
                        """, (item['deezer_id'], item['title'], art['name'], initial_status, item['cover']))
                        
                        queue_id = cur.lastrowid
                        
                        tracks = metadata.get_album_tracks(item['deezer_id'], fallback_artist=art['name'])
                        for t in tracks:
                            db.execute("""
                                INSERT INTO tracks (queue_id, title, artist, track_number, status, duration) 
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (queue_id, t['title'], t['artist'], t['track_num'], initial_status, t.get('duration', 0)))
                        
                        if initial_status == 'pending':
                            count_queued += 1
                            sys_logger.log("SYNC", f"➕ Adicionado à fila: {item['title']} - {art['name']}")

                time.sleep(0.5)
            except Exception as e:
                sys_logger.log("ERROR", f"Erro ao sincronizar {art['name']}: {e}")

        sys_logger.log("SYNC", f"🏁 Sincronização finalizada. {count_queued} novos álbuns na fila.")

@main_bp.route('/api/sync_library', methods=['POST'])
def sync_library():
    app_obj = current_app._get_current_object()
    threading.Thread(target=background_sync_all, args=(app_obj,)).start()
    return jsonify({'success': True, 'message': 'Sincronização iniciada! Acompanhe pelos Logs.'})

def process_single_track_fix(app, track_id):
    with app.app_context():
        db = get_db(); dl = get_downloader()
        track = db.query("SELECT * FROM tracks WHERE id=?", (track_id,), one=True)
        album = db.query("SELECT * FROM queue WHERE id=?", (track['queue_id'],), one=True)
        if not track or not album: return

        meta = {
            'title': track['title'], 'artist': track['artist'],
            'album': album['title'], 'album_artist': album['artist'],
            'track_num': track['track_number'], 'manual_url': track['manual_url']
        }
        
        safe_artist = dl.sanitize(album['artist'])
        safe_album = dl.sanitize(album['title'])
        download_dir = os.path.join("/downloads", safe_artist, safe_album)
        os.makedirs(download_dir, exist_ok=True)
        
        db.execute("UPDATE tracks SET status='downloading' WHERE id=?", (track_id,))
        if dl.download_track(meta, download_dir):
            db.execute("UPDATE tracks SET status='completed', error_msg=NULL WHERE id=?", (track_id,))
            
            try:
                dest_dir = os.path.join("/music", safe_artist, safe_album)
                os.makedirs(dest_dir, exist_ok=True)
                src_file = os.path.join(download_dir, f"{str(track['track_number']).zfill(2)} - {dl.sanitize(track['title'])}.mp3")
                shutil.move(src_file, dest_dir)
            except: pass
            
            sys_logger.log("SUCCESS", f"✔ Faixa corrigida: {track['title']}")
        else:
            db.execute("UPDATE tracks SET status='error' WHERE id=?", (track_id,))

@main_bp.route('/api/fix_track', methods=['POST'])
def fix_track():
    track_id = request.form.get('track_id')
    manual_url = request.form.get('manual_url')
    
    if not track_id or not manual_url:
        return jsonify({'error': 'Dados incompletos'}), 400
    
    db = get_db()
    
    track = db.query("SELECT queue_id FROM tracks WHERE id=?", (track_id,), one=True)
    if not track:
        return jsonify({'error': 'Faixa não encontrada'}), 404
        
    queue_id = track['queue_id']
    
    db.execute("""
        UPDATE tracks 
        SET manual_url = ?, status = 'pending', error_msg = NULL 
        WHERE id = ?
    """, (manual_url, track_id))
    
    db.execute("UPDATE queue SET status='high_priority' WHERE id=?", (queue_id,))
    sys_logger.log("USER", f"🔗 Correção manual solicitada para faixa ID {track_id}")
    return jsonify({'success': True})

# Define um local seguro e persistente para as imagens
ARTIST_IMG_DIR = "/config/artist_images"

@main_bp.route('/artist_image/<artist_name>')
def get_artist_image(artist_name):
    if not artist_name: return "", 404
    os.makedirs(ARTIST_IMG_DIR, exist_ok=True)
    safe_name = "".join([c for c in artist_name if c.isalpha() or c.isdigit() or c in ' .-_()']).strip()
    file_path = os.path.join(ARTIST_IMG_DIR, f"{safe_name}.jpg")
    
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='image/jpeg')
    
    try:
        db = get_db()
        metadata = current_app.config['METADATA']
        artist = db.query("SELECT deezer_id FROM artists WHERE name = ?", (artist_name,), one=True)
        image_url = None
        
        if artist and artist['deezer_id']:
            info = metadata.get_artist(artist['deezer_id'])
            image_url = info.get('picture_xl') or info.get('picture_medium')
        else:
            search_results = metadata.search_artist(artist_name)
            if search_results:
                best_match = search_results[0]
                image_url = best_match.get('picture_xl') or best_match.get('picture_medium')
                if best_match.get('id'):
                    exists = db.query("SELECT 1 FROM artists WHERE name=?", (artist_name,), one=True)
                    if exists:
                        db.execute("UPDATE artists SET deezer_id=? WHERE name=?", (best_match['id'], artist_name))

        if image_url:
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                return send_file(file_path, mimetype='image/jpeg')
                
    except Exception as e:
        print(f"Erro ao recuperar imagem para {artist_name}: {e}")

    return "", 404