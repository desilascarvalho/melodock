## 🚀 v5.3.1

Correção definitiva de metadados para Plex e Jellyfin.

### ✨ Melhorias
- **Tagging Rigoroso:** O sistema agora força o salvamento de apenas **um artista** na tag de metadados, impedindo que o Plex separe faixas incorretamente (ex: "Artist A; Artist B").
- **Feat Handling:** Artistas convidados (Feat.) são movidos obrigatoriamente para o Título da música e removidos da tag Artista.
- **Limpeza:** A tag oculta `artists` (plural) foi desativada para garantir compatibilidade máxima com media servers.