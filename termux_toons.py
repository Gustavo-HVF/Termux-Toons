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
   8. Rede e segurança em equipamentos seus (nmap, SSH, WireGuard, velocidade, modem AT)
   9. Retro: jogos ASCII, interpretador BASIC e template para criar seu jogo
  10. Linux de verdade com proot-distro (Debian, Ubuntu, Arch...), com desktop no Termux:X11
  11. Servidor de arquivos e backup (rclone, Syncthing, Samba, HTTP) e página HTML num link
  12. "Spotify" no terminal: yt-dlp para baixar e mpv para tocar
  13. Vídeos do TikTok, YouTube e outros sites com yt-dlp
  14. Atualização do Termux e dos repositórios
  15. Otimização e limpeza (caches, arquivos grandes/duplicados, processos)
  16. Compartilhar filmes por link: arquivo do celular ou qualquer link de vídeo, com
      player próprio, troca de trilha de áudio e conversão na hora (servidor de vídeo + túnel)
  17. Depuração sem fio (ADB pelo Wi-Fi) do próprio celular, sem PC e sem root
  18. Gerenciador de arquivos: copiar, mover, renomear, compactar e ver Android/data (ADB ou root)
  19. Calculadora científica com botões (setas + Enter): trigonometria, fatorial, %, frações

Uso:
    python termux_toons.py            # menu interativo
    python termux_toons.py --help     # subcomandos (também usados pelo tmux)

Só precisa da biblioteca padrão do Python para abrir; o resto (flask, rich,
pacotes do Termux...) é instalado sob demanda, perguntando antes.
"""

from __future__ import annotations

import argparse
import ast
import atexit
import contextlib
import copy
import fnmatch
import getpass
import hashlib
import hmac
import importlib
import importlib.util
import io
import json
import math
import operator
import os
import platform
import random
import re
import secrets
import select
import shlex
import shutil
import socket
import stat
import statistics
import subprocess
import sys
import tarfile
import threading
import time
import traceback
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from fractions import Fraction
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    import termios
    import tty
except ImportError:  # sem terminal POSIX (ex.: Windows): só o modo numérico
    termios = tty = None

VERSION = "1.3.0"
SCRIPT = Path(__file__).resolve()
try:  # muda a cada atualização do código: serve para reiniciar serviços que ainda rodam a versão antiga
    ASSINATURA = hashlib.sha1(SCRIPT.read_bytes()).hexdigest()[:10]
except OSError:
    ASSINATURA = "?"
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
    "formato_musica": "opus",
    "formato_video": "mp4",
    "qualidade_video": "melhor",
    "midia_porta": 8095,
    "midia_transmissoes": 3,
    "site_porta": 8097,
    "site_pagina": "",
    "adb_endereco": "",
    "x11_usuarios": {},
    "x11_gpu": False,
    "torbox_chave": "",
    "torbox_catalogo": "",
    "compartilhamentos": [],
    "llama_porta": 8080,
    "llama_modelo": "",
    "llama_threads": 4,
    "llama_contexto": 2048,
    "aviso_rede_aceito": False,
    "modem_aviso_aceito": False,
    "modem_dispositivo": "",
    "modem_baud": "115200",
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


def url_tunel(nome: str = "tunel"):
    arq = log_de(nome)
    if not arq.exists():
        return None
    achados = re.findall(r"https://[a-z0-9-]+\.trycloudflare\.com", arq.read_text("utf-8", errors="replace"))
    return achados[-1] if achados else None


def abrir_tunel(nome: str, porta: int, aviso_txt: str | None = None) -> None:
    """Liga um Cloudflare Tunnel rápido para `porta` e mostra o endereço público quando sair."""
    if not garantir_cmd("cloudflared"):
        return
    if servico_ativo(nome):
        aviso("O túnel já está rodando.")
        info(f"URL: {url_tunel(nome)}")
        return
    log_de(nome).unlink(missing_ok=True)  # para encontrar a URL nova no log
    if aviso_txt:
        aviso(aviso_txt)
    if not iniciar_servico(nome, f"cloudflared tunnel --no-autoupdate --url http://localhost:{porta}"):
        return
    info("Aguardando a URL pública...")
    for _ in range(30):
        url = url_tunel(nome)
        if url:
            ok(f"Acesse de qualquer lugar: {NEG}{url}{RST}")
            return
        time.sleep(1)
    aviso("A URL ainda não apareceu; veja o log do túnel em alguns segundos.")


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
        if not servico_ativo("web"):
            aviso("O servidor web não está rodando; o túnel vai apontar para a porta mesmo assim.")
        abrir_tunel("tunel", c["web_porta"], "Com o túnel, a API fica acessível pela internet: guarde bem o token!")

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


# ── Modem (comandos AT / 3GPP) ───────────────────────────────────────
# Fala direto com o modem (rádio) do próprio celular por comandos AT, o
# padrão 3GPP TS 27.007. No Android isso exige root e uma porta serial do
# modem exposta (o nó de dispositivo varia por chip); muitos aparelhos
# não a expõem. Use só no SEU aparelho, com o SEU chip: ligar e mandar SMS
# gastam créditos, e mexer em operadora/dados pode derrubar sua conexão.

# Nós de dispositivo onde a porta AT do modem costuma aparecer, por fabricante de chip.
MODEM_DISPOSITIVOS = [
    "/dev/smd0", "/dev/smd7", "/dev/smd8", "/dev/smd11",           # Qualcomm
    "/dev/radio/pttycmd1", "/dev/radio/atci_mdport",              # MediaTek
    "/dev/ttyC_ril_ctl", "/dev/ttyGS0", "/dev/at_mdm0",           # outros
    "/dev/ttyUSB2", "/dev/ttyUSB3", "/dev/ttyACM0",               # modem USB (OTG)
]

CREG_ESTADOS = {
    "0": "não registrado e não procurando", "1": "registrado (rede local)",
    "2": "procurando operadora", "3": "registro negado", "4": "desconhecido",
    "5": "registrado (roaming)", "6": "registrado (só SMS)", "7": "registrado (só SMS, roaming)",
}


def _modem_dispositivo() -> str:
    dev = cfg().get("modem_dispositivo", "")
    if not dev:
        raise ToonsError("Nenhuma porta do modem escolhida. Use 'Procurar a porta do modem' primeiro.")
    return dev


# Códigos com que o modem encerra uma resposta (3GPP TS 27.007 / V.250).
_MODEM_FALHA = re.compile(r"^(?:ERROR|\+CM[ES] ERROR\b.*|NO CARRIER|BUSY|NO ANSWER|NO DIALTONE)$", re.M | re.I)

# Lê linha a linha e para assim que chega um código final, em vez de sempre esperar o tempo todo.
_MODEM_LER = (
    'CR=$(printf "\\r"); '
    'while IFS= read -r l; do l=${l%"$CR"}; printf "%s\\n" "$l"; '
    'case "$l" in OK|ERROR|"+CME ERROR"*|"+CMS ERROR"*|"NO CARRIER"|BUSY|"NO ANSWER"|"NO DIALTONE") exit 0;; esac; '
    'done'
)

# Confere que a porta é um dispositivo (como root, '<>' criaria um arquivo comum num caminho
# errado), abre como leitura+escrita (fd 3) num bloco { } — se a abertura falhar o shell segue
# (um 'exec 3<>' que falha encerra o sh do Android antes de avisar) —, descarta restos de
# respostas antigas, envia o comando com CR e lê a resposta.
_MODEM_SCRIPT = (
    '[ -c "$DEV" ] && { stty -F "$DEV" "$BAUD" raw -echo clocal; '
    'timeout 0.3 cat <&3 >/dev/null; '
    'printf "%s\\r" "$CMD" >&3; '
    '[ -n "$FIM" ] && { sleep 1; printf "%s" "$FIM" >&3; }; '
    'timeout "$TO" sh -c "$LER" <&3; exit 0; } 2>/dev/null 3<>"$DEV"; '
    'echo __SEM_PORTA__; exit 7'
)


def modem_enviar(comando: str, espera: float = 3.0, final: str | None = None, dev: str | None = None) -> str:
    """Envia um comando AT ao modem (via root) e devolve a resposta já limpa.
    `espera` é o tempo MÁXIMO: a leitura termina antes, no código final (OK, ERROR...).
    `final`, se dado, é um texto enviado logo depois (ex.: Ctrl-Z para concluir um SMS).
    `dev` usa outra porta sem mexer na configuração (para testar portas)."""
    if not tem_root():
        raise ToonsError("Falar com o modem exige root (o comando 'su' não respondeu).")
    dev = dev or _modem_dispositivo()
    variaveis = {"DEV": dev, "BAUD": str(cfg().get("modem_baud", "115200")), "CMD": comando,
                 "TO": f"{espera:g}", "FIM": final or "", "LER": _MODEM_LER, "SCRIPT": _MODEM_SCRIPT}
    # o 'timeout' de fora garante que nada fique preso como root segurando a porta (o timeout
    # do Python só mata o cliente 'su', não o shell que roda como root)
    limite = int(espera) + 6
    linha = ("export " + " ".join(f"{k}={shlex.quote(v)}" for k, v in variaveis.items())
             + f'; timeout {limite} sh -c "$SCRIPT"')
    proc = rodar(["su", "-c", linha], capturar=True, timeout=limite + 15, mostrar=False)
    saida_bruta = proc.stdout or ""
    if "__SEM_PORTA__" in saida_bruta:
        raise ToonsError(f"Não consegui abrir {dev}. É a porta certa? O modem pede root e a porta exata do seu chip.")
    return _modem_limpar(saida_bruta, comando)


def _modem_limpar(saida_bruta: str, comando: str) -> str:
    """Tira o eco do comando e linhas vazias; devolve só a resposta do modem."""
    linhas = []
    for linha in saida_bruta.replace("\r", "\n").split("\n"):
        linha = linha.strip()
        if linha and linha.upper() != comando.upper():
            linhas.append(linha)
    return "\n".join(linhas)


def modem_ok(comando: str, espera: float = 3.0) -> str:
    """Envia o comando e confere se o modem terminou com OK; erro ou silêncio vira ToonsError.
    Devolve a resposta sem a linha final 'OK'."""
    resposta = modem_enviar(comando, espera)
    if _MODEM_FALHA.search(resposta):
        raise ToonsError(f"O modem respondeu com erro:\n{resposta}")
    linhas = resposta.split("\n")
    if "OK" not in linhas:
        raise ToonsError(f"O modem não confirmou '{comando}' com OK (em até {espera:g}s):\n"
                         f"{resposta or '(sem resposta — a porta é a certa?)'}")
    del linhas[len(linhas) - 1 - linhas[::-1].index("OK")]
    return "\n".join(linhas)


def _sms_modo_texto() -> None:
    """SMS em modo texto, com o conjunto de caracteres ASCII (IRA) quando o modem aceita."""
    modem_ok("AT+CMGF=1")
    with contextlib.suppress(ToonsError):
        modem_ok('AT+CSCS="IRA"')


def _so_valor(resposta: str, prefixo: str) -> str:
    """Pega o que vem depois de '+XXX:' na resposta (ex.: '+CSQ: 17,99' → '17,99')."""
    m = re.search(rf"{re.escape(prefixo)}:\s*(.+)", resposta)
    return m.group(1).strip() if m else resposta.strip()


def _descrever_sinal(resposta: str) -> str:
    valor = _so_valor(resposta, "+CSQ")
    rssi = valor.split(",")[0].strip()
    if not rssi.isdigit() or int(rssi) > 31:  # 99 = desconhecido; 100–191 é outra escala (TD-SCDMA)
        return "sinal desconhecido (sem rede?)"
    dbm = -113 + 2 * int(rssi)
    barras = min(5, max(1, (int(rssi) + 3) // 6))
    return f"{dbm} dBm  {'▮' * barras}{'▯' * (5 - barras)}  (CSQ {rssi}/31)"


@submenu
def menu_modem():
    c = cfg()
    if not c.get("modem_aviso_aceito"):
        limpar()
        titulo("📡 Modem — comandos AT")
        print("Isto fala direto com o rádio do SEU celular (padrão 3GPP/AT). Precisa de ROOT e da\n"
              "porta serial do modem, que nem todo aparelho expõe.\n\n"
              "• Ligar e enviar SMS GASTAM créditos do seu chip.\n"
              "• Mexer em operadora (COPS) ou dados (CGACT) pode derrubar sua conexão até reiniciar.\n"
              "• Use só no seu aparelho, com o seu chip. Consulta o IMEI, não altera (alterar é crime).\n")
        if not confirmar("Entendi e vou usar só no meu aparelho", False):
            return
        c["modem_aviso_aceito"] = True
        salvar_cfg()

    def procurar_porta():
        if not tem_root():
            raise ToonsError("Procurar a porta do modem exige root.")
        info("Procurando portas do modem e testando com 'AT' (precisa responder OK)...")
        # só nós de caractere que existem ('ls' com um padrão sem resultado sairia com erro e
        # esconderia os que existem); o 'exit 0' evita o mesmo problema com o último teste
        padroes = ("/dev/smd* /dev/radio/* /dev/tty_ril* /dev/ttyC_ril* /dev/at_mdm* "
                   "/dev/ttyUSB* /dev/ttyACM* /dev/ttyGS* " + " ".join(MODEM_DISPOSITIVOS))
        existentes = saida(["su", "-c", f'for f in {padroes}; do [ -c "$f" ] && echo "$f"; done; exit 0'])
        candidatos = list(dict.fromkeys(l.strip() for l in existentes.splitlines() if l.strip()))
        funcionam = []
        for dev in candidatos:
            with contextlib.suppress(ToonsError):
                if re.search(r"^OK$", modem_enviar("AT", espera=1.5, dev=dev), re.M):
                    funcionam.append(dev)
                    print(f"  {VERD}✔{RST} {dev}")
        if not funcionam:
            raise ToonsError("Nenhuma porta respondeu 'AT'. Seu aparelho pode não expor o modem, ou a porta tem "
                             "outro nome. Veja 'ls /dev/' com root ou informe o caminho manualmente.")
        i = escolher("Qual porta usar?", funcionam)
        if i is not None:
            c["modem_dispositivo"] = funcionam[i]
            salvar_cfg()
            ok(f"Porta do modem: {funcionam[i]}")

    def escolher_porta():
        i = escolher("Porta do modem (ou digite o caminho)", MODEM_DISPOSITIVOS + ["Digitar outro caminho..."])
        if i is None:
            return
        dev = perguntar("Caminho (/dev/...)") if i == len(MODEM_DISPOSITIVOS) else MODEM_DISPOSITIVOS[i]
        if dev:
            c["modem_dispositivo"] = dev
            salvar_cfg()
            ok(f"Porta do modem: {dev}  (teste com 'Informações do aparelho').")

    # ── Informações do aparelho ──
    def informacoes():
        for rotulo, cmd in (("Fabricante (CGMI)", "AT+CGMI"), ("Modelo (CGMM)", "AT+CGMM"),
                            ("Versão de firmware (CGMR)", "AT+CGMR"), ("IMEI (GSN)", "AT+GSN")):
            try:
                resposta = modem_ok(cmd)
                valor = "\n".join(l for l in resposta.splitlines() if l.upper() != "OK") or "?"
                print(f"  {CIANO}{rotulo:<26}{RST} {valor}")
            except ToonsError as e:
                print(f"  {CIANO}{rotulo:<26}{RST} {VERM}{e}{RST}")

    # ── Rede ──
    def sinal():
        print(f"  Sinal: {NEG}{_descrever_sinal(modem_ok('AT+CSQ'))}{RST}")

    def registro():
        valor = _so_valor(modem_ok("AT+CREG?"), "+CREG")
        estado = valor.split(",")[1].strip() if "," in valor else valor
        print(f"  Registro na rede: {NEG}{CREG_ESTADOS.get(estado, 'código ' + estado)}{RST}")
        with contextlib.suppress(ToonsError):
            atual = _so_valor(modem_ok("AT+COPS?"), "+COPS")
            nome = re.search(r'"([^"]+)"', atual)
            if nome:
                print(f"  Operadora atual:  {NEG}{nome.group(1)}{RST}")

    def listar_operadoras():
        info("Procurando operadoras disponíveis (pode levar alguns minutos)...")
        resposta = modem_ok("AT+COPS=?", espera=180)
        nomes = re.findall(r'\(\s*\d+\s*,\s*"([^"]+)"', resposta)
        if nomes:
            for nome in dict.fromkeys(nomes):
                print(f"  • {nome}")
        else:
            print(resposta or "(sem resposta)")

    def selecionar_operadora():
        aviso("Selecionar manualmente pode deixar você sem sinal se a operadora não for a do seu chip.")
        i = escolher("Modo de seleção", ["Automático (recomendado)", "Manual (digitar código MCCMNC)"])
        if i == 0:
            ok(modem_ok("AT+COPS=0", espera=60) or "Modo automático ativado.")
        elif i == 1:
            codigo = perguntar("Código da operadora (MCCMNC, ex.: 72410)")
            if not re.fullmatch(r"\d{5,6}", codigo):
                raise ToonsError("O código MCCMNC tem 5 ou 6 dígitos (ex.: 72410).")
            modem_ok(f'AT+COPS=1,2,"{codigo}"', espera=120)
            ok("Operadora selecionada.")

    # ── Chamadas ──
    def ligar():
        numero = perguntar("Número para ligar (com DDD)")
        if not re.fullmatch(r"[+0-9*#]{2,20}", numero or ""):
            raise ToonsError("Número inválido.")
        if not confirmar(f"Ligar para {numero}? (pode gastar créditos)", False):
            return
        # o ';' faz uma chamada de VOZ; alguns modems só dão OK quando atendem, então o
        # silêncio aqui não é erro — só um código de falha é
        resposta = modem_enviar(f"ATD{numero};", espera=5)
        if _MODEM_FALHA.search(resposta):
            raise ToonsError(f"A chamada não completou:\n{resposta}")
        ok(f"Chamando {numero}... Use 'Encerrar a chamada' para desligar.")

    def atender():
        ok(modem_ok("ATA") or "Chamada atendida.")

    def encerrar():
        ok(modem_ok("ATH") or "Chamada encerrada.")

    # ── SMS ──
    def enviar_sms():
        numero = perguntar("Número de destino (com DDD)")
        if not re.fullmatch(r"[+0-9]{3,20}", numero or ""):
            raise ToonsError("Número inválido.")
        texto = perguntar("Mensagem")
        # o modo texto só leva ASCII com segurança: acentos viram letras sem acento
        ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
        ascii_ = "".join(ch for ch in ascii_ if ch.isprintable()).strip()
        if ascii_ != texto:
            aviso(f"Sem acentos/emojis, a mensagem vai assim: {ascii_}")
            texto = ascii_
        if len(texto) > 160:
            raise ToonsError(f"A mensagem tem {len(texto)} caracteres; um SMS em modo texto leva até 160.")
        if not texto or not confirmar(f"Enviar SMS para {numero}? (pode gastar créditos)", False):
            return
        _sms_modo_texto()
        # manda AT+CMGS="numero", espera o '>' e então o texto + Ctrl-Z (0x1A)
        resposta = modem_enviar(f'AT+CMGS="{numero}"', espera=60, final=texto + "\x1a")
        if re.search(r"\+CMGS:|^OK$", resposta, re.M) and not _MODEM_FALHA.search(resposta):
            ok("SMS enviado.")
        else:
            raise ToonsError(f"Não confirmou o envio:\n{resposta or '(sem resposta)'}")

    def ler_sms():
        _sms_modo_texto()
        filtros = {"Não lidas": '"REC UNREAD"', "Recebidas": '"REC READ"', "Todas": '"ALL"'}
        i = escolher("Quais mensagens?", list(filtros), 1)
        if i is None:
            return
        resposta = modem_ok(f"AT+CMGL={list(filtros.values())[i]}", espera=10)
        blocos = re.findall(r'\+CMGL:\s*(\d+),"[^"]*","([^"]*)"[^\n]*\n(.*?)(?=\n\+CMGL:|\nOK|$)',
                            resposta, re.S)
        if not blocos:
            info(resposta or "Nenhuma mensagem.")
            return
        for idx, remetente, corpo in blocos:
            print(f"  {CIANO}#{idx}{RST} de {NEG}{remetente or '?'}{RST}: {corpo.strip()}")

    def apagar_sms():
        idx = perguntar("Número da mensagem para apagar (veja em 'Ler mensagens')")
        if idx.isdigit() and confirmar(f"Apagar a mensagem #{idx}?", False):
            modem_ok(f"AT+CMGD={idx}")
            ok("Mensagem apagada.")

    # ── Dados móveis ──
    def ver_apn():
        resposta = modem_ok("AT+CGDCONT?")
        contextos = re.findall(r'\+CGDCONT:\s*(\d+),"([^"]*)","([^"]*)"', resposta)
        if contextos:
            for cid, tipo, apn in contextos:
                print(f"  Contexto {cid}: APN {NEG}{apn or '(vazio)'}{RST} ({tipo})")
        else:
            print(resposta or "(sem contextos)")

    def definir_apn():
        apn = perguntar("APN da operadora (ex.: zap.vivo.com.br)")
        if not apn:
            return
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", apn):
            raise ToonsError("APN inválida: use só letras, números, ponto, hífen e sublinhado.")
        cid = perguntar_int("Número do contexto (geralmente 1)", 1, 1, 15)
        modem_ok(f'AT+CGDCONT={cid},"IP","{apn}"')
        ok(f"APN '{apn}' definida no contexto {cid}.")

    def ativar_dados(ligar_dados: bool):
        cid = perguntar_int("Número do contexto", 1, 1, 15)
        modem_ok(f"AT+CGACT={1 if ligar_dados else 0},{cid}", espera=60)
        ok(f"Contexto de dados {cid} {'ativado' if ligar_dados else 'desativado'}.")

    def endereco_ip():
        resposta = ""
        with contextlib.suppress(ToonsError):
            resposta = modem_ok("AT+CGPADDR")
        # contextos sem conexão aparecem vazios ou como 0.0.0.0
        ips = [ip for ip in re.findall(r'\+CGPADDR:\s*\d+,"?([0-9.:]+)"?', resposta)
               if ip.strip("0.:")]
        if not ips:
            with contextlib.suppress(ToonsError):
                ips = [ip for ip in re.findall(r"(\d+\.\d+\.\d+\.\d+)", modem_ok("AT+CIFSR"))
                       if ip != "0.0.0.0"]
        print(f"  IP da conexão de dados: {NEG}{ips[0] if ips else '(sem IP / dados desligados)'}{RST}")

    # ── Console livre ──
    def console():
        info("Digite comandos AT (ex.: AT+CSQ). Enter vazio sai. Veja 3GPP TS 27.007 para a lista.")
        while True:
            cmd = perguntar("AT")
            if not cmd:
                return
            if not cmd.upper().startswith("AT"):
                cmd = "AT" + cmd
            try:
                print(modem_enviar(cmd, espera=30) or "(sem resposta)")
            except ToonsError as e:
                erro(str(e))

    menu("📡 Modem (comandos AT / 3GPP)", [
        (lambda: f"Porta do modem ({c.get('modem_dispositivo') or 'não definida'})", escolher_porta),
        ("Procurar a porta do modem automaticamente", procurar_porta),
        ("Informações do aparelho (IMEI, fabricante, modelo)", informacoes),
        ("Qualidade do sinal (CSQ)", sinal),
        ("Registro na rede e operadora atual (CREG/COPS)", registro),
        ("Listar operadoras disponíveis (COPS=?)", listar_operadoras),
        ("Selecionar operadora (COPS)", selecionar_operadora),
        ("☎  Ligar para um número (ATD)", ligar),
        ("☎  Atender a chamada (ATA)", atender),
        ("☎  Encerrar a chamada (ATH)", encerrar),
        ("✉  Enviar SMS (CMGS)", enviar_sms),
        ("✉  Ler mensagens (CMGL)", ler_sms),
        ("✉  Apagar uma mensagem (CMGD)", apagar_sms),
        ("📶 Ver APN / contextos de dados (CGDCONT?)", ver_apn),
        ("📶 Definir APN (CGDCONT)", definir_apn),
        ("📶 Ativar dados (CGACT=1)", lambda: ativar_dados(True)),
        ("📶 Desativar dados (CGACT=0)", lambda: ativar_dados(False)),
        ("📶 Ver o IP da conexão de dados (CGPADDR)", endereco_ip),
        ("⌨  Console AT (digitar comandos à mão)", console),
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
        ("📡 Modem: comandos AT (chamadas, SMS, sinal, APN; precisa de root)", menu_modem),
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


# ── Interface gráfica da distro no Termux:X11 ────────────────────────
# O app Termux:X11 mostra a tela; o pacote termux-x11 é o servidor X dentro do Termux.
# A distro (proot) enxerga o servidor pelo /tmp compartilhado (--shared-tmp) e o som
# chega pelo PulseAudio do Termux via TCP. Cada ambiente traz os pacotes por gerenciador.

X11_APP = "com.termux.x11/com.termux.x11.MainActivity"
X11_DOWNLOAD = "https://github.com/termux/termux-x11/releases/tag/nightly"
X11_DISPLAY = ":1"
AMBIENTES_GRAFICOS = {
    "xfce": {"nome": "XFCE — completo e leve (recomendado)", "iniciar": "startxfce4",
             "apt": "xfce4 xfce4-terminal xfce4-goodies dbus-x11 fonts-dejavu",
             "pacman": "xfce4 xfce4-goodies dbus ttf-dejavu",
             "apk": "xfce4 xfce4-terminal dbus dbus-x11 font-dejavu adwaita-icon-theme",
             "dnf": "xfce4-session xfwm4 xfce4-panel xfdesktop xfce4-terminal thunar xfce4-settings dbus-x11 dejavu-sans-fonts",
             "zypper": "xfce4-session xfwm4 xfce4-panel xfdesktop xfce4-terminal thunar xfce4-settings dbus-1-x11"},
    "lxqt": {"nome": "LXQt — o mais leve, bom para celulares mais simples", "iniciar": "startlxqt",
             "apt": "lxqt-core qterminal dbus-x11 fonts-dejavu",
             "pacman": "lxqt breeze-icons dbus ttf-dejavu",
             "apk": "lxqt-desktop dbus dbus-x11 font-dejavu",
             "dnf": "lxqt-session lxqt-panel lxqt-config pcmanfm-qt qterminal openbox dbus-x11",
             "zypper": "lxqt-session lxqt-panel lxqt-config pcmanfm-qt qterminal openbox dbus-1-x11"},
    "mate": {"nome": "MATE — visual clássico", "iniciar": "mate-session",
             "apt": "mate-desktop-environment-core dbus-x11 fonts-dejavu",
             "pacman": "mate mate-terminal dbus ttf-dejavu",
             "apk": "mate-desktop-environment dbus dbus-x11 font-dejavu",
             "dnf": "mate-session-manager mate-panel marco caja mate-terminal dbus-x11",
             "zypper": "mate-session-manager mate-panel marco caja mate-terminal dbus-1-x11"},
}
NAVEGADOR_DISTRO = {"apt": '$(. /etc/os-release; [ "$ID" = ubuntu ] && echo epiphany-browser || echo firefox-esr)', "pacman": "firefox", "apk": "firefox", "dnf": "firefox",
                    "zypper": "MozillaFirefox"}


def _script_instalar(pacotes: dict) -> str:
    """Script de shell que instala os pacotes certos para o gerenciador da distro."""
    return (
        "export DEBIAN_FRONTEND=noninteractive; set -e; "
        f"if command -v apt-get >/dev/null; then apt-get update && apt-get install -y {pacotes['apt']}; "
        f"elif command -v pacman >/dev/null; then pacman -Syu --noconfirm --needed {pacotes['pacman']}; "
        f"elif command -v apk >/dev/null; then apk update && apk add {pacotes['apk']}; "
        f"elif command -v dnf >/dev/null; then dnf install -y {pacotes['dnf']}; "
        f"elif command -v zypper >/dev/null; then zypper --non-interactive install {pacotes['zypper']}; "
        "else echo 'Gerenciador de pacotes desconhecido nesta distro.'; exit 1; fi"
    )


def ambiente_da_distro(distro: str) -> str | None:
    """Comando que inicia o desktop já instalado na distro (startxfce4, startlxqt...), ou None."""
    comandos = " ".join(a["iniciar"] for a in AMBIENTES_GRAFICOS.values())
    proc = rodar(["proot-distro", "login", distro, "--", "sh", "-c",
                  f"for c in {comandos}; do command -v $c >/dev/null 2>&1 && echo $c && break; done"],
                 capturar=True, timeout=120, mostrar=False)
    achado = (proc.stdout or "").strip().splitlines()
    return achado[-1] if achado else None


def garantir_termux_x11() -> bool:
    """Pacotes do Termux para a interface gráfica: servidor X (termux-x11) e som (pulseaudio)."""
    if not garantir_cmd("termux-x11", "termux-x11-nightly", repo="x11-repo"):
        return False
    if not tem("pulseaudio") and confirmar("Instalar o pulseaudio (som dos programas da distro)?", True):
        instalar_pkg("pulseaudio")
    return True


def script_desktop(distro: str, iniciar: str, usuario: str = "", gpu: bool = False) -> Path:
    """Grava o script que abre o desktop (o mesmo que o atalho da tela inicial usa) e devolve o caminho."""
    pasta = DATA_DIR / "x11"
    pasta.mkdir(parents=True, exist_ok=True)
    env_distro = [f"DISPLAY={X11_DISPLAY}", "PULSE_SERVER=tcp:127.0.0.1:4713", "XDG_RUNTIME_DIR=/tmp"]
    if gpu:  # OpenGL pela GPU do celular, via virgl (experimental)
        env_distro += ["GALLIUM_DRIVER=virpipe", "MESA_GL_VERSION_OVERRIDE=4.0"]
    login = ["proot-distro", "login", distro, "--shared-tmp"] + (["--user", usuario] if usuario else [])
    linhas = [
        f"#!{PREFIX or '/data/data/com.termux/files/usr'}/bin/bash",
        f"# Gerado pelo Termux-Toons: abre o desktop da distro '{distro}' no app Termux:X11.",
        'export XDG_RUNTIME_DIR="${TMPDIR:-/tmp}"',
        "pkill -f com.termux.x11 >/dev/null 2>&1  # servidor X de uma sessão anterior",
        "command -v pulseaudio >/dev/null && pulseaudio --start --exit-idle-time=-1 "
        "--load='module-native-protocol-tcp auth-ip-acl=127.0.0.1 auth-anonymous=1' >/dev/null 2>&1",
    ]
    if gpu:
        linhas.append("command -v virgl_test_server_android >/dev/null && (virgl_test_server_android >/dev/null 2>&1 &)")
    linhas += [
        f"termux-x11 {X11_DISPLAY} -ac >/dev/null 2>&1 &",
        "sleep 3",
        f"am start --user 0 -n {X11_APP} >/dev/null 2>&1",
        f"{shlex.join(login)} -- env {' '.join(env_distro)} dbus-launch --exit-with-session {shlex.quote(iniciar)}",
        "pkill -f com.termux.x11 >/dev/null 2>&1",
    ]
    if gpu:
        linhas.append("pkill -f virgl_test_server >/dev/null 2>&1")
    script = pasta / f"desktop-{distro}.sh"
    script.write_text("\n".join(linhas) + "\n", "utf-8")
    os.chmod(script, 0o700)
    return script


def iniciar_desktop(distro: str, usuario: str | None = None) -> bool:
    """Abre o desktop da distro no Termux:X11 (roda numa sessão tmux: continua se você sair do menu)."""
    if not garantir_cmd("proot-distro") or not garantir_termux_x11():
        return False
    if distro not in distros_instaladas():
        raise ToonsError(f"A distro '{distro}' não está instalada (veja em 'Listar distros instaladas').")
    info("Procurando o ambiente gráfico instalado na distro...")
    iniciar = ambiente_da_distro(distro)
    if not iniciar:
        raise ToonsError(f"Nenhum ambiente gráfico instalado no '{distro}'. Use 'Instalar um ambiente gráfico' primeiro.")
    c = cfg()
    usuario = c.get("x11_usuarios", {}).get(distro, "") if usuario is None else usuario
    gpu = bool(c.get("x11_gpu"))
    if gpu and not tem("virgl_test_server_android"):
        info("Aceleração ligada: instalando o virglrenderer-android...")
        instalar_pkg("virglrenderer-android")
    script = script_desktop(distro, iniciar, usuario, gpu)
    if servico_ativo("desktop"):
        parar_servico("desktop")
    if not iniciar_servico("desktop", shlex.join([SHELL_BIN, str(script)]), wake_lock=True):
        return False
    time.sleep(2)
    proc = rodar(["am", "start", "--user", "0", "-n", X11_APP], capturar=True, timeout=20, mostrar=False)
    if proc.returncode != 0 or re.search(r"\bError\b|does not exist", f"{proc.stdout}{proc.stderr}"):
        aviso("O app Termux:X11 não abriu: ele está instalado?")
        info(f"Baixe o .apk em {X11_DOWNLOAD} (o 'universal' serve em qualquer celular), instale e tente de novo.")
        return False
    ok(f"Desktop '{iniciar}' do {distro} aberto no Termux:X11" + (f" como {usuario}" if usuario else " como root") + ".")
    info("Para voltar ao Termux, troque de app. Para encerrar: saia pelo menu do desktop ou use 'Parar o desktop'.")
    return True


def parar_desktop() -> None:
    parar_servico("desktop")
    for padrao in ("com.termux.x11", "virgl_test_server"):
        rodar(["pkill", "-f", padrao], capturar=True, mostrar=False)
    if tem("pulseaudio"):
        rodar(["pulseaudio", "--kill"], capturar=True, mostrar=False)
    ok("Desktop encerrado.")


@submenu
def menu_x11():
    c = cfg()

    def instalar_app():
        info("O Termux:X11 é o app que mostra a tela da distro. Baixe o .apk da versão 'nightly' "
             "(o 'universal' serve em qualquer celular) e instale. Ele precisa ser da mesma origem do Termux "
             "(GitHub/F-Droid).")
        if tem("termux-open-url"):
            rodar(["termux-open-url", X11_DOWNLOAD], capturar=True, timeout=20)
        else:
            info(X11_DOWNLOAD)
        garantir_termux_x11()

    def instalar_ambiente():
        if not garantir_cmd("proot-distro"):
            return
        distro = escolher_distro_instalada()
        if not distro:
            return
        chaves = list(AMBIENTES_GRAFICOS)
        i = escolher("Qual ambiente gráfico?", [AMBIENTES_GRAFICOS[k]["nome"] for k in chaves], 1)
        if i is None:
            return
        ambiente = AMBIENTES_GRAFICOS[chaves[i]]
        aviso("Baixa de 300 MB a 1 GB e leva de 10 a 40 minutos, conforme o celular e a internet. "
              "Deixe o celular carregando e o Termux aberto.")
        if not confirmar(f"Instalar {ambiente['nome'].split(' —')[0]} no {distro}?", True):
            return
        with manter_acordado():
            proc = rodar(["proot-distro", "login", distro, "--", "sh", "-c", _script_instalar(ambiente)])
        if proc.returncode != 0:
            raise ToonsError("A instalação falhou (veja as mensagens acima). Tente 'Atualizar pacotes das distros' e repita.")
        ok("Ambiente gráfico instalado.")
        if confirmar("Instalar também um navegador (Firefox; no Ubuntu, o Epiphany)?", True):
            # no Ubuntu o Firefox e o Chromium vêm por snap, que não roda no proot
            rodar(["proot-distro", "login", distro, "--", "sh", "-c", _script_instalar(NAVEGADOR_DISTRO)])
        garantir_termux_x11()
        if confirmar("Abrir o desktop agora?", True):
            iniciar_desktop(distro)

    def abrir():
        distro = escolher_distro_instalada()
        if distro:
            iniciar_desktop(distro)

    def usuario():
        distro = escolher_distro_instalada()
        if not distro:
            return
        info("Alguns programas (navegadores, por exemplo) não gostam de rodar como root. Crie um usuário em "
             "'Criar usuário não-root com sudo' e indique-o aqui.")
        atual = c.get("x11_usuarios", {}).get(distro, "")
        nome = perguntar("Usuário que abre o desktop (Enter = root)", atual).strip()
        c.setdefault("x11_usuarios", {})[distro] = nome
        salvar_cfg()
        ok(f"O desktop do {distro} abre como {nome or 'root'}.")

    def gpu():
        if not c.get("x11_gpu"):
            info("Usa a GPU do celular para OpenGL (virgl). Pode deixar jogos e efeitos mais rápidos, mas em "
                 "alguns aparelhos causa telas pretas ou travamentos. Se der problema, desligue aqui.")
        c["x11_gpu"] = not c.get("x11_gpu")
        salvar_cfg()
        if c["x11_gpu"] and not tem("virgl_test_server_android"):
            instalar_pkg("virglrenderer-android")
        ok(f"Aceleração gráfica {'ligada' if c['x11_gpu'] else 'desligada'} (vale na próxima vez que abrir o desktop).")

    def atalho():
        distro = escolher_distro_instalada()
        if not distro:
            return
        pasta = HOME / ".shortcuts"
        pasta.mkdir(parents=True, exist_ok=True)
        arq = pasta / f"Desktop {distro}.sh"
        arq.write_text(f"#!{PREFIX or '/data/data/com.termux/files/usr'}/bin/bash\n"
                       f"{shlex.join([sys.executable, str(SCRIPT), 'desktop', distro])}\n", "utf-8")
        os.chmod(arq, 0o700)
        ok(f"Atalho criado: {arq}")
        info("Instale o app Termux:Widget (mesma loja do Termux), adicione o widget na tela inicial e toque em "
             f"'Desktop {distro}' para abrir o desktop direto.")

    menu("🖥️ Interface gráfica da distro (Termux:X11)", [
        ("1. Instalar o app Termux:X11 e o servidor X do Termux", instalar_app),
        ("2. Instalar um ambiente gráfico na distro (XFCE, LXQt, MATE)", instalar_ambiente),
        ("▶  Abrir o desktop da distro", abrir),
        ("■  Parar o desktop", parar_desktop),
        ("Usuário que abre o desktop (root ou outro)", usuario),
        (lambda: f"Aceleração gráfica pela GPU ({'ligada' if c.get('x11_gpu') else 'desligada'}, experimental)", gpu),
        ("Criar atalho na tela inicial (Termux:Widget)", atalho),
    ])


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
        ("🖥️ Interface gráfica da distro (Termux:X11)", menu_x11),
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


# ── Publicar página/site HTML num link ───────────────────────────────

SITE_DIR = DATA_DIR / "site"  # cópia do arquivo quando você publica só uma página


class _HandlerSite(SimpleHTTPRequestHandler):
    """Entrega os arquivos de uma pasta como site: abre o index.html, mas não lista pastas
    nem mostra arquivos ocultos (.git, .env...)."""
    server_version = f"TermuxToons/{VERSION}"

    def list_directory(self, path):
        self.send_error(404, "Página não encontrada")
        return None

    def send_head(self):
        partes = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path).split("/")
        if any(p.startswith(".") for p in partes if p):
            self.send_error(404, "Página não encontrada")
            return None
        return super().send_head()

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")  # quem abre o link vê sempre a versão mais nova
        super().end_headers()

    def log_message(self, fmt, *args):
        log(f"{self.client_address[0]} {fmt % args}")


def servir_site(pasta: str, porta: int) -> None:
    """Sobe o site em primeiro plano (é o que roda dentro do tmux)."""
    pasta = str(Path(os.path.expanduser(pasta)).resolve())
    if not Path(pasta).is_dir():
        raise ToonsError(f"Pasta não encontrada: {pasta}")
    with ThreadingHTTPServer(("0.0.0.0", porta), lambda *a, **k: _HandlerSite(*a, directory=pasta, **k)) as servidor:
        log(f"Site de {pasta} em http://{ip_local()}:{porta}  (Ctrl+C para parar)")
        servidor.serve_forever()


def links_do_site() -> list:
    """[(onde funciona, link)] da página publicada: rede local e, com o túnel ligado, a internet."""
    c = cfg()
    caminho = "/" + urllib.parse.quote(c["site_pagina"])
    links = [("Mesma rede Wi-Fi", f"http://{ip_local()}:{c['site_porta']}{caminho}")]
    if servico_ativo("tunel-site") and url_tunel("tunel-site"):
        links.append(("Internet", f"{url_tunel('tunel-site')}{caminho}"))
    return links


def mostrar_links_do_site() -> None:
    if not servico_ativo("site"):
        info("Nenhuma página publicada agora.")
        return
    for onde, link in links_do_site():
        print(f"  {CIANO}{onde}:{RST}\n  {NEG}{link}{RST}")
    if not servico_ativo("tunel-site"):
        print(f"  {DIM}Para quem está fora da sua rede Wi-Fi, use 'Página publicada: liberar para a internet'.{RST}")


def publicar_site() -> None:
    """Escolhe um .html (ou a pasta de um site), sobe o servidor e, se quiser, o túnel para a internet."""
    info("Publica uma página HTML (ou um site com imagens, CSS e JS) num link. Na mesma rede Wi-Fi funciona "
         "na hora; para quem está longe, o túnel da Cloudflare cria um endereço na internet.")
    alvo = Path(os.path.expanduser(perguntar("Arquivo .html ou pasta do site", str(DOWNLOADS))))
    if alvo.is_dir():
        pasta, pagina = alvo, ""
        if not (alvo / "index.html").is_file():
            paginas = sorted(p.name for p in alvo.iterdir() if p.suffix.lower() in (".html", ".htm"))
            i = escolher("Qual página abre primeiro?", paginas)
            if i is None:
                return
            pagina = paginas[i]
        aviso(f"Todos os arquivos de {alvo} ficam acessíveis para quem tiver o link.")
    elif alvo.is_file() and alvo.suffix.lower() in (".html", ".htm"):
        i = escolher("O que publicar?", [
            "Só este arquivo",
            f"A pasta inteira ({alvo.parent.name}/) — use se a página carrega imagens, CSS ou JS dessa pasta"])
        if i is None:
            return
        if i == 0:
            shutil.rmtree(SITE_DIR, ignore_errors=True)
            SITE_DIR.mkdir(parents=True)
            shutil.copy2(alvo, SITE_DIR / "index.html")
            pasta, pagina = SITE_DIR, ""
        else:
            aviso(f"Todos os arquivos de {alvo.parent} ficam acessíveis para quem tiver o link.")
            if not confirmar("Continuar?", True):
                return
            pasta, pagina = alvo.parent, "" if alvo.name == "index.html" else alvo.name
    else:
        raise ToonsError(f"Escolha um arquivo .html ou uma pasta: {alvo}")
    c = cfg()
    c["site_pagina"] = pagina
    salvar_cfg()
    if servico_ativo("site"):
        parar_servico("site")
    if not porta_livre(c["site_porta"]):
        raise ToonsError(f"A porta {c['site_porta']} já está em uso. Troque 'site_porta' em Configurações.")
    if not iniciar_servico("site", cmd_self("site", str(pasta), "--porta", str(c["site_porta"])), reiniciar=True):
        return
    if not servico_ativo("tunel-site") and confirmar("Liberar para a internet (pessoas fora do seu Wi-Fi)?", True):
        abrir_tunel("tunel-site", c["site_porta"])
    print()
    mostrar_links_do_site()
    _, link = links_do_site()[-1]
    if tem("termux-clipboard-set") and confirmar("Copiar o link?", True):
        _tapi(["termux-clipboard-set"], 10, entrada=link, json_saida=False)
        ok("Link copiado.")
    info("O link funciona enquanto o celular estiver ligado com o Termux aberto. O endereço do túnel muda "
         "toda vez que ele é religado.")


def parar_site() -> None:
    parar_servico("tunel-site")
    parar_servico("site")


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
        ("📂 Gerenciador de arquivos (copiar, mover, renomear, Android/data...)", gerenciador_arquivos),
        ("🌍 Publicar página/site HTML num link", publicar_site),
        ("Página publicada: ver o link", mostrar_links_do_site),
        ("Página publicada: liberar para a internet (túnel)",
         lambda: abrir_tunel("tunel-site", cfg()["site_porta"]) if servico_ativo("site") else info("Publique uma página primeiro.")),
        ("Página publicada: tirar do ar", parar_site),
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


# formato: (descrição no menu, opções do yt-dlp, leva a capa embutida?)
FORMATOS_MUSICA = {
    "opus": ("Opus — arquivo menor com ótima qualidade", ["--audio-format", "opus"], True),
    "mp3": ("MP3 320 kbps — toca em qualquer aparelho, som do carro, pendrive",
            ["--audio-format", "mp3", "--audio-quality", "320K"], True),
    "m4a": ("M4A (AAC) — bom para iPhone e aparelhos da Apple", ["--audio-format", "m4a"], True),
    "flac": ("FLAC — sem perdas (bem maior; a origem já vem comprimida)", ["--audio-format", "flac"], True),
    "wav": ("WAV — sem compressão, para editar (não leva capa)", ["--audio-format", "wav"], False),
    "original": ("Original do site, sem converter (mais rápido)", [], False),
}


def comando_ytdlp(alvo: str, formato: str | None = None) -> list:
    """Melhor áudio, convertido para o formato escolhido, com capa (quando o formato aceita) e metadados."""
    formato = formato if formato in FORMATOS_MUSICA else cfg().get("formato_musica", "opus")
    _, opcoes, capa = FORMATOS_MUSICA.get(formato, FORMATOS_MUSICA["opus"])
    selecao = "bestaudio[ext=m4a]/bestaudio/best" if formato == "m4a" else "bestaudio/best"
    return ["yt-dlp", "-f", selecao, "--extract-audio", *opcoes, *(["--embed-thumbnail"] if capa else []),
            "--add-metadata", "-o", str(pasta_musicas() / "%(title)s.%(ext)s"), alvo]


def escolher_formato_musica() -> str | None:
    """Pergunta o formato do áudio (começa no último usado) e o guarda como padrão."""
    c = cfg()
    chaves = list(FORMATOS_MUSICA)
    atual = c.get("formato_musica", "opus")
    i = escolher("Em qual formato baixar?", [FORMATOS_MUSICA[k][0] for k in chaves],
                 str(chaves.index(atual) + 1 if atual in chaves else 1))
    if i is None:
        return None
    c["formato_musica"] = chaves[i]
    salvar_cfg()
    return chaves[i]


def garantir_deps_musica(com_player: bool = True, capa: bool | None = None) -> bool:
    """yt-dlp + ffmpeg; mpv só para tocar (com_player) e mutagen para embutir capas (capa; padrão: com_player)."""
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
    if (com_player if capa is None else capa) and not modulo_existe("mutagen"):
        info("O yt-dlp precisa do módulo 'mutagen' para embutir a capa em arquivos .opus.")
        if confirmar("Instalar mutagen?", True):
            instalar_pip("mutagen")
    return tem("yt-dlp") and tem("ffmpeg") and (not com_player or tem("mpv"))


def baixar_musica(alvo: str, formato: str | None = None) -> bool:
    if not garantir_deps_musica(com_player=False, capa=True):  # baixar não precisa do player
        return False
    garantir_storage()
    pasta_musicas().mkdir(parents=True, exist_ok=True)
    return rodar(comando_ytdlp(alvo, formato)).returncode == 0


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


def _mais_novos_primeiro(arquivos) -> list:
    """Ordena por data de modificação; ignora o que sumiu ou não dá para ler no meio do caminho."""
    datas = {}
    for p in arquivos:
        with contextlib.suppress(OSError):
            datas[p] = p.stat().st_mtime
    return sorted(datas, key=datas.get, reverse=True)


def musicas_locais() -> list:
    pasta = pasta_musicas()
    if not pasta.exists():
        return []
    return _mais_novos_primeiro(p for p in pasta.rglob("*") if p.suffix.lower() in EXTENSOES_AUDIO)


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


def baixar_alvo(alvo: str, formato: str | None = None) -> None:
    """Baixa link do YouTube/SoundCloud/etc., link do Spotify ou termo de busca."""
    if "open.spotify.com/" in alvo:
        buscas = spotify_para_buscas(alvo)
        ok(f"{len(buscas)} música(s) encontrada(s). Procurando no YouTube...")
        for busca in buscas:
            info(busca)
            baixar_musica(f"ytsearch1:{busca} audio", formato)
    elif alvo.startswith(("http://", "https://")):
        baixar_musica(alvo, formato)
    else:
        baixar_musica(f"ytsearch1:{alvo}", formato)


@submenu
def menu_musica():
    c = cfg()

    def buscar_tocar():
        r = escolher_resultado(perguntar("Música ou artista"))
        if r:
            tocar_mpv([r["url"]], stream=True)

    def buscar_baixar():
        r = escolher_resultado(perguntar("Música ou artista"))
        formato = escolher_formato_musica() if r else None
        if formato and baixar_musica(r["url"], formato):
            ok(f"Salvo em {pasta_musicas()}")

    def baixar_link():
        alvo = perguntar("Link (YouTube, YT Music, SoundCloud, playlist...)")
        formato = escolher_formato_musica() if alvo else None
        if formato:
            baixar_alvo(alvo, formato)

    def baixar_spotify():
        url = perguntar("Link do Spotify (música, álbum ou playlist pública)")
        formato = escolher_formato_musica() if url else None
        if formato:
            baixar_alvo(url, formato)

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
        ("Buscar e baixar (escolhe o formato: MP3, Opus, M4A, FLAC...)", buscar_baixar),
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

EXTENSOES_VIDEO = {".mp4", ".webm", ".mkv", ".mov", ".m4v", ".avi"}


def pasta_videos() -> Path:
    return Path(os.path.expanduser(cfg()["pasta_videos"]))


# formato: (descrição no menu, preferência de codecs para o -S do yt-dlp, opções do contêiner)
FORMATOS_VIDEO = {
    "mp4": ("MP4 — toca em qualquer celular, TV e computador (recomendado)",
            ["vcodec:h264", "ext:mp4:m4a"], ["--merge-output-format", "mp4", "--remux-video", "mp4"]),
    "mkv": ("MKV — a melhor qualidade do site, sem converter (alguns players não abrem)",
            [], ["--merge-output-format", "mkv", "--remux-video", "mkv"]),
    "webm": ("WebM — formato aberto (VP9/AV1), arquivos menores", ["ext:webm:webm"], ["--merge-output-format", "webm/mkv"]),
    "mp3": ("Só o áudio, em MP3", [], []),
}
QUALIDADES_VIDEO = {"melhor": "Melhor disponível", "1080": "1080p (Full HD)", "720": "720p (HD) — bom equilíbrio",
                    "480": "480p — economiza espaço e dados", "360": "360p — o menor"}


def comando_video(alvo: str, formato: str | None = None, qualidade: str | None = None) -> list:
    """Melhor vídeo + melhor áudio no formato e na qualidade escolhidos (o yt-dlp junta os dois).
    --trim-filenames evita o erro de nome longo demais com legendas do TikTok."""
    c = cfg()
    formato = formato if formato in FORMATOS_VIDEO else c.get("formato_video", "mp4")
    qualidade = qualidade if qualidade in QUALIDADES_VIDEO else c.get("qualidade_video", "melhor")
    saida_arq = ["--trim-filenames", "150", "-o", str(pasta_videos() / "%(title)s.%(ext)s"), alvo]
    if formato == "mp3":
        return ["yt-dlp", "-f", "bestaudio/best", "--extract-audio", "--audio-format", "mp3", "--audio-quality", "320K",
                "--embed-thumbnail", "--add-metadata", *saida_arq]
    _, preferencia, conteiner = FORMATOS_VIDEO.get(formato, FORMATOS_VIDEO["mp4"])
    ordem = ([f"res:{qualidade}"] if qualidade != "melhor" else []) + preferencia  # res:720 = até 720p
    return ["yt-dlp", "-f", "bv*+ba/b", *(["-S", ",".join(ordem)] if ordem else []), *conteiner, *saida_arq]


def escolher_formato_video():
    """Pergunta formato e qualidade (começam nos últimos usados). Devolve (formato, qualidade) ou None."""
    c = cfg()
    chaves = list(FORMATOS_VIDEO)
    atual = c.get("formato_video", "mp4")
    i = escolher("Em qual formato baixar?", [FORMATOS_VIDEO[k][0] for k in chaves],
                 str(chaves.index(atual) + 1 if atual in chaves else 1))
    if i is None:
        return None
    qualidade = c.get("qualidade_video", "melhor")
    if chaves[i] != "mp3":
        niveis = list(QUALIDADES_VIDEO)
        j = escolher("Qual qualidade?", list(QUALIDADES_VIDEO.values()),
                     str(niveis.index(qualidade) + 1 if qualidade in niveis else 1))
        if j is None:
            return None
        qualidade = niveis[j]
    c["formato_video"], c["qualidade_video"] = chaves[i], qualidade
    salvar_cfg()
    return chaves[i], qualidade


def baixar_video(alvo: str, formato: str | None = None, qualidade: str | None = None) -> bool:
    """Baixa um link (TikTok, YouTube, Shorts, playlist...) ou o 1º resultado de uma busca."""
    if not garantir_deps_musica(com_player=False):
        return False
    garantir_storage()
    pasta_videos().mkdir(parents=True, exist_ok=True)
    if not alvo.startswith(("http://", "https://")):
        alvo = f"ytsearch1:{alvo}"
    return rodar(comando_video(alvo, formato, qualidade)).returncode == 0


def videos_locais() -> list:
    pasta = pasta_videos()
    if not pasta.exists():
        return []
    return _mais_novos_primeiro(p for p in pasta.rglob("*") if p.suffix.lower() in EXTENSOES_VIDEO)


@submenu
def menu_videos():
    c = cfg()

    def por_link():
        info("Cole um ou mais links separados por espaço (TikTok, YouTube, Shorts, playlist...).")
        links = perguntar("Link(s)").split()
        escolha = escolher_formato_video() if links else None
        if not escolha:
            return
        baixados = sum(baixar_video(link, *escolha) for link in links)
        if links:
            (ok if baixados == len(links) else aviso)(f"{baixados} de {len(links)} vídeo(s) baixado(s) em {pasta_videos()}")

    def buscar_baixar():
        termo = perguntar("Buscar no YouTube")
        if not termo or not garantir_deps_musica(com_player=False):
            return
        r = escolher_resultado(termo)
        escolha = escolher_formato_video() if r else None
        if escolha and baixar_video(r["url"], *escolha):
            ok(f"Salvo em {pasta_videos()}")

    def abrir():
        videos = videos_locais()
        if not videos:
            info(f"Nenhum vídeo em {pasta_videos()}.")
            return
        i = escolher("Qual vídeo?", [f"{v.name} ({bytes_humanos(tamanho(v))})" for v in videos])
        if i is None:
            return
        if tem("termux-open"):
            abrir_no_android(str(videos[i]))  # abre no player de vídeo do Android
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
        ("Assistir um link sem baixar (VLC, MX Player...)", assistir_link_no_celular),
        (lambda: f"Pasta dos vídeos ({c['pasta_videos']})", mudar_pasta),
        ("Instalar dependências (yt-dlp, ffmpeg)", lambda: garantir_deps_musica(com_player=False)),
    ])


# ════════════════════════════════════════════════════════════════════
#  Compartilhar filme/vídeo por link (servidor de vídeo)
# ════════════════════════════════════════════════════════════════════
# Um servidor próprio, separado da API: só entrega os vídeos que você
# compartilhou, cada um com um link secreto (e prazo opcional). O vídeo
# pode ser um arquivo do celular, um link direto da internet (servidor
# seu, nuvem, serviços de debrid...) ou uma página de vídeo (YouTube,
# Vimeo... achada pelo yt-dlp), repassados sem baixar o filme inteiro.
# O que o navegador toca é entregue como está (HTTP Range: dá para pular
# para qualquer ponto). O resto (MKV, áudio AC3/DTS, várias trilhas de
# áudio) o ffmpeg converte na hora, copiando o vídeo e recodificando só o
# áudio; o player troca de trilha pedindo uma nova conversão.

TIPOS_VIDEO = {".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm",
               ".mkv": "video/x-matroska", ".mov": "video/quicktime", ".avi": "video/x-msvideo"}
FORMATOS_NAVEGADOR = (".mp4", ".m4v", ".webm")
VIDEO_NAVEGADOR = ("h264", "vp8", "vp9", "av1")
AUDIO_NAVEGADOR = ("aac", "mp3", "opus", "vorbis")
CODECS_LEGENDA_TEXTO = {"subrip", "srt", "ass", "ssa", "webvtt", "mov_text", "text"}
LINGUAS_PT = ("por", "pt", "pob", "ptb", "pt-br")
LEGENDAS_CACHE = DATA_DIR / "cache" / "legendas"
VLC_ANDROID = "org.videolan.vlc"

IDIOMAS = {
    "por": "Português", "pt": "Português", "pob": "Português (BR)", "ptb": "Português (BR)", "pt-br": "Português (BR)",
    "eng": "Inglês", "en": "Inglês", "spa": "Espanhol", "es": "Espanhol", "fre": "Francês", "fra": "Francês",
    "fr": "Francês", "ger": "Alemão", "deu": "Alemão", "de": "Alemão", "ita": "Italiano", "it": "Italiano",
    "jpn": "Japonês", "ja": "Japonês", "kor": "Coreano", "ko": "Coreano", "chi": "Chinês", "zho": "Chinês",
    "zh": "Chinês", "rus": "Russo", "ru": "Russo", "hin": "Hindi", "ara": "Árabe", "tur": "Turco", "pol": "Polonês",
}
CANAIS = {1: "mono", 2: "estéreo", 6: "5.1", 8: "7.1"}


PAGINA_FILME = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="#000000">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%8E%AC%3C/text%3E%3C/svg%3E">
<title>@TITULO@</title>
<style>
 :root{--acc:#8b5cf6;--acc2:#a78bfa;--txt:#f4f4f5;--sub:#a1a1aa;--painel:rgba(24,24,27,.95);--borda:rgba(255,255,255,.1)}
 *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
 html,body{margin:0;height:100%;background:#000;color:var(--txt);overflow:hidden;
  font:15px/1.4 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
 button{font:inherit;color:inherit;background:none;border:0;padding:0;cursor:pointer}
 button:focus-visible{outline:2px solid var(--acc2);outline-offset:2px}
 #player{position:fixed;inset:0;background:#000;user-select:none;-webkit-user-select:none;touch-action:manipulation}
 #player.ocioso{cursor:none}
 video{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#000}
 .camada{position:absolute;left:0;right:0;transition:opacity .25s;pointer-events:none}
 .camada>*{pointer-events:auto}
 #player.ocioso .camada{opacity:0}
 #player.ocioso .camada *{pointer-events:none}
 #topo{top:0;padding:max(14px,env(safe-area-inset-top)) 18px 48px;background:linear-gradient(rgba(0,0,0,.8),transparent);
  display:flex;align-items:center;gap:10px}
 #voltar{display:grid;place-items:center;width:38px;height:38px;border-radius:50%;flex:none;color:#fff;background:rgba(255,255,255,.1)}
 #voltar svg{width:22px;height:22px;fill:currentColor}
 #voltar[hidden]{display:none}
 #topo h1{margin:0;font-size:1.05em;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  text-shadow:0 1px 3px #000;pointer-events:none}
 #baixo{bottom:0;padding:56px max(12px,env(safe-area-inset-right)) max(8px,env(safe-area-inset-bottom)) max(12px,env(safe-area-inset-left));
  background:linear-gradient(transparent,rgba(0,0,0,.88))}
 #barra{position:relative;height:24px;display:flex;align-items:center;cursor:pointer;touch-action:none;margin:0 6px}
 #trilho{position:relative;width:100%;height:4px;border-radius:4px;background:rgba(255,255,255,.22);transition:height .15s}
 #barra:hover #trilho,#barra.arrastando #trilho{height:6px}
 #buf,#prog{position:absolute;left:0;top:0;bottom:0;border-radius:inherit}
 #buf{background:rgba(255,255,255,.35)}
 #prog{background:var(--acc)}
 #bola{position:absolute;top:50%;left:0;width:14px;height:14px;margin:-7px 0 0 -7px;border-radius:50%;background:#fff;
  box-shadow:0 0 0 4px rgba(139,92,246,.45);transform:scale(0);transition:transform .15s}
 #barra:hover #bola,#barra.arrastando #bola,#player.toque #bola{transform:scale(1)}
 #dica{position:absolute;bottom:28px;left:0;transform:translateX(-50%);background:var(--painel);border:1px solid var(--borda);
  padding:3px 8px;border-radius:6px;font-size:.8em;font-variant-numeric:tabular-nums;display:none;pointer-events:none}
 #barra:hover #dica,#barra.arrastando #dica{display:block}
 #linha{display:flex;align-items:center;gap:2px}
 .bt{position:relative;width:44px;height:44px;display:grid;place-items:center;border-radius:50%;transition:background .15s,color .15s}
 .bt:hover{background:rgba(255,255,255,.12)}
 .bt svg{width:26px;height:26px;fill:currentColor}
 .bt.ativo{color:var(--acc2)}
 .bt.ativo::after{content:"";position:absolute;bottom:6px;left:14px;right:14px;height:2px;border-radius:2px;background:var(--acc2)}
 .bt[hidden]{display:none}
 #vol{width:84px;accent-color:var(--acc);margin:0 6px}
 #tempo{font-variant-numeric:tabular-nums;font-size:.88em;color:#e4e4e7;padding:0 8px;white-space:nowrap}
 .esp{flex:1}
 #centro{position:absolute;inset:0;display:grid;place-items:center;pointer-events:none}
 #grande{width:78px;height:78px;border-radius:50%;background:rgba(139,92,246,.92);display:grid;place-items:center;
  pointer-events:auto;box-shadow:0 10px 34px rgba(0,0,0,.55);transition:transform .15s,opacity .2s}
 #grande:hover{transform:scale(1.07)}
 #grande svg{width:42px;height:42px;fill:#fff}
 #girando{display:none;width:58px;height:58px;border-radius:50%;border:4px solid rgba(255,255,255,.18);
  border-top-color:var(--acc2);animation:gira .8s linear infinite}
 @keyframes gira{to{transform:rotate(360deg)}}
 #player.carregando #girando{display:block}
 #player.carregando #grande,#player.tocando #grande{display:none}
 #legenda{position:absolute;left:4%;right:4%;bottom:7%;text-align:center;pointer-events:none;transition:bottom .25s;
  font-size:calc(var(--tam,1) * clamp(17px,3.8vmin,36px));line-height:1.45}
 #player:not(.ocioso) #legenda{bottom:calc(7% + 76px)}
 #legenda span{background:rgba(0,0,0,.7);padding:.06em .38em;border-radius:5px;text-shadow:0 1px 2px #000;
  -webkit-box-decoration-break:clone;box-decoration-break:clone}
 #aviso{position:absolute;top:max(64px,calc(env(safe-area-inset-top) + 50px));left:50%;transform:translateX(-50%);
  max-width:min(92%,520px);text-align:center;background:var(--painel);border:1px solid var(--borda);padding:9px 16px;
  border-radius:12px;font-size:.9em;opacity:0;transition:opacity .2s;pointer-events:none}
 #aviso.ver{opacity:1}
 .pulo{position:absolute;top:50%;transform:translateY(-50%);padding:14px 20px;border-radius:40px;background:rgba(0,0,0,.6);
  font-weight:700;opacity:0;transition:opacity .35s;pointer-events:none;font-variant-numeric:tabular-nums}
 #puloE{left:10%}
 #puloD{right:10%}
 .pulo.ver{opacity:1;transition:none}
 #painel{position:absolute;right:12px;bottom:92px;width:320px;max-width:calc(100% - 24px);max-height:min(62%,460px);overflow:auto;
  background:var(--painel);border:1px solid var(--borda);border-radius:16px;padding:6px;display:none;
  -webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);box-shadow:0 14px 44px rgba(0,0,0,.6)}
 #painel.ver{display:block}
 #painel h3{display:flex;align-items:center;gap:6px;margin:4px 6px 4px;font-size:.78em;text-transform:uppercase;
  letter-spacing:.07em;color:var(--sub);font-weight:600;min-height:32px}
 #painel h3 button{display:grid;place-items:center;width:30px;height:30px;border-radius:50%}
 #painel h3 svg{width:20px;height:20px;fill:currentColor}
 .item{display:flex;align-items:center;gap:10px;width:100%;text-align:left;padding:10px 12px;border-radius:10px}
 .item:hover{background:rgba(255,255,255,.08)}
 .item .marca{width:20px;height:20px;flex:none;fill:var(--acc2);visibility:hidden}
 .item.sel .marca{visibility:visible}
 .item.sel{color:#fff;font-weight:600}
 .item .dir{margin-left:auto;color:var(--sub);font-size:.86em;white-space:nowrap;font-weight:400}
 .item small{display:block;color:var(--sub);font-size:.8em;font-weight:400}
 #cartao{position:absolute;inset:0;display:none;place-items:center;padding:20px;background:rgba(0,0,0,.62)}
 #cartao.ver{display:grid}
 #cartao .caixa{width:100%;max-width:440px;text-align:center;background:var(--painel);border:1px solid var(--borda);
  border-radius:18px;padding:22px 20px;box-shadow:0 14px 44px rgba(0,0,0,.6)}
 #cartao h2{margin:0 0 8px;font-size:1.15em}
 #cartao p{margin:0 0 18px;color:var(--sub)}
 .botoes{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
 .botao{padding:11px 20px;border-radius:99px;background:rgba(255,255,255,.1);font-weight:600}
 .botao:hover{background:rgba(255,255,255,.18)}
 .botao.pri{background:var(--acc)}
 .botao.pri:hover{background:#7c3aed}
 @media (max-width:640px){
  #vol{display:none}
  .bt{width:40px;height:40px}
  .bt svg{width:24px;height:24px}
  #tempo{padding:0 4px;font-size:.82em}
  #painel{left:8px;right:8px;width:auto;max-width:none;bottom:84px}
 }
 @media (max-width:400px){.opcional{display:none}}
 @media (pointer:coarse){#vol{display:none}}
</style></head><body>
<div id="player" class="carregando">
 <video id="v" playsinline preload="metadata"></video>
 <div id="legenda"></div>
 <div id="centro"><button id="grande" aria-label="Assistir"></button><div id="girando"></div></div>
 <div class="pulo" id="puloE"></div><div class="pulo" id="puloD"></div>
 <div id="topo" class="camada"><a id="voltar" hidden title="Voltar à biblioteca" aria-label="Voltar à biblioteca"></a><h1>@TITULO@</h1></div>
 <div id="baixo" class="camada">
  <div id="barra" role="slider" aria-label="Posição no vídeo">
   <div id="trilho"><div id="buf"></div><div id="prog"></div></div><div id="bola"></div><div id="dica">0:00</div>
  </div>
  <div id="linha">
   <button class="bt" id="btPlay" title="Assistir / pausar (espaço)"></button>
   <button class="bt" id="btVolta" title="Voltar 10 s (←)"></button>
   <button class="bt" id="btAvanca" title="Avançar 10 s (→)"></button>
   <button class="bt opcional" id="btSom" title="Som (M)"></button>
   <input type="range" id="vol" min="0" max="1" step="0.05" value="1" aria-label="Volume">
   <span id="tempo">0:00</span>
   <span class="esp"></span>
   <button class="bt" id="btAudio" title="Trilha de áudio (A)" hidden></button>
   <button class="bt" id="btLegenda" title="Legendas (C)" hidden></button>
   <button class="bt" id="btProximo" title="Próximo episódio (N)" hidden></button>
   <button class="bt" id="btAjustes" title="Ajustes"></button>
   <button class="bt opcional" id="btPip" title="Janela flutuante" hidden></button>
   <button class="bt" id="btTela" title="Tela cheia (F)"></button>
  </div>
 </div>
 <div id="painel" role="menu"></div>
 <div id="aviso" role="status"></div>
 <div id="cartao"><div class="caixa"><h2 id="cTit"></h2><p id="cTxt"></p><div class="botoes" id="cBot"></div></div></div>
</div>
<script id="cfg" type="application/json">@CONFIG@</script>
<script>
(function () {
 'use strict';
 var C = JSON.parse(document.getElementById('cfg').textContent);
 function $(id) { return document.getElementById(id); }
 var v = $('v'), P = $('player'), BASE = '/v/' + C.token, CHAVE = 'toons:' + C.token;
 var ICONE = {
  play: 'M8 5v14l11-7z', pausa: 'M6 19h4V5H6v14zm8-14v14h4V5h-4z',
  som: 'M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z',
  mudo: 'M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z',
  audio: 'M12 1c-4.97 0-9 4.03-9 9v7c0 1.66 1.34 3 3 3h3v-8H5v-2c0-3.87 3.13-7 7-7s7 3.13 7 7v2h-4v8h3c1.66 0 3-1.34 3-3v-7c0-4.97-4.03-9-9-9z',
  legenda: 'M19 4H5c-1.11 0-2 .9-2 2v12c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm-8 7H9.5v-.5h-2v3h2V13H11v1c0 .55-.45 1-1 1H7c-.55 0-1-.45-1-1v-4c0-.55.45-1 1-1h3c.55 0 1 .45 1 1v1zm7 0h-1.5v-.5h-2v3h2V13H18v1c0 .55-.45 1-1 1h-3c-.55 0-1-.45-1-1v-4c0-.55.45-1 1-1h3c.55 0 1 .45 1 1v1z',
  ajustes: 'M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z',
  proximo: 'M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z',
  pip: 'M19 7h-8v6h8V7zm2-4H3c-1.1 0-2 .9-2 2v14c0 1.1.9 1.98 2 1.98h18c1.1 0 2-.88 2-1.98V5c0-1.1-.9-2-2-2zm0 16.01H3V4.98h18v14.03z',
  tela: 'M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z',
  sairTela: 'M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z',
  marca: 'M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z',
  voltar: 'M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z',
  denovo: 'M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z'
 };
 function svg(nome) { return '<svg viewBox="0 0 24 24"><path d="' + ICONE[nome] + '"/></svg>'; }
 function svgPulo(frente) {  // seta circular com "10" dentro (espelhada para avançar)
  return '<svg viewBox="0 0 24 24"><g' + (frente ? ' transform="matrix(-1 0 0 1 24 0)"' : '') + '>' +
   '<path d="M12 5A8 8 0 1 0 18.93 9" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>' +
   '<path d="M12.6 1.4L7.4 5l5.2 3.6z"/></g><text x="12" y="15.9" text-anchor="middle" font-size="7.4" ' +
   'font-weight="700" font-family="system-ui,sans-serif">10</text></svg>';
 }

 // ── Ambiente ──
 var ua = navigator.userAgent;
 var ehIOS = /iP(hone|ad|od)/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
 var ehSafari = ehIOS || (/Safari\//.test(ua) && !/Chrome|Chromium|CriOS|FxiOS|Edg|OPR|Android/.test(ua));
 var ehAndroid = /Android/.test(ua);
 function toca(tipo) { try { return !!v.canPlayType(tipo); } catch (e) { return false; } }
 var podeH264 = toca('video/mp4; codecs="avc1.640028"');
 var acodec = !toca('audio/mp4; codecs="mp4a.40.2"') && toca('audio/mp4; codecs="opus"') ? 'opus' : 'aac';

 // ── Estado ──
 var E = {
  audio: C.audio_padrao || 0, legenda: C.legenda_padrao, modo: '', base: 0, iniciado: false, geracao: 0,
  falhas: 0, forcar: false, alvo: null, arrasto: null, tam: 1, atraso: 0, vel: 1, ultimaLegenda: -1, reconexao: null,
  recod: !!(C.video && podeH264 && (!C.video.copiavel || (C.video.codecs && !toca('video/mp4; codecs="' + C.video.codecs + '"'))))
 };
 var sessao = Math.random().toString(36).slice(2, 10);
 function lerSalvo() { try { return JSON.parse(localStorage.getItem(CHAVE)) || {}; } catch (e) { return {}; } }
 function salvar(fim) {
  try {
   localStorage.setItem(CHAVE, JSON.stringify({t: fim ? 0 : agora(), d: duracao(), quando: Date.now(), a: E.audio,
                                                 l: E.legenda, tam: E.tam, at: E.atraso}));
   localStorage.setItem('toons:vol', JSON.stringify({v: v.volume, m: v.muted}));
  } catch (e) {}
 }
 var salvo = lerSalvo();
 if (typeof salvo.a === 'number' && salvo.a < C.audios.length) E.audio = salvo.a;
 if (typeof salvo.l === 'number' && salvo.l < C.legendas.length) E.legenda = salvo.l;
 if (salvo.tam) E.tam = salvo.tam;
 if (salvo.at) E.atraso = salvo.at;
 try { var vol = JSON.parse(localStorage.getItem('toons:vol')); if (vol) { v.volume = vol.v; v.muted = vol.m; } } catch (e) {}

 // Arquivo original (com HTTP Range) quando o navegador o toca; senão, conversão na hora. Sem ffmpeg no
 // celular, ou no Safari com MP4 (ele toca AC3 e HEVC e troca a trilha sozinho), tenta o original mesmo assim.
 function direto() { return !E.forcar && ((C.direto && C.audios.length <= 1) || !C.transmissao || (ehSafari && C.mp4)); }
 function trilhasNativas() { return E.modo === 'direto' && v.audioTracks && v.audioTracks.length > 1; }
 function podeTrocarAudio() { return C.audios.length > 1 && (C.transmissao || (ehSafari && C.mp4)); }
 function agora() { return (E.modo === 'transmissao' ? E.base : 0) + (v.currentTime || 0); }
 function duracao() { return C.duracao || (isFinite(v.duration) ? v.duration : 0); }
 function fmt(s) {
  s = Math.max(0, Math.floor(s || 0));
  var h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60;
  return (h ? h + ':' + (m < 10 ? '0' : '') : '') + m + ':' + (x < 10 ? '0' : '') + x;
 }

 // ── Carregar e pular ──
 function carregar(t, tocar) {
  E.iniciado = true;
  esconderCartao();
  var d = duracao(), minha = ++E.geracao;
  t = Math.max(0, d ? Math.min(t || 0, d - 1) : (t || 0));
  P.classList.add('carregando');
  if (direto()) {
   E.modo = 'direto';
   var url = BASE + '/video';
   var ir = function () { if (minha !== E.geracao) return; if (t) v.currentTime = t; if (tocar) tocarVideo(); };
   if (v.getAttribute('src') !== url) { v.src = url; v.addEventListener('loadedmetadata', ir, {once: true}); }
   else ir();
   return;
  }
  if (!C.transmissao) return falhar('Este vídeo não toca no navegador e o celular que o compartilhou não tem o ffmpeg para convertê-lo.');
  if (ehSafari) return falhar('Este vídeo é convertido na hora, e o Safari (iPhone, iPad e Mac) não aceita esse tipo de transmissão. No VLC ele abre com todas as trilhas de áudio e legendas.');
  E.modo = 'transmissao';
  var abrir = function (k) {
   if (minha !== E.geracao) return;
   E.base = k;
   v.src = BASE + '/stream?a=' + E.audio + '&t=' + k.toFixed(3) + '&ac=' + acodec + '&s=' + sessao + (E.recod ? '&v=h264' : '');
   v.defaultPlaybackRate = v.playbackRate = E.vel;
   atualizarTempo();
   if (tocar) tocarVideo();
  };
  if (t < 1) return abrir(0);
  fetch(BASE + '/ponto?t=' + t.toFixed(3)).then(function (r) { return r.ok ? r.json() : null; })
   .then(function (j) { abrir(j && typeof j.t === 'number' ? j.t : t); }, function () { abrir(t); });
 }
 function tocarVideo() {
  var p = v.play();
  if (p && p.catch) p.catch(function (e) {
   if (e && e.name === 'NotAllowedError') { P.classList.remove('carregando'); mostrarControles(); }
  });
 }
 function pular(t) {
  if (!E.iniciado) return carregar(t, true);
  var d = duracao();
  t = Math.max(0, d ? Math.min(t, d - 0.5) : t);
  if (E.modo === 'direto') { v.currentTime = t; return; }
  var rel = t - E.base, s = v.seekable;
  for (var i = 0; i < s.length; i++) if (rel >= s.start(i) && rel <= s.end(i) - 0.5) { v.currentTime = rel; return; }
  carregar(t, !v.paused || P.classList.contains('carregando'));
 }
 var tAlvo, tPulo = {};
 function pularRel(dt) {
  if (!E.iniciado) return;
  var d = duracao();
  E.alvo = Math.max(0, (E.alvo != null ? E.alvo : agora()) + dt);
  if (d) E.alvo = Math.min(E.alvo, d - 0.5);
  var lado = dt < 0 ? 'puloE' : 'puloD', el = $(lado);
  el.dataset.soma = (+(el.dataset.soma || 0) + Math.abs(dt));
  el.textContent = (dt < 0 ? '« ' : '') + el.dataset.soma + ' s' + (dt > 0 ? ' »' : '');
  el.classList.add('ver');
  clearTimeout(tPulo[lado]);
  tPulo[lado] = setTimeout(function () { el.classList.remove('ver'); el.dataset.soma = 0; }, 700);
  clearTimeout(tAlvo);
  if (E.modo === 'direto') { var alvo = E.alvo; E.alvo = null; pular(alvo); return; }
  E.arrasto = E.alvo; atualizarTempo();
  tAlvo = setTimeout(function () { var alvo = E.alvo; E.alvo = null; E.arrasto = null; pular(alvo); }, 450);
 }
 function alternar() {
  if (!E.iniciado) return carregar(retomar || 0, true);
  if (v.ended) { pular(0); return tocarVideo(); }
  if (v.paused) tocarVideo(); else v.pause();
 }

 // ── Eventos do vídeo ──
 v.addEventListener('playing', function () {
  P.classList.remove('carregando'); P.classList.add('tocando'); E.falhas = 0; atualizarPlay(); agendarOcioso();
 });
 v.addEventListener('play', atualizarPlay);
 v.addEventListener('pause', function () { P.classList.remove('tocando'); atualizarPlay(); mostrarControles(); if (E.iniciado) salvar(); });
 v.addEventListener('waiting', function () { if (E.iniciado) P.classList.add('carregando'); });
 v.addEventListener('seeking', function () { P.classList.add('carregando'); });
 v.addEventListener('seeked', function () { P.classList.remove('carregando'); desenharLegenda(); });
 v.addEventListener('canplay', function () { if (v.paused || !E.iniciado) P.classList.remove('carregando'); });
 v.addEventListener('loadeddata', function () {
  if (v.paused) P.classList.remove('carregando');
  if (!E.iniciado || !C.video || v.videoWidth) return;
  // o navegador abriu só o som: não reconhece o formato da imagem
  if (E.modo === 'transmissao' && !E.recod && podeH264) {
   E.recod = true; aviso('Recodificando o vídeo para o seu navegador…', 3500);
   return carregar(agora(), true);
  }
  if (E.modo === 'direto' && C.transmissao && !ehSafari && !E.forcar) { E.forcar = true; return carregar(agora(), true); }
  falhar('Seu navegador tocou só o som: ele não reconhece o formato da imagem deste vídeo.');
 });
 v.addEventListener('loadedmetadata', function () { if (!E.iniciado) P.classList.remove('carregando'); aplicarTrilhaNativa(); atualizarTempo(); });
 v.addEventListener('timeupdate', function () { atualizarTempo(); desenharLegenda(); });
 v.addEventListener('progress', atualizarBuffer);
 v.addEventListener('durationchange', atualizarTempo);
 v.addEventListener('volumechange', atualizarSom);
 v.addEventListener('ended', function () {
  var d = duracao(), t = agora();
  if (E.modo === 'transmissao' && d && t < d - 5) {  // a conexão caiu antes do fim do filme
   var r = E.reconexao;
   if (!r || t - r > 5) { E.reconexao = t; aviso('Reconectando…'); return carregar(t, true); }
  }
  P.classList.remove('tocando', 'carregando'); atualizarPlay(true); mostrarControles(); salvar(true);
  if (C.proximo) cartao('Próximo episódio', C.proximo.titulo, [['Assistir', proximo, true], ['Rever este', function () { pular(0); tocarVideo(); }]]);
 });
 v.addEventListener('error', function () {
  if (!v.error || !v.getAttribute('src')) return;
  var t = agora();
  if (E.modo === 'direto') {
   if (C.transmissao && !ehSafari) {  // o navegador não toca o arquivo original: passa a converter na hora
    E.forcar = true;
    if (!E.iniciado) { E.modo = ''; P.classList.remove('carregando'); return; }
    aviso('Convertendo na hora para o seu navegador…');
    return carregar(t, true);
   }
   return E.iniciado ? falhar('Seu navegador não conseguiu reproduzir este vídeo.') : P.classList.remove('carregando');
  }
  if (!E.iniciado) return;
  fetch(BASE + '/estado').then(function (r) {
   if (r.status === 410) return {ok: false, erro: 'Este link expirou.'};
   if (r.status === 404) return {ok: false, erro: 'Este link foi apagado ou o vídeo não está mais disponível.'};
   return r.json();
  }).then(function (j) {
   if (!j.ok) return falhar(j.erro);
   E.falhas++;
   if (E.falhas <= 2) { aviso('Reconectando…'); return setTimeout(function () { carregar(t, true); }, 1200); }
   if (!E.recod && podeH264 && C.video) {
    E.recod = true; E.falhas = 0;
    aviso('Recodificando o vídeo para o seu navegador…', 3500);
    return carregar(t, true);
   }
   falhar('Seu navegador não conseguiu reproduzir este vídeo.');
  }, function () { falhar('Sem conexão com o celular que está transmitindo.'); });
 });

 // ── Tempo, barra e botões ──
 function atualizarTempo() {
  var d = duracao(), t = E.arrasto != null ? E.arrasto : E.iniciado ? agora() : (retomar || 0);
  $('tempo').textContent = fmt(t) + (d ? ' / ' + fmt(d) : '');
  var f = d ? Math.min(1, t / d) : 0;
  $('prog').style.width = (f * 100) + '%';
  $('bola').style.left = (f * 100) + '%';
  $('barra').setAttribute('aria-valuenow', Math.floor(t));
  atualizarBuffer();
 }
 function atualizarBuffer() {
  var d = duracao(), b = v.buffered, ini = 0, fim = 0, base = E.modo === 'transmissao' ? E.base : 0;
  for (var i = 0; i < b.length; i++) if (b.start(i) <= v.currentTime + 1 && b.end(i) >= v.currentTime) { ini = b.start(i); fim = b.end(i); }
  $('buf').style.left = d ? ((base + ini) / d * 100) + '%' : '0';
  $('buf').style.width = d && fim ? (Math.min(fim - ini, d) / d * 100) + '%' : '0';
 }
 function atualizarPlay(fim) {
  var tocando = !v.paused && !v.ended;
  $('btPlay').innerHTML = svg(tocando ? 'pausa' : 'play');
  $('grande').innerHTML = svg(fim === true ? 'denovo' : 'play');
 }
 function atualizarSom() { $('btSom').innerHTML = svg(v.muted || v.volume === 0 ? 'mudo' : 'som'); $('vol').value = v.muted ? 0 : v.volume; }
 function atualizarBotoes() {
  $('btAudio').hidden = !podeTrocarAudio();
  $('btLegenda').hidden = !C.legendas.length;
  $('btLegenda').classList.toggle('ativo', E.legenda >= 0);
  $('legenda').style.setProperty('--tam', E.tam);
 }
 function emTela() { return document.fullscreenElement || document.webkitFullscreenElement; }
 function atualizarTela() { $('btTela').innerHTML = svg(emTela() ? 'sairTela' : 'tela'); }
 function alternarTela() {
  if (emTela()) return (document.exitFullscreen || document.webkitExitFullscreen).call(document);
  var pedir = P.requestFullscreen || P.webkitRequestFullscreen;
  if (!pedir) { if (v.webkitEnterFullscreen) { trilhaNativa(); v.webkitEnterFullscreen(); } return; }
  var r = pedir.call(P);
  var girar = function () {
   if (v.videoWidth > v.videoHeight && screen.orientation && screen.orientation.lock) screen.orientation.lock('landscape').catch(function () {});
  };
  if (r && r.then) r.then(girar, function () {}); else girar();
 }
 function trilhaNativa() {  // tela cheia do iPhone usa o player do sistema, que só mostra legendas de <track>
  var velha = v.querySelector('track');
  if (velha) velha.remove();
  if (E.legenda < 0 || E.modo !== 'direto') return;
  var tr = document.createElement('track');
  tr.kind = 'subtitles'; tr.srclang = 'pt'; tr.label = C.legendas[E.legenda].rotulo; tr.default = true;
  tr.src = BASE + '/legenda/' + E.legenda + '.vtt';
  v.appendChild(tr);
 }
 v.addEventListener('webkitendfullscreen', function () { var tr = v.querySelector('track'); if (tr) tr.remove(); });
 document.addEventListener('fullscreenchange', atualizarTela);
 document.addEventListener('webkitfullscreenchange', atualizarTela);

 function ao(id, fn) { $(id).addEventListener('click', function (ev) { ev.stopPropagation(); this.blur(); fn(ev); mostrarControles(); }); }
 ao('btPlay', alternar);
 ao('grande', alternar);
 ao('btVolta', function () { pularRel(-10); });
 ao('btAvanca', function () { pularRel(10); });
 ao('btSom', function () { v.muted = !v.muted; if (!v.muted && v.volume === 0) v.volume = 1; });
 ao('btTela', alternarTela);
 ao('btAudio', function () { abrirPainel('audio'); });
 ao('btLegenda', function () { abrirPainel('legenda'); });
 ao('btAjustes', function () { abrirPainel('ajustes'); });
 ao('btPip', function () {
  if (document.pictureInPictureElement) document.exitPictureInPicture();
  else v.requestPictureInPicture().catch(function () { aviso('Janela flutuante indisponível.'); });
 });
 $('vol').addEventListener('input', function () { v.volume = +this.value; v.muted = v.volume === 0; });
 $('vol').addEventListener('change', function () { this.blur(); salvar(); });

 var barra = $('barra');
 function fracao(ev) { var r = $('trilho').getBoundingClientRect(); return Math.min(1, Math.max(0, (ev.clientX - r.left) / r.width)); }
 function dica(ev) { var f = fracao(ev); $('dica').textContent = fmt(f * duracao()); $('dica').style.left = (f * 100) + '%'; }
 barra.addEventListener('pointerdown', function (ev) {
  if (!duracao() || !E.iniciado) return;
  ev.preventDefault(); ev.stopPropagation();
  barra.setPointerCapture(ev.pointerId); barra.classList.add('arrastando');
  E.arrasto = fracao(ev) * duracao(); dica(ev); atualizarTempo(); mostrarControles();
 });
 barra.addEventListener('pointermove', function (ev) {
  if (!duracao()) return;
  dica(ev);
  if (E.arrasto != null && barra.classList.contains('arrastando')) { E.arrasto = fracao(ev) * duracao(); atualizarTempo(); mostrarControles(); }
 });
 function soltar(ev, pularPara) {
  if (!barra.classList.contains('arrastando')) return;
  barra.classList.remove('arrastando');
  var t = E.arrasto; E.arrasto = null;
  if (pularPara && t != null) pular(t); else atualizarTempo();
 }
 barra.addEventListener('pointerup', function (ev) { soltar(ev, true); });
 barra.addEventListener('pointercancel', function (ev) { soltar(ev, false); });
 barra.addEventListener('click', function (ev) { ev.stopPropagation(); });

 // ── Controles somem sozinhos; toque duplo pula 10 s ──
 var tOcioso;
 function mostrarControles() { P.classList.remove('ocioso'); agendarOcioso(); }
 function agendarOcioso() {
  clearTimeout(tOcioso);
  tOcioso = setTimeout(function () { if (!v.paused && !painelAberto() && E.arrasto == null) P.classList.add('ocioso'); }, 3000);
 }
 var ponteiro = 'mouse', ultimoToque = 0, tToque, ladoPulo = null, ladoAte = 0;
 P.addEventListener('pointerdown', function (ev) { ponteiro = ev.pointerType; P.classList.toggle('toque', ponteiro !== 'mouse'); }, true);
 P.addEventListener('pointermove', function (ev) { if (ev.pointerType === 'mouse') mostrarControles(); });
 P.addEventListener('click', function (ev) {
  if (ev.target.closest('button, input, #painel, #barra, #linha, #cartao')) return;
  if (painelAberto()) return fecharPainel();
  if (!E.iniciado) return alternar();
  if (ponteiro === 'mouse') return alternar();
  var x = ev.clientX / P.clientWidth, lado = x < 0.4 ? -10 : x > 0.6 ? 10 : 0, t = Date.now();
  if (lado && ladoPulo === lado && t < ladoAte) { ladoAte = t + 700; return pularRel(lado); }  // toques seguidos somam
  if (t - ultimoToque < 300) {
   clearTimeout(tToque); ultimoToque = 0;
   if (lado) { ladoPulo = lado; ladoAte = t + 700; pularRel(lado); } else alternarTela();
   return;
  }
  ultimoToque = t;
  tToque = setTimeout(function () {
   if (P.classList.contains('ocioso')) mostrarControles();
   else if (!v.paused) { clearTimeout(tOcioso); P.classList.add('ocioso'); }
  }, 260);
 });
 P.addEventListener('dblclick', function (ev) { if (ponteiro === 'mouse' && !ev.target.closest('button, input, #painel, #barra, #cartao')) alternarTela(); });

 document.addEventListener('keydown', function (ev) {
  if (ev.ctrlKey || ev.metaKey || ev.altKey || ev.target.tagName === 'INPUT') return;
  var k = ev.key, feito = true;
  if (k === ' ' || k === 'k' || k === 'K' || k === 'MediaPlayPause') alternar();
  else if (k === 'ArrowLeft' || k === 'j' || k === 'J') pularRel(-10);
  else if (k === 'ArrowRight' || k === 'l' || k === 'L') pularRel(10);
  else if (k === 'ArrowUp' || k === 'ArrowDown') {
   v.muted = false; v.volume = Math.round(Math.max(0, Math.min(1, v.volume + (k === 'ArrowUp' ? 0.1 : -0.1))) * 10) / 10;
   aviso('Volume ' + Math.round(v.volume * 100) + '%', 900);
  }
  else if (k === 'f' || k === 'F') alternarTela();
  else if (k === 'm' || k === 'M') v.muted = !v.muted;
  else if (k === 'c' || k === 'C') alternarLegenda();
  else if (k === 'a' || k === 'A') { if (podeTrocarAudio()) trocarAudio((E.audio + 1) % C.audios.length); }
  else if (k === 'Escape' && painelAberto()) fecharPainel();
  else if ((k === 'n' || k === 'N') && C.proximo) proximo();
  else if (/^[0-9]$/.test(k) && duracao() && E.iniciado) pular(duracao() * (+k) / 10);
  else feito = false;
  if (feito) { ev.preventDefault(); mostrarControles(); }
 });

 // ── Menus: áudio, legendas e ajustes ──
 var painel = $('painel'), painelAtual = '';
 function painelAberto() { return painel.classList.contains('ver'); }
 function fecharPainel() { painel.classList.remove('ver'); painelAtual = ''; agendarOcioso(); }
 function abrirPainel(nome) { if (painelAtual === nome) return fecharPainel(); mostrarPainel(nome); }
 function rotuloAtraso() { return (E.atraso > 0 ? '+' : '') + E.atraso.toFixed(1).replace('.', ',') + ' s'; }
 var PAINEIS = {
  audio: function () {
   return {titulo: 'Trilha de áudio', itens: C.audios.map(function (a, i) {
    return {rotulo: a.rotulo, sel: i === E.audio, acao: function () { fecharPainel(); trocarAudio(i); }};
   })};
  },
  legenda: function () {
   var itens = [{rotulo: 'Desligada', sel: E.legenda < 0, acao: function () { fecharPainel(); trocarLegenda(-1); }}];
   C.legendas.forEach(function (l, i) {
    itens.push({rotulo: l.rotulo, sel: i === E.legenda, acao: function () { fecharPainel(); trocarLegenda(i); }});
   });
   itens.push({rotulo: 'Tamanho', dir: Math.round(E.tam * 100) + '%', acao: function () { mostrarPainel('tamanho'); }});
   itens.push({rotulo: 'Sincronia', dir: rotuloAtraso(), acao: function () { mostrarPainel('sincronia'); }});
   return {titulo: 'Legendas', itens: itens};
  },
  tamanho: function () {
   return {titulo: 'Tamanho da legenda', voltar: 'legenda', itens: [0.75, 1, 1.25, 1.5, 2].map(function (x) {
    return {rotulo: Math.round(x * 100) + '%', sel: x === E.tam, acao: function () { E.tam = x; atualizarBotoes(); salvar(); mostrarPainel('tamanho'); }};
   })};
  },
  sincronia: function () {
   var mudar = function (d) { return function () { E.atraso = Math.round((E.atraso + d) * 10) / 10; salvar(); desenharLegenda(); mostrarPainel('sincronia'); }; };
   return {titulo: 'Sincronia: ' + rotuloAtraso(), voltar: 'legenda', itens: [
    {rotulo: 'Legenda aparece cedo demais', sub: 'atrasar 0,5 s', acao: mudar(0.5)},
    {rotulo: 'Legenda aparece tarde demais', sub: 'adiantar 0,5 s', acao: mudar(-0.5)},
    {rotulo: 'Zerar', acao: function () { E.atraso = 0; salvar(); desenharLegenda(); mostrarPainel('sincronia'); }}
   ]};
  },
  velocidade: function () {
   return {titulo: 'Velocidade', voltar: 'ajustes', itens: [0.5, 0.75, 1, 1.25, 1.5, 2].map(function (x) {
    return {rotulo: x === 1 ? 'Normal' : String(x).replace('.', ',') + 'x', sel: x === E.vel,
            acao: function () { E.vel = x; v.defaultPlaybackRate = v.playbackRate = x; mostrarPainel('velocidade'); }};
   })};
  },
  ajustes: function () {
   var itens = [{rotulo: 'Velocidade', dir: E.vel === 1 ? 'Normal' : String(E.vel).replace('.', ',') + 'x', acao: function () { mostrarPainel('velocidade'); }}];
   if (C.transmissao && C.video && C.video.copiavel && podeH264 && !direto() && !ehSafari) {
    itens.push({rotulo: 'Imagem', sub: E.recod ? 'recodificada: toca em mais aparelhos, mas pesa no celular que transmite'
                                              : 'original: melhor qualidade', dir: E.recod ? 'Compatível' : 'Original',
     acao: function () { E.recod = !E.recod; fecharPainel(); aviso(E.recod ? 'Imagem compatível' : 'Imagem original'); if (E.iniciado) carregar(agora(), !v.paused); }});
   }
   itens.push({rotulo: 'Abrir no VLC', sub: 'todas as trilhas de áudio e legendas', acao: function () { fecharPainel(); abrirFora(true); }});
   if (ehAndroid) itens.push({rotulo: 'Abrir em outro app', sub: 'MX Player, Just Player…', acao: function () { fecharPainel(); abrirFora(false); }});
   itens.push({rotulo: 'Copiar link do vídeo', sub: 'para colar no VLC, Kodi, TV…', acao: function () { fecharPainel(); copiar(linkArquivo(), 'Link copiado.'); }});
   if (matchMedia('(pointer: fine)').matches) itens.push({rotulo: 'Atalhos do teclado', sub: 'espaço · ← → 10 s · ↑ ↓ volume · F tela cheia · M mudo · C legenda · A áudio · 0–9 posição', acao: function () {}});
   return {titulo: 'Ajustes', itens: itens};
  }
 };
 function mostrarPainel(nome) {
  var spec = PAINEIS[nome]();
  painelAtual = nome; painel.innerHTML = '';
  var h = document.createElement('h3');
  if (spec.voltar) {
   var b = document.createElement('button'); b.innerHTML = svg('voltar'); b.setAttribute('aria-label', 'Voltar');
   b.onclick = function (ev) { ev.stopPropagation(); mostrarPainel(spec.voltar); };
   h.appendChild(b);
  }
  h.appendChild(document.createTextNode(spec.titulo));
  painel.appendChild(h);
  spec.itens.forEach(function (it) {
   var el = document.createElement('button');
   el.className = 'item' + (it.sel ? ' sel' : ''); el.setAttribute('role', 'menuitem');
   el.innerHTML = '<svg class="marca" viewBox="0 0 24 24"><path d="' + ICONE.marca + '"/></svg><span></span>';
   var texto = el.querySelector('span'); texto.textContent = it.rotulo;
   if (it.sub) { var s = document.createElement('small'); s.textContent = it.sub; texto.appendChild(s); }
   if (it.dir) { var d = document.createElement('span'); d.className = 'dir'; d.textContent = it.dir; el.appendChild(d); }
   el.onclick = function (ev) { ev.stopPropagation(); it.acao(); };
   painel.appendChild(el);
  });
  painel.classList.add('ver'); mostrarControles();
 }

 function trocarAudio(i) {
  if (i === E.audio) return;
  E.audio = i; salvar();
  aviso('Áudio: ' + C.audios[i].rotulo);
  if (trilhasNativas()) aplicarTrilhaNativa();
  else if (E.iniciado && E.modo === 'transmissao') carregar(agora(), !v.paused || P.classList.contains('carregando'));
 }
 function aplicarTrilhaNativa() {  // Safari: troca a trilha do próprio arquivo, sem conversão
  if (!trilhasNativas()) return;
  for (var i = 0; i < v.audioTracks.length; i++) v.audioTracks[i].enabled = i === E.audio;
 }

 // ── Legendas (desenhadas pelo player: funcionam também na transmissão convertida) ──
 var cues = [], cacheLeg = {}, legHtml = null;
 function alternarLegenda() {
  if (!C.legendas.length) return;
  if (E.legenda >= 0) { E.ultimaLegenda = E.legenda; trocarLegenda(-1); }
  else trocarLegenda(E.ultimaLegenda >= 0 ? E.ultimaLegenda : Math.max(0, C.legenda_padrao));
 }
 function trocarLegenda(i, calado) {
  E.legenda = i; cues = []; salvar(); atualizarBotoes(); desenharLegenda();
  if (!calado) aviso(i < 0 ? 'Legenda desligada' : 'Legenda: ' + C.legendas[i].rotulo);
  if (i < 0) return;
  if (cacheLeg[i]) { cues = cacheLeg[i]; desenharLegenda(); return; }
  baixarLegenda(i, 0);
 }
 function baixarLegenda(i, tentativa) {
  fetch(BASE + '/legenda/' + i + '.vtt').then(function (r) {
   if (r.status === 202) {
    if (E.legenda !== i) return null;
    if (tentativa % 10 === 0) aviso(C.remoto ? 'Preparando a legenda: o celular que transmite precisa ler o vídeo inteiro uma vez. Pode levar alguns minutos.' : 'Preparando a legenda…', 4000);
    setTimeout(function () { if (E.legenda === i) baixarLegenda(i, tentativa + 1); }, 3000);
    return null;
   }
   if (!r.ok) throw new Error('HTTP ' + r.status);
   return r.text();
  }).then(function (txt) {
   if (txt == null) return;
   cacheLeg[i] = lerVTT(txt);
   if (E.legenda === i) { cues = cacheLeg[i]; desenharLegenda(); if (tentativa) aviso('Legenda pronta.'); }
  }).catch(function () { if (E.legenda === i) aviso('Não consegui carregar essa legenda.'); });
 }
 function segundos(s) { var t = 0; s.replace(',', '.').split(':').forEach(function (x) { t = t * 60 + parseFloat(x); }); return t; }
 function limparTexto(t) {
  t = t.replace(/\{\\[^}]*\}/g, '').replace(/<(?!\/?[ibu]>)[^>]*>/gi, '')
   .replace(/&nbsp;/g, ' ').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
  var div = document.createElement('div'); div.textContent = t;
  return div.innerHTML.replace(/&lt;(\/?)([ibu])&gt;/gi, '<$1$2>').replace(/\n/g, '<br>');
 }
 function lerVTT(txt) {
  var lista = [];
  txt.replace(/\r/g, '').split(/\n{2,}/).forEach(function (bloco) {
   var linhas = bloco.split('\n'), i = 0;
   while (i < linhas.length && linhas[i].indexOf('-->') < 0) i++;
   if (i >= linhas.length) return;
   var m = linhas[i].match(/((?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})\s*-->\s*((?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})/);
   var texto = linhas.slice(i + 1).join('\n').trim();
   if (m && texto) lista.push({i: segundos(m[1]), f: segundos(m[2]), html: limparTexto(texto)});
  });
  return lista.sort(function (a, b) { return a.i - b.i; });
 }
 function desenharLegenda() {
  var t = agora() - E.atraso, html = '';
  if (E.legenda >= 0) {
   for (var i = 0; i < cues.length && cues[i].i <= t; i++) {
    if (t < cues[i].f) html += (html ? '<br>' : '') + '<span>' + cues[i].html + '</span>';
   }
  }
  if (html !== legHtml) { legHtml = html; $('legenda').innerHTML = html; }
 }
 var ultimoQuadro = 0;
 (function quadro(ms) {
  if (!v.paused && ms - ultimoQuadro > 100) { ultimoQuadro = ms; desenharLegenda(); atualizarTempo(); }
  requestAnimationFrame(quadro);
 })(0);

 // ── Abrir fora do navegador (VLC...) ──
 function linkArquivo() { return location.origin + BASE + '/video'; }
 function abrirFora(vlc) {
  var url = linkArquivo();
  v.pause();
  if (ehAndroid) {
   location.href = 'intent://' + url.replace(/^https?:\/\//, '') + '#Intent;scheme=' + location.protocol.replace(':', '') +
    ';action=android.intent.action.VIEW;type=video/*' + (vlc ? ';package=org.videolan.vlc' : '') +
    ';S.title=' + encodeURIComponent(C.titulo) + ';end';
  } else if (ehIOS && vlc) {
   location.href = 'vlc-x-callback://x-callback-url/stream?url=' + encodeURIComponent(url);
  } else {
   copiar(url, 'Link copiado. No VLC: Mídia → Abrir fluxo de rede (Ctrl+N) e cole o link.');
  }
 }
 function copiar(texto, msg) {
  var feito = function () { aviso(msg, 4000); };
  var velho = function () {
   var t = document.createElement('textarea'); t.value = texto; t.style.position = 'fixed'; t.style.opacity = '0';
   document.body.appendChild(t); t.select(); var r = false;
   try { r = document.execCommand('copy'); } catch (e) {}
   t.remove();
   if (r) feito(); else window.prompt('Copie o link:', texto);
  };
  if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(texto).then(feito, velho);
  else velho();
 }

 // ── Avisos e cartões ──
 var tAviso;
 function aviso(msg, ms) {
  var a = $('aviso'); a.textContent = msg; a.classList.add('ver');
  clearTimeout(tAviso); tAviso = setTimeout(function () { a.classList.remove('ver'); }, ms || 2200);
 }
 function cartao(titulo, texto, botoes) {
  $('cTit').textContent = titulo; $('cTxt').textContent = texto;
  var cb = $('cBot'); cb.innerHTML = '';
  botoes.forEach(function (b) {
   var el = document.createElement('button'); el.className = 'botao' + (b[2] ? ' pri' : ''); el.textContent = b[0];
   el.onclick = function (ev) { ev.stopPropagation(); esconderCartao(); b[1](); };
   cb.appendChild(el);
  });
  $('cartao').classList.add('ver');
  P.classList.remove('ocioso');
 }
 function esconderCartao() { $('cartao').classList.remove('ver'); }
 function falhar(msg) {
  ++E.geracao;
  if (!v.paused) v.pause();
  P.classList.remove('carregando', 'tocando'); atualizarPlay();
  var botoes = [['Abrir no VLC', function () { abrirFora(true); }, true]];
  if (ehAndroid) botoes.push(['Outro app', function () { abrirFora(false); }]);
  botoes.push(['Tentar de novo', function () { E.falhas = 0; E.forcar = false; carregar(agora(), true); }]);
  cartao('Não deu para reproduzir aqui', msg, botoes);
 }

 // ── Começo ──
 if ('mediaSession' in navigator) {
  try {
   navigator.mediaSession.metadata = new MediaMetadata({title: C.titulo, artist: 'Termux-Toons'});
   navigator.mediaSession.setActionHandler('play', function () { tocarVideo(); });
   navigator.mediaSession.setActionHandler('pause', function () { v.pause(); });
   navigator.mediaSession.setActionHandler('seekbackward', function () { pularRel(-10); });
   navigator.mediaSession.setActionHandler('seekforward', function () { pularRel(10); });
  } catch (e) {}
 }
 if (document.pictureInPictureEnabled && !v.disablePictureInPicture) $('btPip').hidden = false;
 $('btVolta').innerHTML = svgPulo(false);
 $('btAvanca').innerHTML = svgPulo(true);
 $('btAudio').innerHTML = svg('audio');
 $('btLegenda').innerHTML = svg('legenda');
 $('btAjustes').innerHTML = svg('ajustes');
 function proximo() { location.href = '/v/' + C.proximo.token; }
 if (C.proximo) { $('btProximo').innerHTML = svg('proximo'); $('btProximo').hidden = false; ao('btProximo', proximo); }
 if (C.voltar) { $('voltar').href = C.voltar; $('voltar').innerHTML = svg('voltar'); $('voltar').hidden = false; }
 $('btPip').innerHTML = svg('pip');
 atualizarPlay(); atualizarSom(); atualizarTela(); atualizarBotoes(); atualizarTempo();
 window.addEventListener('pagehide', function () { if (E.iniciado) salvar(); });
 setInterval(function () { if (!v.paused) salvar(); }, 5000);
 if (E.legenda >= 0) trocarLegenda(E.legenda, true);
 if (direto()) { E.modo = 'direto'; v.src = BASE + '/video'; } else P.classList.remove('carregando');
 var retomar = salvo.t > 30 && (!duracao() || salvo.t < duracao() - 60) ? salvo.t : 0;
 if (retomar) {
  cartao('Continuar assistindo?', 'Você parou em ' + fmt(retomar) + '.', [
   ['Continuar', function () { carregar(retomar, true); }, true],
   ['Do início', function () { retomar = 0; carregar(0, true); }]
  ]);
 }
})();
</script></body></html>
"""


def eh_link(texto) -> bool:
    return str(texto).strip().lower().startswith(("http://", "https://"))


def fonte_de(item: dict) -> str:
    """O vídeo de um compartilhamento como foi cadastrado: página, link da internet ou caminho do arquivo.
    Um vídeo do catálogo do TorBox ganha um endereço só para identificá-lo (o link real é pedido na hora)."""
    if item.get("torbox"):
        letra, id_item, fid = item["torbox"]
        return f"{TORBOX_API}/{TORBOX_TIPOS[letra][0]}/{id_item}/{fid}"
    return item.get("pagina") or item.get("url") or item.get("caminho", "")


def fontes_de(item: dict, renovar: bool = False) -> list:
    """O que o ffmpeg e o servidor leem: [arquivo] ou [link]; numa página, [vídeo] ou [vídeo, áudio]
    (sites como o YouTube separam os dois), achados pelo yt-dlp."""
    if item.get("pagina"):
        return info_pagina(item["pagina"], renovar)["enderecos"]
    if item.get("torbox"):
        return [torbox_link(_torbox_config()[0], *item["torbox"], renovar=renovar)]
    return [fonte_de(item)]


# Formato pedido ao yt-dlp: até 1080p, de preferência H.264 + AAC (só copiados, sem pesar no celular), por
# HTTP direto (o ffmpeg não escolhe uma qualidade dentro de um manifesto DASH); senão, o que houver.
_HTTP_SIMPLES = "[protocol^=http][protocol!*=dash]"
FORMATO_PAGINA = (f"bv*[height<=1080][vcodec^=avc1]{_HTTP_SIMPLES}+ba[acodec^=mp4a]{_HTTP_SIMPLES}/"
                  f"bv*[height<=1080]{_HTTP_SIMPLES}+ba{_HTTP_SIMPLES}/b[height<=1080]{_HTTP_SIMPLES}/b")
_PAGINAS: dict = {}          # página -> (quando, {'enderecos', 'titulo', 'duracao'})
_PAGINAS_TRAVA = threading.Lock()
_CABECALHOS_LINK: dict = {}  # endereço achado pelo yt-dlp -> cabeçalhos HTTP que o site exige (Referer...)


def info_pagina(pagina: str, renovar: bool = False) -> dict:
    """Vídeo de uma página (YouTube, Vimeo, Google Drive...) achado pelo yt-dlp, sem baixar:
    {'enderecos': [vídeo] ou [vídeo, áudio], 'titulo', 'duracao'}. Os sites expiram esses endereços em
    poucas horas: ficam 1 hora em cache e `renovar` pede outros."""
    with _PAGINAS_TRAVA:
        achado = _PAGINAS.get(pagina)
        if achado and not renovar and time.time() - achado[0] < 3600:
            return achado[1]
        if not tem("yt-dlp"):
            raise ToonsError("Links de página (YouTube, Vimeo...) precisam do yt-dlp: pkg install python-yt-dlp")
        proc = rodar(["yt-dlp", "-j", "--no-playlist", "--no-warnings", "-f", FORMATO_PAGINA, pagina],
                     capturar=True, timeout=180, mostrar=False)
        dados = None
        with contextlib.suppress(json.JSONDecodeError, IndexError):
            dados = json.loads(proc.stdout.strip().splitlines()[-1]) if proc.returncode == 0 else None
        formatos = [f for f in ((dados.get("requested_formats") or [dados]) if dados else []) if f.get("url")]
        if not formatos:
            raise ToonsError("O yt-dlp não achou um vídeo nessa página. " + (proc.stderr or "").strip()[-300:])
        for velho in (achado[1]["enderecos"] if achado else []):
            _CABECALHOS_LINK.pop(velho, None)
        for f in formatos[:2]:
            _CABECALHOS_LINK[f["url"]] = {k: v for k, v in (f.get("http_headers") or dados.get("http_headers") or {}).items()
                                          if isinstance(v, str) and k.lower() != "accept-encoding"}
        resultado = {"enderecos": [f["url"] for f in formatos[:2]], "titulo": str(dados.get("title") or "Vídeo"),
                     "duracao": dados.get("duration")}
        _PAGINAS[pagina] = (time.time(), resultado)
        return resultado


def _cabecalhos_de(url: str) -> dict:
    return {"User-Agent": USER_AGENT, **_CABECALHOS_LINK.get(url, {})}


def extensao_de(fonte) -> str:
    fonte = str(fonte)
    caminho = urllib.parse.urlsplit(fonte).path if eh_link(fonte) else fonte
    return os.path.splitext(caminho)[1].lower()


def _opcoes_entrada(fonte: str, ffprobe: bool = False) -> list:
    """Opções do ffmpeg/ffprobe para ler `fonte`. Links usam a identificação de um navegador e,
    no ffmpeg, reconectam sozinhos se a conexão cair no meio do filme."""
    if not eh_link(fonte):
        return ["-i", "file:" + fonte]
    cabecalhos = _cabecalhos_de(fonte)
    opcoes = ["-user_agent", cabecalhos.pop("User-Agent"), "-rw_timeout", "30000000"]
    if cabecalhos:
        opcoes += ["-headers", "".join(f"{chave}: {valor}\r\n" for chave, valor in cabecalhos.items())]
    if not ffprobe:
        opcoes += ["-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_on_network_error", "1",
                   "-reconnect_delay_max", "10"]
    return opcoes + ["-i", fonte]


def _srt_para_vtt(dados: bytes) -> bytes:
    """Converte legenda .srt (UTF-8, Windows-1252 ou Latin-1) em WebVTT UTF-8."""
    texto = None
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            texto = dados.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    if texto is None:
        texto = dados.decode("latin-1")
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    if not texto.lstrip().startswith("WEBVTT"):
        texto = "WEBVTT\n\n" + re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", texto)
    return texto.encode("utf-8")


_PORTUGUES = re.compile(r"(^|[._\- \[(])(pt|por|pob|br|pt-br|ptbr)([._\- \])]|$)", re.I)


def legendas_ao_lado(video: Path) -> list:
    """Legendas ao lado do vídeo (mesmo nome + .srt/.vtt), português e .vtt primeiro."""
    candidatas = []
    try:
        for p in video.parent.iterdir():
            resto = p.name[len(video.stem):]
            if (p.name.startswith(video.stem) and resto.lower().endswith((".srt", ".vtt"))
                    and resto[:1] in (".", "_", "-", " ") and p.is_file()):
                candidatas.append(p)
    except OSError:
        return []
    return sorted(candidatas, key=lambda p: (not _PORTUGUES.search(p.stem), p.suffix.lower() != ".vtt", p.name))


def _faixa(cabecalho: str | None, tamanho: int):
    """Interpreta 'Range: bytes=a-b'. Devolve (início, fim) inclusivos; None se não há faixa
    (ou se o cabeçalho é ilegível, e então deve ser ignorado); ValueError se for inatingível."""
    m = re.fullmatch(r"bytes=(\d*)-(\d*)", (cabecalho or "").strip())
    if not m or not (m.group(1) or m.group(2)):
        return None
    if not m.group(1):  # "-N": os últimos N bytes
        n = int(m.group(2))
        if n == 0 or tamanho == 0:
            raise ValueError("faixa inatingível")
        return max(0, tamanho - n), tamanho - 1
    inicio = int(m.group(1))
    if m.group(2) and int(m.group(2)) < inicio:
        return None
    if inicio >= tamanho:
        raise ValueError("faixa inatingível")
    return inicio, min(int(m.group(2)), tamanho - 1) if m.group(2) else tamanho - 1


# ── Faixas do vídeo (ffprobe) ────────────────────────────────────────

def sondar_video(fonte):
    """Faixas do vídeo (arquivo ou link) via ffprobe:
    {'video': [...], 'audio': [...], 'legendas': [...], 'formato': {...}} ou None."""
    if not tem("ffprobe"):
        return None
    fonte = str(fonte)
    proc = rodar(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams",
                  *_opcoes_entrada(fonte, ffprobe=True)], capturar=True, timeout=90, mostrar=False)
    if proc.returncode != 0:
        return None
    try:
        dados = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    faixas = dados.get("streams", [])

    def do_tipo(tipo):
        return [s for s in faixas if s.get("codec_type") == tipo and not (s.get("disposition") or {}).get("attached_pic")]

    return {"video": do_tipo("video"), "audio": do_tipo("audio"), "legendas": do_tipo("subtitle"),
            "formato": dados.get("format") or {}}


_SONDAS: dict = {}
_SONDAS_TRAVA = threading.Lock()


def sonda_em_cache(fontes: list):
    """Faixas de [arquivo], [link] ou [vídeo, áudio] (página), lembrando o resultado de cada fonte."""
    sondas = [_sonda_unica_em_cache(fonte) for fonte in fontes]
    if not sondas or None in sondas:
        return None
    if len(sondas) == 1:
        return sondas[0]
    video, audio = sondas[0], sondas[-1]
    return {"video": video["video"], "audio": audio["audio"], "legendas": video["legendas"], "formato": video["formato"]}


def _sonda_unica_em_cache(fonte: str):
    """sondar_video lembrando o resultado: arquivos até mudarem, links por 6 horas."""
    if eh_link(fonte):
        chave, validade = fonte, 6 * 3600
    else:
        try:
            st = os.stat(fonte)
        except OSError:
            return None
        chave, validade = (fonte, st.st_size, st.st_mtime), None
    with _SONDAS_TRAVA:
        achado = _SONDAS.get(chave)
    if achado and (validade is None or time.time() - achado[0] < validade):
        return achado[1]
    sonda = sondar_video(fonte)
    if sonda is not None:  # falha (link fora do ar, por exemplo) não fica guardada
        with _SONDAS_TRAVA:
            _SONDAS[chave] = (time.time(), sonda)
    return sonda


def _duracao(sonda):
    for origem in ([sonda["formato"]] + sonda["video"]) if sonda else []:
        try:
            duracao = float(origem.get("duration") or 0)
        except (TypeError, ValueError):
            continue
        if duracao > 0:
            return round(duracao, 3)
    return None


def _inicio(sonda) -> float:
    """start_time do arquivo: o ffmpeg conta o -ss a partir dele; o ffprobe mostra tempos absolutos."""
    try:
        return float(sonda["formato"].get("start_time") or 0) if sonda else 0.0
    except (TypeError, ValueError):
        return 0.0


def _hms(segundos) -> str:
    minutos = round((segundos or 0) / 60)
    return f"{minutos // 60}h {minutos % 60:02d}min" if minutos >= 60 else f"{minutos}min"


def _eh_portugues(faixa: dict) -> bool:
    return str((faixa.get("tags") or {}).get("language", "")).lower() in LINGUAS_PT


def _indice_portugues(faixas: list) -> int:
    return next((i for i, f in enumerate(faixas) if _eh_portugues(f)), 0)


def _rotulo_faixa(faixa: dict) -> str:
    """'Português · Dublado · AC3 5.1' para mostrar no menu e no player."""
    tags = faixa.get("tags") or {}
    lingua = str(tags.get("language", "")).lower()
    partes = [IDIOMAS.get(lingua, lingua if lingua not in ("", "und") else "Idioma não informado")]
    nome = str(tags.get("title") or "").strip()
    if nome and nome.lower() not in partes[0].lower():
        partes.append(nome)
    if faixa.get("codec_type") == "audio":
        canais = faixa.get("channels")
        partes.append(str(faixa.get("codec_name", "?")).upper()
                      + (f" {CANAIS.get(canais, f'{canais} canais')}" if canais else ""))
    if (faixa.get("disposition") or {}).get("forced") and "forç" not in nome.lower() and "forced" not in nome.lower():
        partes.append("forçada")
    return " · ".join(partes)


def mostrar_faixas(sonda) -> None:
    """Resumo do vídeo: duração, imagem, trilhas de áudio e legendas."""
    resumo = []
    if _duracao(sonda):
        resumo.append(_hms(_duracao(sonda)))
    if sonda["video"]:
        v = sonda["video"][0]
        resumo.append(f"{str(v.get('codec_name', '?')).upper()} {v.get('width', '?')}x{v.get('height', '?')}")
    if resumo:
        print(f"  🎬 {' · '.join(resumo)}")
    for faixa in sonda["audio"]:
        print(f"  🔊 {_rotulo_faixa(faixa)}")
    for faixa in sonda["legendas"]:
        texto = faixa.get("codec_name") in CODECS_LEGENDA_TEXTO
        print(f"  💬 {_rotulo_faixa(faixa)}{'' if texto else f' {DIM}(em imagem: não aparece no navegador){RST}'}")


# ── O navegador consegue tocar? ──────────────────────────────────────

def _video_compativel(faixa: dict) -> bool:
    codec = faixa.get("codec_name")
    if codec == "h264":
        return faixa.get("pix_fmt") in ("yuv420p", "yuvj420p")  # H.264 de 10 bits não toca no navegador
    return codec in VIDEO_NAVEGADOR


def _video_copiavel(faixa) -> bool:
    """Dá para transmitir sem recodificar a imagem? (HEVC só toca em parte dos navegadores; o player confere.)"""
    return bool(faixa) and (_video_compativel(faixa) or faixa.get("codec_name") == "hevc")


def _codecs_navegador(faixa) -> str:
    """Código do formato de vídeo para o player perguntar ao navegador se consegue tocar (canPlayType)."""
    codec, dez_bits = faixa.get("codec_name"), "10" in str(faixa.get("pix_fmt", ""))
    return {"h264": "avc1.640028", "vp8": "vp8", "vp9": "vp09.02.40.10" if dez_bits else "vp09.00.40.08",
            "av1": "av01.0.08M.10" if dez_bits else "av01.0.08M.08",
            "hevc": "hvc1.2.4.L120.90" if dez_bits else "hvc1.1.6.L120.90"}.get(codec, "")


def _arquivo_unico(fontes: list, sonda) -> bool:
    """A fonte é um arquivo só, que dá para entregar byte a byte (não vídeo + áudio separados nem HLS)?"""
    formato = sonda["formato"].get("format_name", "") if sonda else ""
    return len(fontes) == 1 and extensao_de(fontes[0]) != ".m3u8" and "hls" not in formato


def _toca_direto(fontes: list, sonda) -> bool:
    """O navegador toca o arquivo original como está, sem o ffmpeg?"""
    if not _arquivo_unico(fontes, sonda):
        return False
    ext = extensao_de(fontes[0])
    if sonda is None:
        return ext in FORMATOS_NAVEGADOR  # sem ffprobe, só dá para confiar na extensão
    if ext not in FORMATOS_NAVEGADOR and not (ext == "" and "mp4" in sonda["formato"].get("format_name", "")):
        return False
    if sonda["video"] and not _video_compativel(sonda["video"][0]):
        return False
    return len(sonda["audio"]) == 0 or (len(sonda["audio"]) == 1 and sonda["audio"][0].get("codec_name") in AUDIO_NAVEGADOR)


def _tipo_mime(fonte: str, sonda) -> str:
    ext = extensao_de(fonte)
    if ext in TIPOS_VIDEO:
        return TIPOS_VIDEO[ext]
    formato = sonda["formato"].get("format_name", "") if sonda else ""
    if "mp4" in formato:
        return "video/mp4"
    if "matroska" in formato:
        return "video/x-matroska"
    return "application/octet-stream"


def problemas_de_reproducao(fonte, sonda) -> list:
    """O que impede o navegador de tocar o arquivo como está (o ffmpeg resolve convertendo na hora)."""
    problemas = []
    ext = extensao_de(fonte)
    if ext and ext not in FORMATOS_NAVEGADOR:
        problemas.append(f"o formato {ext} (navegadores tocam bem MP4 e WebM)")
    if sonda:
        if sonda["video"] and not _video_compativel(sonda["video"][0]):
            problemas.append(f"o vídeo está em {str(sonda['video'][0].get('codec_name')).upper()} "
                             f"({sonda['video'][0].get('pix_fmt', '?')})")
        codecs = {str(f.get("codec_name")) for f in sonda["audio"]} - set(AUDIO_NAVEGADOR)
        if codecs:
            problemas.append(f"o áudio está em {', '.join(sorted(c.upper() for c in codecs))}")
        if len(sonda["audio"]) > 1:
            problemas.append(f"há {len(sonda['audio'])} trilhas de áudio e o navegador sozinho só toca uma")
    return problemas


def _precisa_recodificar(sonda) -> bool:
    return bool(sonda and sonda["video"] and not _video_copiavel(sonda["video"][0]))


# ── Legendas: arquivos ao lado, extras e embutidas ───────────────────

def legendas_do_item(item: dict, sonda) -> list:
    """Legendas oferecidas no player, na ordem do menu: [{'tipo', 'ref', 'rotulo', 'pt', 'forcada'}].
    Num link da internet, as embutidas só entram se você escolheu prepará-las (é preciso ler o filme todo)."""
    lista, fonte = [], fonte_de(item)
    if not eh_link(fonte):
        video = Path(fonte)
        for p in legendas_ao_lado(video):
            nome = p.name[len(video.stem):-len(p.suffix)].strip("._- ")
            lista.append({"tipo": "arquivo", "ref": str(p), "rotulo": f"{IDIOMAS.get(nome.lower(), nome or 'Legenda')} · arquivo",
                          "pt": bool(_PORTUGUES.search(p.stem)), "forcada": False})
    for extra in item.get("legendas") or []:
        nome = urllib.parse.unquote(Path(urllib.parse.urlsplit(extra).path if eh_link(extra) else extra).stem)
        lista.append({"tipo": "link" if eh_link(extra) else "arquivo", "ref": extra, "rotulo": f"{nome} · extra",
                      "pt": bool(_PORTUGUES.search(nome)), "forcada": False})
    for legenda in item.get("legendas_tb") or []:  # .srt que vieram junto no torrent
        lista.append({"tipo": "torbox", "ref": legenda["fid"], "rotulo": f"{legenda.get('rotulo') or legenda['nome']} · TorBox",
                      "pt": _parece_portugues(legenda["caminho"]), "forcada": "forced" in legenda["caminho"].lower()})
    if sonda:
        permitidas = set(item.get("legendas_embutidas") or []) if eh_link(fonte) else None
        for n, faixa in enumerate(sonda["legendas"]):
            if faixa.get("codec_name") in CODECS_LEGENDA_TEXTO and (permitidas is None or n in permitidas):
                lista.append({"tipo": "embutida", "ref": n, "rotulo": _rotulo_faixa(faixa), "pt": _eh_portugues(faixa),
                              "forcada": bool((faixa.get("disposition") or {}).get("forced"))})
    return lista


def _legenda_padrao(legendas: list, audio_em_portugues: bool) -> int:
    """Áudio em português: só a legenda forçada (placas, falas em outra língua). Senão, legenda em português."""
    if audio_em_portugues:
        return next((i for i, l in enumerate(legendas) if l["pt"] and l["forcada"]), -1)
    return next((i for i, l in enumerate(legendas) if l["pt"] and not l["forcada"]),
                next((i for i, l in enumerate(legendas) if l["pt"]), -1))


def _arquivo_legenda(item: dict, n: int) -> Path:
    """Cache de uma legenda embutida. Num link, vale para o compartilhamento (trocar o endereço expirado
    que expirou não obriga a baixar o filme de novo); num arquivo, até ele mudar."""
    fonte = fonte_de(item)
    ident = f"link|{item['token']}"
    if not eh_link(fonte):
        st = os.stat(fonte)
        ident = f"{fonte}|{st.st_size}|{st.st_mtime}"
    return LEGENDAS_CACHE / (hashlib.sha1(f"{ident}|{n}".encode()).hexdigest()[:24] + ".vtt")


_EXTRACOES: dict = {}  # nome do arquivo em cache -> ("extraindo" | "erro", quando)
_EXTRACOES_TRAVA = threading.Lock()


def _extrair_legendas(fonte: str, destinos: dict) -> None:
    """Extrai várias legendas embutidas numa passada só do ffmpeg (num link, o filme é lido uma vez)."""
    LEGENDAS_CACHE.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *_opcoes_entrada(fonte)]
    for n, destino in destinos.items():
        cmd += ["-map", f"0:s:{n}", "-c:s", "webvtt", "-f", "webvtt", str(destino) + ".part"]
    log(f"Extraindo {len(destinos)} legenda(s) embutida(s)...")
    proc = rodar(cmd, capturar=True, timeout=4 * 3600, mostrar=False)
    with _EXTRACOES_TRAVA:
        for destino in destinos.values():
            parcial = Path(str(destino) + ".part")
            if proc.returncode == 0 and parcial.exists():
                parcial.replace(destino)
                _EXTRACOES.pop(destino.name, None)
            else:
                parcial.unlink(missing_ok=True)
                _EXTRACOES[destino.name] = ("erro", time.time())
    if proc.returncode != 0:
        log(f"Falha ao extrair legendas: {(proc.stderr or '').strip()[-300:]}")


def legenda_embutida(item: dict, n: int, todas: list):
    """(bytes do .vtt, None) se já extraída; senão (None, 'extraindo' | 'erro'). Na primeira vez dispara a
    extração, em segundo plano, de todas as legendas embutidas do item (`todas`), que ficam em cache."""
    try:
        destinos = {m: _arquivo_legenda(item, m) for m in dict.fromkeys([n, *todas])}
    except OSError:
        return None, "erro"
    with contextlib.suppress(OSError):
        return destinos[n].read_bytes(), None
    with _EXTRACOES_TRAVA:
        estado = _EXTRACOES.get(destinos[n].name)
        if estado is None or (estado[0] == "erro" and time.time() - estado[1] > 300):
            faltando = {m: d for m, d in destinos.items()
                        if not d.exists() and _EXTRACOES.get(d.name, ("",))[0] != "extraindo"}
            for destino in faltando.values():
                _EXTRACOES[destino.name] = ("extraindo", time.time())
            threading.Thread(target=_extrair_legendas, args=(fontes_de(item)[0], faltando), daemon=True).start()
            estado = ("extraindo", time.time())
    return None, estado[0]


_LEGENDAS_LINK: dict = {}  # endereço -> (quando, bytes)


def _baixar_legenda_link(url: str):
    achado = _LEGENDAS_LINK.get(url)
    if achado and time.time() - achado[0] < 3600:
        return achado[1]
    try:
        status, dados, _ = baixar_url(url, timeout=30)
    except OSError:
        return None
    if status >= 400 or not dados:
        return None
    _LEGENDAS_LINK[url] = (time.time(), dados)
    return dados


# ── Transmissão convertida na hora (ffmpeg) ──────────────────────────

def ponto_de_corte(fonte: str, sonda, t: float) -> float:
    """Início do quadro-chave em `t` ou logo antes. O ffmpeg só consegue copiar o vídeo a partir de um
    quadro-chave; começando exatamente nele, o player sabe a que minuto do filme cada imagem pertence."""
    if t <= 0 or not sonda or not sonda["video"]:
        return max(t, 0.0)
    base = _inicio(sonda)
    proc = rodar(["ffprobe", "-v", "error", "-select_streams", "v:0", "-read_intervals", f"{t + base:.3f}%+5",
                  "-show_entries", "packet=pts_time,flags", "-of", "csv=p=0", *_opcoes_entrada(fonte, ffprobe=True)],
                 capturar=True, timeout=60, mostrar=False)
    for linha in (proc.stdout or "").splitlines():
        pts, _, marcas = linha.partition(",")
        if "K" in marcas:
            with contextlib.suppress(ValueError):
                return max(0.0, float(pts) - base)
    return t


_ENCODERS: dict = {}


def tem_encoder(nome: str) -> bool:
    if nome not in _ENCODERS:
        _ENCODERS[nome] = bool(re.search(rf"^\s*\S+\s+{re.escape(nome)}\s", saida(
            ["ffmpeg", "-hide_banner", "-encoders"], timeout=20), re.M))
    return _ENCODERS[nome]


def comando_transmissao(fontes: list, sonda, audio: int = 0, inicio: float = 0.0,
                        recodificar: bool = False, audio_codec: str = "aac") -> list:
    """ffmpeg que gera um MP4 fragmentado (toca enquanto chega) a partir de `inicio` segundos, com a trilha
    de áudio `audio`. A imagem é copiada (leve); só é recodificada se o navegador não toca o formato.
    Com [vídeo, áudio] (página do YouTube, por exemplo) junta as duas fontes."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin"]
    for fonte in fontes:
        if inicio > 0:
            cmd += ["-ss", f"{inicio + 0.005:.3f}"]  # um pouco depois do quadro-chave: o ffmpeg volta até ele
        cmd += _opcoes_entrada(fonte)
    cmd += ["-map", "0:v:0?", "-map", f"{len(fontes) - 1}:a:{audio}?", "-sn", "-dn", "-map_metadata", "-1",
            "-map_chapters", "-1"]
    video = sonda["video"][0] if sonda and sonda["video"] else None
    if video and (recodificar or not _video_copiavel(video)):
        cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", "-maxrate", "4M", "-bufsize", "8M",
                "-vf", "scale=-2:'min(720,ih)'", "-pix_fmt", "yuv420p", "-g", "48"]
    else:
        cmd += ["-c:v", "copy"]
        if video and video.get("codec_name") == "hevc":
            cmd += ["-tag:v", "hvc1"]  # é assim que Safari e Chrome reconhecem HEVC dentro do MP4
    faixas = sonda["audio"] if sonda else []
    origem = faixas[audio].get("codec_name") if audio < len(faixas) else None
    if (audio_codec == "aac" and origem in ("aac", "mp3")) or (audio_codec == "opus" and origem == "opus"):
        cmd += ["-c:a", "copy"]
    elif audio_codec == "opus" and tem_encoder("libopus"):
        cmd += ["-c:a", "libopus", "-b:a", "160k", "-ac", "2"]
    else:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ac", "2"]
    return cmd + ["-max_muxing_queue_size", "4096", "-movflags", "frag_keyframe+empty_moov+default_base_moof",
                  "-frag_duration", "2000000", "-f", "mp4", "pipe:1"]


_TRANSMISSOES: dict = {}  # "token:sessão do player" -> processo do ffmpeg
_TRANSMISSOES_TRAVA = threading.Lock()


def info_link(url: str) -> dict:
    """Confere um link de vídeo pedindo só o primeiro byte: {'status', 'nome', 'tamanho', 'tipo'}.
    Erros de rede viram exceção (OSError)."""
    req = urllib.request.Request(url, headers={**_cabecalhos_de(url), "Range": "bytes=0-0"})
    try:
        resposta = urllib.request.urlopen(req, timeout=25)
    except urllib.error.HTTPError as e:
        return {"status": e.code, "nome": "", "tamanho": None, "tipo": ""}
    with resposta:
        cab, status, final = resposta.headers, resposta.status, resposta.geturl()
    tamanho = None
    m = re.search(r"/(\d+)\s*$", cab.get("Content-Range", ""))
    if m:
        tamanho = int(m.group(1))
    elif status == 200 and str(cab.get("Content-Length", "")).isdigit():
        tamanho = int(cab["Content-Length"])
    disposicao = cab.get("Content-Disposition", "")
    m = (re.search(r"filename\*\s*=\s*(?:UTF-8'')?\"?([^\";]+)", disposicao, re.I)
         or re.search(r"filename\s*=\s*\"?([^\";]+)", disposicao, re.I))
    nome = urllib.parse.unquote(m.group(1)).strip() if m else ""
    if not nome:
        nome = urllib.parse.unquote(os.path.basename(urllib.parse.urlsplit(final).path))
    return {"status": status, "nome": nome, "tamanho": tamanho, "tipo": cab.get_content_type()}


# ── TorBox: catálogo da sua biblioteca ───────────────────────────────
# Com a chave da API do TorBox, o servidor mostra todos os seus filmes e séries numa página
# (um link secreto só, /tb/<código>) e cada vídeo vira um "compartilhamento virtual" que abre no
# mesmo player: o link de download é pedido ao TorBox na hora de assistir. A chave nunca sai do celular.

TORBOX_API = os.environ.get("TOONS_TORBOX_API", "https://api.torbox.app/v1/api")
TORBOX_TIPOS = {"t": ("torrents", "torrent_id"), "u": ("usenet", "usenet_id"), "w": ("webdl", "web_id")}
EXTENSOES_VIDEO_TORBOX = EXTENSOES_VIDEO | {".ts", ".m2ts", ".wmv", ".flv", ".mpg", ".mpeg"}
_TORBOX: dict = {"quando": 0.0, "chave": "", "itens": [], "links": {}}
_TORBOX_TRAVA = threading.Lock()


def _ordem_natural(texto: str) -> list:
    """'Ep 2' antes de 'Ep 10'."""
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", texto)]


def _torbox_config() -> tuple:
    """(chave da API, código do catálogo), relidos do arquivo: o menu pode ter trocado."""
    c = ler_json(CONFIG_FILE, {})
    return c.get("torbox_chave") or "", c.get("torbox_catalogo") or ""


def torbox_chamar(caminho: str, chave: str, **params):
    """Chama a API do TorBox e devolve o campo 'data' da resposta."""
    url = f"{TORBOX_API}/{caminho}" + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {chave}", "Accept": "application/json",
                                               "User-Agent": f"TermuxToons/{VERSION}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resposta:
            dados = json.loads(resposta.read() or b"{}")
    except urllib.error.HTTPError as e:
        detalhe = ""
        with contextlib.suppress(Exception):
            corpo = json.loads(e.read() or b"{}")
            detalhe = str(corpo.get("detail") or corpo.get("error") or "")
        if e.code in (401, 403):
            raise ToonsError("O TorBox recusou a chave da API (confira em torbox.app → Settings → API).") from None
        raise ToonsError(f"O TorBox respondeu HTTP {e.code}. {detalhe}".strip()) from None
    except (OSError, ValueError) as e:
        raise ToonsError(f"Não consegui falar com o TorBox: {e}") from None
    if isinstance(dados, dict) and dados.get("success") is False:
        raise ToonsError(f"TorBox: {dados.get('detail') or dados.get('error') or 'erro desconhecido'}")
    return dados.get("data") if isinstance(dados, dict) else dados


def _torbox_item(letra: str, bruto: dict) -> dict:
    """Um torrent/usenet/download da web, só com os vídeos (sem os 'sample') e as legendas."""
    videos, legendas = [], []
    for arq in bruto.get("files") or []:
        caminho = str(arq.get("name") or arq.get("short_name") or "")
        nome = str(arq.get("short_name") or caminho.rsplit("/", 1)[-1])
        tamanho_arq = int(arq.get("size") or 0)
        entrada = {"fid": int(arq.get("id") or 0), "nome": nome, "caminho": caminho, "tamanho": tamanho_arq}
        ext = os.path.splitext(nome)[1].lower()
        if ext in EXTENSOES_VIDEO_TORBOX and not (re.search(r"\bsample\b", caminho, re.I) and tamanho_arq < 300 * 2**20):
            videos.append(entrada)
        elif ext in (".srt", ".vtt"):
            legendas.append(entrada)
    videos.sort(key=lambda v: _ordem_natural(v["caminho"]))
    return {"tipo": letra, "id": int(bruto.get("id") or 0), "nome": str(bruto.get("name") or "Sem nome"),
            "tamanho": int(bruto.get("size") or 0), "data": str(bruto.get("created_at") or ""),
            "pronto": bool(bruto.get("download_finished") or bruto.get("download_present")),
            "progresso": float(bruto.get("progress") or 0), "videos": videos, "legendas": legendas}


def torbox_biblioteca(chave: str, renovar: bool = False) -> list:
    """Torrents, usenet e downloads da web da conta que têm vídeo, mais novos primeiro (guardado por 1 minuto)."""
    with _TORBOX_TRAVA:
        if not renovar and _TORBOX["chave"] == chave and time.time() - _TORBOX["quando"] < 60:
            return _TORBOX["itens"]
        itens = []
        for letra, (rota, _) in TORBOX_TIPOS.items():
            try:
                lista = torbox_chamar(f"{rota}/mylist", chave, bypass_cache="true") or []
            except ToonsError:
                if letra == "t":  # os torrents são o principal; usenet e web podem não existir no seu plano
                    raise
                continue
            for bruto in lista if isinstance(lista, list) else [lista]:
                if isinstance(bruto, dict):
                    item = _torbox_item(letra, bruto)
                    if item["videos"]:
                        itens.append(item)
        itens.sort(key=lambda it: it["data"], reverse=True)
        _TORBOX.update(quando=time.time(), chave=chave, itens=itens)
        return itens


def torbox_link(chave: str, letra: str, id_item: int, fid: int, renovar: bool = False) -> str:
    """Link de download de um arquivo, pedido ao TorBox (vale algumas horas: fica 1 hora guardado)."""
    with _TORBOX_TRAVA:
        achado = _TORBOX["links"].get((letra, id_item, fid))
    if achado and not renovar and time.time() - achado[0] < 3600:
        return achado[1]
    rota, campo = TORBOX_TIPOS[letra]
    url = torbox_chamar(f"{rota}/requestdl", chave, token=chave, file_id=fid, zip_link="false", redirect="false",
                        **{campo: id_item})
    if not isinstance(url, str) or not eh_link(url):
        raise ToonsError("O TorBox não devolveu um link para este arquivo (ele ainda está sendo baixado?).")
    with _TORBOX_TRAVA:
        _TORBOX["links"][(letra, id_item, fid)] = (time.time(), url)
    return url


def token_torbox(catalogo: str, letra: str, id_item: int, fid: int) -> str:
    """Código do 'compartilhamento virtual' de um vídeo do TorBox: só funciona com o código do catálogo."""
    return f"tb{letra}{id_item}x{fid}k{catalogo}"


def _parece_portugues(texto: str) -> bool:
    return bool(_PORTUGUES.search(texto) or re.search(r"portugu|brazil|brasil", texto, re.I))


def item_torbox(token: str):
    """Monta o compartilhamento virtual de um vídeo do catálogo (título, legendas da pasta, próximo episódio)."""
    m = re.fullmatch(r"tb([tuw])(\d+)x(\d+)k([A-Za-z0-9_-]{8,40})", token)
    chave, catalogo = _torbox_config()
    if not m or not chave or not catalogo or not hmac.compare_digest(m.group(4).encode(), catalogo.encode()):
        return None
    letra, id_item, fid = m.group(1), int(m.group(2)), int(m.group(3))
    item = {"token": token, "torbox": [letra, id_item, fid], "titulo": "Vídeo", "voltar": f"/tb/{catalogo}"}
    with contextlib.suppress(ToonsError):
        entrada = next((it for it in torbox_biblioteca(chave) if it["tipo"] == letra and it["id"] == id_item), None)
        videos = entrada["videos"] if entrada else []
        n = next((i for i, v in enumerate(videos) if v["fid"] == fid), None)
        if n is not None:
            video = videos[n]
            item["titulo"] = titulo_do_arquivo(Path(video["nome"]))
            if n + 1 < len(videos):
                seguinte = videos[n + 1]
                item["proximo"] = {"token": token_torbox(catalogo, letra, id_item, seguinte["fid"]),
                                   "titulo": titulo_do_arquivo(Path(seguinte["nome"]))}
            base = os.path.splitext(video["nome"])[0]
            item["legendas_tb"] = []
            for legenda in entrada["legendas"]:
                if len(videos) == 1 or base.lower() in legenda["caminho"].lower():
                    nome = os.path.splitext(legenda["nome"])[0]  # 'Filme.pt-BR' -> 'Português (BR)'
                    resto = nome[len(base):].strip("._- ") if nome.lower().startswith(base.lower()) else nome
                    item["legendas_tb"].append({**legenda, "rotulo": IDIOMAS.get(resto.lower(), resto or "Legenda")})
            item["legendas_tb"] = item["legendas_tb"][:20]
    return item


PAGINA_TORBOX = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="#09090b">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%8D%BF%3C/text%3E%3C/svg%3E">
<title>Minha biblioteca</title>
<style>
 :root{--acc:#8b5cf6;--acc2:#a78bfa;--fundo:#09090b;--card:#18181b;--txt:#f4f4f5;--sub:#a1a1aa;--borda:rgba(255,255,255,.08)}
 *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
 html,body{margin:0;background:var(--fundo);color:var(--txt);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
 button,input,select{font:inherit;color:inherit}
 button{background:none;border:0;cursor:pointer;padding:0}
 a{color:inherit;text-decoration:none}
 header{position:sticky;top:0;z-index:5;background:rgba(9,9,11,.92);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);
  border-bottom:1px solid var(--borda);padding:max(12px,env(safe-area-inset-top)) 16px 10px}
 .linha{display:flex;gap:10px;align-items:center;max-width:1400px;margin:0 auto}
 h1{margin:0;font-size:1.25em;white-space:nowrap}
 #busca{flex:1;min-width:0;background:var(--card);border:1px solid var(--borda);border-radius:99px;padding:9px 16px;outline:none}
 #busca:focus{border-color:var(--acc)}
 .icone{width:40px;height:40px;border-radius:50%;display:grid;place-items:center;background:var(--card);border:1px solid var(--borda);flex:none}
 .icone svg{width:20px;height:20px;fill:currentColor}
 .filtros{display:flex;gap:8px;margin-top:10px;overflow-x:auto;scrollbar-width:none}
 .filtros::-webkit-scrollbar{display:none}
 .chip{padding:6px 14px;border-radius:99px;background:var(--card);border:1px solid var(--borda);white-space:nowrap;color:var(--sub)}
 .chip.sel{background:var(--acc);border-color:var(--acc);color:#fff}
 select.chip{appearance:none;-webkit-appearance:none;margin-left:auto}
 main{max-width:1400px;margin:0 auto;padding:16px 16px 40px}
 h2{font-size:1.05em;margin:8px 0 12px;color:#e4e4e7}
 .grade{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:14px}
 @media (max-width:520px){.grade{grid-template-columns:repeat(2,1fr);gap:10px}}
 .card{display:flex;flex-direction:column;background:var(--card);border:1px solid var(--borda);border-radius:14px;overflow:hidden;
  text-align:left;transition:transform .15s,border-color .15s}
 .card:hover{transform:translateY(-3px);border-color:rgba(167,139,250,.5)}
 .card.off{opacity:.55}
 .capa{position:relative;aspect-ratio:2/3;display:grid;place-items:center;font-size:2.6em;font-weight:800;color:rgba(255,255,255,.9);
  text-shadow:0 2px 12px rgba(0,0,0,.4);letter-spacing:-.02em;padding:12px;text-align:center;overflow:hidden}
 .capa small{position:absolute;left:8px;top:8px;font-size:.3em;font-weight:700;padding:3px 8px;border-radius:6px;background:rgba(0,0,0,.55);
  text-shadow:none;letter-spacing:0}
 .capa .q{left:auto;right:8px}
 .barra{position:absolute;left:0;right:0;bottom:0;height:4px;background:rgba(0,0,0,.4)}
 .barra i{display:block;height:100%;background:var(--acc2)}
 .info{padding:10px 12px 12px}
 .info b{display:block;font-size:.95em;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
 .info span{display:block;color:var(--sub);font-size:.8em;margin-top:4px}
 .continuar{display:flex;gap:12px;overflow-x:auto;padding-bottom:6px;margin-bottom:18px;scrollbar-width:thin}
 .continuar .card{flex:0 0 220px}
 .continuar .capa{aspect-ratio:16/9;font-size:1.6em}
 #msg{color:var(--sub);text-align:center;padding:60px 20px}
 #msg b{display:block;color:var(--txt);font-size:1.1em;margin-bottom:6px}
 .girando{width:38px;height:38px;margin:0 auto 14px;border-radius:50%;border:4px solid rgba(255,255,255,.15);border-top-color:var(--acc2);
  animation:gira .8s linear infinite}
 @keyframes gira{to{transform:rotate(360deg)}}
 #painel{position:fixed;inset:0;z-index:10;background:rgba(0,0,0,.65);display:none;align-items:flex-end;justify-content:center}
 #painel.ver{display:flex}
 #folha{width:100%;max-width:720px;max-height:88vh;overflow:auto;background:#111113;border:1px solid var(--borda);border-radius:18px 18px 0 0;
  padding:18px 16px max(18px,env(safe-area-inset-bottom))}
 @media (min-width:760px){#painel{align-items:center}#folha{border-radius:18px}}
 #folha h3{margin:0 0 4px;font-size:1.2em}
 #folha .sub{color:var(--sub);font-size:.85em;margin-bottom:12px}
 .temps{display:flex;gap:8px;overflow-x:auto;margin-bottom:10px}
 .ep{display:flex;align-items:center;gap:12px;width:100%;text-align:left;padding:10px;border-radius:12px}
 .ep:hover{background:rgba(255,255,255,.06)}
 .ep .n{flex:none;width:42px;height:42px;border-radius:10px;background:var(--card);display:grid;place-items:center;font-weight:700;color:var(--acc2)}
 .ep .t{flex:1;min-width:0}
 .ep .t b{display:block;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
 .ep .t span{color:var(--sub);font-size:.8em}
 .ep .p{height:3px;border-radius:3px;background:rgba(255,255,255,.12);margin-top:5px;overflow:hidden}
 .ep .p i{display:block;height:100%;background:var(--acc2)}
 .fechar{float:right;font-size:1.4em;color:var(--sub);width:36px;height:36px}
</style></head><body>
<header>
 <div class="linha">
  <h1>🍿 Biblioteca</h1>
  <input id="busca" type="search" placeholder="Buscar filme ou série" autocomplete="off">
  <button class="icone" id="atualizar" title="Atualizar a lista"><svg viewBox="0 0 24 24"><path d="M17.65 6.35A7.96 7.96 0 0 0 12 4a8 8 0 1 0 7.73 10h-2.08A6 6 0 1 1 12 6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg></button>
 </div>
 <div class="filtros linha" id="filtros">
  <button class="chip sel" data-f="tudo">Tudo</button>
  <button class="chip" data-f="filme">🎬 Filmes</button>
  <button class="chip" data-f="serie">📺 Séries</button>
  <button class="chip" data-f="baixando">⏳ Baixando</button>
  <select class="chip" id="ordem" aria-label="Ordenar">
   <option value="data">Mais recentes</option><option value="nome">Nome (A–Z)</option><option value="tamanho">Maiores</option>
  </select>
 </div>
</header>
<main>
 <section id="secContinuar" hidden><h2>Continuar assistindo</h2><div class="continuar" id="continuar"></div></section>
 <h2 id="tituloGrade" hidden></h2>
 <div class="grade" id="grade"></div>
 <div id="msg"><div class="girando"></div>Buscando sua biblioteca no TorBox…</div>
</main>
<div id="painel"><div id="folha"></div></div>
<script>
(function () {
 'use strict';
 function $(id) { return document.getElementById(id); }
 var BASE = location.pathname.replace(/\/+$/, '');
 var itens = [], filtro = 'tudo', DESC = /\b(19[3-9]\d|20[0-4]\d|S\d{1,2}E\d{1,3}|S\d{1,2}|\d{1,2}x\d{2,3}|2160p|1080p|720p|480p|4k|uhd|web[- ]?dl|web[- ]?rip|webrip|blu[- ]?ray|bdrip|brrip|dvdrip|hdtv|hdrip|x26[45]|h ?26[45]|hevc|dual|dublado|legendado|complete|completa|temporada|season|nacional)\b/i;

 function el(tag, classe, texto) { var e = document.createElement(tag); if (classe) e.className = classe; if (texto != null) e.textContent = texto; return e; }
 function bytes(n) { var u = ['B', 'KB', 'MB', 'GB', 'TB'], i = 0; while (n >= 1024 && i < 4) { n /= 1024; i++; } return (i ? n.toFixed(1) : n) + ' ' + u[i]; }
 function fmt(s) { s = Math.floor(s || 0); var h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60); return h ? h + 'h' + (m < 10 ? '0' : '') + m : m + 'min'; }
 function ler(n) {
  n = n.replace(/\.[a-z0-9]{2,4}$/i, '').replace(/[._]+/g, ' ').replace(/\s+/g, ' ');
  var ano = (n.match(/\b(19[3-9]\d|20[0-4]\d)\b/) || [])[1];
  var q = (n.match(/\b(2160p|4k|uhd|1080p|720p|480p)\b/i) || [])[1];
  if (q && /4k|uhd|2160/i.test(q)) q = '4K';
  var ep = n.match(/\bS(\d{1,2}) ?E(\d{1,3})\b/i) || n.match(/\b(\d{1,2})x(\d{2,3})\b/);
  var temp = !ep && n.match(/\b(?:S|season |temporada )(\d{1,2})\b/i);
  var corte = n.search(DESC);
  var titulo = (corte > 0 ? n.slice(0, corte) : n).replace(/[\[\(\-–\s]+$/, '').trim();
  return {titulo: titulo || n.trim(), ano: ano, q: q, temp: ep ? +ep[1] : temp ? +temp[1] : null, ep: ep ? +ep[2] : null};
 }
 function progresso(token) {
  try { var s = JSON.parse(localStorage.getItem('toons:' + token)); return s && s.t > 30 ? s : null; } catch (e) { return null; }
 }
 function cor(texto) { var h = 0; for (var i = 0; i < texto.length; i++) h = (h * 31 + texto.charCodeAt(i)) % 360; return h; }
 function capa(info, pequeno) {
  var c = el('div', 'capa'), h = cor(info.titulo);
  c.style.background = 'linear-gradient(150deg,hsl(' + h + ' 55% 38%),hsl(' + ((h + 50) % 360) + ' 60% 14%))';
  c.textContent = pequeno ? info.titulo : info.titulo.split(' ').slice(0, 3).map(function (p) { return p[0] || ''; }).join('').toUpperCase();
  return c;
 }
 function preparar(it) {
  var info = ler(it.nome), episodios = 0;
  it.videos.forEach(function (v) { v.info = ler(v.nome); if (v.info.ep != null) episodios++; });
  it.info = info;
  it.serie = it.videos.length > 1 && (episodios > 0 || info.temp != null) || info.temp != null && it.videos.length > 0 && episodios > 0;
  it.busca = (info.titulo + ' ' + it.nome).toLowerCase();
  return it;
 }
 function abrir(token) { location.href = '/v/' + token; }

 function card(it) {
  var b = el('button', 'card' + (it.pronto ? '' : ' off')), c = capa(it.info);
  c.appendChild(el('small', '', it.serie ? 'SÉRIE' : 'FILME'));
  if (it.info.q) c.appendChild(el('small', 'q', it.info.q));
  if (!it.pronto) { var bar = el('div', 'barra'), i = el('i'); i.style.width = Math.round((it.progresso || 0) * 100) + '%'; bar.appendChild(i); c.appendChild(bar); }
  b.appendChild(c);
  var inf = el('div', 'info');
  inf.appendChild(el('b', '', it.info.titulo));
  var meta = [it.info.ano, it.serie ? it.videos.length + ' episódios' : null, bytes(it.tamanho)].filter(Boolean).join(' · ');
  inf.appendChild(el('span', '', it.pronto ? meta : 'Baixando no TorBox · ' + Math.round((it.progresso || 0) * 100) + '%'));
  b.appendChild(inf);
  b.onclick = function () {
   if (!it.pronto) return alert('Ainda está sendo baixado no TorBox. Tente de novo quando terminar.');
   if (it.videos.length === 1) return abrir(it.videos[0].token);
   folha(it);
  };
  return b;
 }

 function folha(it) {
  var f = $('folha'); f.innerHTML = '';
  var x = el('button', 'fechar', '✕'); x.onclick = fechar; f.appendChild(x);
  f.appendChild(el('h3', '', it.info.titulo));
  f.appendChild(el('div', 'sub', [it.info.ano, it.videos.length + ' vídeos', bytes(it.tamanho)].filter(Boolean).join(' · ')));
  var grupos = {};
  it.videos.forEach(function (v) { var t = v.info.temp != null ? v.info.temp : 0; (grupos[t] = grupos[t] || []).push(v); });
  var temps = Object.keys(grupos).map(Number).sort(function (a, b) { return a - b; });
  var lista = el('div');
  function mostrar(t) {
   lista.innerHTML = '';
   grupos[t].forEach(function (v, n) {
    var b = el('button', 'ep'), p = progresso(v.token);
    b.appendChild(el('div', 'n', v.info.ep != null ? String(v.info.ep) : String(n + 1)));
    var tx = el('div', 't');
    tx.appendChild(el('b', '', v.info.ep != null ? 'Episódio ' + v.info.ep : v.info.titulo));
    tx.appendChild(el('span', '', [bytes(v.tamanho), v.info.q, p ? 'parou em ' + fmt(p.t) : '', v.nome].filter(Boolean).join(' · ')));
    if (p && p.d) { var bar = el('div', 'p'), i = el('i'); i.style.width = Math.min(100, p.t / p.d * 100) + '%'; bar.appendChild(i); tx.appendChild(bar); }
    b.appendChild(tx);
    b.onclick = function () { abrir(v.token); };
    lista.appendChild(b);
   });
  }
  if (temps.length > 1) {
   var barra = el('div', 'temps');
   temps.forEach(function (t, i) {
    var c = el('button', 'chip' + (i ? '' : ' sel'), t ? 'Temporada ' + t : 'Outros');
    c.onclick = function () { [].forEach.call(barra.children, function (x) { x.classList.remove('sel'); }); c.classList.add('sel'); mostrar(t); };
    barra.appendChild(c);
   });
   f.appendChild(barra);
  }
  f.appendChild(lista);
  mostrar(temps[0]);
  $('painel').classList.add('ver');
 }
 function fechar() { $('painel').classList.remove('ver'); }
 $('painel').onclick = function (ev) { if (ev.target === this) fechar(); };
 document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') fechar(); });

 function desenhar() {
  var termo = $('busca').value.trim().toLowerCase(), ordem = $('ordem').value;
  var lista = itens.filter(function (it) {
   if (termo && it.busca.indexOf(termo) < 0) return false;
   if (filtro === 'filme') return it.pronto && !it.serie;
   if (filtro === 'serie') return it.pronto && it.serie;
   if (filtro === 'baixando') return !it.pronto;
   return true;
  });
  lista.sort(function (a, b) {
   if (ordem === 'nome') return a.info.titulo.localeCompare(b.info.titulo, 'pt');
   if (ordem === 'tamanho') return b.tamanho - a.tamanho;
   return String(b.data).localeCompare(String(a.data));
  });
  var g = $('grade'); g.innerHTML = '';
  lista.forEach(function (it) { g.appendChild(card(it)); });
  $('tituloGrade').hidden = !lista.length;
  $('tituloGrade').textContent = lista.length + (lista.length === 1 ? ' título' : ' títulos');
  $('msg').hidden = !!lista.length;
  if (!lista.length) $('msg').innerHTML = itens.length ? '<b>Nada encontrado</b>Tente outra busca ou outro filtro.'
   : '<b>Nenhum vídeo na sua conta</b>Adicione filmes ou séries no TorBox e toque em atualizar.';
  // Continuar assistindo: vídeos com posição salva pelo player
  var cont = [];
  itens.forEach(function (it) { it.videos.forEach(function (v) { var p = progresso(v.token); if (p && (!p.d || p.t < p.d - 60)) cont.push({it: it, v: v, p: p}); }); });
  cont.sort(function (a, b) { return (b.p.quando || 0) - (a.p.quando || 0); });
  var c = $('continuar'); c.innerHTML = '';
  cont.slice(0, 12).forEach(function (x) {
   var b = el('button', 'card'), cp = capa({titulo: x.it.info.titulo}, true);
   if (x.p.d) { var bar = el('div', 'barra'), i = el('i'); i.style.width = Math.min(100, x.p.t / x.p.d * 100) + '%'; bar.appendChild(i); cp.appendChild(bar); }
   b.appendChild(cp);
   var inf = el('div', 'info');
   inf.appendChild(el('b', '', x.it.serie && x.v.info.ep != null ? x.it.info.titulo + ' · ' + (x.v.info.temp != null ? 'T' + x.v.info.temp + ' ' : '') + 'E' + x.v.info.ep : x.it.info.titulo));
   inf.appendChild(el('span', '', 'parou em ' + fmt(x.p.t)));
   b.appendChild(inf);
   b.onclick = function () { abrir(x.v.token); };
   c.appendChild(b);
  });
  $('secContinuar').hidden = !cont.length;
 }

 function carregar(renovar) {
  $('msg').hidden = false; $('msg').innerHTML = '<div class="girando"></div>Buscando sua biblioteca no TorBox…';
  fetch(BASE + '/lista.json' + (renovar ? '?renovar=1' : '')).then(function (r) { return r.json().then(function (j) { return [r.ok, j]; }); })
   .then(function (res) {
    if (!res[0]) throw new Error(res[1].erro || 'erro');
    itens = res[1].itens.map(preparar);
    desenhar();
   }).catch(function (e) {
    $('grade').innerHTML = ''; $('msg').hidden = false;
    $('msg').innerHTML = '<b>Não consegui carregar a biblioteca</b>';
    $('msg').appendChild(document.createTextNode(e.message === 'Failed to fetch' ? 'Sem conexão com o celular.' : e.message));
   });
 }
 $('busca').addEventListener('input', desenhar);
 $('ordem').addEventListener('change', desenhar);
 $('atualizar').onclick = function () { carregar(true); };
 [].forEach.call(document.querySelectorAll('#filtros [data-f]'), function (b) {
  b.onclick = function () {
   filtro = b.dataset.f;
   [].forEach.call(document.querySelectorAll('#filtros [data-f]'), function (x) { x.classList.toggle('sel', x === b); });
   desenhar();
  };
 });
 window.addEventListener('pageshow', function (ev) { if (ev.persisted && itens.length) desenhar(); });  // voltou do player
 carregar(false);
})();
</script></body></html>
"""


# ── O servidor ───────────────────────────────────────────────────────

def _compartilhamentos() -> list:
    """Lê os links direto do arquivo, a cada pedido: novos links e revogações valem na hora."""
    return ler_json(CONFIG_FILE, {}).get("compartilhamentos", [])


def achar_compartilhamento(token: str):
    if re.fullmatch(r"tb[tuw]\d+x\d+k[A-Za-z0-9_-]+", token):  # vídeo do catálogo do TorBox
        return item_torbox(token)
    achado = None
    for item in _compartilhamentos():
        if hmac.compare_digest(str(item.get("token", "")).encode(), token.encode()):
            achado = item  # sem 'break': o tempo não revela qual link existe
    return achado


def expirado(item: dict) -> bool:
    return bool(item.get("expira")) and time.time() > item["expira"]


def config_do_player(item: dict, fontes: list, sonda) -> dict:
    """Tudo que o player precisa saber do vídeo (vai embutido na página)."""
    fonte = fonte_de(item)
    audios = sonda["audio"] if sonda else []
    video = sonda["video"][0] if sonda and sonda["video"] else None
    audio_padrao = _indice_portugues(audios)
    legendas = legendas_do_item(item, sonda)
    return {
        "token": item["token"],
        "titulo": item.get("titulo") or titulo_do_arquivo(Path(fonte)),
        "duracao": _duracao(sonda),
        "direto": _toca_direto(fontes, sonda),
        "transmissao": tem("ffmpeg"),
        "remoto": eh_link(fonte),
        "mp4": _arquivo_unico(fontes, sonda) and (extensao_de(fontes[0]) in (".mp4", ".m4v", ".mov")
                                                  or "mp4" in (sonda["formato"].get("format_name", "") if sonda else "")),
        "video": {"codecs": _codecs_navegador(video), "copiavel": _video_copiavel(video)} if video else None,
        "audios": [{"rotulo": _rotulo_faixa(f)} for f in audios],
        "audio_padrao": audio_padrao,
        "legendas": [{"rotulo": l["rotulo"]} for l in legendas],
        "legenda_padrao": _legenda_padrao(legendas, bool(audios) and _eh_portugues(audios[audio_padrao])),
        "voltar": item.get("voltar"),
        "proximo": item.get("proximo"),
    }


def _numero(consulta: dict, chave: str, padrao: float) -> float:
    try:
        valor = float(consulta.get(chave, [padrao])[0])
    except (TypeError, ValueError):
        return padrao
    return valor if math.isfinite(valor) else padrao


class _HandlerMidia(BaseHTTPRequestHandler):
    server_version = f"TermuxToons/{VERSION}-{ASSINATURA}"
    timeout = 120  # solta conexões paradas
    maximo_transmissoes = 3

    def _cabecalhos(self, status: int, tipo: str, comprimento: int | None, extra: dict | None = None) -> None:
        self.send_response(status)
        cabecalhos = {"Content-Type": tipo, "Cache-Control": "private, no-cache", "X-Content-Type-Options": "nosniff",
                      "Referrer-Policy": "no-referrer", "X-Robots-Tag": "noindex, nofollow", **(extra or {})}
        if comprimento is not None:
            cabecalhos["Content-Length"] = str(comprimento)
        for chave, valor in cabecalhos.items():
            self.send_header(chave, valor)
        self.end_headers()

    def _enviar(self, status: int, tipo: str, corpo: bytes, com_corpo: bool, extra: dict | None = None) -> None:
        self._cabecalhos(status, tipo, len(corpo), extra)
        if com_corpo and corpo:
            self.wfile.write(corpo)

    def _json(self, status: int, dados: dict, com_corpo: bool) -> None:
        self._enviar(status, "application/json; charset=utf-8", json.dumps(dados).encode(), com_corpo)

    def _aviso(self, status: int, msg: str, com_corpo: bool) -> None:
        import html as html_mod
        corpo = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,"
                 "initial-scale=1'><title>Termux-Toons</title><body style='margin:0;min-height:100vh;display:grid;"
                 "place-items:center;font-family:system-ui,sans-serif;background:#09090b;color:#f4f4f5'>"
                 "<div style='text-align:center;padding:24px'><div style='font-size:48px'>🎬</div>"
                 f"<h2 style='font-weight:600'>{html_mod.escape(msg)}</h2></div>").encode()
        self._enviar(status, "text/html; charset=utf-8", corpo, com_corpo)

    def _pagina(self, item: dict, fontes: list, sonda, com_corpo: bool) -> None:
        import html as html_mod
        config = config_do_player(item, fontes, sonda)
        dados = json.dumps(config).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
        trocas = {"@TITULO@": html_mod.escape(config["titulo"]), "@CONFIG@": dados}
        pagina = re.sub(r"@TITULO@|@CONFIG@", lambda m: trocas[m.group()], PAGINA_FILME)
        self._enviar(200, "text/html; charset=utf-8", pagina.encode(), com_corpo,
                     {"Content-Security-Policy": "default-src 'self'; script-src 'unsafe-inline'; "
                      "style-src 'unsafe-inline'; img-src 'self' data:; media-src 'self'; frame-ancestors 'none'"})

    def _legenda(self, item: dict, sonda, n: int, com_corpo: bool) -> None:
        legendas = legendas_do_item(item, sonda)
        if not 0 <= n < len(legendas):
            return self._json(404, {"erro": "Legenda não encontrada."}, com_corpo)
        legenda = legendas[n]
        if legenda["tipo"] == "embutida":
            todas = [l["ref"] for l in legendas if l["tipo"] == "embutida"]
            dados, estado = legenda_embutida(item, legenda["ref"], todas)
            if dados is None:
                if estado == "extraindo":
                    return self._json(202, {"status": "extraindo"}, com_corpo)
                return self._json(500, {"erro": "Não consegui extrair essa legenda."}, com_corpo)
        elif legenda["tipo"] == "link":
            dados = _baixar_legenda_link(legenda["ref"])
        elif legenda["tipo"] == "torbox":
            try:
                letra, id_item, _ = item["torbox"]
                dados = _baixar_legenda_link(torbox_link(_torbox_config()[0], letra, id_item, legenda["ref"]))
            except ToonsError:
                dados = None
        else:
            try:
                dados = Path(legenda["ref"]).read_bytes()
            except OSError:
                dados = None
        if dados is None:
            return self._json(404, {"erro": "Legenda indisponível."}, com_corpo)
        self._enviar(200, "text/vtt; charset=utf-8", _srt_para_vtt(dados), com_corpo)

    def _copiar(self, origem, restante: int | None) -> None:
        """Copia bytes de `origem` para quem pediu até o fim (ou `restante` bytes)."""
        try:
            while restante is None or restante > 0:
                bloco = origem.read(256 * 1024 if restante is None else min(256 * 1024, restante))
                if not bloco:
                    break
                self.wfile.write(bloco)
                if restante is not None:
                    restante -= len(bloco)
        except OSError:
            pass  # a pessoa fechou a aba ou pulou para outro ponto do filme

    def _arquivo(self, arq: Path, sonda, com_corpo: bool) -> None:
        try:
            tamanho = arq.stat().st_size
            arquivo = open(arq, "rb")
        except OSError:
            return self._aviso(404, "O arquivo não está mais disponível.", com_corpo)
        with arquivo:
            try:
                faixa = _faixa(self.headers.get("Range"), tamanho)
            except ValueError:
                return self._cabecalhos(416, "text/plain", 0, {"Content-Range": f"bytes */{tamanho}"})
            inicio, fim = faixa or (0, tamanho - 1)
            extra = {"Accept-Ranges": "bytes"}
            if faixa:
                extra["Content-Range"] = f"bytes {inicio}-{fim}/{tamanho}"
            self._cabecalhos(206 if faixa else 200, _tipo_mime(str(arq), sonda), fim - inicio + 1, extra)
            if com_corpo:
                arquivo.seek(inicio)
                self._copiar(arquivo, fim - inicio + 1)
        return None

    def _repassar(self, url: str, sonda, com_corpo: bool) -> None:
        """Entrega um link da internet como se fosse um arquivo daqui (com Range), sem revelar o endereço."""
        cabecalhos = _cabecalhos_de(url)
        if self.headers.get("Range"):
            cabecalhos["Range"] = self.headers["Range"]
        try:
            resposta = urllib.request.urlopen(urllib.request.Request(url, headers=cabecalhos), timeout=30)
        except urllib.error.HTTPError as e:
            if e.code == 416:
                return self._cabecalhos(416, "text/plain", 0, {"Content-Range": e.headers.get("Content-Range", "bytes */0")})
            return self._aviso(502, f"O site de origem respondeu HTTP {e.code} (o link pode ter expirado).", com_corpo)
        except OSError:
            return self._aviso(502, "Não consegui acessar o link de origem do vídeo.", com_corpo)
        with resposta:
            extra = {}
            if resposta.headers.get("Content-Range"):
                extra["Content-Range"] = resposta.headers["Content-Range"]
            if resposta.status == 206 or resposta.headers.get("Accept-Ranges", "").lower() == "bytes":
                extra["Accept-Ranges"] = "bytes"
            comprimento = str(resposta.headers.get("Content-Length", ""))
            self._cabecalhos(resposta.status, _tipo_mime(url, sonda), int(comprimento) if comprimento.isdigit() else None, extra)
            if com_corpo:
                self._copiar(resposta, None)
        return None

    def _transmitir(self, item: dict, fontes: list, sonda, consulta: dict, com_corpo: bool) -> None:
        if not tem("ffmpeg"):
            return self._aviso(503, "O ffmpeg não está instalado no celular que compartilhou o vídeo.", com_corpo)
        if not com_corpo:
            return self._cabecalhos(200, "video/mp4", None, {"Cache-Control": "no-store"})
        faixas = len(sonda["audio"]) if sonda else 1
        audio = int(_numero(consulta, "a", 0))
        audio = audio if 0 <= audio < max(faixas, 1) else 0
        inicio = max(0.0, _numero(consulta, "t", 0))
        sessao_player = re.sub(r"[^a-z0-9]", "", consulta.get("s", [""])[0])[:16] or "x"
        chave = f"{item['token']}:{sessao_player}"
        cmd = comando_transmissao(fontes, sonda, audio, inicio, consulta.get("v", [""])[0] == "h264",
                                  "opus" if consulta.get("ac", [""])[0] == "opus" else "aac")
        processo = None
        with _TRANSMISSOES_TRAVA:
            antigo = _TRANSMISSOES.pop(chave, None)
            if antigo:  # o mesmo player pulou para outro ponto ou trocou o áudio: a conversão anterior acaba
                antigo.kill()
            if len(_TRANSMISSOES) < self.maximo_transmissoes:
                processo = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
                _TRANSMISSOES[chave] = processo
        if processo is None:
            return self._aviso(503, "Muita gente assistindo ao mesmo tempo. Tente de novo daqui a pouco.", com_corpo)
        try:
            primeiro = processo.stdout.read1(64 * 1024)
            if not primeiro:
                return self._aviso(502, "Não consegui abrir o vídeo (o link de origem pode ter expirado).", com_corpo)
            self.connection.settimeout(900)  # o player pode passar um bom tempo pausado sem ler nada
            self._cabecalhos(200, "video/mp4", None, {"Cache-Control": "no-store"})
            bloco = primeiro
            while bloco:
                self.wfile.write(bloco)
                bloco = processo.stdout.read1(256 * 1024)
        except OSError:
            pass  # a pessoa fechou a aba, pulou para outro ponto ou ficou tempo demais pausada
        finally:
            if processo.poll() is None:
                processo.kill()
            processo.wait()
            processo.stdout.close()
            with _TRANSMISSOES_TRAVA:
                if _TRANSMISSOES.get(chave) is processo:
                    del _TRANSMISSOES[chave]
        return None

    def _estado(self, item: dict, com_corpo: bool) -> None:
        """Por que a transmissão falhou? O player pergunta isso para mostrar uma mensagem útil."""
        fonte = fonte_de(item)
        if item.get("pagina") or item.get("torbox"):  # pede endereços novos: os antigos podem ter expirado
            try:
                fonte = fontes_de(item, renovar=True)[0]
            except ToonsError as e:
                return self._json(200, {"ok": False, "erro": str(e)}, com_corpo)
        if eh_link(fonte):
            try:
                status = info_link(fonte)["status"]
            except OSError:
                return self._json(200, {"ok": False, "erro": "O celular não conseguiu acessar o link de origem do vídeo."}, com_corpo)
            if status >= 400:
                return self._json(200, {"ok": False, "erro": f"O link de origem respondeu HTTP {status}: "
                                        "ele pode ter expirado. Peça a quem enviou para atualizar o link."}, com_corpo)
        elif not Path(fonte).is_file():
            return self._json(200, {"ok": False, "erro": "O arquivo não está mais disponível."}, com_corpo)
        with _TRANSMISSOES_TRAVA:
            lotado = len(_TRANSMISSOES) >= self.maximo_transmissoes
        if lotado:
            return self._json(200, {"ok": False, "erro": "Muita gente assistindo ao mesmo tempo. Tente de novo daqui a pouco."}, com_corpo)
        return self._json(200, {"ok": True}, com_corpo)

    def _catalogo(self, codigo: str, lista: bool, consulta: dict, com_corpo: bool) -> None:
        """Página da biblioteca do TorBox (/tb/<código>) e a lista dela em JSON."""
        chave, catalogo = _torbox_config()
        if not chave or not catalogo or not hmac.compare_digest(codigo.encode(), catalogo.encode()):
            return self._aviso(404, "Link não encontrado.", com_corpo)
        if not lista:
            return self._enviar(200, "text/html; charset=utf-8", PAGINA_TORBOX.encode(), com_corpo,
                                {"Content-Security-Policy": "default-src 'self'; script-src 'unsafe-inline'; "
                                 "style-src 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'"})
        try:
            itens = torbox_biblioteca(chave, renovar=consulta.get("renovar") == ["1"])
        except ToonsError as e:
            return self._json(502, {"erro": str(e)}, com_corpo)
        saida = [{**{k: it[k] for k in ("tipo", "id", "nome", "tamanho", "data", "pronto", "progresso")},
                  "videos": [{"nome": v["nome"], "tamanho": v["tamanho"],
                              "token": token_torbox(catalogo, it["tipo"], it["id"], v["fid"])} for v in it["videos"]]}
                 for it in itens]
        return self._json(200, {"itens": saida}, com_corpo)

    def _tratar(self, com_corpo: bool) -> None:
        partes = urllib.parse.urlsplit(self.path)
        catalogo = re.fullmatch(r"/tb/([A-Za-z0-9_-]{8,40})(/lista\.json)?/?", partes.path)
        if catalogo:
            return self._catalogo(catalogo.group(1), bool(catalogo.group(2)), urllib.parse.parse_qs(partes.query), com_corpo)
        m = re.fullmatch(r"/v/([A-Za-z0-9_-]{8,64})(?:/(video|stream|ponto|estado|legenda/(\d{1,3})\.vtt))?/?", partes.path)
        item = achar_compartilhamento(m.group(1)) if m else None
        if item is None:
            return self._aviso(404, "Link não encontrado.", com_corpo)
        if expirado(item):
            return self._aviso(410, "Este link expirou.", com_corpo)
        fonte, recurso = fonte_de(item), m.group(2)
        if not eh_link(fonte) and not Path(fonte).is_file():
            return self._aviso(404, "O arquivo não está mais disponível.", com_corpo)
        if recurso == "estado":
            return self._estado(item, com_corpo)
        try:
            fontes = fontes_de(item)
        except ToonsError as e:
            return self._aviso(502, str(e), com_corpo)
        sonda = sonda_em_cache(fontes)
        consulta = urllib.parse.parse_qs(partes.query)
        if recurso == "video":
            if not _arquivo_unico(fontes, sonda):  # vídeo e áudio separados ou HLS: vai convertido, sem pular
                return self._transmitir(item, fontes, sonda, {"s": [secrets.token_hex(4)]}, com_corpo)
            if eh_link(fontes[0]):
                return self._repassar(fontes[0], sonda, com_corpo)
            return self._arquivo(Path(fontes[0]), sonda, com_corpo)
        if recurso == "stream":
            return self._transmitir(item, fontes, sonda, consulta, com_corpo)
        if recurso == "ponto":
            t = max(0.0, _numero(consulta, "t", 0))
            return self._json(200, {"t": round(ponto_de_corte(fontes[0], sonda, t), 3)}, com_corpo)
        if recurso:
            return self._legenda(item, sonda, int(m.group(3)), com_corpo)
        return self._pagina(item, fontes, sonda, com_corpo)

    def do_GET(self):
        self._tratar(True)

    def do_HEAD(self):
        self._tratar(False)

    def log_message(self, fmt, *args):
        texto = re.sub(r"/(v|tb)/([A-Za-z0-9_-]{4})[A-Za-z0-9_-]*", r"/\1/\2…", fmt % args)  # não grava o link inteiro
        log(f"{self.client_address[0]} {texto}")


def servir_midia(host: str, porta: int) -> None:
    """Sobe o servidor de vídeo em primeiro plano (é o que roda dentro do tmux)."""
    _HandlerMidia.maximo_transmissoes = max(1, int(cfg().get("midia_transmissoes", 3)))
    if not tem("ffmpeg"):
        log("Aviso: sem o ffmpeg, só vídeos que o navegador já toca (MP4/WebM com uma trilha de áudio) funcionam.")
    with ThreadingHTTPServer((host, porta), _HandlerMidia) as servidor:
        log(f"Servidor de vídeo em http://{host}:{porta}  (rede local: http://{ip_local()}:{porta})")
        log("Só entrega os vídeos com link ativo. Ctrl+C para parar.")
        try:
            servidor.serve_forever()
        finally:
            with _TRANSMISSOES_TRAVA:
                for processo in _TRANSMISSOES.values():
                    processo.kill()


# ── Criar, listar e revogar links ────────────────────────────────────

def lista_compartilhamentos() -> list:
    """Links atuais, relidos do disco (o CLI e o menu podem criar links ao mesmo tempo)."""
    c = cfg()
    c["compartilhamentos"] = ler_json(CONFIG_FILE, {}).get("compartilhamentos", [])
    return c["compartilhamentos"]


def titulo_do_arquivo(arq: Path) -> str:
    """'Filme.Novo.2021.web.mp4' -> 'Filme Novo 2021' (sem o '.web' da versão convertida)."""
    return re.sub(r"[._]+", " ", re.sub(r"\.web$", "", arq.stem)).strip()


def titulo_do_link(url: str, nome: str = "") -> str:
    """Título a partir do nome do arquivo (do servidor ou do próprio link); 'Vídeo' se não houver."""
    nome = nome or urllib.parse.unquote(os.path.basename(urllib.parse.urlsplit(url).path))
    return titulo_do_arquivo(Path(nome)) if Path(nome).suffix.lower() in EXTENSOES_VIDEO else "Vídeo"


def criar_compartilhamento(alvo, titulo_filme: str | None = None, horas: float | None = None,
                           legendas: list | None = None, embutidas: list | None = None, pagina: bool = False) -> dict:
    """Cria um link secreto para um vídeo do celular, um link direto da internet ou (`pagina`) uma página de
    vídeo que o yt-dlp lê na hora de assistir (YouTube, Vimeo...)."""
    item = {"token": secrets.token_urlsafe(16)}
    if eh_link(alvo):
        item["pagina" if pagina else "url"] = str(alvo).strip()
        padrao = "Vídeo" if pagina else titulo_do_link(str(alvo).strip())
    else:
        arq = Path(os.path.expanduser(str(alvo)))
        if not arq.is_file():
            raise ToonsError(f"Arquivo não encontrado: {arq}")
        if arq.suffix.lower() not in EXTENSOES_VIDEO:
            raise ToonsError(f"Só compartilho vídeos ({', '.join(sorted(EXTENSOES_VIDEO))}); este é '{arq.suffix}'.")
        item["caminho"] = str(arq.resolve())
        padrao = titulo_do_arquivo(arq)
    agora = time.time()
    item.update({"titulo": (titulo_filme or "").strip() or padrao, "criado": agora,
                 "expira": agora + horas * 3600 if horas else None})
    if legendas:
        item["legendas"] = list(legendas)
    if embutidas:
        item["legendas_embutidas"] = sorted(embutidas)
    lista_compartilhamentos().append(item)
    salvar_cfg()
    return item


def atualizar_compartilhamento(token: str, **campos) -> dict | None:
    """Muda campos de um link (None apaga o campo)."""
    for item in lista_compartilhamentos():
        if item["token"] == token:
            item.update(campos)
            for chave in [k for k, v in campos.items() if v is None]:
                item.pop(chave, None)
            salvar_cfg()
            return item
    return None


def revogar_compartilhamentos(tokens: set) -> int:
    lista = lista_compartilhamentos()
    restantes = [i for i in lista if i["token"] not in tokens]
    cfg()["compartilhamentos"] = restantes
    salvar_cfg()
    return len(lista) - len(restantes)


def descricao_prazo(item: dict) -> str:
    if not item.get("expira"):
        return "sem prazo"
    resta = item["expira"] - time.time()
    if resta <= 0:
        return "EXPIROU"
    horas, minutos = divmod(int(resta // 60), 60)
    return f"expira em {horas // 24}d {horas % 24}h" if horas >= 24 else f"expira em {horas}h {minutos:02d}min"


def links_de(item: dict) -> list:
    """[(onde funciona, link)] — rede local e, se o túnel estiver ligado, a internet."""
    porta = cfg()["midia_porta"]
    links = [("Mesma rede Wi-Fi", f"http://{ip_local()}:{porta}/v/{item['token']}")]
    if servico_ativo("tunel-midia") and url_tunel("tunel-midia"):
        links.append(("Internet", f"{url_tunel('tunel-midia')}/v/{item['token']}"))
    return links


def porta_livre(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", porta))
        except OSError:
            return False
    return True


def _versao_servidor_midia(porta: int) -> str:
    """Cabeçalho 'Server' do servidor de vídeo que está no ar ('' se não respondeu)."""
    req = urllib.request.Request(f"http://127.0.0.1:{porta}/", method="HEAD")
    try:
        with _SEM_PROXY.open(req, timeout=3) as r:
            return r.headers.get("Server", "")
    except urllib.error.HTTPError as e:
        return e.headers.get("Server", "")
    except OSError:
        return ""


def garantir_servidor_midia() -> bool:
    porta = cfg()["midia_porta"]
    if servico_ativo("midia"):
        versao = _versao_servidor_midia(porta)
        if not versao or f"TermuxToons/{VERSION}-{ASSINATURA}" in versao:
            return True
        info("O servidor de vídeo ainda roda o código antigo do Termux-Toons (de antes da atualização); reiniciando...")
        parar_servico("midia")
        time.sleep(1)
    if not porta_livre(porta):
        raise ToonsError(f"A porta {porta} já está em uso por outro programa. Troque em 'Porta do servidor'.")
    return iniciar_servico("midia", cmd_self("midia", "--porta", str(porta)), reiniciar=True)


def mostrar_links(item: dict) -> None:
    origem = ("▶ página de vídeo" if item.get("pagina") else "🌐 link da internet" if item.get("url")
              else "📁 arquivo do celular")
    print(f"\n{NEG}🎬 {item['titulo']}{RST}  {DIM}({origem} · {descricao_prazo(item)}){RST}")
    for onde, link in links_de(item):
        print(f"  {CIANO}{onde}:{RST}\n  {NEG}{link}{RST}")
    print(f"\n  {DIM}No VLC (todas as trilhas de áudio e legendas): use o mesmo link terminado em /video.{RST}")
    if not (servico_ativo("tunel-midia") and url_tunel("tunel-midia")):
        print(f"  {DIM}Para quem está fora da sua rede Wi-Fi, ligue o 'Túnel para a internet' neste menu.{RST}")


def abrir_no_android(alvo: str, pacote: str | None = None) -> None:
    """Abre um vídeo (link ou arquivo) num app do Android, como o VLC: o app toca direto, sem baixar."""
    if not eh_link(alvo):
        if not tem("termux-open"):
            raise ToonsError("'termux-open' não encontrado (só existe dentro do Termux).")
        rodar(["termux-open", "--content-type", "video/*", alvo], capturar=True, timeout=20)
        return
    if not tem("am"):
        raise ToonsError("Comando 'am' não encontrado (só existe dentro do Termux).")
    cmd = ["am", "start", "-a", "android.intent.action.VIEW", "-t", "video/*", "-d", alvo]
    if pacote:
        cmd += ["-p", pacote]
    proc = rodar(cmd, capturar=True, timeout=20)
    texto = f"{proc.stdout or ''}{proc.stderr or ''}"
    if proc.returncode != 0 or re.search(r"\bError\b", texto):
        dica_vlc = "O VLC está instalado? " if pacote == VLC_ANDROID else ""
        raise ToonsError(f"{dica_vlc}O Android não abriu o vídeo: {texto.strip()[-200:]}")
    ok("Abrindo no app de vídeo...")


def endereco_para_assistir(url: str) -> str:
    """Link de arquivo passa direto; página (YouTube, TikTok...) vira o endereço do vídeo pelo yt-dlp."""
    try:
        dados = info_link(url)
    except OSError:
        dados = {"status": 0, "tipo": ""}
    if dados["status"] and dados["status"] < 400 and not dados["tipo"].startswith("text/"):
        return url
    if not garantir_deps_musica(com_player=False):
        raise ToonsError("Sem o yt-dlp não consigo achar o vídeo dessa página.")
    info("É uma página: procurando o endereço do vídeo com o yt-dlp...")
    proc = rodar(["yt-dlp", "-g", "-f", "b", "--no-warnings", "--no-playlist", url], capturar=True, timeout=120)
    enderecos = (proc.stdout or "").split()
    if proc.returncode != 0 or not enderecos:
        raise ToonsError("O yt-dlp não achou um vídeo nesse link. " + (proc.stderr or "").strip()[-300:])
    return enderecos[0]


def assistir_link_no_celular(url: str | None = None) -> None:
    """Toca um link no VLC (ou outro app) do próprio celular, sem baixar o vídeo."""
    if url is None:
        info("Serve link direto de arquivo (servidor seu, nuvem, debrid...) e páginas de vídeo (YouTube, TikTok...).")
        url = perguntar("Link do vídeo")
    if not url:
        return
    if not eh_link(url):
        raise ToonsError("O link precisa começar com http:// ou https://")
    alvo = endereco_para_assistir(url)
    i = escolher("Abrir em qual app?", ["VLC", "Escolher o app (MX Player, Just Player...)"])
    if i is not None:
        abrir_no_android(alvo, VLC_ANDROID if i == 0 else None)


# ── Conversão para MP4 (ffmpeg) ──────────────────────────────────────

@contextlib.contextmanager
def manter_acordado():
    """Impede o celular de dormir durante tarefas longas (conversão de vídeo)."""
    usar = tem("termux-wake-lock")
    if usar:
        rodar(["termux-wake-lock"], mostrar=False, timeout=10)
    try:
        yield
    finally:
        if usar and not servicos_ativos():
            rodar(["termux-wake-unlock"], mostrar=False, timeout=10)


def converter_para_mp4(origem: Path):
    """Gera '<nome>.web.mp4' (H.264 + AAC) que toca em qualquer navegador. Devolve o caminho."""
    if not garantir_cmd("ffmpeg"):
        return None
    sonda = sondar_video(origem)
    destino = origem.with_name(origem.stem + ".web.mp4")
    if destino.exists() and destino.stat().st_size > 0:
        info(f"Já existe uma versão convertida: {destino.name}")
        if confirmar("Usar a versão que já existe?", True):
            return destino

    trilha = 0
    if sonda and len(sonda["audio"]) > 1:
        info("Este arquivo tem mais de uma trilha de áudio (ex.: dublado e original). O MP4 convertido fica com "
             "uma só; para trocar de trilha no player, compartilhe o arquivo original (o servidor converte na hora).")
        trilha = escolher("Qual áudio manter?", [_rotulo_faixa(f) for f in sonda["audio"]],
                          str(_indice_portugues(sonda["audio"]) + 1))
        if trilha is None:
            return None

    copiar_video = bool(sonda and sonda["video"] and _video_compativel(sonda["video"][0]))
    if copiar_video:
        modo = escolher("Como converter?", [
            "Rápido: mantém o vídeo como está e só troca o áudio (recomendado)",
            "Completo: recodifica o vídeo (bem mais lento no celular)"])
        if modo is None:
            return None
        copiar_video = modo == 0
    else:
        aviso("O vídeo precisa ser recodificado para H.264. No celular isso pode levar mais tempo "
              "do que a duração do filme; deixe carregando e com a tela ligada.")
        if not confirmar("Continuar?", False):
            return None

    legenda = None
    textos = [(n, f) for n, f in enumerate(sonda["legendas"]) if f.get("codec_name") in CODECS_LEGENDA_TEXTO] \
        if sonda else []
    if textos:
        opcoes = ["Nenhuma"] + [_rotulo_faixa(f) for _, f in textos]
        padrao = _indice_portugues([f for _, f in textos]) + 2 if any(_eh_portugues(f) for _, f in textos) else 1
        escolha = escolher("Extrair uma legenda embutida para o player?", opcoes, str(padrao))
        if escolha:
            legenda = textos[escolha - 1][0]

    parcial = destino.with_name(destino.name + ".part")  # só vira .web.mp4 se terminar sem erro
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "warning", "-stats", "-y", "-i", str(origem),
           "-map", "0:v:0", "-map", f"0:a:{trilha}?", "-sn", "-dn"]
    cmd += ["-c:v", "copy"] if copiar_video else \
        ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p"]
    cmd += ["-c:a", "aac", "-b:a", "160k", "-ac", "2", "-movflags", "+faststart", "-f", "mp4", str(parcial)]
    info("Convertendo...")
    t0 = time.time()
    with manter_acordado():
        resultado = rodar(cmd)
    if resultado.returncode != 0 or not parcial.exists():
        parcial.unlink(missing_ok=True)
        raise ToonsError("O ffmpeg não conseguiu converter este arquivo.")
    parcial.replace(destino)
    if legenda is not None:
        rodar(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(origem), "-map", f"0:s:{legenda}",
               "-c:s", "webvtt", str(destino.with_suffix(".vtt"))], capturar=True, mostrar=False)
        if destino.with_suffix(".vtt").exists():
            ok(f"Legenda extraída: {destino.with_suffix('.vtt').name}")
    ok(f"Pronto em {(time.time() - t0) / 60:.1f} min: {destino.name} ({bytes_humanos(destino.stat().st_size)})")
    return destino


# ── Menu ─────────────────────────────────────────────────────────────

def videos_para_compartilhar() -> list:
    """[(data, tamanho, caminho)] dos vídeos nas pastas de vídeo/downloads/filmes, os mais novos primeiro."""
    pastas = [pasta_videos(), DOWNLOADS, HOME / "storage" / "movies", HOME / "storage" / "shared" / "Movies"]
    vistos, achados = set(), []
    for pasta in pastas:
        if not pasta.is_dir():
            continue
        for arq, st in _arquivos(pasta):
            real = arq.resolve()
            if arq.suffix.lower() in EXTENSOES_VIDEO and not arq.name.endswith(".part") and real not in vistos:
                vistos.add(real)
                achados.append((st.st_mtime, st.st_size, arq))
    return sorted(achados, reverse=True)


def _escolher_video():
    videos = videos_para_compartilhar()
    i = escolher("Qual vídeo você quer compartilhar?",
                 [f"{arq.name} · {bytes_humanos(tam)}" for _, tam, arq in videos] + ["📁 Digitar outro caminho..."])
    if i is None:
        return None
    if i < len(videos):
        return videos[i][2]
    caminho = Path(os.path.expanduser(perguntar("Caminho do arquivo")))
    if not caminho.is_file():
        raise ToonsError(f"Arquivo não encontrado: {caminho}")
    return caminho


def _pedir_prazo():
    """(confirmado, horas ou None). Cancelar com Esc devolve confirmado=False."""
    opcoes = [("Sem prazo (até eu apagar o link)", None), ("6 horas", 6), ("24 horas", 24),
              ("7 dias", 168), ("Outro prazo (em horas)", -1)]
    i = escolher("Por quanto tempo o link vai funcionar?", [rotulo for rotulo, _ in opcoes], "3")
    if i is None:
        return False, None
    horas = opcoes[i][1]
    if horas == -1:
        horas = perguntar_float("Quantas horas", 12)
    return True, horas


def conferir_link(url: str) -> dict:
    """Confere um link sem baixar o vídeo e mostra as faixas: {'pagina', 'titulo', 'tamanho', 'sonda'}.
    Link direto de arquivo passa como está; página (YouTube, Vimeo, Google Drive...) é lida pelo yt-dlp."""
    if not eh_link(url):
        raise ToonsError("O link precisa começar com http:// ou https://")
    info("Conferindo o link (sem baixar o vídeo)...")
    try:
        dados = info_link(url)
    except OSError as e:
        dados = {"status": 0, "tipo": "", "nome": "", "tamanho": None, "erro": str(e)}
    eh_pagina = dados["tipo"].startswith("text/") or not 0 < dados["status"] < 400
    if not eh_pagina:
        detalhes = [x for x in (dados["nome"], bytes_humanos(dados["tamanho"]) if dados["tamanho"] else "") if x]
        ok("Link de arquivo funcionando" + (f": {' · '.join(detalhes)}" if detalhes else "."))
        titulo, fontes = titulo_do_link(url, dados["nome"]), [url]
    else:  # página de vídeo, ou um site que só responde a quem parece navegador: o yt-dlp tenta achar o vídeo
        if not tem("yt-dlp") and not garantir_deps_musica(com_player=False):
            raise ToonsError("Para links de página (YouTube, Vimeo...) é preciso o yt-dlp.")
        info("Não é um link direto de arquivo: procurando o vídeo na página com o yt-dlp...")
        try:
            achado = info_pagina(url)
        except ToonsError as e:
            if dados["status"] >= 400:
                raise ToonsError(f"O site respondeu HTTP {dados['status']}: o link pode ter expirado ou exigir "
                                 "login.") from None
            if dados.get("erro"):
                raise ToonsError(f"Não consegui acessar o link: {dados['erro']}") from None
            raise e
        ok(f"Vídeo encontrado: {achado['titulo']}")
        titulo, fontes = achado["titulo"], achado["enderecos"]
    sonda = sonda_em_cache(fontes) if tem("ffprobe") else None
    if sonda:
        mostrar_faixas(sonda)
    elif tem("ffprobe"):
        aviso("O ffmpeg não reconheceu um vídeo nesse link; o player pode não conseguir tocar.")
    return {"pagina": eh_pagina, "titulo": titulo, "tamanho": None if eh_pagina else dados["tamanho"], "sonda": sonda}


def _pedir_legenda_extra() -> list:
    alvo = perguntar("Legenda .srt/.vtt extra: caminho no celular ou link (Enter pula)", "")
    if not alvo:
        return []
    if eh_link(alvo):
        return [alvo]
    arq = Path(os.path.expanduser(alvo))
    if not arq.is_file() or arq.suffix.lower() not in (".srt", ".vtt"):
        aviso(f"Legenda ignorada: {arq} não é um arquivo .srt ou .vtt.")
        return []
    return [str(arq.resolve())]


def _escolher_embutidas(sonda, tamanho) -> list:
    """Num link, legenda embutida exige ler o filme inteiro: só prepara as que você escolher."""
    textos = [(n, f) for n, f in enumerate(sonda["legendas"]) if f.get("codec_name") in CODECS_LEGENDA_TEXTO] \
        if sonda else []
    if not textos:
        return []
    peso = f" ({bytes_humanos(tamanho)})" if tamanho else ""
    info(f"O vídeo tem {len(textos)} legenda(s) embutida(s). Para usá-las no player, o celular baixa o arquivo "
         f"inteiro uma vez{peso} e guarda só as legendas. Prefira fazer isso no Wi-Fi.")
    if not confirmar("Preparar legendas embutidas?", False):
        return []
    sel = escolher_varios("Quais legendas?", [_rotulo_faixa(f) for _, f in textos])
    return [textos[i][0] for i in sel]


def _preparar_legendas(item: dict, sonda) -> None:
    """Pede ao servidor a primeira legenda embutida do link: ele extrai todas de uma vez, em segundo plano."""
    indice = next((i for i, l in enumerate(legendas_do_item(item, sonda)) if l["tipo"] == "embutida"), None)
    if indice is None:
        return
    url = f"http://127.0.0.1:{cfg()['midia_porta']}/v/{item['token']}/legenda/{indice}.vtt"
    for _ in range(10):
        try:
            _SEM_PROXY.open(url, timeout=10).close()
        except OSError:
            time.sleep(1)
            continue
        ok("Legendas sendo preparadas em segundo plano; aparecem no player quando ficarem prontas.")
        return
    aviso("Não consegui pedir as legendas ao servidor agora; elas serão preparadas quando alguém escolher no player.")


@submenu
def menu_torbox():
    """Catálogo da biblioteca do TorBox no navegador: um link só para todos os filmes e séries."""
    c = cfg()

    def exigir_chave():
        if not c.get("torbox_chave"):
            raise ToonsError("Configure primeiro a chave da API do TorBox (primeira opção deste menu).")
        if not c.get("torbox_catalogo"):
            c["torbox_catalogo"] = secrets.token_urlsafe(12)
            salvar_cfg()

    def links() -> list:
        caminho = f"/tb/{c['torbox_catalogo']}"
        lista = [("Mesma rede Wi-Fi", f"http://{ip_local()}:{c['midia_porta']}{caminho}")]
        if servico_ativo("tunel-midia") and url_tunel("tunel-midia"):
            lista.append(("Internet", f"{url_tunel('tunel-midia')}{caminho}"))
        return lista

    def configurar():
        info("No TorBox: torbox.app → Settings → API → copie a 'API Key'. Ela fica só neste celular "
             "(no config.json, com permissão 600) e nunca é enviada para quem abre o catálogo.")
        chave = perguntar("Chave da API do TorBox").strip()
        if not chave:
            return
        info("Testando a chave...")
        itens = torbox_biblioteca(chave, renovar=True)
        c["torbox_chave"] = chave
        exigir_chave()
        salvar_cfg()
        ok(f"Chave funcionando: {len(itens)} título(s) com {sum(len(it['videos']) for it in itens)} vídeo(s).")
        if confirmar("Abrir o catálogo agora?", True):
            abrir()

    def abrir():
        exigir_chave()
        garantir_servidor_midia()
        link = f"http://127.0.0.1:{c['midia_porta']}/tb/{c['torbox_catalogo']}"
        if tem("termux-open-url"):
            rodar(["termux-open-url", link], capturar=True, timeout=20)
        else:
            info(f"Abra no navegador: {link}")

    def mostrar_enviar():
        exigir_chave()
        garantir_servidor_midia()
        for onde, link in links():
            print(f"  {CIANO}{onde}:{RST}\n  {NEG}{link}{RST}")
        aviso("Quem tiver este link vê e assiste a TODA a sua biblioteca do TorBox. Mande só para quem você "
              "confia; 'Gerar um link novo' corta o acesso de quem tem o antigo.")
        if len(links()) == 1:
            info("Para assistir fora do seu Wi-Fi, ligue o túnel neste menu.")
        _, link = links()[-1]
        i = escolher("O que fazer com o link?", ["Copiar link", "Enviar pelo WhatsApp, Telegram... (menu do Android)",
                                                 "Mostrar QR code", "Nada"], "4")
        if i == 0:
            _tapi(["termux-clipboard-set"], 10, entrada=link, json_saida=False)
            ok("Link copiado.")
        elif i == 1:
            _tapi(["termux-share", "-a", "send"], 30, entrada=f"🍿 Minha biblioteca\n{link}", json_saida=False)
        elif i == 2 and garantir_cmd("qrencode", "libqrencode"):
            rodar(["qrencode", "-t", "ansiutf8"], entrada=link, mostrar=False)

    def assistir_aqui():
        exigir_chave()
        itens = [it for it in torbox_biblioteca(c["torbox_chave"], renovar=True) if it["pronto"]]
        i = escolher("Qual título?", [f"{it['nome']} · {len(it['videos'])} vídeo(s)" for it in itens])
        if i is None:
            return
        videos = itens[i]["videos"]
        j = 0 if len(videos) == 1 else escolher("Qual vídeo?", [v["nome"] for v in videos])
        if j is None:
            return
        link = torbox_link(c["torbox_chave"], itens[i]["tipo"], itens[i]["id"], videos[j]["fid"])
        k = escolher("Abrir em qual app?", ["VLC", "Escolher o app (MX Player, Just Player...)"])
        if k is not None:
            abrir_no_android(link, VLC_ANDROID if k == 0 else None)

    def tunel():
        exigir_chave()
        garantir_servidor_midia()
        abrir_tunel("tunel-midia", c["midia_porta"])
        mostrar_enviar()

    def novo_link():
        if confirmar("Gerar um link novo? O antigo (e os vídeos abertos por ele) param de funcionar.", True):
            c["torbox_catalogo"] = secrets.token_urlsafe(12)
            salvar_cfg()
            ok("Link novo gerado.")
            mostrar_enviar()

    def remover():
        if confirmar("Apagar a chave do TorBox deste celular? O catálogo para de funcionar.", False):
            c["torbox_chave"] = c["torbox_catalogo"] = ""
            salvar_cfg()
            ok("Chave apagada.")

    menu("🍿 Catálogo do TorBox", [
        (lambda: f"Configurar a chave da API ({'configurada' if c.get('torbox_chave') else 'não configurada'})", configurar),
        ("Abrir o catálogo neste celular (navegador)", abrir),
        ("Mostrar / enviar o link do catálogo", mostrar_enviar),
        ("Túnel para a internet: ligar (assistir fora do Wi-Fi)", tunel),
        ("Assistir um vídeo da biblioteca no VLC deste celular", assistir_aqui),
        ("Gerar um link novo (o antigo para de funcionar)", novo_link),
        ("Remover a chave do TorBox", remover),
    ])


@submenu
def menu_midia():
    c = cfg()
    direitos = ("Compartilhe só o que você pode distribuir: vídeos seus, de domínio público, de licença livre "
                "ou com autorização de quem tem os direitos.")

    def compartilhar():
        info(direitos)
        arq = _escolher_video()
        if arq is None:
            return
        sonda = sondar_video(arq)
        if sonda:
            mostrar_faixas(sonda)
        problemas = problemas_de_reproducao(arq, sonda)
        if problemas:
            print()
            aviso("Do jeito que está, o navegador não toca este arquivo:\n  • " + "\n  • ".join(problemas))
            if tem("ffmpeg"):
                info("O servidor converte na hora enquanto a pessoa assiste e o player deixa trocar a trilha de áudio. "
                     + ("A imagem também precisa ser recodificada, o que pesa no celular; se travar, converta antes."
                        if _precisa_recodificar(sonda) else "A imagem é só copiada, então pesa pouco no celular."))
                opcoes = ["Criar o link e converter na hora (recomendado)",
                          "Converter para MP4 antes (arquivo novo; toca até no Safari do iPhone)", "Cancelar"]
            else:
                opcoes = ["Criar o link assim mesmo", "Converter para MP4 antes (instala o ffmpeg)", "Cancelar"]
            i = escolher("O que fazer?", opcoes)
            if i is None or i == 2:
                return
            if i == 1:
                arq = converter_para_mp4(arq)
                if arq is None:
                    return
        titulo_filme = perguntar("Título que aparece na página", titulo_do_arquivo(arq))
        confirmado, horas = _pedir_prazo()
        if not confirmado:
            return
        item = criar_compartilhamento(arq, titulo_filme, horas)
        garantir_servidor_midia()
        mostrar_links(item)
        oferecer_envio(item)

    def compartilhar_link():
        info(direitos)
        info("Cole qualquer link de vídeo: link direto de um arquivo (o mesmo que você abriria no VLC: servidor "
             "seu, Google Drive, Dropbox, OneDrive, serviços de debrid...) ou uma página de vídeo (YouTube, Vimeo, "
             "Dailymotion e os outros sites que o yt-dlp lê). O filme não é baixado: o celular repassa "
             "enquanto a pessoa assiste.")
        url = perguntar("Link do vídeo").strip()
        if not url:
            return
        if not tem("ffmpeg"):
            aviso("Sem o ffmpeg só links de MP4/WebM com uma trilha de áudio tocam no navegador "
                  "(MKV, áudio AC3/DTS, troca de trilha e páginas como o YouTube precisam dele).")
            garantir_cmd("ffmpeg")
        link = conferir_link(url)
        titulo_filme = perguntar("Título que aparece na página", link["titulo"])
        confirmado, horas = _pedir_prazo()
        if not confirmado:
            return
        extras = _pedir_legenda_extra()
        embutidas = [] if link["pagina"] else _escolher_embutidas(link["sonda"], link["tamanho"])
        item = criar_compartilhamento(url, titulo_filme, horas, legendas=extras, embutidas=embutidas,
                                      pagina=link["pagina"])
        garantir_servidor_midia()
        if embutidas:
            _preparar_legendas(item, link["sonda"])
        mostrar_links(item)
        if link["pagina"]:
            info("O endereço do vídeo na página é renovado sozinho quando o site o expira.")
        else:
            info("Se o link expirar (links de download costumam valer só algumas horas), gere outro e use "
                 "'Meus links → Trocar o endereço do vídeo': o link que você enviou continua o mesmo.")
        oferecer_envio(item)

    def oferecer_envio(item):
        links = links_de(item)
        _, link = links[-1]  # o da internet, se existir; senão o da rede local
        acoes = ["Copiar link", "Enviar pelo WhatsApp, Telegram... (menu do Android)", "Mostrar QR code", "Nada"]
        i = escolher("O que fazer com o link?", acoes, "4")
        texto = f"🎬 {item['titulo']}\n{link}"
        if i == 0:
            _tapi(["termux-clipboard-set"], 10, entrada=link, json_saida=False)
            ok("Link copiado.")
        elif i == 1:
            _tapi(["termux-share", "-a", "send"], 30, entrada=texto, json_saida=False)
        elif i == 2 and garantir_cmd("qrencode", "libqrencode"):
            rodar(["qrencode", "-t", "ansiutf8"], entrada=link, mostrar=False)

    def assistir_aqui(item):
        i = escolher("Abrir onde?", ["VLC", "Outro app (MX Player, Just Player...)",
                                     "Navegador (o mesmo player de quem recebe o link)"])
        if i is None:
            return
        if i == 2:
            garantir_servidor_midia()
            pagina = f"http://127.0.0.1:{c['midia_porta']}/v/{item['token']}"
            if not tem("termux-open-url"):
                info(f"Abra no navegador: {pagina}")
                return
            rodar(["termux-open-url", pagina], capturar=True, timeout=20)
        else:
            alvo = endereco_para_assistir(item["pagina"]) if item.get("pagina") else fonte_de(item)
            abrir_no_android(alvo, VLC_ANDROID if i == 0 else None)

    def trocar_endereco(item):
        info("Cole o novo link do mesmo vídeo. Quem já tem o link do Termux-Toons não precisa receber outro.")
        url = perguntar("Novo link do vídeo").strip()
        if not url:
            return
        link = conferir_link(url)
        atualizar_compartilhamento(item["token"], url=None if link["pagina"] else url,
                                   pagina=url if link["pagina"] else None)
        ok("Endereço atualizado.")

    def ver_links():
        lista = lista_compartilhamentos()
        if not lista:
            info("Nenhum link criado ainda.")
            return
        i = escolher("Qual link?", [f"{'▶' if it.get('pagina') else '🌐' if it.get('url') else '📁'} "
                                    f"{it['titulo']} · {descricao_prazo(it)}"
                                    for it in lista])
        if i is None:
            return
        item = lista[i]
        mostrar_links(item)
        if item.get("caminho") and not Path(item["caminho"]).is_file():
            aviso("O arquivo deste link não existe mais.")
        acoes = [("Copiar / enviar / QR code", oferecer_envio), ("Assistir neste celular", assistir_aqui)]
        if item.get("url"):
            acoes.append(("Trocar o endereço do vídeo (o link expirou)", trocar_endereco))
        acoes.append(("Apagar este link", None))
        acao = escolher("O que fazer?", [rotulo for rotulo, _ in acoes] + ["Voltar"], str(len(acoes) + 1))
        if acao is None or acao >= len(acoes):
            return
        _, func = acoes[acao]
        if func:
            func(item)
        elif confirmar("Apagar o link? Quem estiver com ele deixa de conseguir assistir."):
            revogar_compartilhamentos({item["token"]})
            ok("Link apagado.")

    def apagar_todos():
        lista = lista_compartilhamentos()
        if not lista:
            info("Nenhum link criado ainda.")
        elif confirmar(f"Apagar TODOS os {len(lista)} link(s)? Ninguém mais consegue assistir."):
            ok(f"{revogar_compartilhamentos({it['token'] for it in lista})} link(s) apagado(s).")

    def apagar_expirados():
        vencidos = {it["token"] for it in lista_compartilhamentos() if expirado(it)}
        ok(f"{revogar_compartilhamentos(vencidos)} link(s) expirado(s) removido(s).")

    def converter():
        arq = _escolher_video()
        if arq is None:
            return
        problemas = problemas_de_reproducao(arq, sondar_video(arq))
        if problemas:
            info("Motivos para converter:\n  • " + "\n  • ".join(problemas))
        else:
            info("Este arquivo já parece compatível com os navegadores.")
        destino = converter_para_mp4(arq)
        if destino and confirmar("Compartilhar o arquivo convertido agora?", True):
            confirmado, horas = _pedir_prazo()
            if confirmado:
                item = criar_compartilhamento(destino, None, horas)
                garantir_servidor_midia()
                mostrar_links(item)
                oferecer_envio(item)

    def iniciar_servidor():
        garantir_servidor_midia()
        info("O servidor só entrega vídeos com link criado. Crie um em 'Compartilhar um filme'.")

    def mudar_porta():
        nova = perguntar_int("Porta do servidor de vídeo", c["midia_porta"], 1024, 65535)
        c["midia_porta"] = nova
        salvar_cfg()
        ok(f"Porta {nova}. Reinicie o servidor e o túnel para valer.")

    def mudar_transmissoes():
        info("Cada pessoa assistindo um vídeo convertido na hora usa um ffmpeg no celular.")
        c["midia_transmissoes"] = perguntar_int("Quantas conversões ao mesmo tempo", c["midia_transmissoes"], 1, 10)
        salvar_cfg()
        ok("Reinicie o servidor de vídeo para valer.")

    def iniciar_tunel():
        aviso("Pelo túnel, quem tiver o link assiste de qualquer lugar. O filme sai do seu celular, então "
              "a velocidade depende do upload da sua internet. O túnel gratuito da Cloudflare é pensado "
              "para testes e pode ficar lento ou cair.")
        if confirmar("Ligar o túnel para a internet?", True):
            garantir_servidor_midia()
            abrir_tunel("tunel-midia", c["midia_porta"])

    menu("📺 Compartilhar filme por link", [
        ("▶  Compartilhar um filme do celular (criar link)", compartilhar),
        ("🌐 Transmitir de um link da internet (sem baixar)", compartilhar_link),
        ("🍿 Catálogo do TorBox (todos os seus filmes e séries num link só)", menu_torbox),
        ("Meus links (copiar, enviar, assistir, apagar)", ver_links),
        ("Assistir um link neste celular (VLC, MX Player...)", assistir_link_no_celular),
        ("Converter filme para MP4 compatível", converter),
        *itens_servico("midia", "Servidor de vídeo", iniciar_servidor),
        ("Túnel para a internet: ligar", iniciar_tunel),
        ("Túnel para a internet: desligar", lambda: parar_servico("tunel-midia")),
        ("Túnel para a internet: mostrar endereço", lambda: info(url_tunel("tunel-midia") or "Túnel desligado.")),
        ("Apagar links expirados", apagar_expirados),
        ("Apagar TODOS os links", apagar_todos),
        (lambda: f"Porta do servidor ({c['midia_porta']})", mudar_porta),
        (lambda: f"Conversões ao mesmo tempo ({c['midia_transmissoes']})", mudar_transmissoes),
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
    """Logs antigos, logs de serviços parados, fotos temporárias e legendas extraídas (refeitas quando preciso)."""
    ativos = set(servicos_ativos())
    itens = list(LOG_DIR.glob("*.log.old")) if LOG_DIR.exists() else []
    if LOG_DIR.exists():
        itens += [p for p in LOG_DIR.glob("*.log") if p.stem not in ativos]
    itens += list(DATA_DIR.glob("foto_*.jpg"))
    if (DATA_DIR / "teste_dev").exists():
        itens.append(DATA_DIR / "teste_dev")
    if LEGENDAS_CACHE.exists() and "midia" not in ativos:
        itens += list(LEGENDAS_CACHE.glob("*.vtt*"))
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
    ("Logs antigos, fotos temporárias e legendas extraídas do Termux-Toons", lambda: _limpador_lista(_sobras_toons), True),
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


def modo_cache_apps() -> str | None:
    """Como limpar o cache de todos os apps: 'root', 'adb' (depuração sem fio conectada) ou None."""
    if tem_root():
        return "root"
    if tem("adb") and adb_aparelhos():
        return "adb"
    return None


def limpar_cache_apps(modo: str) -> int:
    """Pede ao Android para limpar o cache de todos os apps (pm trim-caches). Precisa de root ou da
    permissão de 'shell' que a depuração sem fio dá. Devolve quantos bytes foram liberados."""
    antes = shutil.disk_usage(HOME).free
    if modo == "root":
        rodar(["su", "-c", "pm trim-caches 999G"])
    else:
        adb("shell", "pm trim-caches 999G", serial=adb_alvo(), timeout=600)
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
    modo = modo_cache_apps()
    if modo:
        origem = "root" if modo == "root" else "depuração sem fio"
        if not interativo or confirmar(f"Limpar também o cache de TODOS os apps ({origem})?", True):
            liberado = limpar_cache_apps(modo)
            total += liberado
            ok(f"Cache de todos os apps: {bytes_humanos(liberado)}")
    elif interativo:
        info("Para limpar o cache dos outros apps sem root, conecte a depuração sem fio (menu 🔌) e use "
             "'Limpar cache de TODOS os apps' neste menu.")
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
        modo = modo_cache_apps()
        if not modo:
            info("Sem root, dá para limpar pela depuração sem fio (ADB pelo Wi-Fi): o Termux se conecta ao "
                 "próprio celular e pede a limpeza com a permissão de 'shell'.")
            i = escolher("Como fazer?", [
                "Conectar pela depuração sem fio e limpar (precisa ter pareado uma vez no menu 🔌)",
                "Abrir a tela de armazenamento do Android e limpar por lá"])
            if i is None:
                return
            if i == 1:
                if not _abrir_tela_android("android.os.storage.action.MANAGE_STORAGE"):
                    _abrir_tela_android("android.settings.INTERNAL_STORAGE_SETTINGS")
                return
            info("Ligue a 'Depuração por Wi-Fi' nas Opções do desenvolvedor, se estiver desligada.")
            if not adb_conectar():
                info("Primeira vez? Use 'Depuração sem fio → Parear este celular' e volte aqui.")
                return
            modo = "adb"
        info("Pedindo ao Android para limpar o cache de todos os apps...")
        ok(f"Liberado: {bytes_humanos(limpar_cache_apps(modo))}")

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
        ("Limpar cache de TODOS os apps (root ou depuração sem fio)", cache_todos_apps),
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
#  17. Depuração sem fio (ADB pelo Wi-Fi) direto do Termux
# ════════════════════════════════════════════════════════════════════
# No Android 11+ a "Depuração por Wi-Fi" deixa o adb do próprio Termux se
# conectar ao celular, sem PC e sem root. Com isso dá para rodar comandos
# com permissão de "shell": impedir que o Android mate o Termux, liberar
# permissões, instalar APKs, gravar a tela, ler o logcat...

TELA_DEPURACAO = "android.settings.APPLICATION_DEVELOPMENT_SETTINGS"
DICA_TELA_DIVIDIDA = ("O Android fecha o código de pareamento se você sair da tela. Abra o Termux e as "
                      "Configurações em tela dividida (ou o Termux em janela flutuante) para ver os dois juntos.")


_ADB_OK = False


def _adb_funciona() -> str:
    """'' se o adb abre; senão a mensagem de erro dele."""
    proc = rodar(["adb", "version"], capturar=True, timeout=20, mostrar=False)
    texto = f"{proc.stdout or ''}{proc.stderr or ''}".strip()
    return "" if proc.returncode == 0 and "CANNOT LINK" not in texto else (texto or f"código {proc.returncode}")


def garantir_adb() -> bool:
    """adb instalado e abrindo. 'CANNOT LINK EXECUTABLE' quer dizer que o android-tools foi atualizado e as
    bibliotecas dele não (atualização pela metade): oferece atualizar o Termux e reinstalar o adb."""
    global _ADB_OK
    if _ADB_OK:
        return True
    if not garantir_cmd("adb", "android-tools"):
        return False
    problema = _adb_funciona()
    if problema:
        erro(f"O adb está instalado, mas não abre: {problema.splitlines()[0][:220]}")
        info("Isso acontece quando um pacote foi atualizado e as bibliotecas de que ele depende não "
             "(atualização pela metade). Resolve atualizando o Termux inteiro: pkg update && pkg upgrade")
        if not IS_TERMUX or not confirmar("Atualizar o Termux e reinstalar o adb agora?", True):
            return False
        rodar(["pkg", "update", "-y"])
        rodar(["pkg", "upgrade", "-y"])
        problema = _adb_funciona()
        if problema:
            rodar(["pkg", "install", "--reinstall", "-y", "android-tools", "abseil-cpp"])
            problema = _adb_funciona()
        if problema:
            erro(f"O adb continua sem abrir: {problema.splitlines()[0][:220]}")
            info("Tente trocar o espelho de pacotes (termux-change-repo) e rodar 'pkg upgrade' de novo.")
            return False
        ok("adb consertado.")
    _ADB_OK = True
    return True


def adb(*args: str, serial: str | None = None, timeout: float = 60) -> subprocess.CompletedProcess:
    """Roda o adb capturando a saída (`serial` escolhe o aparelho quando há mais de um)."""
    return rodar(["adb", *(["-s", serial] if serial else []), *args], capturar=True, timeout=timeout)


def adb_mdns() -> dict:
    """Endereços anunciados pela tela 'Depuração por Wi-Fi': {'pairing': [(ip, porta)], 'connect': [...]}."""
    achados = {"pairing": [], "connect": []}
    for tipo, ip, porta in re.findall(r"_adb-tls-(pairing|connect)\._tcp\.?\s+(\d+\.\d+\.\d+\.\d+):(\d+)",
                                      adb("mdns", "services", timeout=10).stdout or ""):
        achados[tipo].append((ip, int(porta)))
    return achados


def adb_aparelhos() -> list:
    """Seriais dos aparelhos conectados e prontos ('device' no adb devices)."""
    linhas = (adb("devices", timeout=15).stdout or "").splitlines()[1:]
    return [partes[0] for partes in (l.split() for l in linhas) if len(partes) >= 2 and partes[1] == "device"]


def adb_alvo() -> str:
    """O aparelho conectado (o último que o Termux-Toons conectou, se houver vários)."""
    if not garantir_adb():
        raise ToonsError("Sem o adb (pacote android-tools).")
    aparelhos = adb_aparelhos()
    if not aparelhos:
        raise ToonsError("Nenhum aparelho conectado. Use 'Conectar' (ou 'Parear', na primeira vez).")
    preferido = cfg().get("adb_endereco")
    return preferido if preferido in aparelhos else aparelhos[0]


def adb_shell(comando: str, serial: str | None = None, timeout: float = 60) -> str:
    proc = adb("shell", comando, serial=serial or adb_alvo(), timeout=timeout)
    return ((proc.stdout or "") + (proc.stderr or "")).strip()


def pedir_endereco_adb(msg: str) -> tuple:
    """(ip, porta) digitados como o Android mostra ('192.168.0.10:41235') ou só a porta ('41235')."""
    while True:
        texto = perguntar(msg).strip().replace(" ", "")
        m = re.fullmatch(r"(?:(\d{1,3}(?:\.\d{1,3}){3}|\[?[0-9a-fA-F:]+\]?)[:])?(\d{1,5})", texto)
        if m and 1 <= int(m.group(2)) <= 65535:
            return (m.group(1) or ip_local()).strip("[]"), int(m.group(2))
        erro("Digite o endereço como aparece no celular (ex.: 192.168.0.10:41235) ou só a porta (41235).")


def adb_conectar(endereco: str | None = None) -> bool:
    """Conecta o adb à Depuração por Wi-Fi (a porta muda toda vez que ela é ligada)."""
    if not garantir_adb():
        return False
    if not endereco:
        achados = adb_mdns()["connect"]
        if achados:
            ip, porta = achados[0]
            info(f"Depuração por Wi-Fi encontrada em {ip}:{porta}.")
        else:
            info("Na tela 'Depuração por Wi-Fi', veja 'Endereço IP e porta' (ex.: 192.168.0.10:41235).")
            ip, porta = pedir_endereco_adb("Endereço IP e porta (ex.: 192.168.0.10:41235) ou só a porta")
        endereco = f"[{ip}]:{porta}" if ":" in ip else f"{ip}:{porta}"
    saida_adb = adb("connect", endereco, timeout=30)
    texto = f"{saida_adb.stdout or ''}{saida_adb.stderr or ''}".strip()
    if re.search(r"\bconnected to", texto) and not re.search(r"fail|cannot|unable", texto, re.I):
        cfg()["adb_endereco"] = endereco
        salvar_cfg()
        ok(f"Conectado a {endereco}.")
        return True
    erro(f"Não conectou: {texto or 'sem resposta'}")
    info("Confira se a Depuração por Wi-Fi está ligada e se o celular já foi pareado ('Parear', uma vez só).")
    return False


@submenu
def menu_adb():
    c = cfg()

    def abrir_opcoes():
        info("Se as 'Opções do desenvolvedor' não aparecem: Configurações → Sobre o telefone → toque 7 vezes "
             "em 'Número da versão'.")
        _abrir_tela_android(TELA_DEPURACAO)

    def parear():
        if not garantir_adb():
            return
        info("1. Opções do desenvolvedor → Depuração por Wi-Fi → ligue (precisa estar num Wi-Fi).\n"
             "  2. Toque em 'Parear dispositivo com código de pareamento'.\n"
             "  3. Volte aqui e digite a porta e o código que aparecem lá. É preciso parear uma vez só.")
        info(DICA_TELA_DIVIDIDA)
        if confirmar("Abrir as Opções do desenvolvedor agora?", True):
            _abrir_tela_android(TELA_DEPURACAO)
        achados = adb_mdns()["pairing"]
        ip, porta = achados[0] if achados else (ip_local(), None)
        if achados:
            info(f"Tela de pareamento encontrada em {ip}:{porta}.")
        else:
            ip, porta = pedir_endereco_adb("Endereço IP e porta do pareamento (o que aparece junto do código)")
        codigo = perguntar("Código de pareamento (6 dígitos)").replace(" ", "")
        if not codigo:
            return
        proc = adb("pair", f"[{ip}]:{porta}" if ":" in ip else f"{ip}:{porta}", codigo, timeout=30)
        texto = f"{proc.stdout or ''}{proc.stderr or ''}".strip()
        if "Successfully paired" not in texto:
            raise ToonsError(f"O pareamento falhou: {texto or 'sem resposta'}. O código expira rápido: gere outro "
                             "e tente de novo.")
        ok("Pareado! Agora conectando...")
        adb_conectar()

    def status():
        if not garantir_adb():
            return
        print(adb("devices", "-l", timeout=15).stdout)
        if not adb_aparelhos():
            return
        serial = adb_alvo()
        dados = {"Aparelho": adb_shell("getprop ro.product.model", serial),
                 "Android": adb_shell("getprop ro.build.version.release", serial),
                 "SDK": adb_shell("getprop ro.build.version.sdk", serial)}
        mostrar_dados(dados)

    def shell():
        serial = adb_alvo()
        info("Shell do Android com permissão de 'shell' (exit para sair).")
        rodar(["adb", "-s", serial, "shell"])

    def comando():
        cmd = perguntar("Comando (ex.: pm list packages -3, dumpsys battery, wm size)")
        if cmd:
            print(adb_shell(cmd, timeout=120))

    def impedir_morte():
        serial = adb_alvo()
        sdk = int(adb_shell("getprop ro.build.version.sdk", serial) or 0)
        info("O Android 12+ encerra processos 'fantasmas' (filhos do Termux) quando passam de 32 — é o erro "
             "'Process completed (signal 9)'. Isso desliga esse limite.")
        if sdk < 31:
            ok("Este Android é anterior ao 12: não tem esse limite.")
            return
        comandos = ["device_config set_sync_disabled_for_tests persistent",
                    "device_config put activity_manager max_phantom_processes 2147483647",
                    "settings put global settings_enable_monitor_phantom_procs false"]
        for cmd in comandos:
            resposta = adb_shell(cmd, serial)
            print(f"  {DIM}$ {cmd}{RST}" + (f"\n  {resposta}" if resposta else ""))
        limite = adb_shell("device_config get activity_manager max_phantom_processes", serial)
        ok(f"Feito. Limite de processos fantasmas agora: {limite}. Vale até você desfazer (sobrevive a reinícios).")
        info("Desative também a otimização de bateria do Termux (Configurações → Apps → Termux → Bateria).")

    def desfazer_morte():
        serial = adb_alvo()
        for cmd in ("device_config set_sync_disabled_for_tests none",
                    "device_config delete activity_manager max_phantom_processes",
                    "settings put global settings_enable_monitor_phantom_procs true"):
            adb_shell(cmd, serial)
        ok("Comportamento padrão do Android restaurado.")

    def print_tela():
        destino = f"/sdcard/Download/tela_{datetime.now():%Y%m%d_%H%M%S}.png"
        print(adb_shell(f"screencap -p {destino}") or "")
        ok(f"Print salvo em {destino.replace('/sdcard/', 'Armazenamento interno/')}")

    def gravar_tela():
        segundos = perguntar_int("Duração em segundos (até 180)", 30, 1, 180)
        destino = f"/sdcard/Download/gravacao_{datetime.now():%Y%m%d_%H%M%S}.mp4"
        info("Gravando... (Ctrl+C para parar antes)")
        try:
            adb_shell(f"screenrecord --time-limit {segundos} {destino}", timeout=segundos + 30)
        except KeyboardInterrupt:
            time.sleep(1)
        ok(f"Vídeo salvo em {destino.replace('/sdcard/', 'Armazenamento interno/')}")

    def instalar_apk():
        serial = adb_alvo()
        apks = _mais_novos_primeiro(DOWNLOADS.glob("*.apk")) if DOWNLOADS.exists() else []
        i = escolher("Qual APK?", [p.name for p in apks] + ["📁 Digitar outro caminho..."])
        if i is None:
            return
        apk = apks[i] if i < len(apks) else Path(os.path.expanduser(perguntar("Caminho do APK")))
        if not apk.is_file():
            raise ToonsError(f"Arquivo não encontrado: {apk}")
        info(f"Instalando {apk.name}...")
        proc = adb("install", "-r", str(apk), serial=serial, timeout=600)
        texto = f"{proc.stdout or ''}{proc.stderr or ''}".strip()
        (ok if "Success" in texto else erro)(texto[-400:] or "sem resposta")

    def logcat():
        serial = adb_alvo()
        filtro = perguntar("Filtrar por texto (Enter = só erros)", "")
        args = ["logcat", "-d", "-t", "2000"] + ([] if filtro else ["*:E"])
        linhas = (adb(*args, serial=serial, timeout=60).stdout or "").splitlines()
        if filtro:
            linhas = [l for l in linhas if filtro.lower() in l.lower()]
        arquivo = DOWNLOADS / f"logcat_{datetime.now():%Y%m%d_%H%M%S}.txt"
        if garantir_storage():
            arquivo.write_text("\n".join(linhas), "utf-8")
        print("\n".join(linhas[-40:]) or "(nada encontrado)")
        if arquivo.exists():
            ok(f"{len(linhas)} linha(s) salvas em {arquivo}")

    def permissao():
        info("Exemplos: com.joaomgcd.taskerm android.permission.WRITE_SECURE_SETTINGS · "
             "com.termux android.permission.DUMP")
        pacote = perguntar("Pacote do app (ex.: com.termux)")
        perm = perguntar("Permissão", "android.permission.WRITE_SECURE_SETTINGS")
        if pacote and perm:
            resposta = adb_shell(f"pm grant {shlex.quote(pacote)} {shlex.quote(perm)}")
            (erro if resposta else ok)(resposta or f"Permissão concedida a {pacote}.")

    def porta_5555():
        serial = adb_alvo()
        aviso("Com isso, qualquer computador na mesma rede pode pedir para depurar o celular (o Android ainda "
              "pergunta antes de liberar um computador novo). Volta ao normal quando o celular reinicia.")
        if not confirmar("Abrir o ADB na porta 5555?", False):
            return
        print(adb("tcpip", "5555", serial=serial, timeout=30).stdout or "")
        time.sleep(2)
        endereco = f"{ip_local()}:5555"
        adb_conectar(endereco)
        info(f"No computador: adb connect {endereco}")

    def desconectar():
        if garantir_adb():
            print(adb("disconnect", timeout=15).stdout or "")
            ok("Desconectado.")

    def desligar_depuracao():
        adb_shell("settings put global adb_wifi_enabled 0")
        ok("Depuração por Wi-Fi desligada (para usar de novo: ligue nas Opções do desenvolvedor e use 'Conectar').")

    menu("🔌 Depuração sem fio (ADB pelo Wi-Fi)", [
        ("Abrir as Opções do desenvolvedor", abrir_opcoes),
        ("Parear este celular (primeira vez)", parear),
        (lambda: f"Conectar{' (' + c['adb_endereco'] + ')' if c.get('adb_endereco') else ''}", adb_conectar),
        ("Status: aparelhos conectados", status),
        ("Impedir que o Android mate o Termux (signal 9, Android 12+)", impedir_morte),
        ("Desfazer: limite padrão de processos", desfazer_morte),
        ("Shell do Android (adb shell)", shell),
        ("Rodar um comando", comando),
        ("Tirar print da tela", print_tela),
        ("Gravar a tela", gravar_tela),
        ("Instalar APK", instalar_apk),
        ("Logcat (erros ou filtro)", logcat),
        ("Conceder permissão a um app (pm grant)", permissao),
        ("Limpar o cache de todos os apps", lambda: ok(f"Liberado: {bytes_humanos(limpar_cache_apps('adb'))}")),
        ("Liberar ADB na porta 5555 para um computador", porta_5555),
        ("Desconectar", desconectar),
        ("Desligar a Depuração por Wi-Fi", desligar_depuracao),
        ("Instalar o adb (android-tools)", garantir_adb),
    ])


# ════════════════════════════════════════════════════════════════════
#  18. Gerenciador de arquivos (estilo ZArchiver)
# ════════════════════════════════════════════════════════════════════
# Navega, copia, move, renomeia, apaga, mostra os dados, compacta e
# extrai. Três níveis de acesso, do mais fraco ao mais forte:
#   • Termux: o armazenamento interno e a pasta do próprio Termux;
#   • ADB (depuração sem fio): o usuário "shell" do Android, que abre
#     Android/data e Android/obb (escondidas dos apps desde o Android 11),
#     /data/local/tmp e partes do sistema, sem root;
#   • Root: tudo, inclusive /data/data com os dados de cada app.

ARMAZENAMENTO = "/storage/emulated/0"
ICONES_ARQUIVO = [
    (EXTENSOES_VIDEO, "🎬"), (EXTENSOES_AUDIO, "🎵"),
    ({".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp", ".svg"}, "🖼"),
    ({".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".xz", ".bz2", ".zst"}, "📦"),
    ({".apk", ".apks", ".xapk"}, "📱"), ({".pdf"}, "📕"),
    ({".txt", ".md", ".json", ".xml", ".html", ".htm", ".py", ".sh", ".log", ".csv", ".srt", ".vtt", ".ini",
      ".conf", ".js", ".css", ".lua", ".c", ".rs", ".go"}, "📝"),
]
COMPACTADOS = (".zip", ".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".tbz2", ".7z", ".rar")


def _privado_do_termux(caminho: str) -> bool:
    """Pastas que só o Termux enxerga (a home dele): o ADB não lê nem grava ali."""
    return os.path.realpath(caminho).startswith(str(HOME.parent))


class AcessoTermux:
    """Arquivos com a permissão do próprio Termux (Python puro)."""
    nome, rotulo = "termux", "Termux (normal)"

    def listar(self, pasta: str) -> list:
        itens = []
        try:
            with os.scandir(pasta) as entradas:
                for e in entradas:
                    try:
                        st = e.stat()  # segue links: /sdcard e ~/storage/* abrem como pastas
                        eh_pasta = stat.S_ISDIR(st.st_mode)
                    except OSError:
                        st, eh_pasta = None, False
                    itens.append({"nome": e.name, "caminho": e.path, "pasta": eh_pasta,
                                  "tamanho": None if eh_pasta or st is None else st.st_size,
                                  "data": st.st_mtime if st else 0})
        except PermissionError:
            raise ToonsError("Sem permissão para abrir esta pasta com o acesso do Termux.") from None
        except OSError as e:
            raise ToonsError(f"Não consegui abrir a pasta: {e.strerror or e}") from None
        return itens

    def dados(self, caminho: str) -> dict:
        st = os.stat(caminho)
        dados = {"Tipo": "pasta" if stat.S_ISDIR(st.st_mode) else "arquivo",
                 "Tamanho": f"{bytes_humanos(st.st_size)} ({st.st_size:,} bytes)".replace(",", ".")
                 if not stat.S_ISDIR(st.st_mode) else "(use 'Calcular tamanho')",
                 "Modificado": f"{datetime.fromtimestamp(st.st_mtime):%d/%m/%Y %H:%M:%S}",
                 "Permissões": stat.filemode(st.st_mode), "Dono (uid:gid)": f"{st.st_uid}:{st.st_gid}"}
        if os.path.islink(caminho):
            dados["Link para"] = os.path.realpath(caminho)
        return dados

    def tamanho_total(self, caminho: str) -> int:
        return tamanho(Path(caminho))

    def existe(self, caminho: str) -> bool:
        return os.path.lexists(caminho)

    def copiar(self, origem: str, pasta: str, nome: str) -> None:
        destino = os.path.join(pasta, nome)
        if os.path.isdir(origem) and not os.path.islink(origem):
            shutil.copytree(origem, destino, symlinks=True)
        else:
            shutil.copy2(origem, destino)

    def mover(self, origem: str, pasta: str, nome: str) -> None:
        shutil.move(origem, os.path.join(pasta, nome))

    def renomear(self, caminho: str, novo: str) -> None:
        os.rename(caminho, os.path.join(os.path.dirname(caminho), novo))

    def apagar(self, caminho: str) -> None:
        if os.path.isdir(caminho) and not os.path.islink(caminho):
            shutil.rmtree(caminho)
        else:
            os.remove(caminho)

    def criar_pasta(self, caminho: str) -> None:
        os.makedirs(caminho)

    def ler(self, caminho: str, limite: int) -> bytes:
        with open(caminho, "rb") as arq:
            return arq.read(limite)

    def buscar(self, pasta: str, termo: str, limite: int = 200) -> list:
        padrao, achados = f"*{termo.lower()}*", []
        for raiz, pastas, nomes in os.walk(pasta, onerror=lambda e: None):
            for nome in pastas + nomes:
                if fnmatch.fnmatch(nome.lower(), padrao):
                    achados.append(os.path.join(raiz, nome))
                    if len(achados) >= limite:
                        return achados
        return achados


class AcessoShell(AcessoTermux):
    """Arquivos pelo shell do Android: via ADB (usuário 'shell', sem root) ou via su (root)."""

    def __init__(self, nome: str):
        self.nome = nome
        self.rotulo = "Root (vê tudo)" if nome == "root" else "ADB / depuração sem fio (Android/data, obb...)"
        self.serial = adb_alvo() if nome == "adb" else None

    def sh(self, comando: str, timeout: float | None = 120) -> subprocess.CompletedProcess:
        cmd = ["su", "-c", comando] if self.nome == "root" else ["adb", "-s", self.serial, "shell", comando]
        return rodar(cmd, capturar=True, timeout=timeout, mostrar=False)

    def _ok(self, comando: str, timeout: float | None = None) -> str:
        """Saída do comando; erro (com a mensagem do Android) se ele falhar."""
        proc = self.sh(comando, timeout)
        if proc.returncode != 0:
            texto = f"{proc.stderr or ''}{proc.stdout or ''}".strip()
            raise ToonsError(texto[-300:] or f"O comando falhou (código {proc.returncode}).")
        return (proc.stdout or "").strip()

    def listar(self, pasta: str) -> list:
        base = pasta.rstrip("/")
        q = shlex.quote(base) if base else ""
        globs = " ".join(f"{q}/{g}" for g in ("*", ".[!.]*", "..?*"))
        proc = self.sh(f"cd {shlex.quote(pasta)} && stat -L -c '%F|%s|%Y|%n' -- {globs} 2>/dev/null; "
                       f"[ -d {shlex.quote(pasta)} ] || echo NAO_EXISTE; [ -r {shlex.quote(pasta)} ] || echo SEM_PERMISSAO")
        saida_sh = proc.stdout or ""
        if "NAO_EXISTE" in saida_sh:
            raise ToonsError(f"A pasta não existe (ou não aparece com o acesso {self.rotulo}).")
        if "SEM_PERMISSAO" in saida_sh or (proc.returncode != 0 and not saida_sh.strip()
                                           and "Permission denied" in (proc.stderr or "")):
            raise ToonsError(f"Sem permissão para abrir esta pasta com o acesso {self.rotulo}.")
        itens = []
        for linha in saida_sh.splitlines():
            partes = linha.split("|", 3)
            if len(partes) != 4:
                continue
            tipo, tam, data, caminho = partes
            eh_pasta = tipo == "directory"
            itens.append({"nome": caminho.rsplit("/", 1)[-1], "caminho": caminho, "pasta": eh_pasta,
                          "tamanho": None if eh_pasta else int(tam or 0), "data": int(data or 0)})
        return itens

    def dados(self, caminho: str) -> dict:
        tipo, tam, data, perm, dono = (self._ok(
            f"stat -L -c '%F|%s|%Y|%A|%U:%G' -- {shlex.quote(caminho)}").splitlines()[-1].split("|") + [""] * 5)[:5]
        contexto = (self.sh(f"stat -L -c %C -- {shlex.quote(caminho)} 2>/dev/null").stdout or "").strip()
        dados = {"Tipo": "pasta" if tipo == "directory" else "arquivo",
                 "Tamanho": "(use 'Calcular tamanho')" if tipo == "directory"
                 else f"{bytes_humanos(int(tam or 0))} ({int(tam or 0):,} bytes)".replace(",", "."),
                 "Modificado": f"{datetime.fromtimestamp(int(data or 0)):%d/%m/%Y %H:%M:%S}",
                 "Permissões": perm, "Dono": dono}
        if contexto and contexto != "?":
            dados["Contexto SELinux"] = contexto
        return dados

    def tamanho_total(self, caminho: str) -> int:
        texto = self._ok(f"du -sk -- {shlex.quote(caminho)} 2>/dev/null | tail -n 1")
        return int(texto.split()[0]) * 1024 if texto.split() and texto.split()[0].isdigit() else 0

    def existe(self, caminho: str) -> bool:
        return "sim" in (self.sh(f"[ -e {shlex.quote(caminho)} ] && echo sim").stdout or "")

    def copiar(self, origem: str, pasta: str, nome: str) -> None:
        self._ok(f"cp -rp -- {shlex.quote(origem)} {shlex.quote(os.path.join(pasta, nome))}")

    def mover(self, origem: str, pasta: str, nome: str) -> None:
        self._ok(f"mv -- {shlex.quote(origem)} {shlex.quote(os.path.join(pasta, nome))}")

    def renomear(self, caminho: str, novo: str) -> None:
        self.mover(caminho, os.path.dirname(caminho), novo)

    def apagar(self, caminho: str) -> None:
        self._ok(f"rm -rf -- {shlex.quote(caminho)}")

    def criar_pasta(self, caminho: str) -> None:
        self._ok(f"mkdir -p -- {shlex.quote(caminho)}")

    def ler(self, caminho: str, limite: int) -> bytes:
        return self._ok(f"head -c {limite} -- {shlex.quote(caminho)}", timeout=60).encode("utf-8", "replace")

    def buscar(self, pasta: str, termo: str, limite: int = 200) -> list:
        padrao = shlex.quote(f"*{termo}*")
        saida_sh = self.sh(f"find {shlex.quote(pasta)} -iname {padrao} 2>/dev/null | head -n {limite}", 300).stdout
        return [l for l in (saida_sh or "").splitlines() if l.strip()]


def criar_acesso(nome: str):
    """Abre o nível de acesso pedido, conectando a depuração sem fio se precisar."""
    if nome == "termux":
        return AcessoTermux()
    if nome == "root":
        if not tem_root():
            raise ToonsError("Este celular não tem root (o comando su não respondeu).")
        return AcessoShell("root")
    if not garantir_adb():
        raise ToonsError("Sem o adb (pacote android-tools).")
    if not adb_aparelhos():
        info("A depuração sem fio não está conectada. Ligue a 'Depuração por Wi-Fi' nas Opções do desenvolvedor.")
        if not adb_conectar():
            raise ToonsError("Não conectou. Na primeira vez, use 'Depuração sem fio → Parear este celular'.")
    return AcessoShell("adb")


def _icone(item: dict) -> str:
    if item["pasta"]:
        return "📁"
    nome = item["nome"].lower()
    return next((icone for extensoes, icone in ICONES_ARQUIVO if os.path.splitext(nome)[1] in extensoes), "📄")


def _eh_compactado(nome: str) -> bool:
    return nome.lower().endswith(COMPACTADOS)


def _nome_livre(acesso, pasta: str, nome: str) -> str:
    """'foto.jpg' -> 'foto (2).jpg' se já existe na pasta."""
    base, ext = os.path.splitext(nome)
    if base.endswith(".tar"):
        base, ext = base[:-4], ".tar" + ext
    n = 2
    while acesso.existe(os.path.join(pasta, nome)):
        nome, n = f"{base} ({n}){ext}", n + 1
    return nome


def _resolver_conflito(acesso, pasta: str, nome: str):
    """Nome final para colar em `pasta`, ou None para pular. Pergunta se já existir."""
    if not acesso.existe(os.path.join(pasta, nome)):
        return nome
    i = escolher(f"'{nome}' já existe aqui. O que fazer?", ["Manter os dois (renomear o novo)", "Substituir", "Pular"])
    if i == 0:
        return _nome_livre(acesso, pasta, nome)
    if i == 1:
        acesso.apagar(os.path.join(pasta, nome))
        return nome
    return None


def transferir(origem, caminhos: list, destino, pasta: str, mover: bool) -> int:
    """Copia/move `caminhos` (lidos com o acesso `origem`) para `pasta` (com o acesso `destino`).
    Root alcança tudo; entre Termux e ADB, o que está na pasta privada do Termux passa por adb push/pull."""
    feitos = 0
    for caminho in caminhos:
        nome = os.path.basename(caminho.rstrip("/"))
        if os.path.realpath(pasta).startswith(os.path.realpath(caminho).rstrip("/") + "/") and origem.nome == destino.nome:
            erro(f"Não dá para colocar '{nome}' dentro dele mesmo.")
            continue
        try:
            if origem.nome == destino.nome or "root" in (origem.nome, destino.nome):
                acesso = destino if destino.nome == "root" or origem.nome == destino.nome else origem
                final = _resolver_conflito(acesso, pasta, nome)
                if final is None:
                    continue
                (acesso.mover if mover else acesso.copiar)(caminho, pasta, final)
                if acesso.nome == "root" and _privado_do_termux(pasta):  # devolve os arquivos ao Termux
                    acesso.sh(f"chown -R {os.getuid()}:{os.getgid()} -- {shlex.quote(os.path.join(pasta, final))}")
            else:
                adb_acesso = origem if origem.nome == "adb" else destino
                final = _resolver_conflito(destino, pasta, nome)
                if final is None:
                    continue
                alvo = os.path.join(pasta, final)
                if origem.nome == "termux" and _privado_do_termux(caminho):  # Termux privado -> ADB
                    proc = adb("push", caminho, alvo, serial=adb_acesso.serial, timeout=None)
                    if proc.returncode != 0:
                        raise ToonsError((proc.stderr or proc.stdout or "").strip()[-300:])
                    if mover:
                        origem.apagar(caminho)
                elif destino.nome == "termux" and _privado_do_termux(pasta):  # ADB -> Termux privado
                    proc = adb("pull", "-a", caminho, alvo, serial=adb_acesso.serial, timeout=None)
                    if proc.returncode != 0:
                        raise ToonsError((proc.stderr or proc.stdout or "").strip()[-300:])
                    if mover:
                        adb_acesso.apagar(caminho)
                else:  # os dois lados no armazenamento: o shell do ADB faz direto
                    (adb_acesso.mover if mover else adb_acesso.copiar)(os.path.realpath(caminho), os.path.realpath(pasta), final)
            feitos += 1
            ok(f"{'Movido' if mover else 'Copiado'}: {nome}" + (f" → {final}" if final != nome else ""))
        except (OSError, shutil.Error, ToonsError) as e:
            erro(f"{nome}: {e}")
    return feitos


def extrair(arquivo: str, pasta: str) -> str:
    """Extrai .zip/.tar.* com o Python e .7z/.rar com o 7z, numa pasta com o nome do arquivo."""
    nome = os.path.basename(arquivo)
    base = re.sub(r"\.(tar\.(gz|xz|bz2)|tgz|txz|tbz2|zip|tar|7z|rar)$", "", nome, flags=re.I) or nome
    destino = os.path.join(pasta, _nome_livre(AcessoTermux(), pasta, base))
    baixo = nome.lower()
    if baixo.endswith(".zip"):
        with zipfile.ZipFile(arquivo) as z:
            raiz = os.path.realpath(destino)
            for membro in z.namelist():  # nada de '../' saindo da pasta
                if not os.path.realpath(os.path.join(raiz, membro)).startswith(raiz + os.sep) and membro.strip("/"):
                    raise ToonsError(f"Arquivo suspeito dentro do zip: {membro}")
            z.extractall(destino)
    elif baixo.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".tbz2")):
        with tarfile.open(arquivo) as t:
            if hasattr(tarfile, "data_filter"):
                t.extractall(destino, filter="data")
            else:
                raiz = os.path.realpath(destino)
                if any(not os.path.realpath(os.path.join(raiz, m.name)).startswith(raiz) or m.issym() or m.islnk()
                       for m in t.getmembers()):
                    raise ToonsError("O arquivo tem caminhos ou links suspeitos; não extraí.")
                t.extractall(destino)
    else:
        if not garantir_cmd("7z", "p7zip"):
            raise ToonsError("Para .7z e .rar é preciso o 7z (pkg install p7zip).")
        if rodar(["7z", "x", f"-o{destino}", "-y", arquivo]).returncode != 0:
            raise ToonsError("O 7z não conseguiu extrair (senha errada ou arquivo corrompido?).")
    return destino


def compactar(caminhos: list, destino: str) -> None:
    """Junta arquivos e pastas num .zip."""
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for caminho in caminhos:
            pai = os.path.dirname(caminho.rstrip("/"))
            if os.path.isdir(caminho):
                for raiz, _, nomes in os.walk(caminho):
                    z.write(raiz, os.path.relpath(raiz, pai))
                    for nome in nomes:
                        completo = os.path.join(raiz, nome)
                        z.write(completo, os.path.relpath(completo, pai))
            else:
                z.write(caminho, os.path.relpath(caminho, pai))


def _atalhos_de_pasta(acesso) -> list:
    """[(rótulo, caminho)] para 'Ir para...'."""
    atalhos = [("📱 Armazenamento interno", ARMAZENAMENTO)]
    atalhos += [(f"   {nome}", f"{ARMAZENAMENTO}/{nome}") for nome in
                ("Download", "DCIM", "Pictures", "Movies", "Music", "Documents", "WhatsApp/Media", "Android/media")]
    atalhos += [("🔒 Android/data (ADB ou root)", f"{ARMAZENAMENTO}/Android/data"),
                ("🔒 Android/obb (ADB ou root)", f"{ARMAZENAMENTO}/Android/obb")]
    with contextlib.suppress(OSError):
        for nome in sorted(os.listdir("/storage")):
            if nome not in ("emulated", "self") and re.fullmatch(r"[0-9A-F]{4}-[0-9A-F]{4}", nome):
                atalhos.append((f"💾 Cartão SD / pendrive ({nome})", f"/storage/{nome}"))
    atalhos += [("🐧 Home do Termux", str(HOME)), ("⚙ Raiz do sistema (/)", "/"),
                ("🔒 /data/local/tmp (ADB)", "/data/local/tmp"), ("🔒 /data/data — dados dos apps (root)", "/data/data")]
    return atalhos


@submenu
def gerenciador_arquivos(inicio: str | None = None) -> None:
    """Navegador de arquivos com setas: Enter abre pasta ou mostra as ações do arquivo; Esc sobe uma pasta."""
    acesso = AcessoTermux()
    if inicio is None:
        garantir_storage()
        inicio = ARMAZENAMENTO if os.path.isdir(ARMAZENAMENTO) else str(HOME)
    pasta = os.path.abspath(os.path.expanduser(inicio))
    estado = {"ocultos": False, "ordem": "nome", "clip": None,  # clip: (acesso, [caminhos], mover?)
              "oferecido": None}  # pasta protegida em que já oferecemos trocar o acesso
    ordens = {"nome": "nome", "data": "data (mais novos)", "tamanho": "tamanho (maiores)"}

    def colar():
        origem, caminhos, mover = estado["clip"]
        feitos = transferir(origem, caminhos, acesso, pasta, mover)
        if mover and feitos:
            estado["clip"] = None
        pausar()

    def acoes_item(item: dict):
        caminho, nome = item["caminho"], item["nome"]
        opcoes = [("📋 Ver dados (tamanho, data, permissões...)", "dados"), ("📂 Abrir com um app", "abrir"),
                  ("👁 Ver conteúdo (texto)", "ver"), ("✏ Renomear", "renomear"), ("📄 Copiar", "copiar"),
                  ("✂ Recortar (mover)", "mover"), ("⬇ Copiar para Download", "download")]
        if acesso.nome == "termux":
            if _eh_compactado(nome):
                opcoes.append(("📦 Extrair aqui", "extrair"))
            opcoes += [("🗜 Compactar em .zip", "zip"), ("📝 Editar texto (nano)", "editar"),
                       ("📤 Compartilhar (WhatsApp, Telegram...)", "enviar")]
        opcoes += [("🗑 Apagar", "apagar")]
        i = escolher(f"{_icone(item)} {nome}", [r for r, _ in opcoes])
        if i is None:
            return
        acao = opcoes[i][1]
        if acao == "dados":
            mostrar_dados({"Nome": nome, "Caminho": caminho, **acesso.dados(caminho)})
            if item["pasta"] and confirmar("Calcular o tamanho da pasta?", False):
                info("Somando...")
                print(f"Tamanho total: {bytes_humanos(acesso.tamanho_total(caminho))}")
        elif acao == "abrir":
            if acesso.nome != "termux" and not os.access(caminho, os.R_OK):
                aviso("O Termux não enxerga este arquivo direto. Use 'Copiar para Download' e abra de lá.")
            elif not tem("termux-open"):
                raise ToonsError("'termux-open' não encontrado (só existe dentro do Termux).")
            else:
                rodar(["termux-open", "--chooser", caminho], capturar=True, timeout=20)
        elif acao == "ver":
            dados = acesso.ler(caminho, 6000)
            if b"\0" in dados[:2000]:
                aviso("Parece um arquivo binário (não é texto).")
            else:
                print(dados.decode("utf-8", "replace"))
                if len(dados) >= 6000:
                    print(f"{DIM}… (mostrando só o começo){RST}")
        elif acao == "renomear":
            novo = perguntar("Novo nome", nome).strip()
            if novo and novo != nome:
                if "/" in novo:
                    raise ToonsError("O nome não pode ter '/'.")
                if acesso.existe(os.path.join(os.path.dirname(caminho), novo)):
                    raise ToonsError(f"Já existe '{novo}' nesta pasta.")
                acesso.renomear(caminho, novo)
                ok(f"Renomeado para {novo}")
        elif acao in ("copiar", "mover"):
            estado["clip"] = (acesso, [caminho], acao == "mover")
            ok(f"{'Recortado' if acao == 'mover' else 'Copiado'}. Vá até a pasta de destino e use ⚙ → Colar aqui.")
        elif acao == "download":
            transferir(acesso, [caminho], AcessoTermux() if acesso.nome == "termux" else acesso,
                       f"{ARMAZENAMENTO}/Download", False)
        elif acao == "extrair":
            info("Extraindo...")
            ok(f"Extraído em {extrair(caminho, pasta)}")
        elif acao == "zip":
            destino = os.path.join(pasta, _nome_livre(acesso, pasta, os.path.splitext(nome)[0] + ".zip"))
            compactar([caminho], destino)
            ok(f"Criado {os.path.basename(destino)}")
        elif acao == "editar":
            editor = os.environ.get("EDITOR") or next((e for e in ("nano", "nvim", "vi") if tem(e)), None)
            if not editor:
                raise ToonsError("Nenhum editor encontrado (pkg install nano).")
            rodar([editor, caminho])
            return
        elif acao == "enviar":
            if not tem("termux-share"):
                raise ToonsError("Precisa do Termux:API (pkg install termux-api).")
            rodar(["termux-share", "-a", "send", caminho], capturar=True, timeout=30)
        elif acao == "apagar":
            tipo = "a pasta e TUDO dentro dela" if item["pasta"] else "o arquivo"
            if confirmar(f"Apagar {tipo} '{nome}'? Não dá para desfazer.", False):
                acesso.apagar(caminho)
                ok("Apagado.")
        pausar()

    def acoes_varios(itens: list):
        sel = escolher_varios("Marque os itens (Espaço marca, a = todos)",
                              [f"{_icone(it)} {it['nome']}" for it in itens])
        if not sel:
            return
        escolhidos = [itens[i] for i in sel]
        caminhos = [it["caminho"] for it in escolhidos]
        opcoes = ["📄 Copiar", "✂ Recortar (mover)", "🗑 Apagar", "📋 Tamanho total"]
        if len(escolhidos) == 1:
            opcoes += ["✏ Renomear", "📋 Ver dados"]
        if acesso.nome == "termux":
            opcoes.append("🗜 Compactar em .zip")
        i = escolher(f"{len(escolhidos)} item(ns) marcado(s)", opcoes)
        if i is None:
            return
        acao = opcoes[i]
        if "Copiar" in acao or "Recortar" in acao:
            estado["clip"] = (acesso, caminhos, "Recortar" in acao)
            ok("Pronto. Vá até a pasta de destino e use ⚙ → Colar aqui.")
        elif "Apagar" in acao:
            if confirmar(f"Apagar {len(caminhos)} item(ns), com tudo o que tiver dentro? Não dá para desfazer.", False):
                for c in caminhos:
                    try:
                        acesso.apagar(c)
                        ok(f"Apagado: {os.path.basename(c)}")
                    except (OSError, ToonsError) as e:
                        erro(f"{os.path.basename(c)}: {e}")
        elif "Tamanho" in acao:
            info("Somando...")
            print(f"Tamanho total: {bytes_humanos(sum(acesso.tamanho_total(c) for c in caminhos))}")
        elif "Renomear" in acao or "Ver dados" in acao:
            return acoes_item(escolhidos[0])
        elif "Compactar" in acao:
            nome_zip = perguntar("Nome do .zip", (escolhidos[0]["nome"] if len(escolhidos) == 1 else "arquivos") + ".zip")
            destino = os.path.join(pasta, _nome_livre(acesso, pasta, nome_zip if nome_zip.endswith(".zip") else nome_zip + ".zip"))
            info("Compactando...")
            compactar(caminhos, destino)
            ok(f"Criado {os.path.basename(destino)} ({bytes_humanos(os.path.getsize(destino))})")
        pausar()

    def acoes_pasta(itens: list):
        nonlocal pasta, acesso
        clip = estado["clip"]
        opcoes = []
        if clip:
            opcoes.append((f"📋 Colar aqui ({len(clip[1])} item(ns), {'mover' if clip[2] else 'copiar'})", "colar"))
        opcoes += [("☑ Marcar itens (copiar, mover, apagar, renomear pastas...)", "marcar"),
                   ("➕ Nova pasta", "nova"), ("🧭 Ir para... (Download, Android/data, cartão SD, raiz...)", "ir"),
                   ("🔎 Buscar por nome a partir daqui", "buscar"),
                   (f"🔑 Nível de acesso: {acesso.rotulo}", "acesso"),
                   (f"👁 Arquivos ocultos: {'mostrando' if estado['ocultos'] else 'escondidos'}", "ocultos"),
                   (f"↕ Ordenar por: {ordens[estado['ordem']]}", "ordem"), ("📋 Dados desta pasta", "dados")]
        if clip:
            opcoes.append(("✖ Esvaziar a área de transferência", "limpar"))
        i = escolher("Ações nesta pasta", [r for r, _ in opcoes])
        if i is None:
            return
        acao = opcoes[i][1]
        if acao == "colar":
            colar()
        elif acao == "marcar":
            if itens:
                acoes_varios(itens)
            else:
                info("Pasta vazia.")
                pausar()
        elif acao == "nova":
            nome = perguntar("Nome da nova pasta").strip()
            if nome:
                acesso.criar_pasta(os.path.join(pasta, nome))
                ok(f"Pasta '{nome}' criada.")
        elif acao == "ir":
            atalhos = _atalhos_de_pasta(acesso)
            j = escolher("Ir para", [r for r, _ in atalhos] + ["⌨ Digitar um caminho"])
            if j is not None:
                pasta = atalhos[j][1] if j < len(atalhos) else os.path.expanduser(perguntar("Caminho", pasta))
        elif acao == "buscar":
            termo = perguntar("Parte do nome (ex.: .apk, foto, relatorio)").strip()
            if termo:
                info("Buscando...")
                achados = acesso.buscar(pasta, termo)
                if not achados:
                    info("Nada encontrado.")
                    pausar()
                    return
                j = escolher(f"{len(achados)} resultado(s)", [a.replace(pasta.rstrip('/') + "/", "", 1) for a in achados])
                if j is not None:
                    pasta = os.path.dirname(achados[j].rstrip("/")) or "/"
        elif acao == "acesso":
            niveis = [("Termux (normal)", "termux"),
                      ("ADB / depuração sem fio — abre Android/data, Android/obb e mais, sem root", "adb"),
                      ("Root — tudo, inclusive os dados dos apps", "root")]
            j = escolher("Nível de acesso", [r for r, _ in niveis])
            if j is not None:
                try:
                    acesso = criar_acesso(niveis[j][1])
                    ok(f"Acesso: {acesso.rotulo}")
                except ToonsError as e:
                    erro(str(e))
                pausar()
        elif acao == "ocultos":
            estado["ocultos"] = not estado["ocultos"]
        elif acao == "ordem":
            chaves = list(ordens)
            estado["ordem"] = chaves[(chaves.index(estado["ordem"]) + 1) % len(chaves)]
        elif acao == "dados":
            mostrar_dados({"Caminho": pasta, "Itens": len(itens), **acesso.dados(pasta)})
            if confirmar("Calcular o tamanho total?", False):
                print(f"Tamanho total: {bytes_humanos(acesso.tamanho_total(pasta))}")
            pausar()
        elif acao == "limpar":
            estado["clip"] = None

    while True:
        limpar()
        try:
            itens, problema = acesso.listar(pasta), ""
        except ToonsError as e:
            itens, problema = [], str(e)
        # No Android 11+ o Termux vê Android/data e Android/obb vazias (ou só com a pasta dele), sem erro:
        # oferece abrir com o acesso ADB (ou root), que enxerga as pastas dos outros apps.
        protegida = re.search(r"/Android/(data|obb)/?$", pasta) or problema
        if acesso.nome == "termux" and protegida and estado["oferecido"] != pasta:
            estado["oferecido"] = pasta
            print(f"{NEG}📂 {pasta}{RST}")
            aviso(problema or "No Android 11+ o acesso normal do Termux vê esta pasta vazia (só com a pasta do "
                  "próprio Termux): os arquivos dos outros apps ficam escondidos.")
            niveis = (["root"] if tem_root() else []) + ["adb"]
            rotulos = {"root": "Abrir com root", "adb": "Abrir com o acesso ADB (depuração sem fio, sem root)"}
            j = escolher("Como abrir?", [rotulos[n] for n in niveis] + ["Continuar com o acesso normal"])
            if j is not None and j < len(niveis):
                try:
                    acesso = criar_acesso(niveis[j])
                    ok(f"Acesso: {acesso.rotulo}")
                    continue
                except ToonsError as e:
                    erro(str(e))
                    pausar()
            limpar()
        if not estado["ocultos"]:
            itens = [it for it in itens if not it["nome"].startswith(".")]
        chave = {"nome": lambda it: it["nome"].lower(), "data": lambda it: -it["data"],
                 "tamanho": lambda it: -(it["tamanho"] or 0)}[estado["ordem"]]
        itens.sort(key=lambda it: (not it["pasta"], chave(it)))
        clip = estado["clip"]
        print(f"{NEG}📂 {pasta}{RST}")
        print(f"{DIM}🔑 {acesso.rotulo} · {len(itens)} item(ns)"
              + (f" · 📋 {len(clip[1])} para {'mover' if clip[2] else 'copiar'}" if clip else "") + RST)
        if problema:
            aviso(problema)
            if acesso.nome == "termux":
                info("Pastas como Android/data precisam do acesso ADB (depuração sem fio) ou root: ⚙ → Nível de acesso.")
        linhas = ["✖ Sair do gerenciador", "⚙ Ações nesta pasta (colar, marcar, nova pasta, ir para, acesso...)",
                  "⬆ .. (pasta de cima)"]
        for it in itens:
            if it["pasta"]:
                linhas.append(f"📁 {it['nome']}/")
            else:
                data = f"{datetime.fromtimestamp(it['data']):%d/%m/%y %H:%M}" if it["data"] else ""
                linhas.append(f"{_icone(it)} {it['nome']}  {DIM}{bytes_humanos(it['tamanho'] or 0)} · {data}{RST}")
        i = escolher("Enter abre · Esc sobe uma pasta", linhas, "4" if itens else "2")
        if i == 0:
            return
        if i is None or i == 2:
            if pasta == "/":
                if i is None:
                    return
                continue
            pasta = os.path.dirname(pasta.rstrip("/")) or "/"
            continue
        try:
            if i == 1:
                acoes_pasta(itens)
                continue
            item = itens[i - 3]
            if item["pasta"]:
                pasta = item["caminho"]
            else:
                acoes_item(item)
        except (OSError, shutil.Error, zipfile.BadZipFile, tarfile.TarError, ToonsError) as e:
            erro(str(e) if isinstance(e, ToonsError) else f"Falhou: {e}")
            pausar()


# ════════════════════════════════════════════════════════════════════
#  19. Calculadora científica
# ════════════════════════════════════════════════════════════════════
# A expressão é lida com `ast` e só aceita números, contas, constantes e as
# funções da lista abaixo: nunca passa por eval(), então nada digitado roda
# como código. Há travas contra contas que travariam o celular (2**9**9...).

CALC_MAX_BITS = 14000      # ~4200 dígitos; abaixo do limite de int→texto do Python
CALC_MAX_FATORIAL = 1000
CALC_RESERVADOS = ("ans", "pi", "e", "tau", "inf", "mod")


def _calc_int(x, nome: str) -> int:
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    if not isinstance(x, int):
        raise ToonsError(f"{nome} só aceita números inteiros.")
    return x


def _calc_verificar(v):
    """Barra resultados enormes, infinitos ou complexos."""
    if isinstance(v, complex):
        raise ToonsError("Resultado complexo (raiz/potência fracionária de número negativo).")
    if isinstance(v, int):
        if v.bit_length() > CALC_MAX_BITS:
            raise ToonsError("Número grande demais.")
    elif math.isnan(v) or math.isinf(v):
        raise ToonsError("Resultado indefinido ou infinito.")
    return v


def _calc_pot(a, b):
    if isinstance(a, int) and isinstance(b, int) and abs(a) > 1 and b > 0 \
            and b * math.log2(abs(a)) > CALC_MAX_BITS:
        raise ToonsError("Potência grande demais.")
    return _calc_verificar(operator.pow(a, b))


def _calc_div(a, b):
    if b == 0:
        raise ToonsError("Divisão por zero.")
    return operator.truediv(a, b)


def _calc_fatorial(n):
    n = _calc_int(n, "Fatorial")
    if not 0 <= n <= CALC_MAX_FATORIAL:
        raise ToonsError(f"Fatorial vale de 0 a {CALC_MAX_FATORIAL}.")
    return math.factorial(n)


def _calc_funcoes(graus: bool) -> dict:
    """Funções disponíveis; as trigonométricas seguem o modo graus/radianos."""
    a_rad = math.radians if graus else (lambda x: x)
    de_rad = math.degrees if graus else (lambda x: x)

    def sen(x):
        return 0 if graus and x % 180 == 0 else math.sin(a_rad(x))

    def cos(x):
        return 0 if graus and (x - 90) % 180 == 0 else math.cos(a_rad(x))

    def tan(x):
        if graus and (x - 90) % 180 == 0:
            raise ToonsError("A tangente não existe nesse ângulo.")
        return 0 if graus and x % 180 == 0 else math.tan(a_rad(x))

    def log(x, base=10):
        return math.log(x, base)

    def raiz(x, n=2):
        n = _calc_int(n, "raiz")
        if n == 0:
            raise ToonsError("Raiz de índice zero não existe.")
        if x < 0 and n % 2:  # raiz ímpar de negativo é real: raiz(-27, 3) = -3
            return -(abs(x) ** (1 / n))
        if x < 0:
            raise ToonsError("Raiz par de número negativo não é real.")
        r = x ** (1 / n)
        return round(r) if round(r) ** n == x else r  # raiz(8, 3) dá 2, não 2.0000000000000004

    def inversa(f, nome):
        def g(x):
            v = f(x)
            if v == 0:
                raise ToonsError(f"{nome} não existe nesse ângulo.")
            return 1 / v
        return g

    def lista(f, minimo=1):
        def g(*v):
            if len(v) < minimo:
                raise ToonsError(f"Informe pelo menos {minimo} número(s), separados por vírgula.")
            return f(v)
        return g

    def aleatorio(a=None, b=None):
        if a is None:
            return random.random()
        if b is None:
            a, b = 1, a
        return random.randint(_calc_int(a, "aleatorio"), _calc_int(b, "aleatorio"))

    def arredondar(x, casas=0):
        return round(x, _calc_int(casas, "round"))

    funcs = {
        "sin": sen, "sen": sen, "cos": cos, "tan": tan,
        "asin": lambda x: de_rad(math.asin(x)), "asen": lambda x: de_rad(math.asin(x)),
        "acos": lambda x: de_rad(math.acos(x)), "atan": lambda x: de_rad(math.atan(x)),
        "sec": inversa(cos, "Secante"), "csc": inversa(sen, "Cossecante"),
        "cossec": inversa(sen, "Cossecante"), "cot": inversa(tan, "Cotangente"),
        "cotg": inversa(tan, "Cotangente"),
        "sinh": math.sinh, "senh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
        "asinh": math.asinh, "asenh": math.asinh, "acosh": math.acosh, "atanh": math.atanh,
        "sqrt": math.sqrt, "raiz": raiz, "cbrt": lambda x: raiz(x, 3),
        "ln": math.log, "log": log, "log10": math.log10, "log2": math.log2, "exp": math.exp,
        "abs": abs, "floor": math.floor, "ceil": math.ceil, "round": arredondar,
        "fat": _calc_fatorial, "fact": _calc_fatorial, "factorial": _calc_fatorial,
        "gcd": lambda a, b: math.gcd(_calc_int(a, "gcd"), _calc_int(b, "gcd")),
        "mdc": lambda a, b: math.gcd(_calc_int(a, "mdc"), _calc_int(b, "mdc")),
        "lcm": lambda a, b: math.lcm(_calc_int(a, "lcm"), _calc_int(b, "lcm")),
        "mmc": lambda a, b: math.lcm(_calc_int(a, "mmc"), _calc_int(b, "mmc")),
        "comb": lambda n, k: math.comb(_calc_int(n, "comb"), _calc_int(k, "comb")),
        "perm": lambda n, k: math.perm(_calc_int(n, "perm"), _calc_int(k, "perm")),
        "graus": math.degrees, "radianos": math.radians,
        "min": lista(min), "max": lista(max), "soma": lista(sum),
        "media": lista(statistics.fmean), "mediana": lista(statistics.median),
        "desvio": lista(statistics.stdev, 2),
        "aleatorio": aleatorio, "rand": aleatorio,
        "_pct": lambda x: x / 100,  # 'x%' (porcentagem) vira _pct(x)
    }
    return funcs


_CALC_BINARIOS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: _calc_div, ast.Pow: _calc_pot,
    ast.FloorDiv: lambda a, b: operator.floordiv(a, b) if b else _calc_div(a, b),
    ast.Mod: lambda a, b: operator.mod(a, b) if b else _calc_div(a, b),
}


_CALC_TOKEN = re.compile(
    r"\s*(?:(0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|(?:\d[\d_]*\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
    r"|([A-Za-z_]\w*)|(\*\*|//|[-+*/%^(),!√]))")


def _calc_preparar(texto: str, funcoes: dict) -> str:
    """Reescreve o jeito de digitar de calculadora em sintaxe que o `ast` entende:
    5! → fat(5), 10% → _pct(10), √9 → sqrt(9), 'mod' → %, ^ → **, 2pi → 2*pi, 3(4+5) → 3*(4+5)."""
    tokens, pos = [], 0
    texto = texto.rstrip()
    while pos < len(texto):
        m = _CALC_TOKEN.match(texto, pos)
        if not m:
            raise ToonsError(f"Caractere inválido: '{texto[pos:].strip()[0]}'.")
        pos = m.end()
        if m.group(1):
            tokens.append(("num", m.group(1)))
        elif m.group(2):
            tokens.append(("op", "%") if m.group(2) == "mod" else ("nome", m.group(2)))
        else:
            tokens.append(("op", "**" if m.group(3) == "^" else m.group(3)))

    # √ vale para o que vem logo depois: um número, um nome, (grupo) ou função(...)
    while ("op", "√") in tokens:
        i = len(tokens) - 1 - tokens[::-1].index(("op", "√"))  # de trás para frente: √√16
        fim = i + 1
        if fim < len(tokens) and tokens[fim][0] == "nome" and tokens[fim][1] in funcoes:
            fim += 1
        if fim < len(tokens) and tokens[fim] == ("op", "("):
            nivel = 0
            for fim in range(fim, len(tokens)):
                nivel += {("op", "("): 1, ("op", ")"): -1}.get(tokens[fim], 0)
                if nivel == 0:
                    break
            else:
                raise ToonsError("Parênteses não fecham.")
        elif fim >= len(tokens) or tokens[fim][0] not in ("num", "nome"):
            raise ToonsError("'√' precisa de um número depois.")
        tokens[i:fim + 1] = [("nome", "sqrt"), ("op", "(")] + tokens[i + 1:fim + 1] + [("op", ")")]

    def inicio_operando(saida, simbolo):
        """Índice onde começa o número, nome ou (grupo) logo antes de '!' ou '%'."""
        if not saida:
            raise ToonsError(f"'{simbolo}' precisa de um número antes.")
        if saida[-1] == ("op", ")"):
            nivel = 0
            for i in range(len(saida) - 1, -1, -1):
                nivel += {("op", ")"): 1, ("op", "("): -1}.get(saida[i], 0)
                if nivel == 0:
                    # inclui o nome da função: sqrt(4)! → fat(sqrt(4))
                    return i - 1 if i and saida[i - 1][0] == "nome" and saida[i - 1][1] in funcoes else i
            raise ToonsError("Parênteses não fecham.")
        if saida[-1][0] in ("num", "nome"):
            return len(saida) - 1
        raise ToonsError(f"'{simbolo}' precisa de um número antes.")

    saida = []
    for i, tok in enumerate(tokens):
        seguinte = tokens[i + 1] if i + 1 < len(tokens) else None
        # '%' no fim ou antes de outro operador é porcentagem; antes de um número é resto (mod)
        porcentagem = tok == ("op", "%") and (seguinte is None or (seguinte[0] == "op" and seguinte[1] != "("))
        if tok == ("op", "!") or porcentagem:
            j = inicio_operando(saida, tok[1])
            nome = "fat" if tok[1] == "!" else "_pct"
            saida[j:] = [("nome", nome), ("op", "(")] + saida[j:] + [("op", ")")]
            continue
        if saida:
            antes = saida[-1]
            # multiplicação implícita: 2pi, 2x, 2(3+4), (1+2)(3+4), 2sin(30), x(2)
            if ((antes[0] == "num" or antes == ("op", ")") or (antes[0] == "nome" and antes[1] not in funcoes))
                    and (tok[0] == "nome" or tok == ("op", "("))):
                saida.append(("op", "*"))
            elif antes == ("op", ")") and tok[0] == "num":
                saida.append(("op", "*"))
        saida.append(tok)
    return " ".join(valor for _, valor in saida)


def calc_avaliar(texto: str, variaveis: dict | None = None, graus: bool = True):
    """Calcula uma expressão e devolve int ou float. Erros viram ToonsError."""
    variaveis = variaveis or {}
    constantes = {"pi": math.pi, "e": math.e, "tau": math.tau, "inf": math.inf, **variaveis}
    funcoes = _calc_funcoes(graus)
    texto = (texto.strip().replace("×", "*").replace("÷", "/").replace("π", "pi")
             .replace("−", "-"))
    if not texto:
        raise ToonsError("Digite uma conta.")
    if len(texto) > 500:
        raise ToonsError("Expressão longa demais.")
    texto = _calc_preparar(texto, funcoes)

    def calc(no):
        if isinstance(no, ast.Expression):
            return calc(no.body)
        if isinstance(no, ast.Constant) and type(no.value) in (int, float):
            return _calc_verificar(no.value)
        if isinstance(no, ast.Name):
            if no.id in constantes:
                return constantes[no.id]
            raise ToonsError(f"'{no.id}' não existe. Digite 'ajuda' para ver as funções.")
        if isinstance(no, ast.UnaryOp) and isinstance(no.op, (ast.USub, ast.UAdd)):
            valor = calc(no.operand)
            return -valor if isinstance(no.op, ast.USub) else valor
        if isinstance(no, ast.Tuple):
            raise ToonsError("Use ponto para decimais (3.5); a vírgula separa argumentos, como em log(8, 2).")
        # porcentagem como no celular: 200 + 10% = 220, 200 - 10% = 180
        if (isinstance(no, ast.BinOp) and isinstance(no.op, (ast.Add, ast.Sub))
                and isinstance(no.right, ast.Call) and isinstance(no.right.func, ast.Name)
                and no.right.func.id == "_pct" and len(no.right.args) == 1):
            base = calc(no.left)
            parte = base * calc(no.right.args[0]) / 100
            return _calc_verificar(base + parte if isinstance(no.op, ast.Add) else base - parte)
        if isinstance(no, ast.BinOp) and type(no.op) in _CALC_BINARIOS:
            return _calc_verificar(_CALC_BINARIOS[type(no.op)](calc(no.left), calc(no.right)))
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and not no.keywords:
            if no.func.id not in funcoes:
                raise ToonsError(f"Função '{no.func.id}' não existe. Digite 'ajuda'.")
            try:
                return _calc_verificar(funcoes[no.func.id](*[calc(a) for a in no.args]))
            except TypeError:
                raise ToonsError(f"Quantidade de argumentos errada em {no.func.id}(). Digite 'ajuda'.") from None
        raise ToonsError("Não entendi essa expressão (use * entre números, ex.: 2*pi, 3*(4+5)).")

    try:
        return calc(ast.parse(texto, mode="eval"))
    except SyntaxError:
        raise ToonsError("Expressão inválida (confira parênteses e operadores).") from None
    except ZeroDivisionError:
        raise ToonsError("Divisão por zero.") from None
    except ValueError as e:
        motivo = "fora do domínio da função" if "domain" in str(e) else str(e)
        if isinstance(e, statistics.StatisticsError):
            motivo = "faltam números para essa estatística"
        raise ToonsError(f"Conta impossível ({motivo}).") from None
    except OverflowError:
        raise ToonsError("Resultado grande demais.") from None
    except RecursionError:
        raise ToonsError("Expressão aninhada demais.") from None


def calc_formatar(v) -> str:
    """Número para mostrar: inteiros exatos, decimais com até 12 algarismos."""
    if isinstance(v, int):
        digitos = str(abs(v))
        if len(digitos) <= 30:
            return str(v)
        return f"{'-' if v < 0 else ''}{digitos[0]}.{digitos[1:12]}e+{len(digitos) - 1}"
    if v.is_integer() and abs(v) < 1e15:
        return str(int(v))
    return f"{v:.12g}"


def _calc_converter(valor, modo: str) -> str:
    """Resultado como fração ('frac') ou em outra base ('hex', 'bin', 'oct')."""
    try:
        if modo == "frac":
            fracao = Fraction(valor).limit_denominator(10**6)
            return str(fracao) + ("" if float(fracao) == valor else " (aproximada)")
    except (OverflowError, ValueError):
        raise ToonsError("Esse número não vira fração.") from None
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    if not isinstance(valor, int):
        raise ToonsError("Só números inteiros podem ser mostrados em outra base.")
    return {"hex": hex, "bin": bin, "oct": oct}[modo](valor)


AJUDA_CALCULADORA = """\
Operadores:  + - * /  ^ ou **  (potência)  //  mod (resto)  5! (fatorial)  ( )
Porcentagem: 10%  200*10%  200+10% (=220)  200-10% (=180)
Constantes:  pi  e  tau  inf        ans = último resultado (começar com * / ^ continua dele)
Trigonom.:   sin cos tan  asin acos atan  sec csc cot  sinh cosh tanh  asinh acosh atanh
Funções:     sqrt  raiz(x, n)  cbrt  ln  log(x)  log(x, base)  log2  exp
             abs floor ceil round(x, casas)  fat(n)  mdc  mmc  comb(n,k)  perm(n,k)
             graus(rad)  radianos(graus)  aleatorio()  aleatorio(a, b)
Estatística: soma(…)  media(…)  mediana(…)  desvio(…)  min(…)  max(…)
Números:     1.5e3   0xFF   0b1010   0o17      2pi e 3(4+5) multiplicam sozinhos
Variáveis:   x = 5   e depois  2x   ('vars' lista)
Comandos:    deg / rad   hex  bin  oct  frac (mostra ans em outra forma)
             hist   limpar   ajuda   (Enter vazio sai)
Exemplos:    sqrt(2)pi    sin(30)    2^10    10!/3!    log(1000)    media(7, 8.5, 10)"""


@submenu
def menu_calculadora():
    # sem terminal interativo (ou com TOONS_NUMEROS=1) não há setas: usa o modo digitado
    if setas_ativas():
        _calculadora_botoes()
    else:
        _calculadora_texto()


def _calculadora_texto():
    limpar()
    titulo("🧮 Calculadora científica")
    print(f"{AJUDA_CALCULADORA}\n")
    graus = True
    variaveis: dict = {}
    historico: list = []
    while True:
        entrada = perguntar(f"[{'graus' if graus else 'rad'}]")
        comando = entrada.lower()
        if not entrada:
            return
        if comando in ("sair", "exit", "q"):
            return
        if comando in ("ajuda", "help", "?"):
            print(AJUDA_CALCULADORA)
        elif comando in ("deg", "graus"):
            graus = True
            ok("Ângulos em graus.")
        elif comando in ("rad", "radianos"):
            graus = False
            ok("Ângulos em radianos.")
        elif comando == "vars":
            for nome, valor in variaveis.items():
                print(f"  {CIANO}{nome}{RST} = {calc_formatar(valor)}")
            if not variaveis:
                info("Nenhuma variável. Crie com  nome = expressão")
        elif comando in ("hist", "historico", "histórico"):
            for conta, resultado in historico[-20:]:
                print(f"  {DIM}{conta}{RST} = {calc_formatar(resultado)}")
            if not historico:
                info("Nada calculado ainda.")
        elif comando in ("hex", "bin", "oct", "frac"):
            if "ans" not in variaveis:
                info("Faça uma conta primeiro.")
            else:
                try:
                    print(f"  {VERD}={RST} {NEG}{_calc_converter(variaveis['ans'], comando)}{RST}")
                except ToonsError as e:
                    erro(str(e))
        elif comando in ("limpar", "clear", "cls"):
            variaveis.clear()
            historico.clear()
            limpar()
            titulo("🧮 Calculadora científica")
        else:
            atribuicao = re.fullmatch(r"([A-Za-z_]\w*)\s*=(?!=)\s*(.+)", entrada)
            expressao = atribuicao.group(2) if atribuicao else entrada
            # começar com operador continua do último resultado, como numa calculadora: "* 2"
            if "ans" in variaveis and re.match(r"\s*(\*|/|\^|mod\b|%)", expressao):
                expressao = "ans " + expressao
            try:
                if atribuicao and (atribuicao.group(1) in CALC_RESERVADOS
                                   or atribuicao.group(1).lower() in _calc_funcoes(graus)):
                    raise ToonsError(f"'{atribuicao.group(1)}' é reservado; escolha outro nome.")
                valor = calc_avaliar(expressao, variaveis, graus)
            except ToonsError as e:
                erro(str(e))
                continue
            variaveis["ans"] = valor
            if atribuicao:
                variaveis[atribuicao.group(1)] = valor
            historico.append((entrada, valor))
            print(f"  {VERD}={RST} {NEG}{calc_formatar(valor)}{RST}")


# ── Calculadora com botões (setas + Enter) ──
# Cada botão: (rótulo, ação). A ação é o texto que entra na conta ou, começando
# com '#', um comando. Navega com as setas, Enter aperta; o teclado também digita.
CALC_BOTOES = [
    [("DEG", "#modo"), ("(", "("), (")", ")"), ("%", "%"), ("AC", "#limpar"), ("DEL", "#apagar"), ("÷", "/")],
    [("sin", "sin("), ("cos", "cos("), ("tan", "tan("), ("7", "7"), ("8", "8"), ("9", "9"), ("×", "*")],
    [("asin", "asin("), ("acos", "acos("), ("atan", "atan("), ("4", "4"), ("5", "5"), ("6", "6"), ("−", "-")],
    [("ln", "ln("), ("log", "log("), ("e^x", "exp("), ("1", "1"), ("2", "2"), ("3", "3"), ("+", "+")],
    [("√", "√("), ("x^2", "^2"), ("x^y", "^"), ("±", "#sinal"), ("0", "0"), (".", "."), ("=", "#igual")],
    [("π", "pi"), ("e", "e"), ("n!", "!"), ("1/x", "^(-1)"), ("∛", "cbrt("), ("10^x", "10^("), ("ans", "ans")],
    [("EXP", "E"), ("mod", " mod "), ("frac", "#frac"), ("hex", "#hex"), ("hist", "#hist"),
     ("?", "#ajuda"), ("sair", "#sair")],
]
CALC_GRADE_COLUNAS = len(CALC_BOTOES[0])
# o que, depois de um '=', continua a conta a partir do resultado (ans) em vez de começar outra
_CALC_CONTINUA = re.compile(r"^(\s*mod\s*|[-+*/^%!)])")
# pedaço apagado pelo DEL: uma função inteira 'sin(', ' mod ', 'ans', 'pi', '^(-1)' ou um caractere
_CALC_ULTIMO = re.compile(r"(?:[A-Za-z_]+\(|\s*mod\s*|ans|pi|\^\(-1\)|.)$")

AJUDA_BOTOES = [
    "←↑↓→   escolhe o botão",
    "Enter  aperta o botão",
    "Esc    sai",
    "",
    "O teclado também digita:",
    "  0-9 . + - * / ^ ( ) ! % ,",
    "  = calcula · Backspace apaga",
    "  x depois de um número = vezes",
    "",
    "RAD/DEG  troca radianos e graus",
    "±     troca o sinal do número",
    "%     200+10% = 220, 200-10% = 180",
    "n!    fatorial",
    "EXP   1.5 EXP 3 = 1500",
    "ans   último resultado; depois do",
    "      '=', + − × ÷ continuam dele",
    "frac  último resultado em fração",
    "hex   último resultado em hexa",
    "Parênteses abertos fecham sozinhos.",
]


def _calc_estilo(acao: str, rotulo: str) -> str:
    """Cor de fundo/texto de cada tipo de botão."""
    if not _COR:
        return ""
    if acao == "#igual":
        return "\033[1;30;42m"
    if acao in ("#limpar", "#apagar"):
        return "\033[1;97;41m"
    if rotulo.isdigit() or rotulo == ".":
        return "\033[1;97;100m"
    if acao in ("+", "-", "*", "/", "%", "^", "(", ")"):
        return "\033[1;93;100m"
    if acao.startswith("#"):
        return "\033[37;100m"
    return "\033[96;100m"


def _calc_tela(linhas: list) -> None:
    # sem '\n' depois da última linha: numa tela do tamanho exato ele rolaria tudo uma linha
    sys.stdout.write("\033[H" + "\033[K\n".join(linhas) + "\033[K\033[J")
    sys.stdout.flush()


def _calc_painel(titulo_painel: str, linhas: list) -> None:
    """Mostra uma tela de texto (histórico, ajuda) até apertar uma tecla."""
    colunas = shutil.get_terminal_size((60, 24)).columns
    _calc_tela([f"{NEG}{titulo_painel}{RST}", ""] + [_cortar(linha, colunas - 1) for linha in linhas]
               + ["", f"{DIM}Aperte qualquer tecla para voltar{RST}"])
    ler_tecla()


def _cortar(texto: str, largura: int) -> str:
    """Corta o texto (sem cores) para caber na largura, com '…' no fim."""
    if _largura(texto) <= largura:
        return texto
    while texto and _largura(texto) > largura - 1:
        texto = texto[:-1]
    return texto + "…"


def _calculadora_botoes():
    graus = True
    variaveis: dict = {}
    historico: list = []
    conta = ""            # o que está sendo digitado
    linha_resultado = ""  # prévia, resultado ou mensagem de erro
    tipo_resultado = ""   # "previa", "final" ou "erro"
    calculou = False      # True logo depois do '='
    lin, col = 4, 6       # começa no '='

    def fechada(texto: str) -> str:
        return texto + ")" * max(0, texto.count("(") - texto.count(")"))

    def previa() -> None:
        nonlocal linha_resultado, tipo_resultado
        linha_resultado, tipo_resultado = "", ""
        if conta and not calculou:
            with contextlib.suppress(ToonsError):
                linha_resultado = calc_formatar(calc_avaliar(fechada(conta), variaveis, graus))
                tipo_resultado = "previa"

    def acionar(acao: str) -> bool:
        """Executa um botão ou tecla; devolve False para sair."""
        nonlocal conta, linha_resultado, tipo_resultado, calculou, graus
        if acao == "#sair":
            return False
        if acao == "#igual":
            if not conta:
                return True
            texto = fechada(conta)
            try:
                valor = calc_avaliar(texto, variaveis, graus)
            except ToonsError as e:
                linha_resultado, tipo_resultado = str(e), "erro"
                return True
            variaveis["ans"] = valor
            historico.append((texto, valor))
            conta, calculou = texto, True
            linha_resultado, tipo_resultado = calc_formatar(valor), "final"
            return True
        if acao in ("#frac", "#hex"):
            if "ans" not in variaveis:
                linha_resultado, tipo_resultado = "Faça uma conta primeiro.", "erro"
                return True
            try:
                linha_resultado, tipo_resultado = _calc_converter(variaveis["ans"], acao[1:]), "final"
            except ToonsError as e:
                linha_resultado, tipo_resultado = str(e), "erro"
            return True
        if acao == "#hist":
            _calc_painel("Histórico", [f"{DIM}{c}{RST} = {NEG}{calc_formatar(v)}{RST}" for c, v in historico[-30:]]
                         or ["Nada calculado ainda."])
            return True
        if acao == "#ajuda":
            _calc_painel("Calculadora científica — ajuda", AJUDA_BOTOES)
            return True
        if acao == "#modo":
            graus = not graus
        elif acao == "#limpar":
            conta, calculou = "", False
        elif acao == "#apagar":
            conta = "" if calculou else _CALC_ULTIMO.sub("", conta, count=1)
            calculou = False
        elif acao == "#sinal":
            if calculou:
                conta, calculou = "ans", False
            m = re.search(r"(\(-)?(\d+\.?\d*|\.\d+|ans|pi|e)$", conta)
            if m and m.group(1):
                conta = conta[:m.start()] + m.group(2)
            elif m:
                conta = conta[:m.start()] + "(-" + m.group(2)
            else:
                conta += "-"
        else:
            if calculou:
                # depois do '=': operador continua do resultado; número ou função começa outra conta
                conta = "ans" + acao if _CALC_CONTINUA.match(acao) else acao
                calculou = False
            elif len(conta) < 300:
                conta += acao
        previa()
        return True

    sys.stdout.write("\033[?1049h")  # tela alternativa: ao sair, o terminal volta como estava
    _cursor(False)
    try:
        while True:
            colunas, linhas_tela = shutil.get_terminal_size((60, 24))
            largura_botao = min(9, (colunas - 1 - (CALC_GRADE_COLUNAS - 1)) // CALC_GRADE_COLUNAS)
            if largura_botao < 4 or linhas_tela < len(CALC_BOTOES) + 8:  # visor 6 + rodapé 2
                _calc_tela(["Tela pequena demais.", "Esconda o teclado,", "gire o celular ou",
                            "diminua a fonte (pinça).", f"{DIM}Esc sai{RST}"])
                if ler_tecla() == "esc":
                    return
                continue
            total = largura_botao * CALC_GRADE_COLUNAS + CALC_GRADE_COLUNAS - 1
            interno = total - 2
            espaco = linhas_tela >= len(CALC_BOTOES) * 2 + 8  # linha em branco entre fileiras, se couber

            # visor
            if len(conta) > interno - 1:
                mostrar_conta = "…" + conta[-(interno - 2):]
            else:
                mostrar_conta = conta or "0"
            if tipo_resultado == "erro":
                resultado = f"{VERM}{_cortar(linha_resultado, interno - 1)}{RST}"
            elif tipo_resultado == "final":
                resultado = f"{NEG}{VERD}= {_cortar(linha_resultado, interno - 3)}{RST}"
            elif tipo_resultado == "previa":
                resultado = f"{DIM}= {_cortar(linha_resultado, interno - 3)}{RST}"
            else:
                resultado = ""
            modo = "DEG" if graus else "RAD"
            topo = f"{AMAR}{modo}{RST}" + " " * (interno - 3 - len(f"hist {len(historico)}")) \
                + f"{DIM}hist {len(historico)}{RST}"
            conta_cor = f"{DIM}{mostrar_conta}{RST}" if calculou else f"{NEG}{mostrar_conta}{RST}"

            def caixa(texto: str) -> str:
                return f" │{' ' * max(0, interno - _largura(texto))}{texto}│"

            tela = [f" {NEG}{MAG}🧮 Calculadora científica{RST}",
                    " ╭" + "─" * interno + "╮", f" │{topo}│", caixa(conta_cor), caixa(resultado),
                    " ╰" + "─" * interno + "╯"]

            # botões
            for i, fileira in enumerate(CALC_BOTOES):
                celulas = []
                for j, (rotulo, acao) in enumerate(fileira):
                    if acao == "#modo":
                        rotulo = "RAD" if graus else "DEG"  # mostra para qual modo o botão troca
                    texto = rotulo.center(largura_botao)
                    if (i, j) == (lin, col):
                        celula = f"\033[1;30;103m{texto}{RST}" if _COR else f"[{rotulo.center(largura_botao - 2)}]"
                    else:
                        celula = f"{_calc_estilo(acao, rotulo)}{texto}{RST}"
                    celulas.append(celula)
                if espaco:
                    tela.append("")
                tela.append(" " + " ".join(celulas))
            tela.append("")
            tela.append(f" {DIM}{_cortar('←↑↓→ move · Enter aperta · ? ajuda · Esc sai', total)}{RST}")
            _calc_tela(tela)

            tecla = ler_tecla()
            if tecla == "esc":
                return
            if tecla in ("cima", "baixo"):
                lin = (lin + (1 if tecla == "baixo" else -1)) % len(CALC_BOTOES)
            elif tecla in ("esq", "dir"):
                col = (col + (1 if tecla == "dir" else -1)) % CALC_GRADE_COLUNAS
            elif tecla == "home":
                col = 0
            elif tecla == "end":
                col = CALC_GRADE_COLUNAS - 1
            elif tecla == "enter":
                if not acionar(CALC_BOTOES[lin][col][1]):
                    return
            elif tecla == "backspace":
                acionar("#apagar")
            elif tecla == "=":
                acionar("#igual")
            elif tecla == "?":
                acionar("#ajuda")
            elif tecla == "x" and (calculou or conta[-1:].isdigit() or conta.endswith(")")):
                acionar("*")  # 'x' depois de um número (ou do resultado) é vezes
            elif len(tecla) == 1 and (tecla in "0123456789.+-*/^()!%," or tecla.isalpha()):
                acionar(tecla)
    except KeyboardInterrupt:
        return
    finally:
        sys.stdout.write("\033[?1049l")
        _cursor(True)


# ════════════════════════════════════════════════════════════════════
#  Configurações e diagnóstico
# ════════════════════════════════════════════════════════════════════

@submenu
def menu_config():
    c = cfg()

    def mostrar():
        for chave, valor in c.items():
            if chave in ("monitores", "compartilhamentos"):
                valor = f"{len(valor)} item(ns)"
            elif chave.endswith(("token", "_chave", "_catalogo")):
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
    ("yt-dlp", "python-yt-dlp", "música e vídeos"), ("ffmpeg", "ffmpeg", "música e transmissão de filmes"),
    ("mpv", "mpv", "música"),
    ("nmap", "nmap", "rede"), ("sshd", "openssh", "SSH"), ("wg", "wireguard-tools", "WireGuard"),
    ("cloudflared", "cloudflared", "túnel"), ("adb", "android-tools", "depuração sem fio e Android/data"),
    ("termux-x11", "termux-x11-nightly", "desktop da distro (x11-repo)"),
    ("7z", "p7zip", "extrair .7z e .rar"), ("proot-distro", "proot-distro", "Linux"),
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
        ("📺 Compartilhar filme por link", menu_midia),
        ("🧮 Calculadora científica", menu_calculadora),
        ("🔄 Atualização", menu_atualizar),
        ("🧹 Otimização e limpeza", menu_otimizacao),
        ("🔌 Depuração sem fio (ADB pelo Wi-Fi)", menu_adb),
        ("📂 Gerenciador de arquivos (copiar, mover, renomear, Android/data...)", gerenciador_arquivos),
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
    p.add_argument("--formato", choices=list(FORMATOS_MUSICA), help="padrão: o último escolhido no menu")
    p = sub.add_parser("video", help="baixa vídeos (links do TikTok/YouTube ou termo de busca)")
    p.add_argument("alvos", nargs="+")
    p.add_argument("--formato", choices=list(FORMATOS_VIDEO), help="padrão: o último escolhido no menu")
    p.add_argument("--qualidade", choices=list(QUALIDADES_VIDEO), help="padrão: a última escolhida no menu")
    p = sub.add_parser("midia", help="servidor de vídeo (links de compartilhamento) em primeiro plano")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--porta", type=int)
    p = sub.add_parser("desktop", help="abre o desktop de uma distro no Termux:X11 (atalho da tela inicial)")
    p.add_argument("distro", nargs="?", help="nome da distro (padrão: a primeira instalada)")
    p.add_argument("--parar", action="store_true", help="encerra o desktop")
    p = sub.add_parser("arquivos", help="gerenciador de arquivos (copiar, mover, renomear, Android/data...)")
    p.add_argument("pasta", nargs="?")
    p = sub.add_parser("site", help="publica uma pasta como site (página HTML) em primeiro plano")
    p.add_argument("pasta")
    p.add_argument("--porta", type=int)
    p = sub.add_parser("compartilhar", help="cria um link para assistir a um vídeo e liga o servidor")
    p.add_argument("arquivo", help="vídeo do celular, link direto de arquivo ou página de vídeo (YouTube...)")
    p.add_argument("--titulo")
    p.add_argument("--horas", type=float, help="validade do link em horas (padrão: sem prazo)")
    p.add_argument("--legenda", action="append", help="legenda .srt/.vtt extra (arquivo ou link); pode repetir")
    p = sub.add_parser("assistir", help="toca um link no VLC do celular, sem baixar")
    p.add_argument("link")
    p.add_argument("--escolher", action="store_true", help="mostra a lista de apps em vez de abrir o VLC")
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
                baixar_alvo(alvo, args.formato)
        elif args.comando == "video":
            falhas = sum(not baixar_video(alvo, args.formato, args.qualidade) for alvo in args.alvos)
            if falhas:
                raise ToonsError(f"{falhas} download(s) falharam.")
        elif args.comando == "midia":
            servir_midia(args.host, args.porta or cfg()["midia_porta"])
        elif args.comando == "desktop":
            if args.parar:
                parar_desktop()
            else:
                distro = args.distro or next(iter(distros_instaladas()), None)
                if not distro:
                    raise ToonsError("Nenhuma distro instalada (use o menu Linux de verdade).")
                if not iniciar_desktop(distro):
                    return 1
        elif args.comando == "arquivos":
            gerenciador_arquivos(args.pasta)
        elif args.comando == "site":
            servir_site(args.pasta, args.porta or cfg()["site_porta"])
        elif args.comando == "compartilhar":
            link = conferir_link(args.arquivo) if eh_link(args.arquivo) else {"pagina": False, "titulo": None}
            item = criar_compartilhamento(args.arquivo, args.titulo or link["titulo"], args.horas,
                                          legendas=args.legenda, pagina=link["pagina"])
            garantir_servidor_midia()
            mostrar_links(item)
        elif args.comando == "assistir":
            abrir_no_android(endereco_para_assistir(args.link), None if args.escolher else VLC_ANDROID)
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
