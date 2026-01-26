import sqlite3
import os

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self._ensure_directory()

    def _ensure_directory(self):
        d = os.path.dirname(self.db_path)
        if not os.path.exists(d): os.makedirs(d, exist_ok=True)

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')

            conn.execute('''CREATE TABLE IF NOT EXISTS artists (
                deezer_id TEXT PRIMARY KEY, 
                name TEXT, 
                genre TEXT, 
                image_url TEXT, 
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_sync TIMESTAMP
            )''')
            
            conn.execute('''CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY AUTOINCREMENT, deezer_id TEXT, title TEXT, artist TEXT, type TEXT, status TEXT DEFAULT 'pending', error_msg TEXT, cover_url TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            conn.execute('''CREATE TABLE IF NOT EXISTS tracks (id INTEGER PRIMARY KEY AUTOINCREMENT, queue_id INTEGER, deezer_id TEXT, title TEXT, artist TEXT, track_number INTEGER, status TEXT DEFAULT 'pending', manual_url TEXT, duration INTEGER DEFAULT 0, FOREIGN KEY(queue_id) REFERENCES queue(id) ON DELETE CASCADE)''')

            try: conn.execute("ALTER TABLE tracks ADD COLUMN deezer_id TEXT")
            except: pass
            try: conn.execute("ALTER TABLE artists ADD COLUMN image_url TEXT")
            except: pass
            
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('scan_time', '03:00')")
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('download_quality', '3')")
            conn.commit()

    def query(self, sql, args=(), one=False):
        with self.get_connection() as conn:
            cur = conn.execute(sql, args)
            rv = cur.fetchall()
            return (rv[0] if rv else None) if one else rv

    def execute(self, sql, args=()):
        with self.get_connection() as conn:
            cur = conn.execute(sql, args)
            conn.commit()
            return cur

    def get_setting(self, key):
        r = self.query("SELECT value FROM settings WHERE key=?", (key,), one=True)
        return r['value'] if r else None

    def set_setting(self, key, value):
        self.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))