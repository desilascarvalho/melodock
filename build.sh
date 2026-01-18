#!/bin/bash

# 1. Verifica se o arquivo de contagem existe, se não, cria com 0
if [ ! -f build_counter.txt ]; then
    echo 0 > build_counter.txt
fi

# 2. Lê o número atual
CURRENT_BUILD=$(cat build_counter.txt)

# 3. Incrementa +1
NEW_BUILD=$((CURRENT_BUILD + 1))

# 4. Salva o novo número
echo $NEW_BUILD > build_counter.txt

echo "🚀 Iniciando Build da Versão v3.0.$NEW_BUILD ..."

# 5. Roda o Docker passando o número novo
# Note o --build-arg BUILD_NUM=$NEW_BUILD
docker build --build-arg BUILD_NUM=$NEW_BUILD -t desilascarvalho/melodock:latest .

echo "✅ Sucesso! Nova versão v3.0.$NEW_BUILD criada."