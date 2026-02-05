import time
import os
from .logger import sys_logger

class LibraryMaintenance:
    def __init__(self, db, metadata_provider, downloader):
        self.db = db
        self.metadata = metadata_provider
        self.downloader = downloader

    def run(self):
        sys_logger.log("MAINTAIN", "🛠️ Iniciando verificação de integridade da biblioteca...")
        
        # 1. Pega todos os álbuns marcados como 'completed'
        albums = self.db.query("SELECT * FROM queue WHERE status='completed'")
        
        repaired_count = 0
        
        for album in albums:
            try:
                # Pega faixas da API
                api_tracks = self.metadata.get_album_tracks(album['deezer_id'], fallback_artist=album['artist'])
                
                # Pega faixas que já temos no banco para este álbum
                # Usamos um set de IDs para busca rápida
                local_tracks = self.db.query("SELECT deezer_id FROM tracks WHERE queue_id=? AND status='completed'", (album['id'],))
                local_ids = set(t['deezer_id'] for t in local_tracks)
                
                missing_tracks = []
                
                # Verifica quais da API não estão no banco (ou não estão completas)
                for t in api_tracks:
                    if t['deezer_id'] not in local_ids:
                        missing_tracks.append(t)
                
                # Se faltar algo...
                if missing_tracks:
                    sys_logger.log("MAINTAIN", f"⚠️ Álbum incompleto: {album['title']} (Faltam {len(missing_tracks)} faixas). Reparando...")
                    
                    # Adiciona as faixas faltantes na tabela tracks
                    for t in missing_tracks:
                        # Verifica se já não existe como 'pending' ou 'error' para não duplicar
                        exists_pending = self.db.query(
                            "SELECT 1 FROM tracks WHERE queue_id=? AND deezer_id=?", 
                            (album['id'], t['deezer_id']), 
                            one=True
                        )
                        
                        if not exists_pending:
                            self.db.execute(
                                "INSERT INTO tracks (queue_id, deezer_id, title, artist, track_number, status) VALUES (?, ?, ?, ?, ?, 'pending')",
                                (album['id'], t['deezer_id'], t['title'], t['artist'], t['track_num'])
                            )
                    
                    # Reabre o álbum na fila para o Worker processar
                    self.db.execute("UPDATE queue SET status='pending' WHERE id=?", (album['id'],))
                    repaired_count += 1
                    
                # Opcional: Pausa curta para não bombardear a API se tiver muitos álbuns
                time.sleep(0.1)

            except Exception as e:
                sys_logger.log("ERROR", f"Erro ao verificar álbum {album['title']}: {e}")

        if repaired_count > 0:
            sys_logger.log("MAINTAIN", f"✅ Manutenção concluída. {repaired_count} álbuns enviados para reparo.")
        else:
            sys_logger.log("MAINTAIN", "✅ Biblioteca íntegra. Nenhuma faixa faltando.")