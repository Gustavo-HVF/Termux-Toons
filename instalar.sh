#!/usr/bin/env bash
# Instala o essencial para o Termux-Toons e cria o atalho "toons".
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -z "$PREFIX" ] || [[ "$PREFIX" != *com.termux* ]]; then
    echo "Este script é para o Termux. Fora dele, rode: python3 $DIR/termux_toons.py"
    exit 1
fi

pkg update -y
pkg install -y python tmux termux-api git curl

if [ ! -d "$HOME/storage" ]; then
    echo "Permita o acesso ao armazenamento na janela do Android..."
    termux-setup-storage || true
fi

if ! grep -q "alias toons=" "$HOME/.bashrc" 2>/dev/null; then
    echo "alias toons='python $DIR/termux_toons.py'" >> "$HOME/.bashrc"
fi

echo
echo "Pronto! Abra uma nova sessão (ou rode: source ~/.bashrc) e digite: toons"
echo "Para sensores, SMS, câmera etc. instale também o app Termux:API (F-Droid)."
