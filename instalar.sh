#!/usr/bin/env bash
# Instala o essencial para o LNUX e cria o atalho "lnux" (o antigo "toons" passa a abrir o LNUX também).
# Funciona no Termux (Android) e nas distros com apt, pacman, dnf, apk ou zypper.
# Na primeira vez que abrir, o LNUX pergunta qual sistema você usa (já sugerindo o certo).
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

# sudo/doas só quando precisa (no Termux e para quem já é root, não)
if [ "$(id -u)" -eq 0 ]; then
    ROOT=""
elif command -v sudo >/dev/null 2>&1; then
    ROOT="sudo"
elif command -v doas >/dev/null 2>&1; then
    ROOT="doas"
else
    ROOT=""
fi

if [ -n "$PREFIX" ] && [[ "$PREFIX" == *com.termux* ]]; then
    echo "Termux (Android) detectado."
    pkg update -y
    pkg install -y python tmux termux-api git curl
    if [ ! -d "$HOME/storage" ]; then
        echo "Permita o acesso ao armazenamento na janela do Android..."
        termux-setup-storage || true
    fi
    DICA="Para sensores, SMS, câmera etc. instale também o app Termux:API (F-Droid)."
elif command -v apt-get >/dev/null 2>&1; then
    echo "Debian/Ubuntu (apt) detectado."
    $ROOT apt-get update
    $ROOT apt-get install -y python3 python3-pip tmux git curl xdg-utils libnotify-bin
elif command -v pacman >/dev/null 2>&1; then
    echo "Arch (pacman) detectado."
    $ROOT pacman -S --needed --noconfirm python python-pip tmux git curl xdg-utils libnotify
elif command -v dnf >/dev/null 2>&1; then
    echo "Fedora/RHEL (dnf) detectado."
    $ROOT dnf install -y python3 python3-pip tmux git curl xdg-utils libnotify
elif command -v apk >/dev/null 2>&1; then
    echo "Alpine (apk) detectado."
    $ROOT apk add python3 py3-pip tmux git curl xdg-utils libnotify bash
elif command -v zypper >/dev/null 2>&1; then
    echo "openSUSE (zypper) detectado."
    $ROOT zypper --non-interactive install python3 python3-pip tmux git curl xdg-utils libnotify-tools
else
    echo "Não reconheci o gerenciador de pacotes. Instale python3 (3.9 ou mais novo), tmux, git e curl"
    echo "pelo seu sistema e rode: python3 $DIR/lnux.py"
fi

# atalhos: 'lnux' e o antigo 'toons' (agora abrindo o lnux.py)
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ "$rc" = "$HOME/.zshrc" ] && [ ! -f "$rc" ]; then
        continue
    fi
    touch "$rc"
    if ! grep -q "alias lnux=" "$rc"; then
        echo "alias lnux='python3 $DIR/lnux.py'" >> "$rc"
    fi
    if grep -q "^alias toons=" "$rc"; then
        sed -i "s#^alias toons=.*#alias toons='python3 $DIR/lnux.py'#" "$rc"
    fi
done

echo
echo "Pronto! Abra um novo terminal (ou rode: source ~/.bashrc) e digite: lnux"
[ -n "$DICA" ] && echo "$DICA"
exit 0
