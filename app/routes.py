from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify, send_file
from .services.logger import sys_logger
from collections import defaultdict
from difflib import SequenceMatcher
import threading
import os
import shutil
import math
import time
import re
from datetime import datetime

main_bp = Blueprint('main', __name__)

def get_db(): return current_app.config['DB']
def get_meta(): return current_app.config['METADATA']
def get_dl(): return current_app.config['DOWNLOADER']


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

    page = request.args.get('page', 1, type=int)
    per_page = 30
    offset = (page - 1) * per_page
    total_pages = math.ceil(stats['artists'] / per_page) if stats['artists'] else 1

    sort = request.args.get('sort', 'date_desc')
    if sort == 'name_asc':
        order = "ORDER BY name ASC"
    elif sort == 'name_desc':
        order = "ORDER BY name DESC"
    elif sort == 'date_asc':
        order = "ORDER BY added_at ASC"
    else:
        order = "ORDER BY added_at DESC"

    artists_raw = db.query(f"SELECT * FROM artists {order} LIMIT ? OFFSET ?", (per_page, offset))

    artists_list = []
    for art in artists_raw:
        a_dict = dict(art)
        pending = db.query("SELECT 1 FROM queue WHERE artist=? AND status IN ('pending', 'downloading')", (art['name'],), one=True)
        error = db.query("SELECT 1 FROM queue WHERE artist=? AND status='error'", (art['name'],), one=True)

        if pending:
            a_dict['visual_status'] = 'syncing'
        elif error:
            a_dict['visual_status'] = 'error'
        else:
            a_dict['visual_status'] = 'ok'

        artists_list.append(a_dict)

    return render_template(
        'dashboard.html',
        stats=stats,
        artists_list=artists_list,
        current_sort=sort,
        current_page=page,
        total_pages=total_pages
    )


@main_bp.route('/downloads')
def downloads():
    db = get_db()
    active = db.query("SELECT title, artist FROM queue WHERE status='downloading' LIMIT 1", one=True)
    raw = db.query("SELECT * FROM queue WHERE status IN ('pending', 'high_priority', 'error') ORDER BY id ASC")

    grouped = defaultdict(list)
    prio = {}
    for i in raw:
        grouped[i['artist']].append(i)
        if i['status'] == 'high_priority':
            prio[i['artist']] = True

    return render_template('downloads.html', active=active, grouped_queue=grouped, artist_priority=prio)


@main_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    db = get_db()
    if request.method == 'POST':
        if request.form.get('deezer_arl'):
            db.set_setting('deezer_arl', request.form.get('deezer_arl').strip())
        if request.form.get('download_quality'):
            db.set_setting('download_quality', request.form.get('download_quality'))
        if request.form.get('ignored_keywords'):
            db.set_setting('ignored_keywords', request.form.get('ignored_keywords'))
        if request.form.get('max_tracks'):
            db.set_setting('max_tracks', request.form.get('max_tracks'))
        if request.form.get('scan_time'):
            db.set_setting('scan_time', request.form.get('scan_time'))

        sys_logger.log("CONFIG", "Configurações Salvas.")
        return redirect('/settings')

    return render_template(
        'settings.html',
        deezer_arl=db.get_setting('deezer_arl') or "",
        download_quality=db.get_setting('download_quality') or "3",
        ignored_keywords=db.get_setting('ignored_keywords') or "",
        max_tracks=db.get_setting('max_tracks') or "40",
        scan_time=db.get_setting('scan_time') or "03:00"
    )


# --- SYNC ---
def background_sync(app):
    with app.app_context():
        sys_logger.log("SYNC", "🔄 Sincronizando biblioteca...")
        db = get_db()
        artists = db.query("SELECT * FROM artists")
        for art in artists:
            try:
                background_add(app, art['deezer_id'], art['name'])
            except:
                pass
        sys_logger.log("SYNC", "✅ Sincronização finalizada.")


@main_bp.route('/api/sync_library', methods=['POST'])
def sync_library():
    app_obj = current_app._get_current_object()
    threading.Thread(target=background_sync, args=(app_obj,)).start()
    return jsonify({'message': 'Sincronização iniciada.'})


def background_add(app, aid, aname):
    with app.app_context():
        meta = get_meta()
        db = get_db()
        dl = get_dl()

        sys_logger.log("SYSTEM", f"Processando {aname}...")

        keywords = db.get_setting('ignored_keywords') or ""
        BLACKLIST = [k.strip().lower() for k in keywords.split(',') if k.strip()]
        MAX_TRACKS = int(db.get_setting('max_tracks') or 40)

        art_data = meta.get_artist_by_id(aid) if aid else meta.search_artist(aname)
        if not art_data:
            return

        db.execute(
            "REPLACE INTO artists (deezer_id, name, image_url, last_sync) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (art_data['id'], art_data['name'], art_data.get('image'))
        )

        # ✅ Nunca quebrar o fluxo por causa de imagem
        try:
            if hasattr(dl, "save_artist_image"):
                dl.save_artist_image(art_data['name'], art_data.get('image'))
            else:
                sys_logger.log("SYSTEM", "⚠️ Downloader sem save_artist_image (ignorando imagem).")
        except Exception as e:
            sys_logger.log("ERROR", f"Falha ao salvar imagem (ignorando): {e}")

        albums = meta.get_discography(
            art_data['id'],
            target_artist_id=art_data['name'],
            blacklist=BLACKLIST
        )

        cnt = 0
        for alb in albums:
            if alb.get('track_count', 0) > MAX_TRACKS:
                continue

            if not db.query("SELECT 1 FROM queue WHERE deezer_id=?", (alb['deezer_id'],), one=True):
                cur = db.execute(
                    "INSERT INTO queue (deezer_id, title, artist, cover_url, status) VALUES (?, ?, ?, ?, 'pending')",
                    (alb['deezer_id'], alb['title'], art_data['name'], alb.get('cover'))
                )
                qid = cur.lastrowid
                cnt += 1

                tracks = meta.get_album_tracks(alb['deezer_id'], fallback_artist=art_data['name'])
                for t in tracks:
                    db.execute(
                        "INSERT INTO tracks (queue_id, deezer_id, title, artist, track_number) VALUES (?, ?, ?, ?, ?)",
                        (qid, t.get('deezer_id'), t.get('title'), t.get('artist'), t.get('track_num'))
                    )

        if cnt > 0:
            sys_logger.log("SUCCESS", f"Found {cnt} new albums for {art_data['name']}.")


@main_bp.route('/add_artist', methods=['POST'])
def add_artist():
    app = current_app._get_current_object()
    threading.Thread(
        target=background_add,
        args=(app, request.form.get('chosen_id'), request.form.get('artist_name'))
    ).start()
    return redirect('/downloads')


def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def background_import_existing(app, data):
    with app.app_context():
        meta = get_meta()
        db = get_db()
        dl = get_dl()

        sys_logger.log("IMPORT", "🔄 Importando...")
        count = 0

        for item in data:
            deezer_id = item.get('deezer_id')
            if not deezer_id:
                continue

            art_data = meta.get_artist_by_id(deezer_id)
            if not art_data:
                continue

            db.execute(
                "REPLACE INTO artists (deezer_id, name, image_url, last_sync) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (art_data['id'], art_data['name'], art_data.get('image'))
            )

            try:
                if hasattr(dl, "save_artist_image"):
                    dl.save_artist_image(art_data['name'], art_data.get('image'))
            except:
                pass

            albums = meta.get_discography(art_data['id'], target_artist_id=art_data['name'])
            local_folder = item.get('folder')
            artist_path = os.path.join("/music", local_folder)

            if os.path.exists(artist_path):
                local_albums = [d for d in os.listdir(artist_path) if os.path.isdir(os.path.join(artist_path, d))]
                for alb in albums:
                    clean_dz = re.sub(r'[^\w\s]', '', alb['title']).lower()
                    match = False

                    for loc in local_albums:
                        clean_loc = re.sub(r'[^\w\s]', '', loc).lower()
                        if similar(clean_dz, clean_loc) > 0.75 or clean_dz in clean_loc:
                            match = True
                            break

                    if match:
                        if not db.query("SELECT 1 FROM queue WHERE deezer_id=?", (alb['deezer_id'],), one=True):
                            cur = db.execute(
                                "INSERT INTO queue (deezer_id, title, artist, cover_url, status) VALUES (?, ?, ?, ?, 'completed')",
                                (alb['deezer_id'], alb['title'], art_data['name'], alb.get('cover'))
                            )
                            qid = cur.lastrowid

                            tracks = meta.get_album_tracks(alb['deezer_id'], fallback_artist=art_data['name'])
                            for t in tracks:
                                db.execute(
                                    "INSERT INTO tracks (queue_id, deezer_id, title, artist, track_number, status) VALUES (?, ?, ?, ?, ?, 'completed')",
                                    (qid, t.get('deezer_id'), t.get('title'), t.get('artist'), t.get('track_num'))
                                )
                            count += 1

        sys_logger.log("IMPORT", f"✅ Fim. {count} álbuns vinculados.")


@main_bp.route('/api/import_library', methods=['POST'])
def import_library():
    data = request.json
    app_obj = current_app._get_current_object()
    threading.Thread(target=background_import_existing, args=(app_obj, data)).start()
    return jsonify({'success': True})


@main_bp.route('/api/scan_library_preview')
def scan_library_preview():
    from .services.scanner import LibraryScanner
    return jsonify(LibraryScanner(get_meta()).scan_folders())


@main_bp.route('/api/search_live')
def search_live():
    q = request.args.get('q', '')
    if len(q) < 2:
        return jsonify([])
    return jsonify(get_meta().find_potential_artists(q))


@main_bp.route('/artist_image/<artist_id>')
def get_image(artist_id):
    dl = get_dl()
    db = get_db()

    if '?' in artist_id:
        artist_id = artist_id.split('?')[0]

    artist_row = db.query("SELECT name FROM artists WHERE deezer_id=?", (artist_id,), one=True)

    if artist_row:
        safe_name = dl.sanitize(artist_row['name'])
        config_path = f"/config/artist_images/{safe_name}.jpg"
        if os.path.exists(config_path):
            return send_file(config_path)

        music_path = os.path.join("/music", safe_name)
        if os.path.exists(music_path):
            for img in ['folder.jpg', 'cover.jpg', 'artist.jpg', 'fanart.jpg']:
                if os.path.exists(os.path.join(music_path, img)):
                    return send_file(os.path.join(music_path, img))

    try:
        meta = get_meta()
        data = meta.get_artist_by_id(artist_id)

        if data and data.get('image'):
            if hasattr(dl, "save_artist_image"):
                dl.save_artist_image(data['name'], data.get('image'))

            safe_name = dl.sanitize(data['name'])
            config_path = f"/config/artist_images/{safe_name}.jpg"
            if os.path.exists(config_path):
                return send_file(config_path)
    except Exception as e:
        print(f"Erro imagem ID {artist_id}: {e}")

    return "", 404


@main_bp.route('/explorer', methods=['GET', 'POST'])
def explorer():
    recommendations = []
    search_term = ""

    if request.method == 'POST':
        search_term = request.form.get('artist_name', '').strip()
        if len(search_term) > 1:
            meta = get_meta()
            recommendations = meta.get_related_artists(search_term)

            db = get_db()
            for rec in recommendations:
                exists = db.query("SELECT 1 FROM artists WHERE deezer_id=?", (rec['id'],), one=True)
                rec['in_library'] = bool(exists)

    return render_template('explorer.html', recommendations=recommendations, search_term=search_term)


@main_bp.route('/artist/<path:artist_name>')
def artist_profile(artist_name):
    db = get_db()
    artist = db.query("SELECT * FROM artists WHERE name=?", (artist_name,), one=True)
    if not artist:
        return "Erro", 404
    albums = db.query("SELECT * FROM queue WHERE artist=?", (artist_name,))
    d = []
    for a in albums:
        d.append({**dict(a), 'visual_status': a['status']})
    return render_template('artist_details.html', artist=artist, albums=d)


@main_bp.route('/album/<int:qid>')
def album_details(qid):
    db = get_db()
    album = db.query("SELECT * FROM queue WHERE id=?", (qid,), one=True)
    tracks = db.query("SELECT * FROM tracks WHERE queue_id=?", (qid,))
    return render_template('album_details.html', album=album, tracks=tracks, progress={'total': len(tracks), 'completed': 0})


@main_bp.route('/delete_artist', methods=['POST'])
def delete_artist():
    get_db().execute("DELETE FROM artists WHERE name=?", (request.form.get('artist_name'),))
    get_db().execute("DELETE FROM queue WHERE artist=?", (request.form.get('artist_name'),))
    return redirect('/dashboard')


@main_bp.route('/logs')
def logs():
    return render_template('logs.html')


@main_bp.route('/api/logs_data')
def api_logs():
    return jsonify(sys_logger.get_logs())


@main_bp.route('/api/manage_queue', methods=['POST'])
def manage_queue():
    action = request.form.get('action')
    db = get_db()

    if action == 'clear_all':
        db.execute("DELETE FROM tracks WHERE status != 'completed'")
        db.execute("DELETE FROM queue WHERE status != 'completed'")
        sys_logger.log("USER", "☢️ Fila limpa.")
    elif action == 'clear_pending':
        db.execute("DELETE FROM tracks WHERE status='pending'")
        db.execute("DELETE FROM queue WHERE status='pending'")
        sys_logger.log("USER", "🧹 Pendentes limpos.")
    elif action == 'reset_stuck':
        db.execute("UPDATE queue SET status='pending' WHERE status='downloading'")
        db.execute("UPDATE tracks SET status='pending' WHERE status='downloading'")
        sys_logger.log("USER", "🔄 Destravado.")
    elif action == 'purge_filtered':
        keywords = db.get_setting('ignored_keywords') or ""
        blacklist = [k.strip().lower() for k in keywords.split(',') if k.strip()]
        max_tracks = int(db.get_setting('max_tracks') or 40)
        pending = db.query("SELECT * FROM queue WHERE status IN ('pending', 'high_priority', 'error')")
        cnt = 0
        for alb in pending:
            should_del = False
            if any(b in alb['title'].lower() for b in blacklist):
                should_del = True
            if not should_del:
                c = db.query("SELECT COUNT(*) as c FROM tracks WHERE queue_id=?", (alb['id'],), one=True)['c']
                if c > max_tracks:
                    should_del = True
            if should_del:
                db.execute("DELETE FROM tracks WHERE queue_id=?", (alb['id'],))
                db.execute("DELETE FROM queue WHERE id=?", (alb['id'],))
                cnt += 1
        sys_logger.log("FILTER", f"Limpeza concluída. {cnt} removidos.")

    return jsonify({'success': True})


def start_queue_worker(app):
    from .services.queue import QueueWorker
    QueueWorker(app.config['DB'], app.config['METADATA'], app.config['DOWNLOADER']).start()
