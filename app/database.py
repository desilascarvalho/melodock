import sqlite3
import os
import time

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self._ensure_directory()

    def _ensure_directory(self):
        """Garante que a pasta onde o banco vai ficar existe e é gravável"""
        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"📁 Diretório criado: {directory}")
            except Exception as e:
                print(f"❌ ERRO CRÍTICO: Não foi possível criar pasta do banco: {e}")

    def get_connection(self):
        """Cria conexão com timeout maior para evitar travamentos em disco lento"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """
        Executado SEMPRE que o app inicia.
        Cria as tabelas e aplica migrações de schema.
        """
        print(f"🔄 Verificando integridade do banco de dados em: {self.db_path}...")
        
        create_statements = [
            # 1. Configurações
            '''CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )''',
            
            # 2. Artistas (Usando deezer_id como chave)
            '''CREATE TABLE IF NOT EXISTS artists (
                deezer_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                genre TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
            
            # 3. Fila/Álbuns
            '''CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deezer_id TEXT,
                title TEXT,
                artist TEXT,
                type TEXT,
                status TEXT DEFAULT 'pending',
                error_msg TEXT,
                cover_url TEXT, 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
            
            # 4. Faixas
            '''CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                queue_id INTEGER,
                title TEXT,
                artist TEXT,
                track_number INTEGER,
                status TEXT DEFAULT 'pending',
                manual_url TEXT,
                file_path TEXT,
                error_msg TEXT,
                duration INTEGER DEFAULT 0,
                FOREIGN KEY(queue_id) REFERENCES queue(id) ON DELETE CASCADE
            )'''
        ]

        try:
            with self.get_connection() as conn:
                # 1. Cria tabelas se não existirem
                for sql in create_statements:
                    conn.execute(sql)
                
                # 2. Insere configurações padrão
                conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('scan_time', '03:00')")
                
                # --- AUTO MIGRAÇÃO (CORREÇÃO DO ERRO DE DURATION) ---
                try:
                    # Tenta adicionar a coluna duration em bancos antigos
                    conn.execute("ALTER TABLE tracks ADD COLUMN duration INTEGER DEFAULT 0")
                    print("✅ Schema Migrado: Coluna 'duration' adicionada a tabela tracks.")
                except sqlite3.OperationalError:
                    # Se der erro, é porque a coluna já existe. Ignoramos.
                    pass
                # ----------------------------------------------------

                conn.commit()
                print("✅ Banco de dados pronto e verificado.")
                
        except sqlite3.OperationalError as e:
            print(f"❌ ERRO DE PERMISSÃO OU DISCO: {e}")
            print("⚠️  Verifique se o Docker tem permissão de escrita na pasta /config")

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
        res = self.query("SELECT value FROM settings WHERE key=?", (key,), one=True)
        return res['value'] if res else None

    def set_setting(self, key, value):
        self.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))