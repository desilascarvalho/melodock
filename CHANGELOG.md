## 🚀 v5.3.2

Correções críticas de estabilidade e busca, além do novo sistema de imagens.

### ✨ Melhorias
- **Imagens via ID:** O sistema agora busca imagens usando o ID único do Deezer, evitando erros com nomes parecidos.
- **Auto-Repair:** Se a imagem de um artista não existir localmente, ela é baixada automaticamente da API em tempo real ao abrir a biblioteca.
- **Cache Inteligente:** Força a atualização visual das imagens no navegador quando a versão do sistema muda.

### 🐛 Correções de Bugs
- **Explorer Search:** Corrigido erro `405 Method Not Allowed` que impedia a busca de novos artistas na aba Explorer.
- **Queue Manager:** Corrigido erro de sintaxe (crash) ao tentar usar os botões de "Limpar Fila" ou "Limpar Pendentes".