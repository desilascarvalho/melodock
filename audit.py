import os

# Pastas e arquivos para IGNORAR (não queremos ver isso no log)
IGNORE_DIRS = {
    '.git', '__pycache__', 'downloads', 'config', 'venv', 
    '.processing', 'instance', 'deemix', 'xdg', 'cache'
}
IGNORE_EXTS = {'.db', '.pyc', '.jpg', '.png', '.mp3', '.flac', '.zip', '.tar'}
READ_EXTS = {'.py', '.html', '.css', '.js', '.txt', '.md', '.yml', '.yaml', '.json'}

def audit_project(startpath):
    print("=== ESTRUTURA DO PROJETO ===")
    for root, dirs, files in os.walk(startpath):
        # Filtra pastas ignoradas
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print(f'{indent}{os.path.basename(root)}/')
        for f in files:
            if not any(f.endswith(ext) for ext in IGNORE_EXTS):
                print(f'{indent}    {f}')

    print("\n" + "="*40)
    print("=== CONTEÚDO DOS ARQUIVOS CÓDIGO ===")
    print("="*40)
    
    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for f in files:
            if f.endswith(tuple(READ_EXTS)) and "audit.py" not in f:
                filepath = os.path.join(root, f)
                print(f"\n\n--- ARQUIVO: {filepath} ---")
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f_read:
                        print(f_read.read())
                except Exception as e:
                    print(f"[Erro ao ler: {e}]")

if __name__ == '__main__':
    # Roda na pasta atual
    audit_project('.')
