#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Termux-Toons — um canivete suíço em Python para o Termux.

Reúne em um único menu:
   1. Servidor web/API pessoal (Flask, FastAPI ou só biblioteca padrão) + Cloudflare Tunnel
   2. Bots de Telegram e Discord rodando 24h (tmux + termux-wake-lock)
   3. Automação com Termux:API (sensores, SMS, notificações, TTS, câmera, localização)
   4. LLMs locais com llama.cpp compilado no próprio celular
   5. Interfaces TUI (dashboard com rich, tarefas com curses)
   6. Ambiente de desenvolvimento (Neovim + LSP, git, C/Rust/Go, code-server)
   7. Scraping e monitoramento (preço, notícias/RSS, status de site)
   8. Rede e segurança em equipamentos seus (nmap, SSH, WireGuard, velocidade)
   9. Retro: jogos ASCII, interpretador BASIC e template para criar seu jogo
  10. Linux de verdade com proot-distro (Debian, Ubuntu, Arch...)
  11. Servidor de arquivos e backup (rclone, Syncthing, Samba, HTTP)
  12. "Spotify" no terminal: yt-dlp para baixar e mpv para tocar
  13. Vídeos do TikTok, YouTube e outros sites com yt-dlp
  14. Atualização do Termux e dos repositórios
  15. Otimização e limpeza (caches, arquivos grandes/duplicados, processos)

Uso:
    python termux_toons.py            # menu interativo
    python termux_toons.py --help     # subcomandos (também usados pelo tmux)

Só precisa da biblioteca padrão do Python para abrir; o resto (flask, rich,
pacotes do Termux...) é instalado sob demanda, perguntando antes.
"""

from __future__ import annotations

import argparse
import atexit
import contextlib
import copy
import getpass
import hashlib
import hmac
import importlib
import importlib.util
import io
import json
import math
import os
import platform
import random
import re
import secrets
import select
import shlex
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    import termios
    import tty
except ImportError:  # sem terminal POSIX (ex.: Windows): só o modo numérico
    termios = tty = None

VERSION = "1.1.0"
SCRIPT = Path(__file__).resolve()
HOME = Path.home()
PREFIX = os.environ.get("PREFIX", "")
IS_TERMUX = "com.termux" in PREFIX or "TERMUX_VERSION" in os.environ
SHELL_BIN = shutil.which("bash") or shutil.which("sh") or "/bin/sh"

DATA_DIR = HOME / ".termux_toons"
CONFIG_FILE = DATA_DIR / "config.json"
LOG_DIR = DATA_DIR / "logs"
TASKS_FILE = DATA_DIR / "tarefas.json"
STATE_FILE = DATA_DIR / "monitores_estado.json"
RECORDES_FILE = DATA_DIR / "recordes.json"
BASIC_DIR = DATA_DIR / "basic"
DOWNLOADS = HOME / "storage" / "downloads"
LLAMA_DIR = HOME / "llama.cpp"
MODELS_DIR = HOME / "llama-models"
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36"
)


# ════════════════════════════════════════════════════════════════════
#  Interface de texto: cores, mensagens, perguntas e menus
# ════════════════════════════════════════════════════════════════════

_COR = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _c(codigo: int) -> str:
    return f"\033[{codigo}m" if _COR else ""


RST, NEG, DIM, INV = _c(0), _c(1), _c(2), _c(7)
VERM, VERD, AMAR, AZUL, MAG, CIANO = _c(31), _c(32), _c(33), _c(34), _c(35), _c(36)


class ToonsError(Exception):
    """Erro esperado: é mostrado ao usuário sem traceback."""


def limpar() -> None:
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="", flush=True)


def ok(msg: str) -> None:
    print(f"{VERD}✔{RST} {msg}")


def info(msg: str) -> None:
    print(f"{CIANO}ℹ{RST} {msg}")


def aviso(msg: str) -> None:
    print(f"{AMAR}⚠{RST} {msg}")


def erro(msg: str) -> None:
    print(f"{VERM}✖{RST} {msg}")


def log(msg: str) -> None:
    """Mensagem com data/hora, usada pelos serviços em segundo plano."""
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def largura_tela() -> int:
    return shutil.get_terminal_size((60, 20)).columns


def _centralizar(texto: str, largura: int) -> str:
    sobra = max(0, largura - _largura(texto))
    return " " * (sobra // 2) + texto + " " * (sobra - sobra // 2)


def titulo(texto: str) -> None:
    largura = max(20, min(largura_tela(), 70))
    print(f"{CIANO}{'═' * largura}{RST}")
    print(f"{NEG}{_centralizar(texto, largura)}{RST}")
    print(f"{CIANO}{'═' * largura}{RST}")


def perguntar(msg: str, padrao=None) -> str:
    sufixo = f" [{padrao}]" if padrao not in (None, "") else ""
    try:
        resp = input(f"{AMAR}?{RST} {msg}{sufixo}: ").strip()
    except EOFError:
        # Sem terminal para ler (stdin fechado): não há como continuar.
        print()
        raise SystemExit(0) from None
    if resp:
        return resp
    return "" if padrao is None else str(padrao)


def perguntar_int(msg: str, padrao=None, minimo=None, maximo=None) -> int:
    while True:
        resp = perguntar(msg, padrao)
        try:
            valor = int(resp)
        except ValueError:
            erro("Digite um número inteiro.")
            continue
        if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
            erro(f"Valor fora do intervalo ({minimo}–{maximo}).")
            continue
        return valor


def perguntar_float(msg: str, padrao=None) -> float:
    while True:
        resp = perguntar(msg, padrao).replace(",", ".")
        try:
            return float(resp)
        except ValueError:
            erro("Digite um número (ex.: 199.90).")


# ── Navegação com as setas ──────────────────────────────────────────
# Menus e listas são escolhidos com ↑/↓ e Enter. Sem terminal interativo
# (saída redirecionada, scripts) ou com TOONS_NUMEROS=1, volta ao modo de
# digitar o número da opção.

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_SEQUENCIAS = {
    b"[A": "cima", b"OA": "cima", b"[B": "baixo", b"OB": "baixo",
    b"[C": "dir", b"OC": "dir", b"[D": "esq", b"OD": "esq",
    b"[H": "home", b"OH": "home", b"[1~": "home", b"[7~": "home",
    b"[F": "end", b"OF": "end", b"[4~": "end", b"[8~": "end",
    b"[5~": "pgup", b"[6~": "pgdn",
}


def setas_ativas() -> bool:
    return (termios is not None and sys.stdin.isatty() and sys.stdout.isatty()
            and os.environ.get("TOONS_NUMEROS") != "1")


def ler_tecla() -> str:
    """Lê uma tecla sem esperar Enter: 'cima', 'baixo', 'esq', 'dir', 'enter',
    'esc', 'home', 'end', 'pgup', 'pgdn', 'backspace' ou o próprio caractere."""
    fd = sys.stdin.fileno()
    antigo = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)  # sem eco e sem esperar Enter; Ctrl+C continua funcionando
        ch = os.read(fd, 1)
        if not ch:
            raise SystemExit(0)
        if ch == b"\x1b":
            seq, espera = b"", 0.15
            while select.select([fd], [], [], espera)[0]:
                seq += os.read(fd, 1)
                espera = 0.05
                if len(seq) >= 2 and (seq[-1:].isalpha() or seq.endswith(b"~")):
                    break
            return _SEQUENCIAS.get(seq, "" if seq else "esc")
        if ch in (b"\r", b"\n"):
            return "enter"
        if ch in (b"\x7f", b"\x08"):
            return "backspace"
        if ch == b"\x04":
            return "esc"
        if ch[0] >= 0xC0:  # caractere UTF-8 de vários bytes
            ch += os.read(fd, 1 if ch[0] < 0xE0 else 2 if ch[0] < 0xF0 else 3)
        return ch.decode("utf-8", errors="ignore")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, antigo)


def _cursor(visivel: bool) -> None:
    if sys.stdout.isatty():
        sys.stdout.write("\033[?25h" if visivel else "\033[?25l")
        sys.stdout.flush()


atexit.register(_cursor, True)


def _sem_ansi(texto: str) -> str:
    return _ANSI.sub("", texto)


def _largura_char(ch: str) -> int:
    if unicodedata.combining(ch) or unicodedata.category(ch) in ("Mn", "Me", "Cf"):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def _largura(texto: str) -> int:
    return sum(_largura_char(c) for c in _sem_ansi(texto))


def _cortar(texto: str, largura: int) -> str:
    """Corta um texto (que pode ter cores) para caber em `largura` colunas."""
    if _largura(texto) <= largura:
        return texto
    partes, usado, pos = [], 0, 0
    while pos < len(texto):
        m = _ANSI.match(texto, pos)
        if m:
            partes.append(m.group())
            pos = m.end()
            continue
        w = _largura_char(texto[pos])
        if usado + w > largura - 1:
            break
        partes.append(texto[pos])
        usado += w
        pos += 1
    return "".join(partes) + "…" + RST


def _linha_opcao(texto: str, selecionada: bool, colunas: int) -> str:
    if selecionada:
        return f"{CIANO}❯{RST} {INV}{NEG} {_cortar(_sem_ansi(texto), colunas - 5)} {RST}"
    return "   " + _cortar(texto, colunas - 4)


def _mover(tecla: str, sel: int, total: int, pagina: int) -> int:
    """Nova posição da seleção para as teclas de movimento (circular em ↑/↓)."""
    if tecla in ("cima", "k"):
        return (sel - 1) % total
    if tecla in ("baixo", "j"):
        return (sel + 1) % total
    if tecla == "home":
        return 0
    if tecla == "end":
        return total - 1
    if tecla == "pgup":
        return max(0, sel - pagina)
    if tecla == "pgdn":
        return min(total - 1, sel + pagina)
    return sel


def _janela(sel: int, topo: int, altura: int, total: int) -> int:
    """Ajusta o início da parte visível para a seleção ficar na tela."""
    if sel < topo:
        topo = sel
    elif sel >= topo + altura:
        topo = sel - altura + 1
    return max(0, min(topo, total - altura))


def _lista_inline(msg: str, opcoes: list, sel: int = 0, multipla: bool = False):
    """Lista escolhida com as setas logo abaixo da pergunta (sem limpar a tela)."""
    dica = "↑↓ · Espaço marca · a todas · Enter" if multipla else "↑↓ e Enter · Esc cancela"
    print(f"{AMAR}?{RST} {msg} {DIM}({dica}){RST}")
    marcadas, topo, desenhadas, resultado = set(), 0, 0, None
    _cursor(False)
    try:
        while True:
            colunas, linhas_tela = shutil.get_terminal_size((60, 24))
            altura = max(1, min(len(opcoes), linhas_tela - 3))
            topo = _janela(sel, topo, altura, len(opcoes))
            linhas = []
            for i in range(topo, topo + altura):
                caixa = ("[x] " if i in marcadas else "[ ] ") if multipla else ""
                linhas.append(_linha_opcao(caixa + str(opcoes[i]), i == sel, colunas))
            if len(opcoes) > altura:
                linhas.append(f"{DIM}   {sel + 1}/{len(opcoes)}{RST}")
            if desenhadas:
                sys.stdout.write(f"\033[{desenhadas}A\r")
            sys.stdout.write("".join(linha + "\033[K\n" for linha in linhas) + "\033[J")
            sys.stdout.flush()
            desenhadas = len(linhas)

            tecla = ler_tecla()
            if tecla in ("enter", "dir"):
                resultado = (sorted(marcadas) or [sel]) if multipla else sel
                break
            if tecla in ("esc", "esq", "q", "backspace"):
                break
            if multipla and tecla == " ":
                marcadas ^= {sel}
            elif multipla and tecla in ("a", "A"):
                marcadas = set() if len(marcadas) == len(opcoes) else set(range(len(opcoes)))
            elif tecla.isdigit() and 1 <= int(tecla) <= len(opcoes):
                sel = int(tecla) - 1
            else:
                sel = _mover(tecla, sel, len(opcoes), altura)
    finally:
        if desenhadas:
            sys.stdout.write(f"\033[{desenhadas}A\r\033[J")  # some com a lista
        _cursor(True)
    if resultado is None:
        print(f"   {DIM}cancelado{RST}")
    elif multipla:
        print(f"   {VERD}✔{RST} {len(resultado)} selecionada(s)")
    else:
        print(f"   {VERD}✔{RST} {_sem_ansi(str(opcoes[resultado]))}")
    return resultado


def confirmar(msg: str, padrao: bool = False) -> bool:
    if not setas_ativas():
        resp = perguntar(f"{msg} ({'S/n' if padrao else 's/N'})").lower()
        if not resp:
            return padrao
        return resp in ("s", "sim", "y", "yes")
    sim = padrao
    print(f"{AMAR}?{RST} {msg}")
    _cursor(False)
    try:
        while True:
            botoes = (f"{INV}{NEG} Sim {RST}  Não " if sim else f" Sim  {INV}{NEG} Não {RST}") if _COR \
                else ("[Sim]  Não " if sim else " Sim  [Não]")
            sys.stdout.write(f"\r   {botoes}  {DIM}(←→ e Enter){RST}\033[K")
            sys.stdout.flush()
            tecla = ler_tecla()
            if tecla in ("esq", "dir", "cima", "baixo", "\t"):
                sim = not sim
            elif tecla.lower() in ("s", "y"):
                sim = True
                break
            elif tecla.lower() == "n" or tecla == "esc":
                sim = False
                break
            elif tecla == "enter":
                break
    finally:
        _cursor(True)
    sys.stdout.write(f"\r   {VERD}✔{RST} {'Sim' if sim else 'Não'}\033[K\n")
    return sim


def pausar() -> None:
    if setas_ativas():
        print(f"\n{DIM}Pressione qualquer tecla para continuar...{RST}", end="", flush=True)
        with contextlib.suppress(KeyboardInterrupt):
            ler_tecla()
        print()
        return
    try:
        input(f"\n{DIM}Pressione Enter para continuar...{RST}")
    except EOFError:
        print()


def escolher(msg: str, opcoes: list, padrao=None):
    """Escolhe uma opção (setas ou número) e devolve o índice, ou None se cancelar."""
    if not opcoes:
        return None
    if setas_ativas():
        inicial = int(padrao) - 1 if str(padrao).isdigit() and 1 <= int(padrao) <= len(opcoes) else 0
        return _lista_inline(msg, opcoes, inicial)
    for i, op in enumerate(opcoes, 1):
        print(f"  {CIANO}{i:>2}{RST}) {op}")
    resp = perguntar(msg, padrao)
    if resp.isdigit() and 1 <= int(resp) <= len(opcoes):
        return int(resp) - 1
    return None


def _parse_selecao(texto: str, total: int) -> list:
    """'1,3,5-8' -> [0, 2, 4, 5, 6, 7]"""
    indices = []
    for parte in texto.replace(" ", "").split(","):
        if re.fullmatch(r"\d+-\d+", parte):
            a, b = map(int, parte.split("-"))
            indices += range(a - 1, b)
        elif parte.isdigit():
            indices.append(int(parte) - 1)
    return [i for i in dict.fromkeys(indices) if 0 <= i < total]


def escolher_varios(msg: str, opcoes: list) -> list:
    """Marca várias opções (Espaço) e devolve os índices; lista vazia se cancelar."""
    if not opcoes:
        return []
    if setas_ativas():
        return _lista_inline(msg, opcoes, multipla=True) or []
    for i, op in enumerate(opcoes, 1):
        print(f"  {CIANO}{i:>3}{RST}) {op}")
    resp = perguntar(f"{msg} (ex.: 1,4,7-9; 'a' = todas)", "")
    if resp.lower() in ("a", "todas"):
        return list(range(len(opcoes)))
    return _parse_selecao(resp, len(opcoes))


def mostrar_dados(dados, recuo: int = 0) -> None:
    """Imprime dict/list aninhados de forma legível."""
    esp = "  " * recuo
    if isinstance(dados, dict):
        for chave, valor in dados.items():
            if isinstance(valor, (dict, list)) and valor:
                print(f"{esp}{CIANO}{chave}{RST}:")
                mostrar_dados(valor, recuo + 1)
            else:
                print(f"{esp}{CIANO}{chave}{RST}: {valor}")
    elif isinstance(dados, list):
        for item in dados:
            if isinstance(item, (dict, list)):
                mostrar_dados(item, recuo)
                print(f"{esp}{DIM}—{RST}")
            else:
                print(f"{esp}• {item}")
    else:
        print(f"{esp}{dados}")


def submenu(func):
    """Marca uma função como submenu (não limpa a tela nem pausa ao voltar)."""
    func._submenu = True
    return func


def executar(func, rotulo: str = "") -> None:
    eh_submenu = getattr(func, "_submenu", False)
    falhou = False
    try:
        if not eh_submenu:
            limpar()
            titulo(rotulo)
        func()
    except KeyboardInterrupt:
        print()
        aviso("Interrompido.")
    except ToonsError as e:
        erro(str(e))
        falhou = True
    except Exception as e:  # noqa: BLE001 — o menu nunca deve morrer
        erro(f"Erro inesperado: {e!r}")
        if os.environ.get("TOONS_DEBUG"):
            traceback.print_exc()
        falhou = True
    if not eh_submenu or falhou:
        pausar()


def _menu_setas(titulo_menu: str, itens: list, sair: str, cabecalho, sel: int):
    """Desenha o menu em tela cheia e devolve o índice escolhido (None = voltar)."""
    linhas_cab = []
    if cabecalho:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            cabecalho()
        linhas_cab = buffer.getvalue().rstrip("\n").split("\n")
    topo, digitos, t_digito = 0, "", 0.0
    limpar()
    _cursor(False)
    try:
        while True:
            colunas, linhas_tela = shutil.get_terminal_size((60, 24))
            rotulos = [r() if callable(r) else r for r, _ in itens] + [f"↩  {sair}"]
            total = len(rotulos)
            cab = linhas_cab
            disponivel = linhas_tela - len(cab) - 5
            if disponivel < min(total, 6):  # tela pequena: esconde o cabeçalho
                cab, disponivel = [], linhas_tela - 5
            altura = max(1, min(total, disponivel))
            topo = _janela(sel, topo, altura, total)
            largura = max(20, min(colunas, 70))
            linhas = [*cab, f"{CIANO}{'═' * largura}{RST}", f"{NEG}{_centralizar(titulo_menu, largura)}{RST}",
                      f"{CIANO}{'═' * largura}{RST}"]
            linhas += [_linha_opcao(rotulos[i], i == sel, colunas) for i in range(topo, topo + altura)]
            rodape = "↑↓ mover · Enter abre · Esc volta"
            if total > altura:
                rodape += f" · {sel + 1}/{total}"
            linhas += ["", f"{DIM}{rodape}{RST}"]
            sys.stdout.write("\033[H" + "\n".join(_cortar(linha, colunas) + "\033[K" for linha in linhas)
                             + "\033[J")
            sys.stdout.flush()

            tecla = ler_tecla()
            if tecla in ("enter", "dir", " "):
                return None if sel == total - 1 else sel
            if tecla in ("esc", "esq", "q", "backspace"):
                return None
            if tecla.isdigit():  # atalho: digitar o número da opção (0 = voltar)
                agora = time.time()
                digitos = digitos + tecla if agora - t_digito < 1.0 else tecla
                t_digito = agora
                if not 0 <= int(digitos) < total:
                    digitos = tecla
                sel = total - 1 if int(digitos) == 0 else min(int(digitos), total) - 1
            else:
                sel = _mover(tecla, sel, total, altura)
    finally:
        _cursor(True)


def menu(titulo_menu: str, itens: list, sair: str = "Voltar", cabecalho=None) -> None:
    if setas_ativas():
        sel = 0
        while True:
            try:
                escolha = _menu_setas(titulo_menu, itens, sair, cabecalho, sel)
            except KeyboardInterrupt:
                return
            if escolha is None:
                return
            sel = escolha
            rotulo, func = itens[escolha]
            executar(func, rotulo() if callable(rotulo) else rotulo)
    while True:
        limpar()
        if cabecalho:
            cabecalho()
        titulo(titulo_menu)
        for i, (rotulo, _) in enumerate(itens, 1):
            print(f"  {CIANO}{i:>2}{RST}) {rotulo() if callable(rotulo) else rotulo}")
        print(f"  {CIANO}{0:>2}{RST}) {sair}")
        try:
            esc = perguntar("Escolha")
        except KeyboardInterrupt:
            print()
            return
        if esc.lower() in ("0", "q", "sair", "voltar"):
            return
        if not esc.isdigit() or not 1 <= int(esc) <= len(itens):
            continue
        rotulo, func = itens[int(esc) - 1]
        executar(func, rotulo() if callable(rotulo) else rotulo)


# ════════════════════════════════════════════════════════════════════
#  Comandos do sistema, pacotes do Termux e módulos Python
# ════════════════════════════════════════════════════════════════════

def tem(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def rodar(cmd, *, capturar=False, timeout=None, entrada=None, cwd=None,
          mostrar=True, check=False) -> subprocess.CompletedProcess:
    """Executa um comando (lista = sem shell; string = via shell)."""
    usa_shell = isinstance(cmd, str)
    if not usa_shell:
        cmd = [str(c) for c in cmd]
    if mostrar and not capturar:
        print(f"{DIM}$ {cmd if usa_shell else shlex.join(cmd)}{RST}", flush=True)
    try:
        proc = subprocess.run(
            cmd, shell=usa_shell, executable=SHELL_BIN if usa_shell else None,
            text=True, errors="replace", capture_output=capturar,
            timeout=timeout, input=entrada, cwd=cwd,
        )
    except FileNotFoundError:
        proc = subprocess.CompletedProcess(cmd, 127, "", f"comando não encontrado: {cmd[0]}")
    except subprocess.TimeoutExpired:
        proc = subprocess.CompletedProcess(cmd, 124, "", "tempo esgotado")
    if check and proc.returncode != 0:
        detalhe = (proc.stderr or "").strip()[-500:] if capturar else ""
        raise ToonsError(f"Comando falhou (código {proc.returncode}). {detalhe}".strip())
    return proc


def saida(cmd, timeout: float = 20) -> str:
    """Stdout de um comando, ou "" se falhar."""
    proc = rodar(cmd, capturar=True, timeout=timeout, mostrar=False)
    return (proc.stdout or "").strip() if proc.returncode == 0 else ""


def cmd_self(*args: str) -> str:
    """Linha de comando para chamar este próprio script (usada dentro do tmux)."""
    return "PYTHONUNBUFFERED=1 " + shlex.join([sys.executable, str(SCRIPT), *args])


def instalar_pkg(*pacotes: str) -> bool:
    if not IS_TERMUX:
        aviso("Fora do Termux: instale manualmente → " + " ".join(pacotes))
        return False
    return rodar(["pkg", "install", "-y", *pacotes]).returncode == 0


def instalar_de_repo(repo: str, *pacotes: str) -> bool:
    """Ativa um repositório extra (root-repo, tur-repo, x11-repo) e instala pacotes dele."""
    if not instalar_pkg(repo):
        return False
    rodar(["pkg", "update", "-y"])
    return instalar_pkg(*pacotes)


def garantir_cmd(cmd: str, pacote: str | None = None, perguntar_antes: bool = True,
                 repo: str | None = None) -> bool:
    """Verifica se um comando existe; se não, oferece instalar o pacote."""
    if tem(cmd):
        return True
    pacote = pacote or cmd
    aviso(f"'{cmd}' não encontrado (pacote: {pacote}{', do ' + repo if repo else ''}).")
    if perguntar_antes and not confirmar(f"Instalar '{pacote}' agora?", True):
        return False
    if repo:
        instalar_de_repo(repo, *pacote.split())
    else:
        instalar_pkg(*pacote.split())
    return tem(cmd)


def instalar_pip(*pacotes: str) -> bool:
    return rodar([sys.executable, "-m", "pip", "install", "-U", *pacotes]).returncode == 0


def modulo_existe(nome: str) -> bool:
    try:
        return importlib.util.find_spec(nome) is not None
    except (ImportError, ValueError):
        return False


def garantir_modulo(modulo: str, pip_nome: str | None = None, pkg_nome: str | None = None,
                    aviso_extra: str = "") -> bool:
    """Importa um módulo opcional; se faltar, oferece instalar (pkg ou pip)."""
    if modulo_existe(modulo):
        return True
    nome = pip_nome or modulo
    aviso(f"Módulo Python '{modulo}' não está instalado.")
    if aviso_extra:
        info(aviso_extra)
    if not confirmar(f"Instalar '{pkg_nome if (pkg_nome and IS_TERMUX) else nome}' agora?", True):
        return False
    if pkg_nome and IS_TERMUX:
        instalar_pkg(pkg_nome)
    else:
        instalar_pip(*nome.split())
    importlib.invalidate_caches()
    if modulo_existe(modulo):
        ok(f"'{modulo}' instalado.")
        return True
    erro(f"Não foi possível instalar '{modulo}'.")
    return False


def garantir_storage() -> bool:
    """Garante acesso a ~/storage (termux-setup-storage)."""
    if (HOME / "storage").exists():
        return True
    aviso("Sem acesso ao armazenamento compartilhado (~/storage).")
    if IS_TERMUX and tem("termux-setup-storage") and confirmar("Rodar termux-setup-storage agora?", True):
        rodar(["termux-setup-storage"])
        info("Aceite a permissão no Android...")
        for _ in range(20):
            if (HOME / "storage").exists():
                return True
            time.sleep(1)
    return (HOME / "storage").exists()


def bytes_humanos(n: float) -> str:
    for unidade in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unidade == "TB":
            return f"{n:.1f} {unidade}" if unidade != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def fatiar(texto: str, tamanho: int) -> list:
    return [texto[i:i + tamanho] for i in range(0, len(texto), tamanho)] or [""]


# ════════════════════════════════════════════════════════════════════
#  Configuração e arquivos JSON
# ════════════════════════════════════════════════════════════════════

PADRAO_CFG = {
    "api_token": "",
    "web_porta": 8000,
    "web_framework": "flask",
    "telegram_token": "",
    "telegram_ids_permitidos": [],
    "discord_token": "",
    "discord_ids_permitidos": [],
    "bot_permitir_shell": False,
    "alerta_tts": False,
    "alerta_telegram": True,
    "tts_idioma": "",
    "pasta_musicas": "~/storage/downloads",
    "pasta_videos": "~/storage/downloads",
    "llama_porta": 8080,
    "llama_modelo": "",
    "llama_threads": 4,
    "llama_contexto": 2048,
    "aviso_rede_aceito": False,
    "monitores": [],
}

_CFG: dict | None = None


def ler_json(caminho: Path, padrao):
    try:
        return json.loads(caminho.read_text("utf-8"))
    except FileNotFoundError:
        return copy.deepcopy(padrao)
    except (OSError, json.JSONDecodeError) as e:
        aviso(f"Não consegui ler {caminho.name} ({e}); usando valores padrão.")
        return copy.deepcopy(padrao)


def gravar_json(caminho: Path, dados, privado: bool = False) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_name(caminho.name + ".tmp")
    tmp.write_text(json.dumps(dados, indent=2, ensure_ascii=False), "utf-8")
    if privado:
        os.chmod(tmp, 0o600)
    tmp.replace(caminho)


def cfg() -> dict:
    global _CFG
    if _CFG is None:
        _CFG = {**copy.deepcopy(PADRAO_CFG), **ler_json(CONFIG_FILE, {})}
        if not _CFG.get("api_token"):
            _CFG["api_token"] = secrets.token_urlsafe(24)
            salvar_cfg()
    return _CFG


def salvar_cfg() -> None:
    gravar_json(CONFIG_FILE, cfg(), privado=True)


def recarregar_cfg() -> dict:
    global _CFG
    _CFG = None
    return cfg()


def mascarar(segredo: str) -> str:
    if not segredo:
        return "(vazio)"
    return segredo[:4] + "…" + segredo[-4:] if len(segredo) > 10 else "****"


# ════════════════════════════════════════════════════════════════════
#  Serviços em segundo plano: tmux + termux-wake-lock
# ════════════════════════════════════════════════════════════════════

def sessao(nome: str) -> str:
    return f"toons-{nome}"


def log_de(nome: str) -> Path:
    return LOG_DIR / f"{nome}.log"


def servico_ativo(nome: str) -> bool:
    if not tem("tmux"):
        return False
    # "=" força nome exato (sem isso o tmux aceita prefixos).
    return rodar(["tmux", "has-session", "-t", "=" + sessao(nome)],
                 capturar=True, mostrar=False).returncode == 0


def servicos_ativos() -> list:
    if not tem("tmux"):
        return []
    nomes = saida(["tmux", "list-sessions", "-F", "#{session_name}"], timeout=5)
    return [s[len("toons-"):] for s in nomes.splitlines() if s.startswith("toons-")]


def iniciar_servico(nome: str, comando: str, reiniciar: bool = False,
                    wake_lock: bool = True, com_log: bool = True) -> bool:
    """Roda `comando` numa sessão tmux destacada, com log em ~/.termux_toons/logs."""
    if not garantir_cmd("tmux"):
        return False
    if servico_ativo(nome):
        aviso(f"'{nome}' já está rodando.")
        return True
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    arq_log = log_de(nome)
    if arq_log.exists() and arq_log.stat().st_size > 5 * 1024 * 1024:
        arq_log.replace(arq_log.with_suffix(".log.old"))
    q_log = shlex.quote(str(arq_log))
    linha = f"{comando} 2>&1 | tee -a {q_log}" if com_log else comando
    if reiniciar:
        linha = (f"while true; do {linha}; echo \"[$(date)] encerrou; reiniciando em 5s...\" "
                 f"| tee -a {q_log}; sleep 5; done")
    if wake_lock and tem("termux-wake-lock"):
        rodar(["termux-wake-lock"], mostrar=False, timeout=10)
    rodar(["tmux", "new-session", "-d", "-s", sessao(nome), linha], mostrar=False)
    time.sleep(1.5)
    if servico_ativo(nome):
        ok(f"'{nome}' rodando em segundo plano (sessão tmux '{sessao(nome)}').")
        info(f"Log: {arq_log}")
        return True
    erro(f"'{nome}' não ficou de pé. Últimas linhas do log:")
    ver_log(nome, 15)
    return False


def parar_servico(nome: str) -> None:
    if not servico_ativo(nome):
        info(f"'{nome}' não está rodando.")
        return
    rodar(["tmux", "kill-session", "-t", "=" + sessao(nome)], mostrar=False)
    ok(f"'{nome}' parado.")
    if not servicos_ativos() and tem("termux-wake-unlock"):
        rodar(["termux-wake-unlock"], mostrar=False, timeout=10)
        info("Nenhum serviço ativo: wake-lock liberado.")


def ver_log(nome: str, linhas: int = 40) -> None:
    arq = log_de(nome)
    if not arq.exists():
        info("Ainda não há log para este serviço.")
        return
    conteudo = arq.read_text("utf-8", errors="replace").splitlines()[-linhas:]
    print("\n".join(conteudo))


def status_servico(nome: str) -> None:
    if servico_ativo(nome):
        ok(f"'{nome}' está RODANDO.")
    else:
        aviso(f"'{nome}' está PARADO.")
    print(f"{DIM}── últimas linhas do log ──{RST}")
    ver_log(nome, 25)


def abrir_sessao(nome: str) -> None:
    if not servico_ativo(nome):
        info(f"'{nome}' não está rodando.")
        return
    info("Para sair SEM parar o serviço: Ctrl+b e depois d.")
    time.sleep(1.5)
    if os.environ.get("TMUX"):
        rodar(["tmux", "switch-client", "-t", "=" + sessao(nome)], mostrar=False)
    else:
        rodar(["tmux", "attach", "-t", "=" + sessao(nome)], mostrar=False)


def itens_servico(nome: str, rotulo: str, iniciar) -> list:
    """Itens de menu padrão para controlar um serviço em segundo plano."""
    return [
        (f"{rotulo}: iniciar em segundo plano", iniciar),
        (f"{rotulo}: parar", lambda: parar_servico(nome)),
        (f"{rotulo}: status e log", lambda: status_servico(nome)),
        (f"{rotulo}: abrir a sessão tmux", lambda: abrir_sessao(nome)),
    ]


# ════════════════════════════════════════════════════════════════════
#  Termux:API (precisa do pacote termux-api e do app Termux:API)
# ════════════════════════════════════════════════════════════════════

def _tapi(cmd: list, timeout: float = 30, entrada: str | None = None, json_saida: bool = True):
    if not tem(cmd[0]):
        raise ToonsError(f"'{cmd[0]}' não encontrado. Instale com 'pkg install termux-api' "
                         "e instale também o app Termux:API (F-Droid).")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                              timeout=timeout, input=entrada)
    except subprocess.TimeoutExpired:
        raise ToonsError(f"'{cmd[0]}' não respondeu em {timeout:.0f}s. O app Termux:API está "
                         "instalado e com as permissões concedidas?") from None
    texto = proc.stdout.strip()
    if proc.returncode != 0 and not texto:
        raise ToonsError(proc.stderr.strip() or f"'{cmd[0]}' falhou.")
    if json_saida and texto:
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError:
            return texto
        if isinstance(dados, dict) and dados.get("error"):
            raise ToonsError(f"{cmd[0]}: {dados['error']}")
        return dados
    return texto


def bateria() -> dict:
    dados = _tapi(["termux-battery-status"], 15)
    if not isinstance(dados, dict):
        raise ToonsError(f"Resposta inesperada: {dados}")
    return dados


def notificar(titulo_n: str, texto: str, nid: str | None = None, som: bool = False) -> None:
    if not tem("termux-notification"):
        print(f"[notificação] {titulo_n}: {texto}")
        return
    cmd = ["termux-notification", "--title", titulo_n, "--content", texto]
    if nid:
        cmd += ["--id", str(nid)]
    if som:
        cmd.append("--sound")
    _tapi(cmd, 15, json_saida=False)


def falar(texto: str) -> None:
    cmd = ["termux-tts-speak"]
    idioma = cfg().get("tts_idioma")
    if idioma:
        cmd += ["-l", idioma]
    _tapi(cmd, 180, entrada=texto, json_saida=False)  # sem argumentos o texto vem do stdin


def vibrar(ms: int = 500) -> None:
    _tapi(["termux-vibrate", "-d", str(ms)], 10, json_saida=False)


def lanterna(ligar: bool) -> None:
    _tapi(["termux-torch", "on" if ligar else "off"], 10, json_saida=False)


def localizacao(provedor: str = "network") -> dict:
    dados = _tapi(["termux-location", "-p", provedor, "-r", "once"], 90)
    if not isinstance(dados, dict) or "latitude" not in dados:
        raise ToonsError("Localização indisponível (GPS/localização do Android ligada?).")
    return dados


def foto(destino: str | Path | None = None, camera: int = 0) -> Path:
    destino = Path(destino or DATA_DIR / f"foto_{datetime.now():%Y%m%d_%H%M%S}.jpg")
    destino.parent.mkdir(parents=True, exist_ok=True)
    _tapi(["termux-camera-photo", "-c", str(camera), str(destino)], 40, json_saida=False)
    if not destino.exists() or destino.stat().st_size == 0:
        raise ToonsError("A foto não foi gerada (o Termux:API tem permissão de câmera?).")
    return destino


def sms_enviar(numero: str, texto: str) -> None:
    _tapi(["termux-sms-send", "-n", numero, texto], 30, json_saida=False)


def sms_listar(n: int = 10) -> list:
    dados = _tapi(["termux-sms-list", "-l", str(n)], 30)
    return dados if isinstance(dados, list) else []


def sensores() -> list:
    dados = _tapi(["termux-sensor", "-l"], 15)
    return dados.get("sensors", []) if isinstance(dados, dict) else []


def ler_sensor(nome: str):
    return _tapi(["termux-sensor", "-s", nome, "-n", "1"], 20)


# ════════════════════════════════════════════════════════════════════
#  Informações do sistema
# ════════════════════════════════════════════════════════════════════

def ip_local() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # não envia nada, só escolhe a interface
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def ip_publico() -> str:
    try:
        req = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=6) as r:
            return r.read().decode().strip()
    except (OSError, ValueError):
        return "indisponível"


def memoria() -> tuple:
    """(total, disponível) em bytes, lidos de /proc/meminfo."""
    valores = {}
    try:
        for linha in Path("/proc/meminfo").read_text().splitlines():
            chave, _, resto = linha.partition(":")
            valores[chave] = int(resto.split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        return 0, 0
    return valores.get("MemTotal", 0), valores.get("MemAvailable", valores.get("MemFree", 0))


def tempo_ligado() -> str:
    try:
        seg = int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        return "?"
    dias, seg = divmod(seg, 86400)
    horas, seg = divmod(seg, 3600)
    return f"{dias}d {horas}h {seg // 60}m"


def carga_media():
    try:
        return tuple(round(x, 2) for x in os.getloadavg())
    except OSError:
        return None


def getprop(nome: str) -> str:
    return saida(["getprop", nome], timeout=5) if tem("getprop") else ""


def status_sistema(com_bateria: bool = True) -> dict:
    total, disp = memoria()
    disco = shutil.disk_usage(HOME)
    dados = {
        "aparelho": getprop("ro.product.model") or platform.node(),
        "android": getprop("ro.build.version.release") or platform.platform(),
        "python": platform.python_version(),
        "hora": datetime.now().isoformat(timespec="seconds"),
        "ligado_ha": tempo_ligado(),
        "carga": carga_media(),
        "ip_local": ip_local(),
        "memoria": {"total": bytes_humanos(total), "livre": bytes_humanos(disp),
                    "uso_pct": round(100 * (1 - disp / total), 1) if total else None},
        "armazenamento": {"total": bytes_humanos(disco.total), "livre": bytes_humanos(disco.free),
                          "uso_pct": round(100 * disco.used / disco.total, 1)},
        "servicos": servicos_ativos(),
    }
    if com_bateria:
        try:
            b = bateria()
            dados["bateria"] = {k: b.get(k) for k in ("percentage", "status", "temperature", "plugged")}
        except ToonsError:
            dados["bateria"] = None
    return dados


def formatar_status(s: dict) -> str:
    linhas = [
        f"📱 {s['aparelho']} (Android {s['android']})",
        f"⏱️ Ligado há {s['ligado_ha']}",
        f"🧠 RAM: {s['memoria']['livre']} livres de {s['memoria']['total']}",
        f"💾 Disco: {s['armazenamento']['livre']} livres de {s['armazenamento']['total']}",
        f"🌐 IP local: {s['ip_local']}",
    ]
    b = s.get("bateria")
    if b:
        linhas.append(f"🔋 Bateria: {b['percentage']}% ({b['status']}, {b['temperature']}°C)")
    linhas.append(f"⚙️ Serviços: {', '.join(s['servicos']) or 'nenhum'}")
    return "\n".join(linhas)


# ════════════════════════════════════════════════════════════════════
#  1. Servidor web / API pessoal
# ════════════════════════════════════════════════════════════════════

PAGINA_HTML = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Termux-Toons</title>
<style>
 body{font-family:system-ui,sans-serif;background:#111;color:#eee;margin:0;padding:16px;max-width:640px}
 h1{font-size:1.4em} input,button,textarea{font-size:1em;padding:8px;margin:4px 0;border-radius:6px;border:1px solid #444;background:#222;color:#eee}
 button{background:#2a6;border:0;cursor:pointer} input,textarea{width:100%;box-sizing:border-box}
 pre{background:#000;padding:10px;border-radius:6px;white-space:pre-wrap;word-break:break-word}
</style></head><body>
<h1>📱 Termux-Toons API</h1>
<input id="tk" type="password" placeholder="Token da API (fica salvo neste navegador)">
<div>
 <button onclick="api('GET','/api/status')">Status</button>
 <button onclick="api('GET','/api/bateria')">Bateria</button>
 <button onclick="api('POST','/api/vibrar',{ms:400})">Vibrar</button>
 <button onclick="api('POST','/api/lanterna',{ligar:true})">Lanterna ON</button>
 <button onclick="api('POST','/api/lanterna',{ligar:false})">OFF</button>
</div>
<textarea id="tx" rows="2" placeholder="Texto para notificar, falar ou perguntar à IA"></textarea>
<div>
 <button onclick="api('POST','/api/notificar',{titulo:'Web',texto:tx.value})">Notificar</button>
 <button onclick="api('POST','/api/falar',{texto:tx.value})">Falar (TTS)</button>
 <button onclick="api('POST','/api/ia',{prompt:tx.value})">Perguntar à IA</button>
</div>
<pre id="out">Pronto.</pre>
<script>
const tk=document.getElementById('tk'),out=document.getElementById('out'),tx=document.getElementById('tx');
try{tk.value=localStorage.getItem('toons_token')||''}catch(e){}
tk.onchange=()=>{try{localStorage.setItem('toons_token',tk.value)}catch(e){}};
async function api(m,p,b){out.textContent='...';
 try{const r=await fetch(p,{method:m,headers:{'Authorization':'Bearer '+tk.value,'Content-Type':'application/json'},body:b?JSON.stringify(b):undefined});
 out.textContent=r.status+'\\n'+JSON.stringify(await r.json(),null,2)}catch(e){out.textContent='Erro: '+e}}
</script></body></html>
"""


def _bool(valor) -> bool:
    if isinstance(valor, str):
        return valor.strip().lower() not in ("0", "false", "off", "nao", "não", "")
    return bool(valor)


def _exigir(dados: dict, chave: str) -> str:
    valor = str(dados.get(chave, "")).strip()
    if not valor:
        raise ValueError(f"campo '{chave}' é obrigatório")
    return valor


class ToonsAPI:
    """Lógica da API independente de framework: Flask, FastAPI e stdlib só fazem a ponte."""

    def __init__(self):
        self.token = cfg()["api_token"]
        # (método, caminho) -> (exige_token, função(dados) -> dict)
        self.rotas = {
            ("GET", "/api/ping"): (False, lambda d: {"pong": True, "versao": VERSION}),
            ("GET", "/api/status"): (True, lambda d: status_sistema()),
            ("GET", "/api/bateria"): (True, lambda d: bateria()),
            ("GET", "/api/local"): (True, lambda d: localizacao(d.get("provedor", "network"))),
            ("GET", "/api/servicos"): (True, lambda d: {"ativos": servicos_ativos()}),
            ("POST", "/api/notificar"): (True, lambda d: notificar(
                str(d.get("titulo", "Termux-Toons")), _exigir(d, "texto"))),
            ("POST", "/api/falar"): (True, lambda d: falar(_exigir(d, "texto"))),
            ("POST", "/api/vibrar"): (True, lambda d: vibrar(int(d.get("ms", 500)))),
            ("POST", "/api/lanterna"): (True, lambda d: lanterna(_bool(d.get("ligar", True)))),
            ("POST", "/api/ia"): (True, lambda d: {"resposta": ia_perguntar(_exigir(d, "prompt"))}),
        }

    def autorizado(self, headers: dict, query: dict) -> bool:
        auth = headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
        else:
            token = headers.get("x-token") or query.get("token", "")
        return bool(token) and hmac.compare_digest(token.encode(), self.token.encode())

    @staticmethod
    def _json(status: int, dados) -> tuple:
        return status, "application/json; charset=utf-8", json.dumps(dados, ensure_ascii=False).encode()

    def tratar(self, metodo: str, caminho: str, query: dict, corpo: bytes, headers: dict) -> tuple:
        """Devolve (status, content-type, corpo em bytes)."""
        headers = {k.lower(): v for k, v in headers.items()}
        caminho = "/" + caminho.strip("/")
        metodo = metodo.upper()
        if caminho == "/" and metodo == "GET":
            return 200, "text/html; charset=utf-8", PAGINA_HTML.encode()
        rota = self.rotas.get((metodo, caminho))
        if rota is None:
            if any(c == caminho for _, c in self.rotas):
                return self._json(405, {"erro": "método não permitido"})
            return self._json(404, {"erro": "rota não encontrada", "rotas": sorted(
                f"{m} {c}" for m, c in self.rotas)})
        protegida, func = rota
        if protegida and not self.autorizado(headers, query):
            return self._json(401, {"erro": "token inválido ou ausente"})
        dados = {k: v for k, v in query.items() if k != "token"}
        if corpo:
            try:
                extra = json.loads(corpo.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return self._json(400, {"erro": "corpo não é JSON válido"})
            if isinstance(extra, dict):
                dados.update(extra)
        try:
            resultado = func(dados)
        except (ToonsError, ValueError, KeyError) as e:
            return self._json(400, {"erro": str(e)})
        except Exception as e:  # noqa: BLE001
            return self._json(500, {"erro": repr(e)})
        return self._json(200, {"ok": True} if resultado is None else resultado)


def _rodar_flask(api: ToonsAPI, host: str, porta: int) -> None:
    from flask import Flask, Response, request

    app = Flask("termux_toons")
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

    @app.route("/", defaults={"caminho": ""}, methods=["GET", "POST"])
    @app.route("/<path:caminho>", methods=["GET", "POST"])
    def tudo(caminho):
        status, tipo, corpo = api.tratar(request.method, caminho, request.args.to_dict(),
                                         request.get_data(), dict(request.headers))
        return Response(corpo, status=status, content_type=tipo)

    app.run(host=host, port=porta, threaded=True)


def _rodar_fastapi(api: ToonsAPI, host: str, porta: int) -> None:
    import uvicorn
    from fastapi import FastAPI, Request
    from fastapi.responses import Response
    from starlette.concurrency import run_in_threadpool

    app = FastAPI(title="Termux-Toons API", version=VERSION)

    async def tudo(caminho, request):
        corpo = await request.body()
        status, tipo, dados = await run_in_threadpool(
            api.tratar, request.method, caminho, dict(request.query_params), corpo, dict(request.headers))
        return Response(content=dados, status_code=status, media_type=tipo)

    # Anotações como objetos (não strings): o FastAPI precisa delas para injetar o Request.
    tudo.__annotations__ = {"caminho": str, "request": Request}
    app.add_api_route("/{caminho:path}", tudo, methods=["GET", "POST"])
    uvicorn.run(app, host=host, port=porta)


def _rodar_stdlib(api: ToonsAPI, host: str, porta: int) -> None:
    class Handler(BaseHTTPRequestHandler):
        server_version = f"TermuxToons/{VERSION}"

        def _tratar(self):
            url = urllib.parse.urlsplit(self.path)
            query = dict(urllib.parse.parse_qsl(url.query))
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                tamanho = 0
            if tamanho > 1024 * 1024:
                status, tipo, dados = ToonsAPI._json(413, {"erro": "corpo grande demais"})
            else:
                corpo = self.rfile.read(tamanho) if tamanho > 0 else b""
                status, tipo, dados = api.tratar(self.command, url.path, query, corpo, dict(self.headers))
            self.send_response(status)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

        do_GET = do_POST = _tratar

        def log_message(self, fmt, *args):
            log(f"{self.client_address[0]} " + re.sub(r"token=[^&\s\"]+", "token=***", fmt % args))

    with ThreadingHTTPServer((host, porta), Handler) as servidor:
        servidor.serve_forever()


DEPENDENCIAS_WEB = {
    "flask": [("flask", "flask")],
    "fastapi": [("fastapi", "fastapi"), ("uvicorn", "uvicorn")],
    "stdlib": [],
}


def servir(framework: str, host: str, porta: int) -> None:
    """Sobe o servidor em primeiro plano (é o que roda dentro do tmux)."""
    faltando = [m for m, _ in DEPENDENCIAS_WEB.get(framework, []) if not modulo_existe(m)]
    if faltando:
        raise ToonsError(f"Faltam módulos para {framework}: {', '.join(faltando)}. "
                         "Instale pelo menu do servidor web ou use --framework stdlib.")
    api = ToonsAPI()
    log(f"Termux-Toons API ({framework}) em http://{host}:{porta}")
    log(f"Na rede local: http://{ip_local()}:{porta}  |  Ctrl+C para parar")
    runner = {"flask": _rodar_flask, "fastapi": _rodar_fastapi}.get(framework, _rodar_stdlib)
    runner(api, host, porta)


def garantir_dependencias_web(framework: str) -> bool:
    extra = ("No Termux o FastAPI compila o pydantic-core (Rust). Se falhar, rode "
             "'pkg install rust' e tente de novo, ou use Flask/stdlib.") if framework == "fastapi" else ""
    return all(garantir_modulo(mod, pip, aviso_extra=extra) for mod, pip in DEPENDENCIAS_WEB[framework])


def url_tunel():
    arq = log_de("tunel")
    if not arq.exists():
        return None
    achados = re.findall(r"https://[a-z0-9-]+\.trycloudflare\.com", arq.read_text("utf-8", errors="replace"))
    return achados[-1] if achados else None


@submenu
def menu_web():
    c = cfg()

    def iniciar():
        fw, porta = c["web_framework"], c["web_porta"]
        if not garantir_dependencias_web(fw):
            return
        if iniciar_servico("web", cmd_self("serve", "--framework", fw, "--porta", str(porta))):
            enderecos()

    def primeiro_plano():
        if garantir_dependencias_web(c["web_framework"]):
            servir(c["web_framework"], "0.0.0.0", c["web_porta"])

    def escolher_framework():
        opcoes = ["flask  — leve e simples (recomendado)", "fastapi — moderno, com /docs automático",
                  "stdlib — sem dependências (http.server)"]
        i = escolher("Framework", opcoes)
        if i is not None:
            c["web_framework"] = ["flask", "fastapi", "stdlib"][i]
            c["web_porta"] = perguntar_int("Porta", c["web_porta"], 1024, 65535)
            salvar_cfg()
            garantir_dependencias_web(c["web_framework"])
            ok(f"Usando {c['web_framework']} na porta {c['web_porta']}.")

    def enderecos():
        porta = c["web_porta"]
        print(f"\n  Local:      http://127.0.0.1:{porta}")
        print(f"  Rede Wi-Fi: http://{ip_local()}:{porta}")
        if url_tunel() and servico_ativo("tunel"):
            print(f"  Internet:   {url_tunel()}")
        print(f"\n  Token: {NEG}{c['api_token']}{RST}")
        print(f"\n{DIM}Exemplos:{RST}")
        print(f"  curl -H 'Authorization: Bearer {c['api_token']}' http://{ip_local()}:{porta}/api/status")
        print(f"  curl -X POST -H 'Authorization: Bearer {c['api_token']}' -d '{{\"texto\":\"oi\"}}' \\\n"
              f"       http://{ip_local()}:{porta}/api/notificar")
        print(f"\n{DIM}Rotas:{RST} " + ", ".join(sorted(f"{m} {p}" for m, p in ToonsAPI().rotas)))

    def regenerar():
        if confirmar("Gerar um token novo? (o antigo para de funcionar)"):
            c["api_token"] = secrets.token_urlsafe(24)
            salvar_cfg()
            ok("Novo token gerado. Reinicie o servidor se ele estiver rodando.")

    def iniciar_tunel():
        if not garantir_cmd("cloudflared"):
            return
        if servico_ativo("tunel"):
            aviso("O túnel já está rodando.")
            info(f"URL: {url_tunel()}")
            return
        if not servico_ativo("web"):
            aviso("O servidor web não está rodando; o túnel vai apontar para a porta mesmo assim.")
        log_de("tunel").unlink(missing_ok=True)  # para encontrar a URL nova no log
        aviso("Com o túnel, a API fica acessível pela internet: guarde bem o token!")
        if not iniciar_servico("tunel", f"cloudflared tunnel --no-autoupdate --url http://localhost:{c['web_porta']}"):
            return
        info("Aguardando a URL pública...")
        for _ in range(30):
            url = url_tunel()
            if url:
                ok(f"Acesse de qualquer lugar: {NEG}{url}{RST}")
                return
            time.sleep(1)
        aviso("A URL ainda não apareceu; veja o log do túnel em alguns segundos.")

    menu("🌐 Servidor web / API pessoal", [
        *itens_servico("web", "Servidor", iniciar),
        ("Rodar em primeiro plano (Ctrl+C para parar)", primeiro_plano),
        ("Endereços, token e exemplos de uso", enderecos),
        (lambda: f"Escolher framework/porta (atual: {c['web_framework']}:{c['web_porta']})", escolher_framework),
        ("Gerar novo token da API", regenerar),
        ("Cloudflare Tunnel: expor na internet", iniciar_tunel),
        ("Cloudflare Tunnel: parar", lambda: parar_servico("tunel")),
        ("Cloudflare Tunnel: mostrar URL", lambda: info(url_tunel() or "Nenhuma URL encontrada.")),
    ])


# ════════════════════════════════════════════════════════════════════
#  2. Bots de Telegram e Discord (24h com tmux + wake-lock)
# ════════════════════════════════════════════════════════════════════

AJUDA_BOT = """🤖 Termux-Toons — comandos
{p}status – resumo do celular
{p}bateria – nível da bateria
{p}ip – IP local e público
{p}local – localização atual
{p}foto [0|1] – foto (0 traseira, 1 frontal)
{p}falar <texto> – fala em voz alta (TTS)
{p}notificar <texto> – mostra notificação
{p}vibrar [ms] – vibra o celular
{p}lanterna on|off – liga/desliga a lanterna
{p}sms <número> <texto> – envia SMS
{p}ia <pergunta> – pergunta ao LLM local
{p}servicos – serviços ativos
{p}sh <comando> – executa no shell (se habilitado)"""


class BotCore:
    """Comandos compartilhados pelos bots. Cada resposta é um dict:
    {"texto": str} | {"foto": caminho} | {"local": (lat, lon)}"""

    def __init__(self, prefixo: str = "/"):
        self.p = prefixo

    def tratar(self, texto: str) -> list:
        texto = (texto or "").strip()
        if not texto.startswith(self.p):
            return []
        cmd, _, arg = texto[len(self.p):].partition(" ")
        cmd = cmd.split("@")[0].lower()  # /status@MeuBot -> status
        func = getattr(self, f"c_{cmd}", None)
        if func is None:
            return [{"texto": f"Comando desconhecido. Use {self.p}ajuda"}]
        try:
            resp = func(arg.strip())
        except ToonsError as e:
            return [{"texto": f"⚠️ {e}"}]
        except Exception as e:  # noqa: BLE001
            return [{"texto": f"💥 Erro: {e!r}"}]
        return resp if isinstance(resp, list) else [resp]

    def c_start(self, _):
        return {"texto": AJUDA_BOT.format(p=self.p)}

    c_ajuda = c_help = c_start

    def c_status(self, _):
        return {"texto": formatar_status(status_sistema())}

    def c_bateria(self, _):
        b = bateria()
        return {"texto": f"🔋 {b.get('percentage')}% – {b.get('status')} – {b.get('temperature')}°C"}

    def c_ip(self, _):
        return {"texto": f"🏠 Local: {ip_local()}\n🌍 Público: {ip_publico()}"}

    def c_local(self, _):
        loc = localizacao()
        lat, lon = loc["latitude"], loc["longitude"]
        return [{"local": (lat, lon)},
                {"texto": f"📍 Precisão ~{loc.get('accuracy', '?')} m\nhttps://maps.google.com/?q={lat},{lon}"}]

    def c_foto(self, arg):
        return {"foto": str(foto(camera=int(arg) if arg.isdigit() else 0))}

    def c_falar(self, arg):
        if not arg:
            return {"texto": f"Uso: {self.p}falar <texto>"}
        falar(arg)
        return {"texto": "🗣️ Falado!"}

    def c_notificar(self, arg):
        if not arg:
            return {"texto": f"Uso: {self.p}notificar <texto>"}
        notificar("Termux-Toons bot", arg, som=True)
        return {"texto": "🔔 Notificação enviada."}

    def c_vibrar(self, arg):
        vibrar(int(arg) if arg.isdigit() else 500)
        return {"texto": "📳 Vibrando."}

    def c_lanterna(self, arg):
        ligar = arg.lower() not in ("off", "desligar", "0", "nao", "não")
        lanterna(ligar)
        return {"texto": "🔦 Lanterna " + ("ligada" if ligar else "desligada")}

    def c_sms(self, arg):
        numero, _, msg = arg.partition(" ")
        if not numero or not msg.strip():
            return {"texto": f"Uso: {self.p}sms <número> <texto>"}
        sms_enviar(numero, msg.strip())
        return {"texto": f"✉️ SMS enviado para {numero}."}

    def c_ia(self, arg):
        if not arg:
            return {"texto": f"Uso: {self.p}ia <pergunta>"}
        return {"texto": ia_perguntar(arg)}

    def c_servicos(self, _):
        return {"texto": "⚙️ Ativos: " + (", ".join(servicos_ativos()) or "nenhum")}

    def c_sh(self, arg):
        if not cfg().get("bot_permitir_shell"):
            return {"texto": "⛔ Comando sh desabilitado. Ative em Configurações do Termux-Toons."}
        if not arg:
            return {"texto": f"Uso: {self.p}sh <comando>"}
        try:
            proc = subprocess.run(arg, shell=True, executable=SHELL_BIN, capture_output=True,
                                  text=True, errors="replace", timeout=120, cwd=HOME)
            texto = (proc.stdout + proc.stderr).strip() or "(sem saída)"
            codigo = proc.returncode
        except subprocess.TimeoutExpired:
            texto, codigo = "(tempo esgotado: 120s)", 124
        return {"texto": f"$ {arg}\n{texto[-3500:]}\n[código {codigo}]"}


def _multipart(campos: dict, arquivos: dict) -> tuple:
    """Monta um corpo multipart/form-data só com a biblioteca padrão."""
    fronteira = uuid.uuid4().hex
    partes = []
    for nome, valor in campos.items():
        partes.append(f'--{fronteira}\r\nContent-Disposition: form-data; name="{nome}"\r\n\r\n'
                      f'{valor}\r\n'.encode())
    for nome, caminho in arquivos.items():
        caminho = Path(caminho)
        partes.append(f'--{fronteira}\r\nContent-Disposition: form-data; name="{nome}"; '
                      f'filename="{caminho.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
                      + caminho.read_bytes() + b"\r\n")
    partes.append(f"--{fronteira}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={fronteira}"


def tg_chamar(token: str, metodo: str, dados: dict | None = None, arquivos: dict | None = None,
              timeout: float = 30):
    """Chama a Bot API do Telegram e devolve o campo 'result'."""
    if arquivos:
        corpo, tipo = _multipart(dados or {}, arquivos)
    else:
        corpo, tipo = json.dumps(dados or {}).encode(), "application/json"
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{metodo}", data=corpo,
                                 headers={"Content-Type": tipo})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            resp = json.loads(e.read().decode())
        except (ValueError, OSError):
            resp = {"ok": False, "description": f"HTTP {e.code}"}
    if not resp.get("ok"):
        raise ToonsError(f"Telegram: {resp.get('description', 'erro desconhecido')}")
    return resp["result"]


def tg_enviar_texto(token: str, chat_id, texto: str) -> None:
    for parte in fatiar(texto, 4000):
        tg_chamar(token, "sendMessage", {"chat_id": chat_id, "text": parte})


class TelegramBot:
    def __init__(self, token: str, permitidos: list):
        self.token = token
        self.permitidos = {str(i).strip() for i in permitidos if str(i).strip()}
        self.core = BotCore("/")
        self.offset = 0

    def enviar(self, chat_id, resposta: dict) -> None:
        if "texto" in resposta:
            tg_enviar_texto(self.token, chat_id, resposta["texto"])
        elif "foto" in resposta:
            try:
                tg_chamar(self.token, "sendPhoto", {"chat_id": str(chat_id)},
                          {"photo": resposta["foto"]}, timeout=120)
            finally:
                Path(resposta["foto"]).unlink(missing_ok=True)
        elif "local" in resposta:
            lat, lon = resposta["local"]
            tg_chamar(self.token, "sendLocation", {"chat_id": chat_id, "latitude": lat, "longitude": lon})

    def responder(self, chat_id, texto: str) -> None:
        comando = texto.split()[0].split("@")[0].lower() if texto.split() else ""
        if comando in ("/foto", "/local", "/ia"):
            try:
                tg_chamar(self.token, "sendChatAction", {"chat_id": chat_id, "action": "typing"})
            except (ToonsError, OSError):
                pass
        for resposta in self.core.tratar(texto):
            try:
                self.enviar(chat_id, resposta)
            except (ToonsError, OSError) as e:
                log(f"Falha ao responder {chat_id}: {e}")

    def rodar(self) -> None:
        eu = tg_chamar(self.token, "getMe", timeout=20)
        log(f"Bot @{eu.get('username')} conectado. Aguardando mensagens...")
        if not self.permitidos:
            log("ATENÇÃO: nenhum ID permitido. Mande /start ao bot, pegue seu chat_id na "
                "resposta e cadastre em Configurações.")
        espera = 1
        while True:
            try:
                updates = tg_chamar(self.token, "getUpdates", {
                    "timeout": 50, "offset": self.offset, "allowed_updates": ["message"]}, timeout=70)
                espera = 1
            except (ToonsError, OSError, ValueError) as e:
                log(f"Falha de rede/API: {e}. Nova tentativa em {espera}s.")
                time.sleep(espera)
                espera = min(espera * 2, 60)
                continue
            for upd in updates:
                self.offset = upd["update_id"] + 1
                msg = upd.get("message") or {}
                texto = msg.get("text")
                chat_id = (msg.get("chat") or {}).get("id")
                user_id = (msg.get("from") or {}).get("id")
                if not texto or chat_id is None:
                    continue
                if str(chat_id) not in self.permitidos and str(user_id) not in self.permitidos:
                    log(f"Bloqueado: chat_id={chat_id} user_id={user_id} texto={texto[:40]!r}")
                    try:
                        tg_enviar_texto(self.token, chat_id, f"⛔ Não autorizado.\nSeu chat_id é {chat_id}.\n"
                                        "Cadastre-o no Termux-Toons → Configurações.")
                    except (ToonsError, OSError):
                        pass
                    continue
                log(f"{chat_id}: {texto}")
                threading.Thread(target=self.responder, args=(chat_id, texto), daemon=True).start()


def rodar_discord(token: str, permitidos: list) -> None:
    import asyncio

    import discord

    intents = discord.Intents.default()
    intents.message_content = True
    cliente = discord.Client(intents=intents)
    core = BotCore("!")
    ids = {str(i).strip() for i in permitidos if str(i).strip()}

    @cliente.event
    async def on_ready():
        log(f"Discord conectado como {cliente.user}. Use !ajuda")
        if not ids:
            log("ATENÇÃO: nenhum ID permitido; cadastre seu ID de usuário em Configurações.")

    @cliente.event
    async def on_message(msg):
        if msg.author.bot or not msg.content.startswith("!"):
            return
        if str(msg.author.id) not in ids:
            log(f"Bloqueado: user_id={msg.author.id}")
            await msg.channel.send(f"⛔ Não autorizado. Seu ID é {msg.author.id}.")
            return
        log(f"{msg.author}: {msg.content}")
        async with msg.channel.typing():
            respostas = await asyncio.to_thread(core.tratar, msg.content)
        for r in respostas:
            if "texto" in r:
                for parte in fatiar(r["texto"], 1900):
                    await msg.channel.send(parte)
            elif "foto" in r:
                try:
                    await msg.channel.send(file=discord.File(r["foto"]))
                finally:
                    Path(r["foto"]).unlink(missing_ok=True)
            elif "local" in r:
                lat, lon = r["local"]
                await msg.channel.send(f"📍 https://maps.google.com/?q={lat},{lon}")

    cliente.run(token)


def executar_bot(tipo: str) -> None:
    c = cfg()
    if tipo == "telegram":
        if not c["telegram_token"]:
            raise ToonsError("Token do Telegram não configurado.")
        TelegramBot(c["telegram_token"], c["telegram_ids_permitidos"]).rodar()
    else:
        if not c["discord_token"]:
            raise ToonsError("Token do Discord não configurado.")
        if not modulo_existe("discord"):
            raise ToonsError("Módulo discord.py não instalado (pip install discord.py).")
        rodar_discord(c["discord_token"], c["discord_ids_permitidos"])


def _ler_ids(texto: str) -> list:
    return [p for p in re.split(r"[\s,;]+", texto) if p.lstrip("-").isdigit()]


@submenu
def menu_bots():
    c = cfg()

    def configurar_telegram():
        info("Crie o bot com o @BotFather no Telegram (/newbot) e cole o token aqui.")
        token = perguntar("Token do bot", c["telegram_token"])
        if token:
            try:
                eu = tg_chamar(token, "getMe", timeout=15)
                ok(f"Token válido: @{eu.get('username')}")
            except (ToonsError, OSError) as e:
                aviso(f"Não consegui validar o token agora ({e}). Salvando mesmo assim.")
            c["telegram_token"] = token
        atuais = ",".join(map(str, c["telegram_ids_permitidos"]))
        ids = perguntar("chat_ids permitidos (separados por vírgula)", atuais)
        c["telegram_ids_permitidos"] = _ler_ids(ids)
        salvar_cfg()
        ok("Configuração do Telegram salva.")

    def descobrir_chat_id():
        if not c["telegram_token"]:
            raise ToonsError("Configure o token primeiro.")
        if servico_ativo("bot-telegram"):
            info("O bot está rodando: mande /start para ele e veja o chat_id na resposta.")
            return
        info("Mande qualquer mensagem para o seu bot agora. Aguardando até 30s...")
        updates = tg_chamar(c["telegram_token"], "getUpdates", {"timeout": 30}, timeout=40)
        vistos = {}
        for u in updates:
            m = u.get("message") or {}
            if m.get("chat"):
                vistos[m["chat"]["id"]] = m["chat"].get("username") or m["chat"].get("title") or ""
        if not vistos:
            aviso("Nenhuma mensagem recebida.")
            return
        for cid, nome in vistos.items():
            print(f"  chat_id: {NEG}{cid}{RST}  {nome}")
        if confirmar("Adicionar esses IDs à lista de permitidos?", True):
            for cid in vistos:
                if str(cid) not in map(str, c["telegram_ids_permitidos"]):
                    c["telegram_ids_permitidos"].append(str(cid))
            salvar_cfg()
            ok("IDs adicionados.")

    def iniciar_telegram():
        if not c["telegram_token"]:
            raise ToonsError("Configure o token do Telegram primeiro.")
        if iniciar_servico("bot-telegram", cmd_self("bot", "telegram"), reiniciar=True):
            info("Dica: desative a otimização de bateria do Termux no Android para ficar 24h no ar.")

    def configurar_discord():
        info("Crie o app em https://discord.com/developers → Bot → Reset Token. Ative "
             "'Message Content Intent' e convide o bot para o seu servidor.")
        token = perguntar("Token do bot", mascarar(c["discord_token"]) if c["discord_token"] else "")
        if token and "…" not in token and token != "****":
            c["discord_token"] = token
        ids = perguntar("IDs de usuário permitidos (vírgula)", ",".join(map(str, c["discord_ids_permitidos"])))
        c["discord_ids_permitidos"] = _ler_ids(ids)
        salvar_cfg()
        ok("Configuração do Discord salva.")
        garantir_modulo("discord", "discord.py",
                        aviso_extra="O discord.py depende do aiohttp; se a compilação falhar, rode "
                                    "'pkg install clang' e tente de novo.")

    def iniciar_discord():
        if not c["discord_token"]:
            raise ToonsError("Configure o token do Discord primeiro.")
        if not garantir_modulo("discord", "discord.py"):
            return
        iniciar_servico("bot-discord", cmd_self("bot", "discord"), reiniciar=True)

    menu("🤖 Bots Telegram / Discord (24h)", [
        ("Telegram: configurar token e IDs permitidos", configurar_telegram),
        ("Telegram: descobrir meu chat_id", descobrir_chat_id),
        *itens_servico("bot-telegram", "Telegram", iniciar_telegram),
        ("Telegram: rodar em primeiro plano (teste)", lambda: executar_bot("telegram")),
        ("Discord: configurar token e IDs permitidos", configurar_discord),
        *itens_servico("bot-discord", "Discord", iniciar_discord),
        ("Ver comandos disponíveis", lambda: print(AJUDA_BOT.format(p="/ ou !"))),
    ])


# ════════════════════════════════════════════════════════════════════
#  3. Automação com Termux:API
# ════════════════════════════════════════════════════════════════════

@submenu
def menu_termux_api():
    def listar_sensores():
        nomes = sensores()
        if not nomes:
            aviso("Nenhum sensor retornado.")
        for nome in nomes:
            print(f"  • {nome}")

    def ler_sensor_menu():
        nomes = sensores()
        if not nomes:
            raise ToonsError("Nenhum sensor encontrado.")
        i = escolher("Qual sensor?", nomes)
        if i is not None:
            mostrar_dados(ler_sensor(nomes[i]))

    def enviar_sms():
        numero = perguntar("Número (ex.: +5511999999999)")
        texto = perguntar("Mensagem")
        if numero and texto and confirmar(f"Enviar SMS para {numero}?", True):
            sms_enviar(numero, texto)
            ok("SMS enviado.")

    def ler_sms():
        for sms in sms_listar(perguntar_int("Quantas mensagens", 10, 1, 200)):
            print(f"{CIANO}{sms.get('received', '')}{RST} {NEG}{sms.get('number', '')}{RST} "
                  f"[{sms.get('type', '')}]\n  {sms.get('body', '')}\n")

    def notificacao():
        notificar(perguntar("Título", "Termux-Toons"), perguntar("Texto", "Olá do Python!"), som=True)
        ok("Notificação enviada.")

    def tts():
        falar(perguntar("Texto para falar", "Olá! Eu sou o Termux Toons."))

    def tirar_foto():
        cam = perguntar_int("Câmera (0 traseira, 1 frontal)", 0, 0, 5)
        destino = (DOWNLOADS if DOWNLOADS.exists() else DATA_DIR) / f"foto_{datetime.now():%Y%m%d_%H%M%S}.jpg"
        ok(f"Foto salva em {foto(destino, cam)}")

    def local():
        prov = ["network", "gps", "passive"][escolher("Provedor", ["rede (rápido)", "GPS (preciso)", "passivo"], 1) or 0]
        info("Obtendo localização (pode demorar com GPS)...")
        loc = localizacao(prov)
        mostrar_dados(loc)
        print(f"\n  🗺️  https://maps.google.com/?q={loc['latitude']},{loc['longitude']}")

    def clipboard():
        atual = _tapi(["termux-clipboard-get"], 10, json_saida=False)
        print(f"Conteúdo atual:\n{atual}\n")
        novo = perguntar("Novo conteúdo (Enter mantém)")
        if novo:
            _tapi(["termux-clipboard-set"], 10, entrada=novo, json_saida=False)
            ok("Copiado.")

    def alerta_bateria():
        limite = perguntar_int("Avisar quando a bateria ficar abaixo de (%)", 20, 1, 99)
        adicionar_monitor_dados({"nome": f"Bateria < {limite}%", "tipo": "bateria", "limite": limite,
                                 "intervalo": 300})
        info("Inicie o serviço de monitoramento no menu 'Scraping e monitoramento'.")

    menu("📱 Automação com Termux:API", [
        ("Status da bateria", lambda: mostrar_dados(bateria())),
        ("Listar sensores", listar_sensores),
        ("Ler um sensor", ler_sensor_menu),
        ("Enviar SMS", enviar_sms),
        ("Ler últimos SMS", ler_sms),
        ("Enviar notificação", notificacao),
        ("Falar texto (TTS)", tts),
        ("Tirar foto", tirar_foto),
        ("Localização atual", local),
        ("Vibrar", lambda: vibrar(perguntar_int("Duração (ms)", 500, 50, 5000))),
        ("Lanterna liga/desliga", lambda: lanterna(confirmar("Ligar a lanterna?", True))),
        ("Área de transferência", clipboard),
        ("Informações do Wi-Fi", lambda: mostrar_dados(_tapi(["termux-wifi-connectioninfo"], 15))),
        ("Volume do sistema", lambda: mostrar_dados(_tapi(["termux-volume"], 15))),
        ("Criar alerta de bateria baixa", alerta_bateria),
        ("Instalar o pacote termux-api", lambda: instalar_pkg("termux-api")),
    ])


# ════════════════════════════════════════════════════════════════════
#  4. LLMs locais com llama.cpp
# ════════════════════════════════════════════════════════════════════

MODELOS = [
    ("Gemma 3 1B Instruct · Q4_K_M · ~0,8 GB",
     "https://huggingface.co/bartowski/google_gemma-3-1b-it-GGUF/resolve/main/google_gemma-3-1b-it-Q4_K_M.gguf"),
    ("Llama 3.2 1B Instruct · Q4_K_M · ~0,8 GB",
     "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"),
    ("Qwen2.5 1.5B Instruct · Q4_K_M · ~1,1 GB",
     "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"),
    ("Qwen3 1.7B · Q4_K_M · ~1,1 GB",
     "https://huggingface.co/bartowski/Qwen_Qwen3-1.7B-GGUF/resolve/main/Qwen_Qwen3-1.7B-Q4_K_M.gguf"),
    ("Gemma 2 2B Instruct · Q4_K_M · ~1,7 GB",
     "https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf"),
    ("Llama 3.2 3B Instruct · Q4_K_M · ~2,0 GB",
     "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"),
    ("Qwen2.5 3B Instruct · Q4_K_M · ~2,1 GB",
     "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"),
]

_SEM_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # para 127.0.0.1


def baixar_arquivo(url: str, destino: Path) -> Path:
    """Download com barra de progresso e retomada (arquivo .part)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_name(destino.name + ".part")
    inicio = parcial.stat().st_size if parcial.exists() else 0
    headers = {"User-Agent": USER_AGENT}
    if inicio:
        headers["Range"] = f"bytes={inicio}-"
        info(f"Retomando download a partir de {bytes_humanos(inicio)}...")
    try:
        resp = urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30)
    except urllib.error.HTTPError as e:
        if e.code == 416 and inicio:  # já estava completo
            parcial.replace(destino)
            return destino
        raise ToonsError(f"HTTP {e.code} ao baixar {url}") from None
    except OSError as e:
        raise ToonsError(f"Falha de rede: {e}") from None
    with resp:
        if inicio and resp.status != 206:
            inicio = 0  # servidor ignorou o Range: recomeça
        tamanho = resp.headers.get("Content-Length")
        total = int(tamanho) + inicio if tamanho else None
        baixado, t0, ultimo = inicio, time.time(), 0.0
        with open(parcial, "ab" if inicio else "wb") as arq:
            while True:
                bloco = resp.read(1 << 16)
                if not bloco:
                    break
                arq.write(bloco)
                baixado += len(bloco)
                agora = time.time()
                if agora - ultimo > 0.5:
                    ultimo = agora
                    vel = (baixado - inicio) / max(agora - t0, 0.001)
                    if total:
                        frac = baixado / total
                        barra = "█" * int(frac * 25) + "░" * (25 - int(frac * 25))
                        print(f"\r  {barra} {frac * 100:5.1f}%  {bytes_humanos(baixado)}/{bytes_humanos(total)}"
                              f"  {bytes_humanos(vel)}/s   ", end="", flush=True)
                    else:
                        print(f"\r  {bytes_humanos(baixado)}  {bytes_humanos(vel)}/s   ", end="", flush=True)
    print()
    if total and baixado < total:
        raise ToonsError("Download incompleto. Rode de novo para continuar de onde parou.")
    parcial.replace(destino)
    return destino


def llama_bin(nome: str) -> str | None:
    compilado = LLAMA_DIR / "build" / "bin" / nome
    if compilado.exists():
        return str(compilado)
    return shutil.which(nome)


def modelos_baixados() -> list:
    return sorted(MODELS_DIR.glob("*.gguf")) if MODELS_DIR.exists() else []


def modelo_atual() -> Path:
    escolhido = cfg().get("llama_modelo")
    if escolhido and Path(escolhido).exists():
        return Path(escolhido)
    baixados = modelos_baixados()
    if not baixados:
        raise ToonsError("Nenhum modelo .gguf em ~/llama-models. Baixe um no menu.")
    return baixados[0]


def ia_perguntar(prompt: str, historico: list | None = None, timeout: float = 300) -> str:
    """Pergunta ao llama-server (API compatível com OpenAI) rodando no celular."""
    if not prompt:
        raise ToonsError("Escreva uma pergunta.")
    porta = cfg()["llama_porta"]
    mensagens = list(historico or []) + [{"role": "user", "content": prompt}]
    req = urllib.request.Request(
        f"http://127.0.0.1:{porta}/v1/chat/completions",
        data=json.dumps({"messages": mensagens, "temperature": 0.7}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with _SEM_PROXY.open(req, timeout=timeout) as r:
            dados = json.loads(r.read().decode())
    except (OSError, ValueError) as e:
        raise ToonsError(f"O llama-server não respondeu em 127.0.0.1:{porta}. Inicie-o no menu "
                         f"'LLMs locais' ({e}).") from None
    try:
        return dados["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        raise ToonsError(f"Resposta inesperada do servidor: {str(dados)[:200]}") from None


@submenu
def menu_llm():
    c = cfg()

    def instalar_deps():
        instalar_pkg("git", "cmake", "clang", "make", "openssl")

    def compilar():
        compilar_llama()

    def baixar_modelo():
        opcoes = [nome for nome, _ in MODELOS] + ["URL personalizada (.gguf)"]
        i = escolher("Modelo", opcoes)
        if i is None:
            return
        if i < len(MODELOS):
            url = MODELOS[i][1]
        else:
            url = perguntar("URL direta do arquivo .gguf")
            if not url:
                return
        nome = urllib.parse.unquote(url.rsplit("/", 1)[-1].split("?")[0]) or "modelo.gguf"
        destino = MODELS_DIR / nome
        if destino.exists():
            ok(f"Já baixado: {destino}")
        else:
            livre = shutil.disk_usage(HOME).free
            info(f"Espaço livre: {bytes_humanos(livre)}. Baixando para {destino}")
            baixar_arquivo(url, destino)
            ok("Download concluído.")
        c["llama_modelo"] = str(destino)
        salvar_cfg()

    def escolher_modelo():
        baixados = modelos_baixados()
        if not baixados:
            raise ToonsError("Nenhum modelo baixado ainda.")
        i = escolher("Modelo padrão", [f"{m.name} ({bytes_humanos(m.stat().st_size)})" for m in baixados])
        if i is not None:
            c["llama_modelo"] = str(baixados[i])
            salvar_cfg()
            ok(f"Modelo padrão: {baixados[i].name}")

    def conversar():
        binario = llama_bin("llama-cli")
        if not binario:
            raise ToonsError("llama-cli não encontrado. Compile o llama.cpp ou instale 'llama-cpp'.")
        modelo = modelo_atual()
        info(f"Modelo: {modelo.name} — digite /exit ou Ctrl+C para sair.")
        extra = shlex.split(perguntar("Argumentos extras (opcional)", ""))
        rodar([binario, "-m", modelo, "-t", c["llama_threads"], "-c", c["llama_contexto"], *extra])

    def iniciar_servidor():
        binario = llama_bin("llama-server")
        if not binario:
            raise ToonsError("llama-server não encontrado. Compile o llama.cpp primeiro.")
        modelo = modelo_atual()
        host = "0.0.0.0" if confirmar("Deixar acessível na rede Wi-Fi? (sem senha!)", False) else "127.0.0.1"
        porta = c["llama_porta"]
        comando = shlex.join([binario, "-m", str(modelo), "--host", host, "--port", str(porta),
                              "-t", str(c["llama_threads"]), "-c", str(c["llama_contexto"])])
        if iniciar_servico("llama", comando):
            info(f"Interface web e API OpenAI: http://{ip_local() if host == '0.0.0.0' else '127.0.0.1'}:{porta}")
            info("O modelo leva alguns segundos para carregar. Depois use o chat abaixo ou /ia no bot.")

    def chat_api():
        historico = [{"role": "system", "content": "Você é um assistente útil. Responda em português."}]
        info("Chat com o llama-server. Comandos: /limpar, /sair")
        while True:
            try:
                pergunta = input(f"{VERD}Você:{RST} ").strip()
            except EOFError:
                break
            if pergunta in ("/sair", "/exit", "/quit"):
                break
            if pergunta == "/limpar":
                del historico[1:]
                ok("Histórico limpo.")
                continue
            if not pergunta:
                continue
            t0 = time.time()
            resposta = ia_perguntar(pergunta, historico)
            historico += [{"role": "user", "content": pergunta}, {"role": "assistant", "content": resposta}]
            print(f"{MAG}IA:{RST} {resposta}\n{DIM}({time.time() - t0:.1f}s){RST}\n")

    def ajustes():
        nucleos = os.cpu_count() or 4
        c["llama_threads"] = perguntar_int(f"Threads (o aparelho tem {nucleos} núcleos)", c["llama_threads"], 1, 64)
        c["llama_contexto"] = perguntar_int("Tamanho do contexto (tokens)", c["llama_contexto"], 256, 131072)
        c["llama_porta"] = perguntar_int("Porta do llama-server", c["llama_porta"], 1024, 65535)
        salvar_cfg()
        ok("Ajustes salvos.")

    def remover_modelo():
        baixados = modelos_baixados()
        if not baixados:
            info("Nenhum modelo baixado.")
            return
        i = escolher("Remover qual?", [f"{m.name} ({bytes_humanos(m.stat().st_size)})" for m in baixados])
        if i is not None and confirmar(f"Apagar {baixados[i].name}?"):
            baixados[i].unlink()
            ok("Removido.")

    menu("🧠 LLMs locais (llama.cpp)", [
        ("Instalar dependências de compilação (git, cmake, clang)", instalar_deps),
        ("Baixar/atualizar e COMPILAR o llama.cpp no celular", compilar),
        ("Alternativa rápida: instalar llama.cpp pronto (pkg llama-cpp)", lambda: instalar_pkg("llama-cpp")),
        ("Baixar modelo (1B a 3B)", baixar_modelo),
        ("Escolher modelo padrão", escolher_modelo),
        ("Conversar no terminal (llama-cli)", conversar),
        *itens_servico("llama", "llama-server (web + API)", iniciar_servidor),
        ("Chat pelo servidor (com histórico)", chat_api),
        ("Ajustar threads, contexto e porta", ajustes),
        ("Remover modelo baixado", remover_modelo),
    ])


def compilar_llama() -> None:
    for cmd, pacote in (("git", "git"), ("cmake", "cmake"), ("clang", "clang"), ("make", "make")):
        if not garantir_cmd(cmd, pacote):
            raise ToonsError(f"'{cmd}' é necessário para compilar.")
    if (LLAMA_DIR / ".git").exists():
        info("Atualizando o código do llama.cpp...")
        rodar(["git", "-C", LLAMA_DIR, "pull", "--ff-only"])
    else:
        rodar(["git", "clone", "--depth", "1", "https://github.com/ggml-org/llama.cpp", LLAMA_DIR], check=True)
    build = LLAMA_DIR / "build"
    configurar = ["cmake", "-S", LLAMA_DIR, "-B", build, "-DCMAKE_BUILD_TYPE=Release"]
    if rodar(configurar).returncode != 0:
        # Versões novas usam OpenSSL e as antigas libcurl só para baixar modelos: dá para desligar.
        aviso("Configuração falhou; tentando de novo sem suporte a HTTPS embutido...")
        rodar(configurar + ["-DLLAMA_OPENSSL=OFF", "-DLLAMA_CURL=OFF"], check=True)
    nucleos = os.cpu_count() or 4
    jobs = perguntar_int("Compilar com quantos processos paralelos? (menos = menos RAM)", min(4, nucleos), 1, nucleos)
    info("Compilando... isso pode levar de 10 a 30 minutos. Deixe a tela ligada.")
    t0 = time.time()
    rodar(["cmake", "--build", build, "--config", "Release", "-j", str(jobs),
           "--target", "llama-cli", "llama-server"], check=True)
    ok(f"Compilado em {(time.time() - t0) / 60:.1f} min: {build / 'bin'}")


# ════════════════════════════════════════════════════════════════════
#  5. Interfaces TUI: dashboard (rich) e gerenciador de tarefas (curses)
# ════════════════════════════════════════════════════════════════════

def _barra(frac: float, largura: int = 20) -> str:
    frac = max(0.0, min(1.0, frac))
    cheio = round(frac * largura)
    return "█" * cheio + "░" * (largura - cheio)


class _AmostradorCPU:
    """Uso de CPU via /proc/stat (o Android 8+ costuma bloquear; aí devolve None)."""

    def __init__(self):
        self.anterior = self._ler()

    @staticmethod
    def _ler():
        try:
            campos = [int(x) for x in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
        except (OSError, ValueError, IndexError):
            return None
        return sum(campos), campos[3] + (campos[4] if len(campos) > 4 else 0)

    def uso(self):
        atual = self._ler()
        if atual is None or self.anterior is None:
            return None
        total, ocioso = atual[0] - self.anterior[0], atual[1] - self.anterior[1]
        self.anterior = atual
        return None if total <= 0 else 1 - ocioso / total


class _CacheBateria(threading.Thread):
    """termux-battery-status demora ~1s: lê em segundo plano a cada 20s."""

    def __init__(self):
        super().__init__(daemon=True)
        self.valor = None

    def run(self):
        while True:
            try:
                self.valor = bateria()
            except ToonsError:
                self.valor = None
            time.sleep(20)


def _linhas_dashboard(cpu: _AmostradorCPU, bat: _CacheBateria, fixo: dict) -> list:
    """Linhas (rótulo, valor, fração ou None) — usadas pelas versões rich e texto."""
    total, disp = memoria()
    disco = shutil.disk_usage(HOME)
    linhas = [
        ("Aparelho", fixo["aparelho"], None),
        ("Android", fixo["android"], None),
        ("Hora", datetime.now().strftime("%d/%m/%Y %H:%M:%S"), None),
        ("Ligado há", tempo_ligado(), None),
        ("IP local", fixo["ip"], None),
    ]
    uso_cpu = cpu.uso()
    if uso_cpu is not None:
        linhas.append(("CPU", f"{uso_cpu * 100:.0f}%", uso_cpu))
    carga = carga_media()
    if carga:
        linhas.append(("Carga", " ".join(map(str, carga)), None))
    if total:
        linhas.append(("RAM", f"{bytes_humanos(total - disp)} / {bytes_humanos(total)}", 1 - disp / total))
    linhas.append(("Disco", f"{bytes_humanos(disco.used)} / {bytes_humanos(disco.total)}", disco.used / disco.total))
    b = bat.valor
    if b:
        pct = b.get("percentage", 0)
        linhas.append(("Bateria", f"{pct}% {b.get('status', '')} {b.get('temperature', '')}°C", pct / 100))
    linhas.append(("Serviços", ", ".join(servicos_ativos()) or "nenhum", None))
    return linhas


def dashboard() -> None:
    cpu, bat = _AmostradorCPU(), _CacheBateria()
    bat.start()
    fixo = {"aparelho": getprop("ro.product.model") or platform.node(),
            "android": getprop("ro.build.version.release") or platform.release(), "ip": ip_local()}
    if modulo_existe("rich") or garantir_modulo("rich"):
        _dashboard_rich(cpu, bat, fixo)
    else:
        _dashboard_texto(cpu, bat, fixo)


def _dashboard_rich(cpu, bat, fixo) -> None:
    from rich.console import Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    def render():
        tabela = Table.grid(padding=(0, 1))
        tabela.add_column(style="bold cyan", no_wrap=True)
        tabela.add_column()
        for rotulo, valor, frac in _linhas_dashboard(cpu, bat, fixo):
            if frac is None:
                tabela.add_row(rotulo, valor)
            else:
                cor = "green" if frac < 0.6 else "yellow" if frac < 0.85 else "red"
                if rotulo == "Bateria":
                    cor = "red" if frac < 0.2 else "yellow" if frac < 0.5 else "green"
                celula = Text(_barra(frac, 16), style=cor)
                celula.append(f" {valor}", style="default")
                tabela.add_row(rotulo, celula)
        return Panel(Group(tabela, Text("\nCtrl+C para sair", style="dim")),
                     title="📊 Termux-Toons Dashboard", border_style="cyan")

    try:
        with Live(render(), refresh_per_second=2, screen=True) as live:
            while True:
                time.sleep(1)
                live.update(render())
    except KeyboardInterrupt:
        pass


def _dashboard_texto(cpu, bat, fixo) -> None:
    try:
        while True:
            limpar()
            titulo("📊 Dashboard (Ctrl+C para sair)")
            for rotulo, valor, frac in _linhas_dashboard(cpu, bat, fixo):
                barra = f"{_barra(frac, 16)} " if frac is not None else ""
                print(f"  {CIANO}{rotulo:<10}{RST} {barra}{valor}")
            time.sleep(2)
    except KeyboardInterrupt:
        pass


def _curses_ler(tela, prompt: str, inicial: str = ""):
    """Lê uma linha no rodapé (aceita acentos). Esc cancela."""
    import curses
    curses.curs_set(1)
    texto = list(inicial)
    while True:
        alt, larg = tela.getmaxyx()
        linha = prompt + "".join(texto)
        tela.move(alt - 1, 0)
        tela.clrtoeol()
        tela.addnstr(alt - 1, 0, linha[-(larg - 1):], larg - 1)
        tela.refresh()
        ch = tela.get_wch()
        if ch in ("\n", "\r", curses.KEY_ENTER):
            break
        if ch == "\x1b":
            texto = None
            break
        if ch in (curses.KEY_BACKSPACE, "\x7f", "\b", 127):
            if texto:
                texto.pop()
        elif isinstance(ch, str) and ch.isprintable():
            texto.append(ch)
    curses.curs_set(0)
    return None if texto is None else "".join(texto).strip()


def tarefas_tui() -> None:
    import curses
    os.environ.setdefault("ESCDELAY", "25")
    tarefas = ler_json(TASKS_FILE, [])

    def salvar():
        gravar_json(TASKS_FILE, tarefas)

    def app(tela):
        curses.curs_set(0)
        try:
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_GREEN, -1)
            curses.init_pair(2, curses.COLOR_CYAN, -1)
            curses.init_pair(3, curses.COLOR_YELLOW, -1)
        except curses.error:
            pass
        sel, topo = 0, 0
        while True:
            tela.erase()
            alt, larg = tela.getmaxyx()
            ajuda = " a:nova e:editar espaço:feita p:prio d:apagar q:sair "
            tela.addnstr(0, 0, ajuda.ljust(larg - 1), larg - 1, curses.A_REVERSE)
            area = max(1, alt - 3)
            sel = max(0, min(sel, len(tarefas) - 1))
            if sel < topo:
                topo = sel
            elif sel >= topo + area:
                topo = sel - area + 1
            if not tarefas:
                tela.addnstr(2, 2, "Nenhuma tarefa. Aperte 'a' para adicionar.", larg - 3)
            for i, t in enumerate(tarefas[topo:topo + area]):
                idx = topo + i
                marca = "[x]" if t.get("feita") else "[ ]"
                prio = "!" if t.get("prioridade") else " "
                texto = f" {marca} {prio} {t['texto']}"
                atributo = curses.A_REVERSE if idx == sel else 0
                if t.get("feita"):
                    atributo |= curses.color_pair(1) | curses.A_DIM
                elif t.get("prioridade"):
                    atributo |= curses.color_pair(3) | curses.A_BOLD
                tela.addnstr(1 + i, 0, texto.ljust(larg - 1), larg - 1, atributo)
            pendentes = sum(1 for t in tarefas if not t.get("feita"))
            rodape = f" {pendentes} pendente(s) de {len(tarefas)} "
            tela.addnstr(alt - 1, 0, rodape, larg - 1, curses.color_pair(2))
            tela.refresh()

            ch = tela.get_wch()
            if ch in ("q", "Q", "\x1b"):
                return
            if ch in (curses.KEY_UP, "k"):
                sel -= 1
            elif ch in (curses.KEY_DOWN, "j"):
                sel += 1
            elif ch == "a":
                texto = _curses_ler(tela, "Nova tarefa: ")
                if texto:
                    tarefas.append({"texto": texto, "feita": False, "prioridade": False,
                                    "criada": datetime.now().isoformat(timespec="minutes")})
                    sel = len(tarefas) - 1
                    salvar()
            elif tarefas and ch == "e":
                texto = _curses_ler(tela, "Editar: ", tarefas[sel]["texto"])
                if texto:
                    tarefas[sel]["texto"] = texto
                    salvar()
            elif tarefas and ch in (" ", "\n", "\r", curses.KEY_ENTER):
                tarefas[sel]["feita"] = not tarefas[sel].get("feita")
                salvar()
            elif tarefas and ch == "p":
                tarefas[sel]["prioridade"] = not tarefas[sel].get("prioridade")
                salvar()
            elif tarefas and ch == "d":
                if _curses_ler(tela, f"Apagar '{tarefas[sel]['texto'][:30]}'? (s/n) ") in ("s", "S", "sim"):
                    tarefas.pop(sel)
                    salvar()

    curses.wrapper(app)


@submenu
def menu_tui():
    def instalar_textual():
        if garantir_modulo("textual"):
            info("Teste com: python -m textual  (demonstração oficial do Textual)")

    menu("📊 Interfaces TUI", [
        ("Dashboard do sistema (rich)", dashboard),
        ("Gerenciador de tarefas (curses)", tarefas_tui),
        ("Player de música (yt-dlp + mpv)", menu_musica),
        ("Instalar Textual para criar seus próprios apps TUI", instalar_textual),
    ])


# ════════════════════════════════════════════════════════════════════
#  6. Ambiente de desenvolvimento
# ════════════════════════════════════════════════════════════════════

NVIM_INIT_LUA = r"""-- Gerado pelo Termux-Toons: Neovim com LSP nativo, sem plugins.
vim.g.mapleader = " "
local o = vim.opt
o.number = true
o.relativenumber = true
o.mouse = "a"
o.expandtab = true
o.shiftwidth = 4
o.tabstop = 4
o.smartindent = true
o.termguicolors = true
o.ignorecase = true
o.smartcase = true
o.signcolumn = "yes"
o.updatetime = 300
o.clipboard = "unnamedplus" -- usa termux-clipboard-get/set se o termux-api estiver instalado
o.completeopt = { "menuone", "noselect" }

-- Servidores de linguagem: só são iniciados se o executável existir.
local servidores = {
  python = { nome = "pyright", cmd = { "pyright-langserver", "--stdio" }, raiz = { "pyproject.toml", "setup.py", "requirements.txt", ".git" } },
  c      = { nome = "clangd", cmd = { "clangd" }, raiz = { "compile_commands.json", "CMakeLists.txt", "Makefile", ".git" } },
  cpp    = { nome = "clangd", cmd = { "clangd" }, raiz = { "compile_commands.json", "CMakeLists.txt", "Makefile", ".git" } },
  rust   = { nome = "rust_analyzer", cmd = { "rust-analyzer" }, raiz = { "Cargo.toml", ".git" } },
  go     = { nome = "gopls", cmd = { "gopls" }, raiz = { "go.mod", ".git" } },
  lua    = { nome = "lua_ls", cmd = { "lua-language-server" }, raiz = { ".luarc.json", ".git" } },
  sh     = { nome = "bashls", cmd = { "bash-language-server", "start" }, raiz = { ".git" } },
}

vim.api.nvim_create_autocmd("FileType", {
  callback = function(args)
    local s = servidores[args.match]
    if not s or vim.fn.executable(s.cmd[1]) ~= 1 then return end
    local arquivo = vim.api.nvim_buf_get_name(args.buf)
    local pasta = vim.fs.dirname(arquivo)
    local achado = vim.fs.find(s.raiz, { upward = true, path = pasta })[1]
    vim.lsp.start({ name = s.nome, cmd = s.cmd, root_dir = achado and vim.fs.dirname(achado) or pasta })
  end,
})

vim.api.nvim_create_autocmd("LspAttach", {
  callback = function(args)
    local function map(teclas, func, desc)
      vim.keymap.set("n", teclas, func, { buffer = args.buf, desc = desc })
    end
    map("gd", vim.lsp.buf.definition, "Ir para a definição")
    map("gr", vim.lsp.buf.references, "Referências")
    map("K", vim.lsp.buf.hover, "Documentação")
    map("<leader>rn", vim.lsp.buf.rename, "Renomear símbolo")
    map("<leader>ca", vim.lsp.buf.code_action, "Ações de código")
    map("<leader>f", function() vim.lsp.buf.format({ async = true }) end, "Formatar arquivo")
    map("<leader>e", vim.diagnostic.open_float, "Mostrar diagnóstico")
    -- Neovim 0.11+: autocompletar nativo enquanto digita.
    if vim.lsp.completion and vim.lsp.completion.enable then
      pcall(vim.lsp.completion.enable, true, args.data.client_id, args.buf, { autotrigger = true })
    end
  end,
})

vim.keymap.set("i", "<C-Space>", "<C-x><C-o>", { desc = "Completar (LSP)" })
vim.keymap.set("n", "<leader>w", "<cmd>write<cr>", { desc = "Salvar" })
vim.keymap.set("n", "<leader>q", "<cmd>quit<cr>", { desc = "Sair" })
"""

TESTES_DEV = {
    "C": ("clang", "hello.c", '#include <stdio.h>\nint main(void){ puts("Olá do C!"); return 0; }\n',
          "clang hello.c -o hello_c && ./hello_c"),
    "Rust": ("rustc", "hello.rs", 'fn main() { println!("Olá do Rust!"); }\n',
             "rustc hello.rs -o hello_rs && ./hello_rs"),
    "Go": ("go", "hello.go", 'package main\nimport "fmt"\nfunc main() { fmt.Println("Olá do Go!") }\n',
           "go run hello.go"),
    "Python": ("python", "hello.py", 'print("Olá do Python!")\n', "python hello.py"),
}


@submenu
def menu_dev():
    def instalar_go():
        instalar_pkg("golang")
        if not tem("gopls") and not instalar_pkg("gopls") and tem("go"):
            rodar(["go", "install", "golang.org/x/tools/gopls@latest"])
            info("gopls instalado em ~/go/bin — adicione ao PATH: export PATH=$PATH:~/go/bin")

    def instalar_pyright():
        if garantir_cmd("npm", "nodejs-lts"):
            rodar(["npm", "install", "-g", "pyright", "bash-language-server"])

    def configurar_neovim():
        destino = HOME / ".config" / "nvim" / "init.lua"
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.exists():
            copia = destino.with_name(f"init.lua.bak-{datetime.now():%Y%m%d%H%M%S}")
            destino.replace(copia)
            info(f"Config anterior guardada em {copia}")
        destino.write_text(NVIM_INIT_LUA, "utf-8")
        ok(f"Criado {destino}")
        print("  Atalhos: gd definição · K documentação · gr referências · Espaço+rn renomear\n"
              "           Espaço+ca ações · Espaço+f formatar · Ctrl+Espaço completar")
        faltando = [cmd for cmd in ("pyright-langserver", "clangd", "rust-analyzer", "gopls", "lua-language-server")
                    if not tem(cmd)]
        if faltando:
            aviso("Servidores LSP ainda não instalados: " + ", ".join(faltando))
        if not tem("nvim"):
            garantir_cmd("nvim", "neovim")

    def configurar_git():
        if not garantir_cmd("git"):
            return
        nome = perguntar("Seu nome para os commits", saida(["git", "config", "--global", "user.name"]))
        email = perguntar("Seu e-mail", saida(["git", "config", "--global", "user.email"]))
        if nome:
            rodar(["git", "config", "--global", "user.name", nome])
        if email:
            rodar(["git", "config", "--global", "user.email", email])
        rodar(["git", "config", "--global", "init.defaultBranch", "main"])
        rodar(["git", "config", "--global", "core.editor", "nvim" if tem("nvim") else "nano"])
        chave = HOME / ".ssh" / "id_ed25519"
        if not chave.exists() and confirmar("Gerar chave SSH (para GitHub/GitLab)?", True):
            if garantir_cmd("ssh-keygen", "openssh"):
                chave.parent.mkdir(mode=0o700, exist_ok=True)
                rodar(["ssh-keygen", "-t", "ed25519", "-C", email or "termux", "-f", chave])
        pub = chave.with_suffix(".pub")
        if pub.exists():
            print(f"\nSua chave pública (cole em GitHub → Settings → SSH keys):\n{NEG}{pub.read_text().strip()}{RST}")

    def testar_compiladores():
        pasta = DATA_DIR / "teste_dev"
        pasta.mkdir(parents=True, exist_ok=True)
        for linguagem, (cmd, arquivo, codigo, comando) in TESTES_DEV.items():
            if not tem(cmd):
                aviso(f"{linguagem}: '{cmd}' não instalado.")
                continue
            (pasta / arquivo).write_text(codigo, "utf-8")
            proc = rodar(comando, cwd=pasta, capturar=True, timeout=300)
            if proc.returncode == 0:
                ok(f"{linguagem}: {proc.stdout.strip()}")
            else:
                erro(f"{linguagem}: falhou\n{proc.stderr.strip()[-400:]}")

    def instalar_code_server():
        info("O code-server vem do repositório TUR (Termux User Repository).")
        instalar_de_repo("tur-repo", "code-server")

    def iniciar_code_server():
        if not garantir_cmd("code-server", repo="tur-repo"):
            return
        if iniciar_servico("code-server", "code-server --bind-addr 0.0.0.0:8081"):
            info(f"Abra no navegador: http://127.0.0.1:8081  (ou http://{ip_local()}:8081 na rede)")
            time.sleep(2)
            senha_code_server()

    def senha_code_server():
        arq = HOME / ".config" / "code-server" / "config.yaml"
        if not arq.exists():
            info("O arquivo de senha é criado na primeira execução do code-server.")
            return
        achado = re.search(r"^password:\s*(.+)$", arq.read_text(), re.M)
        print(f"Senha: {NEG}{achado.group(1) if achado else '(não encontrada)'}{RST}  (em {arq})")

    menu("💻 Ambiente de desenvolvimento", [
        ("Ferramentas base (git, neovim, tmux, ripgrep, fd, curl, openssh)",
         lambda: instalar_pkg("git", "neovim", "tmux", "ripgrep", "fd", "curl", "wget", "openssh", "nano")),
        ("C/C++: clang, cmake, make, gdb (inclui clangd)", lambda: instalar_pkg("clang", "cmake", "make", "gdb")),
        ("Rust: rust + rust-analyzer", lambda: instalar_pkg("rust", "rust-analyzer")),
        ("Go: golang + gopls", instalar_go),
        ("Python/Bash LSP: pyright e bash-language-server (via Node.js)", instalar_pyright),
        ("Lua LSP: lua-language-server", lambda: instalar_pkg("lua-language-server")),
        ("Configurar Neovim com LSP (gera init.lua)", configurar_neovim),
        ("Configurar git e chave SSH", configurar_git),
        ("Testar compiladores (C, Rust, Go, Python)", testar_compiladores),
        ("code-server (VS Code no navegador): instalar", instalar_code_server),
        *itens_servico("code-server", "code-server", iniciar_code_server),
        ("code-server: mostrar senha", senha_code_server),
    ])


# ════════════════════════════════════════════════════════════════════
#  7. Scraping e monitoramento
# ════════════════════════════════════════════════════════════════════

TIPOS_MONITOR = {
    "status": "Status de site (caiu / voltou)",
    "texto": "Texto aparece ou some da página",
    "preco": "Preço abaixo de um alvo",
    "mudanca": "Qualquer mudança no conteúdo",
    "rss": "Notícias novas em feed RSS/Atom",
    "bateria": "Bateria abaixo de um limite",
}

REGEX_PRECO = {
    "Preço em reais (R$ 1.234,56)": r"R\$\s*([\d.]+,\d{2})",
    'Dados estruturados ("price": "1234.56")': r'"price"\s*:\s*"?([\d.,]+)',
    "Meta tag product:price:amount": r'product:price:amount"\s+content="([\d.,]+)',
}


def baixar_url(url: str, timeout: float = 25) -> tuple:
    """(status HTTP, bytes, charset). Erros de rede viram exceção (OSError)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(8_000_000), r.headers.get_content_charset() or "utf-8"
    except urllib.error.HTTPError as e:
        return e.code, b"", "utf-8"


def baixar_pagina(url: str, timeout: float = 25) -> tuple:
    status, dados, charset = baixar_url(url, timeout)
    try:
        return status, dados.decode(charset, errors="replace")
    except LookupError:
        return status, dados.decode("utf-8", errors="replace")


def texto_limpo(pagina: str) -> str:
    import html as html_mod
    pagina = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", pagina)
    pagina = re.sub(r"(?s)<[^>]+>", " ", pagina)
    return re.sub(r"\s+", " ", html_mod.unescape(pagina)).strip()


def parse_preco(texto: str):
    """Converte '1.299,90', '1,299.90', '1299.9' ou 'R$ 89' em float."""
    s = re.sub(r"[^\d,.]", "", texto or "")
    if not s:
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        decimais = s.rpartition(",")[2]
        s = s.replace(",", ".") if s.count(",") == 1 and len(decimais) in (1, 2) else s.replace(",", "")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.rpartition(".")[2]) == 3):
        s = s.replace(".", "")  # 1.299 = mil duzentos e noventa e nove
    try:
        return float(s)
    except ValueError:
        return None


def reais(valor: float) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def ler_feed(dados: bytes) -> list:
    """Itens (id, título, link) de um feed RSS ou Atom."""
    try:
        raiz = ET.fromstring(dados)
    except ET.ParseError as e:
        raise ToonsError(f"Feed inválido: {e}") from None

    def filho(el, nome):
        for f in el:
            if f.tag.split("}")[-1] == nome:
                return f
        return None

    itens = []
    for el in raiz.iter():
        if el.tag.split("}")[-1] not in ("item", "entry"):
            continue
        t = filho(el, "title")
        titulo_item = (t.text or "").strip() if t is not None else "(sem título)"
        lk = filho(el, "link")
        link = ""
        if lk is not None:
            link = (lk.text or "").strip() or lk.get("href", "")
        ident = filho(el, "guid")
        if ident is None:
            ident = filho(el, "id")
        chave = (ident.text or "").strip() if ident is not None and ident.text else (link or titulo_item)
        itens.append((chave, titulo_item, link))
    return itens


def checar_monitor(m: dict, est: dict) -> tuple:
    """Executa um monitor. Devolve (texto do alerta ou None, resumo)."""
    tipo, nome = m["tipo"], m["nome"]
    if tipo == "bateria":
        pct = int(bateria().get("percentage", 100))
        baixa = pct <= int(m.get("limite", 20))
        alerta = f"🔋 Bateria em {pct}% (limite {m.get('limite')}%)" if baixa and not est.get("baixa") else None
        est["baixa"] = baixa
        return alerta, f"{pct}%"

    if tipo == "status":
        try:
            codigo, _, _ = baixar_url(m["url"])
            no_ar = 200 <= codigo < 400
        except (OSError, ValueError) as e:
            codigo, no_ar = getattr(e, "reason", e), False
        anterior = est.get("no_ar")
        est["no_ar"] = no_ar
        if anterior is None:
            alerta = None if no_ar else f"🔴 {nome} está FORA DO AR ({codigo})\n{m['url']}"
        elif anterior != no_ar:
            alerta = (f"🟢 {nome} voltou ({codigo})" if no_ar else f"🔴 {nome} caiu ({codigo})") + f"\n{m['url']}"
        else:
            alerta = None
        return alerta, f"{'no ar' if no_ar else 'FORA'} ({codigo})"

    if tipo == "rss":
        codigo, dados, _ = baixar_url(m["url"])
        if codigo >= 400:
            raise ToonsError(f"HTTP {codigo}")
        itens = ler_feed(dados)
        primeira = "vistos" not in est
        vistos = set(est.get("vistos", []))
        novos = [i for i in itens if i[0] not in vistos]
        est["vistos"] = list(dict.fromkeys([i[0] for i in itens] + est.get("vistos", [])))[:500]
        filtro = (m.get("filtro") or "").lower()
        if filtro:
            novos = [i for i in novos if filtro in i[1].lower()]
        if primeira or not novos:
            return None, f"{len(itens)} itens" + (" (primeira leitura)" if primeira else "")
        corpo = "\n".join(f"• {t}\n  {lk}" for _, t, lk in novos[:5])
        return f"📰 {nome}: {len(novos)} novidade(s)\n{corpo}", f"{len(novos)} novos"

    codigo, pagina = baixar_pagina(m["url"])
    if codigo >= 400:
        raise ToonsError(f"HTTP {codigo}")

    if tipo == "texto":
        alvo = m["texto"].lower()
        presente = alvo in texto_limpo(pagina).lower() or alvo in pagina.lower()
        condicao = presente if m.get("modo", "aparecer") == "aparecer" else not presente
        alerta = None
        if condicao and not est.get("disparado"):
            alerta = f"🔎 '{m['texto']}' {'apareceu em' if presente else 'sumiu de'} {nome}\n{m['url']}"
        est["disparado"] = condicao
        return alerta, "presente" if presente else "ausente"

    if tipo == "preco":
        achado = re.search(m["regex"], pagina, re.I | re.S)
        if not achado:
            raise ToonsError("preço não encontrado na página (ajuste a regex)")
        valor = parse_preco(achado.group(1) if achado.groups() else achado.group(0))
        if valor is None:
            raise ToonsError(f"não entendi o preço '{achado.group(0)[:40]}'")
        alvo, anterior = float(m["alvo"]), est.get("preco")
        est["preco"] = valor
        alerta = None
        if valor <= alvo and (anterior is None or anterior > alvo or valor < anterior):
            alerta = f"💰 {nome}: {reais(valor)} (alvo {reais(alvo)})\n{m['url']}"
        elif m.get("avisar_mudanca") and anterior is not None and valor != anterior:
            seta = "📉" if valor < anterior else "📈"
            alerta = f"{seta} {nome}: {reais(anterior)} → {reais(valor)}\n{m['url']}"
        return alerta, reais(valor)

    if tipo == "mudanca":
        assinatura = hashlib.sha256(texto_limpo(pagina).encode()).hexdigest()
        anterior = est.get("hash")
        est["hash"] = assinatura
        alerta = f"🔄 {nome} mudou!\n{m['url']}" if anterior and anterior != assinatura else None
        return alerta, assinatura[:12]

    raise ToonsError(f"tipo de monitor desconhecido: {tipo}")


def disparar_alerta(texto: str, m: dict | None = None) -> None:
    log(f"ALERTA: {texto}")
    c = cfg()
    try:
        nid = str(int(hashlib.md5(m["id"].encode()).hexdigest()[:6], 16)) if m else None
        notificar("Termux-Toons", texto, nid=nid, som=True)
    except ToonsError as e:
        log(f"Notificação falhou: {e}")
    if c.get("alerta_tts"):
        try:
            falar(texto.splitlines()[0])
        except ToonsError as e:
            log(f"TTS falhou: {e}")
    if c.get("alerta_telegram") and c.get("telegram_token"):
        for chat in c.get("telegram_ids_permitidos", []):
            try:
                tg_enviar_texto(c["telegram_token"], chat, texto)
            except (ToonsError, OSError) as e:
                log(f"Telegram falhou para {chat}: {e}")


def rodar_monitores(uma_vez: bool = False) -> None:
    """Laço do serviço de monitoramento (roda dentro do tmux)."""
    estado = ler_json(STATE_FILE, {})
    log("Monitoramento iniciado." if not uma_vez else "Checando todos os monitores uma vez...")
    while True:
        monitores = recarregar_cfg().get("monitores", [])  # pega monitores novos sem reiniciar
        ids = {m["id"] for m in monitores}
        estado = {k: v for k, v in estado.items() if k in ids}
        agora = time.time()
        for m in monitores:
            if not m.get("ativo", True):
                continue
            est = estado.setdefault(m["id"], {})
            if not uma_vez and agora - est.get("ultimo", 0) < int(m.get("intervalo", 300)):
                continue
            est["ultimo"] = agora
            try:
                alerta, resumo = checar_monitor(m, est)
                est.update(resumo=resumo, erro=None, quando=datetime.now().strftime("%d/%m %H:%M"))
                log(f"[{m['nome']}] {resumo}")
                if alerta:
                    disparar_alerta(alerta, m)
            except Exception as e:  # noqa: BLE001 — um monitor com erro não derruba os outros
                est.update(erro=str(e), quando=datetime.now().strftime("%d/%m %H:%M"))
                log(f"[{m['nome']}] erro: {e}")
            gravar_json(STATE_FILE, estado)
        if uma_vez:
            return
        time.sleep(10)


def adicionar_monitor_dados(dados: dict) -> None:
    c = cfg()
    dados.setdefault("id", uuid.uuid4().hex[:8])
    dados.setdefault("ativo", True)
    c["monitores"].append(dados)
    salvar_cfg()
    ok(f"Monitor '{dados['nome']}' adicionado.")


@submenu
def menu_monitor():
    c = cfg()

    def adicionar():
        chaves = list(TIPOS_MONITOR)
        i = escolher("Tipo de monitor", [TIPOS_MONITOR[k] for k in chaves])
        if i is None:
            return
        tipo = chaves[i]
        dados = {"tipo": tipo}
        if tipo == "bateria":
            dados["limite"] = perguntar_int("Limite (%)", 20, 1, 99)
            dados["nome"] = f"Bateria < {dados['limite']}%"
        else:
            dados["url"] = perguntar("URL" + (" do feed" if tipo == "rss" else ""))
            if not dados["url"].startswith(("http://", "https://")):
                raise ToonsError("A URL precisa começar com http:// ou https://")
            dados["nome"] = perguntar("Nome do monitor", urllib.parse.urlsplit(dados["url"]).netloc)
        if tipo == "texto":
            dados["texto"] = perguntar("Texto a procurar")
            dados["modo"] = "sumir" if escolher("Avisar quando", ["o texto APARECER", "o texto SUMIR"], 1) == 1 \
                else "aparecer"
        elif tipo == "preco":
            nomes = list(REGEX_PRECO) + ["Regex personalizada (1 grupo de captura)"]
            j = escolher("Como achar o preço na página?", nomes, 1)
            dados["regex"] = REGEX_PRECO[nomes[j]] if j is not None and j < len(REGEX_PRECO) else \
                perguntar("Regex", r"R\$\s*([\d.]+,\d{2})")
            dados["alvo"] = perguntar_float("Avisar quando o preço for menor ou igual a (R$)")
            dados["avisar_mudanca"] = confirmar("Avisar também a cada mudança de preço?", False)
            info("Testando a página...")
            try:
                _, resumo = checar_monitor(dados, {})
                ok(f"Preço encontrado agora: {resumo}")
            except (ToonsError, OSError) as e:
                aviso(f"Teste falhou: {e}. Salve mesmo assim e ajuste depois, se quiser.")
        elif tipo == "rss":
            dados["filtro"] = perguntar("Só avisar se o título contiver (opcional)", "")
        dados["intervalo"] = perguntar_int("Checar a cada quantos minutos", 30 if tipo != "status" else 5, 1) * 60
        adicionar_monitor_dados(dados)
        if not servico_ativo("monitor") and confirmar("Iniciar o serviço de monitoramento agora?", True):
            iniciar_servico("monitor", cmd_self("monitor"), reiniciar=True)

    def listar():
        estado = ler_json(STATE_FILE, {})
        if not c["monitores"]:
            info("Nenhum monitor cadastrado.")
            return
        for m in c["monitores"]:
            est = estado.get(m["id"], {})
            situacao = f"{VERM}erro: {est['erro']}{RST}" if est.get("erro") else est.get("resumo", "—")
            ativo = "" if m.get("ativo", True) else f" {DIM}(pausado){RST}"
            print(f"{CIANO}•{RST} {NEG}{m['nome']}{RST}{ativo} [{m['tipo']}] a cada "
                  f"{int(m.get('intervalo', 300)) // 60} min")
            if m.get("url"):
                print(f"     {DIM}{m['url'][:70]}{RST}")
            print(f"     último: {situacao} {DIM}{est.get('quando', '')}{RST}")
        print(f"\nServiço: {'RODANDO' if servico_ativo('monitor') else 'parado'}")

    def escolher_monitor(msg):
        if not c["monitores"]:
            raise ToonsError("Nenhum monitor cadastrado.")
        i = escolher(msg, [f"{m['nome']} [{m['tipo']}]" for m in c["monitores"]])
        return None if i is None else c["monitores"][i]

    def remover():
        m = escolher_monitor("Remover qual?")
        if m and confirmar(f"Remover '{m['nome']}'?"):
            c["monitores"].remove(m)
            salvar_cfg()
            ok("Removido.")

    def pausar_retomar():
        m = escolher_monitor("Pausar/retomar qual?")
        if m:
            m["ativo"] = not m.get("ativo", True)
            salvar_cfg()
            ok(f"'{m['nome']}' {'ativado' if m['ativo'] else 'pausado'}.")

    def testar_agora():
        estado = copy.deepcopy(ler_json(STATE_FILE, {}))  # cópia: o teste não mexe no estado real
        for m in c["monitores"]:
            try:
                alerta, resumo = checar_monitor(m, estado.setdefault(m["id"], {}))
                ok(f"{m['nome']}: {resumo}" + (f"\n   {AMAR}alerta:{RST} {alerta}" if alerta else ""))
            except Exception as e:  # noqa: BLE001
                erro(f"{m['nome']}: {e}")

    def alertas():
        c["alerta_tts"] = confirmar("Falar os alertas em voz alta (TTS)?", c["alerta_tts"])
        c["alerta_telegram"] = confirmar("Enviar os alertas pelo Telegram (precisa do bot configurado)?",
                                         c["alerta_telegram"])
        salvar_cfg()
        if confirmar("Disparar um alerta de teste agora?", True):
            disparar_alerta("✅ Teste de alerta do Termux-Toons")

    menu("🔎 Scraping e monitoramento", [
        ("Adicionar monitor (preço, notícia, status, texto...)", adicionar),
        ("Listar monitores e último resultado", listar),
        ("Testar todos agora", testar_agora),
        ("Pausar/retomar monitor", pausar_retomar),
        ("Remover monitor", remover),
        *itens_servico("monitor", "Monitoramento 24h",
                       lambda: iniciar_servico("monitor", cmd_self("monitor"), reiniciar=True)),
        ("Configurar alertas (notificação, TTS, Telegram)", alertas),
    ])


# ════════════════════════════════════════════════════════════════════
#  8. Rede e segurança — use SOMENTE em redes e equipamentos seus
# ════════════════════════════════════════════════════════════════════

def _aceitar_aviso_rede() -> bool:
    c = cfg()
    if c.get("aviso_rede_aceito"):
        return True
    limpar()
    titulo("⚠️  Aviso legal")
    print("As ferramentas desta seção (nmap, captura de tráfego...) só podem ser usadas\n"
          "em redes e equipamentos SEUS ou com autorização expressa do dono.\n"
          "Escanear redes de terceiros pode ser crime (Lei 12.737/2012 no Brasil).\n")
    if confirmar("Entendi e vou usar apenas em equipamentos meus/autorizados", False):
        c["aviso_rede_aceito"] = True
        salvar_cfg()
        return True
    return False


def _rede_local_24() -> str:
    partes = ip_local().split(".")
    return ".".join(partes[:3]) + ".0/24" if len(partes) == 4 else "192.168.0.0/24"


@submenu
def menu_rede():
    if not _aceitar_aviso_rede():
        return

    def info_rede():
        print(f"  IP local:   {NEG}{ip_local()}{RST}")
        print(f"  IP público: {NEG}{ip_publico()}{RST}")
        print(f"  Rede /24:   {_rede_local_24()}")
        try:
            wifi = _tapi(["termux-wifi-connectioninfo"], 15)
            if isinstance(wifi, dict):
                for chave in ("ssid", "bssid", "ip", "link_speed_mbps", "rssi", "frequency_mhz"):
                    if chave in wifi:
                        print(f"  {chave:<11} {wifi[chave]}")
        except ToonsError as e:
            aviso(f"Wi-Fi: {e}")

    def descobrir():
        if not garantir_cmd("nmap"):
            return
        rede = perguntar("Rede a varrer", _rede_local_24())
        info("Procurando dispositivos ligados (ping scan, sem escanear portas)...")
        rodar(["nmap", "-sn", rede])

    def portas():
        if not garantir_cmd("nmap"):
            return
        alvo = perguntar("IP ou nome do host (seu!)", ip_local())
        if not confirmar(f"Confirma que '{alvo}' é seu ou você tem autorização?", False):
            return
        modos = {"Rápido (100 portas mais comuns)": ["-F"],
                 "Padrão (1000 portas) + versões dos serviços": ["-sV"],
                 "Completo (todas as 65535 portas, demora)": ["-p-", "-T4"]}
        i = escolher("Tipo de varredura", list(modos), 1)
        if i is not None:
            rodar(["nmap", *list(modos.values())[i], alvo])

    def basicas():
        host = perguntar("Host", "google.com")
        try:
            ips = sorted({r[4][0] for r in socket.getaddrinfo(host, None)})
            ok(f"DNS: {host} → {', '.join(ips)}")
        except socket.gaierror as e:
            erro(f"DNS falhou: {e}")
        rodar(["ping", "-c", "4", host])
        if tem("traceroute") or confirmar("Instalar traceroute para ver a rota?", False) and instalar_pkg("traceroute"):
            rodar(["traceroute", host])

    def velocidade():
        base = "https://speed.cloudflare.com"
        latencias = []
        for _ in range(3):
            t0 = time.time()
            baixar_url(f"{base}/__down?bytes=0", 10)
            latencias.append((time.time() - t0) * 1000)
        ok(f"Latência: {min(latencias):.0f} ms")
        info("Medindo download (25 MB)...")
        req = urllib.request.Request(f"{base}/__down?bytes=25000000", headers={"User-Agent": USER_AGENT})
        recebido, t0 = 0, time.time()
        with urllib.request.urlopen(req, timeout=120) as r:
            while bloco := r.read(1 << 16):
                recebido += len(bloco)
        ok(f"Download: {recebido * 8 / (time.time() - t0) / 1e6:.1f} Mbit/s")
        info("Medindo upload (5 MB)...")
        corpo = os.urandom(5_000_000)
        req = urllib.request.Request(f"{base}/__up", data=corpo, headers={
            "User-Agent": USER_AGENT, "Content-Type": "application/octet-stream"})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=120) as r:
            r.read()
        ok(f"Upload: {len(corpo) * 8 / (time.time() - t0) / 1e6:.1f} Mbit/s")

    def wifi_proximas():
        redes = _tapi(["termux-wifi-scaninfo"], 30)
        if not isinstance(redes, list):
            raise ToonsError(f"Resposta inesperada: {redes} (localização precisa estar ligada)")
        for r in sorted(redes, key=lambda x: x.get("rssi", -999), reverse=True):
            print(f"  {r.get('rssi', '?'):>4} dBm  {r.get('frequency_mhz', '?'):>5} MHz  {r.get('ssid') or '(oculta)'}")

    def trafego():
        if tem_root():
            if not garantir_cmd("tcpdump", repo="root-repo"):
                return
            interface = perguntar("Interface", "wlan0")
            n = perguntar_int("Quantos pacotes capturar", 200, 1)
            arq = DATA_DIR / f"captura_{datetime.now():%Y%m%d_%H%M%S}.pcap"
            rodar(["su", "-c", shlex.join(["tcpdump", "-i", interface, "-c", str(n), "-w", str(arq)])])
            info(f"Captura salva em {arq}. Abra no Wireshark ou leia aqui com a opção de ler .pcap.")
            return
        aviso("Sem root o Android não deixa capturar pacotes diretamente.")
        print("Alternativas sem root:\n"
              "  • App PCAPdroid (F-Droid): captura via VPN local e exporta .pcap\n"
              "  • Depois, leia o .pcap aqui com tcpdump (não precisa de root para ler).\n")
        caminho = perguntar("Caminho de um .pcap para ler (Enter para pular)", "")
        if caminho and garantir_cmd("tcpdump", repo="root-repo"):
            rodar(f"tcpdump -nn -r {shlex.quote(os.path.expanduser(caminho))} | head -n 100")

    def ssh_configurar():
        if not garantir_cmd("sshd", "openssh"):
            return
        info("Defina a senha do seu usuário do Termux (usada para logar via SSH):")
        rodar(["passwd"])
        ok("Pronto. Agora use 'Iniciar servidor SSH'.")

    def ssh_iniciar():
        if not garantir_cmd("sshd", "openssh"):
            return
        rodar(["sshd"])
        usuario = saida(["whoami"]) or getpass.getuser()
        ok(f"SSH na porta 8022. De outro computador:\n    ssh -p 8022 {usuario}@{ip_local()}")

    def ssh_chave():
        chave = perguntar("Cole a chave pública (ssh-ed25519 AAAA... / ssh-rsa ...)")
        if not chave.startswith(("ssh-", "ecdsa-", "sk-")):
            raise ToonsError("Isso não parece uma chave pública SSH.")
        pasta = HOME / ".ssh"
        pasta.mkdir(mode=0o700, exist_ok=True)
        arq = pasta / "authorized_keys"
        with open(arq, "a", encoding="utf-8") as f:
            f.write(chave.strip() + "\n")
        os.chmod(arq, 0o600)
        ok("Chave autorizada.")

    def wireguard():
        if not garantir_cmd("wg", "wireguard-tools"):
            return
        pasta = HOME / "wireguard"
        pasta.mkdir(mode=0o700, exist_ok=True)
        nome = re.sub(r"[^\w-]", "_", perguntar("Nome da configuração", "celular"))
        privada = saida(["wg", "genkey"])
        publica = rodar(["wg", "pubkey"], capturar=True, entrada=privada + "\n", mostrar=False).stdout.strip()
        if not privada or not publica:
            raise ToonsError("Falha ao gerar as chaves.")
        ok(f"Chave pública deste cliente: {NEG}{publica}{RST}")
        endereco = perguntar("Endereço deste cliente na VPN", "10.8.0.2/32")
        dns = perguntar("DNS", "1.1.1.1")
        srv_pub = perguntar("Chave pública do SERVIDOR")
        endpoint = perguntar("Endpoint do servidor (host:porta)", "meu.servidor.com:51820")
        permitidos = perguntar("AllowedIPs (0.0.0.0/0 = todo o tráfego pela VPN)", "0.0.0.0/0, ::/0")
        conf = (f"[Interface]\nPrivateKey = {privada}\nAddress = {endereco}\nDNS = {dns}\n\n"
                f"[Peer]\nPublicKey = {srv_pub}\nEndpoint = {endpoint}\nAllowedIPs = {permitidos}\n"
                "PersistentKeepalive = 25\n")
        arq = pasta / f"{nome}.conf"
        arq.write_text(conf, "utf-8")
        os.chmod(arq, 0o600)
        ok(f"Configuração salva em {arq}")
        print(f"\nNo SERVIDOR, adicione este peer:\n{DIM}[Peer]\nPublicKey = {publica}\n"
              f"AllowedIPs = {endereco}{RST}\n")
        if tem("qrencode") or garantir_cmd("qrencode", "libqrencode"):
            rodar(["qrencode", "-t", "ansiutf8"], entrada=conf, mostrar=False)
            info("No app WireGuard: + → Escanear código QR.")
        info("Subir o túnel direto no Termux exige root (wg-quick). Sem root, use o app WireGuard.")

    menu("🛡️ Rede e segurança (só em equipamentos seus!)", [
        ("Informações de rede (IP local/público, Wi-Fi)", info_rede),
        ("Descobrir dispositivos na rede (nmap -sn)", descobrir),
        ("Escanear portas de um host seu (nmap)", portas),
        ("DNS, ping e traceroute", basicas),
        ("Teste de velocidade (Cloudflare)", velocidade),
        ("Redes Wi-Fi próximas", wifi_proximas),
        ("Análise de tráfego (tcpdump / .pcap)", trafego),
        ("SSH: instalar e definir senha", ssh_configurar),
        ("SSH: iniciar servidor (porta 8022)", ssh_iniciar),
        ("SSH: parar servidor", lambda: rodar(["pkill", "sshd"])),
        ("SSH: autorizar chave pública", ssh_chave),
        ("WireGuard: gerar chaves + config + QR code", wireguard),
    ])


# ════════════════════════════════════════════════════════════════════
#  9. Retro: jogos ASCII, interpretador BASIC e template de jogo
# ════════════════════════════════════════════════════════════════════

def _recorde(jogo: str, pontos: int | None = None) -> int:
    recordes = ler_json(RECORDES_FILE, {})
    if pontos is not None and pontos > recordes.get(jogo, 0):
        recordes[jogo] = pontos
        gravar_json(RECORDES_FILE, recordes)
    return recordes.get(jogo, 0)


def snake() -> None:
    import curses

    def jogo(tela):
        curses.curs_set(0)
        tela.nodelay(True)
        tela.keypad(True)
        try:
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_GREEN, -1)
            curses.init_pair(2, curses.COLOR_RED, -1)
        except curses.error:
            pass
        alt, larg = tela.getmaxyx()
        if alt < 10 or larg < 20:
            tela.nodelay(False)
            tela.addstr(0, 0, "Tela pequena demais.")
            tela.getch()
            return 0
        cobra = [(alt // 2, larg // 2 + i) for i in range(3)]
        direcao = (0, -1)
        direcoes = {curses.KEY_UP: (-1, 0), curses.KEY_DOWN: (1, 0), curses.KEY_LEFT: (0, -1),
                    curses.KEY_RIGHT: (0, 1), ord("w"): (-1, 0), ord("s"): (1, 0), ord("a"): (0, -1),
                    ord("d"): (0, 1)}

        def nova_comida():
            while True:
                pos = (random.randint(2, alt - 2), random.randint(1, larg - 2))
                if pos not in cobra:
                    return pos

        comida, pontos, atraso = nova_comida(), 0, 0.15
        while True:
            tela.erase()
            tela.border()
            tela.addnstr(0, 2, f" SNAKE  pontos:{pontos}  recorde:{_recorde('snake')}  q:sair ", larg - 4)
            tela.addch(comida[0], comida[1], "*", curses.color_pair(2) | curses.A_BOLD)
            for i, (y, x) in enumerate(cobra):
                tela.addch(y, x, "@" if i == 0 else "o", curses.color_pair(1))
            tela.refresh()
            time.sleep(atraso if direcao[0] == 0 else atraso * 1.4)  # vertical mais lento (fonte é alta)
            tecla, nova_dir = tela.getch(), direcao
            while tecla != -1:
                if tecla in (ord("q"), 27):
                    return pontos
                d = direcoes.get(tecla)
                if d and (d[0] + direcao[0], d[1] + direcao[1]) != (0, 0):
                    nova_dir = d
                tecla = tela.getch()
            direcao = nova_dir
            cabeca = (cobra[0][0] + direcao[0], cobra[0][1] + direcao[1])
            if not (1 <= cabeca[0] < alt - 1 and 1 <= cabeca[1] < larg - 1) or cabeca in cobra:
                break
            cobra.insert(0, cabeca)
            if cabeca == comida:
                pontos += 1
                comida = nova_comida()
                atraso = max(0.05, atraso * 0.96)
            else:
                cobra.pop()
        tela.nodelay(False)
        msg = f" FIM DE JOGO! {pontos} pontos. Tecla para sair. "
        tela.addnstr(alt // 2, max(0, (larg - len(msg)) // 2), msg, larg - 1, curses.A_REVERSE)
        tela.refresh()
        time.sleep(0.6)
        tela.getch()
        return pontos

    pontos = curses.wrapper(jogo)
    recorde_antigo = _recorde("snake")
    _recorde("snake", pontos)
    print(f"Você fez {pontos} pontos." + (" 🏆 Novo recorde!" if pontos > recorde_antigo else ""))


def adivinhacao() -> None:
    numero, tentativas = random.randint(1, 100), 0
    print("Pensei em um número de 1 a 100. Tente adivinhar!")
    while True:
        palpite = perguntar_int("Palpite", None, 1, 100)
        tentativas += 1
        if palpite == numero:
            ok(f"Acertou em {tentativas} tentativa(s)!")
            recorde = _recorde("adivinhacao_menos")
            if not recorde or tentativas < recorde:
                recordes = ler_json(RECORDES_FILE, {})
                recordes["adivinhacao_menos"] = tentativas
                gravar_json(RECORDES_FILE, recordes)
                print("🏆 Novo recorde!")
            return
        print("  ⬆️  Maior!" if palpite < numero else "  ⬇️  Menor!")


# ── Interpretador de BASIC ──────────────────────────────────────────

class BasicErro(Exception):
    pass


_BASIC_TOKEN = re.compile(r"""\s*(?:
    (?P<num>\d+\.?\d*(?:[eE][-+]?\d+)?|\.\d+) |
    (?P<str>"[^"]*") |
    (?P<id>[A-Za-z][A-Za-z0-9_]*\$?) |
    (?P<op><>|<=|>=|[-+*/^()=<>,;])
)""", re.X)

_BASIC_RESERVADAS = {"AND", "OR", "NOT", "MOD", "THEN", "TO", "STEP", "ELSE"}


def _basic_fmt(valor) -> str:
    if isinstance(valor, float):
        if valor.is_integer() and abs(valor) < 1e15:
            return str(int(valor))
        return f"{valor:.10g}"
    return str(valor)


def _basic_val(texto) -> float:
    try:
        return float(str(texto).strip())
    except ValueError:
        return 0.0


_BASIC_FUNCOES = {
    "ABS": abs, "INT": lambda x: float(math.floor(x)), "SQR": math.sqrt, "SIN": math.sin,
    "COS": math.cos, "TAN": math.tan, "ATN": math.atan, "LOG": math.log, "EXP": math.exp,
    "RND": lambda x=1: random.random(), "SGN": lambda x: float((x > 0) - (x < 0)),
    "LEN": lambda s: float(len(s)), "LEFT$": lambda s, n: s[:int(n)],
    "RIGHT$": lambda s, n: s[len(s) - int(n):] if int(n) > 0 else "",
    "MID$": lambda s, i, n=None: s[int(i) - 1:] if n is None else s[int(i) - 1:int(i) - 1 + int(n)],
    "STR$": _basic_fmt, "VAL": _basic_val, "CHR$": lambda n: chr(int(n)),
    "ASC": lambda s: float(ord(s[0])) if s else 0.0,
    "UPPER$": lambda s: s.upper(), "LOWER$": lambda s: s.lower(),
}


def _basic_tokens(texto: str, parar_em_then: bool = False) -> list:
    """Lista de (tipo, valor, início, fim). Com parar_em_then, para logo após o THEN."""
    tokens, pos = [], 0
    while pos < len(texto):
        if parar_em_then and tokens and tokens[-1][:2] == ("id", "THEN"):
            break
        if texto[pos:].strip() == "":
            break
        m = _BASIC_TOKEN.match(texto, pos)
        if not m:
            raise BasicErro(f"caractere inválido: {texto[pos:].strip()[:1]!r}")
        tipo = m.lastgroup
        bruto = m.group(tipo)
        if tipo == "num":
            valor = float(bruto)
        elif tipo == "str":
            valor = bruto[1:-1]
        elif tipo == "id":
            valor = bruto.upper()
        else:
            valor = bruto
        tokens.append((tipo, valor, m.start(tipo), m.end()))
        pos = m.end()
    return tokens


class _BasicExpr:
    """Avaliador de expressões por descida recursiva (sem eval do Python)."""

    def __init__(self, basic: "Basic", tokens: list):
        self.b, self.t, self.i = basic, tokens, 0

    def ver(self):
        return self.t[self.i][:2] if self.i < len(self.t) else (None, None)

    def pegar(self):
        tok = self.ver()
        self.i += 1
        return tok

    def esperar(self, op: str):
        if self.ver() != ("op", op):
            raise BasicErro(f"esperava '{op}'")
        self.i += 1

    def fim(self) -> bool:
        return self.i >= len(self.t)

    def expr(self):
        try:
            return self._ou()
        except (TypeError, ValueError, OverflowError, IndexError) as e:
            raise BasicErro(f"erro na expressão ({e})") from None

    def _ou(self):
        v = self._e()
        while self.ver() == ("id", "OR"):
            self.pegar()
            d = self._e()
            v = -1.0 if (v or d) else 0.0
        return v

    def _e(self):
        v = self._nao()
        while self.ver() == ("id", "AND"):
            self.pegar()
            d = self._nao()
            v = -1.0 if (v and d) else 0.0
        return v

    def _nao(self):
        if self.ver() == ("id", "NOT"):
            self.pegar()
            return 0.0 if self._nao() else -1.0
        return self._comparacao()

    def _comparacao(self):
        v = self._soma()
        tipo, op = self.ver()
        if tipo == "op" and op in ("=", "<>", "<", ">", "<=", ">="):
            self.pegar()
            d = self._soma()
            if isinstance(v, str) != isinstance(d, str):
                raise BasicErro("comparação entre texto e número")
            r = {"=": v == d, "<>": v != d, "<": v < d, ">": v > d, "<=": v <= d, ">=": v >= d}[op]
            return -1.0 if r else 0.0
        return v

    def _soma(self):
        v = self._mult()
        while self.ver() in (("op", "+"), ("op", "-")):
            op = self.pegar()[1]
            d = self._mult()
            if isinstance(v, str) != isinstance(d, str):
                raise BasicErro("tipos incompatíveis (use STR$ ou VAL)")
            v = v + d if op == "+" else v - d
        return v

    def _mult(self):
        v = self._unario()
        while self.ver() in (("op", "*"), ("op", "/"), ("id", "MOD")):
            op = self.pegar()[1]
            d = self._unario()
            if op != "*" and d == 0:
                raise BasicErro("divisão por zero")
            v = v * d if op == "*" else v / d if op == "/" else v % d
        return v

    def _unario(self):
        if self.ver() == ("op", "-"):
            self.pegar()
            return -self._unario()
        if self.ver() == ("op", "+"):
            self.pegar()
        return self._potencia()

    def _potencia(self):
        v = self._atomo()
        if self.ver() == ("op", "^"):
            self.pegar()
            return float(v ** self._unario())
        return v

    def _argumentos(self) -> list:
        self.esperar("(")
        args = [self.expr()]
        while self.ver() == ("op", ","):
            self.pegar()
            args.append(self.expr())
        self.esperar(")")
        return args

    def _atomo(self):
        tipo, valor = self.pegar()
        if tipo in ("num", "str"):
            return valor
        if (tipo, valor) == ("op", "("):
            v = self.expr()
            self.esperar(")")
            return v
        if tipo == "id" and valor not in _BASIC_RESERVADAS:
            if valor in _BASIC_FUNCOES:
                return _BASIC_FUNCOES[valor](*self._argumentos())
            if self.ver() == ("op", "("):
                return self.b.matrizes.get((valor, tuple(int(a) for a in self._argumentos())),
                                           "" if valor.endswith("$") else 0.0)
            return self.b.vars.get(valor, "" if valor.endswith("$") else 0.0)
        raise BasicErro("expressão inválida" if tipo else "expressão incompleta")


class Basic:
    """Um BASIC clássico com números de linha.

    Instruções: PRINT, INPUT, LET, IF..THEN, GOTO, GOSUB/RETURN, FOR/NEXT/STEP,
    DIM, REM, CLS, END/STOP, e várias instruções por linha separadas por ':'.
    Comandos: RUN, LIST, NEW, SAVE "x", LOAD "x", FILES, DEMO, AJUDA, SAIR.
    """

    DEMO = {
        10: 'REM ADIVINHE O NUMERO',
        20: 'PRINT "ADIVINHE O NUMERO DE 1 A 100"',
        30: 'N = INT(RND(1) * 100) + 1 : T = 0',
        40: 'INPUT "SEU PALPITE"; P',
        50: 'T = T + 1',
        60: 'IF P < N THEN PRINT "MAIOR!" : GOTO 40',
        70: 'IF P > N THEN PRINT "MENOR!" : GOTO 40',
        80: 'PRINT "ACERTOU EM "; T; " TENTATIVAS!"',
        90: 'FOR I = 1 TO 3 : PRINT "*** PARABENS ***" : NEXT I',
        100: 'END',
    }

    def __init__(self):
        self.programa: dict = {}
        self.vars: dict = {}
        self.matrizes: dict = {}

    # ── execução ──
    @staticmethod
    def dividir(linha: str) -> list:
        """Separa instruções por ':' respeitando aspas; REM e IF ficam com o resto da linha."""
        partes, atual, aspas = [], "", False
        i = 0
        while i < len(linha):
            ch = linha[i]
            if not aspas and not atual.strip() and re.match(r"(?i)(REM|IF)\b", linha[i:]):
                partes.append(linha[i:].strip())
                return partes
            if ch == '"':
                aspas = not aspas
            if ch == ":" and not aspas:
                if atual.strip():
                    partes.append(atual.strip())
                atual = ""
            else:
                atual += ch
            i += 1
        if atual.strip():
            partes.append(atual.strip())
        return partes

    def _destino(self, numero) -> tuple:
        n = int(numero)
        if n not in self.indice:
            raise BasicErro(f"linha {n} não existe")
        return self.indice[n], 0

    def executar(self, texto: str) -> None:
        texto = texto.strip()
        if not texto or texto.upper().startswith("REM") or texto.startswith("'"):
            return
        # No IF o resto depois do THEN é outra instrução: só tokeniza até ele.
        tokens = _basic_tokens(texto, parar_em_then=bool(re.match(r"(?i)IF\b", texto)))
        tipo, kw = tokens[0][:2]
        resto = tokens[1:]
        if tipo != "id":
            raise BasicErro("instrução inválida")

        if kw == "PRINT":
            self._print(resto)
        elif kw == "INPUT":
            self._input(resto)
        elif kw == "IF":
            self._if(texto, tokens)
        elif kw == "GOTO":
            self.salto = self._destino(_BasicExpr(self, resto).expr())
        elif kw == "GOSUB":
            self.pilha_gosub.append((self.pos[0], self.pos[1] + 1))
            self.salto = self._destino(_BasicExpr(self, resto).expr())
        elif kw == "RETURN":
            if not self.pilha_gosub:
                raise BasicErro("RETURN sem GOSUB")
            self.salto = self.pilha_gosub.pop()
        elif kw == "FOR":
            self._for(resto)
        elif kw == "NEXT":
            self._next(resto)
        elif kw in ("END", "STOP"):
            self.terminou = True
        elif kw == "CLS":
            limpar()
        elif kw == "DIM":
            pass  # as matrizes crescem sozinhas
        elif kw == "LET":
            self._atribuir(resto)
        else:
            self._atribuir(tokens)

    def _atribuir(self, tokens: list) -> None:
        if not tokens or tokens[0][0] != "id" or tokens[0][1] in _BASIC_RESERVADAS:
            raise BasicErro("instrução desconhecida")
        nome = tokens[0][1]
        p = _BasicExpr(self, tokens[1:])
        indices = None
        if p.ver() == ("op", "("):
            indices = tuple(int(a) for a in p._argumentos())
        p.esperar("=")
        valor = p.expr()
        if not p.fim():
            raise BasicErro("sobrou algo depois da expressão")
        if nome.endswith("$") != isinstance(valor, str):
            raise BasicErro(f"tipo errado para {nome}")
        if indices is None:
            self.vars[nome] = valor
        else:
            self.matrizes[(nome, indices)] = valor

    def _print(self, tokens: list) -> None:
        p, saida_txt, quebra = _BasicExpr(self, tokens), "", True
        while not p.fim():
            if p.ver() == ("op", ";"):
                p.pegar()
                quebra = False
                continue
            if p.ver() == ("op", ","):
                p.pegar()
                saida_txt += "\t"
                quebra = False
                continue
            saida_txt += _basic_fmt(p.expr())
            quebra = True
        print(saida_txt, end="\n" if quebra else "", flush=True)

    def _input(self, tokens: list) -> None:
        prompt = "? "
        if tokens and tokens[0][0] == "str" and len(tokens) > 1 and tokens[1][1] in (";", ","):
            prompt = tokens[0][1] + ("? " if tokens[1][1] == ";" else "")
            tokens = tokens[2:]
        nomes = [t[1] for t in tokens if t[0] == "id"]
        if not nomes:
            raise BasicErro("INPUT sem variável")
        for nome in nomes:
            while True:
                resp = input(prompt)
                if nome.endswith("$"):
                    self.vars[nome] = resp
                    break
                try:
                    self.vars[nome] = float(resp.replace(",", "."))
                    break
                except ValueError:
                    print("?Digite um número")
            prompt = "?? "

    def _if(self, texto: str, tokens: list) -> None:
        idx = next((i for i, t in enumerate(tokens) if t[:2] == ("id", "THEN")), None)
        if idx is None:
            raise BasicErro("IF sem THEN")
        if _BasicExpr(self, tokens[1:idx]).expr():
            resto = texto[tokens[idx][3]:].strip()
            if re.fullmatch(r"\d+", resto):
                self.salto = self._destino(resto)
                return
            for instrucao in self.dividir(resto):
                self.executar(instrucao)
                if self.salto is not None or self.terminou:
                    return

    def _for(self, tokens: list) -> None:
        idx_to = next((i for i, t in enumerate(tokens) if t[:2] == ("id", "TO")), None)
        if idx_to is None or len(tokens) < 3 or tokens[1][:2] != ("op", "="):
            raise BasicErro("use: FOR I = 1 TO 10 [STEP 1]")
        var = tokens[0][1]
        idx_step = next((i for i, t in enumerate(tokens) if t[:2] == ("id", "STEP")), None)
        inicio = _BasicExpr(self, tokens[2:idx_to]).expr()
        limite = _BasicExpr(self, tokens[idx_to + 1:idx_step]).expr()
        passo = _BasicExpr(self, tokens[idx_step + 1:]).expr() if idx_step else 1.0
        self.vars[var] = inicio
        self.pilha_for = [f for f in self.pilha_for if f["var"] != var]
        if (passo >= 0 and inicio > limite) or (passo < 0 and inicio < limite):
            self._pular_para_next(var)  # laço que não executa nenhuma vez
            return
        self.pilha_for.append({"var": var, "limite": limite, "passo": passo,
                               "volta": (self.pos[0], self.pos[1] + 1)})

    def _pular_para_next(self, var: str) -> None:
        nivel = 0
        i, j = self.pos[0], self.pos[1] + 1
        while i < len(self.linhas):
            partes = self.instr[self.linhas[i]]
            while j < len(partes):
                palavra = partes[j].split()[0].upper() if partes[j].split() else ""
                if palavra == "FOR":
                    nivel += 1
                elif palavra == "NEXT":
                    if nivel == 0:
                        self.salto = (i, j + 1)
                        return
                    nivel -= 1
                j += 1
            i, j = i + 1, 0
        self.terminou = True

    def _next(self, tokens: list) -> None:
        if not self.pilha_for:
            raise BasicErro("NEXT sem FOR")
        if tokens:
            var = tokens[0][1]
            while self.pilha_for and self.pilha_for[-1]["var"] != var:
                self.pilha_for.pop()
            if not self.pilha_for:
                raise BasicErro(f"NEXT {var} sem FOR")
        f = self.pilha_for[-1]
        self.vars[f["var"]] = self.vars.get(f["var"], 0.0) + f["passo"]
        valor = self.vars[f["var"]]
        if (f["passo"] >= 0 and valor <= f["limite"]) or (f["passo"] < 0 and valor >= f["limite"]):
            self.salto = f["volta"]
        else:
            self.pilha_for.pop()

    def run(self) -> None:
        self.vars, self.matrizes = {}, {}
        self.pilha_gosub, self.pilha_for = [], []
        self.linhas = sorted(self.programa)
        self.indice = {n: i for i, n in enumerate(self.linhas)}
        self.instr = {n: self.dividir(self.programa[n]) for n in self.linhas}
        self.terminou = False
        i = j = 0
        while i < len(self.linhas) and not self.terminou:
            n = self.linhas[i]
            if j >= len(self.instr[n]):
                i, j = i + 1, 0
                continue
            self.pos, self.salto = (i, j), None
            try:
                self.executar(self.instr[n][j])
            except BasicErro as e:
                raise BasicErro(f"{e} (linha {n})") from None
            except KeyboardInterrupt:
                raise BasicErro(f"interrompido na linha {n}") from None
            if self.salto is not None:
                i, j = self.salto
            else:
                j += 1

    # ── modo interativo ──
    def listar(self, arg: str = "") -> None:
        faixa = re.fullmatch(r"\s*(\d*)\s*-?\s*(\d*)\s*", arg or "")
        ini = int(faixa.group(1)) if faixa and faixa.group(1) else 0
        fim = int(faixa.group(2)) if faixa and faixa.group(2) else (ini if faixa and faixa.group(1) and "-" not in arg else 10 ** 9)
        for n in sorted(self.programa):
            if ini <= n <= fim:
                print(f"{n} {self.programa[n]}")

    def _arquivo(self, arg: str) -> Path:
        nome = arg.strip().strip('"')
        if not nome:
            raise BasicErro('informe o nome: SAVE "jogo"')
        caminho = Path(os.path.expanduser(nome))
        if not caminho.is_absolute():
            caminho = BASIC_DIR / caminho
        return caminho if caminho.suffix else caminho.with_suffix(".bas")

    def carregar(self, caminho: Path) -> None:
        self.programa = {}
        for linha in caminho.read_text("utf-8").splitlines():
            m = re.match(r"\s*(\d+)\s*(.*)", linha)
            if m and m.group(2).strip():
                self.programa[int(m.group(1))] = m.group(2).strip()

    def repl(self) -> None:
        BASIC_DIR.mkdir(parents=True, exist_ok=True)
        print(f"{VERD}TOONS BASIC {VERSION}{RST} — digite AJUDA para ver os comandos, SAIR para voltar.\nPRONTO")
        while True:
            try:
                linha = input("> ")
            except EOFError:
                return
            except KeyboardInterrupt:
                print()
                continue
            linha = linha.strip()
            if not linha:
                continue
            m = re.match(r"(\d+)\s*(.*)", linha)
            if m:
                n, cod = int(m.group(1)), m.group(2).strip()
                if cod:
                    self.programa[n] = cod
                else:
                    self.programa.pop(n, None)
                continue
            cmd, _, arg = linha.partition(" ")
            cmd = cmd.upper()
            try:
                if cmd in ("SAIR", "BYE", "EXIT", "QUIT", "SYSTEM"):
                    return
                if cmd == "RUN":
                    self.run()
                elif cmd == "LIST":
                    self.listar(arg)
                elif cmd == "NEW":
                    self.programa = {}
                elif cmd == "SAVE":
                    destino = self._arquivo(arg)
                    destino.write_text("".join(f"{n} {c}\n" for n, c in sorted(self.programa.items())), "utf-8")
                    print(f"Salvo em {destino}")
                elif cmd == "LOAD":
                    self.carregar(self._arquivo(arg))
                    print(f"{len(self.programa)} linhas carregadas.")
                elif cmd in ("FILES", "DIR"):
                    for arq in sorted(BASIC_DIR.glob("*.bas")):
                        print(f"  {arq.stem}")
                elif cmd == "DEMO":
                    self.programa = dict(self.DEMO)
                    print("Demo carregada. Digite LIST para ver ou RUN para jogar.")
                elif cmd in ("AJUDA", "HELP"):
                    print(self.__doc__)
                    print("Funções: " + ", ".join(sorted(_BASIC_FUNCOES)))
                    print("Exemplo:\n  10 FOR I = 1 TO 5\n  20 PRINT I; \" AO QUADRADO = \"; I ^ 2\n  30 NEXT I\n  RUN")
                else:
                    self.pos, self.salto, self.terminou = (0, 0), None, False
                    self.linhas, self.indice, self.instr = [], {}, {}
                    self.pilha_gosub, self.pilha_for = [], []
                    for instrucao in self.dividir(linha):
                        self.executar(instrucao)
            except BasicErro as e:
                print(f"?ERRO: {e}")
            except (OSError, KeyboardInterrupt) as e:
                print(f"?ERRO: {e or 'interrompido'}")
            print("PRONTO")


TEMPLATE_JOGO = r'''#!/usr/bin/env python3
"""Meu jogo de terminal — gerado pelo Termux-Toons. Edite à vontade!

Mova o @ com as setas ou WASD, pegue os $ e fuja dos X. q para sair.
"""
import curses
import random
import time


def main(tela):
    curses.curs_set(0)
    tela.nodelay(True)
    tela.keypad(True)
    alt, larg = tela.getmaxyx()
    y, x = alt // 2, larg // 2
    moedas = {(random.randint(1, alt - 2), random.randint(1, larg - 2)) for _ in range(10)}
    inimigos = [[random.randint(1, alt - 2), random.randint(1, larg - 2)] for _ in range(3)]
    pontos = 0
    movimentos = {curses.KEY_UP: (-1, 0), curses.KEY_DOWN: (1, 0), curses.KEY_LEFT: (0, -1),
                  curses.KEY_RIGHT: (0, 1), ord("w"): (-1, 0), ord("s"): (1, 0),
                  ord("a"): (0, -1), ord("d"): (0, 1)}
    while True:
        tecla = tela.getch()
        if tecla == ord("q"):
            break
        dy, dx = movimentos.get(tecla, (0, 0))
        y = min(max(1, y + dy), alt - 2)
        x = min(max(1, x + dx), larg - 2)
        if (y, x) in moedas:
            moedas.remove((y, x))
            pontos += 10
            moedas.add((random.randint(1, alt - 2), random.randint(1, larg - 2)))
        for inimigo in inimigos:  # inimigos andam em direção ao jogador às vezes
            if random.random() < 0.3:
                inimigo[0] += (y > inimigo[0]) - (y < inimigo[0])
                inimigo[1] += (x > inimigo[1]) - (x < inimigo[1])
            if inimigo == [y, x]:
                tela.nodelay(False)
                tela.addstr(alt // 2, max(0, larg // 2 - 10), f" GAME OVER: {pontos} pts ")
                tela.getch()
                return
        tela.erase()
        tela.border()
        tela.addstr(0, 2, f" pontos: {pontos} ")
        for my, mx in moedas:
            tela.addch(my, mx, "$")
        for iy, ix in inimigos:
            tela.addch(iy, ix, "X")
        tela.addch(y, x, "@")
        tela.refresh()
        time.sleep(0.05)


if __name__ == "__main__":
    curses.wrapper(main)
'''


@submenu
def menu_retro():
    def basic():
        Basic().repl()

    def criar_jogo():
        destino = Path(os.path.expanduser(perguntar("Salvar o template em", str(HOME / "meu_jogo.py"))))
        if destino.exists() and not confirmar(f"{destino} já existe. Sobrescrever?"):
            return
        destino.write_text(TEMPLATE_JOGO, "utf-8")
        destino.chmod(0o755)
        ok(f"Template criado: {destino}")
        info(f"Jogue com: python {destino}   |   Edite com: nvim {destino}")
        if confirmar("Jogar agora?", True):
            rodar([sys.executable, destino], mostrar=False)

    menu("👾 Retro: jogos e BASIC", [
        ("Snake (setas ou WASD)", snake),
        ("Adivinhe o número", adivinhacao),
        ("Interpretador BASIC (digite DEMO e RUN)", basic),
        ("Criar meu próprio jogo (gera template em Python)", criar_jogo),
        ("Ver recordes", lambda: mostrar_dados(ler_json(RECORDES_FILE, {}) or {"recordes": "nenhum ainda"})),
    ])


# ════════════════════════════════════════════════════════════════════
#  10. Linux de verdade com proot-distro
# ════════════════════════════════════════════════════════════════════

DISTROS = [("debian", "Debian"), ("ubuntu", "Ubuntu"), ("archlinux", "Arch Linux"),
           ("alpine", "Alpine (bem leve)"), ("fedora", "Fedora"), ("opensuse", "openSUSE")]

SCRIPT_ATUALIZAR_DISTRO = (
    "if command -v apt-get >/dev/null; then apt-get update && apt-get full-upgrade -y; "
    "elif command -v pacman >/dev/null; then pacman -Syu --noconfirm; "
    "elif command -v apk >/dev/null; then apk update && apk upgrade; "
    "elif command -v dnf >/dev/null; then dnf upgrade -y; "
    "elif command -v zypper >/dev/null; then zypper --non-interactive dup; fi"
)


def distros_instaladas() -> list:
    """Nomes das distros instaladas (lê o diretório do proot-distro)."""
    for base in (Path(PREFIX) / "var" / "lib" / "proot-distro" / "installed-rootfs",
                 Path(PREFIX) / "var" / "lib" / "proot-distro" / "containers"):
        if base.is_dir():
            return sorted(p.name for p in base.iterdir() if p.is_dir())
    return []


def escolher_distro_instalada() -> str | None:
    instaladas = distros_instaladas()
    if instaladas:
        i = escolher("Distro", instaladas, 1)
        return None if i is None else instaladas[i]
    return perguntar("Nome da distro instalada (veja em 'Listar')", "debian") or None


def atualizar_distros() -> None:
    nomes = distros_instaladas() if tem("proot-distro") else []
    if not nomes:
        info("Nenhuma distro do proot-distro encontrada.")
        return
    for nome in nomes:
        info(f"Atualizando {nome}...")
        rodar(["proot-distro", "login", nome, "--", "sh", "-c", SCRIPT_ATUALIZAR_DISTRO])


@submenu
def menu_proot():
    def instalar_distro():
        if not garantir_cmd("proot-distro"):
            return
        opcoes = [rotulo for _, rotulo in DISTROS] + ["Outra imagem (ex.: ubuntu:24.04, debian:bookworm)"]
        i = escolher("Qual distro?", opcoes, 1)
        if i is None:
            return
        nome = DISTROS[i][0] if i < len(DISTROS) else perguntar("Imagem")
        if nome == "archlinux":
            info("Em celulares ARM, se a imagem do Arch falhar, procure uma alternativa com "
                 "'proot-distro search arch'.")
        rodar(["proot-distro", "install", nome])

    def login():
        nome = escolher_distro_instalada()
        if not nome:
            return
        cmd = ["proot-distro", "login", nome]
        usuario = perguntar("Usuário (Enter = root)", "")
        if usuario:
            cmd += ["--user", usuario]
        if confirmar("Compartilhar a pasta home do Termux dentro da distro?", False):
            cmd.append("--shared-home")
        info("Digite 'exit' para voltar ao Termux.")
        rodar(cmd)

    def comando():
        nome = escolher_distro_instalada()
        linha = perguntar("Comando para rodar dentro da distro", "uname -a && cat /etc/os-release")
        if nome and linha:
            rodar(["proot-distro", "login", nome, "--", "sh", "-c", linha])

    def criar_usuario():
        nome = escolher_distro_instalada()
        usuario = perguntar("Nome do novo usuário")
        if not nome or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,30}", usuario or ""):
            raise ToonsError("Nome de usuário inválido (use letras minúsculas, números, _ e -).")
        script = (
            "set -e; "
            "if command -v apt-get >/dev/null; then apt-get update && apt-get install -y sudo; "
            "elif command -v pacman >/dev/null; then pacman -Sy --noconfirm sudo; "
            "elif command -v apk >/dev/null; then apk add sudo shadow bash; "
            "elif command -v dnf >/dev/null; then dnf install -y sudo; fi; "
            f"id {usuario} >/dev/null 2>&1 || useradd -m -s /bin/bash {usuario} || useradd -m {usuario}; "
            f"passwd {usuario}; mkdir -p /etc/sudoers.d; "
            f"echo '{usuario} ALL=(ALL:ALL) ALL' > /etc/sudoers.d/{usuario}; chmod 440 /etc/sudoers.d/{usuario}"
        )
        rodar(["proot-distro", "login", nome, "--", "sh", "-c", script])
        ok(f"Entre com: proot-distro login {nome} --user {usuario}")

    def backup():
        nome = escolher_distro_instalada()
        if not nome:
            return
        pasta = DOWNLOADS if DOWNLOADS.exists() else HOME
        destino = pasta / f"proot-{nome}-{datetime.now():%Y%m%d-%H%M}.tar.gz"
        rodar(["proot-distro", "backup", nome, "--output", destino])

    def remover():
        nome = escolher_distro_instalada()
        if nome and confirmar(f"Apagar a distro '{nome}' e TODOS os arquivos dela?"):
            rodar(["proot-distro", "remove", nome])

    def resetar():
        nome = escolher_distro_instalada()
        if nome and confirmar(f"Reinstalar '{nome}' do zero (perde os arquivos dela)?"):
            rodar(["proot-distro", "reset", nome])

    menu("🐧 Linux de verdade (proot-distro)", [
        ("Instalar o proot-distro", lambda: instalar_pkg("proot-distro")),
        ("Instalar uma distro (Debian, Ubuntu, Arch, Alpine...)", instalar_distro),
        ("Listar distros instaladas", lambda: rodar(["proot-distro", "list"])),
        ("Entrar na distro (login)", login),
        ("Rodar um comando dentro da distro", comando),
        ("Atualizar pacotes das distros", atualizar_distros),
        ("Criar usuário não-root com sudo", criar_usuario),
        ("Fazer backup de uma distro", backup),
        ("Resetar distro", resetar),
        ("Remover distro", remover),
    ])


# ════════════════════════════════════════════════════════════════════
#  11. Servidor de arquivos e backup
# ════════════════════════════════════════════════════════════════════

def _pasta_compartilhada_padrao() -> str:
    compartilhado = HOME / "storage" / "shared"
    return str(compartilhado if compartilhado.exists() else HOME)


def _caminho_termux() -> Path:
    """/data/data/com.termux/files (pai de home e usr)."""
    return HOME.parent


@submenu
def menu_arquivos():
    def http_iniciar():
        pasta = os.path.expanduser(perguntar("Pasta a compartilhar", _pasta_compartilhada_padrao()))
        porta = perguntar_int("Porta", 8090, 1024, 65535)
        aviso("Qualquer pessoa na mesma rede Wi-Fi poderá baixar os arquivos dessa pasta (sem senha).")
        if iniciar_servico("http-arquivos", shlex.join([sys.executable, "-m", "http.server", str(porta),
                                                        "--bind", "0.0.0.0", "--directory", pasta])):
            info(f"Abra no navegador: http://{ip_local()}:{porta}")

    def rclone_config():
        if garantir_cmd("rclone"):
            info("Siga o assistente: n (novo remoto) → escolha Google Drive, Dropbox, OneDrive, etc.")
            rodar(["rclone", "config"])

    def _escolher_remoto() -> str | None:
        remotos = saida(["rclone", "listremotes"]).split()
        if not remotos:
            aviso("Nenhum remoto configurado. Use 'rclone: configurar' primeiro.")
            return None
        i = escolher("Remoto", remotos, 1)
        return None if i is None else remotos[i]

    def rclone_copiar():
        if not garantir_cmd("rclone"):
            return
        remoto = _escolher_remoto()
        if not remoto:
            return
        origem = os.path.expanduser(perguntar("Pasta local", _pasta_compartilhada_padrao() + "/DCIM"))
        destino = remoto + perguntar("Pasta no remoto", "Backup-Celular")
        modo = escolher("Modo", ["copy — só envia o que é novo (seguro)",
                                 "sync — espelha (APAGA no destino o que não existe na origem)"], 1)
        if modo == 1 and not confirmar("O sync pode apagar arquivos no destino. Continuar?"):
            return
        rodar(["rclone", "sync" if modo == 1 else "copy", origem, destino, "--progress"])

    def rclone_servir():
        if not garantir_cmd("rclone"):
            return
        pasta = os.path.expanduser(perguntar("Pasta a servir", _pasta_compartilhada_padrao()))
        usuario = perguntar("Usuário", "toons")
        senha = perguntar("Senha", secrets.token_urlsafe(8))
        comando = shlex.join(["rclone", "serve", "webdav", pasta, "--addr", ":8091",
                              "--user", usuario, "--pass", senha])
        if iniciar_servico("webdav", comando):
            info(f"WebDAV em http://{ip_local()}:8091  (usuário {usuario}, senha {senha})")
            info("Funciona em gerenciadores de arquivos (Solid Explorer, CX, Windows, macOS...).")

    def syncthing_iniciar():
        if not garantir_cmd("syncthing"):
            return
        endereco = "0.0.0.0:8384" if confirmar("Abrir a interface web para a rede local?", False) else "127.0.0.1:8384"
        if iniciar_servico("syncthing", f"syncthing serve --no-browser --gui-address={endereco}"):
            info(f"Interface: http://{endereco.replace('0.0.0.0', ip_local())}  (defina uma senha nela!)")

    def samba():
        if not garantir_cmd("smbd", "samba"):
            return
        aviso("Experimental: sem root o Samba não pode usar a porta 445; usaremos a 4450.")
        pasta = os.path.expanduser(perguntar("Pasta a compartilhar", _pasta_compartilhada_padrao()))
        usuario = saida(["whoami"]) or getpass.getuser()
        base = DATA_DIR / "samba"
        (base / "private").mkdir(parents=True, exist_ok=True)
        conf = DATA_DIR / "smb.conf"
        conf.write_text(f"""[global]
   server role = standalone server
   smb ports = 4450
   map to guest = never
   load printers = no
   disable spoolss = yes
   pid directory = {base}
   lock directory = {base}
   state directory = {base}
   cache directory = {base}
   private dir = {base / 'private'}
   log file = {LOG_DIR / 'samba.log'}

[termux]
   path = {pasta}
   read only = no
   valid users = {usuario}
   force user = {usuario}
""", "utf-8")
        info(f"Defina a senha SMB do usuário {usuario}:")
        rodar(["smbpasswd", "-c", conf, "-a", usuario])
        if iniciar_servico("samba", shlex.join(["smbd", "--foreground", "--no-process-group",
                                                "--debug-stdout", "-s", str(conf)])):
            info(f"Conecte em smb://{ip_local()}:4450/termux  (usuário {usuario})")

    def backup():
        base = _caminho_termux()
        pasta = DOWNLOADS if garantir_storage() and DOWNLOADS.exists() else HOME
        incluir_usr = confirmar("Incluir os pacotes instalados ($PREFIX/usr)? Arquivo fica bem maior", False)
        excluir = ["--exclude=./home/storage", "--exclude=./home/.cache"]
        if confirmar("Deixar de fora modelos LLM e o build do llama.cpp?", True):
            excluir += ["--exclude=./home/llama-models", "--exclude=./home/llama.cpp/build"]
        destino = pasta / f"termux-backup-{datetime.now():%Y%m%d-%H%M}.tar.gz"
        info(f"Criando {destino} ...")
        proc = rodar(["tar", "-zcf", destino, "-C", base, *excluir, "./home", *(["./usr"] if incluir_usr else [])])
        if proc.returncode == 0 and destino.exists():
            ok(f"Backup pronto: {destino} ({bytes_humanos(destino.stat().st_size)})")
        else:
            erro("O tar terminou com erro (pode ser só arquivo em uso). Confira o arquivo gerado.")

    def restaurar():
        candidatos = sorted(set(DOWNLOADS.glob("termux-backup-*.tar.gz")) | set(HOME.glob("termux-backup-*.tar.gz"))) \
            if DOWNLOADS.exists() else sorted(HOME.glob("termux-backup-*.tar.gz"))
        if candidatos:
            i = escolher("Backup", [p.name for p in candidatos])
            arq = candidatos[i] if i is not None else None
        else:
            arq = Path(os.path.expanduser(perguntar("Caminho do .tar.gz"))) if confirmar("Informar o caminho?") else None
        if not arq or not arq.exists():
            return
        aviso("A restauração SOBRESCREVE os arquivos atuais. Feche outras sessões do Termux antes.")
        if confirmar(f"Restaurar {arq.name}?"):
            rodar(["tar", "-zxf", arq, "-C", _caminho_termux(), "--recursive-unlink", "--preserve-permissions"])
            ok("Restaurado. Reinicie o Termux.")

    menu("🗄️ Servidor de arquivos e backup", [
        *itens_servico("http-arquivos", "Compartilhar pasta via HTTP", http_iniciar),
        ("rclone: instalar e configurar nuvem (Drive, Dropbox, OneDrive...)", rclone_config),
        ("rclone: copiar/sincronizar pasta com a nuvem", rclone_copiar),
        ("rclone: servir pasta na rede via WebDAV (com senha)", rclone_servir),
        ("rclone: parar WebDAV", lambda: parar_servico("webdav")),
        ("Syncthing: iniciar", syncthing_iniciar),
        ("Syncthing: parar", lambda: parar_servico("syncthing")),
        ("Samba (SMB): configurar e iniciar", samba),
        ("Samba (SMB): parar", lambda: parar_servico("samba")),
        ("Backup do Termux (.tar.gz em Downloads)", backup),
        ("Restaurar backup do Termux", restaurar),
    ])


# ════════════════════════════════════════════════════════════════════
#  12. Música: yt-dlp para baixar e mpv para tocar ("Spotify" do terminal)
# ════════════════════════════════════════════════════════════════════

EXTENSOES_AUDIO = {".opus", ".mp3", ".m4a", ".flac", ".ogg", ".wav", ".aac", ".webm"}
PLAYLISTS_DIR = DATA_DIR / "playlists"
CONTROLES_MPV = ("Controles: Espaço pausa · ←/→ 5s · ↑/↓ 1min · 9/0 volume · "
                 "> próxima · < anterior · q sair")


def pasta_musicas() -> Path:
    return Path(os.path.expanduser(cfg()["pasta_musicas"]))


def comando_ytdlp(alvo: str) -> list:
    """O comando pedido: melhor áudio, convertido para opus, com capa e metadados."""
    return ["yt-dlp", "-f", "bestaudio", "--extract-audio", "--audio-format", "opus",
            "--embed-thumbnail", "--add-metadata",
            "-o", str(pasta_musicas() / "%(title)s.%(ext)s"), alvo]


def garantir_deps_musica(com_player: bool = True) -> bool:
    """yt-dlp + ffmpeg (e, para música, mpv e mutagen)."""
    necessarios = [("yt-dlp", "python-yt-dlp"), ("ffmpeg", "ffmpeg")] + ([("mpv", "mpv")] if com_player else [])
    faltando = [pkg for cmd, pkg in necessarios if not tem(cmd)]
    if faltando:
        aviso("Faltam: " + ", ".join(faltando))
        if confirmar("Instalar agora?", True):
            if IS_TERMUX:
                instalar_pkg(*faltando, "yt-dlp-ejs")
                if not any(tem(js) for js in ("deno", "node", "bun")) and not instalar_pkg("deno"):
                    aviso("O YouTube pode exigir um runtime JavaScript: 'pkg install nodejs-lts' e "
                          "use a opção '--js-runtimes node' no yt-dlp.")
            elif "python-yt-dlp" in faltando:
                instalar_pip("yt-dlp")
    if not com_player:
        return tem("yt-dlp") and tem("ffmpeg")
    if not modulo_existe("mutagen"):
        info("O yt-dlp precisa do módulo 'mutagen' para embutir a capa em arquivos .opus.")
        if confirmar("Instalar mutagen?", True):
            instalar_pip("mutagen")
    return tem("yt-dlp") and tem("mpv")


def baixar_musica(alvo: str) -> bool:
    if not garantir_deps_musica():
        return False
    garantir_storage()
    pasta_musicas().mkdir(parents=True, exist_ok=True)
    return rodar(comando_ytdlp(alvo)).returncode == 0


def buscar_youtube(termo: str, n: int = 10) -> list:
    proc = rodar(["yt-dlp", "--flat-playlist", "--no-warnings", "--print",
                  "%(id)s\t%(title)s\t%(duration_string|?)s\t%(channel,uploader|?)s",
                  f"ytsearch{n}:{termo}"], capturar=True, timeout=120)
    resultados = []
    for linha in proc.stdout.splitlines():
        partes = linha.split("\t")
        if len(partes) == 4 and partes[0]:
            resultados.append({"id": partes[0], "titulo": partes[1], "duracao": partes[2], "canal": partes[3],
                               "url": f"https://www.youtube.com/watch?v={partes[0]}"})
    if not resultados:
        raise ToonsError("Nada encontrado. " + (proc.stderr or "").strip()[-300:])
    return resultados


def escolher_resultado(termo: str) -> dict | None:
    info(f"Buscando '{termo}' no YouTube...")
    resultados = buscar_youtube(termo)
    i = escolher("Qual?", [f"{r['titulo']} {DIM}[{r['duracao']}] {r['canal']}{RST}" for r in resultados], 1)
    return None if i is None else resultados[i]


def tocar_mpv(alvos: list, aleatorio: bool = False, playlist: Path | None = None,
              stream: bool = False, perguntar_fundo: bool = True) -> None:
    if not tem("mpv") and not garantir_deps_musica():
        return
    cmd = ["mpv", "--no-video", "--term-osd-bar"]
    if stream:
        cmd.append("--ytdl-format=bestaudio")
    if aleatorio:
        cmd.append("--shuffle")
    if playlist:
        cmd.append(f"--playlist={playlist}")
    cmd += [str(a) for a in alvos]
    if not alvos and not playlist:
        raise ToonsError("Nada para tocar.")
    if perguntar_fundo and confirmar("Tocar em segundo plano (continua tocando fora do menu)?", False):
        if servico_ativo("musica"):
            parar_servico("musica")
        if iniciar_servico("musica", shlex.join(cmd), com_log=False):
            info("Controle a música em 'Abrir player em segundo plano' (Ctrl+b d para sair).")
        return
    print(CONTROLES_MPV)
    rodar(cmd, mostrar=False)


def musicas_locais() -> list:
    pasta = pasta_musicas()
    if not pasta.exists():
        return []
    return sorted((p for p in pasta.rglob("*") if p.suffix.lower() in EXTENSOES_AUDIO),
                  key=lambda p: p.stat().st_mtime, reverse=True)


def _meta(pagina: str, nome: str) -> str:
    import html as html_mod
    for padrao in (rf'<meta[^>]+(?:property|name)="{nome}"[^>]+content="([^"]*)"',
                   rf'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="{nome}"'):
        achado = re.search(padrao, pagina)
        if achado:
            return html_mod.unescape(achado.group(1)).strip()
    return ""


def _spotify_busca(pagina: str) -> str:
    import html as html_mod
    t = re.search(r"<title>(.*?)</title>", pagina, re.S)
    if t:
        m = re.match(r"(.+?) - (?:song|música|canción)(?: and lyrics| e letra)? (?:by|de|por) (.+?) \| Spotify",
                     html_mod.unescape(t.group(1)).strip())
        if m:
            return f"{m.group(2)} - {m.group(1)}"
    titulo_musica = _meta(pagina, "og:title")
    descricao = _meta(pagina, "og:description")  # "Artista · Álbum · Música · 2020"
    if titulo_musica:
        artista = descricao.split("·")[0].strip() if "·" in descricao else ""
        return f"{artista} - {titulo_musica}".strip(" -")
    raise ToonsError("Não consegui ler o nome da música no Spotify.")


def spotify_para_buscas(url: str) -> list:
    """Converte link do Spotify (música, álbum ou playlist) em buscas 'Artista - Música'."""
    url = url.split("?")[0]
    status, pagina = baixar_pagina(url)
    if status >= 400:
        raise ToonsError(f"Spotify respondeu HTTP {status}.")
    if "/track/" in url:
        return [_spotify_busca(pagina)]
    faixas = list(dict.fromkeys(re.findall(r'content="(https://open\.spotify\.com/track/[A-Za-z0-9]+)"', pagina)))
    if not faixas:
        raise ToonsError("Nenhuma faixa encontrada na página (playlists privadas/dinâmicas não funcionam).")
    buscas = []
    for i, faixa in enumerate(faixas[:50], 1):
        print(f"\r  Lendo faixas do Spotify: {i}/{min(len(faixas), 50)}", end="", flush=True)
        try:
            buscas.append(_spotify_busca(baixar_pagina(faixa)[1]))
        except (ToonsError, OSError):
            pass
    print()
    return buscas


def baixar_alvo(alvo: str) -> None:
    """Baixa link do YouTube/SoundCloud/etc., link do Spotify ou termo de busca."""
    if "open.spotify.com/" in alvo:
        buscas = spotify_para_buscas(alvo)
        ok(f"{len(buscas)} música(s) encontrada(s). Procurando no YouTube...")
        for busca in buscas:
            info(busca)
            baixar_musica(f"ytsearch1:{busca} audio")
    elif alvo.startswith(("http://", "https://")):
        baixar_musica(alvo)
    else:
        baixar_musica(f"ytsearch1:{alvo}")


@submenu
def menu_musica():
    c = cfg()

    def buscar_tocar():
        r = escolher_resultado(perguntar("Música ou artista"))
        if r:
            tocar_mpv([r["url"]], stream=True)

    def buscar_baixar():
        r = escolher_resultado(perguntar("Música ou artista"))
        if r and baixar_musica(r["url"]):
            ok(f"Salvo em {pasta_musicas()}")

    def baixar_link():
        alvo = perguntar("Link (YouTube, YT Music, SoundCloud, playlist...)")
        if alvo:
            baixar_alvo(alvo)

    def baixar_spotify():
        url = perguntar("Link do Spotify (música, álbum ou playlist pública)")
        if url:
            baixar_alvo(url)

    def mix():
        termo = perguntar("Tocar mix de (artista, gênero, 'lofi'...)")
        if termo:
            tocar_mpv([f"ytdl://ytsearch15:{termo}"], stream=True)

    def biblioteca():
        musicas = musicas_locais()
        if not musicas:
            info(f"Nenhuma música em {pasta_musicas()}. Baixe algumas primeiro!")
            return
        sel = escolher_varios("Tocar quais?", [m.stem for m in musicas])
        if sel:
            tocar_mpv([musicas[i] for i in sel])

    def tudo_aleatorio():
        musicas = musicas_locais()
        if not musicas:
            info("Biblioteca vazia.")
            return
        tocar_mpv(musicas, aleatorio=True)

    def criar_playlist():
        musicas = musicas_locais()
        if not musicas:
            info("Biblioteca vazia.")
            return
        sel = escolher_varios("Músicas da playlist", [m.stem for m in musicas])
        if not sel:
            return
        nome = re.sub(r"[^\w\- ]", "_", perguntar("Nome da playlist", "favoritas")).strip() or "playlist"
        PLAYLISTS_DIR.mkdir(parents=True, exist_ok=True)
        arq = PLAYLISTS_DIR / f"{nome}.m3u"
        arq.write_text("#EXTM3U\n" + "".join(f"{musicas[i]}\n" for i in sel), "utf-8")
        ok(f"Playlist '{nome}' com {len(sel)} música(s).")

    def tocar_playlist():
        listas = sorted(PLAYLISTS_DIR.glob("*.m3u")) if PLAYLISTS_DIR.exists() else []
        if not listas:
            info("Nenhuma playlist criada.")
            return
        i = escolher("Playlist", [p.stem for p in listas], 1)
        if i is not None:
            tocar_mpv([], aleatorio=confirmar("Aleatório?", False), playlist=listas[i])

    def mudar_pasta():
        nova = perguntar("Pasta das músicas", c["pasta_musicas"])
        c["pasta_musicas"] = nova
        salvar_cfg()
        ok(f"Músicas em {pasta_musicas()}")

    menu("🎵 Música (yt-dlp + mpv)", [
        ("Buscar e tocar (streaming)", buscar_tocar),
        ("Buscar e baixar (melhor áudio, .opus com capa)", buscar_baixar),
        ("Baixar por link (YouTube, SoundCloud, playlist...)", baixar_link),
        ("Baixar do Spotify (link → busca no YouTube)", baixar_spotify),
        ("Tocar mix/rádio por busca", mix),
        ("Biblioteca: escolher e tocar", biblioteca),
        ("Biblioteca: tocar tudo no aleatório", tudo_aleatorio),
        ("Playlists: criar", criar_playlist),
        ("Playlists: tocar", tocar_playlist),
        ("Abrir player em segundo plano", lambda: abrir_sessao("musica")),
        ("Parar player em segundo plano", lambda: parar_servico("musica")),
        (lambda: f"Pasta das músicas ({c['pasta_musicas']})", mudar_pasta),
        ("Instalar dependências (yt-dlp, ffmpeg, mpv, mutagen)", garantir_deps_musica),
    ])


# ════════════════════════════════════════════════════════════════════
#  13. Vídeos: TikTok, YouTube e outros sites suportados pelo yt-dlp
# ════════════════════════════════════════════════════════════════════

EXTENSOES_VIDEO = {".mp4", ".webm", ".mkv", ".mov", ".m4v"}


def pasta_videos() -> Path:
    return Path(os.path.expanduser(cfg()["pasta_videos"]))


def comando_video(alvo: str) -> list:
    """O comando pedido: melhor vídeo + melhor áudio (ou o melhor arquivo único).
    --trim-filenames evita o erro de nome longo demais com legendas do TikTok."""
    return ["yt-dlp", "-f", "bv*+ba/best", "--trim-filenames", "150",
            "-o", str(pasta_videos() / "%(title)s.%(ext)s"), alvo]


def baixar_video(alvo: str) -> bool:
    """Baixa um link (TikTok, YouTube, Shorts, playlist...) ou o 1º resultado de uma busca."""
    if not garantir_deps_musica(com_player=False):
        return False
    garantir_storage()
    pasta_videos().mkdir(parents=True, exist_ok=True)
    if not alvo.startswith(("http://", "https://")):
        alvo = f"ytsearch1:{alvo}"
    return rodar(comando_video(alvo)).returncode == 0


def videos_locais() -> list:
    pasta = pasta_videos()
    if not pasta.exists():
        return []
    return sorted((p for p in pasta.rglob("*") if p.suffix.lower() in EXTENSOES_VIDEO),
                  key=lambda p: p.stat().st_mtime, reverse=True)


@submenu
def menu_videos():
    c = cfg()

    def por_link():
        info("Cole um ou mais links separados por espaço (TikTok, YouTube, Shorts, playlist...).")
        links = perguntar("Link(s)").split()
        baixados = sum(baixar_video(link) for link in links)
        if links:
            (ok if baixados == len(links) else aviso)(f"{baixados} de {len(links)} vídeo(s) baixado(s) em {pasta_videos()}")

    def buscar_baixar():
        termo = perguntar("Buscar no YouTube")
        if not termo or not garantir_deps_musica(com_player=False):
            return
        r = escolher_resultado(termo)
        if r and baixar_video(r["url"]):
            ok(f"Salvo em {pasta_videos()}")

    def abrir():
        videos = videos_locais()
        if not videos:
            info(f"Nenhum vídeo em {pasta_videos()}.")
            return
        i = escolher("Qual vídeo?", [f"{v.name} ({bytes_humanos(v.stat().st_size)})" for v in videos])
        if i is None:
            return
        if tem("termux-open"):
            rodar(["termux-open", videos[i]])  # abre no player de vídeo do Android
        else:
            info(f"Arquivo: {videos[i]}")

    def mudar_pasta():
        c["pasta_videos"] = perguntar("Pasta dos vídeos", c["pasta_videos"])
        salvar_cfg()
        ok(f"Vídeos em {pasta_videos()}")

    menu("🎬 Vídeos (TikTok, YouTube...)", [
        ("Baixar por link (TikTok, YouTube, Shorts, playlist...)", por_link),
        ("Buscar no YouTube e baixar", buscar_baixar),
        ("Abrir vídeo baixado no player do Android", abrir),
        (lambda: f"Pasta dos vídeos ({c['pasta_videos']})", mudar_pasta),
        ("Instalar dependências (yt-dlp, ffmpeg)", lambda: garantir_deps_musica(com_player=False)),
    ])


# ════════════════════════════════════════════════════════════════════
#  14. Atualização
# ════════════════════════════════════════════════════════════════════

REPO_TOONS = "https://github.com/Gustavo-HVF/Termux-Toons"


def atualizar_termux() -> None:
    if not IS_TERMUX:
        aviso("Isto só funciona dentro do Termux.")
        return
    rodar(["pkg", "upgrade", "-y"])


def atualizar_pip() -> None:
    candidatos = {"rich": "rich", "flask": "flask", "fastapi": "fastapi", "uvicorn": "uvicorn",
                  "discord": "discord.py", "textual": "textual", "mutagen": "mutagen", "yt_dlp": "yt-dlp"}
    instalados = [pip for mod, pip in candidatos.items() if modulo_existe(mod)]
    if "yt-dlp" in instalados and IS_TERMUX and rodar(["dpkg", "-s", "python-yt-dlp"], capturar=True,
                                                       mostrar=False).returncode == 0:
        instalados.remove("yt-dlp")  # veio do pkg: o 'pkg upgrade' cuida dele
    if not instalados:
        info("Nenhum pacote Python opcional instalado.")
        return
    instalar_pip(*instalados)


def atualizar_gits() -> None:
    raiz = Path(os.path.expanduser(perguntar("Pasta onde procurar repositórios git", str(HOME))))
    repos = ([raiz] if (raiz / ".git").exists() else []) + sorted(p.parent for p in raiz.glob("*/.git"))
    if not repos:
        info("Nenhum repositório encontrado.")
        return
    for repo in repos:
        print(f"\n{NEG}{repo}{RST}")
        rodar(["git", "-C", repo, "pull", "--ff-only"])


def atualizar_toons() -> None:
    if (SCRIPT.parent / ".git").exists() and tem("git"):
        if rodar(["git", "-C", SCRIPT.parent, "pull", "--ff-only"]).returncode == 0:
            ok("Termux-Toons atualizado. Reabra o programa para usar a versão nova.")
    else:
        info(f"Este arquivo não está num clone git. Para atualizar:\n  git clone {REPO_TOONS}")


def ativar_repos() -> None:
    repos = {"x11-repo": "programas gráficos (X11)",
             "root-repo": "ferramentas que usam root (tcpdump...)",
             "tur-repo": "Termux User Repository (code-server e outros)"}
    escolhidos = [r for r, desc in repos.items() if confirmar(f"Ativar {r} — {desc}?", False)]
    if escolhidos and instalar_pkg(*escolhidos):
        rodar(["pkg", "update", "-y"])


def limpar_cache() -> None:
    if IS_TERMUX:
        rodar(["pkg", "clean"])
        rodar(["apt", "autoremove", "-y"])
    rodar([sys.executable, "-m", "pip", "cache", "purge"])


def atualizar_tudo() -> None:
    atualizar_termux()
    atualizar_pip()
    atualizar_distros()
    atualizar_toons()
    ok("Tudo atualizado.")


@submenu
def menu_atualizar():
    menu("🔄 Atualização", [
        ("Atualizar o Termux (pkg upgrade)", atualizar_termux),
        ("Trocar o espelho dos repositórios (termux-change-repo)", lambda: rodar(["termux-change-repo"])),
        ("Ativar repositórios extras (x11, root, tur)", ativar_repos),
        ("Atualizar pacotes Python opcionais (pip)", atualizar_pip),
        ("Atualizar e recompilar o llama.cpp", compilar_llama),
        ("Atualizar as distros do proot-distro", atualizar_distros),
        ("Atualizar repositórios git de uma pasta (git pull)", atualizar_gits),
        ("Atualizar o Termux-Toons", atualizar_toons),
        ("Limpar cache de pacotes", limpar_cache),
        ("Atualizar TUDO (Termux, pip, distros, Termux-Toons)", atualizar_tudo),
    ])


# ════════════════════════════════════════════════════════════════════
#  15. Otimização e limpeza
# ════════════════════════════════════════════════════════════════════

_ROOT: bool | None = None


def tem_root() -> bool:
    """True se o 'su' existe e devolve uid 0 (pergunta ao Magisk/KernelSU só uma vez)."""
    global _ROOT
    if _ROOT is None:
        _ROOT = tem("su") and saida(["su", "-c", "id -u"], timeout=20) == "0"
    return _ROOT


def tamanho(caminho: Path) -> int:
    """Tamanho em bytes; pastas são somadas sem seguir links simbólicos."""
    try:
        if caminho.is_symlink() or caminho.is_file():
            return caminho.lstat().st_size
        if not caminho.is_dir():
            return 0
    except OSError:
        return 0
    total = 0
    for raiz, _, arquivos in os.walk(caminho, onerror=lambda e: None):
        for nome in arquivos:
            with contextlib.suppress(OSError):
                total += os.lstat(os.path.join(raiz, nome)).st_size
    return total


def apagar(caminho: Path) -> int:
    """Apaga arquivo ou pasta e devolve quantos bytes foram liberados."""
    liberado = tamanho(caminho)
    try:
        if caminho.is_symlink() or caminho.is_file():
            caminho.unlink()
        elif caminho.is_dir():
            shutil.rmtree(caminho, ignore_errors=True)
    except OSError as e:
        aviso(f"Não consegui apagar {caminho}: {e}")
        return 0
    return liberado


def _arquivos_tmp_antigos() -> list:
    """Arquivos em $PREFIX/tmp com mais de 2 dias (sem mexer nos sockets do tmux)."""
    tmp = Path(PREFIX) / "tmp"
    if not PREFIX or not tmp.is_dir():
        return []
    limite, achados = time.time() - 2 * 86400, []
    for raiz, pastas, arquivos in os.walk(tmp):
        pastas[:] = [p for p in pastas if not p.startswith("tmux")]
        for nome in arquivos:
            arq = Path(raiz) / nome
            with contextlib.suppress(OSError):
                if arq.is_file() and not arq.is_symlink() and arq.stat().st_mtime < limite:
                    achados.append(arq)
    return achados


def _pycaches() -> list:
    achados = []
    for raiz, pastas, _ in os.walk(HOME):
        pastas[:] = [p for p in pastas if p not in ("storage", ".git", "node_modules")]
        if "__pycache__" in pastas:
            achados.append(Path(raiz) / "__pycache__")
            pastas.remove("__pycache__")
    return achados


def _sobras_toons() -> list:
    """Logs antigos, logs de serviços parados e fotos temporárias do Termux-Toons."""
    ativos = set(servicos_ativos())
    itens = list(LOG_DIR.glob("*.log.old")) if LOG_DIR.exists() else []
    if LOG_DIR.exists():
        itens += [p for p in LOG_DIR.glob("*.log") if p.stem not in ativos]
    itens += list(DATA_DIR.glob("foto_*.jpg"))
    if (DATA_DIR / "teste_dev").exists():
        itens.append(DATA_DIR / "teste_dev")
    return itens


def _downloads_incompletos() -> list:
    if not DOWNLOADS.exists():
        return []
    return [p for p in DOWNLOADS.rglob("*") if p.suffix in (".part", ".ytdl", ".temp") and p.is_file()]


def _miniaturas() -> list:
    base = HOME / "storage" / "shared"
    return [base / sub / ".thumbnails" for sub in ("DCIM", "Pictures", "Movies")
            if (base / sub / ".thumbnails").is_dir()]


def _limpador_lista(obter) -> dict:
    """Limpador a partir de uma função que devolve a lista de caminhos a apagar."""
    return {"estimar": lambda: sum(tamanho(p) for p in obter()),
            "limpar": lambda: sum(apagar(p) for p in obter())}


def _limpador_apt() -> dict:
    cache = Path(PREFIX) / "var" / "cache" / "apt"

    def limpar():
        antes = tamanho(cache)
        rodar(["apt", "clean"], capturar=True)
        return max(0, antes - tamanho(cache))

    return {"estimar": lambda: tamanho(cache) if IS_TERMUX else None, "limpar": limpar}


LIMPADORES = [
    # (rótulo, fábrica do limpador, entra na limpeza rápida?)
    ("Cache de pacotes do Termux (apt)", _limpador_apt, True),
    ("Cache geral ~/.cache (pip, yt-dlp, go...)",
     lambda: _limpador_lista(lambda: list((HOME / ".cache").iterdir()) if (HOME / ".cache").is_dir() else []), True),
    ("Cache do npm (~/.npm/_cacache)",
     lambda: _limpador_lista(lambda: [HOME / ".npm" / "_cacache"] if (HOME / ".npm" / "_cacache").exists() else []),
     True),
    ("Arquivos temporários antigos ($PREFIX/tmp)", lambda: _limpador_lista(_arquivos_tmp_antigos), True),
    ("Pastas __pycache__ na home", lambda: _limpador_lista(_pycaches), True),
    ("Logs antigos e fotos temporárias do Termux-Toons", lambda: _limpador_lista(_sobras_toons), True),
    ("Miniaturas da galeria (.thumbnails, o Android recria)", lambda: _limpador_lista(_miniaturas), True),
    ("Downloads incompletos (.part, .ytdl) em Downloads", lambda: _limpador_lista(_downloads_incompletos), False),
    ("Build do llama.cpp (precisa recompilar depois)",
     lambda: _limpador_lista(lambda: [LLAMA_DIR / "build"] if (LLAMA_DIR / "build").exists() else []), False),
]


def _estimar_limpadores(so_rapidos: bool = False) -> list:
    """[(rótulo, limpador, bytes)] dos limpadores que se aplicam a este aparelho."""
    resultado = []
    for rotulo, fabrica, rapido in LIMPADORES:
        if so_rapidos and not rapido:
            continue
        limpador = fabrica()
        estimado = limpador["estimar"]()
        if estimado is not None:
            resultado.append((rotulo, limpador, estimado))
    return resultado


def limpar_cache_apps_root() -> int:
    """Pede ao Android para limpar o cache de todos os apps (pm trim-caches, precisa de root)."""
    antes = shutil.disk_usage(HOME).free
    rodar(["su", "-c", "pm trim-caches 999G"])
    return max(0, shutil.disk_usage(HOME).free - antes)


def otimizacao_rapida(interativo: bool = True) -> None:
    info("Analisando o que dá para limpar com segurança...")
    total = 0
    for rotulo, limpador, estimado in _estimar_limpadores(so_rapidos=True):
        if not estimado:
            continue
        liberado = limpador["limpar"]()
        total += liberado
        ok(f"{rotulo}: {bytes_humanos(liberado)}")
    if tem_root():
        if not interativo or confirmar("Limpar também o cache de TODOS os apps (root)?", True):
            liberado = limpar_cache_apps_root()
            total += liberado
            ok(f"Cache de todos os apps: {bytes_humanos(liberado)}")
    elif interativo:
        info("Sem root, o cache dos outros apps só pode ser limpo pela tela de armazenamento do Android "
             "(opção 'Limpar cache de todos os apps' neste menu).")
    print(f"\n{NEG}Total liberado: {bytes_humanos(total)}{RST} · "
          f"livre agora: {bytes_humanos(shutil.disk_usage(HOME).free)}")


def _abrir_tela_android(acao: str, dado: str | None = None) -> bool:
    """Abre uma tela de configurações do Android (o 'am' do Termux funciona sem root)."""
    if not tem("am"):
        aviso("Comando 'am' não encontrado (só existe dentro do Termux).")
        return False
    cmd = ["am", "start", "-a", acao] + (["-d", dado] if dado else [])
    return rodar(cmd, capturar=True, timeout=20).returncode == 0


TELAS_ANDROID = [
    ("Liberar espaço (limpeza do próprio Android)", "android.os.storage.action.MANAGE_STORAGE"),
    ("Armazenamento (cache e dados por categoria)", "android.settings.INTERNAL_STORAGE_SETTINGS"),
    ("Lista de apps (limpar cache app por app)", "android.settings.MANAGE_APPLICATIONS_SETTINGS"),
    ("Otimização de bateria (deixe o Termux sem restrição)", "android.settings.IGNORE_BATTERY_OPTIMIZATION_SETTINGS"),
    ("Economia de bateria", "android.settings.BATTERY_SAVER_SETTINGS"),
    ("Uso de bateria por app", "android.intent.action.POWER_USAGE_SUMMARY"),
]


def _escolher_pasta(msg: str = "Onde procurar?"):
    opcoes = [("Downloads", DOWNLOADS), ("Armazenamento interno (tudo)", HOME / "storage" / "shared"),
              ("Home do Termux", HOME), ("Outra pasta...", None)]
    disponiveis = [(nome, p) for nome, p in opcoes if p is None or p.exists()]
    i = escolher(msg, [nome for nome, _ in disponiveis])
    if i is None:
        return None
    pasta = disponiveis[i][1]
    if pasta is None:
        pasta = Path(os.path.expanduser(perguntar("Caminho da pasta", str(HOME))))
    if not pasta.is_dir():
        raise ToonsError(f"Pasta não encontrada: {pasta}")
    return pasta


def _arquivos(pasta: Path):
    """Todos os arquivos comuns abaixo de `pasta`, ignorando o que não dá para ler."""
    for raiz, _, nomes in os.walk(pasta, onerror=lambda e: None):
        for nome in nomes:
            caminho = Path(raiz) / nome
            with contextlib.suppress(OSError):
                if caminho.is_file() and not caminho.is_symlink():
                    yield caminho, caminho.stat()


def _hash_arquivo(caminho: Path, limite: int | None = None) -> str:
    h = hashlib.sha1()
    lido = 0
    with open(caminho, "rb") as arq:
        while bloco := arq.read(1 << 20):
            h.update(bloco)
            lido += len(bloco)
            if limite and lido >= limite:
                break
    return h.hexdigest()


@submenu
def menu_otimizacao():
    def rapida():
        otimizacao_rapida()

    def escolher_limpeza():
        info("Calculando o tamanho de cada item...")
        candidatos = [c for c in _estimar_limpadores() if c[2] > 0]
        if not candidatos:
            ok("Nada para limpar. 🎉")
            return
        sel = escolher_varios("O que limpar?", [f"{r} — {bytes_humanos(t)}" for r, _, t in candidatos])
        total = 0
        for i in sel:
            rotulo, limpador, _ = candidatos[i]
            liberado = limpador["limpar"]()
            total += liberado
            ok(f"{rotulo}: {bytes_humanos(liberado)}")
        if sel:
            print(f"\n{NEG}Total liberado: {bytes_humanos(total)}{RST}")

    def cache_todos_apps():
        if tem_root():
            info("Pedindo ao Android para limpar o cache de todos os apps...")
            ok(f"Liberado: {bytes_humanos(limpar_cache_apps_root())}")
            return
        aviso("Sem root, o Android não permite que o Termux limpe o cache de outros apps.")
        info("Vou abrir a tela de armazenamento do Android: lá você limpa o cache (ou use 'Liberar espaço').")
        if not _abrir_tela_android("android.os.storage.action.MANAGE_STORAGE"):
            _abrir_tela_android("android.settings.INTERNAL_STORAGE_SETTINGS")

    def otimizar_apps_root():
        if not tem_root():
            raise ToonsError("Precisa de root. Sem root, o Android faz isso sozinho quando o aparelho "
                             "fica carregando e parado.")
        info("Compilando os apps em segundo plano (pode levar vários minutos, deixe carregando)...")
        rodar(["su", "-c", "cmd package bg-dexopt-job"])
        ok("Otimização dos apps concluída.")

    def trim_root():
        if not tem_root():
            raise ToonsError("Precisa de root. Sem root, o Android roda o TRIM sozinho durante a "
                             "manutenção noturna (carregando e com a tela desligada).")
        rodar(["su", "-c", "sm fstrim"])
        ok("TRIM solicitado ao armazenamento.")

    def espaco():
        pasta = _escolher_pasta("Analisar qual pasta?")
        if not pasta:
            return
        info(f"Somando {pasta} ...")
        try:
            filhos = list(pasta.iterdir())
        except OSError as e:
            raise ToonsError(f"Sem acesso a {pasta}: {e}") from None
        tamanhos = sorted(((tamanho(f), f) for f in filhos), reverse=True)
        total = sum(t for t, _ in tamanhos) or 1
        print(f"\n{NEG}{pasta}{RST} — {bytes_humanos(total)}")
        for t, f in tamanhos[:20]:
            nome = f.name + ("/" if f.is_dir() and not f.is_symlink() else "")
            print(f"  {_barra(t / total, 12)} {bytes_humanos(t):>9}  {nome}")
        livre = shutil.disk_usage(pasta)
        print(f"\nDisco: {bytes_humanos(livre.free)} livres de {bytes_humanos(livre.total)}")

    def grandes():
        pasta = _escolher_pasta()
        if not pasta:
            return
        minimo = perguntar_int("Tamanho mínimo (MB)", 100, 1)
        info("Procurando...")
        achados = sorted(((st.st_size, p) for p, st in _arquivos(pasta) if st.st_size >= minimo * 1024 * 1024),
                         reverse=True)[:40]
        if not achados:
            ok(f"Nenhum arquivo com mais de {minimo} MB.")
            return
        sel = escolher_varios("Marque os que quer APAGAR",
                              [f"{bytes_humanos(t):>9}  {p.relative_to(pasta)}" for t, p in achados])
        escolhidos = [achados[i] for i in sel]
        if escolhidos and confirmar(f"Apagar {len(escolhidos)} arquivo(s) "
                                    f"({bytes_humanos(sum(t for t, _ in escolhidos))})?"):
            ok(f"Liberado: {bytes_humanos(sum(apagar(p) for _, p in escolhidos))}")

    def duplicados():
        pasta = _escolher_pasta()
        if not pasta:
            return
        info("Procurando arquivos com o mesmo conteúdo...")
        por_tamanho = {}
        for p, st in _arquivos(pasta):
            if st.st_size >= 1024:
                por_tamanho.setdefault(st.st_size, []).append((st.st_mtime, p))
        grupos = []
        for t, lista in por_tamanho.items():
            if len(lista) < 2:
                continue
            por_hash = {}
            for mtime, p in lista:
                with contextlib.suppress(OSError):
                    chave = (_hash_arquivo(p, 65536), _hash_arquivo(p) if t > 65536 else "")
                    por_hash.setdefault(chave, []).append((mtime, p))
            grupos += [(t, sorted(g)) for g in por_hash.values() if len(g) > 1]
        if not grupos:
            ok("Nenhum arquivo duplicado encontrado.")
            return
        sobras = [(t, p) for t, g in grupos for _, p in g[1:]]  # mantém o mais antigo de cada grupo
        for t, g in sorted(grupos, reverse=True)[:15]:
            print(f"{NEG}{bytes_humanos(t)}{RST} × {len(g)}")
            for i, (_, p) in enumerate(g):
                print(f"   {'mantém' if i == 0 else 'cópia '}  {p.relative_to(pasta)}")
        if len(grupos) > 15:
            print(f"{DIM}... e mais {len(grupos) - 15} grupo(s){RST}")
        espaco_dup = sum(t for t, _ in sobras)
        if confirmar(f"Apagar {len(sobras)} cópia(s) e liberar {bytes_humanos(espaco_dup)}? "
                     "(fica o arquivo mais antigo de cada grupo)"):
            ok(f"Liberado: {bytes_humanos(sum(apagar(p) for _, p in sobras))}")

    def pastas_vazias():
        pasta = _escolher_pasta()
        if not pasta:
            return
        vazias = set()
        # De baixo para cima: uma pasta é vazia se não tem arquivos e só tem subpastas vazias.
        for raiz, pastas, arquivos in os.walk(pasta, topdown=False, onerror=lambda e: None):
            atual = Path(raiz)
            if atual != pasta and not arquivos and all(atual / d in vazias for d in pastas):
                vazias.add(atual)
        if not vazias:
            ok("Nenhuma pasta vazia.")
            return
        for p in sorted(vazias)[:20]:
            print(f"   {p.relative_to(pasta)}")
        if confirmar(f"Remover {len(vazias)} pasta(s) vazia(s)?"):
            removidas = 0
            for p in sorted(vazias, key=lambda x: len(x.parts), reverse=True):
                with contextlib.suppress(OSError):
                    p.rmdir()
                    removidas += 1
            ok(f"{removidas} pasta(s) removida(s).")

    def processos():
        lista = []
        for pid_dir in Path("/proc").iterdir():
            if not pid_dir.name.isdigit() or int(pid_dir.name) == os.getpid():
                continue
            with contextlib.suppress(OSError, ValueError, IndexError):
                campos = dict(linha.split(":", 1) for linha in (pid_dir / "status").read_text().splitlines()
                              if ":" in linha)
                rss = int(campos.get("VmRSS", "0 kB").split()[0]) * 1024
                if rss:
                    cmdline = (pid_dir / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
                    lista.append((rss, int(pid_dir.name), cmdline.strip() or campos["Name"].strip()))
        if not lista:
            info("Nenhum processo visível (o Android só mostra os do próprio Termux).")
            return
        lista.sort(reverse=True)
        print(f"{DIM}O Android só deixa ver os processos do próprio Termux.{RST}")
        i = escolher("Escolha um para encerrar (Esc para só olhar)",
                     [f"{bytes_humanos(rss):>9}  {pid:<6} {cmd[:60]}" for rss, pid, cmd in lista[:25]])
        if i is not None:
            rss, pid, cmd = lista[i]
            if confirmar(f"Encerrar o processo {pid} ({cmd[:40]})?"):
                try:
                    os.kill(pid, 15)
                    ok("Sinal de encerramento enviado.")
                except OSError as e:
                    erro(f"Não consegui encerrar: {e}")

    def parar_tudo():
        ativos = servicos_ativos()
        if not ativos:
            info("Nenhum serviço do Termux-Toons rodando.")
            return
        if confirmar(f"Parar {', '.join(ativos)}?", True):
            for nome in ativos:
                parar_servico(nome)

    def telas():
        i = escolher("Abrir qual tela do Android?", [nome for nome, _ in TELAS_ANDROID])
        if i is not None and _abrir_tela_android(TELAS_ANDROID[i][1]):
            ok("Tela aberta no Android.")

    menu("🧹 Otimização e limpeza", [
        ("⚡ Otimização rápida (limpa tudo que é seguro)", rapida),
        ("Escolher o que limpar (mostra o tamanho de cada item)", escolher_limpeza),
        ("Limpar cache de TODOS os apps", cache_todos_apps),
        ("Ver o que ocupa espaço", espaco),
        ("Arquivos grandes", grandes),
        ("Arquivos duplicados", duplicados),
        ("Pastas vazias", pastas_vazias),
        ("Processos do Termux que mais usam RAM", processos),
        ("Parar todos os serviços do Termux-Toons", parar_tudo),
        ("Otimizar apps — compilação em segundo plano (root)", otimizar_apps_root),
        ("TRIM do armazenamento (root)", trim_root),
        ("Atalhos para telas do Android (armazenamento, bateria...)", telas),
    ])


# ════════════════════════════════════════════════════════════════════
#  Configurações e diagnóstico
# ════════════════════════════════════════════════════════════════════

@submenu
def menu_config():
    c = cfg()

    def mostrar():
        for chave, valor in c.items():
            if chave == "monitores":
                valor = f"{len(valor)} monitor(es)"
            elif chave.endswith("token"):
                valor = mascarar(valor)
            print(f"  {CIANO}{chave:<24}{RST} {valor}")
        print(f"\nArquivo: {CONFIG_FILE}")

    def shell_bots():
        if not c["bot_permitir_shell"]:
            aviso("Com isso, quem estiver na lista de IDs permitidos poderá rodar QUALQUER comando no celular.")
        c["bot_permitir_shell"] = confirmar("Permitir o comando sh nos bots?", c["bot_permitir_shell"])
        salvar_cfg()

    def tts_idioma():
        c["tts_idioma"] = perguntar("Idioma do TTS (pt, en, es...; vazio = padrão do Android)", c["tts_idioma"])
        salvar_cfg()

    def editar_json():
        editor = os.environ.get("EDITOR") or next((e for e in ("nvim", "nano", "vi") if tem(e)), None)
        if not editor:
            raise ToonsError("Nenhum editor encontrado (pkg install nano).")
        salvar_cfg()
        rodar([editor, CONFIG_FILE])
        novo = ler_json(CONFIG_FILE, {})
        c.clear()
        c.update({**copy.deepcopy(PADRAO_CFG), **novo})
        ok("Configuração recarregada.")

    def resetar():
        if confirmar("Apagar TODAS as configurações (tokens, monitores...)?"):
            c.clear()
            c.update(copy.deepcopy(PADRAO_CFG))
            c["api_token"] = secrets.token_urlsafe(24)
            salvar_cfg()
            ok("Configurações zeradas.")

    menu("⚙️ Configurações", [
        ("Ver configuração atual", mostrar),
        ("Tokens e IDs dos bots (Telegram/Discord)", menu_bots),
        (lambda: f"Comando sh nos bots ({'permitido' if c['bot_permitir_shell'] else 'bloqueado'})", shell_bots),
        (lambda: f"Idioma do TTS ({c['tts_idioma'] or 'padrão'})", tts_idioma),
        ("Editar config.json no editor", editar_json),
        ("Zerar configurações", resetar),
    ])


FERRAMENTAS = [
    ("tmux", "tmux", "serviços 24h"), ("termux-wake-lock", "termux-tools", "manter acordado"),
    ("termux-battery-status", "termux-api", "Termux:API"), ("git", "git", "dev / atualização"),
    ("nvim", "neovim", "editor"), ("clang", "clang", "C/C++ e llama.cpp"), ("cmake", "cmake", "llama.cpp"),
    ("yt-dlp", "python-yt-dlp", "música"), ("ffmpeg", "ffmpeg", "música"), ("mpv", "mpv", "música"),
    ("nmap", "nmap", "rede"), ("sshd", "openssh", "SSH"), ("wg", "wireguard-tools", "WireGuard"),
    ("cloudflared", "cloudflared", "túnel"), ("proot-distro", "proot-distro", "Linux"),
    ("rclone", "rclone", "nuvem"), ("syncthing", "syncthing", "sincronização"),
]
MODULOS_OPCIONAIS = [("rich", "dashboard"), ("flask", "servidor web"), ("fastapi", "servidor web"),
                     ("uvicorn", "servidor web"), ("discord", "bot Discord"), ("mutagen", "capas de música"),
                     ("textual", "apps TUI")]


def diagnostico() -> None:
    print(f"Termux-Toons {VERSION} · Python {platform.python_version()} · "
          f"{'Termux ' + os.environ.get('TERMUX_VERSION', '') if IS_TERMUX else 'fora do Termux'}")
    print(f"Armazenamento (~/storage): {'ok' if (HOME / 'storage').exists() else 'sem acesso (termux-setup-storage)'}")
    print(f"\n{NEG}Programas{RST}")
    for cmd, pacote, uso in FERRAMENTAS:
        marca = f"{VERD}✔{RST}" if tem(cmd) else f"{VERM}✖{RST}"
        print(f"  {marca} {cmd:<22} {DIM}{uso} · pkg install {pacote}{RST}")
    marca = f"{VERD}✔{RST}" if llama_bin("llama-cli") else f"{VERM}✖{RST}"
    print(f"  {marca} {'llama-cli':<22} {DIM}LLM · compile pelo menu{RST}")
    print(f"\n{NEG}Módulos Python opcionais{RST}")
    for mod, uso in MODULOS_OPCIONAIS:
        print(f"  {VERD + '✔' if modulo_existe(mod) else VERM + '✖'}{RST} {mod:<22} {DIM}{uso}{RST}")
    if tem("termux-battery-status"):
        try:
            bateria()
            ok("App Termux:API respondendo.")
        except ToonsError as e:
            aviso(str(e))
    print(f"\nServiços ativos: {', '.join(servicos_ativos()) or 'nenhum'}")


def instalar_essenciais() -> None:
    if not IS_TERMUX:
        aviso("Fora do Termux: instale python3, tmux e git pelo gerenciador do seu sistema.")
        return
    rodar(["pkg", "update", "-y"])
    instalar_pkg("python", "tmux", "termux-api", "git", "curl", "nano")
    garantir_storage()
    instalar_pip("rich")
    info("Instale também o app Termux:API (F-Droid) para sensores, SMS, câmera etc.")
    ok("Essenciais instalados.")


# ════════════════════════════════════════════════════════════════════
#  Menu principal e linha de comando
# ════════════════════════════════════════════════════════════════════

BANNER = [
    "╔╦╗╔═╗╦═╗╔╦╗╦ ╦═╗ ╦  ╔╦╗╔═╗╔═╗╔╗╔╔═╗",
    " ║ ║╣ ╠╦╝║║║║ ║╔╩╦╝   ║ ║ ║║ ║║║║╚═╗",
    " ╩ ╚═╝╩╚═╩ ╩╚═╝╩ ╚═   ╩ ╚═╝╚═╝╝╚╝╚═╝",
]


def cabecalho() -> None:
    for linha in BANNER:
        print(f"{MAG}{linha}{RST}")
    ambiente = "Termux" if IS_TERMUX else "fora do Termux"
    print(f"{DIM}v{VERSION} · {ambiente} · serviços: {', '.join(servicos_ativos()) or 'nenhum'}{RST}")


def menu_principal() -> None:
    menu("Menu principal", [
        ("🌐 Servidor web / API pessoal", menu_web),
        ("🤖 Bots Telegram / Discord 24h", menu_bots),
        ("📱 Automação com Termux:API", menu_termux_api),
        ("🧠 LLMs locais (llama.cpp)", menu_llm),
        ("📊 Interfaces TUI (dashboard, tarefas)", menu_tui),
        ("💻 Ambiente de desenvolvimento", menu_dev),
        ("🔎 Scraping e monitoramento", menu_monitor),
        ("🛡️ Rede e segurança", menu_rede),
        ("👾 Retro: jogos e BASIC", menu_retro),
        ("🐧 Linux de verdade (proot-distro)", menu_proot),
        ("🗄️ Arquivos e backup", menu_arquivos),
        ("🎵 Música (yt-dlp + mpv)", menu_musica),
        ("🎬 Vídeos (TikTok, YouTube)", menu_videos),
        ("🔄 Atualização", menu_atualizar),
        ("🧹 Otimização e limpeza", menu_otimizacao),
        ("⚙️ Configurações", menu_config),
        ("🩺 Diagnóstico", diagnostico),
        ("📦 Instalar essenciais (python, tmux, termux-api, git)", instalar_essenciais),
    ], sair="Sair", cabecalho=cabecalho)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="termux_toons.py",
        description="Termux-Toons: canivete suíço para o Termux. Sem argumentos abre o menu.")
    sub = parser.add_subparsers(dest="comando", metavar="COMANDO")
    p = sub.add_parser("serve", help="sobe o servidor web/API em primeiro plano")
    p.add_argument("--framework", choices=list(DEPENDENCIAS_WEB))
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--porta", type=int)
    p = sub.add_parser("bot", help="roda um bot em primeiro plano")
    p.add_argument("tipo", choices=["telegram", "discord"])
    p = sub.add_parser("monitor", help="roda os monitores de scraping")
    p.add_argument("--uma-vez", action="store_true", help="checa tudo uma vez e sai")
    sub.add_parser("dashboard", help="dashboard do sistema")
    sub.add_parser("tarefas", help="gerenciador de tarefas")
    sub.add_parser("snake", help="jogo da cobrinha")
    p = sub.add_parser("basic", help="interpretador BASIC")
    p.add_argument("arquivo", nargs="?", help="programa .bas para rodar")
    p = sub.add_parser("baixar", help="baixa áudio (link do YouTube/Spotify ou termo de busca)")
    p.add_argument("alvos", nargs="+")
    p = sub.add_parser("video", help="baixa vídeos (links do TikTok/YouTube ou termo de busca)")
    p.add_argument("alvos", nargs="+")
    p = sub.add_parser("tocar", help="toca a biblioteca (sem argumentos) ou um mix por busca")
    p.add_argument("busca", nargs="*")
    sub.add_parser("atualizar", help="atualiza Termux, pacotes Python, distros e o Termux-Toons")
    sub.add_parser("limpar", help="otimização rápida: limpa caches e temporários com segurança")
    sub.add_parser("doctor", help="diagnóstico do ambiente")
    args = parser.parse_args(argv)

    try:
        if args.comando is None:
            menu_principal()
            print("Até mais! 👋")
        elif args.comando == "serve":
            c = cfg()
            servir(args.framework or c["web_framework"], args.host, args.porta or c["web_porta"])
        elif args.comando == "bot":
            executar_bot(args.tipo)
        elif args.comando == "monitor":
            rodar_monitores(args.uma_vez)
        elif args.comando == "dashboard":
            dashboard()
        elif args.comando == "tarefas":
            tarefas_tui()
        elif args.comando == "snake":
            snake()
        elif args.comando == "basic":
            interpretador = Basic()
            if args.arquivo:
                interpretador.carregar(Path(args.arquivo))
                interpretador.run()
            else:
                interpretador.repl()
        elif args.comando == "baixar":
            for alvo in args.alvos:
                baixar_alvo(alvo)
        elif args.comando == "video":
            falhas = sum(not baixar_video(alvo) for alvo in args.alvos)
            if falhas:
                raise ToonsError(f"{falhas} download(s) falharam.")
        elif args.comando == "tocar":
            if args.busca:
                tocar_mpv([f"ytdl://ytsearch15:{' '.join(args.busca)}"], stream=True, perguntar_fundo=False)
            else:
                tocar_mpv(musicas_locais(), aleatorio=True, perguntar_fundo=False)
        elif args.comando == "limpar":
            otimizacao_rapida(interativo=False)
        elif args.comando == "atualizar":
            atualizar_tudo()
        elif args.comando == "doctor":
            diagnostico()
    except (ToonsError, BasicErro) as e:
        erro(str(e))
        return 1
    except KeyboardInterrupt:
        print()
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
