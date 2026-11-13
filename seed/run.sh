#!/bin/sh
# Executa a carga de exemplos a partir da raiz do projeto.
# Interrompe o script em caso de erro ou uso de variável não definida.
set -eu

# Calcula a raiz a partir da localização deste script.
cd "$(dirname "$0")/.."
# Repassa os argumentos recebidos para o programa Python de carga.
python seed/__init__.py "$@"
