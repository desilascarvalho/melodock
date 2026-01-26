import os
from .logger import sys_logger

MUSIC_LIB_DIR = "/music"

class LibraryScanner:
    def __init__(self, metadata_provider):
        self.metadata = metadata_provider

    def scan_folders(self):
        """
        Lê as pastas em /music e tenta adivinhar o artista.
        Retorna uma lista de candidatos para o usuário aprovar.
        """
        if not os.path.exists(MUSIC_LIB_DIR):
            return {"error": "Diretório /music não encontrado"}

        folders = [f for f in os.listdir(MUSIC_LIB_DIR) if os.path.isdir(os.path.join(MUSIC_LIB_DIR, f))]
        folders.sort()

        candidates = []
        
        for folder_name in folders:
            if folder_name.startswith('.'): continue 

            sys_logger.log("SCAN", f"Analisando pasta: {folder_name}")
            
            result = self.metadata.search_artist(folder_name)
            
            candidate = {
                "folder": folder_name,
                "detected_name": "Desconhecido",
                "deezer_id": "",
                "status": "not_found",
                "image": ""
            }

            if result:
                candidate["detected_name"] = result['name']
                candidate["deezer_id"] = result['id']
                candidate["image"] = result['image']
                candidate["status"] = "found"
            
            candidates.append(candidate)

        return candidates