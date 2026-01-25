## 🚀 v5.3.2

Correção rigorosa de tags para Media Servers (Plex/Jellyfin).

### ✨ Melhorias
- **Anti-Split:** Implementado separador textual (` & `) para artistas múltiplos. Isso impede que o Plex use `;` para quebrar o artista em duas entradas separadas.
- **Tag Cleaning:** Tags desnecessárias (Compositor, Envolvidos, Lista de Artistas) foram desativadas para manter os metadados limpos.
- **Single Artist:** Reforço na configuração para manter o artista principal no foco.