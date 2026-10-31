#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Termux-Toons — um canivete suíço em Python para o Termux.

Reúne em um único menu:
   1. Servidor web/API pessoal (Flask, FastAPI ou só biblioteca padrão) + Cloudflare Tunnel
   2. Bots de Telegram e Discord rodando 24h (tmux + termux-wake-lock)
   3. Scraping e monitoramento (preço, notícias/RSS, status de site, chuva)
   4. Rede e segurança em equipamentos seus (nmap, SSH, WireGuard, velocidade, modem AT)
   5. Linux de verdade com proot-distro (Debian, Ubuntu, Arch...), com desktop no Termux:X11
   6. Arquivos e backup: gerenciador de arquivos (ADB ou root para Android/data), rclone, Syncthing,
      Samba, HTTP, backup e página HTML num link
   7. Música, rádio e podcasts: yt-dlp para baixar, mpv para tocar, rádios online e podcasts
   8. Vídeos do TikTok, YouTube e outros sites com yt-dlp
   9. Compartilhar filmes por link: arquivo do celular ou qualquer link de vídeo, com player próprio,
      troca de trilha de áudio e conversão na hora (servidor de vídeo + túnel)
  10. Calculadora científica com botões (setas + Enter)
  11. Utilitários: notas, tarefas, lembretes/alarmes, cronômetro/Pomodoro, agenda, conversor, gastos,
      senhas, previsão do tempo, QR code (Wi-Fi, PIX) e tradutor
  12. Celular e sistema: depuração sem fio (ADB), Termux:API, painel do sistema, bateria, uso de dados e
      apps, resolução da tela (inteira ou por app), fotos, conversor de arquivos, automação por eventos,
      espelhamento e transmissão da tela por link
  13. Internet: e-mail, notícias, downloads (aria2), chat na rede local, Browsh/w3m e encurtador/pastebin
  14. Inteligência artificial: Claude/ChatGPT/Gemini, LLMs locais (llama.cpp), voz (whisper.cpp) e OCR
  15. Diversão e aprendizado: jogos (incluindo os retrô), cursos de Python/Bash/Git, BASIC, leitor de
      livros e arte ASCII
  16. Programação e servidores: ambiente de desenvolvimento, SQLite/MariaDB/PostgreSQL, GitHub, cron,
      Minecraft, Jellyfin e Navidrome
  17. Atualização do Termux e dos repositórios
  18. Otimização e limpeza (caches, arquivos grandes/duplicados, processos)
  19. Configurações e diagnóstico

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
import base64
import calendar
import contextlib
import copy
import csv
import difflib
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
import posixpath
import random
import re
import secrets
import select
import shlex
import shutil
import socket
import stat
import statistics
import string
import struct
import subprocess
import sys
import tarfile
import textwrap
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
from datetime import date, datetime, timedelta
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


def _c(codigo: int | str) -> str:
    return f"\033[{codigo}m" if _COR else ""


RST, NEG, DIM, INV = _c(0), _c(1), _c(2), _c(7)
VERM, VERD, AMAR, AZUL, MAG, CIANO = _c(31), _c(32), _c(33), _c(34), _c(35), _c(36)
# opção selecionada: preto (38;5;16, que o negrito não clareia) sobre o ciano do tema
DESTAQUE = _c("1;38;5;16;46")


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


def _no_centro(texto: str, colunas: int) -> str:
    """Recua o texto para ele ficar no meio da tela (sem espaços à direita)."""
    return " " * max(0, (colunas - _largura(texto)) // 2) + texto


def _faixa_titulo(texto: str, largura: int) -> str:
    """Título numa linha só, ═══ texto ═══, com `largura` colunas."""
    texto = f" {texto} "
    sobra = max(0, largura - _largura(texto))
    return f"{CIANO}{'═' * (sobra // 2)}{RST}{NEG}{texto}{RST}{CIANO}{'═' * (sobra - sobra // 2)}{RST}"


def titulo(texto: str) -> None:
    colunas = largura_tela()
    print(_no_centro(_faixa_titulo(texto, max(20, min(colunas, 70))), colunas))


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
    # numa tela cheia o terminal já está assim: mudar de novo (TCSAFLUSH) jogaria fora a tecla já apertada
    ja_sem_enter = not antigo[3] & termios.ICANON
    try:
        if not ja_sem_enter:
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
        if not ja_sem_enter:
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


def _linha_opcao(texto: str, selecionada: bool, largura: int) -> str:
    """Uma opção da lista; a selecionada vira uma faixa colorida de `largura` colunas de texto."""
    if selecionada:
        texto = _cortar(_sem_ansi(texto), largura)  # o corte termina em RST: o destaque volta logo depois
        return f"{CIANO}❯{RST} {DESTAQUE} {texto}{DESTAQUE}{' ' * (largura - _largura(texto))} {RST}"
    return "   " + _cortar(texto, largura)


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
    maior = max(_largura(str(op)) for op in opcoes) + (4 if multipla else 0)
    _cursor(False)
    try:
        while True:
            colunas, linhas_tela = shutil.get_terminal_size((60, 24))
            altura = max(1, min(len(opcoes), linhas_tela - 3))
            topo = _janela(sel, topo, altura, len(opcoes))
            largura = max(1, min(maior, colunas - 5))
            linhas = []
            for i in range(topo, topo + altura):
                caixa = ("[x] " if i in marcadas else "[ ] ") if multipla else ""
                linhas.append(_linha_opcao(caixa + str(opcoes[i]), i == sel, largura))
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


def _botoes_sim_nao(sim: bool) -> str:
    if not _COR:
        return "[Sim]  Não " if sim else " Sim  [Não]"
    return f"{DESTAQUE} Sim {RST}  Não " if sim else f" Sim  {DESTAQUE} Não {RST}"


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
            sys.stdout.write(f"\r   {_botoes_sim_nao(sim)}  {DIM}(←→ e Enter){RST}\033[K")
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


def confirmar_no_prazo(msg: str, prazo: float) -> bool:
    """Sim/Não com contagem regressiva até `prazo` (um time.time()). Começa no Não e o tempo esgotado conta
    como Não: quem não consegue ler a tela (ex.: resolução que deu errado) só precisa esperar ou dar Enter."""
    print(f"{AMAR}?{RST} {msg}")
    if not setas_ativas():
        print(f"   Digite s e Enter em até {max(0, round(prazo - time.time()))} s para manter.")
        pronto = select.select([sys.stdin], [], [], max(0.0, prazo - time.time()))[0]
        sim = bool(pronto) and sys.stdin.readline().strip().lower() in ("s", "sim", "y", "yes")
        print(f"   {VERD}✔{RST} {'Sim' if sim else 'Não'}" if pronto else f"   {DIM}tempo esgotado{RST}")
        return sim
    fd = sys.stdin.fileno()
    antigo = termios.tcgetattr(fd)
    sim, esgotou = False, True
    _cursor(False)
    try:
        tty.setcbreak(fd)  # o tempo todo, para o select ver cada tecla sem esperar Enter
        while (resta := prazo - time.time()) > 0:
            sys.stdout.write(f"\r   {_botoes_sim_nao(sim)}  {AMAR}volta sozinho em {math.ceil(resta)} s{RST}\033[K")
            sys.stdout.flush()
            if not select.select([fd], [], [], min(1.0, resta))[0]:
                continue
            tecla = ler_tecla()
            if tecla in ("esq", "dir", "cima", "baixo", "\t"):
                sim = not sim
            elif tecla.lower() in ("s", "y", "n") or tecla in ("esc", "enter"):
                sim = tecla.lower() in ("s", "y") or (tecla == "enter" and sim)
                esgotou = False
                break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, antigo)
        _cursor(True)
    fim = f"{DIM}tempo esgotado{RST}" if esgotou else f"{VERD}✔{RST} {'Sim' if sim else 'Não'}"
    sys.stdout.write(f"\r   {fim}\033[K\n")
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


def _quebrar(linha: str, colunas: int) -> list:
    """Quebra por palavras uma linha que não cabe na tela, mantendo a cor do começo."""
    if _largura(linha) <= colunas:
        return [linha]
    cor = re.match(f"(?:{_ANSI.pattern})*", linha).group()
    return [cor + parte + RST for parte in textwrap.wrap(_sem_ansi(linha), max(10, colunas - 4))] or [linha]


def _menu_setas(titulo_menu: str, itens: list, sair: str, cabecalho, sel: int, descricoes=None):
    """Desenha o menu em tela cheia, no centro da tela, e devolve o índice escolhido (None = voltar).
    Com `descricoes` (um texto por item), a da opção selecionada aparece embaixo da lista."""
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
            cab = [parte for linha in linhas_cab for parte in _quebrar(linha, colunas)]
            if cab:
                cab.append("")
            # descrições: guarda o espaço da maior (até 6 linhas) para a lista não pular ao mudar de opção
            largura_desc = max(20, min(colunas - 4, 64))
            quebradas = [textwrap.wrap(d or "", largura_desc) for d in descricoes or []]
            reserva = min(max(map(len, quebradas), default=0), 6)
            fixas = 4 + (reserva + 1 if reserva else 0)  # título, linhas vazias, rodapé (+ descrição)
            disponivel = linhas_tela - len(cab) - fixas
            if disponivel < min(total, 6):  # tela pequena: esconde o cabeçalho
                cab, disponivel = [], linhas_tela - fixas
            if disponivel < min(total, 4) and reserva > 2:  # tela bem baixa: descrição em 2 linhas
                disponivel, reserva = disponivel + reserva - 2, 2
            altura = max(1, min(total, disponivel))
            topo = _janela(sel, topo, altura, total)
            # as opções formam um bloco alinhado à esquerda (emojis um embaixo do outro) e o bloco vai para o meio
            largura = max(1, min(max(map(_largura, rotulos)), colunas - 4))
            recuo = " " * max(0, (colunas - largura - 4) // 2)
            linhas = [_no_centro(linha, colunas) for linha in cab]
            linhas += [_no_centro(_faixa_titulo(titulo_menu, max(20, min(colunas, 70))), colunas), ""]
            for i in range(topo, topo + altura):
                rotulo = f"{DIM}{rotulos[i]}{RST}" if i == total - 1 and i != sel else rotulos[i]  # "Voltar" apagado
                linhas.append(recuo + _linha_opcao(rotulo, i == sel, largura))
            if reserva:
                texto = quebradas[sel] if sel < len(quebradas) else []
                if len(texto) > reserva:
                    texto = texto[:reserva - 1] + [_cortar(texto[reserva - 1] + " …", largura_desc)]
                recuo_desc = " " * max(0, (colunas - largura_desc) // 2)
                linhas += [""] + [f"{recuo_desc}{CIANO}{t}{RST}" for t in texto] + [""] * (reserva - len(texto))
            rodape = "↑↓ mover · Enter abre · Esc volta"
            if total > altura:
                rodape += f" · {sel + 1}/{total}"
            linhas += ["", _no_centro(f"{DIM}{rodape}{RST}", colunas)]
            linhas = [""] * max(0, (linhas_tela - len(linhas)) // 2) + linhas  # sobrando espaço, centraliza na altura
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


def menu(titulo_menu: str, itens: list, sair: str = "Voltar", cabecalho=None, descricoes=None) -> None:
    if setas_ativas():
        sel = 0
        while True:
            try:
                escolha = _menu_setas(titulo_menu, itens, sair, cabecalho, sel, descricoes)
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
            if descricoes and i <= len(descricoes) and descricoes[i - 1]:
                for linha in textwrap.wrap(descricoes[i - 1], max(20, min(largura_tela(), 80) - 8)):
                    print(f"      {DIM}{linha}{RST}")
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


def pasta_download() -> Path:
    """A pasta Download do celular, com o caminho que a pessoa reconhece.
    ~/storage/downloads é um atalho para /storage/emulated/0/Download; o Android mostra
    o atalho como se estivesse dentro do Termux (/data/data/com.termux/...), então aqui
    resolvemos para o caminho real. Cai em alternativas quando o atalho ainda não existe."""
    for p in (HOME / "storage" / "downloads", Path("/storage/emulated/0/Download"), Path("/sdcard/Download")):
        try:
            if p.exists():
                return p.resolve()
        except OSError:
            continue
    return HOME / "storage" / "downloads"


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
    "sites": {},
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
    "tts_velocidade": 1.0,
    "tempo_local": {},
    "tradutor_destino": "en",
    "tradutor_falar": False,
    "bateria_alerta_carga": 80,
    "bateria_alerta_baixa": 15,
    "bateria_alerta_temp": 42,
    "automacoes": [],
    "email": {},
    "feeds": [],
    "aria2_segredo": "",
    "aria2_pasta": "",
    "aria2_simultaneos": 3,
    "chat_nome": "",
    "whisper_modelo": "base",
    "radios_favoritas": [],
    "podcasts": [],
    "banner_texto": "",
    "banner_fonte": "standard",
    "minecraft_memoria": "1G",
    "tela_porta": 8093,
    "tela_token": "",
    "tela_controle": False,
    "tela_qualidade": "normal",
    "trote_porta": 8099,
    "trote_titulo": "Você caiu no trote! 👻",
    "trote_mensagem": "EU TE PEGUEI!!!",
    "trote_imagem": "",
    "trote_som": "",
    "trote_piscar": True,
    "trote_vibrar": True,
    "trote_notificacoes": True,
    "trote_notif_textos": [
        "👻 ele está atrás de você",
        "😱 NÃO OLHE PARA TRÁS",
        "🔪 estou te vendo...",
        "💀 3... 2... 1...",
        "📵 é tarde demais",
        "🩸 você não devia ter clicado",
    ],
    "trote_cor": "#b10000",
    "trote_atraso": 2,
    "trote_duracao": 15,
    "trote_volume": 1.0,
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
    idioma, velocidade = cfg().get("tts_idioma"), cfg().get("tts_velocidade") or 1.0
    if idioma:
        cmd += ["-l", idioma]
    if float(velocidade) != 1.0:
        cmd += ["-r", str(velocidade)]
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

    menu("📱 Termux:API", [
        ("Listar sensores", listar_sensores),
        ("Ler um sensor", ler_sensor_menu),
        ("Enviar SMS", enviar_sms),
        ("Ler últimos SMS", ler_sms),
        ("Enviar notificação", notificacao),
        ("Tirar foto", tirar_foto),
        ("Localização atual", local),
        ("Vibrar", lambda: vibrar(perguntar_int("Duração (ms)", 500, 50, 5000))),
        ("Lanterna liga/desliga", lambda: lanterna(confirmar("Ligar a lanterna?", True))),
        ("Área de transferência", clipboard),
        ("Volume do sistema", lambda: mostrar_dados(_tapi(["termux-volume"], 15))),
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


def instalar_textual() -> None:
    if garantir_modulo("textual"):
        info("Teste com: python -m textual  (demonstração oficial do Textual)")


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
        ("Textual: biblioteca para criar seus próprios apps de terminal", instalar_textual),
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
    "chuva": "Chuva prevista nas próximas horas",
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
    if tipo == "chuva":
        return checar_chuva(m, est)
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
        elif tipo == "chuva":
            dados.update(configurar_alerta_chuva())
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


def basic_repl() -> None:
    Basic().repl()


def criar_jogo() -> None:
    """Gera um template de jogo em Python para a pessoa editar e jogar."""
    destino = Path(os.path.expanduser(perguntar("Salvar o template em", str(HOME / "meu_jogo.py"))))
    if destino.exists() and not confirmar(f"{destino} já existe. Sobrescrever?"):
        return
    destino.write_text(TEMPLATE_JOGO, "utf-8")
    destino.chmod(0o755)
    ok(f"Template criado: {destino}")
    info(f"Jogue com: python {destino}   |   Edite com: nvim {destino}")
    if confirmar("Jogar agora?", True):
        rodar([sys.executable, destino], mostrar=False)


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

MAX_SITES = 5  # quantos sites podem ficar no ar ao mesmo tempo
SITES_DIR = DATA_DIR / "sites"  # cópia do arquivo quando você publica só uma página (uma pasta por site)


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


def _servico_site(n: int) -> str:
    """Serviço tmux do site n (o 1º mantém o nome de antes, 'site')."""
    return "site" if n == 1 else f"site-{n}"


def _tunel_site(n: int) -> str:
    return "tunel-" + _servico_site(n)


def _dados_site(n: int) -> dict:
    """O que está publicado no site n: nome, página que abre primeiro e porta."""
    c = cfg()
    padrao = {"nome": f"Site {n}", "pagina": c.get("site_pagina", "") if n == 1 else "", "porta": c["site_porta"]}
    return {**padrao, **c["sites"].get(str(n), {})}


def sites_no_ar() -> list:
    """Números (1 a MAX_SITES) dos sites publicados agora."""
    ativos = set(servicos_ativos())
    return [n for n in range(1, MAX_SITES + 1) if _servico_site(n) in ativos]


def _porta_do_site(n: int, preferida: int) -> int:
    """A porta que o site n já usava, se estiver livre; senão a primeira livre que nenhum outro site usa."""
    ocupadas = {_dados_site(k)["porta"] for k in sites_no_ar() if k != n}
    if preferida not in ocupadas and porta_livre(preferida, espera=3):
        return preferida
    # Depois da site_porta, pula para 8111 em diante: 8098 e 8099 são do chat e do trote.
    for porta in (cfg()["site_porta"], *range(8111, 8131)):
        if porta not in ocupadas and porta_livre(porta):
            return porta
    raise ToonsError("Não achei uma porta livre para o site. Troque 'site_porta' em Configurações.")


def links_do_site(n: int) -> list:
    """[(onde funciona, link)] do site n: rede local e, com o túnel ligado, a internet."""
    site = _dados_site(n)
    caminho = "/" + urllib.parse.quote(site["pagina"])
    links = [("Mesma rede Wi-Fi", f"http://{ip_local()}:{site['porta']}{caminho}")]
    tunel = _tunel_site(n)
    if servico_ativo(tunel) and url_tunel(tunel):
        links.append(("Internet", f"{url_tunel(tunel)}{caminho}"))
    return links


def _rotulo_site(n: int) -> str:
    return f"{n}. {_dados_site(n)['nome']}  {DIM}{links_do_site(n)[-1][1]}{RST}"


def _mostrar_links(n: int) -> None:
    print(f"  {NEG}{n}. {_dados_site(n)['nome']}{RST}")
    for onde, link in links_do_site(n):
        print(f"  {CIANO}{onde}:{RST}\n  {NEG}{link}{RST}")
    if not servico_ativo(_tunel_site(n)):
        print(f"  {DIM}Para quem está fora da sua rede Wi-Fi, use 'Site publicado: liberar para a internet'.{RST}")


def mostrar_links_do_site() -> None:
    no_ar = sites_no_ar()
    if not no_ar:
        info("Nenhuma página publicada agora.")
        return
    info(f"{len(no_ar)} de {MAX_SITES} sites no ar.")
    for n in no_ar:
        print()
        _mostrar_links(n)


def _escolher_site(msg: str) -> int | None:
    """Qual site publicado usar (só pergunta se houver mais de um no ar)."""
    no_ar = sites_no_ar()
    if not no_ar:
        info("Nenhuma página publicada agora. Use 'Publicar página/site HTML num link'.")
        return None
    if len(no_ar) == 1:
        return no_ar[0]
    i = escolher(msg, [_rotulo_site(n) for n in no_ar])
    return None if i is None else no_ar[i]


def liberar_site() -> None:
    """Liga o túnel da Cloudflare de um site publicado (para quem está fora do Wi-Fi)."""
    n = _escolher_site("Liberar qual site para a internet?")
    if n is not None:
        abrir_tunel(_tunel_site(n), _dados_site(n)["porta"])


def qr_do_site(n: int | None = None) -> None:
    """Mostra na tela o QR code do link de um site publicado e oferece baixar a imagem (.png)."""
    n = n or _escolher_site("QR code de qual site?")
    if n is None:
        return
    links = links_do_site(n)
    i = len(links) - 1  # o da internet, quando o túnel está ligado
    if len(links) > 1:
        i = escolher("QR code de qual link?", [f"{onde}: {link}" for onde, link in links], len(links))
        if i is None:
            return
    onde, link = links[i]
    if not garantir_cmd("qrencode", "libqrencode"):
        return
    mostrar_qr(link, salvar=False)
    print(f"  {CIANO}{onde}:{RST} {NEG}{link}{RST}")
    if confirmar("Baixar o QR code (imagem .png na pasta Download)?", True) \
            and not salvar_qr(link, f"site {_dados_site(n)['nome']}"):
        raise ToonsError("Não consegui salvar a imagem do QR code.")


def publicar_site() -> None:
    """Escolhe um .html (ou a pasta de um site), sobe o servidor e, se quiser, o túnel para a internet."""
    info("Publica uma página HTML (ou um site com imagens, CSS e JS) num link. Na mesma rede Wi-Fi funciona "
         f"na hora; para quem está longe, o túnel da Cloudflare cria um endereço na internet. Até {MAX_SITES} "
         "sites ficam no ar ao mesmo tempo, cada um com o seu link.")
    no_ar = sites_no_ar()
    if len(no_ar) >= MAX_SITES:
        i = escolher(f"Já há {MAX_SITES} sites no ar (o máximo). Qual substituir?", [_rotulo_site(k) for k in no_ar])
        if i is None:
            return
        n = no_ar[i]
    elif no_ar:
        i = escolher("Onde publicar?", [f"➕ Mais um site ({len(no_ar)} de {MAX_SITES} no ar)"]
                     + [f"Substituir {_rotulo_site(k)}" for k in no_ar], 1)
        if i is None:
            return
        n = next(k for k in range(1, MAX_SITES + 1) if k not in no_ar) if i == 0 else no_ar[i - 1]
    else:
        n = 1
    garantir_storage()
    # Lista os .html que estão no celular (Download, Documentos, DCIM...) para escolher na hora,
    # em vez de a pessoa ter que digitar o caminho da pasta Download.
    htmls = listar_arquivos((".html", ".htm"))
    alvo = None
    if htmls:
        rotulos = [_rotulo_arquivo(a) for a in htmls] + ["✍️  Digitar o caminho (arquivo .html ou pasta do site)..."]
        i = escolher("Página .html encontrada no celular (Download, Documentos...)", rotulos)
        if i is None:
            return
        if i < len(htmls):
            alvo = htmls[i]
    if alvo is None:
        resp = perguntar("Arquivo .html ou pasta do site", str(pasta_download())).strip().strip("'\"")
        if not resp:
            return
        alvo = Path(os.path.expanduser(resp))
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
            copia = SITES_DIR / str(n)
            shutil.rmtree(copia, ignore_errors=True)
            copia.mkdir(parents=True)
            shutil.copy2(alvo, copia / "index.html")
            pasta, pagina = copia, ""
        else:
            aviso(f"Todos os arquivos de {alvo.parent} ficam acessíveis para quem tiver o link.")
            if not confirmar("Continuar?", True):
                return
            pasta, pagina = alvo.parent, "" if alvo.name == "index.html" else alvo.name
    else:
        raise ToonsError(f"Escolha um arquivo .html ou uma pasta: {alvo}")
    servico, tunel = _servico_site(n), _tunel_site(n)
    anterior = _dados_site(n)["porta"]
    if servico_ativo(servico):
        parar_servico(servico)
    porta = _porta_do_site(n, anterior)
    if porta != anterior and servico_ativo(tunel):
        parar_servico(tunel)  # apontava para a porta antiga
    cfg()["sites"][str(n)] = {"nome": alvo.name, "pagina": pagina, "porta": porta}
    salvar_cfg()
    if not iniciar_servico(servico, cmd_self("site", str(pasta), "--porta", str(porta)), reiniciar=True):
        return
    if not servico_ativo(tunel) and confirmar("Liberar para a internet (pessoas fora do seu Wi-Fi)?", True):
        abrir_tunel(tunel, porta)
    print()
    _mostrar_links(n)
    _, link = links_do_site(n)[-1]
    if tem("termux-clipboard-set") and confirmar("Copiar o link?", True):
        _tapi(["termux-clipboard-set"], 10, entrada=link, json_saida=False)
        ok("Link copiado.")
    if confirmar("Gerar o QR code do link (e baixar a imagem)?", True):
        qr_do_site(n)
    info("O link funciona enquanto o celular estiver ligado com o Termux aberto. O endereço do túnel muda "
         "toda vez que ele é religado.")


def parar_site() -> None:
    """Tira do ar um dos sites publicados (ou todos)."""
    no_ar = sites_no_ar()
    if not no_ar:
        info("Nenhuma página publicada agora.")
        return
    alvos = no_ar
    if len(no_ar) > 1:
        i = escolher("Tirar qual site do ar?", [_rotulo_site(n) for n in no_ar] + [f"Todos ({len(no_ar)})"])
        if i is None:
            return
        alvos = no_ar if i == len(no_ar) else [no_ar[i]]
    for n in alvos:
        if servico_ativo(_tunel_site(n)):
            parar_servico(_tunel_site(n))
        parar_servico(_servico_site(n))


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
        (f"🌍 Publicar página/site HTML num link (até {MAX_SITES} ao mesmo tempo)", publicar_site),
        ("Sites publicados: ver os links", mostrar_links_do_site),
        ("Site publicado: QR code do link (gerar e baixar)", qr_do_site),
        ("Site publicado: liberar para a internet (túnel)", liberar_site),
        ("Site publicado: tirar do ar", parar_site),
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

    menu("🎵 Música, rádio e podcasts", [
        ("Buscar e tocar (streaming)", buscar_tocar),
        ("Buscar e baixar (escolhe o formato: MP3, Opus, M4A, FLAC...)", buscar_baixar),
        ("Baixar por link (YouTube, SoundCloud, playlist...)", baixar_link),
        ("Baixar do Spotify (link → busca no YouTube)", baixar_spotify),
        ("Tocar mix/rádio por busca", mix),
        ("📻 Rádio online (estações do Brasil e do mundo)", menu_radio),
        ("🎙️ Podcasts (buscar, seguir, ouvir, baixar)", menu_podcasts),
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


def porta_livre(porta: int, espera: float = 0) -> bool:
    """Com `espera`, insiste por até tantos segundos: um servidor recém-parado leva um
    instante para soltar a porta."""
    limite = time.monotonic() + espera
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", porta))
                return True
            except OSError:
                if time.monotonic() >= limite:
                    return False
        time.sleep(0.25)


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
        ("📖 Comandos do ADB: lista com a descrição de cada um", menu_comandos_adb),
        ("Tirar print da tela", print_tela),
        ("Gravar a tela", gravar_tela),
        ("Instalar APK", instalar_apk),
        ("Logcat (erros ou filtro)", logcat),
        ("Conceder permissão a um app (pm grant)", permissao),
        ("Liberar ADB na porta 5555 para um computador", porta_5555),
        ("Desconectar", desconectar),
        ("Desligar a Depuração por Wi-Fi", desligar_depuracao),
        ("Instalar o adb (android-tools)", garantir_adb),
    ])


# ── Comandos do ADB com descrição ────────────────────────────────────
# Baseado na documentação oficial (developer.android.com/tools/adb). Cada comando é
# (como aparece, descrição, o que rodar, marca). O que rodar vai depois de "adb -s <aparelho>":
# "shell ..." roda dentro do Android e {nome} é perguntado na hora (PARAMETROS_ADB); None = só para
# consultar (precisa de root, de um app de teste, apaga dados ou tem opção melhor no menu).
# Marcas: "local" não precisa de aparelho conectado; "perigoso" pede confirmação já marcada em Não.

COMANDOS_ADB = {
    "🔌 Aparelhos e conexão": ("Ver os aparelhos, parear e conectar pelo Wi-Fi e reiniciar o servidor do adb.", [
        ("adb devices -l", "Lista os aparelhos conectados com o número de série, o estado (device = pronto, offline = "
         "sem resposta, unauthorized = falta aceitar no celular) e a descrição (produto, modelo, aparelho).",
         "devices -l", "local"),
        ("adb pair <ip:porta> <código>", "Pareia com o celular pela Depuração por Wi-Fi (Android 11+) usando o IP, a "
         "porta e o código de 6 dígitos da tela 'Parear dispositivo com código de pareamento'. Feito uma vez só.",
         "pair {endereco} {codigo}", "local"),
        ("adb connect <ip:porta>", "Conecta ao celular pelo Wi-Fi. No Android 11+ use o IP e a porta da tela "
         "'Depuração por Wi-Fi' (a porta muda cada vez que ela é ligada); no Android 10 ou anterior, a porta 5555 "
         "liberada pelo adb tcpip.", "connect {endereco}", "local"),
        ("adb mdns services", "Lista os aparelhos que se anunciam na rede (mDNS): o celular com a Depuração por Wi-Fi "
         "ligada aparece como _adb-tls-connect, com IP e porta. Nas versões novas do adb a documentação usa "
         "adb mdns track-services --proto-text.", "mdns services", "local"),
        ("adb server-status", "Mostra a configuração do servidor do adb: versão, se o mDNS está ligado e onde fica o "
         "log. Só existe nas versões novas do adb (a documentação pede a 37 ou mais nova).", "server-status", "local"),
        ("adb kill-server", "Encerra o servidor do adb; o próximo comando abre outro sozinho. Resolve conexões "
         "travadas ou aparelho que sumiu da lista.", "kill-server", "local"),
        ("adb start-server", "Abre o servidor do adb (se já estiver aberto, não faz nada).", "start-server", "local"),
        ("adb tcpip 5555", "Deixa o celular aceitando o adb na porta 5555 até reiniciar: o jeito do Android 10 ou "
         "anterior, depois de uma conexão USB. Enquanto isso, qualquer aparelho na mesma rede pode pedir para depurar.",
         "tcpip 5555", "perigoso"),
        ("adb -s <série> <comando>", "Escolhe o aparelho quando há mais de um conectado (a série vem do adb devices). "
         "-d escolhe o único aparelho USB, -e o único emulador, e a variável ANDROID_SERIAL define um padrão. Aqui o "
         "Termux-Toons já faz isso sozinho.", None, ""),
        ("adb help", "Lista todos os comandos que o adb aceita, com as opções de cada um.", "help", "local"),
    ]),
    "📂 Arquivos e shell": ("Copiar arquivos entre o Termux e o celular e usar o shell do Android.", [
        ("adb push <no Termux> <no celular>", "Copia um arquivo ou pasta daqui para o celular (ex.: foto.jpg para "
         "/sdcard/foto.jpg). Com a permissão de 'shell' dá para escrever onde o Termux sozinho não alcança, como "
         "/data/local/tmp.", "push {no_termux} {no_celular}", ""),
        ("adb pull <no celular> <no Termux>", "Copia um arquivo ou pasta do celular para cá. Serve para pastas "
         "protegidas, como Android/data, que o Termux sozinho não lê.", "pull {no_celular} {no_termux}", ""),
        ("adb shell", "Abre um shell interativo dentro do Android, com a permissão de 'shell'. Sai com exit ou Ctrl+D.",
         "shell", ""),
        ("adb shell ls /system/bin", "Lista as ferramentas de linha de comando do Android (a maioria responde a "
         "--help).", "shell ls /system/bin", ""),
        ("adb shell toybox --help", "Ajuda do toybox, que fornece a maioria dos comandos básicos do Android (ls, cp, "
         "grep...).", "shell toybox --help", ""),
    ]),
    "📦 Instalar apps": ("Instalar APKs, inclusive divididos em vários arquivos e de teste.", [
        ("adb install <apk>", "Instala um APK no celular.", "install {apk}", ""),
        ("adb install -t <apk>", "Instala um APK de teste (android:testOnly), como os gerados com uma versão de "
         "prévia do SDK.", "install -t {apk}", ""),
        ("adb install-multiple <apks>", "Instala de uma vez um app dividido em vários APKs (split APK: o base.apk e "
         "os split_*.apk).", "install-multiple {apks}", ""),
        ("pm install: opções", "Dentro do shell, pm install aceita: -r reinstala mantendo os dados, -t aceita APK de "
         "teste, -d deixa voltar para uma versão mais antiga, -g concede todas as permissões do app, -i define quem "
         "instalou, --user escolhe o usuário, --install-location 0/1/2 (automático, interno, externo), --fastdeploy "
         "envia só o que mudou e --incremental abre o app antes de terminar de instalar.", None, ""),
    ]),
    "📋 Gerenciador de pacotes (pm)": ("Listar apps, permissões e recursos; limpar, desativar e dar permissões.", [
        ("adb shell pm list packages", "Lista todos os apps instalados. Opções: -f mostra o APK, -d só desativados, -e "
         "só ativados, -s só do sistema, -3 só os de terceiros, -i quem instalou, -u inclui os desinstalados; um texto "
         "no fim filtra.", "shell pm list packages", ""),
        ("adb shell pm list packages -3", "Só os apps que você instalou (de terceiros).", "shell pm list packages -3",
         ""),
        ("adb shell pm list packages -s", "Só os apps do sistema.", "shell pm list packages -s", ""),
        ("adb shell pm list packages -d", "Só os apps desativados.", "shell pm list packages -d", ""),
        ("adb shell pm list packages -f <texto>", "Apps com o texto no nome, junto com o caminho do APK de cada um.",
         "shell pm list packages -f {filtro}", ""),
        ("adb shell pm list permission-groups", "Lista os grupos de permissões (câmera, localização, contatos...).",
         "shell pm list permission-groups", ""),
        ("adb shell pm list permissions -g -d", "Lista as permissões perigosas (-d) por grupo (-g). Outras opções: -f "
         "tudo sobre cada uma, -s resumo, -u só as que aparecem para o usuário.", "shell pm list permissions -g -d",
         ""),
        ("adb shell pm list features", "Lista os recursos do aparelho (câmera, NFC, sensores, Wi-Fi...).",
         "shell pm list features", ""),
        ("adb shell pm list libraries", "Lista as bibliotecas compartilhadas que o aparelho oferece aos apps.",
         "shell pm list libraries", ""),
        ("adb shell pm list users", "Lista os usuários do aparelho (o principal, perfil de trabalho, convidado...).",
         "shell pm list users", ""),
        ("adb shell pm path <pacote>", "Mostra onde fica o APK de um app.", "shell pm path {pacote}", ""),
        ("adb shell pm clear <pacote>", "Apaga TODOS os dados de um app (login, arquivos, configurações), como se ele "
         "tivesse acabado de ser instalado.", "shell pm clear {pacote}", "perigoso"),
        ("adb shell pm disable-user --user 0 <pacote>", "Desativa (congela) um app para o seu usuário, sem "
         "desinstalar. Volta com pm enable.", "shell pm disable-user --user 0 {pacote}", "perigoso"),
        ("adb shell pm enable <pacote>", "Reativa um app ou componente desativado.", "shell pm enable {pacote}", ""),
        ("adb shell pm grant <pacote> <permissão>", "Concede uma permissão a um app (ex.: "
         "android.permission.WRITE_SECURE_SETTINGS para apps de automação).", "shell pm grant {pacote} {permissao}",
         ""),
        ("adb shell pm revoke <pacote> <permissão>", "Tira uma permissão de um app.",
         "shell pm revoke {pacote} {permissao}", ""),
        ("adb shell pm uninstall -k --user 0 <pacote>", "Remove o app só para o seu usuário (bom para bloatware); -k "
         "guarda os dados e o cache. Volta com cmd package install-existing <pacote>.",
         "shell pm uninstall -k --user 0 {pacote}", "perigoso"),
        ("adb shell pm get-install-location", "Mostra onde os apps novos são instalados: 0 automático, 1 memória "
         "interna, 2 externa.", "shell pm get-install-location", ""),
        ("adb shell pm set-install-location <0|1|2>", "Muda o local padrão de instalação. A documentação avisa que é "
         "só para depuração e pode quebrar apps.", None, ""),
        ("adb shell pm trim-caches <espaço>", "Apaga arquivos de cache dos apps até sobrar o espaço livre pedido "
         "(ex.: 2G).", "shell pm trim-caches {espaco}", ""),
        ("adb shell pm get-max-users", "Mostra quantos usuários o aparelho aceita.", "shell pm get-max-users", ""),
        ("adb shell pm get-app-links <pacote>", "Mostra os links de sites que um app abre direto (App Links) e se estão "
         "verificados.", "shell pm get-app-links {pacote}", ""),
        ("adb shell pm create-user / remove-user", "Cria um usuário novo no aparelho, ou apaga um usuário com TODOS "
         "os dados dele. Prefira as configurações do Android.", None, ""),
        ("adb shell pm set-permission-enforced", "Liga ou desliga a exigência de uma permissão no sistema todo. Só "
         "para testes.", None, ""),
    ]),
    "🚀 Gerenciador de atividades (am)": ("Abrir telas e links, parar apps, mandar avisos e ver travamentos.", [
        ("adb shell am start -a VIEW -d <link>", "Abre um link (site, mapa, tel:, mailto:...) no app padrão: é o "
         "exemplo da documentação, am start -a android.intent.action.VIEW.",
         "shell am start -a android.intent.action.VIEW -d {link}", ""),
        ("adb shell am start -W -n <componente>", "Abre uma tela específica de um app pelo componente "
         "(pacote/.Atividade). Opções: -W espera abrir, -S força a parada antes, -R <n> repete, -D liga a depuração, "
         "--user escolhe o usuário.", "shell am start -W -n {componente}", ""),
        ("adb shell am force-stop <pacote>", "Força a parada de tudo o que é de um app.",
         "shell am force-stop {pacote}", ""),
        ("adb shell am kill <pacote>", "Encerra só os processos do app que podem ser encerrados sem atrapalhar, como "
         "o Android faz para liberar memória.", "shell am kill {pacote}", ""),
        ("adb shell am kill-all", "Encerra todos os processos em segundo plano (apps abertos em segundo plano "
         "recomeçam do zero).", "shell am kill-all", "perigoso"),
        ("adb shell am broadcast -a <ação>", "Manda um aviso (broadcast) para os apps; por padrão vai para todos os "
         "usuários. Os avisos do sistema são protegidos e o Android recusa.", "shell am broadcast -a {acao}", ""),
        ("adb shell am monitor", "Acompanha ao vivo os travamentos (crash) e os 'não está respondendo' (ANR) dos apps. "
         "Ctrl+C para sair.", "shell am monitor", ""),
        ("adb shell am to-uri -a VIEW -d <link>", "Mostra um intent escrito como URI (bom para atalhos e automação).",
         "shell am to-uri -a android.intent.action.VIEW -d {link}", ""),
        ("adb shell am to-intent-uri -a VIEW -d <link>", "Igual ao anterior, no formato intent: (o que as páginas "
         "usam para abrir apps).", "shell am to-intent-uri -a android.intent.action.VIEW -d {link}", ""),
        ("adb shell am clear-debug-app", "Desfaz o set-debug-app (o app volta a abrir sem esperar o depurador).",
         "shell am clear-debug-app", ""),
        ("adb shell am set-debug-app -w <pacote>", "Marca um app para depuração: -w faz ele parar esperando o "
         "depurador ao abrir e --persistent mantém a marcação. Sem um depurador o app fica travado na abertura.",
         None, ""),
        ("adb shell am display-size / display-density", "Muda a resolução ou a densidade da tela. Use 🖥️ Resolução "
         "da tela (Celular e sistema): ela volta sozinha em 1 minuto se ficar ruim.", None, ""),
        ("adb shell am screen-compat on|off <pacote>", "Liga ou desliga o modo de compatibilidade de tela de apps "
         "antigos.", None, ""),
        ("adb shell am startservice <intent>", "Inicia um serviço de um app (precisa saber o componente do serviço).",
         None, ""),
        ("adb shell am instrument <componente>", "Roda os testes instrumentados de um app (pacote_de_teste/runner). "
         "Opções: -w espera terminar, -r resultado bruto, -e nome valor, -p arquivo de perfil.", None, ""),
        ("adb shell am profile start|stop <processo>", "Liga e desliga o profiler de um processo, gravando num "
         "arquivo.", None, ""),
        ("adb shell am dumpheap <processo> <arquivo>", "Salva a memória (heap) de um processo num arquivo; -n salva a "
         "memória nativa.", None, ""),
        ("adb shell am dumpbitmaps", "Mostra os bitmaps na memória dos apps (Android 16+); -d salva as imagens num "
         ".zip.", None, ""),
        ("adb shell am memory-limiter", "Ajusta os limites de memória dos apps (Android 17+).", None, ""),
        ("Argumentos de intent (-a, -d, -n, --es...)", "start, startservice, broadcast, to-uri e to-intent-uri "
         "aceitam: -a ação, -d endereço (URI), -t tipo MIME, -c categoria, -n componente, -f flags, extras como --es "
         "chave texto, --ez chave true/false, --ei chave número, e flags como --activity-clear-top.", None, ""),
    ]),
    "🏢 Política do dispositivo (dpm)": ("Comandos para apps de administração (empresas e testes): só consulta.", [
        ("adb shell dpm set-active-admin <componente>", "Define um app como administrador ativo do aparelho.", None,
         ""),
        ("adb shell dpm set-profile-owner <componente>", "Define um app como dono do perfil (perfil de trabalho).",
         None, ""),
        ("adb shell dpm set-device-owner <componente>", "Define um app como dono do aparelho (controle total, usado "
         "por empresas). Difícil de desfazer.", None, ""),
        ("adb shell dpm remove-active-admin <componente>", "Remove um administrador (e o dono do aparelho ou do "
         "perfil). Só funciona se o app tiver android:testOnly.", None, ""),
        ("adb shell dpm clear-freeze-period-record", "Apaga o registro dos períodos de congelamento de atualizações "
         "do sistema (Android 9+).", None, ""),
        ("adb shell dpm force-network-logs", "Libera os registros de rede para o app administrador (Android 9+), com "
         "limite de uso.", None, ""),
        ("adb shell dpm force-security-logs", "Libera os registros de segurança para o app administrador "
         "(Android 9+), com limite de uso.", None, ""),
    ]),
    "📸 Print e gravação da tela": ("Tirar print e gravar vídeo da tela (vão para a pasta Download).", [
        ("adb shell screencap <arquivo.png>", "Tira um print da tela. Aqui ele vai para a pasta Download do celular "
         "(print_<data>.png).", "shell screencap -p /sdcard/Download/print_{agora}.png", ""),
        ("adb shell screenrecord --time-limit <s> <arquivo>", "Grava a tela em vídeo, sem som, pelo tempo pedido "
         "(até 180 s), na pasta Download. Outras opções: --size LxA, --bit-rate (padrão 20 Mbps), --rotate e "
         "--verbose.", "shell screenrecord --time-limit {segundos} /sdcard/Download/tela_{agora}.mp4", ""),
        ("adb shell screenrecord --help", "Mostra todas as opções do gravador de tela.", "shell screenrecord --help",
         ""),
    ]),
    "🔧 Portas, diagnóstico e testes": ("Encaminhar portas, ler o log, o estado do sistema e perfis de apps.", [
        ("adb forward tcp:<porta> tcp:<porta>", "Encaminha uma porta daqui para uma porta do celular (ex.: tcp:6100 "
         "tcp:7100). Com local:logd no lugar da segunda, o que chegar vai para o log do sistema.",
         "forward tcp:{porta} tcp:{porta_celular}", ""),
        ("adb forward --list", "Lista os encaminhamentos de porta ativos.", "forward --list", "local"),
        ("adb forward --remove-all", "Desfaz todos os encaminhamentos de porta.", "forward --remove-all", "local"),
        ("adb logcat -d -t 200", "Mostra as últimas 200 linhas do log do sistema (o logcat tem uma página própria na "
         "documentação).", "logcat -d -t 200", ""),
        ("adb shell dumpsys <serviço>", "Mostra o estado de um serviço do sistema: battery (bateria), wifi, meminfo "
         "(memória), cpuinfo, display... A lista completa sai com dumpsys -l.", "shell dumpsys {servico}", ""),
        ("adb shell cmd package dump-profiles <pacote>", "Gera em texto o perfil ART de um app "
         "(/data/misc/profman/<pacote>.prof.txt). Para copiar o arquivo depois, precisa de root.",
         "shell cmd package dump-profiles {pacote}", ""),
        ("adb shell cmd testharness enable", "Modo de teste: APAGA o aparelho e o deixa como novo (só mantém a chave "
         "de depuração), pula o assistente inicial e desliga a tela de bloqueio, as atualizações e a sincronização.",
         None, ""),
        ("adb shell sqlite3 <banco.db>", "Abre um banco SQLite de um app (em /data/data/<pacote>/databases); .dump "
         "mostra o conteúdo e .schema as tabelas. Precisa de root.", None, ""),
    ]),
    "💡 Dicas e variáveis": ("Aspas, variáveis de ambiente e opções avançadas do adb.", [
        ("Aspas nos comandos do shell", "Desde as Platform Tools 23 o adb trata os argumentos como o ssh: o que vai "
         "para o shell do Android leva aspas duplas por fora e simples por dentro. Ex.: adb shell setprop chave "
         "\"'duas palavras'\" (sem as de fora, falha).", None, ""),
        ("ANDROID_SERIAL", "Variável com a série do aparelho padrão; o -s passa por cima dela.", None, ""),
        ("ADB_TRACE=all", "Liga o registro detalhado do adb, para relatar problemas.", None, ""),
        ("ADB_MDNS=1 e ADB_MDNS_OPENSCREEN=0", "Ligam o mDNS (achar aparelhos na rede) e escolhem o backend "
         "libadbmdns, que é o padrão.", None, ""),
        ("ADB_LIBUSB", "Escolhe o backend USB (nativo ou libusb); desde o adb 34 o libusb é o padrão, menos no "
         "Windows.", None, ""),
        ("ADB_BURST_MODE=1", "Liga o modo Burst, experimental (adb 36+).", None, ""),
    ]),
}

# {nome} nos comandos: (pergunta, resposta sugerida). pacote, apk e apks abrem uma lista para escolher.
PARAMETROS_ADB = {
    "endereco": ("IP e porta (ex.: 192.168.0.10:41235)", None),
    "codigo": ("Código de pareamento (6 dígitos)", None),
    "no_termux": ("Arquivo ou pasta aqui no Termux", "~/storage/downloads"),
    "no_celular": ("Caminho no celular", "/sdcard/Download/"),
    "filtro": ("Texto no nome do app", "google"),
    "permissao": ("Permissão", "android.permission.POST_NOTIFICATIONS"),
    "espaco": ("Espaço livre desejado (ex.: 2G, 500M)", "2G"),
    "link": ("Link", "https://developer.android.com/tools/adb"),
    "componente": ("Componente (pacote/.Atividade)", "com.android.settings/.Settings"),
    "acao": ("Ação do aviso", "com.exemplo.TESTE"),
    "segundos": ("Duração em segundos (1 a 180)", "30"),
    "porta": ("Porta aqui no Termux", "8080"),
    "porta_celular": ("Porta no celular", "8080"),
    "servico": ("Serviço (battery, wifi, meminfo, cpuinfo, display...)", "battery"),
}


def _valor_parametro_adb(nome: str, serial: str | None):
    """Pergunta um {nome} do comando: texto, ou uma lista (apks). None = cancelou."""
    if nome == "agora":
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    if nome == "pacote":
        return _escolher_app_android("adb", serial, todos=True)
    if nome == "apk":
        apk = escolher_arquivo("Qual APK?", (".apk",))
        return str(apk) if apk else None
    if nome == "apks":
        return [str(p) for p in escolher_arquivos("Quais APKs? (Espaço marca)", (".apk", ".apks"))] or None
    pergunta, sugestao = PARAMETROS_ADB[nome]
    valor = perguntar(pergunta, sugestao).strip()
    return os.path.expanduser(valor) if nome == "no_termux" else (valor or None)


def comando_adb(comando: str, descricao: str, modelo: str | None, marca: str) -> None:
    """Tela de um comando: a descrição e, se dá para rodar daqui, roda perguntando o que faltar."""
    for linha in textwrap.wrap(descricao, max(20, min(largura_tela(), 80) - 2)):
        print(linha)
    print(f"\n{DIM}Comando:{RST} {NEG}{comando}{RST}")
    if modelo is None:
        info("Este fica só para consulta: não roda por aqui.")
        return
    if "perigoso" in marca:
        aviso("Leia a descrição acima antes: esse comando muda o celular.")
    if not confirmar("Rodar agora?", "perigoso" not in marca) or not garantir_adb():
        return
    serial = None if "local" in marca else adb_alvo()
    valores = {}
    for _, nome, _, _ in string.Formatter().parse(modelo):
        if nome and nome not in valores:
            valores[nome] = _valor_parametro_adb(nome, serial)
            if valores[nome] is None:
                return
    preenchido = modelo.format(**{nome: " ".join(map(shlex.quote, v)) if isinstance(v, list) else shlex.quote(v)
                                  for nome, v in valores.items()})
    # "shell ..." vai inteiro para o shell do Android, com as aspas: assim um valor com espaço não se parte
    argumentos = ["shell", preenchido[6:]] if preenchido.startswith("shell ") else shlex.split(preenchido)
    rodar(["adb", *(["-s", serial] if serial else []), *argumentos])


def _menu_categoria_adb(nome: str) -> None:
    _, comandos = COMANDOS_ADB[nome]
    menu(nome, [(cmd, lambda e=(cmd, desc, modelo, marca): comando_adb(*e)) for cmd, desc, modelo, marca in comandos],
         descricoes=[desc for _, desc, _, _ in comandos])


@submenu
def menu_comandos_adb():
    menu("📖 Comandos do ADB", [(f"{nome} ({len(cmds)})", submenu(lambda n=nome: _menu_categoria_adb(n)))
                               for nome, (_, cmds) in COMANDOS_ADB.items()],
         descricoes=[desc for desc, _ in COMANDOS_ADB.values()],
         cabecalho=lambda: print(f"{DIM}Da documentação oficial do adb. Escolha um para ver a descrição e rodar "
                                 f"(precisa estar conectado pela depuração sem fio).{RST}"))


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
#  Ajudantes das ferramentas novas (menus 20 a 25)
# ════════════════════════════════════════════════════════════════════

NOTAS_DIR = DATA_DIR / "notas"
LEMBRETES_FILE = DATA_DIR / "lembretes.json"
AGENDA_FILE = DATA_DIR / "agenda.json"
GASTOS_FILE = DATA_DIR / "gastos.json"
COFRE_FILE = DATA_DIR / "cofre.json"
CAMBIO_FILE = DATA_DIR / "cambio.json"
POMODORO_FILE = DATA_DIR / "pomodoro.json"

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
         "outubro", "novembro", "dezembro"]
DIAS_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def pasta_saida(*sub: str) -> Path:
    """Onde salvar o que a pessoa vai querer abrir: Downloads/Termux-Toons (ou ~/.termux_toons/saida)."""
    base = DOWNLOADS / "Termux-Toons" if DOWNLOADS.exists() else DATA_DIR / "saida"
    pasta = base.joinpath(*sub)
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _abridor(url: str):
    local = urllib.parse.urlsplit(url).hostname in ("127.0.0.1", "localhost")
    return _SEM_PROXY if local else urllib.request.build_opener()


def pedir_bytes(url: str, dados: bytes | None = None, cabecalhos: dict | None = None, timeout: float = 30,
                metodo: str | None = None) -> bytes:
    """Faz uma requisição HTTP e devolve o corpo. Erros viram ToonsError com uma mensagem legível."""
    req = urllib.request.Request(url, data=dados, method=metodo,
                                 headers={"User-Agent": USER_AGENT, **(cabecalhos or {})})
    host = urllib.parse.urlsplit(url).netloc
    try:
        with _abridor(url).open(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        detalhe = e.read()[:300].decode("utf-8", errors="replace").strip()
        raise ToonsError(f"HTTP {e.code} em {host}" + (f": {detalhe}" if detalhe else "")) from None
    except (OSError, ValueError) as e:
        raise ToonsError(f"Sem resposta de {host} ({getattr(e, 'reason', e)}). Está com internet?") from None


def pedir_json(url: str, dados=None, cabecalhos: dict | None = None, timeout: float = 30,
               metodo: str | None = None):
    """Chama uma API e devolve o JSON da resposta; `dados` (dict/list) vai como corpo JSON."""
    corpo = json.dumps(dados).encode() if dados is not None else None
    extra = {"Accept": "application/json", **({"Content-Type": "application/json"} if corpo else {})}
    bruto = pedir_bytes(url, corpo, {**extra, **(cabecalhos or {})}, timeout, metodo)
    try:
        return json.loads(bruto.decode("utf-8", errors="replace") or "null")
    except ValueError:
        raise ToonsError(f"Resposta inesperada de {urllib.parse.urlsplit(url).netloc}.") from None


def url_com(base: str, **params) -> str:
    """Monta uma URL com parâmetros (ignora os vazios)."""
    limpos = {k: v for k, v in params.items() if v not in (None, "")}
    return base + ("?" + urllib.parse.urlencode(limpos) if limpos else "")


def sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def contem(texto: str, termo: str) -> bool:
    """Busca sem diferenciar maiúsculas nem acentos."""
    return sem_acento(termo).lower() in sem_acento(texto).lower()


def numero_br(v: float, casas: int = 6) -> str:
    """1234.5 → '1.234,5' (até `casas` decimais, sem zeros sobrando)."""
    if v != v or v in (float("inf"), float("-inf")):
        return str(v)
    if v and not 1e-4 <= abs(v) < 1e15:
        return f"{v:.4e}".replace(".", ",")
    texto = f"{v:,.{casas}f}".rstrip("0").rstrip(".") if casas else f"{v:,.0f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def ler_numero(msg: str, padrao=None, minimo: float | None = None) -> float:
    """Lê um número aceitando vírgula ('12,50') ou ponto e separador de milhar ('1.299,90')."""
    while True:
        texto = perguntar(msg, padrao)
        valor = parse_preco(texto) if re.search(r"\d", texto) else None
        if texto.strip().startswith("-") and valor is not None:
            valor = -valor
        if valor is None:
            erro("Digite um número (ex.: 12,50).")
        elif minimo is not None and valor < minimo:
            erro(f"O valor mínimo é {numero_br(minimo)}.")
        else:
            return valor


def copiar_texto(texto: str, avisar: bool = True) -> bool:
    """Copia para a área de transferência do Android (Termux:API)."""
    try:
        _tapi(["termux-clipboard-set"], 10, entrada=texto, json_saida=False)
    except ToonsError as e:
        aviso(f"Não consegui copiar ({e}).")
        return False
    if avisar:
        ok("Copiado para a área de transferência.")
    return True


def abrir_link(url: str) -> None:
    """Abre um link no navegador do Android."""
    for cmd in (["termux-open-url", url], ["xdg-open", url]):
        if tem(cmd[0]):
            rodar(cmd, capturar=True, timeout=20)
            return
    info(f"Abra no navegador: {url}")


def abrir_arquivo(caminho) -> None:
    """Abre um arquivo no app padrão do Android."""
    if tem("termux-open"):
        rodar(["termux-open", str(caminho)], capturar=True, timeout=20)
    else:
        info(f"Arquivo: {caminho}")


def notificar_seguro(titulo_n: str, texto: str, **extra) -> None:
    """Notificação que nunca derruba quem chamou (fora do Termux só imprime)."""
    try:
        notificar(titulo_n, texto, **extra)
    except ToonsError as e:
        log(f"Notificação falhou: {e}")


def _pastas_de_arquivos() -> list:
    """(pasta, profundidade) onde os arquivos da pessoa costumam estar."""
    s = HOME / "storage"
    pastas = [(s / "downloads", 3), (s / "dcim", 3), (s / "pictures", 3), (s / "music", 3), (s / "movies", 3),
              (s / "shared" / "Documents", 3), (s / "shared", 2), (HOME, 1)]
    return [(p, n) for p, n in pastas if p.exists()]


def listar_arquivos(extensoes: tuple = (), pastas: list | None = None, limite: int = 200) -> list:
    """Arquivos com essas extensões, os mais novos primeiro (sem repetir os que aparecem por dois caminhos)."""
    vistos, achados = set(), []
    for pasta, profundidade in pastas or _pastas_de_arquivos():
        pasta = Path(pasta)
        for raiz, dirs, arquivos in os.walk(pasta, onerror=lambda e: None):
            nivel = len(Path(raiz).relative_to(pasta).parts)
            dirs[:] = [] if nivel + 1 >= profundidade else \
                [d for d in dirs if not d.startswith(".") and d not in ("Android", "node_modules", "__pycache__")]
            for nome in arquivos:
                if nome.startswith(".") or (extensoes and not nome.lower().endswith(extensoes)):
                    continue
                caminho = Path(raiz) / nome
                try:
                    real, mtime = caminho.resolve(), caminho.stat().st_mtime
                except OSError:
                    continue
                if real not in vistos:
                    vistos.add(real)
                    achados.append((mtime, caminho))
    achados.sort(key=lambda par: par[0], reverse=True)
    return [c for _, c in achados[:limite]]


def _rotulo_arquivo(caminho: Path) -> str:
    try:
        quando = datetime.fromtimestamp(caminho.stat().st_mtime).strftime("%d/%m %H:%M")
        tamanho_txt = bytes_humanos(caminho.stat().st_size)
    except OSError:
        quando = tamanho_txt = "?"
    return f"{caminho.name}  {DIM}{tamanho_txt} · {quando} · {caminho.parent.name}{RST}"


def escolher_arquivo(msg: str, extensoes: tuple = (), pastas: list | None = None) -> Path | None:
    """Mostra os arquivos recentes (Downloads, DCIM...) e devolve o escolhido; dá para digitar o caminho."""
    arquivos = listar_arquivos(extensoes, pastas)
    opcoes = [_rotulo_arquivo(a) for a in arquivos] + ["Digitar o caminho do arquivo..."]
    if not arquivos:
        info(f"Nenhum arquivo {'/'.join(extensoes) or ''} encontrado nas pastas comuns.")
    i = escolher(msg, opcoes)
    if i is None:
        return None
    if i < len(arquivos):
        return arquivos[i]
    caminho = Path(os.path.expanduser(perguntar("Caminho do arquivo").strip().strip("'\"")))
    if not caminho.is_file():
        raise ToonsError(f"Arquivo não encontrado: {caminho}")
    return caminho


def escolher_arquivos(msg: str, extensoes: tuple = (), pastas: list | None = None) -> list:
    """Vários arquivos de uma vez (Espaço marca)."""
    arquivos = listar_arquivos(extensoes, pastas)
    if not arquivos:
        raise ToonsError(f"Nenhum arquivo {'/'.join(extensoes)} encontrado nas pastas comuns.")
    return [arquivos[i] for i in escolher_varios(msg, [_rotulo_arquivo(a) for a in arquivos])]


def editar_texto(inicial: str = "", sufixo: str = ".md") -> str | None:
    """Texto longo: abre o nano (ou $EDITOR); sem editor, lê linhas até uma linha só com '.'."""
    editor = os.environ.get("EDITOR") or ("nano" if tem("nano") else "vim" if tem("vim") else "")
    if editor and sys.stdin.isatty():
        pasta = DATA_DIR / "tmp"
        pasta.mkdir(parents=True, exist_ok=True)
        arq = pasta / f"texto_{os.getpid()}{sufixo}"
        arq.write_text(inicial, "utf-8")
        if "nano" in editor:
            info("No nano: escreva, depois Ctrl+O e Enter para salvar e Ctrl+X para sair.")
            time.sleep(1.2)
        try:
            rodar(shlex.split(editor) + [str(arq)], mostrar=False)
            return arq.read_text("utf-8")
        finally:
            arq.unlink(missing_ok=True)
    info("Digite o texto. Para terminar, digite uma linha só com um ponto (.)")
    linhas = []
    while True:
        try:
            linha = input()
        except EOFError:
            break
        if linha.strip() == ".":
            break
        linhas.append(linha)
    return "\n".join(linhas) if linhas else (inicial or None)


def ler_linhas(msg: str) -> str:
    """Lê várias linhas no próprio terminal até uma linha vazia."""
    info(f"{msg} (linha vazia termina)")
    linhas = []
    while True:
        try:
            linha = input(f"{DIM}…{RST} ")
        except EOFError:
            break
        if not linha.strip():
            break
        linhas.append(linha)
    return "\n".join(linhas)


class TelaCheia:
    """Tela alternativa do terminal, teclas lidas sem Enter e cursor escondido; tudo volta ao sair."""

    def __enter__(self):
        if not setas_ativas():
            raise ToonsError("Isto precisa de um terminal interativo (abra pelo Termux).")
        self.fd = sys.stdin.fileno()
        self.antigo = termios.tcgetattr(self.fd)
        sys.stdout.write("\033[?1049h\033[?25l")
        sys.stdout.flush()
        tty.setcbreak(self.fd)
        return self

    def __exit__(self, *erro_info):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.antigo)
        sys.stdout.write("\033[?25h\033[?1049l")
        sys.stdout.flush()
        return False

    @contextlib.contextmanager
    def normal(self):
        """Volta ao terminal normal por um instante (para perguntar algo com Enter)."""
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.antigo)
        sys.stdout.write("\033[?25h\033[?1049l")
        sys.stdout.flush()
        try:
            yield
        finally:
            sys.stdout.write("\033[?1049h\033[?25l")
            sys.stdout.flush()
            tty.setcbreak(self.fd)


def desenhar(linhas: list) -> None:
    """Redesenha a tela inteira (sem quebra depois da última linha, para não rolar)."""
    colunas, altura = shutil.get_terminal_size((60, 24))
    linhas = [_cortar(linha, colunas) for linha in linhas[:altura]]
    sys.stdout.write("\033[H" + "\033[K\n".join(linhas) + "\033[K\033[J")
    sys.stdout.flush()


def tecla_ou_nada(espera: float) -> str | None:
    """Uma tecla, se alguém apertar dentro de `espera` segundos (use dentro de TelaCheia)."""
    if select.select([sys.stdin], [], [], espera)[0]:
        return ler_tecla()
    return None


_DIGITOS_GRANDES = {
    "0": ("███", "█ █", "█ █", "█ █", "███"), "1": (" █ ", "██ ", " █ ", " █ ", "███"),
    "2": ("███", "  █", "███", "█  ", "███"), "3": ("███", "  █", "███", "  █", "███"),
    "4": ("█ █", "█ █", "███", "  █", "  █"), "5": ("███", "█  ", "███", "  █", "███"),
    "6": ("███", "█  ", "███", "█ █", "███"), "7": ("███", "  █", "  █", "  █", "  █"),
    "8": ("███", "█ █", "███", "█ █", "███"), "9": ("███", "█ █", "███", "  █", "███"),
    ":": (" ", "█", " ", "█", " "), ".": (" ", " ", " ", " ", "█"), "-": ("   ", "   ", "███", "   ", "   "),
    " ": ("  ",) * 5,
}


def numeros_grandes(texto: str) -> list:
    """'12:34' em algarismos de 5 linhas feitos de blocos."""
    linhas = [""] * 5
    for ch in texto:
        desenho = _DIGITOS_GRANDES.get(ch, ("   ",) * 5)
        for i in range(5):
            linhas[i] += desenho[i] + " "
    return [linha.rstrip() for linha in linhas]


def parse_duracao(texto: str, unidade_padrao: str = "m") -> int:
    """'25' (minutos), '90s', '1h30m', '1h 30min', '10:00' (mm:ss) → segundos."""
    t = sem_acento(texto).strip().lower().replace(" ", "")
    if re.fullmatch(r"\d+:\d{1,2}(:\d{1,2})?", t):
        segundos = 0
        for parte in t.split(":"):
            segundos = segundos * 60 + int(parte)
        return segundos
    if re.fullmatch(r"\d+(?:[.,]\d+)?", t):
        return int(float(t.replace(",", ".")) * {"s": 1, "m": 60, "h": 3600}[unidade_padrao])
    padrao = r"(\d+(?:[.,]\d+)?)(horas?|h|minutos?|mins?|m|segundos?|seg|s)"
    if not t or not re.fullmatch(f"(?:{padrao})+", t):
        raise ToonsError("Não entendi o tempo. Exemplos: 25 (minutos), 90s, 1h30m, 10:00.")
    total = 0.0
    for numero, unidade in re.findall(padrao, t):
        total += float(numero.replace(",", ".")) * {"h": 3600, "m": 60, "s": 1}[unidade[0]]
    return int(total)


def fmt_relogio(segundos: float, decimos: bool = False) -> str:
    segundos = max(0.0, segundos)
    h, resto = divmod(int(segundos), 3600)
    m, s = divmod(resto, 60)
    texto = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    return texto + (f".{int(segundos * 10) % 10}" if decimos else "")


def tempo_ate(quando: datetime, agora: datetime | None = None) -> str:
    """'em 2 h 5 min', 'em 3 dias', 'há 10 min'."""
    diferenca = (quando - (agora or datetime.now())).total_seconds()
    passado, s = diferenca < 0, abs(int(diferenca))
    if s < 60:
        texto = "menos de 1 min"
    elif s < 3600:
        texto = f"{s // 60} min"
    elif s < 86400:
        texto = f"{s // 3600} h" + (f" {s % 3600 // 60} min" if s % 3600 >= 60 else "")
    else:
        texto = f"{s // 86400} dia{'s' if s >= 172800 else ''}"
    return f"há {texto}" if passado else f"em {texto}"


def barra_horizontal(frac: float, largura: int = 20) -> str:
    cheio = max(0, min(largura, round(frac * largura)))
    return "█" * cheio + "░" * (largura - cheio)


# ════════════════════════════════════════════════════════════════════
#  20. Utilitários
# ════════════════════════════════════════════════════════════════════

# ── Bloco de notas ───────────────────────────────────────────────────

def _slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", sem_acento(texto).lower()).strip("-")[:40] or "nota"


def ler_nota(arq: Path) -> dict:
    linhas = arq.read_text("utf-8", errors="replace").splitlines()
    titulo_n = linhas[0].lstrip("#").strip() if linhas else ""
    tags, inicio = [], 1
    if len(linhas) > 1 and linhas[1].lower().startswith("tags:"):
        tags, inicio = [t.strip() for t in linhas[1][5:].split(",") if t.strip()], 2
    return {"arq": arq, "titulo": titulo_n or arq.stem, "tags": tags,
            "corpo": "\n".join(linhas[inicio:]).strip("\n"), "mtime": arq.stat().st_mtime}


def listar_notas() -> list:
    notas = []
    for arq in NOTAS_DIR.glob("*.md") if NOTAS_DIR.exists() else []:
        with contextlib.suppress(OSError):
            notas.append(ler_nota(arq))
    return sorted(notas, key=lambda n: n["mtime"], reverse=True)


def salvar_nota(titulo_n: str, corpo: str, tags=(), arq: Path | None = None) -> Path:
    """Grava uma nota em Markdown (usada também pelo OCR, ditado e IA)."""
    NOTAS_DIR.mkdir(parents=True, exist_ok=True)
    arq = arq or NOTAS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-{_slug(titulo_n)}.md"
    cabeca = f"# {titulo_n.strip() or 'Sem título'}\n" + (f"tags: {', '.join(tags)}\n" if tags else "")
    arq.write_text(cabeca + "\n" + (corpo or "").strip() + "\n", "utf-8")
    return arq


@submenu
def menu_notas():
    def ler_tags(padrao: str = "") -> list:
        return [t.strip() for t in perguntar("Tags separadas por vírgula (opcional)", padrao).split(",") if t.strip()]

    def nova():
        titulo_n = perguntar("Título da nota")
        if not titulo_n:
            return
        tags = ler_tags()
        corpo = editar_texto()
        if not (corpo or "").strip() and not confirmar("A nota ficou vazia. Salvar mesmo assim?", False):
            return
        ok(f"Nota salva: {salvar_nota(titulo_n, corpo or '', tags).name}")

    def abrir(nota: dict):
        while True:
            limpar()
            titulo(nota["titulo"])
            data_n = datetime.fromtimestamp(nota["mtime"]).strftime("%d/%m/%Y %H:%M")
            print(f"{DIM}{data_n}{' · tags: ' + ', '.join(nota['tags']) if nota['tags'] else ''}{RST}\n")
            print(nota["corpo"] or f"{DIM}(vazia){RST}")
            print()
            acoes = ["Editar o texto", "Mudar título e tags", "Copiar o texto", "Ouvir (ler em voz alta)",
                     "Exportar para Downloads", "Apagar", "Voltar"]
            i = escolher("O que fazer?", acoes)
            if i in (None, 6):
                return
            if i == 0:
                novo = editar_texto(nota["corpo"])
                if novo is not None:
                    salvar_nota(nota["titulo"], novo, nota["tags"], nota["arq"])
            elif i == 1:
                novo_titulo = perguntar("Título", nota["titulo"])
                salvar_nota(novo_titulo, nota["corpo"], ler_tags(", ".join(nota["tags"])), nota["arq"])
            elif i == 2:
                copiar_texto(f"{nota['titulo']}\n\n{nota['corpo']}")
                pausar()
            elif i == 3:
                try:
                    falar(f"{nota['titulo']}. {nota['corpo']}")
                except ToonsError as e:
                    erro(str(e))
                    pausar()
            elif i == 4:
                destino = pasta_saida("Notas") / nota["arq"].name
                shutil.copy2(nota["arq"], destino)
                ok(f"Exportada: {destino}")
                pausar()
            elif i == 5:
                if confirmar(f"Apagar a nota '{nota['titulo']}'?", False):
                    nota["arq"].unlink(missing_ok=True)
                    ok("Nota apagada.")
                    return
            nota.update(ler_nota(nota["arq"]))

    def escolher_e_abrir(notas: list, msg: str = "Qual nota?"):
        if not notas:
            info("Nenhuma nota encontrada.")
            return
        rotulos = [f"{n['titulo']}  {DIM}{datetime.fromtimestamp(n['mtime']):%d/%m}"
                   f"{' · ' + ', '.join(n['tags']) if n['tags'] else ''}{RST}" for n in notas]
        i = escolher(msg, rotulos)
        if i is not None:
            abrir(notas[i])

    def buscar():
        termo = perguntar("Procurar por")
        if termo:
            escolher_e_abrir([n for n in listar_notas()
                              if contem(n["titulo"] + "\n" + n["corpo"] + " " + " ".join(n["tags"]), termo)])

    def por_tag():
        notas = listar_notas()
        contagem = {}
        for n in notas:
            for t in n["tags"]:
                contagem[t] = contagem.get(t, 0) + 1
        if not contagem:
            info("Nenhuma nota tem tags ainda.")
            return
        tags = sorted(contagem, key=str.lower)
        i = escolher("Qual tag?", [f"{t} ({contagem[t]})" for t in tags])
        if i is not None:
            escolher_e_abrir([n for n in notas if tags[i] in n["tags"]])

    def exportar_todas():
        notas = listar_notas()
        if not notas:
            info("Nenhuma nota para exportar.")
            return
        destino = pasta_saida() / f"notas_{datetime.now():%Y%m%d_%H%M}.zip"
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
            for n in notas:
                z.write(n["arq"], n["arq"].name)
        ok(f"{len(notas)} nota(s) exportada(s): {destino}")

    menu("📝 Bloco de notas", [
        ("Nova nota", nova),
        (lambda: f"Minhas notas ({len(listar_notas())})", lambda: escolher_e_abrir(listar_notas())),
        ("Buscar nas notas", buscar),
        ("Ver por tag", por_tag),
        ("Exportar todas (.zip em Downloads)", exportar_todas),
    ])


# ── Lembretes e alarmes ──────────────────────────────────────────────

REPETICOES = {"nao": "Não repetir", "diario": "Todo dia", "dias_uteis": "Dias úteis (segunda a sexta)",
              "semanal": "Toda semana", "mensal": "Todo mês"}


def parse_quando(texto: str, agora: datetime | None = None) -> datetime:
    """Entende '18:30', '18h', 'amanhã 7h', '25/12 08:00', '10min', 'em 2 horas', '+1d'."""
    agora = (agora or datetime.now()).replace(second=0, microsecond=0)
    t = re.sub(r"\s+", " ", sem_acento(texto).strip().lower())
    # relativo: '+2h', 'em 2 horas', '10min', '3 dias' (um '7h' sozinho é horário, não 'daqui a 7 horas')
    m = re.fullmatch(r"(\+|em |daqui (?:a )?)?\s*(\d+)\s*(s|seg|segundos?|m|min|minutos?|h|horas?|d|dias?)", t)
    if m and (m.group(1) or m.group(3) != "h"):
        unidade = {"s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(3)[0]]
        return (datetime.now() + timedelta(seconds=int(m.group(2)) * unidade)).replace(microsecond=0)
    dia = None
    m = re.match(r"(hoje|amanha|depois de amanha)\b\s*(?:as\s*|a\s*)?", t)
    if m:
        dia = agora.date() + timedelta(days={"hoje": 0, "amanha": 1, "depois de amanha": 2}[m.group(1)])
        t = t[m.end():]
    else:
        m = re.match(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\s*(?:as\s*)?", t)
        if m:
            ano = int(m.group(3)) if m.group(3) else agora.year
            ano += 2000 if ano < 100 else 0
            try:
                dia = date(ano, int(m.group(2)), int(m.group(1)))
            except ValueError:
                raise ToonsError("Data inválida.") from None
            if not m.group(3) and dia < agora.date():
                dia = dia.replace(year=ano + 1)  # '05/01' digitado em dezembro é do ano que vem
            t = t[m.end():]
    t = t.strip()
    hora = minuto = None
    if t:
        m = re.fullmatch(r"(\d{1,2})(?:[:h](\d{2})?)?(?:min)?", t)
        if not m:
            raise ToonsError("Não entendi. Exemplos: 18:30 · 7h · amanhã 7h · 25/12 08:00 · 10min · em 2 horas")
        hora, minuto = int(m.group(1)), int(m.group(2) or 0)
        if hora > 23 or minuto > 59:
            raise ToonsError("Hora inválida.")
    if dia is None and hora is None:
        raise ToonsError("Diga quando: 18:30, amanhã 7h, 25/12 08:00, 10min...")
    if hora is None:
        hora, minuto = 9, 0
    quando = datetime.combine(dia or agora.date(), datetime.min.time()).replace(hour=hora, minute=minuto)
    if dia is None and quando <= agora:
        quando += timedelta(days=1)  # '7h' já passou hoje: é amanhã
    return quando


def proxima_vez(quando: datetime, repetir: str, agora: datetime, dia_mes: int | None = None) -> datetime | None:
    """Próxima ocorrência de um lembrete que se repete (None se não repete)."""
    if repetir not in REPETICOES or repetir == "nao":
        return None
    while quando <= agora:
        if repetir == "diario":
            quando += timedelta(days=1)
        elif repetir == "semanal":
            quando += timedelta(weeks=1)
        elif repetir == "dias_uteis":
            quando += timedelta(days=1)
            while quando.weekday() >= 5:
                quando += timedelta(days=1)
        else:
            ano, mes = (quando.year + 1, 1) if quando.month == 12 else (quando.year, quando.month + 1)
            dia_alvo = min(dia_mes or quando.day, calendar.monthrange(ano, mes)[1])
            quando = quando.replace(year=ano, month=mes, day=dia_alvo)
    return quando


def lembretes() -> list:
    return sorted(ler_json(LEMBRETES_FILE, []), key=lambda lem: lem["quando"])


def adicionar_lembrete(texto: str, quando: datetime, repetir: str = "nao", alarme: bool = False,
                       falar_texto: bool = False) -> dict:
    lista = ler_json(LEMBRETES_FILE, [])
    lem = {"id": uuid.uuid4().hex[:8], "texto": texto, "quando": quando.isoformat(), "repetir": repetir,
           "alarme": alarme, "falar": falar_texto, "dia_mes": quando.day}
    lista.append(lem)
    gravar_json(LEMBRETES_FILE, lista)
    return lem


def disparar_lembrete(lem: dict, atrasado: bool = False) -> None:
    texto = ("(atrasado) " if atrasado else "") + lem["texto"]
    log(f"{'Alarme' if lem.get('alarme') else 'Lembrete'}: {texto}")
    titulo_n = "⏰ Alarme" if lem.get("alarme") else "🔔 Lembrete"
    if tem("termux-notification"):
        with contextlib.suppress(ToonsError):
            _tapi(["termux-notification", "--title", titulo_n, "--content", texto, "--id", f"lembrete{lem['id']}",
                   "--sound", "--priority", "high", "--vibrate", "500,300,500,300,500"], 15, json_saida=False)
    else:
        print(f"[{titulo_n}] {texto}")
    if lem.get("alarme") and not atrasado:
        for _ in range(6):
            with contextlib.suppress(ToonsError):
                vibrar(700)
            time.sleep(1.2)
    if (lem.get("falar") or lem.get("alarme")) and not atrasado:
        with contextlib.suppress(ToonsError):
            falar(lem["texto"])


def rodar_lembretes() -> None:
    """Laço do serviço de lembretes (roda dentro do tmux)."""
    log("Serviço de lembretes iniciado.")
    while True:
        agora = datetime.now()
        mudancas = {}
        for lem in ler_json(LEMBRETES_FILE, []):
            quando = datetime.fromisoformat(lem["quando"])
            if quando > agora:
                continue
            disparar_lembrete(lem, atrasado=agora - quando > timedelta(minutes=30))
            mudancas[lem["id"]] = proxima_vez(quando, lem.get("repetir", "nao"), agora, lem.get("dia_mes"))
        if mudancas:
            # relê o arquivo antes de gravar: o menu pode ter mudado algo enquanto o alarme tocava
            atual = []
            for lem in ler_json(LEMBRETES_FILE, []):
                if lem["id"] in mudancas:
                    if mudancas[lem["id"]] is None:
                        continue
                    lem["quando"] = mudancas[lem["id"]].isoformat()
                atual.append(lem)
            gravar_json(LEMBRETES_FILE, atual)
        time.sleep(10)


def _garantir_servico_lembretes() -> None:
    if not servico_ativo("lembretes") and confirmar("O serviço de lembretes está parado. Iniciar agora?", True):
        iniciar_servico("lembretes", cmd_self("lembretes"), reiniciar=True)


@submenu
def menu_lembretes():
    def novo(alarme: bool):
        texto = perguntar("Mensagem do alarme" if alarme else "Lembrar de quê?", "Alarme" if alarme else None)
        if not texto:
            return
        quando = parse_quando(perguntar("Quando? (18:30 · amanhã 7h · 25/12 08:00 · 10min · em 2 horas)"))
        chaves = list(REPETICOES)
        i = escolher("Repetir?", list(REPETICOES.values()), 1)
        repetir = chaves[i] if i is not None else "nao"
        falar_texto = not alarme and confirmar("Falar o lembrete em voz alta também?", False)
        adicionar_lembrete(texto, quando, repetir, alarme, falar_texto)
        ok(f"{'Alarme' if alarme else 'Lembrete'} para {quando:%d/%m %H:%M} ({tempo_ate(quando)}).")
        _garantir_servico_lembretes()

    def listar():
        lista = lembretes()
        if not lista:
            info("Nenhum lembrete.")
            return
        for lem in lista:
            quando = datetime.fromisoformat(lem["quando"])
            icone = "⏰" if lem.get("alarme") else "🔔"
            rep = "" if lem.get("repetir", "nao") == "nao" else f" {DIM}({REPETICOES[lem['repetir']].lower()}){RST}"
            print(f"  {icone} {NEG}{quando:%d/%m %H:%M}{RST} {DIM}{tempo_ate(quando)}{RST}  {lem['texto']}{rep}")
        print(f"\nServiço: {'RODANDO' if servico_ativo('lembretes') else 'PARADO (os lembretes não tocam)'}")

    def apagar_lembrete():
        lista = lembretes()
        if not lista:
            info("Nenhum lembrete.")
            return
        marcados = escolher_varios("Apagar quais?", [f"{datetime.fromisoformat(l['quando']):%d/%m %H:%M}  {l['texto']}"
                                                     for l in lista])
        ids = {lista[i]["id"] for i in marcados}
        if ids:
            gravar_json(LEMBRETES_FILE, [l for l in ler_json(LEMBRETES_FILE, []) if l["id"] not in ids])
            ok(f"{len(ids)} apagado(s).")

    def testar():
        disparar_lembrete({"id": "teste", "texto": "Teste de alarme do Termux-Toons", "alarme": True})

    menu("⏰ Lembretes e alarmes", [
        ("Novo lembrete", lambda: novo(False)),
        ("Novo alarme (toca, vibra e fala)", lambda: novo(True)),
        (lambda: f"Ver lembretes ({len(lembretes())})", listar),
        ("Apagar lembretes", apagar_lembrete),
        ("Testar o alarme agora", testar),
        *itens_servico("lembretes", "Serviço de lembretes",
                       lambda: iniciar_servico("lembretes", cmd_self("lembretes"), reiniciar=True)),
    ])


# ── Cronômetro, timer e Pomodoro ─────────────────────────────────────

def _tela_relogio(nome: str, tempo_txt: str, extras: list, dica: str, destaque: bool = False) -> None:
    colunas, _ = shutil.get_terminal_size((60, 24))
    grandes = numeros_grandes(tempo_txt)
    if max(len(linha) for linha in grandes) > colunas - 2:
        grandes = [tempo_txt]
    cor = (INV if destaque else "") + NEG + (VERD if not destaque else "")
    linhas = ["", _centralizar(f"{NEG}{nome}{RST}", colunas), ""]
    linhas += [_centralizar(f"{cor}{linha}{RST}", colunas) for linha in grandes]
    linhas += [""] + [_centralizar(e, colunas) for e in extras] + ["", f"{DIM}{_centralizar(dica, colunas)}{RST}"]
    desenhar(linhas)


def _avisar_fim(titulo_n: str, texto: str) -> None:
    notificar_seguro(titulo_n, texto, som=True)
    with contextlib.suppress(ToonsError):
        vibrar(1000)
    sys.stdout.write("\a")


def cronometro() -> None:
    voltas, acumulado, inicio, rodando = [], 0.0, time.monotonic(), True
    with TelaCheia():
        while True:
            decorrido = acumulado + (time.monotonic() - inicio if rodando else 0)
            extras = [f"Volta {i}: {fmt_relogio(v, True)}  (+{fmt_relogio(v - (voltas[i - 2] if i > 1 else 0), True)})"
                      for i, v in enumerate(voltas, 1)][-8:]
            _tela_relogio("⌚ Cronômetro" + ("" if rodando else "  (pausado)"), fmt_relogio(decorrido, True),
                          extras, "Espaço pausa · Enter marca volta · r zera · Esc sai")
            tecla = tecla_ou_nada(0.1)
            if tecla in ("esc", "q"):
                break
            if tecla == " ":
                if rodando:
                    acumulado, rodando = decorrido, False
                else:
                    inicio, rodando = time.monotonic(), True
            elif tecla in ("enter", "v"):
                voltas.append(decorrido)
            elif tecla == "r":
                voltas, acumulado, inicio = [], 0.0, time.monotonic()
    print(f"Tempo: {fmt_relogio(decorrido, True)}" + (f" · {len(voltas)} volta(s)" if voltas else ""))


def temporizador(segundos: int | None = None) -> None:
    if segundos is None:
        segundos = parse_duracao(perguntar("Quanto tempo? (5 = 5 min · 90s · 1h30m · 10:00)", "5"))
    if segundos <= 0:
        raise ToonsError("O tempo precisa ser maior que zero.")
    with TelaCheia():
        fim, restante, pausado = time.monotonic() + segundos, float(segundos), False
        while True:
            if not pausado:
                restante = fim - time.monotonic()
            if restante <= 0:
                break
            _tela_relogio("⏳ Timer" + ("  (pausado)" if pausado else ""), fmt_relogio(restante + 0.999),
                          [f"de {fmt_relogio(segundos)}"], "Espaço pausa · + / - um minuto · Esc cancela")
            tecla = tecla_ou_nada(0.2)
            if tecla in ("esc", "q"):
                return
            if tecla == " ":
                pausado = not pausado
                fim = time.monotonic() + restante
            elif tecla in ("+", "-"):
                ajuste = 60 if tecla == "+" else -min(60, restante - 1)
                restante += ajuste
                fim += ajuste
        _avisar_fim("⏰ Tempo esgotado!", f"O timer de {fmt_relogio(segundos)} terminou.")
        t0, piscar = time.monotonic(), False
        while time.monotonic() - t0 < 120:
            piscar = not piscar
            _tela_relogio("⏰ TEMPO ESGOTADO!", "00:00", [], "Aperte qualquer tecla", destaque=piscar)
            if not piscar and time.monotonic() - t0 < 30:
                sys.stdout.write("\a")
                sys.stdout.flush()
            if tecla_ou_nada(0.5) is not None:
                break


def pomodoro() -> None:
    foco = perguntar_int("Minutos de foco", 25, 1, 180)
    pausa = perguntar_int("Minutos de pausa curta", 5, 1, 60)
    longa = perguntar_int("Minutos de pausa longa (a cada 4 focos)", 15, 1, 120)
    hoje = date.today().isoformat()
    estat = ler_json(POMODORO_FILE, {})
    feitos = 0
    fase, n_foco = "foco", 0
    with TelaCheia():
        while True:
            duracao = {"foco": foco, "pausa": pausa, "longa": longa}[fase] * 60
            nome = {"foco": "🍅 Foco", "pausa": "☕ Pausa curta", "longa": "🌴 Pausa longa"}[fase]
            fim, restante, pausado, pulou = time.monotonic() + duracao, float(duracao), False, False
            while restante > 0:
                if not pausado:
                    restante = fim - time.monotonic()
                total_hoje = estat.get(hoje, 0) + feitos
                _tela_relogio(f"{nome}{'  (pausado)' if pausado else ''}", fmt_relogio(max(0, restante) + 0.999),
                              [f"Pomodoros hoje: {'🍅' * min(total_hoje, 12)} {total_hoje}"],
                              "Espaço pausa · p pula a fase · Esc sai")
                tecla = tecla_ou_nada(0.3)
                if tecla in ("esc", "q"):
                    estat[hoje] = estat.get(hoje, 0) + feitos
                    gravar_json(POMODORO_FILE, estat)
                    print(f"Pomodoros concluídos agora: {feitos} (hoje: {estat[hoje]}).")
                    return
                if tecla == " ":
                    pausado = not pausado
                    fim = time.monotonic() + restante
                elif tecla == "p":
                    pulou = True
                    break
            if fase == "foco":
                if not pulou:
                    feitos += 1
                n_foco += 1
                fase = "longa" if n_foco % 4 == 0 else "pausa"
                _avisar_fim("🍅 Foco concluído!", "Hora da pausa.")
            else:
                fase = "foco"
                _avisar_fim("☕ Pausa terminou", "Hora de focar de novo.")


@submenu
def menu_relogio():
    menu("⏱️ Cronômetro, timer e Pomodoro", [
        ("Cronômetro (com voltas)", cronometro),
        ("Timer (contagem regressiva)", temporizador),
        ("Pomodoro (25 min foco / 5 min pausa)", pomodoro),
        ("Timer rápido: 1 minuto", lambda: temporizador(60)),
        ("Timer rápido: 5 minutos", lambda: temporizador(300)),
        ("Timer rápido: 10 minutos", lambda: temporizador(600)),
    ])


# ── Calendário e agenda ──────────────────────────────────────────────

def pascoa(ano: int) -> date:
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher)."""
    a, (b, c) = ano % 19, divmod(ano, 100)
    d, e = divmod(b, 4)
    g = (b - (b + 8) // 25 + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    return date(ano, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1)


def feriados(ano: int) -> dict:
    """Feriados nacionais do Brasil (e os pontos facultativos mais comuns)."""
    p = pascoa(ano)
    lista = {
        date(ano, 1, 1): "Confraternização Universal", date(ano, 4, 21): "Tiradentes",
        date(ano, 5, 1): "Dia do Trabalho", date(ano, 9, 7): "Independência do Brasil",
        date(ano, 10, 12): "Nossa Senhora Aparecida", date(ano, 11, 2): "Finados",
        date(ano, 11, 15): "Proclamação da República", date(ano, 12, 25): "Natal",
        p - timedelta(days=48): "Carnaval (ponto facultativo)", p - timedelta(days=47): "Carnaval (ponto facultativo)",
        p - timedelta(days=2): "Sexta-feira Santa", p: "Páscoa",
        p + timedelta(days=60): "Corpus Christi (ponto facultativo)",
    }
    if ano >= 2024:
        lista[date(ano, 11, 20)] = "Dia Nacional de Zumbi e da Consciência Negra"
    return lista


def eventos_do_dia(dia: date) -> list:
    return sorted(ler_json(AGENDA_FILE, {}).get(dia.isoformat(), []), key=lambda ev: ev.get("hora") or "")


def parse_data(texto: str, hoje: date | None = None) -> date:
    """'hoje', 'amanhã', '25/12', '25/12/2026' → data."""
    hoje = hoje or date.today()
    t = sem_acento(texto).strip().lower()
    if t in ("", "hoje"):
        return hoje
    if t == "amanha":
        return hoje + timedelta(days=1)
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", t)
    if not m:
        raise ToonsError("Data inválida. Use dd/mm ou dd/mm/aaaa.")
    ano = int(m.group(3)) if m.group(3) else hoje.year
    try:
        return date(ano + (2000 if ano < 100 else 0), int(m.group(2)), int(m.group(1)))
    except ValueError:
        raise ToonsError("Data inválida.") from None


def adicionar_evento(dia: date | None = None) -> None:
    dia = dia or parse_data(perguntar("Data (dd/mm, hoje, amanhã)", "hoje"))
    texto = perguntar(f"O que acontece em {dia:%d/%m/%Y}?")
    if not texto:
        return
    hora = perguntar("Hora (hh:mm, opcional)", "").replace("h", ":").strip(":")
    if hora:
        m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?", hora)
        if not m or int(m.group(1)) > 23 or int(m.group(2) or 0) > 59:
            raise ToonsError("Hora inválida.")
        hora = f"{int(m.group(1)):02d}:{m.group(2) or '00'}"
    agenda = ler_json(AGENDA_FILE, {})
    agenda.setdefault(dia.isoformat(), []).append({"hora": hora, "texto": texto})
    gravar_json(AGENDA_FILE, agenda)
    ok("Evento salvo.")
    antecedencias = [("Não criar lembrete", None), ("Na hora", 0), ("15 minutos antes", 15), ("1 hora antes", 60),
                     ("1 dia antes", 1440)]
    i = escolher("Criar um lembrete?", [a for a, _ in antecedencias], 1)
    if i and antecedencias[i][1] is not None:
        quando = datetime.combine(dia, datetime.min.time()).replace(
            hour=int(hora[:2]) if hora else 9, minute=int(hora[3:]) if hora else 0)
        quando -= timedelta(minutes=antecedencias[i][1])
        if quando <= datetime.now():
            aviso("Esse horário já passou: lembrete não criado.")
            return
        adicionar_lembrete(f"{texto} ({dia:%d/%m}{' ' + hora if hora else ''})", quando)
        ok(f"Lembrete para {quando:%d/%m %H:%M}.")
        _garantir_servico_lembretes()


def apagar_evento(dia: date) -> None:
    agenda = ler_json(AGENDA_FILE, {})
    eventos = sorted(agenda.get(dia.isoformat(), []), key=lambda ev: ev.get("hora") or "")
    if not eventos:
        info("Nenhum evento nesse dia.")
        return
    i = escolher("Apagar qual?", [f"{ev.get('hora') or '--:--'}  {ev['texto']}" for ev in eventos])
    if i is not None:
        eventos.pop(i)
        if eventos:
            agenda[dia.isoformat()] = eventos
        else:
            agenda.pop(dia.isoformat(), None)
        gravar_json(AGENDA_FILE, agenda)
        ok("Evento apagado.")


def somar_meses(dia: date, n: int) -> date:
    ano, mes = divmod(dia.month - 1 + n, 12)
    ano += dia.year
    return date(ano, mes + 1, min(dia.day, calendar.monthrange(ano, mes + 1)[1]))


def calendario() -> None:
    sel = hoje = date.today()
    with TelaCheia() as tela:
        while True:
            agenda = ler_json(AGENDA_FILE, {})
            fer = {**feriados(sel.year - 1), **feriados(sel.year), **feriados(sel.year + 1)}
            linhas = ["", f"  {NEG}{MAG}◀  {MESES[sel.month - 1].capitalize()} de {sel.year}  ▶{RST}", "",
                      f"  {VERM}Do{RST} Se  Te  Qu  Qu  Se  Sá"]
            for semana in calendar.Calendar(firstweekday=6).monthdatescalendar(sel.year, sel.month):
                celulas = []
                for d in semana:
                    marca = "•" if agenda.get(d.isoformat()) else ("*" if d in fer else " ")
                    txt = f"{d.day:>2}{marca}"
                    if d == sel:
                        txt = f"{INV}{NEG}{txt}{RST}"
                    elif d.month != sel.month:
                        txt = f"{DIM}{txt}{RST}"
                    elif d == hoje:
                        txt = f"{NEG}{AMAR}\033[4m{txt}{RST}" if _COR else txt
                    elif d in fer or d.weekday() == 6:
                        txt = f"{VERM}{txt}{RST}"
                    celulas.append(txt)
                linhas.append("  " + " ".join(celulas))
            linhas += ["", f"  {NEG}{DIAS_SEMANA[sel.weekday()].capitalize()}, {sel.day} de "
                           f"{MESES[sel.month - 1]} de {sel.year}{RST}", f"  {DIM}{tempo_ate_dia(sel, hoje)}{RST}"]
            if sel in fer:
                linhas.append(f"  {VERM}🎉 {fer[sel]}{RST}")
            eventos = sorted(agenda.get(sel.isoformat(), []), key=lambda ev: ev.get("hora") or "")
            linhas += [f"  {CIANO}•{RST} {ev.get('hora') or '--:--'}  {ev['texto']}" for ev in eventos]
            if not eventos and sel not in fer:
                linhas.append(f"  {DIM}Nenhum evento.{RST}")
            linhas += ["", f"  {DIM}←→ dia · ↑↓ semana · PgUp/PgDn mês{RST}",
                       f"  {DIM}t hoje · a adiciona · d apaga · Esc sai{RST}",
                       f"  {DIM}• evento · * feriado{RST}"]
            desenhar(linhas)
            tecla = ler_tecla()
            passos = {"esq": -1, "dir": 1, "cima": -7, "baixo": 7}
            if tecla in ("esc", "q"):
                return
            if tecla in passos:
                sel += timedelta(days=passos[tecla])
            elif tecla in ("pgup", "<", ","):
                sel = somar_meses(sel, -1)
            elif tecla in ("pgdn", ">", "."):
                sel = somar_meses(sel, 1)
            elif tecla in ("t", "home"):
                sel = hoje
            elif tecla in ("a", "enter"):
                with tela.normal():
                    try:
                        adicionar_evento(sel)
                    except ToonsError as e:
                        erro(str(e))
                        pausar()
            elif tecla in ("d", "backspace"):
                with tela.normal():
                    apagar_evento(sel)


def tempo_ate_dia(dia: date, hoje: date | None = None) -> str:
    n = (dia - (hoje or date.today())).days
    if n == 0:
        return "hoje"
    if n == 1:
        return "amanhã"
    if n == -1:
        return "ontem"
    return f"daqui a {n} dias" if n > 0 else f"há {-n} dias"


@submenu
def menu_agenda():
    def proximos():
        hoje = date.today()
        itens = []
        for chave, eventos in ler_json(AGENDA_FILE, {}).items():
            dia = date.fromisoformat(chave)
            if dia >= hoje:
                itens += [(dia, ev.get("hora") or "", ev["texto"], False) for ev in eventos]
        for dia, nome in {**feriados(hoje.year), **feriados(hoje.year + 1)}.items():
            if hoje <= dia <= hoje + timedelta(days=120):
                itens.append((dia, "", nome, True))
        if not itens:
            info("Nada nos próximos dias.")
            return
        for dia, hora, texto, feriado in sorted(itens)[:30]:
            cor = VERM if feriado else ""
            print(f"  {NEG}{dia:%d/%m}{RST} {DIAS_SEMANA[dia.weekday()][:3]} {hora:5}  {cor}{texto}{RST}  "
                  f"{DIM}{tempo_ate_dia(dia, hoje)}{RST}")

    def lista_feriados():
        ano = perguntar_int("Ano", date.today().year, 1900, 2200)
        for dia, nome in sorted(feriados(ano).items()):
            print(f"  {NEG}{dia:%d/%m}{RST} {DIAS_SEMANA[dia.weekday()]:<8} {nome}")

    def contagem():
        dia = parse_data(perguntar("Contar quantos dias até (dd/mm/aaaa)"))
        n = (dia - date.today()).days
        semanas, dias = divmod(abs(n), 7)
        ok(f"{tempo_ate_dia(dia).capitalize()} ({semanas} semana(s) e {dias} dia(s)) · {DIAS_SEMANA[dia.weekday()]}.")

    menu("📅 Calendário e agenda", [
        ("Abrir o calendário (setas)", calendario),
        ("Adicionar evento", adicionar_evento),
        ("Próximos eventos e feriados", proximos),
        ("Feriados nacionais de um ano", lista_feriados),
        ("Quantos dias faltam até...", contagem),
    ])


# ── Conversor de unidades e moedas ───────────────────────────────────

UNIDADES = {
    "Comprimento": {"milímetro (mm)": 0.001, "centímetro (cm)": 0.01, "metro (m)": 1, "quilômetro (km)": 1000,
                    "polegada (in)": 0.0254, "pé (ft)": 0.3048, "jarda (yd)": 0.9144, "milha (mi)": 1609.344,
                    "milha náutica": 1852},
    "Massa": {"miligrama (mg)": 1e-6, "grama (g)": 1e-3, "quilo (kg)": 1, "tonelada (t)": 1000,
              "onça (oz)": 0.028349523125, "libra (lb)": 0.45359237, "arroba (@)": 15},
    "Área": {"cm²": 1e-4, "m²": 1, "km²": 1e6, "hectare (ha)": 1e4, "alqueire paulista": 24200,
             "alqueire mineiro": 48400, "acre": 4046.8564224, "pé²": 0.09290304},
    "Volume": {"mililitro (ml)": 1e-3, "litro (l)": 1, "metro cúbico (m³)": 1000, "xícara (240 ml)": 0.24,
               "colher de sopa (15 ml)": 0.015, "colher de chá (5 ml)": 0.005, "galão americano": 3.785411784,
               "onça líquida (fl oz)": 0.0295735295625},
    "Velocidade": {"m/s": 1, "km/h": 1 / 3.6, "mph": 0.44704, "nó": 1852 / 3600},
    "Tempo": {"segundo": 1, "minuto": 60, "hora": 3600, "dia": 86400, "semana": 604800, "mês (30 dias)": 2592000,
              "ano (365 dias)": 31536000},
    "Dados": {"bit": 0.125, "byte (B)": 1, "KB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12, "KiB": 1024,
              "MiB": 1024 ** 2, "GiB": 1024 ** 3, "TiB": 1024 ** 4},
    "Energia": {"joule (J)": 1, "quilojoule (kJ)": 1000, "caloria (cal)": 4.184, "quilocaloria (kcal)": 4184,
                "watt-hora (Wh)": 3600, "quilowatt-hora (kWh)": 3.6e6},
    "Pressão": {"pascal (Pa)": 1, "quilopascal (kPa)": 1000, "bar": 1e5, "atmosfera (atm)": 101325,
                "psi (libra/pol²)": 6894.757293168, "mmHg": 133.322387415},
    "Temperatura": {"Celsius (°C)": None, "Fahrenheit (°F)": None, "Kelvin (K)": None},
}

MOEDAS = {"BRL": "Real", "USD": "Dólar americano", "EUR": "Euro", "GBP": "Libra esterlina", "ARS": "Peso argentino",
          "CLP": "Peso chileno", "UYU": "Peso uruguaio", "PYG": "Guarani paraguaio", "MXN": "Peso mexicano",
          "CAD": "Dólar canadense", "AUD": "Dólar australiano", "JPY": "Iene japonês", "CNY": "Yuan chinês",
          "CHF": "Franco suíço", "INR": "Rúpia indiana"}


def converter_temperatura(valor: float, de: str, para: str) -> float:
    celsius = {"C": valor, "F": (valor - 32) * 5 / 9, "K": valor - 273.15}[de[0] if de[0] in "CFK" else de]
    return {"C": celsius, "F": celsius * 9 / 5 + 32, "K": celsius + 273.15}[para[0]]


def converter_unidade(categoria: str, valor: float, de: str, para: str) -> float:
    if categoria == "Temperatura":
        return converter_temperatura(valor, de, para)
    tabela = UNIDADES[categoria]
    return valor * tabela[de] / tabela[para]


def cotacoes(renovar: bool = False) -> dict:
    """Câmbio a partir do real (open.er-api.com, sem chave); guarda por 6 h para funcionar sem internet."""
    cache = ler_json(CAMBIO_FILE, {})
    if not renovar and cache.get("taxas") and time.time() - cache.get("quando", 0) < 6 * 3600:
        return cache
    try:
        dados = pedir_json("https://open.er-api.com/v6/latest/BRL", timeout=20)
        if dados.get("result") != "success":
            raise ToonsError(f"Serviço de câmbio respondeu: {dados.get('error-type', 'erro')}")
        cache = {"quando": time.time(), "taxas": dados["rates"], "fonte": dados.get("time_last_update_utc", "")}
        gravar_json(CAMBIO_FILE, cache)
    except ToonsError:
        if not cache.get("taxas"):
            raise
        aviso(f"Sem internet: usando a cotação salva em {datetime.fromtimestamp(cache['quando']):%d/%m %H:%M}.")
    return cache


def converter_moeda(valor: float, de: str, para: str, taxas: dict) -> float:
    if de not in taxas or para not in taxas:
        raise ToonsError(f"Moeda sem cotação: {de if de not in taxas else para}")
    return valor / taxas[de] * taxas[para]


@submenu
def menu_conversor():
    def unidades(categoria: str):
        nomes = list(UNIDADES[categoria])
        i = escolher("Converter de", nomes)
        if i is None:
            return
        j = escolher("Para", nomes, (i + 1) % len(nomes) + 1)
        if j is None:
            return
        valor = ler_numero(f"Valor em {nomes[i]}")
        resultado = converter_unidade(categoria, valor, nomes[i], nomes[j])
        print(f"\n  {numero_br(valor)} {nomes[i]} = {NEG}{VERD}{numero_br(resultado)} {nomes[j]}{RST}\n")
        print(f"{DIM}  Em todas as unidades:{RST}")
        for nome in nomes:
            print(f"    {numero_br(converter_unidade(categoria, valor, nomes[i], nome)):>18}  {nome}")

    def moedas():
        dados = cotacoes()
        siglas = [s for s in MOEDAS if s in dados["taxas"]]
        rotulos = [f"{s} · {MOEDAS[s]}" for s in siglas] + ["Outra (digitar a sigla)"]

        def pegar(msg, padrao):
            k = escolher(msg, rotulos, padrao)
            if k is None:
                return None
            if k < len(siglas):
                return siglas[k]
            sigla = perguntar("Sigla da moeda (ex.: COP, PEN, KRW)").upper()
            if sigla not in dados["taxas"]:
                raise ToonsError(f"Sem cotação para '{sigla}'.")
            return sigla

        de = pegar("Converter de", 2)
        para = de and pegar("Para", 1)
        if not para:
            return
        valor = ler_numero(f"Valor em {de}")
        resultado = converter_moeda(valor, de, para, dados["taxas"])
        print(f"\n  {numero_br(valor, 2)} {de} = {NEG}{VERD}{numero_br(resultado, 4)} {para}{RST}")
        print(f"  {DIM}1 {de} = {numero_br(converter_moeda(1, de, para, dados['taxas']), 4)} {para} · "
              f"cotação de {dados.get('fonte', '')[:25]}{RST}")

    def tabela_real():
        dados = cotacoes()
        print(f"{DIM}Quanto vale 1 unidade de cada moeda em reais ({dados.get('fonte', '')[:25]}):{RST}")
        for sigla, nome in MOEDAS.items():
            if sigla != "BRL" and sigla in dados["taxas"]:
                print(f"  {sigla}  {nome:<20} R$ {numero_br(1 / dados['taxas'][sigla], 4)}")

    menu("💱 Conversor de unidades e moedas", [
        ("💵 Moedas (cotação do dia)", moedas),
        ("💵 Tabela: quanto vale cada moeda em reais", tabela_real),
        *[(f"📏 {cat}", (lambda c=cat: unidades(c))) for cat in UNIDADES],
        ("🔄 Atualizar a cotação agora", lambda: cotacoes(renovar=True) and ok("Cotação atualizada.")),
    ])


# ── Controle de gastos ───────────────────────────────────────────────

CATEGORIAS_GASTO = ["Alimentação", "Mercado", "Transporte", "Moradia", "Contas", "Saúde", "Lazer", "Educação",
                    "Compras", "Outros"]
CATEGORIAS_ENTRADA = ["Salário", "Freelance", "Vendas", "Presente", "Outros"]


def _gastos() -> dict:
    dados = ler_json(GASTOS_FILE, {})
    dados.setdefault("lancamentos", [])
    dados.setdefault("orcamento", 0)
    dados.setdefault("categorias", list(CATEGORIAS_GASTO))
    return dados


def resumo_mes(lancamentos: list, ano: int, mes: int) -> dict:
    prefixo = f"{ano:04d}-{mes:02d}"
    do_mes = [l for l in lancamentos if l["data"].startswith(prefixo)]
    por_categoria = {}
    for l in do_mes:
        if l["tipo"] == "saida":
            por_categoria[l["categoria"]] = por_categoria.get(l["categoria"], 0) + l["valor"]
    entradas = sum(l["valor"] for l in do_mes if l["tipo"] == "entrada")
    saidas = sum(l["valor"] for l in do_mes if l["tipo"] == "saida")
    return {"lancamentos": do_mes, "entradas": entradas, "saidas": saidas, "saldo": entradas - saidas,
            "por_categoria": dict(sorted(por_categoria.items(), key=lambda par: -par[1]))}


@submenu
def menu_gastos():
    def lancar(tipo: str):
        dados = _gastos()
        valor = ler_numero("Valor (R$)", minimo=0.01)
        cats = dados["categorias"] if tipo == "saida" else CATEGORIAS_ENTRADA
        i = escolher("Categoria", cats + ["Nova categoria..."])
        if i is None:
            return
        if i == len(cats):
            nova = perguntar("Nome da categoria").strip().capitalize()
            if not nova:
                return
            if tipo == "saida" and nova not in dados["categorias"]:
                dados["categorias"].append(nova)
            categoria = nova
        else:
            categoria = cats[i]
        descricao = perguntar("Descrição (opcional)", "")
        texto_data = perguntar("Data (hoje, ontem, dd/mm)", "hoje")
        dia = date.today() - timedelta(days=1) if sem_acento(texto_data).lower() == "ontem" else parse_data(texto_data)
        dados["lancamentos"].append({"id": uuid.uuid4().hex[:8], "data": dia.isoformat(), "valor": round(valor, 2),
                                     "tipo": tipo, "categoria": categoria, "descricao": descricao})
        gravar_json(GASTOS_FILE, dados)
        ok(f"{'Gasto' if tipo == 'saida' else 'Entrada'} de {reais(valor)} lançado em {categoria}.")
        if tipo == "saida" and dados["orcamento"]:
            gasto = resumo_mes(dados["lancamentos"], dia.year, dia.month)["saidas"]
            frac = gasto / dados["orcamento"]
            if frac >= 1:
                aviso(f"Você passou do orçamento do mês: {reais(gasto)} de {reais(dados['orcamento'])}.")
            elif frac >= 0.8:
                aviso(f"Atenção: já usou {frac:.0%} do orçamento do mês.")

    def pedir_mes() -> tuple:
        texto = perguntar("Mês (mm/aaaa)", f"{date.today():%m/%Y}")
        m = re.fullmatch(r"(\d{1,2})/(\d{4})", texto.strip())
        if not m or not 1 <= int(m.group(1)) <= 12:
            raise ToonsError("Use o formato mm/aaaa.")
        return int(m.group(2)), int(m.group(1))

    def resumo():
        dados = _gastos()
        ano, mes = pedir_mes()
        r = resumo_mes(dados["lancamentos"], ano, mes)
        titulo(f"{MESES[mes - 1].capitalize()} de {ano}")
        print(f"  Entradas: {VERD}{reais(r['entradas'])}{RST}")
        print(f"  Saídas:   {VERM}{reais(r['saidas'])}{RST}")
        print(f"  Saldo:    {NEG}{(VERD if r['saldo'] >= 0 else VERM)}{reais(r['saldo'])}{RST}")
        if dados["orcamento"]:
            frac = r["saidas"] / dados["orcamento"]
            cor = VERM if frac >= 1 else AMAR if frac >= 0.8 else VERD
            print(f"  Orçamento: {cor}{barra_horizontal(min(frac, 1))}{RST} {frac:.0%} de {reais(dados['orcamento'])}")
        if r["por_categoria"]:
            print(f"\n{NEG}  Gastos por categoria{RST}")
            maior = max(r["por_categoria"].values())
            for cat, valor in r["por_categoria"].items():
                print(f"  {cat:<14} {CIANO}{barra_horizontal(valor / maior, 16)}{RST} {reais(valor):>13} "
                      f"{DIM}{valor / r['saidas']:.0%}{RST}")

    def ultimos():
        dados = _gastos()
        lista = sorted(dados["lancamentos"], key=lambda l: (l["data"], l["id"]), reverse=True)[:60]
        if not lista:
            info("Nenhum lançamento ainda.")
            return
        rotulos = [f"{date.fromisoformat(l['data']):%d/%m} {(VERM + '-') if l['tipo'] == 'saida' else (VERD + '+')}"
                   f"{reais(l['valor'])}{RST} {l['categoria']}{DIM}{' · ' + l['descricao'] if l['descricao'] else ''}{RST}"
                   for l in lista]
        marcados = escolher_varios("Lançamentos (marque com Espaço para apagar, Enter sem marcar volta)", rotulos)
        if marcados and confirmar(f"Apagar {len(marcados)} lançamento(s)?", False):
            ids = {lista[i]["id"] for i in marcados}
            dados["lancamentos"] = [l for l in dados["lancamentos"] if l["id"] not in ids]
            gravar_json(GASTOS_FILE, dados)
            ok("Apagado(s).")

    def historico():
        dados = _gastos()
        hoje = date.today()
        meses = [somar_meses(hoje.replace(day=1), -k) for k in range(5, -1, -1)]
        resumos = [(d, resumo_mes(dados["lancamentos"], d.year, d.month)) for d in meses]
        maior = max([max(r["entradas"], r["saidas"]) for _, r in resumos] + [1])
        for d, r in resumos:
            print(f"  {MESES[d.month - 1][:3]}/{d.year % 100:02d}  {VERD}{barra_horizontal(r['entradas'] / maior, 18)}{RST} "
                  f"{reais(r['entradas'])}")
            print(f"          {VERM}{barra_horizontal(r['saidas'] / maior, 18)}{RST} {reais(r['saidas'])}  "
                  f"{DIM}saldo {reais(r['saldo'])}{RST}")

    def orcamento():
        dados = _gastos()
        dados["orcamento"] = round(ler_numero("Orçamento mensal para gastos (R$, 0 desliga)",
                                              numero_br(dados["orcamento"], 2), 0), 2)
        gravar_json(GASTOS_FILE, dados)
        ok("Orçamento salvo." if dados["orcamento"] else "Orçamento desligado.")

    def exportar():
        dados = _gastos()
        destino = pasta_saida() / f"gastos_{datetime.now():%Y%m%d}.csv"
        with open(destino, "w", newline="", encoding="utf-8-sig") as arq:  # utf-8-sig: o Excel abre com acentos
            escritor = csv.writer(arq, delimiter=";")
            escritor.writerow(["data", "tipo", "categoria", "valor", "descrição"])
            for l in sorted(dados["lancamentos"], key=lambda l: l["data"]):
                escritor.writerow([l["data"], l["tipo"], l["categoria"], numero_br(l["valor"], 2), l["descricao"]])
        ok(f"Planilha salva: {destino}")

    def cabecalho_gastos():
        r = resumo_mes(_gastos()["lancamentos"], date.today().year, date.today().month)
        print(f"{DIM}Este mês: entradas {reais(r['entradas'])} · saídas {reais(r['saidas'])} · "
              f"saldo {reais(r['saldo'])}{RST}")

    menu("💰 Controle de gastos", [
        ("➖ Lançar gasto", lambda: lancar("saida")),
        ("➕ Lançar entrada (salário, venda...)", lambda: lancar("entrada")),
        ("Resumo do mês (por categoria)", resumo),
        ("Últimos lançamentos (e apagar)", ultimos),
        ("Últimos 6 meses", historico),
        ("Orçamento mensal", orcamento),
        ("Exportar planilha (.csv para Excel/Sheets)", exportar),
    ], cabecalho=cabecalho_gastos)


# ── Gerenciador de senhas ────────────────────────────────────────────

SIMBOLOS_SENHA = "!@#$%&*-_=+?"


def gerar_senha(tamanho: int = 20, simbolos: bool = True) -> str:
    alfabeto = string.ascii_letters + string.digits + (SIMBOLOS_SENHA if simbolos else "")
    while True:
        senha = "".join(secrets.choice(alfabeto) for _ in range(tamanho))
        if (any(c.islower() for c in senha) and any(c.isupper() for c in senha) and any(c.isdigit() for c in senha)
                and (not simbolos or any(c in SIMBOLOS_SENHA for c in senha))):
            return senha


def gerar_frase_senha(palavras: int = 5) -> str:
    lista = sorted({sem_acento(p).lower() for p in PALAVRAS_FORCA if len(p) >= 4 and p.isalpha()})
    return "-".join(secrets.choice(lista) for _ in range(palavras)) + f"-{secrets.randbelow(100)}"


def forca_senha(senha: str) -> str:
    variedade = sum(bool(re.search(p, senha)) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[^\w]"))
    if len(senha) >= 16 and variedade >= 3 or len(senha) >= 24:
        return f"{VERD}forte{RST}"
    if len(senha) >= 12 and variedade >= 3:
        return f"{AMAR}razoável{RST}"
    return f"{VERM}fraca{RST}"


def _cofre_chave(senha: str, meta: dict) -> bytes:
    sal = base64.b64decode(meta["sal"])
    if meta["kdf"] == "scrypt":
        bruta = hashlib.scrypt(senha.encode(), salt=sal, n=2 ** 15, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)
    else:
        bruta = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, 600_000, dklen=32)
    return base64.urlsafe_b64encode(bruta)


def cofre_salvar(entradas: list, senha: str, meta: dict | None = None) -> dict:
    """Criptografa as entradas (Fernet: AES + HMAC) com uma chave derivada da senha mestra."""
    from cryptography.fernet import Fernet
    meta = meta or {"versao": 1, "kdf": "scrypt" if hasattr(hashlib, "scrypt") else "pbkdf2",
                    "sal": base64.b64encode(secrets.token_bytes(16)).decode()}
    token = Fernet(_cofre_chave(senha, meta)).encrypt(json.dumps(entradas, ensure_ascii=False).encode())
    gravar_json(COFRE_FILE, {**meta, "dados": token.decode()}, privado=True)
    return meta


def cofre_abrir(senha: str) -> tuple:
    from cryptography.fernet import Fernet, InvalidToken
    dados = ler_json(COFRE_FILE, None)
    if not dados:
        raise ToonsError("O cofre ainda não foi criado.")
    meta = {k: dados[k] for k in ("versao", "kdf", "sal")}
    try:
        entradas = json.loads(Fernet(_cofre_chave(senha, meta)).decrypt(dados["dados"].encode()))
    except InvalidToken:
        raise ToonsError("Senha mestra errada.") from None
    return entradas, meta


def _copiar_e_limpar(texto: str, segundos: int = 30) -> None:
    """Copia e apaga da área de transferência depois de um tempo (se ninguém copiou outra coisa)."""
    if not copiar_texto(texto, avisar=False):
        return
    ok(f"Copiado. A área de transferência será limpa em {segundos} s.")

    def limpar_depois():
        with contextlib.suppress(Exception):
            if _tapi(["termux-clipboard-get"], 10, json_saida=False) == texto:
                _tapi(["termux-clipboard-set"], 10, entrada="", json_saida=False)

    temporizador_limpeza = threading.Timer(segundos, limpar_depois)
    temporizador_limpeza.daemon = True
    temporizador_limpeza.start()


@submenu
def menu_senhas():
    def gerador():
        tipo = escolher("Tipo", ["Senha aleatória (letras, números e símbolos)", "Senha sem símbolos",
                                 "Frase-senha (fácil de lembrar, ex.: casa-tigre-livro-...)"])
        if tipo is None:
            return
        if tipo == 2:
            senha = gerar_frase_senha(perguntar_int("Quantas palavras", 5, 3, 10))
        else:
            senha = gerar_senha(perguntar_int("Tamanho", 20, 8, 128), simbolos=tipo == 0)
        print(f"\n  {NEG}{senha}{RST}   ({forca_senha(senha)})\n")
        if confirmar("Copiar?", True):
            _copiar_e_limpar(senha, 60)

    def abrir_cofre():
        if not garantir_modulo("cryptography", pkg_nome="python-cryptography",
                               aviso_extra="Ele faz a criptografia do cofre (AES)."):
            return
        if not COFRE_FILE.exists():
            info("Vamos criar o cofre. A senha mestra protege todas as outras.")
            aviso("Se você esquecer a senha mestra, NÃO há como recuperar as senhas guardadas.")
            senha = getpass.getpass("Nova senha mestra: ")
            if len(senha) < 8:
                raise ToonsError("Use pelo menos 8 caracteres na senha mestra.")
            if getpass.getpass("Repita a senha mestra: ") != senha:
                raise ToonsError("As senhas não conferem.")
            cofre_salvar([], senha)
            ok("Cofre criado.")
        else:
            senha = getpass.getpass("Senha mestra: ")
        info("Abrindo o cofre...")
        entradas, meta = cofre_abrir(senha)
        estado = {"senha": senha, "meta": meta}

        def salvar():
            estado["meta"] = cofre_salvar(entradas, estado["senha"], estado["meta"])

        def pedir_entrada(base: dict | None = None) -> dict | None:
            base = base or {}
            nome = perguntar("Nome (ex.: Gmail, Banco)", base.get("nome"))
            if not nome:
                return None
            usuario = perguntar("Usuário / e-mail", base.get("usuario", ""))
            senha_nova = getpass.getpass("Senha (Enter = gerar uma forte" + (", ou manter a atual" if base else "")
                                         + "): ")
            if not senha_nova:
                senha_nova = base.get("senha") if base and not confirmar("Gerar uma senha nova?", False) \
                    else gerar_senha(20)
            return {"nome": nome, "usuario": usuario, "senha": senha_nova,
                    "url": perguntar("Site (opcional)", base.get("url", "")),
                    "notas": perguntar("Observações (opcional)", base.get("notas", "")),
                    "alterada": datetime.now().strftime("%Y-%m-%d")}

        def ver(entrada: dict):
            while True:
                limpar()
                titulo(f"🔐 {entrada['nome']}")
                print(f"  Usuário: {entrada.get('usuario') or '-'}")
                print(f"  Senha:   {'•' * 12}  ({forca_senha(entrada['senha'])})")
                if entrada.get("url"):
                    print(f"  Site:    {entrada['url']}")
                if entrada.get("notas"):
                    print(f"  Notas:   {entrada['notas']}")
                print(f"  {DIM}alterada em {entrada.get('alterada', '?')}{RST}\n")
                i = escolher("O que fazer?", ["Copiar a senha", "Copiar o usuário", "Mostrar a senha", "Editar",
                                              "Abrir o site", "Apagar", "Voltar"])
                if i in (None, 6):
                    return
                if i == 0:
                    _copiar_e_limpar(entrada["senha"])
                elif i == 1:
                    copiar_texto(entrada.get("usuario", ""))
                elif i == 2:
                    print(f"\n  {NEG}{entrada['senha']}{RST}")
                elif i == 3:
                    nova = pedir_entrada(entrada)
                    if nova:
                        entrada.update(nova)
                        salvar()
                        ok("Salvo.")
                elif i == 4 and entrada.get("url"):
                    abrir_link(entrada["url"] if "://" in entrada["url"] else "https://" + entrada["url"])
                elif i == 5 and confirmar(f"Apagar '{entrada['nome']}' do cofre?", False):
                    entradas.remove(entrada)
                    salvar()
                    ok("Apagado.")
                    return
                if i in (0, 1, 2, 3):
                    pausar()

        def lista(filtro: str = ""):
            achadas = sorted([e for e in entradas if not filtro or contem(f"{e['nome']} {e.get('usuario', '')} "
                                                                          f"{e.get('url', '')}", filtro)],
                             key=lambda e: e["nome"].lower())
            if not achadas:
                info("Nada encontrado.")
                return
            i = escolher("Qual?", [f"{e['nome']}  {DIM}{e.get('usuario', '')}{RST}" for e in achadas])
            if i is not None:
                ver(achadas[i])

        def adicionar():
            nova = pedir_entrada()
            if nova:
                entradas.append(nova)
                salvar()
                ok(f"'{nova['nome']}' guardada no cofre.")

        def auditoria():
            repetidas = {}
            for e in entradas:
                repetidas.setdefault(e["senha"], []).append(e["nome"])
            problemas = 0
            for e in entradas:
                if "fraca" in forca_senha(e["senha"]):
                    print(f"  {VERM}fraca{RST}     {e['nome']}")
                    problemas += 1
            for nomes in repetidas.values():
                if len(nomes) > 1:
                    print(f"  {AMAR}repetida{RST}  {', '.join(nomes)}")
                    problemas += 1
            if not problemas:
                ok("Nenhuma senha fraca ou repetida. 👏")

        def trocar_mestra():
            nova = getpass.getpass("Nova senha mestra: ")
            if len(nova) < 8 or getpass.getpass("Repita: ") != nova:
                raise ToonsError("Senha curta (mínimo 8) ou não confere.")
            estado["senha"] = nova
            estado["meta"] = cofre_salvar(entradas, nova)  # sal novo junto com a senha nova
            ok("Senha mestra trocada.")

        def backup():
            destino = pasta_saida() / f"cofre_backup_{datetime.now():%Y%m%d}.json"
            shutil.copy2(COFRE_FILE, destino)
            ok(f"Backup criptografado salvo em {destino} (só abre com a senha mestra).")

        menu(f"🔐 Cofre ({len(entradas)} senhas)", [
            (lambda: f"Ver senhas ({len(entradas)})", lista),
            ("Buscar", lambda: lista(perguntar("Procurar por"))),
            ("Guardar nova senha", adicionar),
            ("Verificar senhas fracas ou repetidas", auditoria),
            ("Trocar a senha mestra", trocar_mestra),
            ("Backup do cofre (arquivo criptografado)", backup),
        ], sair="Fechar o cofre")

    menu("🔐 Gerenciador de senhas", [
        ("Abrir o cofre de senhas", abrir_cofre),
        ("Gerar senha forte (sem guardar)", gerador),
    ])


# ── Previsão do tempo ────────────────────────────────────────────────

CLIMA_CODIGOS = {
    0: ("☀️", "Céu limpo"), 1: ("🌤️", "Poucas nuvens"), 2: ("⛅", "Parcialmente nublado"), 3: ("☁️", "Nublado"),
    45: ("🌫️", "Neblina"), 48: ("🌫️", "Neblina com geada"), 51: ("🌦️", "Garoa fraca"), 53: ("🌦️", "Garoa"),
    55: ("🌧️", "Garoa forte"), 56: ("🌧️", "Garoa congelante"), 57: ("🌧️", "Garoa congelante forte"),
    61: ("🌦️", "Chuva fraca"), 63: ("🌧️", "Chuva"), 65: ("🌧️", "Chuva forte"), 66: ("🌧️", "Chuva congelante"),
    67: ("🌧️", "Chuva congelante forte"), 71: ("🌨️", "Neve fraca"), 73: ("🌨️", "Neve"), 75: ("❄️", "Neve forte"),
    77: ("🌨️", "Grãos de neve"), 80: ("🌦️", "Pancadas de chuva fracas"), 81: ("🌧️", "Pancadas de chuva"),
    82: ("⛈️", "Pancadas de chuva fortes"), 85: ("🌨️", "Pancadas de neve"), 86: ("🌨️", "Pancadas de neve fortes"),
    95: ("⛈️", "Trovoadas"), 96: ("⛈️", "Trovoadas com granizo"), 99: ("⛈️", "Trovoadas com granizo forte"),
}


def clima(codigo) -> tuple:
    return CLIMA_CODIGOS.get(int(codigo or 0), ("🌡️", f"Código {codigo}"))


def buscar_cidade(nome: str) -> list:
    dados = pedir_json(url_com("https://geocoding-api.open-meteo.com/v1/search", name=nome, count=8,
                               language="pt", format="json"))
    return [{"nome": ", ".join(x for x in (r.get("name"), r.get("admin1"), r.get("country")) if x),
             "lat": r["latitude"], "lon": r["longitude"]} for r in (dados or {}).get("results", [])]


def previsao(lat: float, lon: float) -> dict:
    return pedir_json(url_com(
        "https://api.open-meteo.com/v1/forecast", latitude=lat, longitude=lon, timezone="auto", forecast_days=7,
        current="temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
        hourly="temperature_2m,precipitation_probability,weather_code",
        daily="weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset"))


def proximas_horas(dados: dict, horas: int) -> list:
    """Índices das próximas `horas` horas na previsão horária, a partir da hora atual do lugar."""
    agora = dados.get("current", {}).get("time", "")[:13]
    tempos = dados["hourly"]["time"]
    inicio = next((i for i, t in enumerate(tempos) if t[:13] >= agora), 0)
    return list(range(inicio, min(inicio + horas, len(tempos))))


def _local_do_tempo(perguntar_sempre: bool = False) -> dict:
    c = cfg()
    local = c.get("tempo_local") or {}
    if local and not perguntar_sempre:
        return local
    i = escolher("Onde?", ["Minha localização (GPS/rede)", "Buscar uma cidade"])
    if i is None:
        raise ToonsError("Cancelado.")
    if i == 0:
        info("Pegando a localização...")
        loc = localizacao("network")
        local = {"nome": "Minha localização", "lat": round(loc["latitude"], 3), "lon": round(loc["longitude"], 3)}
    else:
        achadas = buscar_cidade(perguntar("Cidade"))
        if not achadas:
            raise ToonsError("Cidade não encontrada.")
        k = escolher("Qual?", [a["nome"] for a in achadas])
        if k is None:
            raise ToonsError("Cancelado.")
        local = achadas[k]
    c["tempo_local"] = local
    salvar_cfg()
    return local


def mostrar_previsao(local: dict | None = None) -> None:
    local = local or _local_do_tempo()
    dados = previsao(local["lat"], local["lon"])
    atual = dados["current"]
    emoji, desc = clima(atual["weather_code"])
    titulo(f"🌦️ {local['nome']}")
    print(f"  {emoji}  {NEG}{atual['temperature_2m']:.0f}°C{RST}  {desc}")
    print(f"  Sensação {atual['apparent_temperature']:.0f}°C · umidade {atual['relative_humidity_2m']}% · "
          f"vento {atual['wind_speed_10m']:.0f} km/h · chuva agora {atual['precipitation']} mm")
    h = dados["hourly"]
    print(f"\n{NEG}  Próximas horas{RST}")
    for i in proximas_horas(dados, 12)[::2]:
        e, _ = clima(h["weather_code"][i])
        chance = h["precipitation_probability"][i]
        cor = AZUL if (chance or 0) >= 50 else DIM
        print(f"  {h['time'][i][11:16]}  {e}  {h['temperature_2m'][i]:>5.1f}°C  {cor}💧 {chance or 0}%{RST}")
    d = dados["daily"]
    print(f"\n{NEG}  Próximos dias{RST}")
    for i, dia_txt in enumerate(d["time"]):
        dia = date.fromisoformat(dia_txt)
        e, descricao = clima(d["weather_code"][i])
        nome_dia = "hoje" if i == 0 else DIAS_SEMANA[dia.weekday()][:3]
        print(f"  {nome_dia:<5} {dia:%d/%m}  {e}  {d['temperature_2m_min'][i]:>3.0f}° / {NEG}"
              f"{d['temperature_2m_max'][i]:.0f}°{RST}  💧{d['precipitation_probability_max'][i] or 0:>3}%  "
              f"{DIM}{descricao}{RST}")
    print(f"\n  {DIM}🌅 {d['sunrise'][0][11:16]} · 🌇 {d['sunset'][0][11:16]} · dados: Open-Meteo{RST}")


def configurar_alerta_chuva() -> dict:
    """Dados de um monitor do tipo 'chuva' (usado também pelo menu de monitoramento)."""
    local = _local_do_tempo(perguntar_sempre=True)
    limite = perguntar_int("Avisar quando a chance de chuva passar de (%)", 60, 10, 100)
    horas = perguntar_int("Olhando quantas horas à frente", 3, 1, 24)
    return {"tipo": "chuva", "nome": f"Chuva em {local['nome']}", "lat": local["lat"], "lon": local["lon"],
            "limite": limite, "horas": horas}


def checar_chuva(m: dict, est: dict) -> tuple:
    dados = pedir_json(url_com("https://api.open-meteo.com/v1/forecast", latitude=m["lat"], longitude=m["lon"],
                               timezone="auto", forecast_days=2, current="weather_code",
                               hourly="precipitation_probability"))
    horas = int(m.get("horas", 3))
    chances = [dados["hourly"]["precipitation_probability"][i] or 0 for i in proximas_horas(dados, horas)]
    maximo = max(chances, default=0)
    vai_chover = maximo >= int(m.get("limite", 60))
    alerta = None
    if vai_chover and not est.get("avisado"):
        alerta = f"🌧️ {m['nome']}: {maximo}% de chance de chuva nas próximas {horas} h. Leve o guarda-chuva!"
    est["avisado"] = vai_chover
    return alerta, f"{maximo}% nas próximas {horas} h"


@submenu
def menu_tempo():
    def alerta():
        dados = configurar_alerta_chuva()
        dados["intervalo"] = 1800
        adicionar_monitor_dados(dados)
        if not servico_ativo("monitor") and confirmar("Iniciar o serviço de monitoramento agora?", True):
            iniciar_servico("monitor", cmd_self("monitor"), reiniciar=True)

    menu("🌦️ Previsão do tempo", [
        (lambda: f"Previsão para {(cfg().get('tempo_local') or {}).get('nome', 'meu local')}",
         lambda: mostrar_previsao()),
        ("Previsão de outra cidade", lambda: mostrar_previsao(_local_do_tempo(perguntar_sempre=True))),
        ("Trocar meu local padrão", lambda: _local_do_tempo(perguntar_sempre=True) and ok("Local salvo.")),
        ("Criar alerta de chuva (notificação)", alerta),
    ])


# ── QR code ──────────────────────────────────────────────────────────

def crc16_pix(texto: str) -> str:
    """CRC16-CCITT (polinômio 0x1021, início 0xFFFF), como o Banco Central pede no PIX."""
    crc = 0xFFFF
    for byte in texto.encode():
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return f"{crc:04X}"


def pix_copia_e_cola(chave: str, nome: str, cidade: str, valor: float | None = None, descricao: str = "",
                     txid: str = "***") -> str:
    """Código PIX estático (BR Code), o mesmo do 'PIX copia e cola'."""
    def campo(ident: str, conteudo: str) -> str:
        return f"{ident}{len(conteudo):02d}{conteudo}"

    def limpo(texto: str, maximo: int) -> str:
        return re.sub(r"[^A-Za-z0-9 ]", "", sem_acento(texto)).upper().strip()[:maximo] or "X"

    conta = campo("00", "br.gov.bcb.pix") + campo("01", chave) + (campo("02", descricao[:40]) if descricao else "")
    payload = (campo("00", "01") + campo("26", conta) + campo("52", "0000") + campo("53", "986")
               + (campo("54", f"{valor:.2f}") if valor else "") + campo("58", "BR") + campo("59", limpo(nome, 25))
               + campo("60", limpo(cidade, 15)) + campo("62", campo("05", re.sub(r"[^A-Za-z0-9*]", "", txid)[:25]))
               + "6304")
    return payload + crc16_pix(payload)


def wifi_qr(ssid: str, senha: str, seguranca: str = "WPA", oculta: bool = False) -> str:
    def esc(t: str) -> str:
        return re.sub(r'([\\;,:"])', r"\\\1", t)
    return f"WIFI:T:{seguranca};S:{esc(ssid)};" + (f"P:{esc(senha)};" if seguranca != "nopass" else "") + \
        ("H:true;" if oculta else "") + ";"


def mostrar_qr(conteudo: str, nome_arquivo: str = "qrcode", salvar: bool = True) -> Path | None:
    if not garantir_cmd("qrencode", "libqrencode"):
        return None
    rodar(["qrencode", "-t", "ansiutf8", "-m", "2"], entrada=conteudo, mostrar=False)
    return salvar_qr(conteudo, nome_arquivo) if salvar else None


def salvar_qr(conteudo: str, nome_arquivo: str = "qrcode") -> Path | None:
    """Grava o QR code como imagem .png em Download/Termux-Toons/QR codes."""
    destino = pasta_saida("QR codes") / f"{_slug(nome_arquivo)}_{datetime.now():%H%M%S}.png"
    rodar(["qrencode", "-o", str(destino), "-s", "10", "-m", "3"], entrada=conteudo, mostrar=False)
    if destino.exists():
        ok(f"Imagem salva: {destino}")
        return destino
    return None


@submenu
def menu_qr():
    def texto_ou_link():
        conteudo = perguntar("Texto ou link")
        if conteudo:
            mostrar_qr(conteudo, "texto")

    def wifi():
        ssid = perguntar("Nome da rede (SSID)")
        if not ssid:
            return
        tipos = [("WPA/WPA2/WPA3 (o mais comum)", "WPA"), ("WEP (antigo)", "WEP"), ("Sem senha", "nopass")]
        i = escolher("Segurança", [t for t, _ in tipos], 1) or 0
        senha = "" if tipos[i][1] == "nopass" else getpass.getpass("Senha do Wi-Fi: ")
        mostrar_qr(wifi_qr(ssid, senha, tipos[i][1], confirmar("A rede é oculta?", False)), f"wifi_{ssid}")
        info("Quem escanear com a câmera conecta direto, sem digitar a senha.")

    def pix():
        tipos = ["CPF/CNPJ", "Celular", "E-mail", "Chave aleatória"]
        i = escolher("Tipo da chave PIX", tipos)
        if i is None:
            return
        chave = perguntar("Chave").strip()
        if i == 0:
            chave = re.sub(r"\D", "", chave)
            if len(chave) not in (11, 14):
                raise ToonsError("CPF tem 11 dígitos e CNPJ 14.")
        elif i == 1:
            digitos = re.sub(r"\D", "", chave)
            chave = "+" + (digitos if digitos.startswith("55") and len(digitos) > 11 else "55" + digitos)
        elif i == 2 and "@" not in chave:
            raise ToonsError("E-mail inválido.")
        nome = perguntar("Nome de quem recebe")
        cidade = perguntar("Cidade de quem recebe")
        valor_txt = perguntar("Valor em R$ (Enter = quem paga digita)", "")
        valor = parse_preco(valor_txt) if valor_txt else None
        descricao = perguntar("Descrição (opcional)", "")
        codigo = pix_copia_e_cola(chave, nome, cidade, valor, descricao)
        mostrar_qr(codigo, "pix")
        print(f"\n{NEG}PIX copia e cola:{RST}\n{codigo}\n")
        if confirmar("Copiar o código?", True):
            copiar_texto(codigo)
        aviso("Confira o nome e o valor no app do banco antes de usar.")

    def contato():
        nome = perguntar("Nome")
        fone = perguntar("Telefone", "")
        email_c = perguntar("E-mail", "")
        vcard = f"BEGIN:VCARD\nVERSION:3.0\nFN:{nome}\n" + (f"TEL:{fone}\n" if fone else "") + \
            (f"EMAIL:{email_c}\n" if email_c else "") + "END:VCARD"
        mostrar_qr(vcard, f"contato_{nome}")

    def ler():
        if not garantir_cmd("zbarimg", "zbar"):
            return
        i = escolher("Ler de onde?", ["Tirar uma foto agora", "Uma imagem do celular (print, foto...)"])
        if i is None:
            return
        if i == 0:
            arq = foto(DATA_DIR / "tmp" / "qr.jpg")
        else:
            arq = escolher_arquivo("Qual imagem?", (".jpg", ".jpeg", ".png", ".webp"))
            if not arq:
                return
        proc = rodar(["zbarimg", "-q", "--raw", str(arq)], capturar=True, timeout=60, mostrar=False)
        conteudo = (proc.stdout or "").strip()
        if not conteudo:
            raise ToonsError("Nenhum QR code encontrado (tente uma foto mais nítida e de perto).")
        print(f"\n{NEG}Conteúdo:{RST}\n{conteudo}\n")
        acoes = ["Copiar", "Abrir o link"] if re.match(r"https?://", conteudo) else ["Copiar"]
        j = escolher("O que fazer?", acoes + ["Nada"])
        if j == 0:
            copiar_texto(conteudo)
        elif j == 1 and len(acoes) == 2:
            abrir_link(conteudo)

    menu("🔳 QR code", [
        ("Gerar de um texto ou link", texto_ou_link),
        ("Gerar de uma rede Wi-Fi (conectar sem digitar senha)", wifi),
        ("Gerar PIX (QR e copia e cola)", pix),
        ("Gerar cartão de contato", contato),
        ("Ler um QR code (câmera ou imagem)", ler),
    ])


# ── Tradutor e dicionário ────────────────────────────────────────────

IDIOMAS = {"pt": "Português", "en": "Inglês", "es": "Espanhol", "fr": "Francês", "it": "Italiano", "de": "Alemão",
           "ja": "Japonês", "ko": "Coreano", "zh-CN": "Chinês", "ru": "Russo", "ar": "Árabe", "nl": "Holandês"}


def traduzir(texto: str, destino: str = "en", origem: str = "auto") -> tuple:
    """(tradução, idioma detectado). Usa o tradutor do Google (sem chave) e o MyMemory se ele falhar."""
    try:
        dados = pedir_json(url_com("https://translate.googleapis.com/translate_a/single", client="gtx", sl=origem,
                                   tl=destino, dt="t", q=texto), timeout=20)
        traducao = "".join(parte[0] for parte in dados[0] if parte and parte[0])
        return traducao, dados[2] if len(dados) > 2 and isinstance(dados[2], str) else origem
    except (ToonsError, TypeError, IndexError):
        de = origem if origem != "auto" else ("en" if destino.startswith("pt") else "pt")
        dados = pedir_json(url_com("https://api.mymemory.translated.net/get", q=texto[:500],
                                   langpair=f"{de}|{destino}"), timeout=20)
        traducao = (dados.get("responseData") or {}).get("translatedText")
        if not traducao:
            raise ToonsError("Não consegui traduzir agora.") from None
        return traducao, de


def falar_em(texto: str, idioma: str) -> None:
    _tapi(["termux-tts-speak", "-l", idioma.split("-")[0]], 180, entrada=texto, json_saida=False)


def dicionario_pt(palavra: str) -> list:
    """Definições do Dicionário Aberto."""
    import html as html_mod
    dados = pedir_json(f"https://api.dicionario-aberto.net/word/{urllib.parse.quote(palavra.lower())}")
    definicoes = []
    for verbete in dados or []:
        for d in re.findall(r"<def>(.*?)</def>", verbete.get("xml", ""), re.S):
            texto = re.sub(r"\s+", " ", html_mod.unescape(re.sub(r"<[^>]+>", " ", d))).replace("_", "").strip()
            definicoes += [linha.strip() for linha in texto.split(";") if linha.strip()][:3]
    return definicoes[:10]


def dicionario_en(palavra: str) -> list:
    try:
        dados = pedir_json(f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(palavra.lower())}")
    except ToonsError:
        return []
    saida = []
    for entrada in dados if isinstance(dados, list) else []:
        for sentido in entrada.get("meanings", []):
            for d in sentido.get("definitions", [])[:2]:
                saida.append(f"({sentido.get('partOfSpeech', '')}) {d.get('definition', '')}"
                             + (f" — ex.: {d['example']}" if d.get("example") else ""))
    return saida[:10]


@submenu
def menu_tradutor():
    c = cfg()

    def destino_atual() -> str:
        return c.get("tradutor_destino", "en")

    def traduzir_loop():
        info(f"Traduzindo para {IDIOMAS.get(destino_atual(), destino_atual())} (o idioma de origem é detectado). "
             "Enter vazio sai.")
        while True:
            texto = perguntar("Texto")
            if not texto:
                return
            traducao, origem = traduzir(texto, destino_atual())
            print(f"  {DIM}[{IDIOMAS.get(origem, origem)} → {IDIOMAS.get(destino_atual(), destino_atual())}]{RST} "
                  f"{NEG}{VERD}{traducao}{RST}")
            if c.get("tradutor_falar"):
                with contextlib.suppress(ToonsError):
                    falar_em(traducao, destino_atual())

    def trocar_idioma():
        codigos = list(IDIOMAS)
        i = escolher("Traduzir para", [f"{IDIOMAS[k]} ({k})" for k in codigos],
                     codigos.index(destino_atual()) + 1 if destino_atual() in codigos else None)
        if i is not None:
            c["tradutor_destino"] = codigos[i]
            salvar_cfg()
            ok(f"Agora traduzindo para {IDIOMAS[codigos[i]]}.")

    def traduzir_area():
        texto = _tapi(["termux-clipboard-get"], 10, json_saida=False)
        if not texto:
            raise ToonsError("A área de transferência está vazia.")
        traducao, origem = traduzir(texto, destino_atual())
        print(f"{DIM}{texto[:300]}{RST}\n\n{NEG}{VERD}{traducao}{RST}")
        if confirmar("Copiar a tradução?", True):
            copiar_texto(traducao)

    def dicionario():
        palavra = perguntar("Palavra")
        if not palavra:
            return
        definicoes = dicionario_pt(palavra) if not re.fullmatch(r"[A-Za-z' -]+", palavra) or \
            escolher("Dicionário", ["Português", "Inglês"]) == 0 else dicionario_en(palavra)
        if not definicoes:
            info("Não encontrei essa palavra.")
        for d in definicoes:
            print(f"  • {d}")

    menu("🌍 Tradutor e dicionário", [
        (lambda: f"Traduzir para {IDIOMAS.get(destino_atual(), destino_atual())}", traduzir_loop),
        ("Trocar o idioma de destino", trocar_idioma),
        ("Traduzir o que está copiado", traduzir_area),
        ("Dicionário (português ou inglês)", dicionario),
        (lambda: f"Falar as traduções em voz alta: {'sim' if c.get('tradutor_falar') else 'não'}",
         lambda: (c.update(tradutor_falar=not c.get("tradutor_falar")), salvar_cfg())),
    ])


@submenu
def menu_utilitarios():
    menu("🧰 Utilitários", [
        ("📝 Bloco de notas", menu_notas),
        ("✅ Lista de tarefas", tarefas_tui),
        ("⏰ Lembretes e alarmes", menu_lembretes),
        ("⏱️ Cronômetro, timer e Pomodoro", menu_relogio),
        ("📅 Calendário e agenda (feriados)", menu_agenda),
        ("💱 Conversor de unidades e moedas", menu_conversor),
        ("💰 Controle de gastos", menu_gastos),
        ("🔐 Gerenciador de senhas", menu_senhas),
        ("🌦️ Previsão do tempo", menu_tempo),
        ("🔳 QR code (Wi-Fi, PIX, ler)", menu_qr),
        ("🌍 Tradutor e dicionário", menu_tradutor),
    ])


# ════════════════════════════════════════════════════════════════════
#  21. Celular e sistema
# ════════════════════════════════════════════════════════════════════

BATERIA_LOG = DATA_DIR / "bateria.csv"
AUTOMACAO_ESTADO = DATA_DIR / "automacao_estado.json"


# ── Saúde da bateria ─────────────────────────────────────────────────

def carregando(b: dict) -> bool:
    return b.get("status") in ("CHARGING", "FULL") or b.get("plugged") not in (None, "", "UNPLUGGED")


def registrar_bateria() -> dict:
    b = bateria()
    linha = ",".join(str(b.get(k, "")) for k in ("percentage", "temperature", "status", "plugged", "current"))
    with open(BATERIA_LOG, "a", encoding="utf-8") as arq:
        arq.write(f"{int(time.time())},{linha}\n")
    return b


def historico_bateria(horas: float | None = None) -> list:
    """[(epoch, %, °C, status, plugged, corrente)] do registro, opcionalmente só das últimas `horas`."""
    if not BATERIA_LOG.exists():
        return []
    desde = time.time() - horas * 3600 if horas else 0
    pontos = []
    for linha in BATERIA_LOG.read_text("utf-8", errors="replace").splitlines():
        partes = linha.split(",")
        if len(partes) < 6:
            continue
        try:
            t, pct = int(partes[0]), int(float(partes[1]))
            temp = float(partes[2]) if partes[2] else None
        except ValueError:
            continue
        if t >= desde:
            pontos.append((t, pct, temp, partes[3], partes[4], partes[5]))
    return pontos


def estatisticas_bateria(pontos: list) -> dict:
    """Ciclos estimados (soma das cargas / 100), consumo médio por hora e temperatura."""
    carregado, gasto, horas_gastando = 0, 0, 0.0
    for (t0, p0, _, s0, pl0, _), (t1, p1, *_) in zip(pontos, pontos[1:]):
        if t1 - t0 > 3 * 3600:
            continue  # buraco no registro (serviço parado): não dá para saber o que houve
        if p1 > p0:
            carregado += p1 - p0
        elif p1 < p0 and not carregando({"status": s0, "plugged": pl0}):
            gasto += p0 - p1
            horas_gastando += (t1 - t0) / 3600
        elif not carregando({"status": s0, "plugged": pl0}):
            horas_gastando += (t1 - t0) / 3600
    temps = [p[2] for p in pontos if p[2] is not None]
    return {"ciclos": carregado / 100, "consumo_hora": gasto / horas_gastando if horas_gastando >= 0.5 else None,
            "temp_max": max(temps, default=None), "temp_media": sum(temps) / len(temps) if temps else None,
            "dias": (pontos[-1][0] - pontos[0][0]) / 86400 if len(pontos) > 1 else 0}


def rodar_bateria() -> None:
    """Serviço: registra a bateria e avisa ao chegar em 80% carregando, bateria baixa ou temperatura alta."""
    log("Registro da bateria iniciado.")
    avisou = {"carga": False, "baixa": False, "temp": 0.0}
    while True:
        c = recarregar_cfg()
        try:
            b = registrar_bateria()
        except ToonsError as e:
            log(f"Não consegui ler a bateria: {e}")
            time.sleep(300)
            continue
        pct, temp, plugado = int(b.get("percentage", 0)), float(b.get("temperature") or 0), carregando(b)
        limite_carga = int(c.get("bateria_alerta_carga", 80))
        if limite_carga and plugado and pct >= limite_carga and not avisou["carga"]:
            notificar_seguro(f"🔌 Bateria em {pct}%", "Pode tirar do carregador: parar perto de 80% faz a bateria "
                             "durar mais.", som=True)
            avisou["carga"] = True
        elif not plugado:
            avisou["carga"] = False
        limite_baixa = int(c.get("bateria_alerta_baixa", 15))
        if limite_baixa and not plugado and pct <= limite_baixa and not avisou["baixa"]:
            notificar_seguro(f"🪫 Bateria em {pct}%", "Hora de carregar.", som=True)
            avisou["baixa"] = True
        elif plugado or pct > limite_baixa:
            avisou["baixa"] = False
        limite_temp = float(c.get("bateria_alerta_temp", 42))
        if limite_temp and temp >= limite_temp and time.time() - avisou["temp"] > 3600:
            notificar_seguro(f"🌡️ Bateria quente: {temp:.0f}°C", "Tire da capa, saia do sol ou pare de carregar "
                             "um pouco.", som=True)
            avisou["temp"] = time.time()
        if BATERIA_LOG.exists() and BATERIA_LOG.stat().st_size > 3_000_000:
            manter = [",".join(map(str, p)) for p in historico_bateria(24 * 60)]
            BATERIA_LOG.write_text("\n".join(manter) + "\n", "utf-8")
        log(f"{pct}% · {temp:.1f}°C · {b.get('status', '')}")
        time.sleep(120 if plugado else 300)


def _corrente_ma(valor) -> str:
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "?"
    return f"{v / 1000:.0f} mA" if abs(v) > 20000 else f"{v:.0f} mA"  # uns aparelhos dão µA, outros mA


@submenu
def menu_bateria():
    c = cfg()

    def agora():
        b = bateria()
        pct = int(b.get("percentage", 0))
        cor = VERD if pct > 50 else AMAR if pct > 20 else VERM
        print(f"\n  {cor}{barra_horizontal(pct / 100, 25)}{RST} {NEG}{pct}%{RST}")
        saude = {"GOOD": "boa", "OVERHEAT": "superaquecida", "DEAD": "ruim", "COLD": "fria",
                 "OVER_VOLTAGE": "tensão alta"}.get(b.get("health"), b.get("health", "?"))
        estado = {"CHARGING": "carregando", "DISCHARGING": "descarregando", "FULL": "cheia",
                  "NOT_CHARGING": "conectada, sem carregar"}.get(b.get("status"), b.get("status", "?"))
        fonte = {"PLUGGED_AC": "tomada", "PLUGGED_USB": "USB", "PLUGGED_WIRELESS": "sem fio",
                 "UNPLUGGED": "nenhuma"}.get(b.get("plugged"), b.get("plugged", "?"))
        print(f"  Estado: {estado} · fonte: {fonte}")
        print(f"  Saúde: {saude} · temperatura: {float(b.get('temperature') or 0):.1f}°C · "
              f"corrente: {_corrente_ma(b.get('current'))}")
        if b.get("cycle") not in (None, -1):
            print(f"  Ciclos de carga (informado pelo Android): {b['cycle']}")
        est = estatisticas_bateria(historico_bateria(24 * 7))
        if est["consumo_hora"] and not carregando(b):
            print(f"  Consumo médio: {est['consumo_hora']:.1f}%/h · dura mais uns "
                  f"{pct / est['consumo_hora']:.0f} h nesse ritmo")
        if not servico_ativo("bateria"):
            info("Ligue o 'Registro da bateria' para ter histórico, gráfico e alertas.")

    def grafico():
        pontos = historico_bateria(24)
        if len(pontos) < 2:
            info("Ainda não há registro suficiente. Inicie o registro e volte em algumas horas.")
            return
        blocos = "▁▂▃▄▅▆▇█"
        agora_t = time.time()
        por_meia_hora = {}
        for t, pct, temp, *_ in pontos:
            por_meia_hora[int((agora_t - t) // 1800)] = (pct, temp)
        faixa = "".join(blocos[min(7, por_meia_hora[k][0] * 8 // 101)] if k in por_meia_hora else " "
                        for k in range(47, -1, -1))
        print(f"\n  Últimas 24 h (cada barra = 30 min):\n  {VERD}{faixa}{RST}\n  {DIM}-24h{' ' * 38}agora{RST}\n")
        for k in range(46, -1, -4):
            if k in por_meia_hora:
                pct, temp = por_meia_hora[k]
                hora = datetime.fromtimestamp(agora_t - k * 1800).strftime("%H:%M")
                print(f"  {hora}  {barra_horizontal(pct / 100, 20)} {pct:>3}%  {DIM}{temp or 0:.0f}°C{RST}")

    def estatisticas():
        pontos = historico_bateria()
        if len(pontos) < 2:
            info("Sem registro ainda.")
            return
        est = estatisticas_bateria(pontos)
        print(f"  Registro de {est['dias']:.1f} dia(s) · {len(pontos)} medições")
        print(f"  Cargas somadas: {est['ciclos']:.1f} ciclo(s) completos (≈ {est['ciclos'] / max(est['dias'], 1):.2f}"
              f" por dia)")
        if est["consumo_hora"]:
            print(f"  Consumo médio fora da tomada: {est['consumo_hora']:.1f}%/h")
        if est["temp_max"] is not None:
            print(f"  Temperatura: média {est['temp_media']:.1f}°C · máxima {est['temp_max']:.1f}°C")
        info("Uma bateria de celular costuma aguentar de 500 a 1000 ciclos antes de perder capacidade.")

    def alertas():
        c["bateria_alerta_carga"] = perguntar_int("Avisar ao carregar até (%; 0 desliga)",
                                                  c.get("bateria_alerta_carga", 80), 0, 100)
        c["bateria_alerta_baixa"] = perguntar_int("Avisar quando cair para (%; 0 desliga)",
                                                  c.get("bateria_alerta_baixa", 15), 0, 99)
        c["bateria_alerta_temp"] = perguntar_int("Avisar se esquentar acima de (°C; 0 desliga)",
                                                 int(c.get("bateria_alerta_temp", 42)), 0, 80)
        salvar_cfg()
        ok("Alertas salvos (valem com o registro da bateria ligado).")

    menu("🔋 Saúde da bateria", [
        ("Bateria agora", agora),
        ("Gráfico das últimas 24 horas", grafico),
        ("Estatísticas (ciclos, consumo, temperatura)", estatisticas),
        ("Configurar alertas (80%, baixa, quente)", alertas),
        *itens_servico("bateria", "Registro da bateria",
                       lambda: iniciar_servico("bateria", cmd_self("bateria-log"), reiniciar=True)),
    ])


# ── Uso de dados e tempo de tela (ADB) ───────────────────────────────

def _segundos_de(texto: str) -> int:
    total = 0
    for parte in texto.split(":"):
        total = total * 60 + int(parte or 0)
    return total


def parse_tempo_de_tela(dump: str, periodo: str = "daily") -> list:
    """[(pacote, segundos, aberturas)] do 'dumpsys usagestats' (bloco diário ou semanal)."""
    inicio = dump.find(f"In-memory {periodo} stats")
    if inicio < 0:
        return []
    fim = dump.find("In-memory", inicio + 10)
    bloco = dump[inicio:fim if fim > 0 else None]
    uso = {}
    for linha in bloco.splitlines():
        m = re.search(r'package=(\S+) totalTime(?:Used)?="([\d:]+)"', linha)
        if not m:
            continue
        aberturas = re.search(r"appLaunchCount=(\d+)", linha)
        s, n = _segundos_de(m.group(2)), int(aberturas.group(1)) if aberturas else 0
        anterior = uso.get(m.group(1), (0, 0))
        uso[m.group(1)] = (max(anterior[0], s), max(anterior[1], n))
    return sorted(((p, s, n) for p, (s, n) in uso.items() if s > 0), key=lambda x: -x[1])


def parse_netstats(dump: str, desde: int) -> dict:
    """{uid: {'movel': bytes, 'wifi': bytes, 'outra': bytes}} da seção 'UID stats' do 'dumpsys netstats detail'."""
    inicio = dump.find("UID stats:")
    if inicio < 0:
        return {}
    fim = dump.find("UID tag stats:", inicio)
    uso, atual = {}, None
    for linha in dump[inicio:fim if fim > 0 else None].splitlines():
        m = re.search(r"ident=\[(.*?)\] uid=(-?\d+) set=\S+ tag=(0x[0-9a-fA-F]+)", linha)
        if m:
            if m.group(3) != "0x0":
                atual = None
                continue
            ident = m.group(1)
            rede = "movel" if re.search(r"type=(?:MOBILE|0)\b|transports=\{0\}", ident) else \
                "wifi" if re.search(r"type=(?:WIFI|1)\b|transports=\{1\}", ident) else "outra"
            atual = uso.setdefault(int(m.group(2)), {"movel": 0, "wifi": 0, "outra": 0}), rede
            continue
        b = re.search(r"st=(\d+) rb=(\d+) rp=\d+ tb=(\d+)", linha)
        if b and atual and int(b.group(1)) >= desde:
            atual[0][atual[1]] += int(b.group(2)) + int(b.group(3))
    return uso


def mapa_uids(lista_pm: str) -> dict:
    """uid → pacote, de 'pm list packages -U'."""
    mapa = {}
    for linha in lista_pm.splitlines():
        m = re.match(r"package:(\S+) uid:([\d,]+)", linha.strip())
        if m:
            for uid in m.group(2).split(","):
                mapa.setdefault(int(uid), m.group(1))
    return mapa


@submenu
def menu_uso_celular():
    def tempo_de_tela(periodo: str):
        info("Lendo as estatísticas de uso pelo ADB...")
        uso = parse_tempo_de_tela(adb_shell("dumpsys usagestats", timeout=120), periodo)
        if not uso:
            raise ToonsError("O Android não devolveu o tempo de uso (versão diferente ou sem permissão).")
        total = sum(s for _, s, _ in uso)
        print(f"\n  Total: {NEG}{fmt_relogio(total)}{RST} {DIM}({'hoje' if periodo == 'daily' else 'esta semana'}){RST}\n")
        maior = uso[0][1]
        for pacote, s, n in uso[:20]:
            print(f"  {fmt_relogio(s):>8} {CIANO}{barra_horizontal(s / maior, 14)}{RST} {pacote}"
                  + (f" {DIM}({n}x){RST}" if n else ""))

    def dados_por_app():
        i = escolher("Período", ["Desde o início do mês", "Últimos 7 dias", "Últimos 30 dias"])
        if i is None:
            return
        hoje = datetime.now()
        desde = int((hoje.replace(day=1, hour=0, minute=0, second=0) if i == 0 else
                     hoje - timedelta(days=7 if i == 1 else 30)).timestamp())
        info("Lendo o uso de dados pelo ADB (pode levar alguns segundos)...")
        uso = parse_netstats(adb_shell("dumpsys netstats detail", timeout=180), desde)
        if not uso:
            raise ToonsError("O Android não devolveu o uso de dados por app (versão diferente ou sem permissão).")
        nomes = mapa_uids(adb_shell("pm list packages -U"))
        nomes.update({0: "root (sistema)", 1000: "Android (sistema)", 1013: "mídia", -5: "tethering (roteador)"})
        linhas = sorted(((nomes.get(uid, f"uid {uid}"), v) for uid, v in uso.items()),
                        key=lambda par: -(par[1]["movel"] + par[1]["wifi"] + par[1]["outra"]))
        movel = sum(v["movel"] for _, v in linhas)
        wifi = sum(v["wifi"] for _, v in linhas)
        print(f"\n  Dados móveis: {NEG}{bytes_humanos(movel)}{RST} · Wi-Fi: {NEG}{bytes_humanos(wifi)}{RST}\n")
        print(f"  {'móvel':>10} {'Wi-Fi':>10}  app")
        for nome, v in linhas[:25]:
            if v["movel"] + v["wifi"] + v["outra"] < 1024 * 100:
                continue
            print(f"  {bytes_humanos(v['movel']):>10} {bytes_humanos(v['wifi']):>10}  {nome}")

    menu("📊 Uso de dados e tempo de tela (pelo ADB)", [
        ("Tempo de tela hoje", lambda: tempo_de_tela("daily")),
        ("Tempo de tela na semana", lambda: tempo_de_tela("weekly")),
        ("Internet gasta por app (móvel e Wi-Fi)", dados_por_app),
    ], cabecalho=lambda: print(f"{DIM}Precisa do ADB conectado (🔌 Depuração sem fio, em Celular e sistema).{RST}"))


# ── Gerenciador de apps (ADB) ────────────────────────────────────────

def listar_pacotes(tipo: str = "-3") -> list:
    return sorted(l.split(":", 1)[1].strip() for l in adb_shell(f"pm list packages {tipo}").splitlines()
                  if l.startswith("package:"))


def info_pacote(pacote: str) -> dict:
    dump = adb_shell(f"dumpsys package {shlex.quote(pacote)}", timeout=60)

    def achar(chave):
        m = re.search(rf"{chave}=(\S+(?: \S+)?)", dump)
        return m.group(1) if m else "?"
    permissoes = re.findall(r"(android\.permission\.[A-Z_]+|[\w.]+\.permission\.[\w.]+): granted=true", dump)
    return {"versão": achar("versionName"), "instalado em": achar("firstInstallTime"),
            "atualizado em": achar("lastUpdateTime"), "Android alvo": achar("targetSdk"),
            "desativado": "enabled=3" in dump or "enabled=2" in dump, "permissões": sorted(set(permissoes))}


@submenu
def menu_apps():
    def acoes(pacote: str):
        while True:
            limpar()
            titulo(f"📦 {pacote}")
            dados = info_pacote(pacote)
            for chave in ("versão", "instalado em", "atualizado em", "Android alvo"):
                print(f"  {CIANO}{chave}{RST}: {dados[chave]}")
            if dados["desativado"]:
                print(f"  {AMAR}(desativado){RST}")
            print()
            opcoes = ["Abrir o app", "Forçar parada", "Ver e revogar permissões", "Extrair o APK para Downloads",
                      "Reativar" if dados["desativado"] else "Desativar (congelar, sem desinstalar)",
                      "Limpar os dados do app (apaga tudo dele!)", "Desinstalar só para mim (bloatware, reversível)",
                      "Desinstalar de vez", "Voltar"]
            i = escolher("O que fazer?", opcoes)
            if i in (None, 8):
                return
            q = shlex.quote(pacote)
            if i == 0:
                print(adb_shell(f"monkey -p {q} -c android.intent.category.LAUNCHER 1")[-200:])
            elif i == 1:
                adb_shell(f"am force-stop {q}")
                ok("Parado.")
            elif i == 2:
                perms = dados["permissões"]
                if not perms:
                    info("Nenhuma permissão perigosa concedida.")
                else:
                    marcadas = escolher_varios("Revogar quais? (Espaço marca)", perms)
                    if marcadas and confirmar(f"Revogar {len(marcadas)} permissão(ões)?", True):
                        for k in marcadas:
                            print(adb_shell(f"pm revoke {q} {perms[k]}") or f"  revogada: {perms[k]}")
            elif i == 3:
                caminhos = [l.split(":", 1)[1] for l in adb_shell(f"pm path {q}").splitlines() if l.startswith("package:")]
                destino = pasta_saida("APKs", pacote)
                for caminho in caminhos:
                    adb("pull", caminho, str(destino / Path(caminho).name), serial=adb_alvo(), timeout=600)
                ok(f"{len(caminhos)} arquivo(s) em {destino}" + (" (APK dividido: instale todos juntos)"
                                                                 if len(caminhos) > 1 else ""))
            elif i == 4:
                cmd = f"pm enable {q}" if dados["desativado"] else f"pm disable-user --user 0 {q}"
                print(adb_shell(cmd))
            elif i == 5 and confirmar(f"Apagar TODOS os dados de {pacote} (login, arquivos, configurações)?", False):
                print(adb_shell(f"pm clear {q}"))
            elif i == 6:
                aviso("Remover app do sistema pode quebrar funções do celular. Volta com 'Reinstalar app removido'.")
                if confirmar(f"Desinstalar {pacote} para o seu usuário?", False):
                    print(adb_shell(f"pm uninstall -k --user 0 {q}"))
                    return
            elif i == 7 and confirmar(f"Desinstalar {pacote} de vez?", False):
                print(adb_shell(f"pm uninstall {q}"))
                return
            pausar()

    def listar(tipo: str, msg: str):
        pacotes = listar_pacotes(tipo)
        filtro = perguntar("Filtrar por nome (Enter = todos)", "")
        pacotes = [p for p in pacotes if filtro.lower() in p.lower()]
        if not pacotes:
            info("Nenhum app encontrado.")
            return
        i = escolher(f"{msg} ({len(pacotes)})", pacotes)
        if i is not None:
            acoes(pacotes[i])

    def reinstalar():
        todos = set(listar_pacotes("-u"))
        instalados = set(listar_pacotes(""))
        removidos = sorted(todos - instalados)
        if not removidos:
            info("Nenhum app removido só para o seu usuário.")
            return
        i = escolher("Reinstalar qual?", removidos)
        if i is not None:
            print(adb_shell(f"cmd package install-existing {shlex.quote(removidos[i])}"))

    menu("📦 Gerenciador de apps (pelo ADB, sem root)", [
        ("Apps que eu instalei", lambda: listar("-3", "Apps instalados")),
        ("Apps do sistema", lambda: listar("-s", "Apps do sistema")),
        ("Apps desativados (para reativar)", lambda: listar("-d", "Apps desativados")),
        ("Reinstalar app removido", reinstalar),
    ], cabecalho=lambda: print(f"{DIM}Precisa do ADB conectado (🔌 Depuração sem fio, em Celular e sistema).{RST}"))


# ── Resolução da tela (root ou ADB) ──────────────────────────────────
# Menos pixels deixam jogos mais leves e gastam menos bateria. A tela inteira muda com 'wm size', e a
# densidade ('wm density') muda na mesma proporção para ícones e letras continuarem do mesmo tamanho. Um
# app sozinho muda no Android 12+ pelas mudanças de compatibilidade DOWNSCALED/DOWNSCALE_xx (qualquer app,
# mas alguns celulares só deixam em apps de teste) ou, no Android 13+, pelo modo de jogo (só jogos).
# Toda mudança volta sozinha se não for confirmada em TEMPO_CONFIRMAR segundos: um vigia em outro processo
# desfaz mesmo que o Termux-Toons feche ou a tela fique impossível de usar.

RESOLUCAO_FILE = DATA_DIR / "resolucao_pendente.json"
TEMPO_CONFIRMAR = 60
_RECUSA_ANDROID = re.compile(r"exception|error|denied|denial|not allowed|cannot|unknown|invalid|not a game|usage:",
                             re.I)


def acesso_shell_android() -> tuple:
    """('root', None) ou ('adb', serial): quem dá a permissão de 'shell'. Conecta a depuração sem fio se precisar."""
    modo = modo_cache_apps()
    if modo is None:
        info("Precisa de root ou da depuração sem fio (ADB pelo Wi-Fi), que dá ao Termux a permissão de 'shell'. "
             "Ligue a 'Depuração por Wi-Fi' nas Opções do desenvolvedor, se estiver desligada.")
        if not adb_conectar():
            raise ToonsError("Sem conexão. Primeira vez? Use 'Depuração sem fio → Parear este celular' e volte aqui.")
        modo = "adb"
    return modo, (adb_alvo() if modo == "adb" else None)


def shell_android(comando: str, modo: str, serial: str | None = None, timeout: float = 60) -> tuple:
    """(código de saída, texto) de um comando rodado com a permissão de 'shell' do Android."""
    cmd = ["su", "-c", comando] if modo == "root" else ["adb", *(["-s", serial] if serial else []), "shell", comando]
    proc = rodar(cmd, capturar=True, timeout=timeout, mostrar=False)
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


def tela_android(modo: str, serial: str | None) -> dict:
    """Resolução e densidade de fábrica ('fisica') e as que valem agora ('atual')."""
    tamanho = shell_android("wm size", modo, serial)[1]
    densidade = shell_android("wm density", modo, serial)[1]
    fisica = re.search(r"Physical size:\s*(\d+)x(\d+)", tamanho)
    dpi_fisica = re.search(r"Physical density:\s*(\d+)", densidade)
    if not fisica or not dpi_fisica:
        raise ToonsError(f"O Android não informou a tela: {(tamanho or densidade)[:200] or 'sem resposta'}")
    atual = re.search(r"Override size:\s*(\d+)x(\d+)", tamanho) or fisica
    dpi_atual = re.search(r"Override density:\s*(\d+)", densidade) or dpi_fisica
    return {"fisica": (int(fisica[1]), int(fisica[2])), "atual": (int(atual[1]), int(atual[2])),
            "dpi_fisica": int(dpi_fisica[1]), "dpi_atual": int(dpi_atual[1]),
            "mudou_tamanho": atual is not fisica, "mudou_dpi": dpi_atual is not dpi_fisica}


def desfazer_resolucao(vigia: str | None = None) -> bool:
    """Desfaz a mudança de resolução que espera confirmação. O vigia (outro processo, com o id da mudança) espera
    o prazo acabar e só desfaz se ninguém confirmou. True se desfez."""
    estado = ler_json(RESOLUCAO_FILE, {})
    if vigia:
        while estado.get("id") == vigia and time.time() < estado["prazo"] + 3:  # folga: quem confirma no fim ganha
            time.sleep(1)
            estado = ler_json(RESOLUCAO_FILE, {})
        if estado.get("id") != vigia:
            return False  # confirmada ou já desfeita
    if not estado:
        return False
    codigo, texto = shell_android(estado["desfazer"], estado["modo"], estado.get("serial"))
    if codigo != 0:  # fica anotada: 'toons resolucao' ou a próxima mudança pelo menu tentam de novo
        aviso(f"Não consegui desfazer ({estado['descricao']}): {texto[-200:] or f'código {codigo}'}. "
              "Rode: toons resolucao")
        return False
    RESOLUCAO_FILE.unlink(missing_ok=True)
    if vigia:
        log(f"Sem confirmação em {TEMPO_CONFIRMAR} s: desfeito ({estado['descricao']}).")
    return True


def mudar_com_prazo(descricao: str, tentativas: list, desfazer: str, modo: str, serial: str | None,
                    depois=None) -> bool:
    """Aplica a primeira forma (comando) que o Android aceitar e pede confirmação; sem ela, desfaz."""
    if ler_json(RESOLUCAO_FILE, {}):  # sobrou uma mudança sem confirmar que não deu para desfazer antes
        desfazer_resolucao()
    estado = {"id": secrets.token_hex(4), "prazo": time.time() + TEMPO_CONFIRMAR, "modo": modo, "serial": serial,
              "desfazer": desfazer, "descricao": descricao}
    gravar_json(RESOLUCAO_FILE, estado)  # antes de mudar: se algo cair no meio, o vigia já sabe desfazer
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / "resolucao.log", "a") as arq_log:
        subprocess.Popen([sys.executable, str(SCRIPT), "resolucao", "--vigiar", estado["id"]],
                         stdin=subprocess.DEVNULL, stdout=arq_log, stderr=subprocess.STDOUT, start_new_session=True)
    manter = False
    try:
        for comando in tentativas:
            codigo, texto = shell_android(comando, modo, serial)
            if codigo == 0 and not _RECUSA_ANDROID.search(texto):
                break
        else:
            raise ToonsError(f"O Android não deixou: {texto[-300:] or f'código {codigo}'}")
        ok(f"Mudou: {descricao}.")
        if depois:
            depois()
        manter = confirmar_no_prazo("Ficou bom? Manter assim?", estado["prazo"])
    finally:
        if manter:
            RESOLUCAO_FILE.unlink(missing_ok=True)
            ok("Mantido.")
        elif desfazer_resolucao():
            info("Desfeito: voltou ao que era.")
    return manter


def _par(valor: float) -> int:
    return max(2, round(valor / 2) * 2)


def mudar_resolucao_tela() -> None:
    modo, serial = acesso_shell_android()
    tela = tela_android(modo, serial)
    (lf, af), (la, aa) = tela["fisica"], tela["atual"]
    print(f"  De fábrica: {NEG}{lf}×{af}{RST} · {tela['dpi_fisica']} dpi")
    if tela["mudou_tamanho"] or tela["mudou_dpi"]:
        print(f"  Agora:      {NEG}{la}×{aa}{RST} · {tela['dpi_atual']} dpi")
    fatores = [0.9, 0.75, 2 / 3, 0.5]
    dicas = {0.9: " (quase igual, um pouco mais leve)", 0.5: " (bem mais leve, perde nitidez)"}
    opcoes = [f"{round(f * 100)}% · {_par(lf * f)}×{_par(af * f)}{dicas.get(f, '')}" for f in fatores]
    i = escolher("Nova resolução", opcoes + ["Digitar a largura em pixels"])
    if i is None:
        return
    if i < len(fatores):
        largura = _par(lf * fatores[i])
    else:
        largura = _par(perguntar_int(f"Largura em pixels ({_par(lf * 0.3)} a {lf})", _par(lf * 0.75),
                                     _par(lf * 0.3), lf))
    altura = _par(af * largura / lf)
    # densidade na mesma proporção da largura: ícones e letras ficam do tamanho que estavam (e o 'Tamanho da
    # exibição' escolhido nas configurações continua valendo)
    dpi = round(tela["dpi_atual"] * largura / la)
    aviso(f"Se a tela ficar estranha, não precisa fazer nada: em {TEMPO_CONFIRMAR} s ela volta sozinha.")
    desfazer = "; ".join([f"wm size {la}x{aa}" if tela["mudou_tamanho"] else "wm size reset",
                          f"wm density {tela['dpi_atual']}" if tela["mudou_dpi"] else "wm density reset"])
    mudar_com_prazo(f"tela em {largura}×{altura} ({dpi} dpi)", [f"wm size {largura}x{altura} && wm density {dpi}"],
                    desfazer, modo, serial)


def resolucao_original(modo: str | None = None, serial: str | None = None) -> None:
    """Volta a tela à resolução de fábrica, com a densidade na proporção de volta (mantém o 'Tamanho da exibição')."""
    if modo is None:
        modo, serial = acesso_shell_android()
    tela = tela_android(modo, serial)
    dpi = round(tela["dpi_atual"] * tela["fisica"][0] / tela["atual"][0])
    densidade = "wm density reset" if abs(dpi - tela["dpi_fisica"]) <= 2 else f"wm density {dpi}"
    codigo, texto = shell_android(f"wm size reset; {densidade}", modo, serial)
    if codigo != 0:
        raise ToonsError(f"O Android não deixou: {texto[-300:] or f'código {codigo}'}")
    ok(f"Tela de volta a {tela['fisica'][0]}×{tela['fisica'][1]}.")


def _sdk_android(modo: str, serial: str | None) -> int:
    texto = shell_android("getprop ro.build.version.sdk", modo, serial)[1]
    return int(texto) if texto.isdigit() else 0


def _escalas_app(sdk: int) -> list:
    """Porcentagens que o Android aceita para um app (o 12 só tem de 10 em 10)."""
    return [90, 85, 80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30] if sdk >= 33 else [90, 80, 70, 60, 50]


def _desfazer_app(pacote: str, sdk: int) -> str:
    q = shlex.quote(pacote)
    comandos = [f"am compat reset DOWNSCALED {q}"] + [f"am compat reset DOWNSCALE_{e} {q}" for e in _escalas_app(sdk)]
    return "; ".join(comandos + ([f"cmd game reset {q}"] if sdk >= 33 else []))


def _escolher_app_android(modo: str, serial: str | None, todos: bool = False) -> str | None:
    """Pacote escolhido entre os apps instalados pela pessoa (ou todos, com os do sistema)."""
    lista = shell_android("pm list packages" + ("" if todos else " -3"), modo, serial)[1]
    pacotes = sorted(l.split(":", 1)[1].strip() for l in lista.splitlines() if l.startswith("package:"))
    filtro = perguntar("Filtrar por nome (ex.: freefire; Enter = todos)", "").replace(" ", "").lower()
    pacotes = [p for p in pacotes if filtro in p.lower()]
    if not pacotes:
        info("Nenhum app encontrado.")
        return None
    i = escolher(f"Qual app? ({len(pacotes)})", pacotes)
    return None if i is None else pacotes[i]


def mudar_resolucao_app() -> None:
    modo, serial = acesso_shell_android()
    sdk = _sdk_android(modo, serial)
    if sdk < 31:
        raise ToonsError("Mudar a resolução de um app só existe no Android 12 ou mais novo. "
                         "Use 'Diminuir a resolução da tela inteira'.")
    pacote = _escolher_app_android(modo, serial)
    if not pacote:
        return
    escalas = _escalas_app(sdk)
    i = escolher(f"Resolução do {pacote}", [f"{e}%" + (" (bem mais leve, perde nitidez)" if e == 50 else "")
                                            for e in escalas])
    if i is None:
        return
    escala, q = escalas[i], shlex.quote(pacote)
    shell_android(_desfazer_app(pacote, sdk), modo, serial)  # tira uma escala anterior (o Android usaria a maior)
    tentativas = [f"am compat enable DOWNSCALED {q} && am compat enable DOWNSCALE_{escala} {q} && am force-stop {q}"]
    if sdk >= 33:  # sem permissão para a forma acima: o modo de jogo (só funciona em jogos)
        modo_jogo = "" if sdk >= 34 else "--mode 2 "
        tentativas.append(f"cmd game set {modo_jogo}--downscale {escala / 100:g} {q}"
                          + ("" if sdk >= 34 else f" && cmd game mode 2 {q}") + f" && am force-stop {q}")

    def abrir_app():
        info(f"Abrindo o app para você ver. Volte ao Termux e confirme em até {TEMPO_CONFIRMAR} s; "
             "sem confirmação o app volta ao normal (se estiver aberto, pode fechar).")
        time.sleep(2)
        shell_android(f"monkey -p {q} -c android.intent.category.LAUNCHER 1", modo, serial)

    mudar_com_prazo(f"{pacote} em {escala}%", tentativas, _desfazer_app(pacote, sdk), modo, serial, abrir_app)


def app_resolucao_normal() -> None:
    modo, serial = acesso_shell_android()
    sdk = _sdk_android(modo, serial)
    if sdk < 31:
        info("Antes do Android 12 não existe resolução por app: nada para desfazer.")
        return
    pacote = _escolher_app_android(modo, serial)
    if pacote:
        shell_android(_desfazer_app(pacote, sdk), modo, serial)
        ok(f"{pacote} de volta à resolução normal (vale na próxima vez que ele abrir).")


@submenu
def menu_resolucao():
    menu("🖥️ Resolução da tela", [
        ("Diminuir a resolução da tela inteira", mudar_resolucao_tela),
        ("Diminuir a resolução de um app (Android 12+)", mudar_resolucao_app),
        ("Voltar a tela à resolução de fábrica", resolucao_original),
        ("Voltar um app à resolução normal", app_resolucao_normal),
    ], cabecalho=lambda: print(f"{DIM}Precisa de root ou da depuração sem fio (🔌). Toda mudança volta sozinha se "
                               f"você não confirmar em {TEMPO_CONFIRMAR} s.{RST}"))


# ── Organizador de fotos ─────────────────────────────────────────────

EXT_IMAGEM = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".bmp", ".gif")


def _pasta_fotos() -> Path:
    for p in (HOME / "storage" / "dcim" / "Camera", HOME / "storage" / "dcim", HOME / "storage" / "pictures"):
        if p.exists():
            return p
    return HOME


def data_da_foto(caminho: Path) -> datetime:
    """Data em que a foto foi tirada (EXIF), ou a data do arquivo."""
    with contextlib.suppress(Exception):
        from PIL import Image
        with Image.open(caminho) as img:
            exif = img.getexif()
            texto = exif.get_ifd(0x8769).get(36867) or exif.get(306)
            if texto:
                return datetime.strptime(str(texto)[:19], "%Y:%m:%d %H:%M:%S")
    return datetime.fromtimestamp(caminho.stat().st_mtime)


def dhash(caminho: Path) -> int | None:
    """Impressão digital visual de 64 bits: fotos parecidas têm números com poucos bits diferentes."""
    try:
        from PIL import Image
        with Image.open(caminho) as img:
            cinza = img.convert("L").resize((9, 8))
            px = list(cinza.getdata())
    except Exception:  # noqa: BLE001 — arquivo que o Pillow não abre fica de fora
        return None
    bits = 0
    for linha in range(8):
        for col in range(8):
            bits = (bits << 1) | (px[linha * 9 + col] > px[linha * 9 + col + 1])
    return bits


def agrupar_parecidas(hashes: dict, limite: int = 6) -> list:
    """Grupos de caminhos cujas impressões digitais diferem em até `limite` bits."""
    itens = list(hashes.items())
    grupos, usados = [], set()
    for i, (a, ha) in enumerate(itens):
        if a in usados:
            continue
        grupo = [a] + [b for b, hb in itens[i + 1:] if b not in usados and bin(ha ^ hb).count("1") <= limite]
        if len(grupo) > 1:
            usados.update(grupo)
            grupos.append(grupo)
    return grupos


@submenu
def menu_fotos():
    estado = {"pasta": _pasta_fotos()}

    def fotos(recursivo: bool = False) -> list:
        pasta = estado["pasta"]
        arquivos = pasta.rglob("*") if recursivo else pasta.iterdir()
        return sorted((a for a in arquivos if a.is_file() and a.suffix.lower() in EXT_IMAGEM),
                      key=lambda a: a.stat().st_mtime, reverse=True)

    def precisa_pillow() -> bool:
        return garantir_modulo("PIL", pip_nome="pillow", pkg_nome="python-pillow",
                               aviso_extra="O Pillow lê e grava as imagens.")

    def trocar_pasta():
        opcoes = [p for p in (HOME / "storage" / "dcim" / "Camera", HOME / "storage" / "dcim",
                              HOME / "storage" / "pictures", HOME / "storage" / "downloads",
                              HOME / "storage" / "shared" / "Pictures" / "Screenshots") if p.exists()]
        i = escolher("Pasta das fotos", [str(p) for p in opcoes] + ["Digitar outra..."])
        if i is None:
            return
        pasta = opcoes[i] if i < len(opcoes) else Path(os.path.expanduser(perguntar("Pasta")))
        if not pasta.is_dir():
            raise ToonsError("Pasta não encontrada.")
        estado["pasta"] = pasta

    def organizar():
        lista = fotos()
        if not lista:
            info("Nenhuma foto nessa pasta.")
            return
        mover = escolher("Como organizar?", [
            "Copiar para Downloads/Termux-Toons/Fotos por data (as originais ficam onde estão)",
            f"Mover para subpastas ano/mês dentro de {estado['pasta'].name}"]) == 1
        if precisa_pillow() is False:
            aviso("Sem o Pillow: uso a data do arquivo em vez da data da foto.")
        base = estado["pasta"] if mover else pasta_saida("Fotos por data")
        feitos = 0
        for arq in lista:
            quando = data_da_foto(arq)
            destino = base / f"{quando:%Y}" / f"{quando:%m}"
            destino.mkdir(parents=True, exist_ok=True)
            alvo = destino / arq.name
            if alvo.exists():
                continue
            (shutil.move if mover else shutil.copy2)(str(arq), str(alvo))
            feitos += 1
            print(f"\r  {feitos}/{len(lista)}", end="", flush=True)
        print()
        ok(f"{feitos} foto(s) {'movida(s)' if mover else 'copiada(s)'} para {base}/ano/mês.")

    def duplicadas():
        lista = fotos(recursivo=True)
        por_tamanho = {}
        for a in lista:
            por_tamanho.setdefault(a.stat().st_size, []).append(a)
        grupos = {}
        for candidatos in (g for g in por_tamanho.values() if len(g) > 1):
            for a in candidatos:
                grupos.setdefault(_hash_arquivo(a), []).append(a)
        grupos = [sorted(g, key=lambda a: a.stat().st_mtime) for g in grupos.values() if len(g) > 1]
        if not grupos:
            ok("Nenhuma foto repetida (idêntica).")
            return
        sobra = [a for g in grupos for a in g[1:]]
        for g in grupos[:15]:
            print(f"  {CIANO}•{RST} {g[0].name} {DIM}+ {len(g) - 1} cópia(s){RST}")
        espaco = sum(a.stat().st_size for a in sobra)
        if confirmar(f"Apagar as {len(sobra)} cópias e liberar {bytes_humanos(espaco)}? (fica a mais antiga)", False):
            for a in sobra:
                a.unlink(missing_ok=True)
            ok("Cópias apagadas.")

    def parecidas():
        if not precisa_pillow():
            return
        lista = fotos()[:600]
        info(f"Comparando {len(lista)} fotos...")
        hashes = {}
        for n, a in enumerate(lista, 1):
            h = dhash(a)
            if h is not None:
                hashes[a] = h
            if n % 20 == 0:
                print(f"\r  {n}/{len(lista)}", end="", flush=True)
        print()
        grupos = agrupar_parecidas(hashes)
        if not grupos:
            ok("Nenhuma foto parecida encontrada.")
            return
        info(f"{len(grupos)} grupo(s) de fotos parecidas (rajadas, repetidas, prints iguais).")
        for n, grupo in enumerate(grupos, 1):
            limpar()
            titulo(f"Grupo {n} de {len(grupos)}")
            marcadas = escolher_varios("Marque as que quer APAGAR (Espaço) e Enter; Esc pula o grupo",
                                       [_rotulo_arquivo(a) for a in grupo])
            if len(marcadas) == len(grupo):
                aviso("Você marcou todas: nenhuma foi apagada nesse grupo.")
            elif marcadas and confirmar(f"Apagar {len(marcadas)} foto(s)?", False):
                for k in marcadas:
                    grupo[k].unlink(missing_ok=True)

    def comprimir():
        if not precisa_pillow():
            return
        from PIL import Image, ImageOps
        lista = escolher_arquivos("Quais fotos comprimir? (Espaço marca, a = todas)", EXT_IMAGEM,
                                  [(estado["pasta"], 1)])
        if not lista:
            return
        lado = perguntar_int("Lado maior em pixels (1920 = Full HD)", 1920, 320, 8000)
        qualidade = perguntar_int("Qualidade JPEG (60 a 95)", 80, 30, 100)
        destino = pasta_saida("Fotos comprimidas")
        antes = depois = 0
        for a in lista:
            with Image.open(a) as img:
                img = ImageOps.exif_transpose(img).convert("RGB")
                img.thumbnail((lado, lado))
                alvo = destino / (a.stem + ".jpg")
                img.save(alvo, "JPEG", quality=qualidade, optimize=True)
            antes += a.stat().st_size
            depois += alvo.stat().st_size
        ok(f"{len(lista)} foto(s): {bytes_humanos(antes)} → {bytes_humanos(depois)} em {destino}")

    def sem_localizacao():
        if not precisa_pillow():
            return
        from PIL import Image
        lista = escolher_arquivos("Quais fotos? (Espaço marca)", (".jpg", ".jpeg", ".webp", ".png"),
                                  [(estado["pasta"], 1)])
        destino = pasta_saida("Fotos sem localização")
        for a in lista:
            with Image.open(a) as img:
                exif = img.getexif()
                exif.pop(0x8825, None)  # bloco GPS
                img.save(destino / a.name, exif=exif.tobytes(), **({"quality": 95} if a.suffix.lower() in
                                                                      (".jpg", ".jpeg") else {}))
        ok(f"{len(lista)} foto(s) sem a localização em {destino}. Compartilhe essas cópias.")

    menu("📸 Organizador de fotos", [
        (lambda: f"Pasta: {estado['pasta']}", trocar_pasta),
        ("Organizar por data (ano/mês)", organizar),
        ("Achar fotos repetidas (idênticas)", duplicadas),
        ("Achar fotos parecidas (rajadas, prints)", parecidas),
        ("Comprimir fotos (para enviar ou guardar)", comprimir),
        ("Tirar a localização (GPS) antes de compartilhar", sem_localizacao),
    ])


# ── Conversor de arquivos ────────────────────────────────────────────

EXT_VIDEO = (".mp4", ".mkv", ".webm", ".mov", ".avi", ".3gp", ".m4v")
EXT_AUDIO = (".mp3", ".m4a", ".opus", ".ogg", ".wav", ".flac", ".aac", ".amr", ".wma")
EXT_DOC = (".docx", ".doc", ".odt", ".rtf", ".pptx", ".ppt", ".odp", ".xlsx", ".xls", ".ods")


def _saida_convertida(origem: Path, extensao: str, sufixo: str = "") -> Path:
    destino = pasta_saida("Convertidos") / f"{origem.stem}{sufixo}{extensao}"
    n = 2
    while destino.exists():
        destino = destino.with_name(f"{origem.stem}{sufixo}_{n}{extensao}")
        n += 1
    return destino


def _ffmpeg(*args) -> None:
    if not garantir_cmd("ffmpeg"):
        raise ToonsError("O ffmpeg é necessário.")
    proc = rodar(["ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y", *map(str, args)], mostrar=False)
    if proc.returncode != 0:
        raise ToonsError("O ffmpeg não conseguiu converter esse arquivo.")


@submenu
def menu_conversor_arquivos():
    def pillow() -> bool:
        return garantir_modulo("PIL", pip_nome="pillow", pkg_nome="python-pillow")

    def imagem():
        if not pillow():
            return
        from PIL import Image, ImageOps
        arq = escolher_arquivo("Qual imagem?", EXT_IMAGEM)
        if not arq:
            return
        formatos = [("JPG", ".jpg", "JPEG"), ("PNG", ".png", "PNG"), ("WEBP", ".webp", "WEBP"), ("PDF", ".pdf", "PDF")]
        i = escolher("Converter para", [f[0] for f in formatos])
        if i is None:
            return
        lado = perguntar_int("Redimensionar: lado maior em pixels (0 = manter)", 0, 0, 20000)
        with Image.open(arq) as img:
            img = ImageOps.exif_transpose(img)
            if formatos[i][2] in ("JPEG", "PDF"):
                img = img.convert("RGB")
            if lado:
                img.thumbnail((lado, lado))
            destino = _saida_convertida(arq, formatos[i][1])
            img.save(destino, formatos[i][2], **({"quality": 90} if formatos[i][2] in ("JPEG", "WEBP") else {}))
        ok(f"Salvo: {destino}")

    def imagens_para_pdf():
        if not pillow():
            return
        from PIL import Image, ImageOps
        lista = escolher_arquivos("Quais imagens? (Espaço marca; a ordem é a da lista)", EXT_IMAGEM)
        if not lista:
            return
        paginas = []
        for a in lista:
            with Image.open(a) as img:
                paginas.append(ImageOps.exif_transpose(img).convert("RGB"))
        destino = _saida_convertida(lista[0], ".pdf", "_documento")
        paginas[0].save(destino, "PDF", save_all=True, append_images=paginas[1:], resolution=150)
        ok(f"PDF com {len(paginas)} página(s): {destino}")

    def video_gif():
        arq = escolher_arquivo("Qual vídeo?", EXT_VIDEO)
        if not arq:
            return
        inicio = perguntar("Começar em (segundos ou mm:ss)", "0")
        duracao = perguntar_int("Duração do GIF (segundos)", 5, 1, 60)
        largura = perguntar_int("Largura (px)", 480, 120, 1080)
        destino = _saida_convertida(arq, ".gif")
        filtro = (f"fps=12,scale={largura}:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse")
        _ffmpeg("-ss", parse_duracao(inicio, "s") if inicio.strip() else 0, "-t", duracao, "-i", arq,
                "-vf", filtro, "-loop", "0", destino)
        ok(f"GIF salvo: {destino} ({bytes_humanos(destino.stat().st_size)})")

    def audio(origem_exts: tuple, msg: str):
        arq = escolher_arquivo(msg, origem_exts)
        if not arq:
            return
        formatos = [("MP3", ".mp3", ["-c:a", "libmp3lame", "-q:a", "2"]), ("M4A (AAC)", ".m4a", ["-c:a", "aac", "-b:a", "192k"]),
                    ("OPUS", ".opus", ["-c:a", "libopus", "-b:a", "128k"]), ("WAV", ".wav", []),
                    ("FLAC", ".flac", ["-c:a", "flac"])]
        i = escolher("Converter para", [f[0] for f in formatos])
        if i is None:
            return
        destino = _saida_convertida(arq, formatos[i][1])
        _ffmpeg("-i", arq, "-vn", *formatos[i][2], destino)
        ok(f"Salvo: {destino}")

    def comprimir_video():
        arq = escolher_arquivo("Qual vídeo?", EXT_VIDEO)
        if not arq:
            return
        alturas = [("720p (bom para WhatsApp)", 720), ("480p (bem menor)", 480), ("1080p", 1080)]
        i = escolher("Resolução", [a for a, _ in alturas])
        if i is None:
            return
        destino = _saida_convertida(arq, ".mp4", f"_{alturas[i][1]}p")
        info("Comprimindo (vídeos longos demoram; deixe a tela ligada)...")
        _ffmpeg("-i", arq, "-vf", f"scale=-2:'min({alturas[i][1]},ih)'", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "28", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", destino)
        ok(f"{bytes_humanos(arq.stat().st_size)} → {bytes_humanos(destino.stat().st_size)}: {destino}")

    def pdf_juntar():
        if not garantir_cmd("qpdf"):
            return
        lista = escolher_arquivos("Quais PDFs juntar? (Espaço marca; a ordem é a da lista)", (".pdf",))
        if len(lista) < 2:
            raise ToonsError("Marque pelo menos dois PDFs.")
        destino = _saida_convertida(lista[0], ".pdf", "_juntado")
        rodar(["qpdf", "--empty", "--pages", *map(str, lista), "--", str(destino)], check=True, capturar=True)
        ok(f"PDF juntado: {destino}")

    def pdf_paginas():
        if not garantir_cmd("qpdf"):
            return
        arq = escolher_arquivo("Qual PDF?", (".pdf",))
        if not arq:
            return
        total = saida(["qpdf", "--show-npages", str(arq)])
        i = escolher(f"O PDF tem {total} página(s)", ["Separar páginas (ex.: 1-3,5)", "Uma página por arquivo"])
        if i == 0:
            paginas = perguntar("Quais páginas? (ex.: 1-3,5,8-z; z = última)")
            destino = _saida_convertida(arq, ".pdf", "_paginas")
            rodar(["qpdf", str(arq), "--pages", ".", paginas, "--", str(destino)], check=True, capturar=True)
            ok(f"Salvo: {destino}")
        elif i == 1:
            pasta = pasta_saida("Convertidos", arq.stem)
            rodar(["qpdf", "--split-pages", str(arq), str(pasta / f"{arq.stem}-%d.pdf")], check=True, capturar=True)
            ok(f"Páginas separadas em {pasta}")

    def pdf_comprimir():
        if not garantir_cmd("gs", "ghostscript"):
            return
        arq = escolher_arquivo("Qual PDF?", (".pdf",))
        if not arq:
            return
        niveis = [("Média (bom para e-mail)", "/ebook"), ("Máxima (menor, imagens piores)", "/screen"),
                  ("Leve (para imprimir)", "/printer")]
        i = escolher("Compressão", [n for n, _ in niveis])
        if i is None:
            return
        destino = _saida_convertida(arq, ".pdf", "_comprimido")
        rodar(["gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4", f"-dPDFSETTINGS={niveis[i][1]}", "-dNOPAUSE",
               "-dQUIET", "-dBATCH", f"-sOutputFile={destino}", str(arq)], check=True)
        ok(f"{bytes_humanos(arq.stat().st_size)} → {bytes_humanos(destino.stat().st_size)}: {destino}")

    def pdf_para_imagens():
        if not garantir_cmd("pdftoppm", "poppler"):
            return
        arq = escolher_arquivo("Qual PDF?", (".pdf",))
        if not arq:
            return
        pasta = pasta_saida("Convertidos", f"{arq.stem}_imagens")
        rodar(["pdftoppm", "-png", "-r", "120", str(arq), str(pasta / "pagina")], check=True)
        ok(f"Imagens em {pasta}")

    def pdf_para_texto():
        if not garantir_cmd("pdftotext", "poppler"):
            return
        arq = escolher_arquivo("Qual PDF?", (".pdf",))
        if not arq:
            return
        destino = _saida_convertida(arq, ".txt")
        rodar(["pdftotext", "-layout", str(arq), str(destino)], check=True)
        ok(f"Texto salvo: {destino}")

    def documento_pdf():
        arq = escolher_arquivo("Qual documento?", EXT_DOC)
        if not arq:
            return
        distros = distros_instaladas()
        if not distros:
            raise ToonsError("Converter Word/Excel/PowerPoint em PDF usa o LibreOffice, que roda numa distro Linux. "
                             "Instale uma (Debian é a mais leve) no menu 🐧 Linux de verdade e tente de novo.")
        distro = distros[0] if len(distros) == 1 else distros[escolher("Qual distro?", distros) or 0]
        tem_office = rodar(["proot-distro", "login", distro, "--", "sh", "-c", "command -v soffice"],
                           capturar=True, timeout=120).returncode == 0
        if not tem_office:
            aviso("O LibreOffice não está na distro (são uns 500 MB).")
            if not confirmar("Instalar agora?", True):
                return
            rodar(["proot-distro", "login", distro, "--", "sh", "-c",
                   "(apt-get update && apt-get install -y libreoffice-writer libreoffice-calc libreoffice-impress) || "
                   "(pacman -Sy --noconfirm libreoffice-fresh) || (apk add libreoffice) || (dnf install -y libreoffice)"])
        tmp = Path(os.environ.get("TMPDIR", PREFIX + "/tmp" if PREFIX else "/tmp")) / "toons_doc"
        tmp.mkdir(parents=True, exist_ok=True)
        shutil.copy2(arq, tmp / arq.name)
        info("Convertendo com o LibreOffice (a primeira vez demora)...")
        rodar(["proot-distro", "login", distro, "--shared-tmp", "--", "soffice", "--headless", "--convert-to", "pdf",
               "--outdir", "/tmp/toons_doc", f"/tmp/toons_doc/{arq.name}"], timeout=900)
        pdf = tmp / (arq.stem + ".pdf")
        if not pdf.exists():
            raise ToonsError("O LibreOffice não gerou o PDF.")
        destino = _saida_convertida(arq, ".pdf")
        shutil.move(str(pdf), destino)
        ok(f"PDF salvo: {destino}")

    menu("🔁 Conversor de arquivos", [
        ("🖼️ Imagem: trocar formato / redimensionar (JPG, PNG, WEBP, PDF)", imagem),
        ("🖼️ Várias imagens → um PDF (documento escaneado)", imagens_para_pdf),
        ("🎬 Vídeo → GIF", video_gif),
        ("🎬 Vídeo → áudio (MP3, M4A...)", lambda: audio(EXT_VIDEO, "De qual vídeo?")),
        ("🎬 Comprimir vídeo (720p/480p)", comprimir_video),
        ("🎵 Áudio → outro formato (ex.: áudio do WhatsApp .opus → MP3)", lambda: audio(EXT_AUDIO, "Qual áudio?")),
        ("📄 PDF: juntar vários", pdf_juntar),
        ("📄 PDF: separar páginas", pdf_paginas),
        ("📄 PDF: comprimir", pdf_comprimir),
        ("📄 PDF → imagens (PNG)", pdf_para_imagens),
        ("📄 PDF → texto", pdf_para_texto),
        ("📄 Word/Excel/PowerPoint → PDF (LibreOffice na distro)", documento_pdf),
    ])


# ── Automação por eventos ────────────────────────────────────────────

GATILHOS = {
    "horario": "Num horário (todo dia ou em dias da semana)",
    "intervalo": "A cada X minutos",
    "wifi_conectar": "Ao conectar num Wi-Fi",
    "wifi_desconectar": "Ao sair de um Wi-Fi",
    "carregando": "Ao começar a carregar",
    "descarregando": "Ao tirar do carregador",
    "bateria_abaixo": "Bateria caiu abaixo de X%",
    "bateria_acima": "Bateria subiu acima de X%",
}
ACOES = {
    "notificar": "Mostrar uma notificação",
    "falar": "Falar um texto",
    "vibrar": "Vibrar",
    "volume": "Mudar o volume",
    "lanterna": "Ligar/desligar a lanterna",
    "abrir_link": "Abrir um link",
    "telegram": "Mandar mensagem no Telegram (bot configurado)",
    "comando": "Rodar um comando do Termux",
}


def descrever_automacao(a: dict) -> str:
    g, ac = a["gatilho"], a["acao"]
    quando = {
        "horario": lambda: f"às {g['hora']}" + ("" if len(g.get("dias", [])) in (0, 7) else
                                                 " (" + ",".join(DIAS_SEMANA[d][:3] for d in g["dias"]) + ")"),
        "intervalo": lambda: f"a cada {g['minutos']} min",
        "wifi_conectar": lambda: f"ao conectar em {g.get('ssid') or 'qualquer Wi-Fi'}",
        "wifi_desconectar": lambda: f"ao sair de {g.get('ssid') or 'qualquer Wi-Fi'}",
        "carregando": lambda: "ao começar a carregar", "descarregando": lambda: "ao tirar do carregador",
        "bateria_abaixo": lambda: f"bateria < {g['limite']}%", "bateria_acima": lambda: f"bateria > {g['limite']}%",
    }[g["tipo"]]()
    return f"{quando} → {ACOES[ac['tipo']].lower()}" + (f": {ac.get('texto') or ac.get('valor') or ''}"[:60]
                                                         if ac.get("texto") or ac.get("valor") else "")


def executar_acao(acao: dict) -> None:
    tipo = acao["tipo"]
    if tipo == "notificar":
        notificar("Termux-Toons", acao["texto"], som=True)
    elif tipo == "falar":
        falar(acao["texto"])
    elif tipo == "vibrar":
        vibrar(int(acao.get("valor") or 800))
    elif tipo == "volume":
        _tapi(["termux-volume", acao["fluxo"], str(acao["valor"])], 15, json_saida=False)
    elif tipo == "lanterna":
        lanterna(acao["valor"] == "on")
    elif tipo == "abrir_link":
        abrir_link(acao["valor"])
    elif tipo == "telegram":
        c = cfg()
        if not c.get("telegram_token") or not c.get("telegram_ids_permitidos"):
            raise ToonsError("Configure o bot do Telegram primeiro (menu Bots).")
        for chat in c["telegram_ids_permitidos"]:
            tg_enviar_texto(c["telegram_token"], chat, acao["texto"])
    elif tipo == "comando":
        proc = rodar(acao["valor"], capturar=True, timeout=600, mostrar=False)
        log(f"comando terminou com código {proc.returncode}: {(proc.stdout or '')[-300:]}")
    else:
        raise ToonsError(f"Ação desconhecida: {tipo}")


def gatilhos_disparados(automacoes: list, anterior: dict, atual: dict, agora: datetime, ja_rodou: dict) -> list:
    """Automações cujo gatilho aconteceu entre o estado `anterior` e o `atual` (funções puras, para testar)."""
    disparar = []
    for a in automacoes:
        if not a.get("ativo", True):
            continue
        g, ident = a["gatilho"], a["id"]
        tipo = g["tipo"]
        if tipo == "horario":
            dias = g.get("dias") or list(range(7))
            chave = agora.strftime("%Y-%m-%d")
            if agora.strftime("%H:%M") >= g["hora"] and agora.weekday() in dias and ja_rodou.get(ident) != chave \
                    and agora - datetime.combine(agora.date(), datetime.strptime(g["hora"], "%H:%M").time()) \
                    < timedelta(minutes=10):
                ja_rodou[ident] = chave
                disparar.append(a)
        elif tipo == "intervalo":
            if agora.timestamp() - float(ja_rodou.get(ident, 0)) >= int(g["minutos"]) * 60:
                ja_rodou[ident] = agora.timestamp()
                disparar.append(a)
        elif not anterior:
            continue  # primeira leitura: ainda não há mudança para comparar
        elif tipo in ("wifi_conectar", "wifi_desconectar"):
            alvo = g.get("ssid") or None
            antes, depois = anterior.get("ssid"), atual.get("ssid")
            if antes == depois:
                continue
            if tipo == "wifi_conectar" and depois and (alvo is None or depois == alvo):
                disparar.append(a)
            elif tipo == "wifi_desconectar" and antes and (alvo is None or antes == alvo):
                disparar.append(a)
        elif tipo in ("carregando", "descarregando"):
            if anterior.get("carregando") is not None and anterior.get("carregando") != atual.get("carregando") \
                    and atual.get("carregando") == (tipo == "carregando"):
                disparar.append(a)
        elif tipo in ("bateria_abaixo", "bateria_acima") and anterior.get("pct") is not None:
            limite = int(g["limite"])
            if tipo == "bateria_abaixo" and anterior["pct"] >= limite > atual["pct"]:
                disparar.append(a)
            elif tipo == "bateria_acima" and anterior["pct"] <= limite < atual["pct"]:
                disparar.append(a)
    return disparar


def _estado_do_celular(automacoes: list) -> dict:
    tipos = {a["gatilho"]["tipo"] for a in automacoes if a.get("ativo", True)}
    estado = {}
    if tipos & {"wifi_conectar", "wifi_desconectar"}:
        with contextlib.suppress(ToonsError):
            w = _tapi(["termux-wifi-connectioninfo"], 20)
            ssid = (w.get("ssid") or "").strip('"') if isinstance(w, dict) else ""
            conectado = isinstance(w, dict) and w.get("supplicant_state") == "COMPLETED"
            estado["ssid"] = ssid if conectado and ssid not in ("", "<unknown ssid>") else None
    if tipos & {"carregando", "descarregando", "bateria_abaixo", "bateria_acima"}:
        with contextlib.suppress(ToonsError):
            b = bateria()
            estado["pct"], estado["carregando"] = int(b.get("percentage", 0)), carregando(b)
    return estado


def rodar_automacoes() -> None:
    """Laço do serviço de automação (roda dentro do tmux)."""
    log("Automação iniciada.")
    persistido = ler_json(AUTOMACAO_ESTADO, {})
    ja_rodou, anterior = persistido.get("ja_rodou", {}), {}
    while True:
        automacoes = recarregar_cfg().get("automacoes", [])
        atual = _estado_do_celular(automacoes)
        for a in gatilhos_disparados(automacoes, anterior, atual, datetime.now(), ja_rodou):
            log(f"▶ {a['nome']}: {descrever_automacao(a)}")
            try:
                executar_acao(a["acao"])
            except Exception as e:  # noqa: BLE001 — uma automação com erro não derruba as outras
                log(f"  erro: {e}")
        anterior = {**anterior, **atual}
        gravar_json(AUTOMACAO_ESTADO, {"ja_rodou": ja_rodou})
        time.sleep(20)


@submenu
def menu_automacao():
    c = cfg()
    c.setdefault("automacoes", [])

    def pedir_gatilho() -> dict | None:
        chaves = list(GATILHOS)
        i = escolher("Quando?", list(GATILHOS.values()))
        if i is None:
            return None
        tipo = chaves[i]
        g = {"tipo": tipo}
        if tipo == "horario":
            hora = perguntar("Hora (hh:mm)", "07:00").replace("h", ":")
            m = re.fullmatch(r"(\d{1,2}):?(\d{2})?", hora)
            if not m or int(m.group(1)) > 23:
                raise ToonsError("Hora inválida.")
            g["hora"] = f"{int(m.group(1)):02d}:{m.group(2) or '00'}"
            dias = escolher_varios("Em quais dias? (Espaço marca, a = todos)",
                                   [d.capitalize() for d in DIAS_SEMANA])
            g["dias"] = sorted(dias)
        elif tipo == "intervalo":
            g["minutos"] = perguntar_int("A cada quantos minutos", 60, 1, 10080)
        elif tipo.startswith("wifi"):
            atual = ""
            with contextlib.suppress(ToonsError, AttributeError):
                atual = (_tapi(["termux-wifi-connectioninfo"], 20).get("ssid") or "").strip('"')
            g["ssid"] = perguntar("Nome da rede (Enter = qualquer uma)", atual if atual != "<unknown ssid>" else "")
        elif tipo.startswith("bateria"):
            g["limite"] = perguntar_int("Limite (%)", 20 if tipo == "bateria_abaixo" else 80, 1, 99)
        return g

    def pedir_acao() -> dict | None:
        chaves = list(ACOES)
        i = escolher("Fazer o quê?", list(ACOES.values()))
        if i is None:
            return None
        tipo = chaves[i]
        a = {"tipo": tipo}
        if tipo in ("notificar", "falar", "telegram"):
            a["texto"] = perguntar("Texto")
        elif tipo == "vibrar":
            a["valor"] = perguntar_int("Duração (ms)", 800, 50, 5000)
        elif tipo == "volume":
            fluxos = ["music", "ring", "notification", "alarm", "system", "call"]
            nomes = ["Mídia (música/vídeo)", "Toque", "Notificações", "Alarme", "Sistema", "Chamada"]
            k = escolher("Qual volume?", nomes)
            if k is None:
                return None
            a["fluxo"], a["valor"] = fluxos[k], perguntar_int("Nível (0 = mudo; o máximo costuma ser 15)", 0, 0, 30)
        elif tipo == "lanterna":
            a["valor"] = "on" if confirmar("Ligar? (Não = desligar)", True) else "off"
        elif tipo == "abrir_link":
            a["valor"] = perguntar("Link")
        elif tipo == "comando":
            a["valor"] = perguntar("Comando (ex.: termux-wifi-enable false)")
        return a

    def nova():
        g = pedir_gatilho()
        a = g and pedir_acao()
        if not a:
            return
        auto = {"id": uuid.uuid4().hex[:8], "gatilho": g, "acao": a, "ativo": True}
        auto["nome"] = perguntar("Nome da automação", descrever_automacao(auto)[:40])
        c["automacoes"].append(auto)
        salvar_cfg()
        ok(f"Automação criada: {descrever_automacao(auto)}")
        if not servico_ativo("automacao") and confirmar("Iniciar o serviço de automação agora?", True):
            iniciar_servico("automacao", cmd_self("automacao"), reiniciar=True)

    def escolher_auto(msg: str) -> dict | None:
        if not c["automacoes"]:
            info("Nenhuma automação ainda.")
            return None
        i = escolher(msg, [f"{'✅' if a.get('ativo', True) else '⏸️'} {a['nome']}  {DIM}{descrever_automacao(a)}{RST}"
                           for a in c["automacoes"]])
        return None if i is None else c["automacoes"][i]

    def alternar():
        a = escolher_auto("Ligar/desligar qual?")
        if a:
            a["ativo"] = not a.get("ativo", True)
            salvar_cfg()
            ok(f"'{a['nome']}' {'ligada' if a['ativo'] else 'desligada'}.")

    def testar():
        a = escolher_auto("Testar a ação de qual?")
        if a:
            executar_acao(a["acao"])
            ok("Ação executada.")

    def apagar_auto():
        a = escolher_auto("Apagar qual?")
        if a and confirmar(f"Apagar '{a['nome']}'?", False):
            c["automacoes"].remove(a)
            salvar_cfg()
            ok("Apagada.")

    menu("🤖 Automação por eventos (um 'Tasker' no Termux)", [
        ("Nova automação", nova),
        (lambda: f"Ligar/desligar automações ({len(c['automacoes'])})", alternar),
        ("Testar a ação de uma automação", testar),
        ("Apagar automação", apagar_auto),
        *itens_servico("automacao", "Serviço de automação",
                       lambda: iniciar_servico("automacao", cmd_self("automacao"), reiniciar=True)),
    ], cabecalho=lambda: print(f"{DIM}Ex.: ao conectar no Wi-Fi de casa → volume no máximo · 23h → modo silencioso"
                               f" · bateria < 20% → falar 'carregue o celular'{RST}"))


# ── Espelhar e controlar a tela ──────────────────────────────────────

def iniciar_x11() -> None:
    """Sobe o servidor do Termux:X11 (display :0) e abre o app."""
    if not garantir_termux_x11():
        raise ToonsError("O Termux:X11 é necessário (pacote termux-x11-nightly e o app Termux:X11).")
    if not servico_ativo("x11") and not servico_ativo("desktop"):
        iniciar_servico("x11", "termux-x11 :0 -ac", com_log=False)
    rodar(["am", "start", "--user", "0", "-n", X11_APP], capturar=True, timeout=20, mostrar=False)


# ── Transmitir a tela por link (navegador, pela rede ou pelo túnel) ──
# O scrcpy precisa de uma conexão ADB direta, que só passaria pelo túnel expondo a depuração do celular à
# internet. Aqui o próprio celular tira a tela (pelo ADB ligado a ele mesmo, ou root) e manda as imagens
# para uma página com link secreto: abre em qualquer navegador, na mesma rede ou pelo túnel da Cloudflare.
# O navegador pede o próximo quadro e o servidor só responde quando a tela muda (o túnel rápido não lida
# bem com streams contínuos, e assim a tela parada não gasta dados nem bateria).

TELA_QUALIDADES = {"rapida": ("Rápida (480 px, gasta menos dados)", 480, 55), "normal": ("Normal (720 px)", 720, 70),
                   "nitida": ("Nítida (1080 px, mais pesada)", 1080, 85)}
# formato do 'screencap' (PixelFormat do Android) → (modo do Pillow, modo bruto, bytes por pixel)
_FORMATOS_TELA = {1: ("RGBA", "RGBA", 4), 2: ("RGBA", "RGBX", 4), 5: ("RGBA", "BGRA", 4), 3: ("RGB", "RGB", 3),
                  4: ("RGB", "BGR;16", 2)}
TECLAS_TELA = {"voltar": 4, "inicio": 3, "recentes": 187, "volume_mais": 24, "volume_menos": 25, "energia": 26}


def _comando_no_celular(comando: str, saida_binaria: bool = False, timeout: float = 15, serial: str | None = None):
    """Roda um comando no Android com permissão de 'shell': por root, ou pelo ADB ligado ao próprio celular."""
    cmd = ["su", "-c", comando] if tem_root() else ["adb", "-s", serial or adb_alvo(), "exec-out", comando]
    proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        raise ToonsError(f"'{comando.split()[0]}' falhou: {proc.stderr.decode(errors='replace').strip()[-200:]}")
    return proc.stdout if saida_binaria else proc.stdout.decode(errors="replace")


def quadro_da_tela(bruto: bytes, largura_max: int, qualidade: int) -> tuple:
    """(JPEG, largura e altura reais da tela) a partir da saída crua do 'screencap' (cabeçalho + pixels)."""
    from PIL import Image
    if len(bruto) < 16:
        raise ToonsError("Captura vazia.")
    largura, altura, formato = struct.unpack_from("<III", bruto)
    modo, bruto_modo, bpp = _FORMATOS_TELA.get(formato, ("RGBA", "RGBA", 4))
    cabecalho = len(bruto) - largura * altura * bpp  # 12 bytes (Android antigo) ou 16 (com o espaço de cor)
    if not largura or not altura or cabecalho not in (12, 16):
        raise ToonsError(f"Formato de captura inesperado ({largura}x{altura}, formato {formato}).")
    img = Image.frombuffer(modo, (largura, altura), bruto[cabecalho:], "raw", bruto_modo, 0, 1).convert("RGB")
    if largura > largura_max:
        img = img.resize((largura_max, max(1, round(altura * largura_max / largura))))
    buffer = io.BytesIO()
    img.save(buffer, "JPEG", quality=qualidade)
    return buffer.getvalue(), (largura, altura)


def tamanho_png(dados: bytes) -> tuple:
    """Largura e altura de um PNG (bloco IHDR)."""
    if dados[:8] != b"\x89PNG\r\n\x1a\n":
        raise ToonsError("A captura não veio em PNG.")
    return struct.unpack(">II", dados[16:24])


class TransmissaoTela:
    """Captura a tela enquanto alguém assiste e guarda o último quadro para as páginas abertas."""

    def __init__(self, largura: int, qualidade: int):
        self.largura, self.qualidade = largura, qualidade
        self.quadro, self.tipo, self.n, self.tamanho = None, "image/jpeg", 0, (0, 0)
        self.erro, self.ultimo_pedido, self.serial = "", 0.0, None
        self.cond = threading.Condition()
        self.com_pillow = modulo_existe("PIL")
        threading.Thread(target=self._laco, daemon=True).start()

    def capturar(self) -> tuple:
        if not tem_root() and not self.serial:
            self.serial = adb_alvo()  # uma vez só (não a cada quadro); volta a procurar se a conexão cair
        if self.com_pillow:
            bruto = _comando_no_celular("screencap", True, serial=self.serial)
            return (*quadro_da_tela(bruto, self.largura, self.qualidade), "image/jpeg")
        png = _comando_no_celular("screencap -p", True, serial=self.serial)  # sem o Pillow: PNG (mais lento)
        return png, tamanho_png(png), "image/png"

    def _laco(self) -> None:
        anterior = None
        while True:
            if time.time() - self.ultimo_pedido > 10:
                time.sleep(0.3)  # ninguém assistindo: não captura (economiza bateria)
                continue
            inicio = time.time()
            try:
                quadro, tamanho, tipo = self.capturar()
                if quadro != anterior:
                    anterior = quadro
                    with self.cond:
                        self.quadro, self.tamanho, self.tipo, self.erro = quadro, tamanho, tipo, ""
                        self.n += 1
                        self.cond.notify_all()
            except Exception as e:  # noqa: BLE001 — a transmissão continua tentando
                self.erro, self.serial = str(e), None
                log(f"Captura falhou: {e}")
                time.sleep(2)
            time.sleep(max(0.0, 0.12 - (time.time() - inicio)))  # no máximo uns 8 quadros por segundo

    def proximo(self, depois: int, espera: float = 10) -> tuple:
        """(número, quadro, tipo) do primeiro quadro mais novo que `depois` (ou o atual, se demorar)."""
        self.ultimo_pedido = time.time()
        with self.cond:
            self.cond.wait_for(lambda: self.n > depois, timeout=espera)
            return self.n, self.quadro, self.tipo


def comando_de_controle(acao: dict, tamanho: tuple) -> str:
    """Comando 'input' do Android para um toque, arrasto, tecla ou texto vindo do navegador.
    As posições chegam de 0 a 1 (proporção da imagem) e viram pixels da tela de verdade."""
    largura, altura = tamanho
    if not largura or not altura:
        raise ToonsError("Ainda não há imagem da tela.")

    def px(valor, total) -> int:
        return max(0, min(total - 1, int(float(valor) * total)))

    tipo = acao.get("tipo")
    if tipo == "toque":
        return f"input tap {px(acao['x'], largura)} {px(acao['y'], altura)}"
    if tipo == "arrastar":
        duracao = max(50, min(3000, int(acao.get("ms", 300))))
        return (f"input swipe {px(acao['x1'], largura)} {px(acao['y1'], altura)} {px(acao['x2'], largura)} "
                f"{px(acao['y2'], altura)} {duracao}")
    if tipo == "tecla" and acao.get("tecla") in TECLAS_TELA:
        return f"input keyevent {TECLAS_TELA[acao['tecla']]}"
    if tipo == "texto":
        texto = "".join(ch for ch in sem_acento(str(acao.get("texto", ""))) if 32 <= ord(ch) < 127)[:200]
        if not texto:
            raise ToonsError("Texto vazio (o Android só aceita letras sem acento por aqui).")
        return "input text " + shlex.quote(texto.replace(" ", "%s"))
    raise ToonsError(f"Ação desconhecida: {tipo}")


PAGINA_TELA = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<meta name="referrer" content="no-referrer"><title>Tela do celular</title>
<style>
html,body{margin:0;height:100%;background:#111;color:#eee;font-family:system-ui,sans-serif;overflow:hidden}
body{display:flex;flex-direction:column}
#palco{flex:1;min-height:0;display:flex;align-items:center;justify-content:center;padding:6px}
#tela{max-width:100%;max-height:100%;touch-action:none;user-select:none;-webkit-user-drag:none;
  box-shadow:0 0 24px #000;border-radius:6px;background:#222;min-width:40px;min-height:40px}
#barra{display:flex;gap:6px;align-items:center;justify-content:center;flex-wrap:wrap;padding:6px 6px 10px}
button{background:#2b2b2b;color:#eee;border:1px solid #444;border-radius:10px;padding:8px 12px;font-size:15px}
#status{position:fixed;top:8px;left:10px;font-size:13px;background:#000a;padding:2px 8px;border-radius:8px}
</style></head><body>
<div id="status">conectando…</div>
<div id="palco"><img id="tela" alt="Tela do celular" draggable="false"></div>
<div id="barra">__BARRA__</div>
<script>
const token = new URLSearchParams(location.search).get("t") || "";
const CONTROLE = __CONTROLE__;
const img = document.getElementById("tela"), st = document.getElementById("status");
const espera = ms => new Promise(f => setTimeout(f, ms));
let n = 0;
async function laco() {
  for (;;) {
    try {
      const r = await fetch(`/quadro?t=${encodeURIComponent(token)}&n=${n}`, {cache: "no-store"});
      if (r.status === 200) {
        n = +r.headers.get("X-Quadro");
        const url = URL.createObjectURL(await r.blob()), antigo = img.src;
        img.src = url;
        if (antigo.startsWith("blob:")) URL.revokeObjectURL(antigo);
        st.textContent = "● ao vivo";
      } else if (r.status === 204) {
        const e = r.headers.get("X-Erro");
        st.textContent = e ? "⚠ " + decodeURIComponent(e) : "● ao vivo (tela parada)";
        if (e) await espera(1500);
      } else {
        st.textContent = r.status === 403 ? "link inválido ou trocado" : "transmissão parada";
        await espera(3000);
      }
    } catch (e) {
      st.textContent = "sem conexão… tentando de novo";
      await espera(2000);
    }
  }
}
function enviar(acao) {
  fetch(`/controle?t=${encodeURIComponent(token)}`, {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify(acao)}).then(r => { if (!r.ok) st.textContent = "⚠ o controle não foi aceito"; });
}
if (CONTROLE) {
  let ini = null;
  const pos = e => { const b = img.getBoundingClientRect();
    return {x: (e.clientX - b.left) / b.width, y: (e.clientY - b.top) / b.height}; };
  img.addEventListener("pointerdown", e => { ini = {...pos(e), t: Date.now()}; img.setPointerCapture(e.pointerId);
    e.preventDefault(); });
  img.addEventListener("pointerup", e => {
    if (!ini) return;
    const fim = pos(e), b = img.getBoundingClientRect(), ms = Date.now() - ini.t;
    const dist = Math.hypot((fim.x - ini.x) * b.width, (fim.y - ini.y) * b.height);
    if (dist < 12 && ms < 600) enviar({tipo: "toque", x: ini.x, y: ini.y});
    else enviar({tipo: "arrastar", x1: ini.x, y1: ini.y, x2: fim.x, y2: fim.y, ms: Math.max(80, ms)});
    ini = null;
  });
  img.addEventListener("contextmenu", e => e.preventDefault());
  document.querySelectorAll("[data-tecla]").forEach(b => b.onclick = () => enviar({tipo: "tecla", tecla: b.dataset.tecla}));
  document.getElementById("texto").onclick = () => { const t = prompt("Texto para digitar no celular (sem acentos):");
    if (t) enviar({tipo: "texto", texto: t}); };
}
laco();
</script></body></html>"""

BARRA_CONTROLE = ('<button data-tecla="voltar">◀ Voltar</button><button data-tecla="inicio">● Início</button>'
                  '<button data-tecla="recentes">▢ Recentes</button><button id="texto">⌨ Texto</button>'
                  '<button data-tecla="volume_menos">🔉</button><button data-tecla="volume_mais">🔊</button>')
PAGINA_SEM_ACESSO = ("<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
                     "<body style='background:#111;color:#eee;font-family:sans-serif;text-align:center;padding:40px'>"
                     "<h2>Link inválido</h2><p>Peça um link novo para quem está transmitindo a tela.</p>")


class _HandlerTela(BaseHTTPRequestHandler):
    server_version = "TermuxToons"
    transmissao: TransmissaoTela | None = None
    token = ""
    controle = False
    executar = staticmethod(lambda comando: _comando_no_celular(comando, serial=_HandlerTela.transmissao.serial))

    def log_message(self, formato, *args):
        pass

    def _consulta(self) -> dict:
        return urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)

    def _autorizado(self) -> bool:
        token = (self._consulta().get("t") or [""])[0]
        return bool(self.token) and hmac.compare_digest(token.encode(), self.token.encode())

    def _responder(self, codigo: int, corpo: bytes = b"", tipo: str = "text/plain; charset=utf-8",
                   extra: dict | None = None) -> None:
        self.send_response(codigo)
        for chave, valor in {"Content-Type": tipo, "Content-Length": str(len(corpo)), "Cache-Control": "no-store",
                             "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
                             **(extra or {})}.items():
            self.send_header(chave, valor)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(corpo)

    def do_GET(self):
        caminho = urllib.parse.urlsplit(self.path).path
        if not self._autorizado():
            self._responder(403, PAGINA_SEM_ACESSO.encode(), "text/html; charset=utf-8")
            return
        if caminho == "/":
            pagina = PAGINA_TELA.replace("__CONTROLE__", "true" if self.controle else "false").replace(
                "__BARRA__", BARRA_CONTROLE if self.controle else "<span style='opacity:.6'>Só visualização</span>")
            self._responder(200, pagina.encode(), "text/html; charset=utf-8")
        elif caminho == "/quadro":
            try:
                depois = int((self._consulta().get("n") or ["0"])[0])
            except ValueError:
                depois = 0
            n, quadro, tipo = self.transmissao.proximo(depois)
            if quadro is None or n <= depois:
                erro_txt = urllib.parse.quote(self.transmissao.erro[:200]) if self.transmissao.erro else ""
                self._responder(204, extra={"X-Erro": erro_txt} if erro_txt else None)
            else:
                self._responder(200, quadro, tipo, {"X-Quadro": str(n)})
        else:
            self._responder(404, b"nada aqui")

    def do_POST(self):
        if urllib.parse.urlsplit(self.path).path != "/controle":
            self._responder(404)
            return
        if not self._autorizado() or not self.controle:
            self._responder(403, b"controle bloqueado")
            return
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
            acao = json.loads(self.rfile.read(min(tamanho, 10_000)) or b"{}")
            self.executar(comando_de_controle(acao, self.transmissao.tamanho))
        except (ToonsError, ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as e:
            self._responder(400, str(e).encode())
            return
        self._responder(204)


def servir_tela(porta: int) -> None:
    """Servidor da transmissão de tela (roda dentro do tmux)."""
    c = cfg()
    if not c.get("tela_token"):
        raise ToonsError("Crie a transmissão pelo menu primeiro (ela gera o link secreto).")
    _, largura, qualidade = TELA_QUALIDADES.get(c.get("tela_qualidade"), TELA_QUALIDADES["normal"])
    _HandlerTela.transmissao = TransmissaoTela(largura, qualidade)
    _HandlerTela.token, _HandlerTela.controle = c["tela_token"], bool(c.get("tela_controle"))
    with ThreadingHTTPServer(("0.0.0.0", porta), _HandlerTela) as servidor:
        log(f"Transmissão da tela em http://{ip_local()}:{porta} · controle "
            f"{'PERMITIDO' if _HandlerTela.controle else 'bloqueado'}")
        servidor.serve_forever()


def links_da_tela() -> list:
    c = cfg()
    links = [("Mesma rede Wi-Fi", f"http://{ip_local()}:{c['tela_porta']}/?t={c['tela_token']}")]
    if servico_ativo("tunel-tela") and url_tunel("tunel-tela"):
        links.append(("Internet (de qualquer lugar)", f"{url_tunel('tunel-tela')}/?t={c['tela_token']}"))
    return links


def mostrar_links_tela(oferecer_acoes: bool = True) -> None:
    if not servico_ativo("tela"):
        info("A transmissão está parada.")
        return
    links = links_da_tela()
    print(f"\n{NEG}📡 Transmissão da tela{RST} {DIM}(controle "
          f"{'permitido' if cfg().get('tela_controle') else 'bloqueado'}){RST}")
    for onde, link in links:
        print(f"  {CIANO}{onde}:{RST}\n  {NEG}{link}{RST}")
    if len(links) == 1:
        print(f"  {DIM}Para alguém fora do seu Wi-Fi, ligue a transmissão escolhendo 'qualquer lugar'.{RST}")
    if not oferecer_acoes:
        return
    link = links[-1][1]
    i = escolher("E agora?", ["Copiar o link", "Mostrar QR code", "Enviar (WhatsApp, Telegram...)",
                              "Abrir aqui para testar", "Nada"])
    if i == 0:
        copiar_texto(link)
    elif i == 1:
        mostrar_qr(link, "tela")
    elif i == 2 and tem("termux-share"):
        _tapi(["termux-share", "-a", "send"], 30, entrada=f"📱 Veja a tela do meu celular:\n{link}", json_saida=False)
    elif i == 3:
        abrir_link(links[0][1])


def iniciar_transmissao_tela() -> None:
    c = cfg()
    if not tem_root():
        try:
            adb_alvo()
        except ToonsError as e:
            erro(str(e))
            info("Sem root, a tela é capturada pelo ADB ligado ao próprio celular: conecte em "
                 "📲 Celular e sistema → 🔌 Depuração sem fio e volte aqui.")
            return
    if not modulo_existe("PIL"):
        garantir_modulo("PIL", pip_nome="pillow", pkg_nome="python-pillow",
                        aviso_extra="Com ele a transmissão fica bem mais rápida (sem ele, funciona com imagens PNG).")
    chaves = list(TELA_QUALIDADES)
    i = escolher("Qualidade da imagem", [TELA_QUALIDADES[k][0] for k in chaves],
                 chaves.index(c.get("tela_qualidade", "normal")) + 1)
    if i is None:
        return
    c["tela_qualidade"] = chaves[i]
    j = escolher("Quem vai assistir?", ["Alguém na mesma rede Wi-Fi", "Qualquer lugar (internet, pelo túnel)"])
    if j is None:
        return
    aviso("Quem tiver o link vê TUDO o que aparece na tela: notificações, mensagens, senhas digitadas...")
    c["tela_controle"] = confirmar("Permitir que quem assiste TOQUE e digite no seu celular?", False)
    if not c.get("tela_token"):
        c["tela_token"] = secrets.token_urlsafe(18)
    salvar_cfg()
    if servico_ativo("tela"):
        parar_servico("tela")  # reinicia para valer a qualidade e o controle escolhidos
        time.sleep(1)
    if not porta_livre(c["tela_porta"]):
        raise ToonsError(f"A porta {c['tela_porta']} está em uso por outro programa.")
    if not iniciar_servico("tela", cmd_self("tela", "--porta", str(c["tela_porta"])), reiniciar=True):
        return
    if j == 1:
        abrir_tunel("tunel-tela", c["tela_porta"])
    elif servico_ativo("tunel-tela"):
        parar_servico("tunel-tela")
    mostrar_links_tela()
    info("Telas de apps protegidos (bancos, por exemplo) aparecem pretas: o Android não deixa capturar.")


def parar_transmissao_tela() -> None:
    parar_servico("tunel-tela")
    parar_servico("tela")


def novo_link_tela() -> None:
    c = cfg()
    c["tela_token"] = secrets.token_urlsafe(18)
    salvar_cfg()
    ok("Link novo criado: o antigo parou de funcionar.")
    if servico_ativo("tela"):
        parar_servico("tela")
        time.sleep(1)
        iniciar_servico("tela", cmd_self("tela", "--porta", str(c["tela_porta"])), reiniciar=True)
        mostrar_links_tela()


def alternar_controle_tela() -> None:
    c = cfg()
    if not c.get("tela_controle"):
        aviso("Com o controle ligado, quem tiver o link toca, arrasta e digita no seu celular.")
        if not confirmar("Permitir o controle pelo navegador?", False):
            return
    c["tela_controle"] = not c.get("tela_controle")
    salvar_cfg()
    ok(f"Controle pelo navegador {'PERMITIDO' if c['tela_controle'] else 'bloqueado'}.")
    if servico_ativo("tela"):
        parar_servico("tela")
        time.sleep(1)
        iniciar_servico("tela", cmd_self("tela", "--porta", str(c["tela_porta"])), reiniciar=True)


@submenu
def menu_espelhar():
    c = cfg()

    def outro_celular():
        if not garantir_adb() or not garantir_cmd("scrcpy", "scrcpy", repo="x11-repo"):
            return
        info("No OUTRO celular: Opções do desenvolvedor → Depuração por Wi-Fi (os dois na mesma rede).")
        if confirmar("É a primeira vez com esse celular (precisa parear)?", True):
            ip, porta = pedir_endereco_adb("Endereço de 'Parear com código' (ip:porta)")
            codigo = perguntar("Código de pareamento (6 dígitos)")
            print((adb("pair", f"{ip}:{porta}", codigo, timeout=60).stdout or "").strip())
        ip, porta = pedir_endereco_adb("Endereço da tela 'Depuração por Wi-Fi' (ip:porta)")
        resultado = (adb("connect", f"{ip}:{porta}", timeout=30).stdout or "").strip()
        print(resultado)
        if "connected" not in resultado:
            raise ToonsError("Não conectou. Confira o endereço e se os dois estão na mesma rede.")
        iniciar_x11()
        info("Abrindo a tela do outro celular no Termux:X11. Para fechar, volte aqui e aperte Ctrl+C.")
        rodar("DISPLAY=:0 " + shlex.join(["scrcpy", "-s", f"{ip}:{porta}", "--max-size", "1280",
                                          "--video-bit-rate", "4M"]), mostrar=False)

    def num_pc():
        print("Para ver e controlar ESTE celular num computador (Windows, Mac ou Linux):\n"
              "  1. No PC, instale o scrcpy: https://github.com/Genymobile/scrcpy\n"
              "  2. Celular e PC na mesma rede Wi-Fi.\n")
        if confirmar("Liberar o ADB deste celular na porta 5555 agora (precisa do ADB sem fio conectado)?", True):
            print(adb("tcpip", "5555", serial=adb_alvo(), timeout=30).stdout or "")
            ip = ip_local()
            print(f"\n  No PC, rode:  {NEG}scrcpy --tcpip={ip}:5555{RST}\n")
            aviso("A porta 5555 fica aberta na rede até reiniciar o celular. Use só em redes de confiança.")

    menu("📲 Espelhar e transmitir a tela", [
        ("🌍 Transmitir a tela por link (navegador; Wi-Fi ou internet)", iniciar_transmissao_tela),
        (lambda: f"Transmissão: mostrar o link ({'no ar' if servico_ativo('tela') else 'parada'})", mostrar_links_tela),
        (lambda: f"Transmissão: controle pelo navegador ({'permitido' if c.get('tela_controle') else 'bloqueado'})",
         alternar_controle_tela),
        ("Transmissão: gerar link novo (o antigo para de funcionar)", novo_link_tela),
        ("Transmissão: parar (e fechar o túnel)", parar_transmissao_tela),
        ("Ver e controlar OUTRO celular aqui (scrcpy + Termux:X11)", outro_celular),
        ("Ver e controlar ESTE celular num PC (scrcpy, mesma rede)", num_pc),
    ])


@submenu
def menu_celular():
    menu("📲 Celular e sistema", [
        ("🔌 Depuração sem fio (ADB pelo Wi-Fi, sem root)", menu_adb),
        ("📱 Termux:API (sensores, SMS, câmera, localização...)", menu_termux_api),
        ("📊 Painel do sistema ao vivo (CPU, RAM, bateria, serviços)", dashboard),
        ("🔋 Saúde da bateria (histórico e alertas de 80%)", menu_bateria),
        ("📊 Uso de dados e tempo de tela (ADB)", menu_uso_celular),
        ("📦 Gerenciador de apps (ADB, sem root)", menu_apps),
        ("🖥️ Resolução da tela (inteira ou de um app)", menu_resolucao),
        ("📸 Organizador de fotos", menu_fotos),
        ("🔁 Conversor de arquivos (imagem, vídeo, áudio, PDF)", menu_conversor_arquivos),
        ("🤖 Automação por eventos (Wi-Fi, carregador, horário)", menu_automacao),
        ("📲 Espelhar e transmitir a tela (scrcpy ou link pela internet)", menu_espelhar),
    ])


# ════════════════════════════════════════════════════════════════════
#  22. Internet e comunicação
# ════════════════════════════════════════════════════════════════════

FAVORITOS_FILE = DATA_DIR / "noticias_favoritas.json"
LINKS_FILE = DATA_DIR / "links.json"


# ── E-mail (IMAP/SMTP) ───────────────────────────────────────────────

EMAIL_PROVEDORES = {
    "gmail.com": ("imap.gmail.com", "smtp.gmail.com", 465),
    "googlemail.com": ("imap.gmail.com", "smtp.gmail.com", 465),
    "outlook.com": ("outlook.office365.com", "smtp.office365.com", 587),
    "hotmail.com": ("outlook.office365.com", "smtp.office365.com", 587),
    "live.com": ("outlook.office365.com", "smtp.office365.com", 587),
    "yahoo.com": ("imap.mail.yahoo.com", "smtp.mail.yahoo.com", 465),
    "yahoo.com.br": ("imap.mail.yahoo.com", "smtp.mail.yahoo.com", 465),
    "icloud.com": ("imap.mail.me.com", "smtp.mail.me.com", 587),
    "zoho.com": ("imap.zoho.com", "smtp.zoho.com", 465),
}


def decodificar_cabecalho(valor) -> str:
    import email.errors
    import email.header
    if not valor:
        return ""
    try:
        return str(email.header.make_header(email.header.decode_header(str(valor))))
    except (UnicodeDecodeError, LookupError, email.errors.HeaderParseError):
        return str(valor)


def html_para_texto(pagina: str) -> str:
    """HTML → texto mantendo os parágrafos."""
    import html as html_mod
    pagina = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", pagina)
    pagina = re.sub(r"(?i)<br\s*/?>", "\n", pagina)
    pagina = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|blockquote)>", "\n\n", pagina)
    pagina = re.sub(r"(?s)<[^>]+>", " ", pagina)
    texto = html_mod.unescape(pagina)
    texto = re.sub(r"[ \t\r\f\v\xa0]+", " ", texto)
    return re.sub(r"\n\s*\n\s*(\n\s*)+", "\n\n", "\n".join(l.strip() for l in texto.splitlines())).strip()


def _email_cfg() -> dict:
    e = cfg().get("email") or {}
    if not e.get("endereco") or not e.get("senha"):
        raise ToonsError("Configure a conta de e-mail primeiro.")
    return e


def conectar_imap():
    import imaplib
    e = _email_cfg()
    try:
        conexao = imaplib.IMAP4_SSL(e["imap"], 993, timeout=30)
        conexao.login(e["endereco"], e["senha"])
    except imaplib.IMAP4.error as falha:
        raise ToonsError(f"O servidor recusou o login ({falha}). No Gmail use uma 'senha de app' "
                         "(myaccount.google.com/apppasswords).") from None
    except OSError as falha:
        raise ToonsError(f"Sem conexão com {e['imap']} ({falha}).") from None
    return conexao


def listar_emails(criterio: str = "ALL", n: int = 25, caixa: str = "INBOX") -> list:
    """[{uid, de, assunto, data, lido}] dos e-mails mais novos."""
    import email
    conexao = conectar_imap()
    try:
        conexao.select(caixa, readonly=True)
        status, dados = conexao.uid("SEARCH", None, criterio)
        if status != "OK":
            raise ToonsError(f"Busca recusada pelo servidor: {dados}")
        uids = dados[0].split()[-n:]
        if not uids:
            return []
        status, dados = conexao.uid("FETCH", b",".join(uids),
                                    "(UID FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        mensagens = []
        for parte in dados:
            if not isinstance(parte, tuple):
                continue
            meta = parte[0].decode(errors="replace")
            uid = re.search(r"UID (\d+)", meta)
            cab = email.message_from_bytes(parte[1])
            mensagens.append({"uid": uid.group(1) if uid else "", "de": decodificar_cabecalho(cab["From"]),
                              "assunto": decodificar_cabecalho(cab["Subject"]) or "(sem assunto)",
                              "data": cab["Date"] or "", "lido": "\\Seen" in meta})
        return sorted(mensagens, key=lambda m: int(m["uid"] or 0), reverse=True)
    finally:
        with contextlib.suppress(Exception):
            conexao.logout()


def baixar_email(uid: str, marcar_lido: bool = True, caixa: str = "INBOX"):
    import email
    import email.policy
    conexao = conectar_imap()
    try:
        conexao.select(caixa, readonly=not marcar_lido)
        status, dados = conexao.uid("FETCH", uid, "(BODY.PEEK[])")
        bruto = next((p[1] for p in dados if isinstance(p, tuple)), None)
        if status != "OK" or bruto is None:
            raise ToonsError("Não consegui baixar esse e-mail.")
        if marcar_lido:
            conexao.uid("STORE", uid, "+FLAGS", "(\\Seen)")
        return email.message_from_bytes(bruto, policy=email.policy.default)
    finally:
        with contextlib.suppress(Exception):
            conexao.logout()


def corpo_do_email(msg) -> str:
    parte = msg.get_body(preferencelist=("plain", "html"))
    if parte is None:
        return "(sem texto)"
    try:
        conteudo = parte.get_content()
    except (LookupError, UnicodeDecodeError):
        conteudo = parte.get_payload(decode=True).decode("utf-8", errors="replace")
    return html_para_texto(conteudo) if parte.get_content_type() == "text/html" else conteudo.strip()


def apagar_email(uid: str, caixa: str = "INBOX") -> None:
    """Move para a lixeira (ou marca como apagado, se o servidor não tiver lixeira)."""
    conexao = conectar_imap()
    try:
        _, pastas = conexao.list()
        lixeira = next((re.search(r'"([^"]+)"$|(\S+)$', p.decode(errors="replace")).group(0).strip('"')
                        for p in pastas or [] if b"\\Trash" in p), None)
        conexao.select(caixa)
        if lixeira and conexao.uid("MOVE", uid, f'"{lixeira}"')[0] == "OK":
            return
        conexao.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
        conexao.expunge()
    finally:
        with contextlib.suppress(Exception):
            conexao.logout()


def enviar_email(para: str, assunto: str, corpo: str, anexos=(), responder_a=None) -> None:
    import mimetypes
    import smtplib
    from email.message import EmailMessage
    e = _email_cfg()
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = e["endereco"], para, assunto
    if responder_a is not None and responder_a["Message-ID"]:
        msg["In-Reply-To"] = msg["References"] = responder_a["Message-ID"]
    msg.set_content(corpo)
    for anexo in anexos:
        tipo = (mimetypes.guess_type(str(anexo))[0] or "application/octet-stream").split("/")
        msg.add_attachment(Path(anexo).read_bytes(), maintype=tipo[0], subtype=tipo[1], filename=Path(anexo).name)
    porta = int(e.get("porta_smtp", 465))
    try:
        servidor = smtplib.SMTP_SSL(e["smtp"], porta, timeout=60) if porta == 465 else \
            smtplib.SMTP(e["smtp"], porta, timeout=60)
        with servidor:
            if porta != 465:
                servidor.starttls()
            servidor.login(e["endereco"], e["senha"])
            servidor.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        raise ToonsError("Login recusado para enviar. No Gmail use uma 'senha de app'.") from None
    except (smtplib.SMTPException, OSError) as falha:
        raise ToonsError(f"Falha ao enviar: {falha}") from None


@submenu
def menu_email():
    c = cfg()

    def configurar():
        endereco = perguntar("Seu e-mail", (c.get("email") or {}).get("endereco"))
        if "@" not in endereco:
            raise ToonsError("E-mail inválido.")
        dominio = endereco.split("@", 1)[1].lower()
        imap, smtp, porta = EMAIL_PROVEDORES.get(dominio, ("", "", 465))
        if not imap:
            info("Não conheço esse provedor: digite os servidores (estão na ajuda do seu e-mail).")
            imap = perguntar("Servidor IMAP", f"imap.{dominio}")
            smtp = perguntar("Servidor SMTP", f"smtp.{dominio}")
            porta = perguntar_int("Porta SMTP (465 = SSL, 587 = STARTTLS)", 465, 1, 65535)
        if dominio.startswith(("gmail", "googlemail")):
            info("No Gmail: ative a verificação em duas etapas e crie uma 'senha de app' em "
                 "myaccount.google.com/apppasswords. Use ela aqui, não a sua senha normal.")
        elif dominio in ("outlook.com", "hotmail.com", "live.com"):
            aviso("A Microsoft bloqueou senha comum em apps de e-mail em muitas contas pessoais; pode não funcionar.")
        senha = getpass.getpass("Senha (de app): ")
        c["email"] = {"endereco": endereco, "senha": senha, "imap": imap, "smtp": smtp, "porta_smtp": porta}
        salvar_cfg()
        info("Testando o login...")
        conectar_imap().logout()
        ok("Conta configurada (a senha fica só neste celular, em ~/.termux_toons/config.json).")

    def caixa(criterio: str = "ALL", rotulo_caixa: str = "Caixa de entrada"):
        info("Buscando e-mails...")
        lista = listar_emails(criterio)
        if not lista:
            info("Nenhum e-mail.")
            return
        while True:
            rotulos = [f"{'' if m['lido'] else NEG + '● '}{m['assunto'][:60]}{RST}  {DIM}{m['de'][:30]}{RST}"
                       for m in lista]
            i = escolher(f"{rotulo_caixa} ({len(lista)} mais recentes)", rotulos)
            if i is None:
                return
            ler(lista[i])
            lista[i]["lido"] = True

    def ler(item: dict):
        msg = baixar_email(item["uid"])
        while True:
            limpar()
            titulo(item["assunto"][:60])
            print(f"{DIM}De: {decodificar_cabecalho(msg['From'])}\nData: {msg['Date']}{RST}\n")
            texto = corpo_do_email(msg)
            print(texto[:6000] + (f"\n{DIM}[... continua]{RST}" if len(texto) > 6000 else ""))
            anexos = list(msg.iter_attachments())
            if anexos:
                print(f"\n📎 {', '.join(decodificar_cabecalho(a.get_filename()) or 'anexo' for a in anexos)}")
            print()
            acoes = ["Responder", "Salvar os anexos", "Ouvir", "Apagar (lixeira)", "Voltar"]
            j = escolher("O que fazer?", acoes)
            if j in (None, 4):
                return
            if j == 0:
                corpo = editar_texto("\n\n" + "\n".join("> " + l for l in texto.splitlines()[:40]), ".txt")
                if corpo and confirmar("Enviar a resposta?", True):
                    assunto = item["assunto"] if item["assunto"].lower().startswith("re:") else "Re: " + item["assunto"]
                    enviar_email(msg["Reply-To"] or msg["From"], assunto, corpo, responder_a=msg)
                    ok("Resposta enviada.")
            elif j == 1:
                pasta = pasta_saida("Anexos")
                for a in anexos:
                    nome = Path(decodificar_cabecalho(a.get_filename()) or "anexo").name
                    (pasta / nome).write_bytes(a.get_payload(decode=True) or b"")
                ok(f"{len(anexos)} anexo(s) salvos em {pasta}" if anexos else "Este e-mail não tem anexos.")
            elif j == 2:
                with contextlib.suppress(ToonsError):
                    falar(f"{item['assunto']}. {texto[:3000]}")
            elif j == 3 and confirmar("Apagar este e-mail?", False):
                apagar_email(item["uid"])
                ok("Apagado.")
                pausar()
                return
            pausar()

    def escrever():
        para = perguntar("Para (e-mail)")
        if "@" not in para:
            raise ToonsError("E-mail inválido.")
        assunto = perguntar("Assunto")
        corpo = editar_texto("", ".txt")
        if not corpo:
            return
        anexos = []
        while confirmar("Anexar um arquivo?" if not anexos else "Anexar mais um?", False):
            arq = escolher_arquivo("Qual arquivo?")
            if arq:
                anexos.append(arq)
        if confirmar(f"Enviar para {para}?", True):
            enviar_email(para, assunto, corpo, anexos)
            ok("E-mail enviado.")

    def buscar():
        termo = sem_acento(perguntar("Procurar por (palavra do assunto, remetente ou texto)")).replace('"', "")
        if termo:
            caixa(f'(TEXT "{termo}")', f"Busca: {termo}")

    conta = lambda: (c.get("email") or {}).get("endereco") or "não configurada"  # noqa: E731
    menu("📧 E-mail", [
        ("Caixa de entrada", caixa),
        ("Só os não lidos", lambda: caixa("UNSEEN", "Não lidos")),
        ("Escrever e-mail", escrever),
        ("Buscar e-mails", buscar),
        (lambda: f"Configurar a conta ({conta()})", configurar),
    ])


# ── Leitor de notícias (RSS) ─────────────────────────────────────────

FEEDS_PADRAO = [
    {"nome": "g1", "url": "https://g1.globo.com/rss/g1/"},
    {"nome": "BBC News Brasil", "url": "https://feeds.bbci.co.uk/portuguese/rss.xml"},
    {"nome": "Agência Brasil", "url": "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml"},
    {"nome": "Folha (em cima da hora)", "url": "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml"},
    {"nome": "Tecnoblog", "url": "https://tecnoblog.net/feed/"},
    {"nome": "Olhar Digital", "url": "https://olhardigital.com.br/feed/"},
]


def _data_do_feed(texto: str | None):
    import email.utils
    if not texto:
        return None
    texto = texto.strip()
    with contextlib.suppress(TypeError, ValueError, IndexError):
        return email.utils.parsedate_to_datetime(texto)
    with contextlib.suppress(ValueError):
        return datetime.fromisoformat(texto.replace("Z", "+00:00"))
    return None


def ler_feed_completo(dados: bytes) -> list:
    """Itens de RSS/Atom com título, link, resumo, data e o áudio (podcasts)."""
    try:
        raiz = ET.fromstring(dados)
    except ET.ParseError as e:
        raise ToonsError(f"Feed inválido: {e}") from None

    def nome(el):
        return el.tag.split("}")[-1]

    def filho(el, *nomes):
        for f in el:
            if nome(f) in nomes:
                return f
        return None

    itens = []
    for el in raiz.iter():
        if nome(el) not in ("item", "entry"):
            continue
        t = filho(el, "title")
        link_el = filho(el, "link")
        link = ""
        if link_el is not None:
            link = (link_el.text or "").strip() or link_el.get("href", "")
        resumo_el = filho(el, "description", "summary", "content", "encoded")
        audio_el = next((f for f in el if nome(f) == "enclosure" and
                         (f.get("type", "").startswith("audio") or f.get("url", "").split("?")[0].endswith(
                             (".mp3", ".m4a", ".ogg", ".opus")))), None)
        data_el = filho(el, "pubDate", "published", "updated", "date")
        itens.append({"titulo": " ".join((t.text or "").split()) if t is not None else "(sem título)", "link": link,
                      "resumo": html_para_texto(resumo_el.text or "") if resumo_el is not None else "",
                      "data": _data_do_feed(data_el.text if data_el is not None else None),
                      "audio": audio_el.get("url") if audio_el is not None else None})
    return itens


def baixar_feed(url: str) -> list:
    return ler_feed_completo(pedir_bytes(url, timeout=25))


def texto_da_materia(url: str) -> str:
    """Os parágrafos de uma página de notícia (modo leitura)."""
    import html as html_mod
    codigo, pagina = baixar_pagina(url)
    if codigo >= 400:
        raise ToonsError(f"A página respondeu HTTP {codigo}.")
    paragrafos = []
    for bruto in re.findall(r"(?is)<p\b[^>]*>(.*?)</p>", re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", pagina)):
        texto = " ".join(html_mod.unescape(re.sub(r"(?s)<[^>]+>", " ", bruto)).split())
        if len(texto) >= 40:
            paragrafos.append(texto)
    return "\n\n".join(paragrafos) or texto_limpo(pagina)[:5000]


def _quando_txt(d) -> str:
    if not d:
        return ""
    try:
        d = d.astimezone() if d.tzinfo else d
        return d.strftime("%d/%m %H:%M")
    except (ValueError, OverflowError):
        return ""


@submenu
def menu_noticias():
    c = cfg()
    if not c.get("feeds"):
        c["feeds"] = copy.deepcopy(FEEDS_PADRAO)

    def abrir_item(item: dict, fonte: str):
        while True:
            limpar()
            titulo(fonte)
            print(f"{NEG}{item['titulo']}{RST}\n{DIM}{_quando_txt(item['data'])}{RST}\n")
            print((item["resumo"] or "(sem resumo)")[:1500] + "\n")
            i = escolher("O que fazer?", ["Ler a matéria inteira (modo leitura)", "Abrir no navegador",
                                         "Ouvir a matéria", "Guardar nos favoritos", "Copiar o link", "Voltar"])
            if i in (None, 5):
                return
            if i == 0:
                ler_texto(item["titulo"], texto_da_materia(item["link"]))
            elif i == 1:
                abrir_link(item["link"])
            elif i == 2:
                info("Lendo em voz alta (Ctrl+C interrompe)...")
                with contextlib.suppress(ToonsError, KeyboardInterrupt):
                    texto = texto_da_materia(item["link"])
                    for pedaco in fatiar(f"{item['titulo']}.\n{texto}", 3000):
                        falar(pedaco)
            elif i == 3:
                favs = ler_json(FAVORITOS_FILE, [])
                favs.insert(0, {"titulo": item["titulo"], "link": item["link"], "fonte": fonte,
                                "quando": datetime.now().strftime("%Y-%m-%d")})
                gravar_json(FAVORITOS_FILE, favs[:300])
                ok("Guardada nos favoritos.")
                pausar()
            elif i == 4:
                copiar_texto(item["link"])
                pausar()

    def ver_fonte(feed: dict | None):
        fontes = [feed] if feed else c["feeds"]
        itens = []
        for f in fontes:
            try:
                itens += [(f["nome"], it) for it in baixar_feed(f["url"])[:30]]
            except ToonsError as e:
                aviso(f"{f['nome']}: {e}")
        if not itens:
            info("Nenhuma notícia carregada.")
            return
        itens.sort(key=lambda par: par[1]["data"].timestamp() if par[1]["data"] else 0, reverse=True)
        while True:
            rotulos = [f"{it['titulo'][:80]}  {DIM}{'' if feed else nome + ' · '}{_quando_txt(it['data'])}{RST}"
                       for nome, it in itens[:80]]
            i = escolher(feed["nome"] if feed else "Todas as fontes", rotulos)
            if i is None:
                return
            abrir_item(itens[i][1], itens[i][0])

    def escolher_fonte():
        i = escolher("Qual fonte?", ["📰 Todas as fontes (mais recentes primeiro)"] + [f["nome"] for f in c["feeds"]])
        if i is not None:
            ver_fonte(None if i == 0 else c["feeds"][i - 1])

    def favoritos():
        favs = ler_json(FAVORITOS_FILE, [])
        if not favs:
            info("Nenhum favorito ainda.")
            return
        i = escolher("Favoritos", [f"{f['titulo'][:80]}  {DIM}{f['fonte']} · {f['quando']}{RST}" for f in favs])
        if i is None:
            return
        j = escolher("O que fazer?", ["Ler (modo leitura)", "Abrir no navegador", "Remover dos favoritos"])
        if j == 0:
            ler_texto(favs[i]["titulo"], texto_da_materia(favs[i]["link"]))
        elif j == 1:
            abrir_link(favs[i]["link"])
        elif j == 2:
            favs.pop(i)
            gravar_json(FAVORITOS_FILE, favs)
            ok("Removido.")

    def adicionar_fonte():
        url = perguntar("Endereço do feed RSS/Atom (ex.: https://site.com/feed/)")
        if not url.startswith(("http://", "https://")):
            raise ToonsError("O endereço precisa começar com http:// ou https://")
        itens = baixar_feed(url)
        ok(f"Feed válido: {len(itens)} notícias.")
        c["feeds"].append({"nome": perguntar("Nome da fonte", urllib.parse.urlsplit(url).netloc), "url": url})
        salvar_cfg()

    def remover_fonte():
        i = escolher("Remover qual?", [f["nome"] for f in c["feeds"]])
        if i is not None and confirmar(f"Remover '{c['feeds'][i]['nome']}'?", True):
            c["feeds"].pop(i)
            salvar_cfg()

    menu("📰 Notícias (RSS)", [
        ("Ler notícias", escolher_fonte),
        ("Favoritos", favoritos),
        ("Adicionar uma fonte (feed RSS)", adicionar_fonte),
        ("Remover uma fonte", remover_fonte),
    ])


# ── Gerenciador de downloads (aria2) ─────────────────────────────────

def aria2(metodo: str, *params):
    """Chama o aria2 rodando em segundo plano (JSON-RPC em 127.0.0.1:6800)."""
    corpo = {"jsonrpc": "2.0", "id": "toons", "method": f"aria2.{metodo}",
             "params": [f"token:{cfg().get('aria2_segredo', '')}", *params]}
    try:
        resposta = pedir_json("http://127.0.0.1:6800/jsonrpc", corpo, timeout=15)
    except ToonsError as e:
        if "HTTP" not in str(e):
            raise ToonsError("O gerenciador de downloads não está rodando (inicie o serviço).") from None
        raise
    if resposta.get("error"):
        raise ToonsError(f"aria2: {resposta['error'].get('message')}")
    return resposta.get("result")


def iniciar_aria2() -> bool:
    if not garantir_cmd("aria2c", "aria2"):
        return False
    c = cfg()
    if not c.get("aria2_segredo"):
        c["aria2_segredo"] = secrets.token_hex(16)
        salvar_cfg()
    sessao_arq = DATA_DIR / "aria2.sessao"
    sessao_arq.touch()
    pasta = c.get("aria2_pasta") or str(pasta_saida("Downloads"))
    cmd = shlex.join([
        "aria2c", "--enable-rpc", "--rpc-listen-port=6800", f"--rpc-secret={c['aria2_segredo']}", f"--dir={pasta}",
        "--continue=true", f"--input-file={sessao_arq}", f"--save-session={sessao_arq}", "--save-session-interval=20",
        f"--max-concurrent-downloads={c.get('aria2_simultaneos', 3)}", "--split=8", "--max-connection-per-server=8",
        "--min-split-size=1M", "--seed-time=0", "--follow-torrent=true", "--auto-file-renaming=true",
        "--file-allocation=none", "--console-log-level=warn", "--summary-interval=0"])
    return iniciar_servico("downloads", cmd, reiniciar=True)


def _garantir_aria2() -> None:
    if not servico_ativo("downloads"):
        info("Iniciando o gerenciador de downloads em segundo plano...")
        if not iniciar_aria2():
            raise ToonsError("O aria2 não iniciou.")
        time.sleep(1.5)


def nome_download(d: dict) -> str:
    info_bt = (d.get("bittorrent") or {}).get("info") or {}
    if info_bt.get("name"):
        return info_bt["name"]
    arquivos = d.get("files") or [{}]
    if arquivos[0].get("path"):
        return Path(arquivos[0]["path"]).name
    uris = arquivos[0].get("uris") or [{}]
    return (uris[0].get("uri") or d.get("gid", "?")).rsplit("/", 1)[-1][:60] or "(buscando nome...)"


def todos_downloads() -> list:
    campos = ["gid", "status", "totalLength", "completedLength", "downloadSpeed", "files", "bittorrent",
              "errorMessage", "numSeeders", "connections"]
    return (aria2("tellActive", campos) or []) + (aria2("tellWaiting", 0, 100, campos) or []) + \
        (aria2("tellStopped", 0, 100, campos) or [])


def linha_download(d: dict, largura_barra: int = 14) -> str:
    total, feito = int(d.get("totalLength") or 0), int(d.get("completedLength") or 0)
    frac = feito / total if total else 0
    estado = {"active": f"{VERD}⬇{RST}", "waiting": f"{DIM}⏳{RST}", "paused": f"{AMAR}⏸{RST}",
              "complete": f"{VERD}✔{RST}", "error": f"{VERM}✖{RST}", "removed": f"{DIM}✖{RST}"}.get(d["status"], "?")
    velocidade = int(d.get("downloadSpeed") or 0)
    extra = f" {bytes_humanos(velocidade)}/s" if d["status"] == "active" else ""
    if d["status"] == "active" and velocidade and total:
        extra += f" · falta {fmt_relogio((total - feito) / velocidade)}"
    return (f"{estado} {barra_horizontal(frac, largura_barra)} {frac:4.0%} {nome_download(d)[:40]}"
            f" {DIM}{bytes_humanos(total) if total else ''}{extra}{RST}")


@submenu
def menu_downloads():
    c = cfg()

    def adicionar():
        alvo = perguntar("Link (http, https, ftp ou magnet:)")
        if not alvo:
            return
        if not re.match(r"(https?|ftp)://|magnet:\?", alvo):
            raise ToonsError("Isso não parece um link de download.")
        _garantir_aria2()
        opcoes = {}
        nome = perguntar("Salvar com outro nome? (Enter = nome original)", "")
        if nome:
            opcoes["out"] = Path(nome).name
        aria2("addUri", [alvo], opcoes)
        ok("Download adicionado à fila.")

    def adicionar_torrent():
        arq = escolher_arquivo("Qual arquivo .torrent?", (".torrent",))
        if not arq:
            return
        _garantir_aria2()
        aria2("addTorrent", base64.b64encode(arq.read_bytes()).decode())
        ok("Torrent adicionado. (Ele para de compartilhar quando termina de baixar.)")

    def ver():
        lista = todos_downloads()
        if not lista:
            info("Nenhum download.")
            return
        i = escolher("Downloads", [linha_download(d) for d in lista])
        if i is None:
            return
        d = lista[i]
        if d.get("errorMessage"):
            erro(d["errorMessage"])
        acoes = {"active": ["Pausar", "Cancelar"], "waiting": ["Pausar", "Cancelar"], "paused": ["Continuar", "Cancelar"]}
        opcoes = acoes.get(d["status"], ["Tirar da lista"]) + ["Voltar"]
        j = escolher(nome_download(d), opcoes)
        if j is None or opcoes[j] == "Voltar":
            return
        escolha = opcoes[j]
        if escolha == "Pausar":
            aria2("pause", d["gid"])
        elif escolha == "Continuar":
            aria2("unpause", d["gid"])
        elif escolha == "Cancelar" and confirmar("Cancelar este download?", False):
            aria2("remove", d["gid"])
        elif escolha == "Tirar da lista":
            aria2("removeDownloadResult", d["gid"])
        ok("Feito.")

    def ao_vivo():
        with TelaCheia():
            while True:
                try:
                    lista = todos_downloads()
                    status = aria2("getGlobalStat")
                except ToonsError as e:
                    desenhar([str(e), "", "Aperte uma tecla"])
                    ler_tecla()
                    return
                linhas = ["", f"  {NEG}⬇ Downloads{RST}  {bytes_humanos(int(status['downloadSpeed']))}/s · "
                              f"{status['numActive']} ativo(s) · {status['numWaiting']} na fila", ""]
                linhas += ["  " + linha_download(d) for d in lista[:20]] or [f"  {DIM}Nenhum download.{RST}"]
                linhas += ["", f"  {DIM}Atualiza a cada segundo · qualquer tecla sai{RST}"]
                desenhar(linhas)
                if tecla_ou_nada(1.0) is not None:
                    return

    def configurar():
        c["aria2_pasta"] = os.path.expanduser(perguntar("Pasta dos downloads",
                                                        c.get("aria2_pasta") or str(pasta_saida("Downloads"))))
        c["aria2_simultaneos"] = perguntar_int("Quantos downloads ao mesmo tempo", c.get("aria2_simultaneos", 3), 1, 10)
        salvar_cfg()
        if servico_ativo("downloads") and confirmar("Reiniciar o gerenciador para aplicar?", True):
            parar_servico("downloads")
            iniciar_aria2()

    menu("⬇️ Gerenciador de downloads (aria2)", [
        ("Adicionar link ou magnet", adicionar),
        ("Adicionar arquivo .torrent", adicionar_torrent),
        ("Ver downloads (pausar, continuar, cancelar)", ver),
        ("Acompanhar ao vivo", ao_vivo),
        ("Pausar todos", lambda: aria2("pauseAll") and ok("Pausados.")),
        ("Continuar todos", lambda: aria2("unpauseAll") and ok("Continuando.")),
        ("Limpar os concluídos da lista", lambda: aria2("purgeDownloadResult") and ok("Lista limpa.")),
        ("Configurar pasta e downloads simultâneos", configurar),
        *itens_servico("downloads", "Gerenciador", iniciar_aria2),
    ])


# ── Chat na rede local ───────────────────────────────────────────────

CHAT_PORTA, CHAT_DESCOBERTA = 8099, 8098
CHAT_MAX_ARQUIVO = 20 * 1024 * 1024


def _mostrar_chat(msg: dict) -> None:
    tipo = msg.get("t")
    if tipo == "msg":
        linha = f"{CIANO}{msg.get('de', '?')}{RST}: {msg.get('texto', '')}"
    elif tipo in ("entrou", "saiu"):
        linha = f"{DIM}→ {msg.get('de', '?')} {'entrou' if tipo == 'entrou' else 'saiu'}{RST}"
    elif tipo == "arquivo":
        nome = Path(msg.get("nome") or "arquivo").name
        destino = pasta_saida("Chat") / nome
        try:
            destino.write_bytes(base64.b64decode(msg.get("dados", "")))
            linha = f"📎 {CIANO}{msg.get('de', '?')}{RST} enviou {NEG}{nome}{RST} → {DIM}{destino}{RST}"
        except (ValueError, OSError) as e:
            linha = f"{VERM}Arquivo de {msg.get('de')} chegou com erro: {e}{RST}"
    elif tipo == "quem":
        linha = f"{DIM}Na sala: {', '.join(msg.get('nomes', []))}{RST}"
    elif tipo == "erro":
        linha = f"{VERM}{msg.get('texto')}{RST}"
    else:
        return
    sys.stdout.write(f"\r\033[K{linha}\n{AMAR}>{RST} ")
    sys.stdout.flush()


def _ler_linhas_socket(sock, ao_receber) -> None:
    """Lê mensagens JSON (uma por linha) até a conexão fechar."""
    arquivo = sock.makefile("rb")
    try:
        for bruto in arquivo:
            with contextlib.suppress(ValueError):
                ao_receber(json.loads(bruto.decode("utf-8", errors="replace")))
    except OSError:
        pass


def _fechar_socket(sock) -> None:
    """Fecha de verdade: o close() sozinho não fecha enquanto outra thread lê pelo makefile()."""
    with contextlib.suppress(OSError):
        sock.shutdown(socket.SHUT_RDWR)
    with contextlib.suppress(OSError):
        sock.close()


class SalaChat:
    """Servidor da sala: repassa as mensagens para todos e se anuncia na rede (UDP)."""

    def __init__(self, nome_sala: str, senha: str, meu_nome: str):
        self.nome_sala, self.senha, self.meu_nome = nome_sala, senha, meu_nome
        self.clientes, self.trava, self.ativa = {}, threading.Lock(), True

    def iniciar(self) -> None:
        self.servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.servidor.bind(("0.0.0.0", CHAT_PORTA))
        except OSError:
            raise ToonsError(f"A porta {CHAT_PORTA} está ocupada (já tem uma sala aberta?).") from None
        self.servidor.listen()
        threading.Thread(target=self._aceitar, daemon=True).start()
        threading.Thread(target=self._anunciar, daemon=True).start()

    def _anunciar(self) -> None:
        aviso_udp = json.dumps({"app": "toons-chat", "sala": self.nome_sala, "porta": CHAT_PORTA,
                                "senha": bool(self.senha)}).encode()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        ip = ip_local()
        destinos = ["255.255.255.255"] + ([ip.rsplit(".", 1)[0] + ".255"] if ip.count(".") == 3 else [])
        while self.ativa:
            for destino in destinos:
                with contextlib.suppress(OSError):
                    sock.sendto(aviso_udp, (destino, CHAT_DESCOBERTA))
            time.sleep(2)

    def _aceitar(self) -> None:
        while self.ativa:
            try:
                cli, _ = self.servidor.accept()
            except OSError:
                return
            threading.Thread(target=self._atender, args=(cli,), daemon=True).start()

    def _atender(self, cli) -> None:
        nome = None

        def receber(msg: dict):
            nonlocal nome
            if nome is None:
                if msg.get("t") != "oi" or (self.senha and msg.get("senha") != self.senha):
                    self._enviar(cli, {"t": "erro", "texto": "Senha errada ou programa diferente."})
                    cli.close()
                    return
                nome = str(msg.get("de") or "anônimo")[:30]
                with self.trava:
                    self.clientes[cli] = nome
                self._enviar(cli, {"t": "bem-vindo", "sala": self.nome_sala})
                self.espalhar({"t": "entrou", "de": nome}, exceto=cli)
            elif msg.get("t") == "quem":
                self._enviar(cli, {"t": "quem", "nomes": self.nomes()})
            elif msg.get("t") in ("msg", "arquivo"):
                self.espalhar({**msg, "de": nome}, exceto=cli)

        _ler_linhas_socket(cli, receber)
        with self.trava:
            self.clientes.pop(cli, None)
        if nome:
            self.espalhar({"t": "saiu", "de": nome})

    def _enviar(self, cli, msg: dict) -> None:
        with contextlib.suppress(OSError):
            cli.sendall(json.dumps(msg).encode() + b"\n")

    def nomes(self) -> list:
        with self.trava:
            return [self.meu_nome] + list(self.clientes.values())

    def espalhar(self, msg: dict, exceto=None) -> None:
        with self.trava:
            clientes = [c for c in self.clientes if c is not exceto]
        for c in clientes:
            self._enviar(c, msg)
        if msg.get("de") != self.meu_nome:  # o que eu mesmo mandei já está na minha tela
            _mostrar_chat(msg)

    def mandar(self, msg: dict) -> None:
        self.espalhar({**msg, "de": self.meu_nome})

    def fechar(self) -> None:
        self.ativa = False
        with contextlib.suppress(OSError):
            self.servidor.close()
        with self.trava:
            for c in list(self.clientes):
                _fechar_socket(c)


def procurar_salas(segundos: float = 4) -> list:
    """Salas anunciadas na rede: [(nome, ip, porta, tem_senha)]."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("", CHAT_DESCOBERTA))
    except OSError:
        return []
    sock.settimeout(0.5)
    achadas, fim = {}, time.time() + segundos
    while time.time() < fim:
        try:
            dados, (ip, _) = sock.recvfrom(4096)
            aviso_udp = json.loads(dados)
        except (OSError, ValueError):
            continue
        if aviso_udp.get("app") == "toons-chat":
            achadas[(ip, aviso_udp.get("porta", CHAT_PORTA))] = (aviso_udp.get("sala", "?"), bool(aviso_udp.get("senha")))
    sock.close()
    return [(nome, ip, porta, senha) for (ip, porta), (nome, senha) in achadas.items()]


def _conversar(mandar, pedir_quem) -> None:
    print(f"{DIM}Digite e Enter para mandar · /arquivo envia um arquivo · /quem lista quem está · /sair{RST}")
    while True:
        try:
            texto = input(f"{AMAR}>{RST} ").strip()
        except EOFError:
            return
        if not texto:
            continue
        if texto in ("/sair", "/s"):
            return
        if texto == "/quem":
            pedir_quem()
        elif texto.startswith("/arquivo"):
            caminho = texto[8:].strip()
            arq = Path(os.path.expanduser(caminho)) if caminho else escolher_arquivo("Qual arquivo?")
            if not arq or not arq.is_file():
                erro("Arquivo não encontrado.")
                continue
            if arq.stat().st_size > CHAT_MAX_ARQUIVO:
                erro(f"Arquivo grande demais (máximo {bytes_humanos(CHAT_MAX_ARQUIVO)}).")
                continue
            mandar({"t": "arquivo", "nome": arq.name, "dados": base64.b64encode(arq.read_bytes()).decode()})
            ok(f"Enviado: {arq.name}")
        else:
            mandar({"t": "msg", "texto": texto})


@submenu
def menu_chat():
    c = cfg()

    def meu_nome() -> str:
        if not c.get("chat_nome"):
            c["chat_nome"] = perguntar("Seu nome no chat", getpass.getuser())[:30]
            salvar_cfg()
        return c["chat_nome"]

    def criar_sala():
        nome = meu_nome()
        sala = SalaChat(perguntar("Nome da sala", f"Sala de {nome}"), perguntar("Senha da sala (opcional)", ""), nome)
        sala.iniciar()
        ok(f"Sala aberta em {ip_local()}:{CHAT_PORTA}. Os outros entram em 'Entrar numa sala' (mesmo Wi-Fi).")
        try:
            _conversar(sala.mandar, lambda: _mostrar_chat({"t": "quem", "nomes": sala.nomes()}))
        finally:
            sala.fechar()

    def entrar():
        nome = meu_nome()
        info("Procurando salas na rede (4 s)...")
        salas = procurar_salas()
        opcoes = [f"{s[0]}  {DIM}{s[1]}{' 🔒' if s[3] else ''}{RST}" for s in salas] + ["Digitar o IP da sala..."]
        i = escolher("Qual sala?", opcoes)
        if i is None:
            return
        if i < len(salas):
            ip, porta = salas[i][1], salas[i][2]
        else:
            ip, porta = perguntar("IP de quem abriu a sala"), CHAT_PORTA
        senha = getpass.getpass("Senha da sala (Enter se não tiver): ")
        sock = socket.create_connection((ip, porta), timeout=10)
        sock.settimeout(None)
        sock.sendall(json.dumps({"t": "oi", "de": nome, "senha": senha}).encode() + b"\n")
        threading.Thread(target=_ler_linhas_socket, args=(sock, _mostrar_chat), daemon=True).start()
        ok(f"Conectado a {ip}.")
        try:
            _conversar(lambda msg: sock.sendall(json.dumps(msg).encode() + b"\n"),
                       lambda: sock.sendall(b'{"t": "quem"}\n'))
        except OSError:
            erro("A conexão caiu (a sala foi fechada?).")
        finally:
            _fechar_socket(sock)

    menu("💬 Chat na rede local (sem internet)", [
        ("Criar uma sala", criar_sala),
        ("Entrar numa sala", entrar),
        (lambda: f"Meu nome no chat: {c.get('chat_nome') or '(definir)'}",
         lambda: (c.pop("chat_nome", None), meu_nome())),
    ], cabecalho=lambda: print(f"{DIM}Funciona entre celulares com o Termux-Toons no mesmo Wi-Fi (ou roteador do "
                               f"celular), sem internet.{RST}"))


# ── Navegador em modo texto e Browsh ─────────────────────────────────

def _url_digitada(texto: str) -> str:
    texto = texto.strip()
    if not texto:
        raise ToonsError("Digite um endereço.")
    if re.match(r"[a-z]+://", texto):
        return texto
    if "." in texto and " " not in texto:
        return "https://" + texto
    return url_com("https://lite.duckduckgo.com/lite/", q=texto)


def garantir_browsh() -> bool:
    if tem("browsh"):
        return True
    info("O Browsh mostra os sites modernos (com imagens, vídeos e JavaScript) dentro do terminal.\n"
         "  Ele usa o Firefox por trás: a instalação baixa uns 250 MB (pacotes 'browsh' e 'firefox' do x11-repo).")
    if not confirmar("Instalar o Browsh agora?", True):
        return False
    instalar_de_repo("x11-repo", "browsh")
    return tem("browsh")


def abrir_browsh(url: str | None = None) -> None:
    if not garantir_browsh():
        return
    print(f"{NEG}Atalhos do Browsh:{RST} Ctrl+L digita endereço · Backspace volta · Ctrl+T nova aba · "
          f"Ctrl+W fecha aba · Ctrl+Q sai")
    info("A primeira abertura demora (o Firefox inicia por trás).")
    time.sleep(2)
    rodar(["browsh", "--startup-url", url or "https://lite.duckduckgo.com/lite/"], mostrar=False)


@submenu
def menu_navegador():
    def w3m(url: str) -> None:
        if garantir_cmd("w3m"):
            print(f"{DIM}w3m: setas navegam · Enter abre link · B volta · U digita endereço · q sai{RST}")
            time.sleep(1)
            rodar(["w3m", url], mostrar=False)

    def salvar_texto():
        url = _url_digitada(perguntar("Endereço da página"))
        destino = pasta_saida("Páginas") / f"{_slug(urllib.parse.urlsplit(url).netloc + urllib.parse.urlsplit(url).path)}.txt"
        if tem("w3m") or garantir_cmd("w3m"):
            texto = saida(["w3m", "-dump", "-cols", "100", url], timeout=60)
        else:
            texto = texto_da_materia(url)
        destino.write_text(texto, "utf-8")
        ok(f"Página salva como texto: {destino}")

    menu("🌐 Navegador no terminal", [
        ("🦊 Browsh: sites modernos no terminal (com Firefox)", lambda: abrir_browsh(
            _url_digitada(perguntar("Endereço ou busca (Enter = página de busca)", "lite.duckduckgo.com/lite/")))),
        ("w3m: abrir um site (leve, só texto)", lambda: w3m(_url_digitada(perguntar("Endereço ou busca")))),
        ("Pesquisar na web (DuckDuckGo)", lambda: w3m(url_com("https://lite.duckduckgo.com/lite/",
                                                               q=perguntar("Pesquisar por")))),
        ("Modo leitura (só o texto da matéria)", lambda: ler_texto(
            "Modo leitura", texto_da_materia(_url_digitada(perguntar("Endereço da página"))))),
        ("Salvar uma página como texto", salvar_texto),
        ("Abrir no navegador do Android", lambda: abrir_link(_url_digitada(perguntar("Endereço")))),
    ])


# ── Encurtador de links e pastebin ───────────────────────────────────

def _guardar_link(tipo: str, url: str, original: str) -> None:
    historico = ler_json(LINKS_FILE, [])
    historico.insert(0, {"tipo": tipo, "url": url, "original": original[:200],
                         "quando": datetime.now().strftime("%Y-%m-%d %H:%M")})
    gravar_json(LINKS_FILE, historico[:500])


def encurtar_link(url: str) -> str:
    for base in ("https://is.gd/create.php", "https://v.gd/create.php"):
        with contextlib.suppress(ToonsError):
            curto = pedir_bytes(url_com(base, format="simple", url=url), timeout=20).decode().strip()
            if curto.startswith("http"):
                return curto
    curto = pedir_bytes(url_com("https://tinyurl.com/api-create.php", url=url), timeout=20).decode().strip()
    if not curto.startswith("http"):
        raise ToonsError(f"Não consegui encurtar: {curto[:100]}")
    return curto


def colar_texto_online(texto: str) -> str:
    """Publica um texto e devolve o link (paste.rs; dpaste.com se falhar)."""
    with contextlib.suppress(ToonsError):
        link = pedir_bytes("https://paste.rs/", texto.encode(), {"Content-Type": "text/plain; charset=utf-8"},
                           timeout=30, metodo="POST").decode().strip()
        if link.startswith("http"):
            return link
    corpo = urllib.parse.urlencode({"content": texto, "expiry_days": 30}).encode()
    link = pedir_bytes("https://dpaste.com/api/v2/", corpo, {"Content-Type": "application/x-www-form-urlencoded"},
                       timeout=30, metodo="POST").decode().strip()
    if not link.startswith("http"):
        raise ToonsError("Não consegui publicar o texto agora.")
    return link


def enviar_arquivo_online(caminho: Path, tempo: str | None = "24h") -> str:
    """Publica um arquivo: temporário no Litterbox (1h a 72h) ou permanente no Catbox."""
    limite = (1024 if tempo else 200) * 1024 * 1024
    if caminho.stat().st_size > limite:
        raise ToonsError(f"Arquivo grande demais (máximo {bytes_humanos(limite)}).")
    campos = {"reqtype": "fileupload", **({"time": tempo} if tempo else {})}
    corpo, tipo = _multipart(campos, {"fileToUpload": caminho})
    url = "https://litterbox.catbox.moe/resources/internals/api.php" if tempo else "https://catbox.moe/user/api.php"
    link = pedir_bytes(url, corpo, {"Content-Type": tipo}, timeout=600, metodo="POST").decode().strip()
    if not link.startswith("http"):
        raise ToonsError(f"O envio falhou: {link[:200]}")
    return link


@submenu
def menu_links():
    def depois(tipo: str, link: str, original: str):
        _guardar_link(tipo, link, original)
        print(f"\n  {NEG}{VERD}{link}{RST}\n")
        i = escolher("E agora?", ["Copiar o link", "Mostrar QR code do link", "Compartilhar (WhatsApp...)", "Nada"])
        if i == 0:
            copiar_texto(link)
        elif i == 1:
            mostrar_qr(link, "link")
        elif i == 2 and tem("termux-share"):
            rodar(["termux-share", "-a", "send"], entrada=link, capturar=True, timeout=30)

    def encurtar():
        url = _url_digitada(perguntar("Link para encurtar"))
        depois("curto", encurtar_link(url), url)

    def colar():
        i = escolher("De onde vem o texto?", ["Digitar agora", "O que está copiado", "Um arquivo de texto"])
        if i is None:
            return
        if i == 0:
            texto = editar_texto("", ".txt") or ""
        elif i == 1:
            texto = _tapi(["termux-clipboard-get"], 10, json_saida=False)
        else:
            arq = escolher_arquivo("Qual arquivo?", (".txt", ".md", ".py", ".sh", ".json", ".log", ".csv"))
            texto = arq.read_text("utf-8", errors="replace") if arq else ""
        if not texto.strip():
            raise ToonsError("Texto vazio.")
        aviso("O texto fica público para quem tiver o link.")
        if confirmar("Publicar?", True):
            depois("texto", colar_texto_online(texto), texto[:80])

    def arquivo():
        arq = escolher_arquivo("Qual arquivo?")
        if not arq:
            return
        tempos = [("1 hora", "1h"), ("12 horas", "12h"), ("24 horas", "24h"), ("3 dias", "72h"),
                  ("Para sempre (Catbox, até 200 MB)", None)]
        i = escolher("O link vale por", [t for t, _ in tempos], 3)
        if i is None:
            return
        aviso("Qualquer pessoa com o link baixa o arquivo.")
        if confirmar(f"Enviar {arq.name} ({bytes_humanos(arq.stat().st_size)})?", True):
            info("Enviando...")
            depois("arquivo", enviar_arquivo_online(arq, tempos[i][1]), arq.name)

    def historico():
        lista = ler_json(LINKS_FILE, [])
        if not lista:
            info("Nenhum link ainda.")
            return
        i = escolher("Histórico", [f"{l['url']}  {DIM}{l['tipo']} · {l['quando']} · {l['original'][:30]}{RST}"
                                   for l in lista])
        if i is not None:
            copiar_texto(lista[i]["url"])

    menu("🔗 Encurtador de links e pastebin", [
        ("Encurtar um link", encurtar),
        ("Publicar um texto (pastebin)", colar),
        ("Enviar um arquivo e gerar link", arquivo),
        ("Histórico de links (copiar)", historico),
    ])


@submenu
def menu_internet():
    menu("🌐 Internet e comunicação", [
        ("📧 E-mail (ler, responder, enviar)", menu_email),
        ("📰 Notícias (RSS, modo leitura, ouvir)", menu_noticias),
        ("⬇️ Gerenciador de downloads (links, magnet, torrent)", menu_downloads),
        ("💬 Chat na rede local (sem internet)", menu_chat),
        ("🦊 Navegador no terminal (Browsh e w3m)", menu_navegador),
        ("🔗 Encurtador de links e pastebin", menu_links),
    ])


# ════════════════════════════════════════════════════════════════════
#  23. Inteligência artificial: assistente na nuvem, voz e OCR
# ════════════════════════════════════════════════════════════════════

CONVERSAS_DIR = DATA_DIR / "conversas_ia"
WHISPER_DIR = HOME / "whisper.cpp"

IA_PROVEDORES = {"claude": "Claude (Anthropic)", "openai": "ChatGPT (OpenAI)", "gemini": "Gemini (Google)"}
IA_ESFORCOS = ["low", "medium", "high", "xhigh", "max"]
# Modelos do Claude que aceitam o 'fallbacks: "default"' (troca de modelo no servidor se o pedido for recusado).
CLAUDE_COM_FALLBACK = {"claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-1", "claude-opus-5"}
IA_SISTEMA_PADRAO = ("Você é um assistente útil que roda no celular da pessoa, dentro do Termux. Responda em "
                     "português do Brasil, de forma clara e direta. O terminal não mostra Markdown: prefira texto "
                     "simples, listas com hífen e blocos de código curtos.")


def ia_config() -> dict:
    c = cfg()
    ia = c.setdefault("ia_nuvem", {})
    ia.setdefault("provedor", "claude")
    ia.setdefault("chaves", {})
    ia.setdefault("modelos", {"claude": "claude-opus-5-5"})
    ia.setdefault("esforco", "medium")
    ia.setdefault("sistema", IA_SISTEMA_PADRAO)
    return ia


def garantir_anthropic() -> bool:
    """Instala o SDK oficial da Anthropic (no Termux, com as rodas pré-compiladas do TUR quando houver)."""
    if modulo_existe("anthropic"):
        return True
    aviso("O SDK oficial da Anthropic (pacote Python 'anthropic') não está instalado.")
    if not confirmar("Instalar agora?", True):
        return False
    extra = ["--extra-index-url", "https://termux-user-repository.github.io/pypi/"] if IS_TERMUX else []
    if rodar([sys.executable, "-m", "pip", "install", "-U", *extra, "anthropic"]).returncode != 0 and IS_TERMUX:
        info("Algumas partes precisam ser compiladas (Rust). Isso pode levar uns 15 minutos na primeira vez.")
        instalar_pkg("rust", "binutils")
        rodar([sys.executable, "-m", "pip", "install", "-U", "anthropic"])
    importlib.invalidate_caches()
    if not modulo_existe("anthropic"):
        erro("Não consegui instalar o SDK da Anthropic.")
        return False
    return True


def _chave(provedor: str) -> str:
    ia = ia_config()
    chave = ia["chaves"].get(provedor) or os.environ.get(
        {"claude": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY"}[provedor], "")
    if not chave:
        onde = {"claude": "console.anthropic.com → API Keys", "openai": "platform.openai.com/api-keys",
                "gemini": "aistudio.google.com/apikey"}[provedor]
        info(f"Você precisa de uma chave de API do {IA_PROVEDORES[provedor]} ({onde}).")
        chave = getpass.getpass("Cole a chave (fica só neste celular): ").strip()
        if not chave:
            raise ToonsError("Sem chave não dá para usar esse provedor.")
        ia["chaves"][provedor] = chave
        salvar_cfg()
    return chave


def _imagem_base64(caminho: Path) -> tuple:
    """(tipo MIME, base64) de uma imagem, reduzida para no máximo 1568 px quando o Pillow existe."""
    tipo = {".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}.get(caminho.suffix.lower(), "image/jpeg")
    dados = caminho.read_bytes()
    if modulo_existe("PIL"):
        with contextlib.suppress(Exception):
            from PIL import Image, ImageOps
            with Image.open(caminho) as img:
                img = ImageOps.exif_transpose(img).convert("RGB")
                img.thumbnail((1568, 1568))
                buffer = io.BytesIO()
                img.save(buffer, "JPEG", quality=85)
                dados, tipo = buffer.getvalue(), "image/jpeg"
    if len(dados) > 4_500_000:
        raise ToonsError("Imagem grande demais (instale o Pillow para ela ser reduzida automaticamente).")
    return tipo, base64.b64encode(dados).decode()


def _mensagens_claude(historico: list) -> list:
    mensagens = []
    for m in historico:
        if m["role"] == "assistant" and m.get("claude") is not None:
            # devolve o conteúdo exatamente como veio (inclui os blocos de raciocínio, que a API exige de volta)
            mensagens.append({"role": "assistant", "content": m["claude"]})
            continue
        conteudo = [{"type": "text", "text": m["texto"]}]
        if m.get("imagem"):
            tipo, b64 = m["imagem"]
            conteudo.insert(0, {"type": "image", "source": {"type": "base64", "media_type": tipo, "data": b64}})
        mensagens.append({"role": m["role"], "content": conteudo})
    return mensagens


def _responder_claude(historico: list, mostrar) -> dict:
    import anthropic
    ia = ia_config()
    modelo = ia["modelos"].get("claude") or "claude-opus-5-5"
    cliente = anthropic.Anthropic(api_key=_chave("claude"))
    pedido = {"model": modelo, "max_tokens": 64000, "system": ia["sistema"], "messages": _mensagens_claude(historico)}
    if ia.get("esforco"):
        pedido["output_config"] = {"effort": ia["esforco"]}
    if modelo in CLAUDE_COM_FALLBACK:
        pedido.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
    try:
        with cliente.beta.messages.stream(**pedido) as stream:
            for evento in stream:
                if evento.type == "content_block_delta" and evento.delta.type == "text_delta":
                    mostrar(evento.delta.text)
            final = stream.get_final_message()
    except anthropic.AuthenticationError:
        ia["chaves"].pop("claude", None)
        salvar_cfg()
        raise ToonsError("Chave da API recusada: confira e cole de novo.") from None
    except anthropic.PermissionDeniedError as e:
        raise ToonsError(f"Sua chave não tem acesso a isso: {e.message}") from None
    except anthropic.NotFoundError:
        raise ToonsError(f"Modelo '{modelo}' não encontrado. Escolha outro em Configurar.") from None
    except anthropic.RateLimitError:
        raise ToonsError("Limite de uso atingido. Espere um pouco e tente de novo.") from None
    except anthropic.BadRequestError as e:
        raise ToonsError(f"Pedido recusado pela API: {e.message}") from None
    except anthropic.APIStatusError as e:
        raise ToonsError(f"Erro da API ({e.status_code}): {e.message}") from None
    except anthropic.APIConnectionError:
        raise ToonsError("Sem conexão com a API da Anthropic. Está com internet?") from None
    texto = "".join(b.text for b in final.content if b.type == "text")
    if final.stop_reason == "refusal":
        texto += "\n[O modelo recusou este pedido.]"
        mostrar("\n[O modelo recusou este pedido.]")
    elif final.stop_reason == "max_tokens":
        mostrar("\n[Resposta cortada: chegou ao limite de tamanho.]")
    servido_por = final.model if final.model != modelo else ""
    return {"role": "assistant", "texto": texto, "claude": final.content, "modelo": servido_por}


def _ler_sse(resposta):
    """Linhas 'data: ...' de um stream SSE."""
    for bruto in resposta:
        linha = bruto.decode("utf-8", errors="replace").strip()
        if linha.startswith("data:"):
            yield linha[5:].strip()


def _erro_http(e: urllib.error.HTTPError) -> ToonsError:
    try:
        dados = json.loads(e.read().decode())
        detalhe = (dados.get("error") or {}).get("message") or str(dados)[:200]
    except (ValueError, AttributeError):
        detalhe = ""
    return ToonsError(f"A API respondeu HTTP {e.code}: {detalhe}")


def _responder_openai(historico: list, mostrar) -> dict:
    ia = ia_config()
    modelo = ia["modelos"].get("openai")
    if not modelo:
        raise ToonsError("Escolha um modelo do ChatGPT em Configurar → Modelo.")
    mensagens = [{"role": "system", "content": ia["sistema"]}]
    for m in historico:
        conteudo = m["texto"]
        if m.get("imagem"):
            tipo, b64 = m["imagem"]
            conteudo = [{"type": "text", "text": m["texto"]},
                        {"type": "image_url", "image_url": {"url": f"data:{tipo};base64,{b64}"}}]
        mensagens.append({"role": m["role"], "content": conteudo})
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions",
                                 data=json.dumps({"model": modelo, "messages": mensagens, "stream": True}).encode(),
                                 headers={"Authorization": f"Bearer {_chave('openai')}",
                                          "Content-Type": "application/json"})
    partes = []
    try:
        with urllib.request.urlopen(req, timeout=600) as resposta:
            for dado in _ler_sse(resposta):
                if dado == "[DONE]":
                    break
                with contextlib.suppress(ValueError, KeyError, IndexError):
                    pedaco = json.loads(dado)["choices"][0]["delta"].get("content")
                    if pedaco:
                        partes.append(pedaco)
                        mostrar(pedaco)
    except urllib.error.HTTPError as e:
        raise _erro_http(e) from None
    except OSError as e:
        raise ToonsError(f"Sem conexão com a OpenAI ({e}).") from None
    return {"role": "assistant", "texto": "".join(partes)}


def _responder_gemini(historico: list, mostrar) -> dict:
    ia = ia_config()
    modelo = ia["modelos"].get("gemini")
    if not modelo:
        raise ToonsError("Escolha um modelo do Gemini em Configurar → Modelo.")
    conteudos = []
    for m in historico:
        partes_msg = [{"text": m["texto"]}]
        if m.get("imagem"):
            partes_msg.append({"inline_data": {"mime_type": m["imagem"][0], "data": m["imagem"][1]}})
        conteudos.append({"role": "model" if m["role"] == "assistant" else "user", "parts": partes_msg})
    corpo = {"system_instruction": {"parts": [{"text": ia["sistema"]}]}, "contents": conteudos}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:streamGenerateContent?alt=sse",
        data=json.dumps(corpo).encode(),
        headers={"x-goog-api-key": _chave("gemini"), "Content-Type": "application/json"})
    partes = []
    try:
        with urllib.request.urlopen(req, timeout=600) as resposta:
            for dado in _ler_sse(resposta):
                with contextlib.suppress(ValueError, KeyError, IndexError):
                    for p in json.loads(dado)["candidates"][0]["content"]["parts"]:
                        if p.get("text"):
                            partes.append(p["text"])
                            mostrar(p["text"])
    except urllib.error.HTTPError as e:
        raise _erro_http(e) from None
    except OSError as e:
        raise ToonsError(f"Sem conexão com o Google ({e}).") from None
    return {"role": "assistant", "texto": "".join(partes)}


def ia_responder(historico: list, mostrar=None) -> dict:
    """Manda a conversa para o provedor escolhido e devolve a resposta (mostrando o texto enquanto chega)."""
    provedor = ia_config()["provedor"]
    if provedor == "claude" and not garantir_anthropic():
        raise ToonsError("O SDK da Anthropic é necessário para usar o Claude.")
    estado = {"primeiro": True}

    def exibir(pedaco: str):
        if estado["primeiro"]:
            sys.stdout.write("\r\033[K")
            estado["primeiro"] = False
        sys.stdout.write(pedaco)
        sys.stdout.flush()

    sys.stdout.write(f"{DIM}pensando…{RST}")
    sys.stdout.flush()
    funcao = {"claude": _responder_claude, "openai": _responder_openai, "gemini": _responder_gemini}[provedor]
    try:
        resposta = funcao(historico, mostrar or exibir)
    finally:
        if estado["primeiro"]:
            sys.stdout.write("\r\033[K")
        print()
    return resposta


def ia_listar_modelos(provedor: str) -> list:
    if provedor == "claude":
        if not garantir_anthropic():
            return []
        import anthropic
        try:
            return [m.id for m in anthropic.Anthropic(api_key=_chave("claude")).models.list()]
        except anthropic.APIError as e:
            raise ToonsError(f"Não consegui listar os modelos: {e}") from None
    if provedor == "openai":
        dados = pedir_json("https://api.openai.com/v1/models", cabecalhos={"Authorization": f"Bearer {_chave('openai')}"})
        return sorted((m["id"] for m in dados.get("data", []) if re.match(r"(gpt|o\d|chatgpt)", m["id"])), reverse=True)
    dados = pedir_json("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
                       cabecalhos={"x-goog-api-key": _chave("gemini")})
    return sorted((m["name"].removeprefix("models/") for m in dados.get("models", [])
                   if "generateContent" in m.get("supportedGenerationMethods", [])), reverse=True)


def conversa_ia(primeira: str | None = None, imagem: Path | None = None) -> None:
    """Chat no terminal com o assistente escolhido."""
    ia = ia_config()
    historico = []
    provedor = ia["provedor"]
    print(f"{NEG}{IA_PROVEDORES[provedor]}{RST} {DIM}· {ia['modelos'].get(provedor) or '(escolha o modelo)'}{RST}")
    print(f"{DIM}/novo recomeça · /foto manda uma imagem · /copiar copia a última resposta · /salvar vira nota · "
          f"Enter vazio sai{RST}\n")
    anexo = _imagem_base64(imagem) if imagem else None
    while True:
        if primeira:
            texto, primeira = primeira, None
            print(f"{AMAR}você>{RST} {texto[:300]}{'…' if len(texto) > 300 else ''}")
        else:
            try:
                texto = input(f"{AMAR}você>{RST} ").strip()
            except EOFError:
                texto = ""
        if not texto:
            break
        if texto == "/novo":
            historico, anexo = [], None
            ok("Conversa nova.")
            continue
        if texto == "/foto":
            arq = escolher_arquivo("Qual imagem?", EXT_IMAGEM)
            if arq:
                anexo = _imagem_base64(arq)
                ok(f"{arq.name} vai junto com a próxima mensagem.")
            continue
        if texto == "/copiar":
            if historico:
                copiar_texto(historico[-1]["texto"])
            continue
        if texto == "/salvar":
            _salvar_conversa(historico, como_nota=True)
            continue
        historico.append({"role": "user", "texto": texto, "imagem": anexo})
        anexo = None
        print(f"{CIANO}ia>{RST} ", end="")
        try:
            resposta = ia_responder(historico)
        except ToonsError as e:
            erro(str(e))
            historico.pop()
            continue
        except KeyboardInterrupt:
            print()
            aviso("Resposta interrompida.")
            historico.pop()
            continue
        if resposta.get("modelo"):
            info(f"(respondido por {resposta['modelo']})")
        historico.append(resposta)
    if historico:
        _salvar_conversa(historico)


def _salvar_conversa(historico: list, como_nota: bool = False) -> None:
    texto = "\n\n".join(f"{'Você' if m['role'] == 'user' else 'IA'}: {m['texto']}" for m in historico)
    if como_nota:
        ok(f"Salva como nota: {salvar_nota('Conversa com IA ' + datetime.now().strftime('%d/%m %H:%M'), texto, ['ia']).name}")
        return
    CONVERSAS_DIR.mkdir(parents=True, exist_ok=True)
    (CONVERSAS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.txt").write_text(texto, "utf-8")


def texto_de_arquivo(caminho: Path) -> str:
    """Texto de .txt/.md/.pdf/.epub/.html (para resumir, ler em voz alta etc.)."""
    sufixo = caminho.suffix.lower()
    if sufixo == ".pdf":
        if not garantir_cmd("pdftotext", "poppler"):
            raise ToonsError("O pdftotext (pacote poppler) é necessário para ler PDF.")
        proc = rodar(["pdftotext", "-layout", str(caminho), "-"], capturar=True, timeout=300, mostrar=False)
        return proc.stdout or ""
    if sufixo == ".epub":
        return "\n\n".join(ler_epub(caminho)[1])
    texto = caminho.read_text("utf-8", errors="replace")
    return html_para_texto(texto) if sufixo in (".html", ".htm") else texto


# ── Voz: transcrever (whisper.cpp) e falar ───────────────────────────

WHISPER_MODELOS = {"tiny": "o mais rápido, menos preciso (75 MB)", "base": "equilíbrio (142 MB)",
                   "small": "mais preciso e mais lento (466 MB)"}
EXT_VOZ = EXT_AUDIO + (".mp4", ".webm", ".3gp")


def whisper_bin() -> Path | None:
    for nome in ("whisper-cli", "main"):
        caminho = WHISPER_DIR / "build" / "bin" / nome
        if caminho.exists():
            return caminho
    achado = shutil.which("whisper-cli")
    return Path(achado) if achado else None


def compilar_whisper() -> None:
    for cmd, pacote in (("git", "git"), ("cmake", "cmake"), ("clang", "clang"), ("make", "make")):
        if not garantir_cmd(cmd, pacote):
            raise ToonsError(f"'{cmd}' é necessário para compilar.")
    if (WHISPER_DIR / ".git").exists():
        rodar(["git", "-C", WHISPER_DIR, "pull", "--ff-only"])
    else:
        rodar(["git", "clone", "--depth", "1", "https://github.com/ggml-org/whisper.cpp", WHISPER_DIR], check=True)
    build = WHISPER_DIR / "build"
    rodar(["cmake", "-S", WHISPER_DIR, "-B", build, "-DCMAKE_BUILD_TYPE=Release"], check=True)
    nucleos = os.cpu_count() or 4
    jobs = perguntar_int("Compilar com quantos processos paralelos?", min(4, nucleos), 1, nucleos)
    info("Compilando o whisper.cpp (uns 5 a 15 minutos)...")
    rodar(["cmake", "--build", build, "--config", "Release", "-j", str(jobs), "--target", "whisper-cli"], check=True)
    ok(f"Pronto: {whisper_bin()}")


def modelo_whisper() -> Path:
    return WHISPER_DIR / "models" / f"ggml-{cfg().get('whisper_modelo', 'base')}.bin"


def transcrever_audio(arquivo: Path, idioma: str = "pt") -> str:
    binario = whisper_bin()
    if not binario:
        raise ToonsError("O whisper.cpp ainda não foi compilado (use 'Instalar o whisper' neste menu).")
    modelo = modelo_whisper()
    if not modelo.exists():
        raise ToonsError(f"Baixe o modelo '{modelo.stem}' primeiro (opção 'Baixar modelo de voz').")
    if not garantir_cmd("ffmpeg"):
        raise ToonsError("O ffmpeg é necessário para preparar o áudio.")
    tmp = DATA_DIR / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    wav, base_saida = tmp / "voz16k.wav", tmp / "transcricao"
    rodar(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(arquivo), "-ar", "16000", "-ac", "1",
           "-c:a", "pcm_s16le", str(wav)], check=True, capturar=True)
    info("Transcrevendo (no celular isso leva mais ou menos o tempo do áudio)...")
    rodar([str(binario), "-m", str(modelo), "-l", idioma, "-f", str(wav), "-otxt", "-of", str(base_saida),
           "-t", str(min(4, os.cpu_count() or 4)), "-np"], capturar=True, timeout=3600)
    resultado = base_saida.with_suffix(".txt")
    if not resultado.exists():
        raise ToonsError("O whisper não gerou a transcrição.")
    texto = " ".join(resultado.read_text("utf-8", errors="replace").split())
    resultado.unlink(missing_ok=True)
    return texto


def _pastas_whatsapp() -> list:
    s = HOME / "storage" / "shared"
    pastas = [s / "Android" / "media" / "com.whatsapp" / "WhatsApp" / "Media" / "WhatsApp Voice Notes",
              s / "Android" / "media" / "com.whatsapp" / "WhatsApp" / "Media" / "WhatsApp Audio",
              s / "WhatsApp" / "Media" / "WhatsApp Voice Notes"]
    return [(p, 3) for p in pastas if p.exists()]


def _depois_do_texto(texto: str, titulo_nota: str) -> None:
    """Ações para um texto gerado (transcrição, OCR)."""
    print(f"\n{NEG}Texto:{RST}\n{texto}\n")
    while True:
        i = escolher("O que fazer com o texto?", ["Copiar", "Salvar como nota", "Traduzir", "Ouvir",
                                                  "Perguntar à IA sobre ele", "Pronto"])
        if i in (None, 5):
            return
        if i == 0:
            copiar_texto(texto)
        elif i == 1:
            ok(f"Nota salva: {salvar_nota(titulo_nota, texto).name}")
        elif i == 2:
            traducao, _ = traduzir(texto, cfg().get("tradutor_destino", "en"))
            print(f"\n{VERD}{traducao}{RST}\n")
        elif i == 3:
            with contextlib.suppress(ToonsError):
                falar(texto[:3500])
        elif i == 4:
            pergunta = perguntar("O que você quer saber? (Enter = resumir)", "Resuma e explique este texto.")
            conversa_ia(f"{pergunta}\n\n---\n{texto}")
            return


@submenu
def menu_voz():
    c = cfg()

    def instalar():
        compilar_whisper()
        if not modelo_whisper().exists() and confirmar("Baixar o modelo de voz agora?", True):
            baixar_modelo()

    def baixar_modelo():
        nomes = list(WHISPER_MODELOS)
        i = escolher("Qual modelo?", [f"{n}: {d}" for n, d in WHISPER_MODELOS.items()], 2)
        if i is None:
            return
        c["whisper_modelo"] = nomes[i]
        salvar_cfg()
        if not modelo_whisper().exists():
            baixar_arquivo(f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{nomes[i]}.bin",
                           modelo_whisper())
        ok(f"Modelo em uso: {nomes[i]}")

    def transcrever_arquivo():
        pastas = _pastas_whatsapp() + _pastas_de_arquivos()
        arq = escolher_arquivo("Qual áudio? (os do WhatsApp aparecem primeiro)", EXT_VOZ, pastas)
        if arq:
            _depois_do_texto(transcrever_audio(arq), f"Transcrição de {arq.name}")

    def ditar():
        if not tem("termux-microphone-record"):
            raise ToonsError("Precisa do Termux:API (pkg install termux-api + app Termux:API).")
        arq = DATA_DIR / "tmp" / "ditado.m4a"
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.unlink(missing_ok=True)
        _tapi(["termux-microphone-record", "-f", str(arq), "-l", "0"], 20, json_saida=False)
        try:
            input(f"{VERM}● Gravando...{RST} fale e aperte Enter para parar. ")
        finally:
            _tapi(["termux-microphone-record", "-q"], 20, json_saida=False)
        time.sleep(1)
        if not arq.exists() or arq.stat().st_size == 0:
            raise ToonsError("Nada foi gravado (o Termux:API tem permissão de microfone?).")
        _depois_do_texto(transcrever_audio(arq), f"Ditado {datetime.now():%d/%m %H:%M}")

    def falar_texto():
        texto = perguntar("Texto para falar")
        if texto:
            falar(texto)

    def configurar_voz():
        with contextlib.suppress(ToonsError):
            motores = _tapi(["termux-tts-engines"], 15)
            if isinstance(motores, list) and motores:
                print("Motores de voz instalados: " + ", ".join(m.get("label", m.get("name", "?")) for m in motores))
        c["tts_idioma"] = perguntar("Idioma da voz (pt, en, es...; Enter = do sistema)", c.get("tts_idioma", ""))
        c["tts_velocidade"] = perguntar_float("Velocidade (1 = normal, 1.5 = mais rápido)", c.get("tts_velocidade", 1.0))
        salvar_cfg()
        with contextlib.suppress(ToonsError):
            falar("Assim fica a minha voz.")

    pronto = lambda: "pronto" if whisper_bin() and modelo_whisper().exists() else "não instalado"  # noqa: E731
    menu("🎙️ Voz para texto e texto para voz", [
        ("Transcrever um áudio (WhatsApp, gravações...)", transcrever_arquivo),
        ("Ditar uma nota (grava e transcreve)", ditar),
        ("Falar um texto", falar_texto),
        ("Configurar a voz (idioma e velocidade)", configurar_voz),
        (lambda: f"Instalar o whisper ({pronto()})", instalar),
        (lambda: f"Baixar/trocar modelo de voz ({c.get('whisper_modelo', 'base')})", baixar_modelo),
    ], cabecalho=lambda: print(f"{DIM}A transcrição roda no próprio celular (whisper.cpp): nada vai para a "
                               f"internet.{RST}"))


# ── Ler texto de imagens (OCR) ───────────────────────────────────────

def garantir_tesseract(idiomas=("por", "eng")) -> bool:
    if not garantir_cmd("tesseract"):
        return False
    lista = rodar(["tesseract", "--list-langs"], capturar=True, timeout=30, mostrar=False)
    texto = (lista.stdout or "") + (lista.stderr or "")
    pasta = re.search(r'"([^"]+)"', texto)
    instalados = set(texto.split())
    for idioma in idiomas:
        if idioma in instalados:
            continue
        destino = Path(pasta.group(1) if pasta else f"{PREFIX}/share/tessdata") / f"{idioma}.traineddata"
        info(f"Baixando o idioma '{idioma}' do OCR...")
        baixar_arquivo(f"https://github.com/tesseract-ocr/tessdata_fast/raw/main/{idioma}.traineddata", destino)
    return True


def ocr(imagem: Path, idiomas: str = "por+eng") -> str:
    proc = rodar(["tesseract", str(imagem), "stdout", "-l", idiomas], capturar=True, timeout=300, mostrar=False)
    if proc.returncode != 0:
        raise ToonsError(f"O tesseract falhou: {(proc.stderr or '').strip()[-200:]}")
    return re.sub(r"\n{3,}", "\n\n", proc.stdout or "").strip()


def ultimo_print() -> Path | None:
    s = HOME / "storage" / "shared"
    pastas = [(p, 1) for p in (s / "Pictures" / "Screenshots", s / "DCIM" / "Screenshots") if p.exists()]
    prints = listar_arquivos(EXT_IMAGEM, pastas, limite=1) if pastas else []
    return prints[0] if prints else None


@submenu
def menu_ocr():
    def ler_de(origem: str):
        if not garantir_tesseract():
            return
        if origem == "foto":
            arq = foto(DATA_DIR / "tmp" / "ocr.jpg")
        elif origem == "print":
            arq = ultimo_print()
            if not arq:
                raise ToonsError("Não achei prints (pasta Screenshots).")
            info(f"Usando o print mais recente: {arq.name}")
        else:
            arq = escolher_arquivo("Qual imagem?", EXT_IMAGEM)
            if not arq:
                return
        info("Lendo o texto da imagem...")
        texto = ocr(arq)
        if not texto:
            raise ToonsError("Não achei texto na imagem (tente uma foto mais nítida, reta e bem iluminada).")
        _depois_do_texto(texto, f"Texto de {arq.name}")

    menu("🔍 Ler texto de imagens (OCR)", [
        ("Tirar uma foto e ler o texto", lambda: ler_de("foto")),
        ("Ler de uma imagem do celular", lambda: ler_de("arquivo")),
        ("Ler do último print de tela", lambda: ler_de("print")),
    ])


@submenu
def menu_ia():
    ia = ia_config()

    def configurar():
        provedores = list(IA_PROVEDORES)
        i = escolher("Provedor", list(IA_PROVEDORES.values()), provedores.index(ia["provedor"]) + 1)
        if i is None:
            return
        ia["provedor"] = provedor = provedores[i]
        _chave(provedor)
        j = escolher("O que mais?", ["Escolher o modelo (lista da API)", "Digitar o nome do modelo",
                                     "Trocar a chave da API", "Esforço do Claude (quanto pensa)",
                                     "Instruções do assistente", "Nada"])
        if j == 0:
            modelos = ia_listar_modelos(provedor)
            if modelos:
                atual = ia["modelos"].get(provedor)
                k = escolher("Modelo", modelos, modelos.index(atual) + 1 if atual in modelos else None)
                if k is not None:
                    ia["modelos"][provedor] = modelos[k]
        elif j == 1:
            ia["modelos"][provedor] = perguntar("Nome do modelo", ia["modelos"].get(provedor) or "")
        elif j == 2:
            ia["chaves"].pop(provedor, None)
            _chave(provedor)
        elif j == 3:
            k = escolher("Esforço (mais = respostas melhores, mais lentas e mais caras)",
                         ["low (rápido e barato)", "medium (padrão)", "high", "xhigh", "max"],
                         IA_ESFORCOS.index(ia.get("esforco", "medium")) + 1)
            if k is not None:
                ia["esforco"] = IA_ESFORCOS[k]
        elif j == 4:
            ia["sistema"] = editar_texto(ia["sistema"], ".txt") or IA_SISTEMA_PADRAO
        salvar_cfg()
        ok(f"{IA_PROVEDORES[provedor]} · {ia['modelos'].get(provedor) or '(sem modelo)'}")

    def pergunta_rapida():
        texto = perguntar("Pergunta")
        if texto:
            print(f"{CIANO}ia>{RST} ", end="")
            ia_responder([{"role": "user", "texto": texto}])

    def resumir():
        i = escolher("Resumir o quê?", ["Um arquivo (PDF, texto, livro)", "O que está copiado",
                                        "Uma página da internet"])
        if i is None:
            return
        if i == 0:
            arq = escolher_arquivo("Qual arquivo?", (".pdf", ".txt", ".md", ".epub", ".html"))
            texto = texto_de_arquivo(arq) if arq else ""
        elif i == 1:
            texto = _tapi(["termux-clipboard-get"], 10, json_saida=False)
        else:
            texto = texto_da_materia(_url_digitada(perguntar("Endereço")))
        if not texto.strip():
            raise ToonsError("Nada para resumir.")
        conversa_ia(f"Resuma o texto abaixo em tópicos curtos e diga os pontos principais.\n\n---\n{texto[:400000]}")

    def sobre_foto():
        i = escolher("Qual foto?", ["Tirar agora", "Escolher do celular"])
        if i is None:
            return
        arq = foto(DATA_DIR / "tmp" / "ia.jpg") if i == 0 else escolher_arquivo("Qual imagem?", EXT_IMAGEM)
        if arq:
            conversa_ia(perguntar("O que você quer saber da foto?", "Descreva esta imagem."), imagem=arq)

    atual = lambda: f"{IA_PROVEDORES[ia['provedor']]} · {ia['modelos'].get(ia['provedor']) or 'sem modelo'}"  # noqa: E731
    menu("✨ Inteligência artificial", [
        (lambda: f"💬 Conversar ({atual()})", conversa_ia),
        ("❓ Pergunta rápida", pergunta_rapida),
        ("📄 Resumir arquivo, texto copiado ou página", resumir),
        ("🖼️ Perguntar sobre uma foto", sobre_foto),
        ("⚙️ Configurar (Claude, ChatGPT ou Gemini; chave e modelo)", configurar),
        ("🎙️ Voz para texto e texto para voz", menu_voz),
        ("🔍 Ler texto de imagens (OCR)", menu_ocr),
        ("🧠 IA local, sem internet (llama.cpp)", menu_llm),
    ], cabecalho=lambda: print(f"{DIM}Na nuvem é preciso uma chave de API do provedor (paga por uso).{RST}"))


# ════════════════════════════════════════════════════════════════════
#  24. Diversão e aprendizado
# ════════════════════════════════════════════════════════════════════

LEITURA_FILE = DATA_DIR / "leitura.json"
APRENDER_FILE = DATA_DIR / "aprender.json"


def _recorde_menor(jogo: str, valor: float | None = None) -> float | None:
    """Recorde em que menor é melhor (tempo)."""
    recordes = ler_json(RECORDES_FILE, {})
    atual = recordes.get(jogo)
    if valor is not None and (atual is None or valor < atual):
        recordes[jogo] = valor
        gravar_json(RECORDES_FILE, recordes)
        return valor
    return atual


def _curses_cores(curses) -> None:
    with contextlib.suppress(curses.error):
        curses.start_color()
        curses.use_default_colors()
        for n, cor in enumerate((curses.COLOR_RED, curses.COLOR_GREEN, curses.COLOR_YELLOW, curses.COLOR_BLUE,
                                 curses.COLOR_MAGENTA, curses.COLOR_CYAN, curses.COLOR_WHITE), 1):
            curses.init_pair(n, cor, -1)


def _escrever(tela, y: int, x: int, texto: str, atributo: int = 0) -> None:
    """addstr que não estoura quando a tela é pequena."""
    alt, larg = tela.getmaxyx()
    if 0 <= y < alt and 0 <= x < larg:
        with contextlib.suppress(Exception):
            tela.addnstr(y, x, texto, max(0, larg - x - 1), atributo)


# ── 2048 ─────────────────────────────────────────────────────────────

def mover_linha_2048(linha: list) -> tuple:
    """Junta para a esquerda: ([2,2,4,0] → [4,4,0,0], 4 pontos)."""
    numeros = [n for n in linha if n]
    resultado, pontos, i = [], 0, 0
    while i < len(numeros):
        if i + 1 < len(numeros) and numeros[i] == numeros[i + 1]:
            resultado.append(numeros[i] * 2)
            pontos += numeros[i] * 2
            i += 2
        else:
            resultado.append(numeros[i])
            i += 1
    return resultado + [0] * (len(linha) - len(resultado)), pontos


def mover_2048(grade: list, direcao: str) -> tuple:
    """(nova grade, pontos) movendo para 'esq', 'dir', 'cima' ou 'baixo'."""
    linhas = [list(col) for col in zip(*grade)] if direcao in ("cima", "baixo") else [list(l) for l in grade]
    inverter = direcao in ("dir", "baixo")
    novas, pontos = [], 0
    for linha in linhas:
        movida, p = mover_linha_2048(linha[::-1] if inverter else linha)
        novas.append(movida[::-1] if inverter else movida)
        pontos += p
    if direcao in ("cima", "baixo"):
        novas = [list(col) for col in zip(*novas)]
    return novas, pontos


def jogo_2048() -> None:
    import curses

    def nova_peca(grade):
        vazias = [(i, j) for i in range(4) for j in range(4) if not grade[i][j]]
        if vazias:
            i, j = random.choice(vazias)
            grade[i][j] = 4 if random.random() < 0.1 else 2

    def jogo(tela):
        curses.curs_set(0)
        tela.keypad(True)
        _curses_cores(curses)
        cores = {2: 7, 4: 7, 8: 3, 16: 3, 32: 1, 64: 1, 128: 2, 256: 2, 512: 6, 1024: 4, 2048: 5}
        teclas = {curses.KEY_LEFT: "esq", curses.KEY_RIGHT: "dir", curses.KEY_UP: "cima", curses.KEY_DOWN: "baixo",
                  ord("a"): "esq", ord("d"): "dir", ord("w"): "cima", ord("s"): "baixo"}
        grade, pontos, venceu = [[0] * 4 for _ in range(4)], 0, False
        nova_peca(grade)
        nova_peca(grade)
        while True:
            tela.erase()
            _escrever(tela, 0, 0, f" 2048   pontos: {pontos}   recorde: {_recorde('2048')}", curses.A_BOLD)
            for i, linha in enumerate(grade):
                _escrever(tela, 2 + i * 2, 1, "+------" * 4 + "+")
                for j, n in enumerate(linha):
                    _escrever(tela, 3 + i * 2, 1 + j * 7, "|")
                    if n:
                        _escrever(tela, 3 + i * 2, 2 + j * 7, f"{n:^6}",
                                  curses.color_pair(cores.get(n, 5)) | curses.A_BOLD)
                _escrever(tela, 3 + i * 2, 29, "|")
            _escrever(tela, 10, 1, "+------" * 4 + "+")
            _escrever(tela, 12, 1, "setas ou WASD movem · r recomeça · q sai")
            sem_jogadas = all(mover_2048(grade, d)[0] == grade for d in ("esq", "dir", "cima", "baixo"))
            if sem_jogadas:
                _escrever(tela, 14, 1, f"FIM DE JOGO! {pontos} pontos. r recomeça, q sai.", curses.A_REVERSE)
            if not venceu and any(2048 in l for l in grade):
                venceu = True
                _escrever(tela, 14, 1, "VOCÊ FEZ 2048! 🎉 Continue jogando!", curses.A_REVERSE)
            tela.refresh()
            tecla = tela.getch()
            if tecla in (ord("q"), 27):
                return pontos
            if tecla == ord("r"):
                _recorde("2048", pontos)
                grade, pontos, venceu = [[0] * 4 for _ in range(4)], 0, False
                nova_peca(grade)
                nova_peca(grade)
                continue
            direcao = teclas.get(tecla)
            if direcao and not sem_jogadas:
                nova, ganhos = mover_2048(grade, direcao)
                if nova != grade:
                    grade, pontos = nova, pontos + ganhos
                    nova_peca(grade)

    pontos = curses.wrapper(jogo)
    antigo = _recorde("2048")
    _recorde("2048", pontos)
    print(f"Você fez {pontos} pontos." + (" 🏆 Novo recorde!" if pontos > antigo else ""))


# ── Campo minado ─────────────────────────────────────────────────────

def vizinhos(i: int, j: int, linhas: int, colunas: int):
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if (di or dj) and 0 <= i + di < linhas and 0 <= j + dj < colunas:
                yield i + di, j + dj


def campo_minado() -> None:
    import curses
    niveis = [("Fácil 9x9, 10 minas", 9, 9, 10), ("Médio 16x16, 40 minas", 16, 16, 40),
              ("Difícil 16x30, 99 minas (tela larga)", 16, 30, 99)]
    k = escolher("Nível", [n[0] for n in niveis])
    if k is None:
        return
    nome_nivel, linhas, colunas, total_minas = niveis[k]

    def jogo(tela):
        curses.curs_set(0)
        tela.keypad(True)
        _curses_cores(curses)
        alt, larg = tela.getmaxyx()
        if alt < linhas + 5 or larg < colunas * 2 + 2:
            tela.addstr(0, 0, "Tela pequena para esse nível. Tecla para sair.")
            tela.getch()
            return None
        minas, aberto, bandeira = set(), set(), set()
        cy = cx = 0
        inicio, perdeu = None, False

        def numero(i, j):
            return sum((a, b) in minas for a, b in vizinhos(i, j, linhas, colunas))

        def abrir(i, j):
            pilha = [(i, j)]
            while pilha:
                a, b = pilha.pop()
                if (a, b) in aberto or (a, b) in bandeira:
                    continue
                aberto.add((a, b))
                if numero(a, b) == 0:
                    pilha.extend(v for v in vizinhos(a, b, linhas, colunas) if v not in aberto)

        cores_num = {1: 4, 2: 2, 3: 1, 4: 5, 5: 1, 6: 6, 7: 7, 8: 7}
        while True:
            venceu = len(aberto) == linhas * colunas - total_minas and minas
            tempo = int(time.time() - inicio) if inicio else 0
            tela.erase()
            _escrever(tela, 0, 0, f" 💣 {total_minas - len(bandeira)}   ⏱ {tempo}s   {nome_nivel.split(',')[0]}",
                      curses.A_BOLD)
            for i in range(linhas):
                for j in range(colunas):
                    if (i, j) in aberto or ((perdeu or venceu) and (i, j) in minas):
                        if (i, j) in minas:
                            ch, attr = "*", curses.color_pair(1) | curses.A_BOLD
                        else:
                            n = numero(i, j)
                            ch, attr = (str(n), curses.color_pair(cores_num[n]) | curses.A_BOLD) if n else (" ", 0)
                    elif (i, j) in bandeira:
                        ch, attr = "F", curses.color_pair(3) | curses.A_BOLD
                    else:
                        ch, attr = "·", curses.A_DIM
                    if (i, j) == (cy, cx):
                        attr |= curses.A_REVERSE
                    _escrever(tela, 2 + i, 1 + j * 2, ch, attr)
            ajuda = "setas movem · Enter/Espaço abre · f bandeira · q sai"
            if perdeu:
                ajuda = "💥 BOOM! Você perdeu. r recomeça · q sai"
            elif venceu:
                ajuda = f"🎉 Você venceu em {tempo}s! r recomeça · q sai"
            _escrever(tela, linhas + 3, 1, ajuda, curses.A_REVERSE if perdeu or venceu else 0)
            tela.refresh()
            tecla = tela.getch()
            if tecla in (ord("q"), 27):
                return tempo if venceu else None
            if tecla == ord("r"):
                if venceu:
                    _recorde_menor(f"campo_minado_{k}", tempo)
                minas, aberto, bandeira, inicio, perdeu = set(), set(), set(), None, False
                continue
            if perdeu or venceu:
                continue
            if tecla in (curses.KEY_UP, ord("w")):
                cy = (cy - 1) % linhas
            elif tecla in (curses.KEY_DOWN, ord("s")):
                cy = (cy + 1) % linhas
            elif tecla in (curses.KEY_LEFT, ord("a")):
                cx = (cx - 1) % colunas
            elif tecla in (curses.KEY_RIGHT, ord("d")):
                cx = (cx + 1) % colunas
            elif tecla == ord("f") and (cy, cx) not in aberto:
                bandeira ^= {(cy, cx)}
            elif tecla in (10, 13, curses.KEY_ENTER, ord(" ")) and (cy, cx) not in bandeira:
                if not minas:  # a primeira jogada nunca cai numa mina
                    proibidas = {(cy, cx), *vizinhos(cy, cx, linhas, colunas)}
                    livres = [(i, j) for i in range(linhas) for j in range(colunas) if (i, j) not in proibidas]
                    minas = set(random.sample(livres, total_minas))
                    inicio = time.time()
                if (cy, cx) in minas:
                    perdeu = True
                else:
                    abrir(cy, cx)

    tempo = curses.wrapper(jogo)
    if tempo is not None:
        recorde = _recorde_menor(f"campo_minado_{k}")
        novo = _recorde_menor(f"campo_minado_{k}", tempo) == tempo and (recorde is None or tempo < recorde)
        print(f"Venceu em {tempo}s." + (" 🏆 Novo recorde!" if novo else ""))


# ── Sudoku ───────────────────────────────────────────────────────────

_SUDOKU_VIZINHOS = [
    sorted({r * 9 + c for c in range(9)} | {k * 9 + (i % 9) for k in range(9)} |
           {(r // 3 * 3 + a) * 9 + (i % 9) // 3 * 3 + b for a in range(3) for b in range(3)} - {i})
    for i in range(81) for r in [i // 9]
]


def resolver_sudoku(grade: list, limite: int = 2, aleatorio: bool = False) -> tuple:
    """(quantidade de soluções até `limite`, primeira solução). `grade`: 81 números, 0 = vazio."""
    g = list(grade)
    achadas = {"n": 0, "primeira": None}

    def candidatos(i):
        usados = {g[v] for v in _SUDOKU_VIZINHOS[i]}
        return [n for n in range(1, 10) if n not in usados]

    def busca():
        melhor, opcoes = None, None
        for i in range(81):
            if g[i] == 0:
                cands = candidatos(i)
                if not cands:
                    return
                if melhor is None or len(cands) < len(opcoes):
                    melhor, opcoes = i, cands
                    if len(cands) == 1:
                        break
        if melhor is None:
            achadas["n"] += 1
            if achadas["primeira"] is None:
                achadas["primeira"] = list(g)
            return
        if aleatorio:
            random.shuffle(opcoes)
        for n in opcoes:
            g[melhor] = n
            busca()
            g[melhor] = 0
            if achadas["n"] >= limite:
                return

    busca()
    return achadas["n"], achadas["primeira"]


def gerar_sudoku(vazias: int = 45) -> tuple:
    """(enigma com solução única, solução)."""
    _, solucao = resolver_sudoku([0] * 81, limite=1, aleatorio=True)
    enigma = list(solucao)
    posicoes = list(range(81))
    random.shuffle(posicoes)
    tiradas = 0
    for p in posicoes:
        if tiradas >= vazias:
            break
        guardado, enigma[p] = enigma[p], 0
        if resolver_sudoku(enigma, limite=2)[0] != 1:
            enigma[p] = guardado
        else:
            tiradas += 1
    return enigma, solucao


def sudoku() -> None:
    import curses
    niveis = [("Fácil", 36), ("Médio", 46), ("Difícil", 54)]
    k = escolher("Nível", [n for n, _ in niveis])
    if k is None:
        return
    info("Gerando um sudoku com solução única...")
    enigma, solucao = gerar_sudoku(niveis[k][1])

    def jogo(tela):
        curses.curs_set(0)
        tela.keypad(True)
        _curses_cores(curses)
        g = list(enigma)
        cursor, verificar, inicio, dicas = 0, False, time.time(), 0
        while True:
            tela.erase()
            completo = g == solucao
            _escrever(tela, 0, 0, f" SUDOKU {niveis[k][0]}   ⏱ {int(time.time() - inicio)}s   dicas: {dicas}",
                      curses.A_BOLD)
            for linha in range(9):
                y = 2 + linha + linha // 3
                if linha % 3 == 0:
                    _escrever(tela, y - 1 if linha else 1, 0, "+-------+-------+-------+")
                texto_x = 0
                for col in range(9):
                    if col % 3 == 0:
                        _escrever(tela, y, texto_x, "|")
                        texto_x += 2
                    i = linha * 9 + col
                    n = g[i]
                    attr = curses.A_BOLD if enigma[i] else curses.color_pair(6)
                    if n and verificar and not enigma[i] and n != solucao[i]:
                        attr = curses.color_pair(1) | curses.A_BOLD
                    if i == cursor:
                        attr |= curses.A_REVERSE
                    _escrever(tela, y, texto_x, str(n) if n else ".", attr)
                    texto_x += 2
                _escrever(tela, y, texto_x, "|")
            _escrever(tela, 13, 0, "+-------+-------+-------+")
            ajuda = "🎉 RESOLVIDO! q sai" if completo else \
                "setas movem · 1-9 escreve · 0/Del apaga · v confere · d dica · q sai"
            _escrever(tela, 15, 0, ajuda, curses.A_REVERSE if completo else 0)
            tela.refresh()
            tecla = tela.getch()
            if tecla in (ord("q"), 27):
                return int(time.time() - inicio) if completo else None
            if completo:
                continue
            linha, col = divmod(cursor, 9)
            if tecla in (curses.KEY_UP, ord("w")):
                cursor = ((linha - 1) % 9) * 9 + col
            elif tecla in (curses.KEY_DOWN, ord("s")):
                cursor = ((linha + 1) % 9) * 9 + col
            elif tecla in (curses.KEY_LEFT, ord("a")):
                cursor = linha * 9 + (col - 1) % 9
            elif tecla in (curses.KEY_RIGHT,):
                cursor = linha * 9 + (col + 1) % 9
            elif ord("1") <= tecla <= ord("9") and not enigma[cursor]:
                g[cursor] = tecla - ord("0")
            elif tecla in (ord("0"), ord("."), curses.KEY_BACKSPACE, curses.KEY_DC, 127, 8) and not enigma[cursor]:
                g[cursor] = 0
            elif tecla == ord("v"):
                verificar = not verificar
            elif tecla == ord("d") and not enigma[cursor]:
                g[cursor] = solucao[cursor]
                dicas += 1

    tempo = curses.wrapper(jogo)
    if tempo is not None:
        recorde = _recorde_menor(f"sudoku_{k}")
        _recorde_menor(f"sudoku_{k}", tempo)
        print(f"Resolvido em {fmt_relogio(tempo)}." + (" 🏆 Novo recorde!" if recorde is None or tempo < recorde else ""))


# ── Forca ────────────────────────────────────────────────────────────

PALAVRAS_POR_TEMA = {
    "Frutas": ["abacaxi", "banana", "laranja", "morango", "melancia", "goiaba", "maracujá", "jabuticaba", "abacate",
               "mamão", "manga", "pitanga", "framboesa", "tangerina", "carambola", "acerola", "cupuaçu", "açaí"],
    "Animais": ["elefante", "girafa", "tartaruga", "jacaré", "capivara", "tamanduá", "onça", "papagaio", "golfinho",
                "borboleta", "cachorro", "coruja", "pinguim", "camaleão", "tucano", "macaco", "jabuti", "lobo"],
    "Países": ["brasil", "argentina", "portugal", "japão", "alemanha", "canadá", "austrália", "méxico", "egito",
               "noruega", "chile", "colômbia", "itália", "frança", "marrocos", "tailândia", "uruguai", "peru"],
    "Objetos": ["guarda-chuva", "travesseiro", "computador", "geladeira", "bicicleta", "telescópio", "tesoura",
                "cadeira", "liquidificador", "ventilador", "relógio", "mochila", "caderno", "lanterna", "espelho"],
    "Profissões": ["professor", "engenheira", "médico", "programador", "bombeiro", "cozinheira", "jardineiro",
                   "astronauta", "advogada", "veterinário", "motorista", "eletricista", "enfermeira", "arquiteto"],
    "Comidas": ["feijoada", "brigadeiro", "coxinha", "pastel", "tapioca", "moqueca", "pamonha", "acarajé",
                "churrasco", "lasanha", "panqueca", "quindim", "pipoca", "macarrão", "farofa", "cuscuz"],
}
PALAVRAS_FORCA = [p for lista in PALAVRAS_POR_TEMA.values() for p in lista]
DESENHO_FORCA = [
    ["  +---+", "  |   |", "      |", "      |", "      |", "=======",],
    ["  +---+", "  |   |", "  O   |", "      |", "      |", "=======",],
    ["  +---+", "  |   |", "  O   |", "  |   |", "      |", "=======",],
    ["  +---+", "  |   |", "  O   |", " /|   |", "      |", "=======",],
    ["  +---+", "  |   |", "  O   |", " /|\\  |", "      |", "=======",],
    ["  +---+", "  |   |", "  O   |", " /|\\  |", " /    |", "=======",],
    ["  +---+", "  |   |", "  O   |", " /|\\  |", " / \\  |", "=======",],
]


def forca() -> None:
    temas = list(PALAVRAS_POR_TEMA)
    i = escolher("Tema", ["Sorteado"] + temas)
    if i is None:
        return
    tema = random.choice(temas) if i == 0 else temas[i - 1]
    palavra = random.choice(PALAVRAS_POR_TEMA[tema])
    base = sem_acento(palavra).lower()
    certas, erradas = set(), []
    while True:
        limpar()
        titulo(f"🪢 Forca · tema: {tema}")
        for linha in DESENHO_FORCA[len(erradas)]:
            print("   " + linha)
        mostrada = " ".join(ch if not ch.isalpha() or sem_acento(ch).lower() in certas else "_" for ch in palavra)
        print(f"\n   {NEG}{mostrada.upper()}{RST}\n")
        print(f"   Erros: {VERM}{' '.join(erradas).upper() or '-'}{RST}   ({6 - len(erradas)} chance(s))")
        if all(not ch.isalpha() or ch in certas for ch in base):
            ok(f"Você acertou: {palavra.upper()}! 🎉")
            _recorde("forca_vitorias", _recorde("forca_vitorias") + 1)
            return
        if len(erradas) >= 6:
            erro(f"Enforcado! A palavra era {palavra.upper()}.")
            return
        print(f"\n   {DIM}Digite uma letra (ou a palavra inteira). Esc sai.{RST}")
        if setas_ativas():
            tecla = ler_tecla()
            if tecla == "esc":
                return
            letra = sem_acento(tecla).lower()
        else:
            letra = sem_acento(perguntar("Letra")).lower()
        if len(letra) > 1:
            if letra == base:
                certas.update(base)
            else:
                erradas.append(letra[:10])
            continue
        if not letra.isalpha() or letra in certas or letra in erradas:
            continue
        if letra in base:
            certas.add(letra)
        else:
            erradas.append(letra)


# ── Jogo da velha ────────────────────────────────────────────────────

_LINHAS_VELHA = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def vencedor_velha(tab: list):
    for a, b, c in _LINHAS_VELHA:
        if tab[a] and tab[a] == tab[b] == tab[c]:
            return tab[a]
    return "empate" if all(tab) else None


def melhor_jogada_velha(tab: list, eu: str = "O") -> int:
    """Minimax: a jogada que nunca perde."""
    outro = "X" if eu == "O" else "O"

    def valor(t, vez, prof):
        v = vencedor_velha(t)
        if v == eu:
            return 10 - prof
        if v == outro:
            return prof - 10
        if v == "empate":
            return 0
        notas = []
        for i in range(9):
            if not t[i]:
                t[i] = vez
                notas.append(valor(t, outro if vez == eu else eu, prof + 1))
                t[i] = ""
        return max(notas) if vez == eu else min(notas)

    opcoes = []
    for i in range(9):
        if not tab[i]:
            tab[i] = eu
            opcoes.append((valor(tab, outro, 1), i))
            tab[i] = ""
    melhor = max(n for n, _ in opcoes)
    return random.choice([i for n, i in opcoes if n == melhor])


def jogo_da_velha() -> None:
    niveis = ["Fácil", "Médio", "Impossível"]
    nivel = escolher("Dificuldade", niveis, 2)
    if nivel is None:
        return
    placar = {"você": 0, "celular": 0, "empate": 0}
    with TelaCheia():
        while True:
            tab, cursor, vez = [""] * 9, 4, "X" if sum(placar.values()) % 2 == 0 else "O"
            while not vencedor_velha(tab):
                if vez == "O":
                    livres = [i for i in range(9) if not tab[i]]
                    usar_ia = nivel == 2 or (nivel == 1 and random.random() < 0.6)
                    tab[melhor_jogada_velha(tab) if usar_ia else random.choice(livres)] = "O"
                    vez = "X"
                    continue
                linhas = ["", f"  {NEG}⭕ Jogo da velha · {niveis[nivel]}{RST}", "",
                          f"  Você {NEG}X{RST} {placar['você']} · celular {NEG}O{RST} {placar['celular']} · "
                          f"empates {placar['empate']}", ""]
                for linha in range(3):
                    celulas = []
                    for col in range(3):
                        i = linha * 3 + col
                        simbolo = tab[i] or " "
                        cor = AZUL if simbolo == "X" else VERM if simbolo == "O" else ""
                        txt = f" {cor}{NEG}{simbolo}{RST} "
                        celulas.append(f"{INV}{txt}{RST}" if i == cursor else txt)
                    linhas.append("    " + "│".join(celulas))
                    if linha < 2:
                        linhas.append("    ───┼───┼───")
                linhas += ["", f"  {DIM}setas escolhem · Enter joga · Esc sai{RST}"]
                desenhar(linhas)
                tecla = ler_tecla()
                if tecla in ("esc", "q"):
                    return
                movimentos = {"esq": -1, "dir": 1, "cima": -3, "baixo": 3}
                if tecla in movimentos:
                    cursor = (cursor + movimentos[tecla]) % 9
                elif tecla.isdigit() and tecla != "0":
                    cursor = int(tecla) - 1
                    tecla = "enter"
                if tecla in ("enter", " ") and not tab[cursor]:
                    tab[cursor] = "X"
                    vez = "O"
            v = vencedor_velha(tab)
            placar["você" if v == "X" else "celular" if v == "O" else "empate"] += 1
            linhas = [""] + ["    " + " │ ".join(t or " " for t in tab[r * 3:r * 3 + 3]) for r in range(3)]
            resultado = "🎉 Você venceu!" if v == "X" else "😈 O celular venceu!" if v == "O" else "🤝 Empate!"
            desenhar(linhas + ["", f"  {NEG}{resultado}{RST}", "",
                               f"  {DIM}Enter joga de novo · Esc sai{RST}"])
            if ler_tecla() in ("esc", "q"):
                return


# ── Tetris ───────────────────────────────────────────────────────────

PECAS_TETRIS = {
    "I": [(0, 0), (0, 1), (0, 2), (0, 3)], "O": [(0, 0), (0, 1), (1, 0), (1, 1)],
    "T": [(0, 0), (0, 1), (0, 2), (1, 1)], "S": [(0, 1), (0, 2), (1, 0), (1, 1)],
    "Z": [(0, 0), (0, 1), (1, 1), (1, 2)], "J": [(0, 0), (1, 0), (1, 1), (1, 2)],
    "L": [(0, 2), (1, 0), (1, 1), (1, 2)],
}
CORES_TETRIS = {"I": 6, "O": 3, "T": 5, "S": 2, "Z": 1, "J": 4, "L": 7}


def girar_peca(blocos: list) -> list:
    """Gira 90° no sentido horário e encosta no canto (0, 0)."""
    girados = [(c, -l) for l, c in blocos]
    min_l, min_c = min(l for l, _ in girados), min(c for _, c in girados)
    return [(l - min_l, c - min_c) for l, c in girados]


def tetris() -> None:
    import curses
    linhas_t, colunas_t = 20, 10

    def jogo(tela):
        curses.curs_set(0)
        tela.keypad(True)
        tela.nodelay(True)
        _curses_cores(curses)
        alt, larg = tela.getmaxyx()
        if alt < linhas_t + 2 or larg < colunas_t * 2 + 14:
            tela.nodelay(False)
            tela.addstr(0, 0, "Tela pequena (esconda o teclado ou gire o celular). Tecla para sair.")
            tela.getch()
            return 0
        campo = [[None] * colunas_t for _ in range(linhas_t)]
        saco = []

        def sortear():
            if not saco:
                saco.extend(random.sample(list(PECAS_TETRIS), len(PECAS_TETRIS)))
            return saco.pop()

        def cabe(blocos, y, x):
            return all(0 <= x + c < colunas_t and y + l < linhas_t and (y + l < 0 or campo[y + l][x + c] is None)
                       for l, c in blocos)

        tipo, proximo = sortear(), sortear()
        blocos, y, x = PECAS_TETRIS[tipo], 0, 3
        pontos, linhas_feitas, nivel, pausado = 0, 0, 1, False
        ultima_queda = time.time()
        while True:
            intervalo = max(0.08, 0.8 - (nivel - 1) * 0.07)
            tecla = tela.getch()
            if tecla in (ord("q"), 27):
                return pontos
            if tecla == ord("p"):
                pausado = not pausado
            if not pausado:
                if tecla in (curses.KEY_LEFT, ord("a")) and cabe(blocos, y, x - 1):
                    x -= 1
                elif tecla in (curses.KEY_RIGHT, ord("d")) and cabe(blocos, y, x + 1):
                    x += 1
                elif tecla in (curses.KEY_UP, ord("w")):
                    girada = girar_peca(blocos)
                    for desvio in (0, -1, 1, -2, 2):
                        if cabe(girada, y, x + desvio):
                            blocos, x = girada, x + desvio
                            break
                elif tecla in (curses.KEY_DOWN, ord("s")) and cabe(blocos, y + 1, x):
                    y += 1
                    pontos += 1
                elif tecla == ord(" "):
                    while cabe(blocos, y + 1, x):
                        y += 1
                        pontos += 2
                    ultima_queda = 0
                if time.time() - ultima_queda >= intervalo:
                    ultima_queda = time.time()
                    if cabe(blocos, y + 1, x):
                        y += 1
                    else:
                        for l, c in blocos:
                            if y + l < 0:
                                return pontos
                            campo[y + l][x + c] = tipo
                        cheias = [i for i, linha in enumerate(campo) if all(linha)]
                        for i in cheias:
                            del campo[i]
                            campo.insert(0, [None] * colunas_t)
                        linhas_feitas += len(cheias)
                        pontos += (0, 100, 300, 500, 800)[len(cheias)] * nivel
                        nivel = 1 + linhas_feitas // 10
                        tipo, proximo = proximo, sortear()
                        blocos, y, x = PECAS_TETRIS[tipo], 0, 3
                        if not cabe(blocos, y, x):
                            return pontos
            tela.erase()
            for i in range(linhas_t):
                _escrever(tela, i, 0, "│")
                _escrever(tela, i, colunas_t * 2 + 1, "│")
                for j in range(colunas_t):
                    if campo[i][j]:
                        _escrever(tela, i, 1 + j * 2, "██", curses.color_pair(CORES_TETRIS[campo[i][j]]))
            _escrever(tela, linhas_t, 0, "└" + "──" * colunas_t + "┘")
            for l, c in blocos:
                if y + l >= 0:
                    _escrever(tela, y + l, 1 + (x + c) * 2, "██", curses.color_pair(CORES_TETRIS[tipo]) | curses.A_BOLD)
            px = colunas_t * 2 + 4
            _escrever(tela, 0, px, "TETRIS", curses.A_BOLD)
            _escrever(tela, 2, px, f"pontos {pontos}")
            _escrever(tela, 3, px, f"linhas {linhas_feitas}")
            _escrever(tela, 4, px, f"nível  {nivel}")
            _escrever(tela, 5, px, f"recorde {_recorde('tetris')}")
            _escrever(tela, 7, px, "próxima:")
            for l, c in PECAS_TETRIS[proximo]:
                _escrever(tela, 8 + l, px + c * 2, "██", curses.color_pair(CORES_TETRIS[proximo]))
            for k, ajuda in enumerate(("←→ move", "↑ gira", "↓ desce", "Espaço cai", "p pausa", "q sai")):
                _escrever(tela, 11 + k, px, ajuda, curses.A_DIM)
            if pausado:
                _escrever(tela, linhas_t // 2, 4, " PAUSADO ", curses.A_REVERSE)
            tela.refresh()
            time.sleep(0.02)

    pontos = curses.wrapper(jogo)
    antigo = _recorde("tetris")
    _recorde("tetris", pontos)
    print(f"Fim de jogo: {pontos} pontos." + (" 🏆 Novo recorde!" if pontos > antigo else ""))


# ── Quiz ─────────────────────────────────────────────────────────────

PERGUNTAS_QUIZ = [
    ("Qual é a capital do Brasil?", ["Rio de Janeiro", "São Paulo", "Brasília", "Salvador"], 2),
    ("Qual é o maior planeta do Sistema Solar?", ["Saturno", "Júpiter", "Netuno", "Terra"], 1),
    ("Quantos estados tem o Brasil, sem contar o Distrito Federal?", ["24", "25", "26", "27"], 2),
    ("Em que ano o Brasil declarou a independência?", ["1500", "1822", "1889", "1888"], 1),
    ("Quem pintou a Mona Lisa?", ["Michelangelo", "Leonardo da Vinci", "Rafael", "Van Gogh"], 1),
    ("Qual é a fórmula química da água?", ["CO2", "O2", "H2O", "NaCl"], 2),
    ("Qual é o maior oceano do mundo?", ["Atlântico", "Índico", "Ártico", "Pacífico"], 3),
    ("Quantas Copas do Mundo a seleção brasileira masculina venceu?", ["3", "4", "5", "6"], 2),
    ("Quem escreveu 'Dom Casmurro'?", ["José de Alencar", "Machado de Assis", "Clarice Lispector",
                                       "Jorge Amado"], 1),
    ("Qual é o planeta mais próximo do Sol?", ["Vênus", "Marte", "Mercúrio", "Terra"], 2),
    ("Quantos ossos tem o corpo humano adulto?", ["186", "206", "226", "306"], 1),
    ("Em que ano o ser humano pisou na Lua pela primeira vez?", ["1959", "1965", "1969", "1975"], 2),
    ("Qual é a moeda do Japão?", ["Yuan", "Won", "Iene", "Rupia"], 2),
    ("Qual é o maior país do mundo em área?", ["China", "Canadá", "Estados Unidos", "Rússia"], 3),
    ("Que gás as plantas absorvem na fotossíntese?", ["Oxigênio", "Gás carbônico", "Nitrogênio", "Hélio"], 1),
    ("Qual é o maior rio totalmente brasileiro?", ["Amazonas", "São Francisco", "Paraná", "Tocantins"], 1),
    ("Quem descobriu a penicilina?", ["Louis Pasteur", "Alexander Fleming", "Marie Curie", "Oswaldo Cruz"], 1),
    ("Quantos lados tem um hexágono?", ["5", "6", "7", "8"], 1),
    ("Qual é o menor estado do Brasil em área?", ["Alagoas", "Sergipe", "Espírito Santo", "Rio de Janeiro"], 1),
    ("Qual é o maior estado do Brasil em área?", ["Pará", "Mato Grosso", "Amazonas", "Minas Gerais"], 2),
    ("Quem escreveu 'Os Lusíadas'?", ["Fernando Pessoa", "Luís de Camões", "Eça de Queirós",
                                      "Machado de Assis"], 1),
    ("Qual é o símbolo químico do ferro?", ["F", "Fr", "Fe", "Ir"], 2),
    ("Em que continente fica o Egito?", ["Ásia", "África", "Europa", "Oceania"], 1),
    ("Qual é a capital da Argentina?", ["Montevidéu", "Santiago", "Buenos Aires", "Lima"], 2),
    ("Qual é a capital da Austrália?", ["Sydney", "Melbourne", "Camberra", "Perth"], 2),
    ("Quanto dura o tempo regulamentar de uma partida de futebol?", ["60 min", "80 min", "90 min", "100 min"], 2),
    ("O que significa a sigla CPU?", ["Central de Programas Úteis", "Unidade Central de Processamento",
                                      "Computador Pessoal Universal", "Controle de Placa Única"], 1),
    ("Quem criou o Linux?", ["Bill Gates", "Linus Torvalds", "Steve Jobs", "Richard Stallman"], 1),
    ("Em que ano foi lançado o primeiro iPhone?", ["2005", "2007", "2009", "2010"], 1),
    ("Qual é o maior mamífero do mundo?", ["Elefante-africano", "Baleia-azul", "Girafa", "Tubarão-baleia"], 1),
    ("Que aparelho mede terremotos?", ["Barômetro", "Termômetro", "Sismógrafo", "Anemômetro"], 2),
    ("Quantos jogadores de cada time ficam em quadra no vôlei?", ["5", "6", "7", "11"], 1),
    ("Quem foi a primeira mulher eleita presidente do Brasil?", ["Marina Silva", "Dilma Rousseff",
                                                                 "Zélia Cardoso", "Benedita da Silva"], 1),
    ("Em que ano foi assinada a Lei Áurea, que aboliu a escravidão no Brasil?", ["1822", "1871", "1888", "1889"], 2),
    ("Em que ano foi proclamada a República no Brasil?", ["1822", "1888", "1889", "1930"], 2),
    ("Quem compôs 'As Quatro Estações'?", ["Mozart", "Beethoven", "Vivaldi", "Bach"], 2),
    ("Qual é o ponto mais alto do Brasil?", ["Pico da Bandeira", "Pico da Neblina", "Monte Roraima",
                                             "Pico das Agulhas Negras"], 1),
    ("Qual é a capital de Minas Gerais?", ["Uberlândia", "Juiz de Fora", "Belo Horizonte", "Ouro Preto"], 2),
    ("Qual é a capital do Canadá?", ["Toronto", "Vancouver", "Montreal", "Ottawa"], 3),
    ("Quantos bits tem um byte?", ["4", "8", "16", "32"], 1),
    ("Qual é o símbolo químico do ouro?", ["Ag", "Au", "Or", "Go"], 1),
    ("Qual país tem o formato parecido com uma bota?", ["Grécia", "Portugal", "Itália", "Chile"], 2),
    ("Quantos dias tem um ano bissexto?", ["364", "365", "366", "367"], 2),
    ("Em que estado nasceu o Pelé?", ["São Paulo", "Rio de Janeiro", "Minas Gerais", "Bahia"], 2),
    ("Qual órgão bombeia o sangue pelo corpo?", ["Pulmão", "Fígado", "Coração", "Rim"], 2),
    ("Qual é a unidade de medida da corrente elétrica?", ["Volt", "Watt", "Ohm", "Ampere"], 3),
    ("Qual é a raiz quadrada de 144?", ["11", "12", "13", "14"], 1),
    ("Qual é a montanha mais alta do mundo?", ["K2", "Aconcágua", "Everest", "Kilimanjaro"], 2),
    ("Em que cidade fica o Cristo Redentor?", ["São Paulo", "Rio de Janeiro", "Salvador", "Belo Horizonte"], 1),
    ("Qual bioma predomina no sertão nordestino?", ["Cerrado", "Pampa", "Caatinga", "Pantanal"], 2),
    ("Que vitamina o corpo produz com a luz do sol?", ["Vitamina A", "Vitamina C", "Vitamina D", "Vitamina K"], 2),
    ("Qual linguagem de programação tem o nome de uma cobra?", ["Java", "Python", "Ruby", "Rust"], 1),
]


def quiz() -> None:
    perguntas = random.sample(PERGUNTAS_QUIZ, 10)
    acertos = 0
    for n, (pergunta, opcoes, certa) in enumerate(perguntas, 1):
        limpar()
        titulo(f"🧠 Quiz · pergunta {n} de 10 · acertos: {acertos}")
        print(f"\n  {NEG}{pergunta}{RST}\n")
        ordem = random.sample(range(4), 4)
        i = escolher("Sua resposta", [opcoes[k] for k in ordem])
        if i is None:
            return
        if ordem[i] == certa:
            acertos += 1
            ok("Certa! ✅")
        else:
            erro(f"Errou. A resposta é: {opcoes[certa]}")
        time.sleep(1.2)
    antigo = _recorde("quiz")
    _recorde("quiz", acertos)
    limpar()
    titulo("🧠 Resultado")
    print(f"\n  Você acertou {NEG}{acertos} de 10{RST}." + (" 🏆 Novo recorde!" if acertos > antigo else ""))


@submenu
def menu_jogos():
    menu("🎮 Jogos", [
        ("2048 (setas)", jogo_2048),
        ("Campo minado", campo_minado),
        ("Sudoku (gera um novo a cada partida)", sudoku),
        ("Tetris", tetris),
        ("Snake, a cobrinha (setas ou WASD)", snake),
        ("Forca", forca),
        ("Jogo da velha contra o celular", jogo_da_velha),
        ("Adivinhe o número", adivinhacao),
        ("Quiz de conhecimentos gerais", quiz),
        ("Ver recordes", lambda: mostrar_dados(ler_json(RECORDES_FILE, {}) or {"recordes": "nenhum ainda"})),
    ])


# ── Aprender programação ─────────────────────────────────────────────

# (id, título, explicação, enunciado, saída esperada, dica, solução)
LICOES = {
    "Python": [
        ("py1", "Olá, mundo", "O print() mostra um texto na tela. O texto fica entre aspas:\n\n  print(\"Oi!\")",
         "Mostre na tela: Olá, Termux!", "Olá, Termux!", "Use print(\"...\")", 'print("Olá, Termux!")'),
        ("py2", "Variáveis e contas", "Variáveis guardam valores. As contas usam + - * / e ** (potência):\n\n"
         "  preco = 10\n  quantidade = 3\n  print(preco * quantidade)",
         "Crie a = 7 e b = 5 e mostre a multiplicação dos dois.", "35", "a * b", "a = 7\nb = 5\nprint(a * b)"),
        ("py3", "Textos e f-strings", "Um f-string junta texto e variáveis: coloque f antes das aspas e a variável "
         "entre chaves:\n\n  nome = \"Bia\"\n  print(f\"Oi, {nome}!\")",
         "Com nome = \"Ana\", mostre: Oi, Ana!", "Oi, Ana!", "print(f\"Oi, {nome}!\")",
         'nome = "Ana"\nprint(f"Oi, {nome}!")'),
        ("py4", "Decisões com if", "O if roda um bloco só se a condição for verdadeira. O bloco é indentado "
         "(4 espaços):\n\n  nota = 8\n  if nota >= 7:\n      print(\"aprovado\")\n  else:\n      print(\"recuperação\")",
         "Com idade = 20, mostre \"maior\" se idade >= 18, senão \"menor\".", "maior",
         "if idade >= 18: ... else: ...",
         'idade = 20\nif idade >= 18:\n    print("maior")\nelse:\n    print("menor")'),
        ("py5", "Listas", "Uma lista guarda vários valores entre colchetes. len() diz quantos são:\n\n"
         "  cores = [\"azul\", \"verde\"]\n  print(len(cores))",
         "Crie frutas = [\"maçã\", \"banana\", \"uva\"] e mostre quantos itens ela tem.", "3", "print(len(frutas))",
         'frutas = ["maçã", "banana", "uva"]\nprint(len(frutas))'),
        ("py6", "Repetição com for", "O for repete para cada item. range(1, 4) gera 1, 2 e 3:\n\n"
         "  for n in range(1, 4):\n      print(n)",
         "Mostre os números de 1 a 5, um por linha.", "1\n2\n3\n4\n5", "range(1, 6)",
         "for n in range(1, 6):\n    print(n)"),
        ("py7", "Funções", "Funções guardam um pedaço de código com nome. return devolve o resultado:\n\n"
         "  def dobro(x):\n      return x * 2\n  print(dobro(4))",
         "Crie a função quadrado(x) e mostre quadrado(9).", "81", "return x * x",
         "def quadrado(x):\n    return x * x\nprint(quadrado(9))"),
        ("py8", "Dicionários", "Dicionários guardam pares chave: valor:\n\n"
         "  idades = {\"Ana\": 30, \"Rui\": 25}\n  print(idades[\"Rui\"])",
         "Crie precos = {\"pão\": 1.5, \"leite\": 4.0} e mostre o preço do leite.", "4.0", 'precos["leite"]',
         'precos = {"pão": 1.5, "leite": 4.0}\nprint(precos["leite"])'),
        ("py9", "Repetição com while", "O while repete enquanto a condição for verdadeira:\n\n"
         "  n = 3\n  while n > 0:\n      print(n)\n      n = n - 1",
         "Some os números de 1 a 100 com while e mostre o total.", "5050",
         "total = 0, n = 1; enquanto n <= 100: total += n; n += 1",
         "total = 0\nn = 1\nwhile n <= 100:\n    total += n\n    n += 1\nprint(total)"),
    ],
    "Bash": [
        ("sh1", "echo", "No terminal, echo mostra um texto:\n\n  echo \"Bom dia\"",
         "Mostre: Olá do Bash", "Olá do Bash", "echo \"...\"", 'echo "Olá do Bash"'),
        ("sh2", "Variáveis", "Crie com nome=valor (sem espaços!) e use com $nome:\n\n  cidade=\"Recife\"\n"
         "  echo \"Moro em $cidade\"", "Com nome=\"Termux\", mostre: Oi, Termux", "Oi, Termux",
         "echo \"Oi, $nome\"", 'nome="Termux"\necho "Oi, $nome"'),
        ("sh3", "Contas", "Contas inteiras ficam dentro de $(( )):\n\n  echo $(( 10 + 5 ))",
         "Mostre o resultado de 6 vezes 7.", "42", "echo $(( 6 * 7 ))", "echo $(( 6 * 7 ))"),
        ("sh4", "Repetição com for", "O for percorre uma lista de palavras:\n\n  for fruta in maçã uva; do\n"
         "    echo $fruta\n  done", "Mostre 1, 2 e 3, um por linha, usando for.", "1\n2\n3",
         "for i in 1 2 3; do echo $i; done", "for i in 1 2 3; do\n  echo $i\ndone"),
        ("sh5", "Decisões com if", "Comparações de números: -gt (maior), -lt (menor), -eq (igual):\n\n"
         "  n=3\n  if [ $n -lt 5 ]; then\n    echo pequeno\n  fi",
         "Com num=10, mostre \"grande\" se num for maior que 5.", "grande", "[ $num -gt 5 ]",
         "num=10\nif [ $num -gt 5 ]; then\n  echo grande\nfi"),
        ("sh6", "Pipes", "O | manda a saída de um comando para outro. sort ordena linhas:\n\n"
         "  printf \"b\\na\\n\" | sort", "Ordene banana, abacaxi e cereja (uma por linha) com sort.",
         "abacaxi\nbanana\ncereja", "printf \"banana\\nabacaxi\\ncereja\\n\" | sort",
         'printf "banana\\nabacaxi\\ncereja\\n" | sort'),
        ("sh7", "Funções", "Funções no bash recebem argumentos em $1, $2...:\n\n  saudar() {\n"
         "    echo \"Olá, $1\"\n  }\n  saudar Rita", "Crie a função ola e chame com: ola Mundo",
         "Olá, Mundo", "ola() { echo \"Olá, $1\"; }", 'ola() {\n  echo "Olá, $1"\n}\nola Mundo'),
    ],
    "Git": [
        ("git1", "O que é o Git", "O Git guarda o histórico das mudanças nos seus arquivos: dá para voltar "
         "versões e trabalhar em equipe.", "Para que serve o Git?",
         ["Controlar as versões dos arquivos", "Compilar programas", "Editar imagens", "Navegar na internet"], 0, ""),
        ("git2", "Começar um repositório", "Numa pasta nova, git init cria o repositório.",
         "Qual comando começa um repositório na pasta atual?",
         ["git start", "git init", "git new", "git create"], 1, ""),
        ("git3", "Ver o que mudou", "git status mostra os arquivos novos, alterados e os preparados para o commit.",
         "Qual comando mostra o que mudou?", ["git log", "git diff --all", "git status", "git show"], 2, ""),
        ("git4", "Preparar as mudanças", "git add escolhe o que vai no próximo commit. git add . pega tudo.",
         "Como preparar todos os arquivos para o commit?", ["git add .", "git commit", "git push", "git save"], 0,
         ""),
        ("git5", "Gravar um commit", "O commit é uma 'foto' das mudanças preparadas, com uma mensagem.",
         "Qual comando grava as mudanças com uma mensagem?",
         ["git save \"msg\"", "git commit -m \"msg\"", "git push -m \"msg\"", "git add -m \"msg\""], 1, ""),
        ("git6", "Enviar para o GitHub", "git push manda os seus commits para o repositório remoto.",
         "Qual comando envia os commits para o GitHub?", ["git pull", "git fetch", "git push", "git send"], 2, ""),
        ("git7", "Trazer as novidades", "git pull baixa os commits novos do remoto e junta com os seus.",
         "Qual comando baixa e junta as novidades do remoto?", ["git pull", "git push", "git clone", "git init"], 0,
         ""),
        ("git8", "Branches", "Um branch é uma linha de trabalho separada. git switch -c nome cria e muda para ele.",
         "Como criar um branch 'teste' e ir para ele?",
         ["git branch teste --go", "git switch -c teste", "git new teste", "git commit -b teste"], 1, ""),
    ],
}


def _normalizar_saida(texto: str) -> str:
    return "\n".join(linha.rstrip() for linha in texto.strip().splitlines())


def executar_exercicio(curso: str, codigo: str) -> tuple:
    """(saída, erro) rodando o código do aluno num processo separado com tempo limite."""
    pasta = DATA_DIR / "tmp" / "aprender"
    pasta.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-c", codigo] if curso == "Python" else ["bash" if tem("bash") else "sh", "-c", codigo]
    proc = rodar(cmd, capturar=True, timeout=10, cwd=pasta, mostrar=False)
    if proc.returncode == 124 and proc.stderr == "tempo esgotado":
        return "", "O código demorou demais (laço infinito?)."
    return proc.stdout or "", (proc.stderr or "").strip()


@submenu
def menu_aprender():
    def progresso() -> set:
        return set(ler_json(APRENDER_FILE, {}).get("feitas", []))

    def marcar(ident: str):
        feitas = progresso() | {ident}
        gravar_json(APRENDER_FILE, {"feitas": sorted(feitas)})

    def licao(curso: str, dados: tuple) -> bool:
        ident, nome, explicacao, enunciado = dados[:4]
        limpar()
        titulo(f"{curso}: {nome}")
        print(f"\n{explicacao}\n")
        print(f"{NEG}{AMAR}Exercício:{RST} {enunciado}\n")
        if curso == "Git":
            opcoes, certa = dados[4], dados[5]
            i = escolher("Resposta", opcoes)
            if i == certa:
                ok("Certo! ✅")
                marcar(ident)
                return True
            if i is not None:
                erro(f"Não é essa. Resposta: {opcoes[certa]}")
            return False
        esperado, dica, solucao = dados[4], dados[5], dados[6]
        tentativas = 0
        while True:
            codigo = ler_linhas("Digite o código")
            if not codigo.strip():
                return False
            saida_aluno, falha = executar_exercicio(curso, codigo)
            if saida_aluno:
                print(f"{DIM}── saída ──{RST}\n{saida_aluno.rstrip()}")
            if falha:
                print(f"{VERM}{falha[-600:]}{RST}")
            if _normalizar_saida(saida_aluno) == _normalizar_saida(esperado):
                ok("Perfeito! ✅ Lição concluída.")
                marcar(ident)
                return True
            tentativas += 1
            erro("Ainda não. A saída esperada é:\n" + esperado)
            if tentativas >= 2:
                k = escolher("Quer ajuda?", ["Ver a dica", "Ver a solução", "Tentar de novo", "Sair da lição"])
                if k == 0:
                    info(f"Dica: {dica}")
                elif k == 1:
                    print(f"\n{VERD}{solucao}{RST}\n")
                elif k in (3, None):
                    return False

    def curso(nome: str):
        while True:
            feitas = progresso()
            licoes = LICOES[nome]
            rotulos = [f"{'✅' if l[0] in feitas else '⬜'} {k}. {l[1]}" for k, l in enumerate(licoes, 1)]
            i = escolher(f"{nome}: {sum(l[0] in feitas for l in licoes)} de {len(licoes)} concluídas", rotulos)
            if i is None:
                return
            if licao(nome, licoes[i]):
                pausar()

    def playground():
        i = escolher("Qual?", ["Python (digite exit() para sair)", "Bash (digite exit para sair)"])
        if i == 0:
            rodar([sys.executable], mostrar=False)
        elif i == 1:
            rodar(["bash" if tem("bash") else "sh"], mostrar=False)

    def total(nome: str) -> str:
        feitas = progresso()
        return f"{sum(l[0] in feitas for l in LICOES[nome])}/{len(LICOES[nome])}"

    menu("🎓 Aprender programação", [
        (lambda: f"🐍 Python ({total('Python')})", lambda: curso("Python")),
        (lambda: f"🐚 Bash, o terminal ({total('Bash')})", lambda: curso("Bash")),
        (lambda: f"🌿 Git ({total('Git')})", lambda: curso("Git")),
        ("👾 Interpretador BASIC retrô (digite DEMO e RUN)", basic_repl),
        ("🕹️ Criar meu próprio jogo (gera um template em Python)", criar_jogo),
        ("🧪 Experimentar à vontade (Python ou Bash)", playground),
        ("Zerar o progresso", lambda: confirmar("Zerar todas as lições?", False) and gravar_json(APRENDER_FILE, {})),
    ])


# ── Leitor de livros ─────────────────────────────────────────────────

def ler_epub(caminho: Path) -> tuple:
    """(título, [capítulos em texto]) de um EPUB."""
    try:
        with zipfile.ZipFile(caminho) as z:
            container = ET.fromstring(z.read("META-INF/container.xml"))
            opf_caminho = next(el.get("full-path") for el in container.iter() if el.tag.endswith("rootfile"))
            opf = ET.fromstring(z.read(opf_caminho))
            base = posixpath.dirname(opf_caminho)
            manifesto = {el.get("id"): el.get("href") for el in opf.iter() if el.tag.split("}")[-1] == "item"}
            espinha = [el.get("idref") for el in opf.iter() if el.tag.split("}")[-1] == "itemref"]
            titulo_l = next((el.text for el in opf.iter() if el.tag.split("}")[-1] == "title" and el.text),
                            caminho.stem)
            capitulos = []
            for ref in espinha:
                href = manifesto.get(ref)
                if not href:
                    continue
                interno = posixpath.normpath(posixpath.join(base, urllib.parse.unquote(href)))
                with contextlib.suppress(KeyError):
                    texto = html_para_texto(z.read(interno).decode("utf-8", errors="replace"))
                    if texto.strip():
                        capitulos.append(texto)
    except (zipfile.BadZipFile, KeyError, StopIteration, ET.ParseError) as e:
        raise ToonsError(f"EPUB inválido: {e}") from None
    return titulo_l.strip(), capitulos


def quebrar_texto(texto: str, largura: int) -> list:
    """Linhas para mostrar: cada parágrafo quebrado na largura, com uma linha em branco entre eles."""
    linhas = []
    for paragrafo in re.split(r"\n\s*\n", texto.replace("\r", "")):
        paragrafo = " ".join(paragrafo.split())
        if paragrafo:
            linhas += textwrap.wrap(paragrafo, largura) or [""]
            linhas.append("")
    return linhas or ["(vazio)"]


def ler_texto(titulo_l: str, texto: str, chave: str | None = None) -> None:
    """Leitor de tela cheia: páginas com as setas, ir para %, ouvir em voz alta; lembra onde parou (`chave`)."""
    salvos = ler_json(LEITURA_FILE, {}) if chave else {}
    fracao = float(salvos.get(chave, {}).get("fracao", 0)) if chave else 0.0
    with TelaCheia() as tela:
        largura_atual, linhas, topo = None, [], 0
        while True:
            colunas, altura = shutil.get_terminal_size((60, 24))
            largura = max(20, min(colunas - 2, 90))
            altura_texto = max(3, altura - 3)
            if largura != largura_atual:
                linhas, largura_atual = quebrar_texto(texto, largura), largura
                topo = int(fracao * len(linhas))
            topo = max(0, min(topo, max(0, len(linhas) - altura_texto)))
            fracao = topo / max(1, len(linhas))
            pct = 100 if topo + altura_texto >= len(linhas) else int(fracao * 100)
            desenhar([f" {NEG}{titulo_l[:colunas - 8]}{RST}"] + [" " + l for l in linhas[topo:topo + altura_texto]]
                     + [""] * (altura_texto - len(linhas[topo:topo + altura_texto]))
                     + [f" {DIM}{pct}% · ←→ página · ↑↓ linha · g ir para % · f ouvir · Esc sai{RST}"])
            tecla = ler_tecla()
            if tecla in ("esc", "q"):
                break
            if tecla in ("dir", " ", "pgdn", "enter", "l"):
                topo += altura_texto - 1
            elif tecla in ("esq", "pgup", "backspace", "h"):
                topo -= altura_texto - 1
            elif tecla in ("baixo", "j"):
                topo += 1
            elif tecla in ("cima", "k"):
                topo -= 1
            elif tecla == "home":
                topo = 0
            elif tecla == "end":
                topo = len(linhas)
            elif tecla == "g":
                with tela.normal():
                    topo = int(perguntar_int("Ir para (%)", pct, 0, 100) / 100 * len(linhas))
            elif tecla == "f":
                while topo < len(linhas):
                    pagina = " ".join(linhas[topo:topo + altura_texto]).strip()
                    desenhar([f" {NEG}{titulo_l[:colunas - 8]}{RST}"] + [" " + l for l in
                                                                       linhas[topo:topo + altura_texto]]
                             + [f" {VERD}🔊 lendo... (qualquer tecla para parar ao fim da página){RST}"])
                    try:
                        if pagina:
                            falar(pagina)
                    except ToonsError as e:
                        desenhar([str(e), "Aperte uma tecla"])
                        ler_tecla()
                        break
                    if tecla_ou_nada(0.05) is not None:
                        break
                    topo += altura_texto - 1
    if chave:
        salvos = ler_json(LEITURA_FILE, {})
        salvos[chave] = {"titulo": titulo_l, "fracao": round(fracao, 4), "quando": datetime.now().isoformat()}
        gravar_json(LEITURA_FILE, salvos)


def abrir_livro(caminho: Path) -> None:
    sufixo = caminho.suffix.lower()
    if sufixo == ".epub":
        titulo_l, capitulos = ler_epub(caminho)
        texto = "\n\n".join(capitulos)
    elif sufixo == ".pdf":
        if not garantir_cmd("pdftotext", "poppler"):
            return
        info("Extraindo o texto do PDF...")
        texto = rodar(["pdftotext", str(caminho), "-"], capturar=True, timeout=600, mostrar=False).stdout or ""
        texto = re.sub(r"(?<![.!?:])\n(?=\S)", " ", texto)  # junta as linhas quebradas no meio da frase
        titulo_l = caminho.stem
    else:
        texto, titulo_l = texto_de_arquivo(caminho), caminho.stem
    if not texto.strip():
        raise ToonsError("Não achei texto nesse arquivo (PDF escaneado? use o OCR).")
    ler_texto(titulo_l, texto, chave=str(caminho.resolve()))


@submenu
def menu_livros():
    def abrir():
        arq = escolher_arquivo("Qual livro?", (".epub", ".pdf", ".txt", ".md", ".html", ".htm"))
        if arq:
            abrir_livro(arq)

    def continuar():
        salvos = ler_json(LEITURA_FILE, {})
        livros = sorted(((k, v) for k, v in salvos.items() if Path(k).exists()), key=lambda kv: kv[1]["quando"],
                        reverse=True)
        if not livros:
            info("Nenhum livro aberto ainda.")
            return
        i = escolher("Continuar qual?", [f"{v['titulo'][:50]}  {DIM}{v['fracao']:.0%} · {v['quando'][:10]}{RST}"
                                         for _, v in livros])
        if i is not None:
            abrir_livro(Path(livros[i][0]))

    def esquecer():
        salvos = ler_json(LEITURA_FILE, {})
        if not salvos:
            info("A lista está vazia.")
            return
        chaves = list(salvos)
        marcados = escolher_varios("Tirar quais da lista?", [salvos[k]["titulo"] for k in chaves])
        for i in marcados:
            salvos.pop(chaves[i], None)
        gravar_json(LEITURA_FILE, salvos)

    menu("📖 Leitor de livros", [
        ("Continuar lendo", continuar),
        ("Abrir um livro (EPUB, PDF, TXT)", abrir),
        ("Tirar livros da lista", esquecer),
    ], cabecalho=lambda: print(f"{DIM}No livro: ←→ vira a página · g vai para % · f lê em voz alta · "
                               f"ele lembra onde você parou.{RST}"))


# ── Rádio e podcasts ─────────────────────────────────────────────────

RADIO_SERVIDORES = ["https://de1.api.radio-browser.info", "https://nl1.api.radio-browser.info",
                    "https://at1.api.radio-browser.info"]


def buscar_radios(**filtros) -> list:
    """Estações do radio-browser.info (gratuito, sem chave)."""
    params = {"limit": 60, "order": "clickcount", "reverse": "true", "hidebroken": "true", **filtros}
    ultimo_erro = None
    for servidor in RADIO_SERVIDORES:
        try:
            return pedir_json(url_com(f"{servidor}/json/stations/search", **params), timeout=20) or []
        except ToonsError as e:
            ultimo_erro = e
    raise ultimo_erro or ToonsError("Rádios indisponíveis agora.")


@submenu
def menu_radio():
    c = cfg()

    def tocar_radio(r: dict):
        url = r.get("url_resolved") or r.get("url")
        print(f"\n{NEG}📻 {r.get('name', '').strip()}{RST} {DIM}{r.get('codec', '')} {r.get('bitrate', '')} kbps · "
              f"{r.get('tags', '')[:60]}{RST}")
        if r.get("stationuuid"):
            with contextlib.suppress(ToonsError):
                pedir_bytes(f"{RADIO_SERVIDORES[0]}/json/url/{r['stationuuid']}", timeout=5)  # conta o clique
        favoritas = c.setdefault("radios_favoritas", [])
        if not any(f.get("url") == url for f in favoritas) and confirmar("Guardar nas favoritas?", False):
            favoritas.append({"name": r.get("name", "").strip(), "url_resolved": url, "codec": r.get("codec", ""),
                              "bitrate": r.get("bitrate", ""), "tags": r.get("tags", "")})
            salvar_cfg()
        tocar_mpv([url])

    def lista(radios: list):
        if not radios:
            info("Nenhuma rádio encontrada.")
            return
        i = escolher("Qual rádio?", [f"{r.get('name', '?').strip()[:45]}  {DIM}{r.get('state') or r.get('country', '')}"
                                     f" · {r.get('codec', '')} {r.get('bitrate', '')}{RST}" for r in radios])
        if i is not None:
            tocar_radio(radios[i])

    def generos():
        nomes = [("Sertanejo", "sertanejo"), ("Pop", "pop"), ("Rock", "rock"), ("MPB", "mpb"), ("Samba e pagode", "samba"),
                 ("Gospel", "gospel"), ("Notícias", "news"), ("Funk", "funk"), ("Forró", "forro"),
                 ("Clássica", "classical"), ("Jazz", "jazz"), ("Eletrônica", "electronic"), ("Lo-fi", "lofi")]
        i = escolher("Gênero", [n for n, _ in nomes])
        if i is not None:
            lista(buscar_radios(tag=nomes[i][1], **({} if nomes[i][1] in ("classical", "jazz", "lofi", "electronic")
                                                    else {"countrycode": "BR"})))

    def favoritas():
        favs = c.get("radios_favoritas", [])
        if not favs:
            info("Nenhuma favorita ainda (ela é oferecida quando você toca uma rádio).")
            return
        i = escolher("Favoritas", [f["name"] for f in favs] + ["Remover uma favorita..."])
        if i is None:
            return
        if i < len(favs):
            tocar_radio(favs[i])
        else:
            k = escolher("Remover qual?", [f["name"] for f in favs])
            if k is not None:
                favs.pop(k)
                salvar_cfg()

    menu("📻 Rádio online", [
        ("Mais ouvidas do Brasil", lambda: lista(buscar_radios(countrycode="BR"))),
        ("Buscar pelo nome (ex.: CBN, Jovem Pan)", lambda: lista(buscar_radios(name=perguntar("Nome da rádio")))),
        ("Por gênero", generos),
        ("Rádios de uma cidade/estado", lambda: lista(buscar_radios(countrycode="BR",
                                                                     state=perguntar("Estado (ex.: Bahia)")))),
        ("Favoritas", favoritas),
    ])


@submenu
def menu_podcasts():
    c = cfg()
    c.setdefault("podcasts", [])

    def episodios(pod: dict):
        info("Carregando episódios...")
        eps = [e for e in baixar_feed(pod["feed"]) if e["audio"]][:40]
        if not eps:
            info("Nenhum episódio com áudio nesse feed.")
            return
        while True:
            i = escolher(pod["nome"], [f"{e['titulo'][:70]}  {DIM}{_quando_txt(e['data'])[:5]}{RST}" for e in eps])
            if i is None:
                return
            ep = eps[i]
            j = escolher(ep["titulo"][:60], ["Ouvir agora", "Baixar para ouvir offline", "Ver a descrição"])
            if j == 0:
                tocar_mpv([ep["audio"]])
            elif j == 1:
                nome = _slug(ep["titulo"]) + (Path(urllib.parse.urlsplit(ep["audio"]).path).suffix or ".mp3")
                destino = pasta_saida("Podcasts", _slug(pod["nome"])) / nome
                baixar_arquivo(ep["audio"], destino)
                ok(f"Salvo: {destino}")
            elif j == 2:
                print(ep["resumo"][:2000] or "(sem descrição)")
                pausar()

    def buscar():
        termo = perguntar("Buscar podcast (nome ou assunto)")
        if not termo:
            return
        dados = pedir_json(url_com("https://itunes.apple.com/search", media="podcast", country="BR", term=termo,
                                   limit=25))
        resultados = [r for r in dados.get("results", []) if r.get("feedUrl")]
        if not resultados:
            info("Nada encontrado.")
            return
        i = escolher("Qual?", [f"{r['collectionName'][:50]}  {DIM}{r.get('artistName', '')[:30]}{RST}"
                               for r in resultados])
        if i is None:
            return
        pod = {"nome": resultados[i]["collectionName"], "feed": resultados[i]["feedUrl"]}
        if not any(p["feed"] == pod["feed"] for p in c["podcasts"]) and confirmar("Seguir este podcast?", True):
            c["podcasts"].append(pod)
            salvar_cfg()
        episodios(pod)

    def meus():
        if not c["podcasts"]:
            info("Você não segue nenhum podcast ainda.")
            return
        i = escolher("Meus podcasts", [p["nome"] for p in c["podcasts"]] + ["Deixar de seguir..."])
        if i is None:
            return
        if i < len(c["podcasts"]):
            episodios(c["podcasts"][i])
        else:
            k = escolher("Deixar de seguir qual?", [p["nome"] for p in c["podcasts"]])
            if k is not None:
                c["podcasts"].pop(k)
                salvar_cfg()

    menu("🎙️ Podcasts", [
        (lambda: f"Meus podcasts ({len(c['podcasts'])})", meus),
        ("Buscar podcast", buscar),
        ("Seguir pelo link do feed RSS", lambda: (c["podcasts"].append({"nome": perguntar("Nome"),
                                                                        "feed": perguntar("Link do feed")}),
                                                  salvar_cfg())),
    ])


# ── Arte ASCII, banner e tema do Termux ──────────────────────────────

ARCO_IRIS = [196, 202, 208, 214, 220, 226, 190, 154, 118, 82, 46, 47, 48, 49, 50, 51, 45, 39, 33, 27, 21, 57, 93,
             129, 165, 201, 200, 199, 198, 197]

TEMAS_TERMUX = {
    "Dracula": ("#282a36", "#f8f8f2", ["#21222c", "#ff5555", "#50fa7b", "#f1fa8c", "#bd93f9", "#ff79c6", "#8be9fd",
                                       "#f8f8f2", "#6272a4", "#ff6e6e", "#69ff94", "#ffffa5", "#d6acff", "#ff92df",
                                       "#a4ffff", "#ffffff"]),
    "Gruvbox": ("#282828", "#ebdbb2", ["#282828", "#cc241d", "#98971a", "#d79921", "#458588", "#b16286", "#689d6a",
                                       "#a89984", "#928374", "#fb4934", "#b8bb26", "#fabd2f", "#83a598", "#d3869b",
                                       "#8ec07c", "#ebdbb2"]),
    "Nord": ("#2e3440", "#d8dee9", ["#3b4252", "#bf616a", "#a3be8c", "#ebcb8b", "#81a1c1", "#b48ead", "#88c0d0",
                                    "#e5e9f0", "#4c566a", "#bf616a", "#a3be8c", "#ebcb8b", "#81a1c1", "#b48ead",
                                    "#8fbcbb", "#eceff4"]),
    "Solarized escuro": ("#002b36", "#839496", ["#073642", "#dc322f", "#859900", "#b58900", "#268bd2", "#d33682",
                                                "#2aa198", "#eee8d5", "#002b36", "#cb4b16", "#586e75", "#657b83",
                                                "#839496", "#6c71c4", "#93a1a1", "#fdf6e3"]),
    "Tokyo Night": ("#1a1b26", "#c0caf5", ["#15161e", "#f7768e", "#9ece6a", "#e0af68", "#7aa2f7", "#bb9af7",
                                           "#7dcfff", "#a9b1d6", "#414868", "#f7768e", "#9ece6a", "#e0af68",
                                           "#7aa2f7", "#bb9af7", "#7dcfff", "#c0caf5"]),
    "Monokai": ("#272822", "#f8f8f2", ["#272822", "#f92672", "#a6e22e", "#f4bf75", "#66d9ef", "#ae81ff", "#a1efe4",
                                       "#f8f8f2", "#75715e", "#f92672", "#a6e22e", "#f4bf75", "#66d9ef", "#ae81ff",
                                       "#a1efe4", "#f9f8f5"]),
}


def arco_iris(texto: str) -> str:
    if not _COR:
        return texto
    saida = []
    for linha in texto.splitlines():
        saida.append("".join(f"\033[38;5;{ARCO_IRIS[(i // 2) % len(ARCO_IRIS)]}m{ch}" if ch.strip() else ch
                             for i, ch in enumerate(linha)) + RST)
    return "\n".join(saida)


def fontes_figlet() -> list:
    pasta = saida(["figlet", "-I2"])
    return sorted(p.stem for p in Path(pasta).glob("*.flf")) if pasta and Path(pasta).is_dir() else ["standard"]


def figlet(texto: str, fonte: str = "standard", largura: int | None = None) -> str:
    return saida(["figlet", "-f", fonte, "-w", str(largura or largura_tela()), texto]) or texto


def imagem_em_blocos(caminho: Path, largura: int) -> list:
    """Imagem colorida no terminal: cada caractere '▀' mostra 2 pixels (cores de 24 bits)."""
    from PIL import Image, ImageOps
    with Image.open(caminho) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        altura = max(2, round(largura * img.height / img.width / 2) * 2)
        img = img.resize((largura, altura))
        px = img.load()
    linhas = []
    for y in range(0, altura, 2):
        linha = []
        for x in range(largura):
            (r1, g1, b1), (r2, g2, b2) = px[x, y], px[x, y + 1]
            linha.append(f"\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m▀")
        linhas.append("".join(linha) + RST)
    return linhas


# ── Fonte do terminal ────────────────────────────────────────────────
# O Termux usa ~/.termux/font.ttf (TTF ou OTF, sempre com esse nome) e recarrega com termux-reload-settings.
# A fonte vem do celular: .ttf/.otf soltos (Download, Documents, Fonts...) ou dentro de um .zip baixado (Google
# Fonts e Nerd Fonts vêm assim), além das monoespaçadas do próprio Android. No terminal ela precisa ser
# monoespaçada (todas as letras da mesma largura), senão colunas e menus ficam tortos.

FONTE_TERMUX = HOME / ".termux" / "font.ttf"
FONTE_ANTES = FONTE_TERMUX.with_name("font.ttf.antes-do-toons")
EXT_FONTE = (".ttf", ".otf")


def info_fonte(dados: bytes) -> tuple:
    """(nome, monoespaçada) de uma fonte TTF/OTF, lidos das tabelas name, post e hmtx. (None, None) se não for."""
    try:
        if dados[:4] not in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
            return None, None
        tabelas = {}
        for i in range(struct.unpack(">H", dados[4:6])[0]):
            tag, _, inicio, tamanho = struct.unpack(">4sIII", dados[12 + 16 * i:28 + 16 * i])
            tabelas[tag] = inicio
        nomes = {}
        if b"name" in tabelas:
            t = tabelas[b"name"]
            _, total, textos = struct.unpack(">HHH", dados[t:t + 6])
            for i in range(total):
                plataforma, _, _, id_nome, tamanho, pos = struct.unpack(">6H", dados[t + 6 + 12 * i:t + 18 + 12 * i])
                if id_nome in (1, 4) and (id_nome not in nomes or plataforma == 3):  # 4 = nome completo, 1 = família
                    bruto = dados[t + textos + pos:t + textos + pos + tamanho]
                    nomes[id_nome] = bruto.decode("utf-16-be" if plataforma in (0, 3) else "latin-1", "replace")
        mono = False
        if b"post" in tabelas:  # isFixedPitch: a própria fonte diz que é monoespaçada
            mono = struct.unpack(">I", dados[tabelas[b"post"] + 12:tabelas[b"post"] + 16])[0] != 0
        if not mono and b"hhea" in tabelas and b"hmtx" in tabelas:  # senão: quase todas as larguras iguais
            quantas = struct.unpack(">H", dados[tabelas[b"hhea"] + 34:tabelas[b"hhea"] + 36])[0]
            larguras = [struct.unpack(">H", dados[tabelas[b"hmtx"] + 4 * i:tabelas[b"hmtx"] + 4 * i + 2])[0]
                        for i in range(quantas)]
            larguras = [w for w in larguras if w]
            mono = bool(larguras) and max(map(larguras.count, set(larguras))) >= 0.9 * len(larguras)
        return (nomes.get(4) or nomes.get(1) or "?").strip(), mono
    except (struct.error, IndexError):
        return None, None


def fontes_do_celular() -> list:
    """[(rótulo, arquivo, nome dentro do .zip ou None)]: fontes soltas e em .zip, mais novas primeiro, e as
    monoespaçadas do Android no fim."""
    achados = []
    for arq in listar_arquivos(EXT_FONTE + (".zip",), limite=400):
        if arq.suffix.lower() != ".zip":
            achados.append((f"{arq.name}  {DIM}{arq.parent.name}{RST}", arq, None))
            continue
        with contextlib.suppress(OSError, zipfile.BadZipFile):
            with zipfile.ZipFile(arq) as z:
                achados += [(f"{Path(m).name}  {DIM}em {arq.name}{RST}", arq, m) for m in sorted(z.namelist())
                            if m.lower().endswith(EXT_FONTE) and not m.startswith("__MACOSX")
                            and not Path(m).name.startswith(".")]
    with contextlib.suppress(OSError):
        achados += [(f"{p.name}  {DIM}do Android{RST}", p, None) for p in sorted(Path("/system/fonts").glob("*"))
                    if "mono" in p.name.lower() and p.suffix.lower() in EXT_FONTE]
    return achados


def _recarregar_termux() -> bool:
    if not tem("termux-reload-settings"):
        return False
    rodar(["termux-reload-settings"], capturar=True, timeout=20)
    return True


def _gravar_fonte(dados: bytes | None) -> None:
    """Põe a fonte no Termux (None = volta à padrão) e recarrega."""
    if dados is None:
        FONTE_TERMUX.unlink(missing_ok=True)
    else:
        FONTE_TERMUX.parent.mkdir(parents=True, exist_ok=True)
        FONTE_TERMUX.write_bytes(dados)
    _recarregar_termux()


def trocar_fonte_terminal() -> None:
    fontes = fontes_do_celular()
    if not fontes:
        info("Nenhuma fonte (.ttf, .otf ou .zip com fontes) encontrada no Download, Documents ou Fonts. Baixe uma "
             "monoespaçada (ex.: JetBrains Mono, Fira Code ou uma 'Mono' das Nerd Fonts) e volte aqui.")
    elif len(fontes) > 15:
        filtro = sem_acento(perguntar("Filtrar por nome (ex.: mono, jetbrains; Enter = todas)", "")).lower()
        fontes = [f for f in fontes if filtro in sem_acento(_sem_ansi(f[0])).lower()] or fontes
    i = escolher(f"Qual fonte? ({len(fontes)})", [rotulo for rotulo, _, _ in fontes]
                 + ["Digitar o caminho do arquivo (.ttf, .otf ou .zip)..."])
    if i is None:
        return
    if i < len(fontes):
        _, arquivo, membro = fontes[i]
    else:
        arquivo = Path(os.path.expanduser(perguntar("Caminho da fonte").strip().strip("'\"")))
        if not arquivo.is_file():
            raise ToonsError(f"Arquivo não encontrado: {arquivo}")
        membro = None
        if arquivo.suffix.lower() == ".zip":
            with zipfile.ZipFile(arquivo) as z:
                dentro = [m for m in sorted(z.namelist()) if m.lower().endswith(EXT_FONTE)]
            if not dentro:
                raise ToonsError("Esse .zip não tem nenhuma fonte .ttf ou .otf.")
            j = escolher("Qual fonte do .zip?", [Path(m).name for m in dentro])
            if j is None:
                return
            membro = dentro[j]
    try:
        if membro:
            with zipfile.ZipFile(arquivo) as z:
                dados = z.read(membro)
        else:
            dados = arquivo.read_bytes()
    except (OSError, zipfile.BadZipFile, KeyError) as e:
        raise ToonsError(f"Não consegui ler a fonte: {e}") from None
    nome, mono = info_fonte(dados)
    if nome is None:
        raise ToonsError("Esse arquivo não é uma fonte TTF/OTF que o Termux consiga usar.")
    print(f"  Fonte: {NEG}{nome}{RST} · {'monoespaçada ✔' if mono else f'{AMAR}não é monoespaçada{RST}'}")
    if not mono:
        aviso("No terminal as letras dela ficam desalinhadas (colunas e menus tortos). Prefira uma com 'Mono' no nome.")
        if not confirmar("Usar mesmo assim?", False):
            return
    anterior = FONTE_TERMUX.read_bytes() if FONTE_TERMUX.exists() else None
    if anterior is not None and not FONTE_ANTES.exists():  # guarda a fonte que a pessoa tinha antes do Toons
        FONTE_ANTES.write_bytes(anterior)
    _gravar_fonte(dados)
    if not IS_TERMUX or not tem("termux-reload-settings"):
        ok(f"Fonte salva em {FONTE_TERMUX}: reabra o Termux para ver.")
        return
    manter = False
    try:
        manter = confirmar_no_prazo("A fonte ficou boa? Manter assim?", time.time() + TEMPO_CONFIRMAR)
    finally:
        if manter:
            ok(f"Fonte trocada: {nome}.")
        else:
            _gravar_fonte(anterior)
            info("Voltou à fonte de antes.")


def fonte_original_terminal() -> None:
    if FONTE_ANTES.exists():
        _gravar_fonte(FONTE_ANTES.read_bytes())
        ok("Voltou à fonte que você usava antes do Termux-Toons.")
    else:
        _gravar_fonte(None)
        ok("Voltou à fonte padrão do Termux.")


@submenu
def menu_arte():
    c = cfg()

    def texto_grande():
        if not garantir_cmd("figlet"):
            return
        texto = perguntar("Texto", "Termux")
        fontes = fontes_figlet()
        i = escolher("Fonte", fontes, fontes.index("standard") + 1 if "standard" in fontes else None)
        if i is None:
            return
        arte = figlet(texto, fontes[i])
        colorido = confirmar("Colorir com arco-íris?", True)
        print(arco_iris(arte) if colorido else arte)
        j = escolher("E agora?", ["Copiar", "Salvar em arquivo", "Usar como banner do Termux-Toons", "Nada"])
        if j == 0:
            copiar_texto(arte)
        elif j == 1:
            destino = pasta_saida("Arte") / f"{_slug(texto)}.txt"
            destino.write_text(arte + "\n", "utf-8")
            ok(f"Salvo: {destino}")
        elif j == 2:
            c["banner_texto"], c["banner_fonte"] = texto, fontes[i]
            salvar_cfg()
            ok("Banner trocado (aparece no menu principal).")

    def imagem():
        arq = escolher_arquivo("Qual imagem?", EXT_IMAGEM)
        if not arq:
            return
        largura = min(largura_tela() - 1, 120)
        if tem("chafa"):
            rodar(["chafa", "--size", f"{largura}x{largura}", str(arq)], mostrar=False)
        elif garantir_modulo("PIL", pip_nome="pillow", pkg_nome="python-pillow"):
            print("\n".join(imagem_em_blocos(arq, largura)))
        if confirmar("Diminua a fonte (pinça) para ver mais detalhes. Salvar como arquivo de texto colorido?", False):
            destino = pasta_saida("Arte") / f"{arq.stem}.ans"
            destino.write_text("\n".join(imagem_em_blocos(arq, largura)) + "\n", "utf-8")
            ok(f"Salvo: {destino} (veja com: cat '{destino}')")

    def tema():
        nomes = list(TEMAS_TERMUX) + ["Voltar ao tema padrão do Termux"]
        i = escolher("Tema de cores do Termux", nomes)
        if i is None:
            return
        arq = HOME / ".termux" / "colors.properties"
        arq.parent.mkdir(exist_ok=True)
        if arq.exists() and not (arq.parent / "colors.properties.antes-do-toons").exists():
            shutil.copy2(arq, arq.parent / "colors.properties.antes-do-toons")
        if i == len(TEMAS_TERMUX):
            backup = arq.parent / "colors.properties.antes-do-toons"
            if backup.exists():
                shutil.copy2(backup, arq)
            else:
                arq.unlink(missing_ok=True)
        else:
            fundo, frente, cores = TEMAS_TERMUX[nomes[i]]
            arq.write_text(f"# Tema {nomes[i]} (Termux-Toons)\nbackground={fundo}\nforeground={frente}\n"
                           f"cursor={frente}\n" + "".join(f"color{k}={cor}\n" for k, cor in enumerate(cores)), "utf-8")
        if tem("termux-reload-settings"):
            rodar(["termux-reload-settings"], capturar=True, timeout=20)
        ok("Tema aplicado." if tem("termux-reload-settings") else "Tema salvo: reabra o Termux para ver.")

    def boas_vindas():
        motd = Path(PREFIX or "/usr") / "etc" / "motd"
        backup = motd.with_name("motd.antes-do-toons")
        i = escolher("Mensagem ao abrir o Termux", ["Texto grande com o meu nome", "Uma frase minha",
                                                    "Nenhuma mensagem", "Voltar a original"])
        if i is None:
            return
        if motd.exists() and not backup.exists():
            shutil.copy2(motd, backup)
        if i == 0:
            if not garantir_cmd("figlet"):
                return
            motd.write_text(arco_iris(figlet(perguntar("Nome", getpass.getuser()), "standard", 40)) + "\n", "utf-8")
        elif i == 1:
            motd.write_text(perguntar("Frase") + "\n", "utf-8")
        elif i == 2:
            motd.write_text("", "utf-8")
        elif backup.exists():
            shutil.copy2(backup, motd)
        ok("Pronto: abra uma nova sessão do Termux para ver.")

    menu("🎨 Arte ASCII e visual do Termux", [
        ("Texto em letras grandes (figlet)", texto_grande),
        ("Imagem no terminal (colorida)", imagem),
        ("Tema de cores do Termux (Dracula, Nord...)", tema),
        ("🔤 Fonte do terminal (uma fonte baixada no celular)", trocar_fonte_terminal),
        ("Fonte do terminal: voltar à original", fonte_original_terminal),
        ("Mensagem de boas-vindas do Termux", boas_vindas),
        ("Banner do Termux-Toons: voltar ao original",
         lambda: (c.update(banner_texto=""), salvar_cfg(), ok("Banner original de volta."))),
    ])


# ── Trote / pegadinha (screamer): link que dá um susto em quem abrir ──

TROTE_DIR = DATA_DIR / "trote"  # página gerada + imagem/som copiados

# Rosto padrão (SVG) para quando a pessoa não escolhe uma imagem própria.
_TROTE_ROSTO_SVG = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 800'>
<rect width='600' height='800' fill='#040404'/>
<radialGradient id='pele' cx='50%' cy='38%' r='62%'>
  <stop offset='0%' stop-color='#aab2a6'/><stop offset='62%' stop-color='#3a423a'/>
  <stop offset='100%' stop-color='#050605'/>
</radialGradient>
<ellipse cx='300' cy='380' rx='215' ry='305' fill='url(#pele)'/>
<ellipse cx='210' cy='330' rx='72' ry='98' fill='#000'/>
<ellipse cx='390' cy='330' rx='72' ry='98' fill='#000'/>
<circle cx='210' cy='348' r='15' fill='#8b0000'/>
<circle cx='390' cy='348' r='15' fill='#8b0000'/>
<path d='M300 378 l-24 76 l48 0 Z' fill='#0a0c0a'/>
<path d='M188 556 Q300 516 412 556 Q360 700 300 712 Q240 700 188 556 Z' fill='#060606'/>
<g stroke='#15170f' stroke-width='7'>
  <line x1='232' y1='558' x2='242' y2='648'/><line x1='272' y1='542' x2='277' y2='690'/>
  <line x1='322' y1='542' x2='327' y2='690'/><line x1='366' y1='558' x2='360' y2='648'/>
</g>
<g stroke='#6b0000' stroke-width='3' fill='none' opacity='0.85'>
  <path d='M208 248 l-28 -82 l9 40 l-24 -20'/><path d='M392 248 l34 -72 l-11 36 l27 -16'/>
  <path d='M300 118 l-10 60 l16 -24 l-2 34'/>
</g>
</svg>"""

# Página do trote. __CFG__ vira um objeto JSON com as opções escolhidas no Termux.
_TROTE_HTML = """<!doctype html>
<html lang='pt-br'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no'>
<meta name='theme-color' content='#000000'>
<title>Carregando…</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  html, body { height:100%; background:#0b0e12; color:#e8eef5; overflow:hidden;
    font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif; }
  #gate, #fim { min-height:100%; display:flex; flex-direction:column; justify-content:center;
    align-items:center; text-align:center; padding:28px 20px 160px; gap:14px; }
  #gate h1, #fim h1 { font-size:26px; font-weight:800; }
  #gate p, #fim p { opacity:.78; max-width:420px; line-height:1.5; }
  #fim { position:fixed; inset:0; display:none; padding-bottom:28px; }
  .selo { font-size:52px; }
  .cookie { position:fixed; left:0; right:0; bottom:0; background:#161b22;
    border-top:1px solid #2a323c; padding:16px; display:flex; flex-direction:column;
    gap:10px; align-items:center; }
  .cookie span { font-size:13px; opacity:.82; max-width:520px; line-height:1.45; }
  .cookie .botoes { display:flex; gap:10px; flex-wrap:wrap; justify-content:center; }
  button { font-size:15px; font-weight:700; border:0; border-radius:10px; padding:13px 20px;
    cursor:pointer; }
  .ok { background:#2ea043; color:#fff; }
  .alt { background:transparent; color:#9fb0c3; border:1px solid #2a323c; }
  #espera { position:fixed; inset:0; display:none; flex-direction:column; gap:18px;
    align-items:center; justify-content:center; background:#000; }
  .spin { width:54px; height:54px; border:5px solid #1c2531; border-top-color:#4b9fff;
    border-radius:50%; animation:gira .8s linear infinite; }
  @keyframes gira { to { transform:rotate(360deg); } }
  #cena { position:fixed; inset:0; display:none; background:#000; overflow:hidden; }
  #rosto { position:absolute; inset:0; width:100%; height:100%; object-fit:cover;
    animation:tremer .09s infinite; }
  @keyframes tremer { 0%{transform:translate(0,0) scale(1.04)} 25%{transform:translate(-8px,6px) scale(1.07)}
    50%{transform:translate(7px,-7px) scale(1.05)} 75%{transform:translate(-6px,-6px) scale(1.08)}
    100%{transform:translate(6px,7px) scale(1.04)} }
  #flash { position:fixed; inset:0; opacity:0; pointer-events:none; mix-blend-mode:screen; }
  #msg { position:fixed; inset:0; display:flex; align-items:center; justify-content:center;
    text-align:center; padding:16px; font-size:min(16vw,120px); font-weight:900; overflow-wrap:anywhere;
    color:#fff; text-shadow:0 0 18px #000, 0 0 40px #b10000; letter-spacing:1px;
    pointer-events:none; animation:treme .12s infinite; }
  @keyframes treme { 0%{transform:translate(0,0)} 50%{transform:translate(4px,-4px) skewX(2deg)}
    100%{transform:translate(-4px,4px) skewX(-2deg)} }
  @media (prefers-reduced-motion: reduce) { #rosto, #msg { animation:none; } }
  #bandeja { position:fixed; top:0; left:0; right:0; padding:8px; display:flex;
    flex-direction:column; gap:7px; pointer-events:none; z-index:50; }
  .notif { display:flex; gap:10px; align-items:center; background:rgba(22,27,34,.97);
    border:1px solid #2a323c; border-radius:12px; padding:10px 12px;
    box-shadow:0 6px 18px rgba(0,0,0,.5); animation:entra .18s ease-out; }
  @keyframes entra { from{transform:translateY(-120%); opacity:0} to{transform:none; opacity:1} }
  .nicone { font-size:22px; }
  .ncorpo { flex:1; text-align:left; min-width:0; }
  .ntitulo { font-size:13px; font-weight:800; color:#fff; }
  .ntexto { font-size:13px; color:#cdd7e2; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .nhora { font-size:11px; color:#8a97a6; }
</style>
</head>
<body>
<div id='gate'>
  <div class='selo'>🔒</div>
  <h1>Verificação de segurança</h1>
  <p>Para acessar o conteúdo, confirme que você não é um robô e aceite os cookies deste site.</p>
  <div class='cookie'>
    <span>🍪 Este site usa cookies e recursos do navegador (som, vibração e notificações)
      para melhorar a sua experiência. Ao continuar, você concorda com tudo isso.</span>
    <div class='botoes'>
      <button class='ok' id='aceitar'>Aceitar e continuar</button>
      <button class='alt' id='aceitar2'>Só os necessários</button>
    </div>
  </div>
</div>
<div id='espera'><div class='spin'></div><div>Carregando conteúdo…</div></div>
<div id='cena'>
  <img id='rosto' alt=''>
  <div id='flash'></div>
  <div id='msg'></div>
</div>
<div id='bandeja'></div>
<div id='fim'>
  <div class='selo'>😂</div>
  <h1>Calma, era só um trote!</h1>
  <p>Pode respirar: quem te mandou o link estava só brincando com você.</p>
</div>
<script>
const CFG = __CFG__;
const $ = s => document.querySelector(s);
// Quem ativou "reduzir movimento" no celular não vê pisca-pisca nem tremedeira.
const calmo = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
const timers = [];  // tudo o que repete, para o fim do susto parar de uma vez
function depois(fn, ms){ timers.push(setTimeout(fn, ms)); }
function repetir(fn, ms){ timers.push(setInterval(fn, ms)); }
// Recursos do navegador que podem faltar, dar erro ou devolver uma Promise rejeitada.
function quieto(fn){ try { const p = fn(); if (p && p.catch) p.catch(() => {}); } catch(e){} }

// A imagem e o som já começam a baixar enquanto a pessoa lê o aviso de cookies.
const rosto = $('#rosto');
rosto.addEventListener('error', function padrao(){  // formato que o navegador não abre (HEIC...)
  rosto.removeEventListener('error', padrao); rosto.src = '/' + CFG.rosto; });
rosto.src = '/' + CFG.imagem;
const somBaixado = (CFG.som && CFG.volume > 0)
  ? fetch('/' + CFG.som).then(r => r.ok ? r.arrayBuffer() : null).catch(() => null)
  : Promise.resolve(null);

let actx = null, saida = null, somPronto = Promise.resolve(null), ruido = null, curva = null;
let acabou = false, swReg = null, notifReal = false, ni = 0;

// Tem que rodar dentro do toque no botão: é isso que libera o som (bloqueio de autoplay).
// Tudo passa pelo Web Audio: o volume vale até no iPhone (que ignora o volume de <audio>) e o
// arquivo não precisa de HTTP Range para tocar.
function liberarAudio(){
  if (CFG.volume <= 0) return;
  quieto(() => { if (navigator.audioSession) navigator.audioSession.type = 'playback'; });  // iPhone no silencioso
  try {
    actx = new (window.AudioContext || window.webkitAudioContext)();
    quieto(() => actx.resume());
    const mudo = actx.createBufferSource();  // iOS antigo só libera depois de tocar algo no toque
    mudo.buffer = actx.createBuffer(1, 1, 22050); mudo.connect(actx.destination); mudo.start(0);
    saida = actx.createGain(); saida.gain.value = CFG.volume; saida.connect(actx.destination);
  } catch(e){ actx = null; return; }
  somPronto = somBaixado.then(dados => new Promise(pronto => {
    if (!dados) return pronto(null);
    try {  // com callbacks: também funciona no Safari antigo, que não devolve Promise
      const p = actx.decodeAudioData(dados, pronto, () => pronto(null));
      if (p && p.catch) p.catch(() => pronto(null));
    } catch(e){ pronto(null); }
  }));
}

function umGrito(){
  const t0 = actx.currentTime + 0.02, dur = 1.7, n = Math.floor(actx.sampleRate * dur);
  if (!curva){  // distorção (tanh) e ruído: calculados uma vez só
    curva = new Float32Array(1024);
    for (let i = 0; i < 1024; i++) curva[i] = Math.tanh((i / 512 - 1) * 9);
    ruido = actx.createBuffer(1, n, actx.sampleRate);
    const d = ruido.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
  }
  const env = actx.createGain(), ws = actx.createWaveShaper();
  env.gain.setValueAtTime(0.0001, t0);
  env.gain.exponentialRampToValueAtTime(1, t0 + 0.03);
  env.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
  ws.curve = curva; env.connect(ws); ws.connect(saida);
  const ns = actx.createBufferSource(), bp = actx.createBiquadFilter();
  ns.buffer = ruido; bp.type = 'bandpass'; bp.frequency.value = 1300; bp.Q.value = 0.6;
  ns.connect(bp); bp.connect(env); ns.start(t0); ns.stop(t0 + dur);
  [620, 940, 1500].forEach((f, i) => {
    const o = actx.createOscillator(), lfo = actx.createOscillator(), lg = actx.createGain();
    o.type = 'sawtooth';
    o.frequency.setValueAtTime(f, t0);
    o.frequency.exponentialRampToValueAtTime(f * 2.4, t0 + 0.22);
    o.frequency.exponentialRampToValueAtTime(f * 0.8, t0 + dur);
    lfo.frequency.value = 16 + i * 5; lg.gain.value = f * 0.3;  // o tremido da voz
    lfo.connect(lg); lg.connect(o.frequency); o.connect(env);
    lfo.start(t0); lfo.stop(t0 + dur); o.start(t0); o.stop(t0 + dur);
  });
}

function gritar(){
  if (!actx) return;
  let decidido = false;
  const sintetico = () => { if (decidido || acabou) return; decidido = true; umGrito(); repetir(umGrito, 1700); };
  depois(sintetico, 1500);  // o arquivo não chegou a tempo (túnel lento): grita assim mesmo
  somPronto.then(buf => {
    if (!buf) return sintetico();  // sem arquivo, ou num formato que o navegador não toca
    if (decidido || acabou) return;
    decidido = true;
    const f = actx.createBufferSource(); f.buffer = buf; f.loop = true; f.connect(saida); f.start();
  });
}

function tique(){
  if (!actx) return;
  const t = actx.currentTime, o = actx.createOscillator(), g = actx.createGain();
  o.type = 'square'; o.frequency.value = 880;
  g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.4, t + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, t + 0.2);
  o.connect(g); g.connect(saida); o.start(t); o.stop(t + 0.2);
}

// 2 piscadas por segundo: abaixo do limite de 3 por segundo (WCAG 2.3.1) que pode provocar
// crise em quem tem epilepsia fotossensível.
function piscar(){
  if (!CFG.piscar || calmo) return;
  const f = $('#flash'); let aceso = false; f.style.background = CFG.cor;
  repetir(() => { aceso = !aceso; f.style.opacity = aceso ? '0.85' : '0'; }, 250);
}

const VIBRACAO = [400, 120, 400, 120, 600, 200, 350, 120];
function vibrar(){
  if (!CFG.vibrar || !navigator.vibrate) return;
  navigator.vibrate(VIBRACAO);  // repete só quando o padrão inteiro termina
  repetir(() => navigator.vibrate(VIBRACAO), VIBRACAO.reduce((a, b) => a + b, 0));
}

// Pede a permissão e registra o service worker. Notificação de verdade do Android só sai
// com permissão E em contexto seguro (o link https do túnel; o localhost); no link http da
// rede Wi-Fi o navegador bloqueia e o serviceWorker nem existe, então fica só a reserva.
async function prepararNotificacoes(){
  if (!CFG.notificacoes || !('Notification' in window)) return;
  try { if (Notification.permission === 'default') await Notification.requestPermission(); } catch(e){}
  if (Notification.permission !== 'granted' || !('serviceWorker' in navigator)) return;
  try {
    await navigator.serviceWorker.register('/sw.js');
    swReg = await navigator.serviceWorker.ready;  // precisa estar ativo para o showNotification
    notifReal = !!(swReg && swReg.showNotification);
  } catch(e){ swReg = null; notifReal = false; }
}

function soltarNotificacao(){
  const lista = CFG.notif_textos.length ? CFG.notif_textos : [CFG.mensagem];
  const txt = lista[ni++ % lista.length];
  tique();  // a vibração fica com vibrar(): aqui ela cortaria o padrão (ou tremeria com ela desligada)
  if (notifReal){  // notificação de verdade do Android; renotify: toca/vibra de novo a cada uma
    quieto(() => swReg.showNotification(CFG.titulo, {body: txt, tag: 'trote', renotify: true}));
    return;  // com a de verdade na tela do celular, a barra imitada não entra
  }
  // Reserva (link http:// ou permissão negada): uma barra desenhada dentro do próprio site.
  const el = document.createElement('div'); el.className = 'notif';
  el.innerHTML = "<div class='nicone'>⚠️</div><div class='ncorpo'><div class='ntitulo'></div>" +
    "<div class='ntexto'></div></div><div class='nhora'>agora</div>";
  el.querySelector('.ntitulo').textContent = CFG.titulo;
  el.querySelector('.ntexto').textContent = txt;
  const b = $('#bandeja'); b.appendChild(el);
  while (b.children.length > 8) b.removeChild(b.firstChild);
  setTimeout(() => el.remove(), 6000);
}

function piscarTitulo(){
  const alt = ['⚠ ' + CFG.titulo, '😱😱😱', CFG.titulo, '👁 ' + CFG.titulo + ' 👁']; let k = 0;
  repetir(() => { document.title = alt[k++ % alt.length]; }, 420);
}

function assustar(){
  $('#espera').style.display = 'none';
  $('#cena').style.display = 'block';
  $('#msg').textContent = CFG.mensagem;
  gritar(); piscar(); vibrar(); piscarTitulo();
  if (CFG.notificacoes){ soltarNotificacao(); repetir(soltarNotificacao, 700); }
  if (CFG.duracao > 0) depois(revelar, CFG.duracao * 1000);
}

// Fim do susto: para som, vibração e efeitos e conta que era brincadeira.
function revelar(){
  acabou = true;
  timers.forEach(t => clearTimeout(t));  // clearTimeout também cancela os setInterval
  if (navigator.vibrate) navigator.vibrate(0);
  if (actx) quieto(() => actx.close());
  if (swReg) quieto(() => swReg.getNotifications({tag: 'trote'}).then(ns => ns.forEach(n => n.close())));
  if (document.fullscreenElement || document.webkitFullscreenElement)
    quieto(() => (document.exitFullscreen || document.webkitExitFullscreen).call(document));
  $('#cena').style.display = 'none';
  $('#bandeja').textContent = '';
  document.title = '😂 Era só um trote!';
  $('#fim').style.display = 'flex';
}

async function comecar(){
  $('#gate').remove();
  // Tela cheia e áudio precisam sair aqui dentro do toque, antes de qualquer await.
  const raiz = document.documentElement, cheia = raiz.requestFullscreen || raiz.webkitRequestFullscreen;
  if (cheia) quieto(() => cheia.call(raiz));
  liberarAudio();
  if (CFG.atraso > 0) $('#espera').style.display = 'flex';
  await prepararNotificacoes();  // espera a pessoa responder "Permitir?" antes do susto
  if (CFG.atraso > 0) depois(assustar, CFG.atraso * 1000);
  else assustar();
}

$('#aceitar').addEventListener('click', comecar);
$('#aceitar2').addEventListener('click', comecar);
document.addEventListener('contextmenu', e => e.preventDefault());  // segurar a imagem não abre menu
</script>
</body>
</html>"""

TROTE_ROSTO = "rosto.svg"  # sempre gerado: a página volta para ele se a imagem escolhida não abrir

# Service worker: no Android, só por aqui (showNotification) dá para disparar a notificação de
# verdade do celular; o new Notification() da página não funciona lá. Toque na notificação só a fecha.
_TROTE_SW = """self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('notificationclick', (e) => { e.notification.close(); });
"""


def _num_trote(c: dict, chave: str, minimo: float, maximo: float) -> float:
    """Número da config dentro do intervalo; um valor inválido (editado à mão) vira o padrão."""
    try:
        return min(maximo, max(minimo, float(c.get(chave))))
    except (TypeError, ValueError):
        return PADRAO_CFG[chave]


def montar_pagina_trote(c: dict, img_arquivo: str, som_arquivo: str) -> str:
    textos = c.get("trote_notif_textos") or []
    if isinstance(textos, str):  # config editada à mão: um texto por linha
        textos = textos.splitlines()
    elif not isinstance(textos, list):
        textos = []
    cor = str(c.get("trote_cor") or "")
    opcoes = {
        "titulo": str(c.get("trote_titulo") or "Trote"),
        "mensagem": str(c.get("trote_mensagem") or ""),
        "imagem": img_arquivo or TROTE_ROSTO,
        "rosto": TROTE_ROSTO,
        "som": som_arquivo,
        "piscar": bool(c.get("trote_piscar", True)),
        "vibrar": bool(c.get("trote_vibrar", True)),
        "notificacoes": bool(c.get("trote_notificacoes", True)),
        "notif_textos": [str(t).strip() for t in textos if str(t).strip()],
        "cor": cor if re.fullmatch(r"#[0-9a-fA-F]{6}", cor) else PADRAO_CFG["trote_cor"],
        "atraso": _num_trote(c, "trote_atraso", 0, 30),
        "duracao": _num_trote(c, "trote_duracao", 0, 600),
        "volume": _num_trote(c, "trote_volume", 0, 1),
    }
    # Escapa < > &: um "</script>" na mensagem não pode fechar o <script> da página.
    dados = json.dumps(opcoes).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return _TROTE_HTML.replace("__CFG__", dados)


def preparar_trote() -> list:
    """Gera a pasta do trote: index.html, o rosto padrão e cópias da imagem e do som escolhidos.
    Devolve avisos para quem publica (por exemplo, um arquivo escolhido que não existe mais)."""
    c = cfg()
    TROTE_DIR.mkdir(parents=True, exist_ok=True)
    (TROTE_DIR / TROTE_ROSTO).write_text(_TROTE_ROSTO_SVG, "utf-8")
    (TROTE_DIR / "sw.js").write_text(_TROTE_SW, "utf-8")  # notificações de verdade no Android
    avisos, copiados = [], {}
    for chave, base, rotulo in (("trote_imagem", "imagem", "A imagem escolhida"),
                                ("trote_som", "som", "O som escolhido")):
        escolhido = os.path.expanduser(str(c.get(chave) or ""))
        copiados[base] = ""
        if escolhido and Path(escolhido).is_file():
            copiados[base] = base + (Path(escolhido).suffix.lower() or ".bin")
            # copyfile (e não copy2): a cópia fica com a data de agora, e quem já abriu o link não
            # recebe do cache a imagem/som de antes (o servidor compara a data com If-Modified-Since).
            with contextlib.suppress(shutil.SameFileError):
                shutil.copyfile(escolhido, TROTE_DIR / copiados[base])
        elif escolhido:
            avisos.append(f"{rotulo} não existe mais ({escolhido}); usando o padrão.")
        for antigo in TROTE_DIR.glob(base + ".*"):  # sobras de uma escolha anterior
            if antigo.name != copiados[base]:
                antigo.unlink(missing_ok=True)
    # Troca atômica: quem abre o link enquanto você edita não recebe a página pela metade.
    tmp = TROTE_DIR / ".index.html.tmp"
    tmp.write_text(montar_pagina_trote(c, copiados["imagem"], copiados["som"]), "utf-8")
    tmp.replace(TROTE_DIR / "index.html")
    return avisos


def servir_trote(porta: int) -> None:
    """Sobe a página do trote em primeiro plano (roda dentro do tmux)."""
    for texto in preparar_trote():  # regenera a partir da config atual a cada (re)início
        log(texto)
    pasta = str(TROTE_DIR)
    with ThreadingHTTPServer(("0.0.0.0", porta), lambda *a, **k: _HandlerSite(*a, directory=pasta, **k)) as servidor:
        log(f"Trote no ar em http://{ip_local()}:{porta}  (Ctrl+C para parar)")
        servidor.serve_forever()


def links_trote() -> list:
    c = cfg()
    links = [("Mesma rede Wi-Fi", f"http://{ip_local()}:{c['trote_porta']}/")]
    if servico_ativo("tunel-trote") and url_tunel("tunel-trote"):
        links.append(("Internet", f"{url_tunel('tunel-trote')}/"))
    return links


def mostrar_links_trote() -> None:
    if not servico_ativo("trote"):
        info("O trote não está no ar. Use 'Preparar e publicar'.")
        return
    for onde, link in links_trote():
        print(f"  {CIANO}{onde}:{RST}\n  {NEG}{link}{RST}")
    if not servico_ativo("tunel-trote"):
        print(f"  {DIM}Para quem está fora do seu Wi-Fi, use 'Liberar para a internet'.{RST}")


def parar_trote() -> None:
    parar_servico("tunel-trote")
    parar_servico("trote")


@submenu
def menu_editar_trote():
    c = cfg()

    def salvar(msg="Salvo."):
        salvar_cfg()
        if servico_ativo("trote"):  # o servidor lê os arquivos a cada acesso: basta gerar de novo
            for texto in preparar_trote():
                aviso(texto)
            msg += " Já vale no link publicado."
        ok(msg)

    def avisar_se_grande(arq):
        tamanho_arq = arq.stat().st_size
        if tamanho_arq > 8 * 1024 * 1024:
            aviso(f"Arquivo grande ({bytes_humanos(tamanho_arq)}): demora para carregar no celular de quem "
                  "abrir, principalmente pela internet. Prefira um arquivo curto.")

    def _texto(chave, msg):
        c[chave] = perguntar(msg, c.get(chave, ""))
        salvar()

    def _alternar(chave):
        c[chave] = not c.get(chave, True)
        salvar("Ligado." if c[chave] else "Desligado.")

    def escolher_imagem():
        if c.get("trote_imagem") and confirmar("Voltar à imagem padrão (rosto embutido)?", False):
            c["trote_imagem"] = ""
            salvar("Usando o rosto padrão.")
            return
        # Sem HEIC: o Chrome do Android não abre (a página cairia no rosto padrão).
        arq = escolher_arquivo("Imagem do susto (fica em tela cheia)", tuple(e for e in EXT_IMAGEM if e != ".heic"))
        if arq:
            avisar_se_grande(arq)
            c["trote_imagem"] = str(arq)
            salvar(f"Imagem: {arq.name}")

    def escolher_som():
        if c.get("trote_som") and confirmar("Voltar ao grito sintético padrão?", False):
            c["trote_som"] = ""
            salvar("Usando o grito sintético.")
            return
        # Sem AMR e WMA: os navegadores não tocam (a página cairia no grito sintético).
        arq = escolher_arquivo("Som do grito (toca em loop)", tuple(e for e in EXT_AUDIO if e not in (".amr", ".wma")))
        if arq:
            avisar_se_grande(arq)
            c["trote_som"] = str(arq)
            salvar(f"Som: {arq.name}")

    def editar_cor():
        cor = perguntar("Cor do pisca-pisca (hex, ex.: #b10000)", c.get("trote_cor", "#b10000")).strip()
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", cor):
            raise ToonsError("Use um hex de 6 dígitos, como #b10000.")
        c["trote_cor"] = cor
        salvar("Cor salva.")

    def editar_atraso():
        c["trote_atraso"] = perguntar_int("Segundos de 'carregando' antes do susto (0 = na hora)",
                                          c.get("trote_atraso", 2), 0, 30)
        salvar()

    def editar_duracao():
        c["trote_duracao"] = perguntar_int("Segundos de susto até a página revelar que era trote "
                                           "(0 = só para quando fechar a página)", c.get("trote_duracao", 15), 0, 600)
        salvar()

    def editar_volume():
        c["trote_volume"] = round(min(1.0, max(0.0, perguntar_float("Volume (0.0 a 1.0)", c.get("trote_volume", 1.0)))), 2)
        salvar()

    def editar_notificacoes_texto():
        atual = "\n".join(c.get("trote_notif_textos") or [])
        novo = editar_texto(atual, ".txt")
        if novo is None:
            return
        c["trote_notif_textos"] = [l.strip() for l in novo.splitlines() if l.strip()]
        salvar(f"{len(c['trote_notif_textos'])} notificação(ões) salva(s).")

    def img_rotulo():
        v = c.get("trote_imagem")
        return f"🖼️ Imagem do susto (atual: {Path(v).name if v else 'rosto padrão'})"

    def som_rotulo():
        v = c.get("trote_som")
        return f"🔊 Som do grito (atual: {Path(v).name if v else 'grito sintético'})"

    def duracao_rotulo():
        d = c.get("trote_duracao", 15)
        return f"⏳ Duração do susto (atual: {f'{d}s' if d else 'até fechar a página'})"

    menu("✏️ Personalizar o trote", [
        (lambda: f"📛 Nome/título do site (atual: {c.get('trote_titulo','')[:28]})",
         lambda: _texto("trote_titulo", "Nome/título que aparece na aba e nas notificações")),
        (lambda: f"💬 Mensagem do susto (atual: {c.get('trote_mensagem','')[:28]})",
         lambda: _texto("trote_mensagem", "Mensagem gigante que aparece na tela")),
        (img_rotulo, escolher_imagem),
        (som_rotulo, escolher_som),
        (lambda: f"✨ Piscar a tela: {'LIGADO' if c.get('trote_piscar', True) else 'desligado'}",
         lambda: _alternar("trote_piscar")),
        (lambda: f"📳 Vibrar o celular: {'LIGADO' if c.get('trote_vibrar', True) else 'desligado'}",
         lambda: _alternar("trote_vibrar")),
        (lambda: f"🔔 Notificações: {'LIGADAS' if c.get('trote_notificacoes', True) else 'desligadas'}",
         lambda: _alternar("trote_notificacoes")),
        ("📝 Editar os textos das notificações", editar_notificacoes_texto),
        (lambda: f"🎨 Cor do pisca-pisca (atual: {c.get('trote_cor','#b10000')})", editar_cor),
        (lambda: f"⏱️ Atraso até o susto (atual: {c.get('trote_atraso',2)}s)", editar_atraso),
        (duracao_rotulo, editar_duracao),
        (lambda: f"🔈 Volume (atual: {c.get('trote_volume',1.0)})", editar_volume),
    ])


@submenu
def menu_trote():
    c = cfg()

    def iniciar():
        aviso("Trote/screamer: a página dá um susto (grito alto, imagem em tela cheia, tela piscando, "
              "vibração e notificações) em quem abrir o link. Use só com quem topa a brincadeira.")
        info("A tela pisca forte e com som alto: NÃO envie para quem tem epilepsia fotossensível, "
             "problema cardíaco ou está dirigindo.")
        if not confirmar("Preparar e publicar o link do trote?", True):
            return
        porta = c["trote_porta"]
        if servico_ativo("trote"):
            parar_servico("trote")
        for texto in preparar_trote():
            aviso(texto)
        if not porta_livre(porta, espera=3):
            raise ToonsError(f"A porta {porta} já está em uso. Troque 'trote_porta' em Configurações.")
        if not iniciar_servico("trote", cmd_self("trote", "--porta", str(porta)), reiniciar=True):
            return
        if not servico_ativo("tunel-trote") and confirmar("Liberar o link para a internet (fora do seu Wi-Fi)?", True):
            abrir_tunel("tunel-trote", porta)
        print()
        mostrar_links_trote()
        if tem("termux-clipboard-set") and confirmar("Copiar o link?", True):
            _tapi(["termux-clipboard-set"], 10, entrada=links_trote()[-1][1], json_saida=False)
            ok("Link copiado. Mande para a vítima. 😈")
        info("O link funciona enquanto o Termux estiver aberto. O endereço do túnel muda a cada vez que religa. "
             "O que você muda em 'Personalizar' já vale no link publicado.")
        if servico_ativo("trote"):
            info("Notificações de VERDADE do Android só saem pelo link da internet (túnel) e se a pessoa "
                 "tocar em 'Permitir'. No link da rede Wi-Fi o navegador bloqueia e aparece a imitação "
                 "dentro do site. Para mandar as de verdade, use 'Liberar para a internet'.")

    menu("👻 Trote / pegadinha (screamer)", [
        ("😈 Preparar e publicar o link do trote", iniciar),
        ("🔗 Ver o link", mostrar_links_trote),
        ("🌍 Liberar para a internet (túnel)",
         lambda: abrir_tunel("tunel-trote", cfg()["trote_porta"]) if servico_ativo("trote") else info("Publique o trote primeiro.")),
        ("🛑 Tirar do ar", parar_trote),
        ("✏️ Personalizar (som, imagem, mensagem, efeitos...)", menu_editar_trote),
    ])


@submenu
def menu_diversao():
    menu("🎮 Diversão e aprendizado", [
        ("🎮 Jogos (2048, tetris, sudoku, snake, campo minado...)", menu_jogos),
        ("🎓 Aprender programação (Python, Bash, Git e BASIC retrô)", menu_aprender),
        ("📖 Leitor de livros (EPUB, PDF) e audiolivro", menu_livros),
        ("🎨 Arte ASCII, banner e tema do Termux", menu_arte),
        ("👻 Trote / pegadinha: link que dá um susto (screamer)", menu_trote),
    ])


# ════════════════════════════════════════════════════════════════════
#  25. Programação e servidores
# ════════════════════════════════════════════════════════════════════

BANCOS_DIR = DATA_DIR / "bancos"
MINECRAFT_DIR = HOME / "minecraft-servidor"


# ── Banco de dados ───────────────────────────────────────────────────

def _celula(valor) -> str:
    if valor is None:
        return "NULL"
    if isinstance(valor, bytes):
        return f"<{len(valor)} bytes>"
    return str(valor).replace("\n", " ")


def tabela_texto(colunas: list, linhas: list, largura_max: int = 24) -> list:
    """Linhas de uma tabela alinhada para o terminal."""
    larguras = [min(largura_max, max([len(str(c))] + [len(_celula(l[i])) for l in linhas]))
                for i, c in enumerate(colunas)]
    saida = [" │ ".join(f"{NEG}{str(c)[:w]:<{w}}{RST}" for c, w in zip(colunas, larguras)),
             "─┼─".join("─" * w for w in larguras)]
    for linha in linhas:
        saida.append(" │ ".join(f"{_celula(v)[:w]:<{w}}" for v, w in zip(linha, larguras)))
    return saida


def rodar_sql(conexao, sql: str) -> tuple:
    """(colunas, linhas, linhas afetadas). Vários comandos de uma vez rodam como script, sem resultado."""
    import sqlite3
    comandos = [c for c in re.split(r";\s*(?=\S|$)", sql.strip()) if c.strip()]
    try:
        if len(comandos) > 1:
            conexao.executescript(sql)
            conexao.commit()
            return [], [], -1
        cursor = conexao.execute(sql)
        if cursor.description:
            return [d[0] for d in cursor.description], cursor.fetchmany(500), -1
        conexao.commit()
        return [], [], cursor.rowcount
    except sqlite3.Error as e:
        raise ToonsError(f"SQL: {e}") from None


def ver_tabela_paginada(nome: str, colunas: list, linhas: list) -> None:
    if not linhas:
        info("Nenhuma linha.")
        return
    if not setas_ativas():
        print("\n".join(tabela_texto(colunas, linhas[:50])))
        return
    pagina = 0
    with TelaCheia():
        while True:
            _, altura = shutil.get_terminal_size((60, 24))
            por_pagina = max(3, altura - 5)
            paginas = (len(linhas) - 1) // por_pagina + 1
            pagina = max(0, min(pagina, paginas - 1))
            trecho = linhas[pagina * por_pagina:(pagina + 1) * por_pagina]
            desenhar([f" {NEG}{nome}{RST} {DIM}· {len(linhas)} linha(s) · página {pagina + 1}/{paginas}{RST}"]
                     + [" " + l for l in tabela_texto(colunas, trecho)]
                     + [f" {DIM}←→ página · Esc sai{RST}"])
            tecla = ler_tecla()
            if tecla in ("esc", "q"):
                return
            pagina += 1 if tecla in ("dir", "baixo", "pgdn", " ") else -1 if tecla in ("esq", "cima", "pgup") else 0


@submenu
def menu_banco_de_dados():
    import sqlite3

    def abrir_banco(caminho: Path):
        conexao = sqlite3.connect(caminho)

        def tabelas() -> list:
            return [r[0] for r in conexao.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY 1")]

        def ver():
            nomes = tabelas()
            if not nomes:
                info("O banco não tem tabelas. Crie com SQL (veja os exemplos) ou importe um CSV.")
                return
            contagens = [conexao.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0] for n in nomes]
            i = escolher("Qual tabela?", [f"{n}  {DIM}{q} linha(s){RST}" for n, q in zip(nomes, contagens)])
            if i is not None:
                colunas, linhas, _ = rodar_sql(conexao, f'SELECT * FROM "{nomes[i]}" LIMIT 500')
                ver_tabela_paginada(nomes[i], colunas, linhas)

        def sql():
            info("Exemplo: SELECT * FROM clientes WHERE cidade = 'Recife';")
            comando = ler_linhas("Digite o SQL")
            if not comando.strip():
                return
            colunas, linhas, afetadas = rodar_sql(conexao, comando)
            if colunas:
                ver_tabela_paginada("Resultado", colunas, linhas)
            else:
                ok("Feito." + (f" {afetadas} linha(s) afetada(s)." if afetadas >= 0 else ""))

        def esquema():
            for (texto,) in conexao.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"):
                print(f"{CIANO}{texto};{RST}\n")

        def importar_csv():
            arq = escolher_arquivo("Qual planilha CSV?", (".csv",))
            if not arq:
                return
            texto = arq.read_text("utf-8-sig", errors="replace")
            try:
                dialeto = csv.Sniffer().sniff(texto[:5000], delimiters=",;\t")
            except csv.Error:
                dialeto = csv.excel
            linhas = list(csv.reader(io.StringIO(texto), dialeto))
            if len(linhas) < 2:
                raise ToonsError("O CSV precisa de um cabeçalho e pelo menos uma linha.")
            colunas = [re.sub(r"\W+", "_", sem_acento(c).strip().lower()).strip("_") or f"coluna{k}"
                       for k, c in enumerate(linhas[0], 1)]
            nome = re.sub(r"\W+", "_", sem_acento(perguntar("Nome da tabela", arq.stem)).lower()).strip("_")
            conexao.execute(f'CREATE TABLE IF NOT EXISTS "{nome}" ({", ".join(f"{chr(34)}{c}{chr(34)} TEXT" for c in colunas)})')
            marcadores = ", ".join("?" * len(colunas))
            dados = [(l + [""] * len(colunas))[:len(colunas)] for l in linhas[1:] if any(l)]
            conexao.executemany(f'INSERT INTO "{nome}" VALUES ({marcadores})', dados)
            conexao.commit()
            ok(f"{len(dados)} linha(s) importada(s) na tabela '{nome}'.")

        def exportar_csv():
            nomes = tabelas()
            i = escolher("Exportar qual tabela?", nomes) if nomes else None
            if i is None:
                return
            cursor = conexao.execute(f'SELECT * FROM "{nomes[i]}"')
            destino = pasta_saida() / f"{nomes[i]}.csv"
            with open(destino, "w", newline="", encoding="utf-8-sig") as arq:
                escritor = csv.writer(arq, delimiter=";")
                escritor.writerow([d[0] for d in cursor.description])
                escritor.writerows(cursor)
            ok(f"Planilha salva: {destino}")

        def exemplos():
            print(f"""{CIANO}CREATE TABLE contatos (id INTEGER PRIMARY KEY, nome TEXT, telefone TEXT);
INSERT INTO contatos (nome, telefone) VALUES ('Ana', '81 99999-0000');
SELECT * FROM contatos WHERE nome LIKE 'A%' ORDER BY nome;
UPDATE contatos SET telefone = '81 98888-0000' WHERE id = 1;
DELETE FROM contatos WHERE id = 1;
SELECT cidade, COUNT(*) FROM clientes GROUP BY cidade;{RST}""")

        try:
            menu(f"🗃️ {caminho.name}", [
                ("Ver tabelas e dados", ver),
                ("Rodar SQL", sql),
                ("Estrutura (CREATE TABLE...)", esquema),
                ("Importar planilha CSV", importar_csv),
                ("Exportar tabela para CSV", exportar_csv),
                ("Exemplos de SQL", exemplos),
            ])
        finally:
            conexao.close()

    def escolher_banco():
        BANCOS_DIR.mkdir(parents=True, exist_ok=True)
        bancos = sorted(BANCOS_DIR.glob("*.db"))
        opcoes = [b.name for b in bancos] + ["➕ Criar banco novo", "📂 Abrir um arquivo .db do celular"]
        i = escolher("Qual banco?", opcoes)
        if i is None:
            return
        if i < len(bancos):
            abrir_banco(bancos[i])
        elif i == len(bancos):
            nome = re.sub(r"\W+", "_", sem_acento(perguntar("Nome do banco", "meu_banco"))).strip("_") or "banco"
            abrir_banco(BANCOS_DIR / f"{nome}.db")
        else:
            arq = escolher_arquivo("Qual arquivo?", (".db", ".sqlite", ".sqlite3", ".db3"))
            if arq:
                abrir_banco(arq)

    def mariadb():
        if not garantir_cmd("mariadbd-safe", "mariadb") and not tem("mysqld_safe"):
            return
        dados = Path(PREFIX or "/usr") / "var" / "lib" / "mysql"
        if not (dados / "mysql").exists():
            info("Preparando o MariaDB pela primeira vez...")
            rodar(["mariadb-install-db" if tem("mariadb-install-db") else "mysql_install_db"])
        i = escolher("MariaDB (MySQL)", ["Iniciar o servidor", "Abrir o console SQL", "Parar o servidor",
                                         "Status e log"])
        if i == 0:
            iniciar_servico("mariadb", "mariadbd-safe" if tem("mariadbd-safe") else "mysqld_safe")
            info(f"Conecte em localhost:3306 com o usuário '{getpass.getuser()}' (sem senha, só daqui do celular).")
        elif i == 1:
            rodar(["mariadb" if tem("mariadb") else "mysql", "-u", getpass.getuser()], mostrar=False)
        elif i == 2:
            parar_servico("mariadb")
        elif i == 3:
            status_servico("mariadb")

    def postgres():
        if not garantir_cmd("postgres", "postgresql"):
            return
        dados = Path(PREFIX or "/usr") / "var" / "lib" / "postgresql"
        if not (dados / "PG_VERSION").exists():
            info("Preparando o PostgreSQL pela primeira vez...")
            dados.mkdir(parents=True, exist_ok=True)
            rodar(["initdb", str(dados)], check=True)
        i = escolher("PostgreSQL", ["Iniciar o servidor", "Abrir o console (psql)", "Criar um banco", "Parar",
                                    "Status e log"])
        if i == 0:
            iniciar_servico("postgres", shlex.join(["postgres", "-D", str(dados)]))
            time.sleep(2)
            rodar(["createdb", getpass.getuser()], capturar=True)  # banco padrão do usuário (se já existir, tudo bem)
            info(f"Conecte em localhost:5432 com o usuário '{getpass.getuser()}'.")
        elif i == 1:
            rodar(["psql", perguntar("Banco", getpass.getuser())], mostrar=False)
        elif i == 2:
            rodar(["createdb", perguntar("Nome do banco")])
        elif i == 3:
            parar_servico("postgres")
        elif i == 4:
            status_servico("postgres")

    menu("🗃️ Banco de dados", [
        ("SQLite: abrir ou criar um banco (leve, sem servidor)", escolher_banco),
        ("MariaDB / MySQL (servidor)", mariadb),
        ("PostgreSQL (servidor)", postgres),
    ])


# ── GitHub no celular ────────────────────────────────────────────────

def repos_locais() -> list:
    """Pastas com repositório git em ~, ~/projetos e ~/storage/shared (até 2 níveis)."""
    achados = []
    for base in (HOME, HOME / "projetos", HOME / "storage" / "shared"):
        if not base.exists():
            continue
        for pasta in [base] + [p for p in base.iterdir() if p.is_dir() and not p.name.startswith(".")]:
            with contextlib.suppress(OSError):
                if (pasta / ".git").exists() and pasta not in achados:
                    achados.append(pasta)
    return achados


def _garantir_identidade_git() -> None:
    if not saida(["git", "config", "--global", "user.name"]):
        rodar(["git", "config", "--global", "user.name", perguntar("Seu nome (aparece nos commits)")])
    if not saida(["git", "config", "--global", "user.email"]):
        rodar(["git", "config", "--global", "user.email", perguntar("Seu e-mail do GitHub")])


@submenu
def menu_github():
    def gh_ok() -> bool:
        if not (garantir_cmd("git") and garantir_cmd("gh")):
            return False
        if tem("termux-open-url"):
            os.environ.setdefault("BROWSER", "termux-open-url")
        if rodar(["gh", "auth", "status"], capturar=True, timeout=30).returncode != 0:
            aviso("Você ainda não entrou na sua conta do GitHub.")
            if confirmar("Entrar agora (abre o navegador com um código)?", True):
                rodar(["gh", "auth", "login", "--web", "--git-protocol", "https"], mostrar=False)
                rodar(["gh", "auth", "setup-git"], capturar=True)
        return rodar(["gh", "auth", "status"], capturar=True, timeout=30).returncode == 0

    def acoes_repo(repo: str):
        while True:
            i = escolher(repo, ["Clonar para o celular", "Ver issues", "Ver pull requests", "Criar issue",
                                "Abrir no navegador", "Voltar"])
            if i in (None, 5):
                return
            if i == 0:
                destino = HOME / "projetos" / repo.split("/")[-1]
                destino.parent.mkdir(exist_ok=True)
                rodar(["gh", "repo", "clone", repo, str(destino)])
                ok(f"Clonado em {destino}")
            elif i == 1:
                rodar(["gh", "issue", "list", "-R", repo, "--limit", "30"])
            elif i == 2:
                rodar(["gh", "pr", "list", "-R", repo, "--limit", "30"])
            elif i == 3:
                titulo_i = perguntar("Título da issue")
                if titulo_i:
                    corpo = editar_texto("", ".md") or ""
                    rodar(["gh", "issue", "create", "-R", repo, "--title", titulo_i, "--body", corpo])
            elif i == 4:
                rodar(["gh", "repo", "view", repo, "--web"], capturar=True)
            pausar()

    def meus_repos():
        if not gh_ok():
            return
        bruto = saida(["gh", "repo", "list", "--limit", "60", "--json", "nameWithOwner,description,isPrivate"], 60)
        repos = json.loads(bruto or "[]")
        if not repos:
            info("Nenhum repositório (ou sem conexão).")
            return
        i = escolher("Meus repositórios", [f"{'🔒' if r['isPrivate'] else '🌐'} {r['nameWithOwner']}  "
                                           f"{DIM}{(r.get('description') or '')[:40]}{RST}" for r in repos])
        if i is not None:
            acoes_repo(repos[i]["nameWithOwner"])

    def outro_repo():
        if gh_ok():
            repo = perguntar("Repositório (dono/nome, ex.: termux/termux-app)")
            if "/" in repo:
                acoes_repo(repo.strip())

    def escolher_repo_local() -> Path | None:
        repos = repos_locais()
        i = escolher("Qual projeto?", [str(r) for r in repos] + ["Digitar a pasta..."])
        if i is None:
            return None
        pasta = repos[i] if i < len(repos) else Path(os.path.expanduser(perguntar("Pasta")))
        if not pasta.is_dir():
            raise ToonsError("Pasta não encontrada.")
        return pasta

    def commit_push():
        if not garantir_cmd("git"):
            return
        pasta = escolher_repo_local()
        if not pasta:
            return
        _garantir_identidade_git()
        mudancas = saida(["git", "-C", str(pasta), "status", "--short"])
        if not mudancas:
            info("Nada mudou desde o último commit.")
        else:
            print(mudancas)
            mensagem = perguntar("\nMensagem do commit (o que você mudou?)")
            if mensagem and confirmar("Adicionar tudo e fazer o commit?", True):
                rodar(["git", "-C", str(pasta), "add", "-A"], check=True, capturar=True)
                rodar(["git", "-C", str(pasta), "commit", "-m", mensagem], check=True)
        if confirmar("Enviar para o GitHub (push)?", True):
            if rodar(["git", "-C", str(pasta), "push"]).returncode != 0:
                rodar(["git", "-C", str(pasta), "push", "-u", "origin", "HEAD"])

    def criar_repo():
        if not gh_ok():
            return
        pasta = Path(os.path.expanduser(perguntar("Pasta do projeto", str(HOME / "projetos" / "meu-projeto"))))
        pasta.mkdir(parents=True, exist_ok=True)
        _garantir_identidade_git()
        if not (pasta / ".git").exists():
            rodar(["git", "-C", str(pasta), "init", "-b", "main"], capturar=True)
            if not any(p.name != ".git" for p in pasta.iterdir()):
                (pasta / "README.md").write_text(f"# {pasta.name}\n", "utf-8")
            rodar(["git", "-C", str(pasta), "add", "-A"], capturar=True)
            rodar(["git", "-C", str(pasta), "commit", "-m", "Primeiro commit"], capturar=True)
        visibilidade = "--private" if confirmar("Repositório privado?", True) else "--public"
        rodar(["gh", "repo", "create", perguntar("Nome no GitHub", pasta.name), visibilidade, "--source", str(pasta),
               "--push"])

    def atualizar():
        pasta = escolher_repo_local()
        if pasta:
            rodar(["git", "-C", str(pasta), "pull", "--ff-only"])

    menu("🐙 GitHub no celular", [
        ("Meus repositórios (clonar, issues, PRs)", meus_repos),
        ("Outro repositório (dono/nome)", outro_repo),
        ("Commit e push de um projeto (assistente)", commit_push),
        ("Baixar novidades de um projeto (pull)", atualizar),
        ("Criar repositório no GitHub a partir de uma pasta", criar_repo),
        ("Entrar / ver a conta do GitHub", lambda: gh_ok() and rodar(["gh", "auth", "status"])),
    ])


# ── Tarefas agendadas (cron) ─────────────────────────────────────────

def crontab_atual() -> str:
    proc = rodar(["crontab", "-l"], capturar=True, timeout=20, mostrar=False)
    return proc.stdout if proc.returncode == 0 else ""


def tarefas_agendadas(texto: str) -> list:
    """[(id, nome, expressão, comando)] das tarefas criadas pelo Termux-Toons no crontab."""
    tarefas, linhas = [], texto.splitlines()
    for i, linha in enumerate(linhas[:-1]):
        m = re.match(r"# toons:(\w+) (.*)", linha)
        if m:
            partes = linhas[i + 1].split(None, 5)
            if len(partes) == 6:
                tarefas.append((m.group(1), m.group(2), " ".join(partes[:5]), partes[5]))
    return tarefas


def gravar_crontab(texto: str) -> None:
    caminho = f"PATH={PREFIX}/bin:/usr/bin:/bin" if PREFIX else ""
    if caminho and caminho not in texto:
        texto = caminho + "\n" + texto
    proc = rodar(["crontab", "-"], entrada=texto.rstrip("\n") + "\n", capturar=True, timeout=20, mostrar=False)
    if proc.returncode != 0:
        raise ToonsError(f"O crontab recusou: {(proc.stderr or '').strip()}")


def descrever_cron(expressao: str) -> str:
    minuto, hora, dia, mes, semana = expressao.split()
    if expressao.startswith("*/") and hora == "*":
        return f"a cada {minuto[2:]} min"
    if minuto.isdigit() and hora == "*":
        return f"toda hora, no minuto {minuto}"
    if minuto.isdigit() and hora.isdigit():
        quando = f"{int(hora):02d}:{int(minuto):02d}"
        if dia == "*" and semana == "*":
            return f"todo dia às {quando}"
        if semana == "1-5":
            return f"dias úteis às {quando}"
        if semana.isdigit():
            return f"{['domingo', *DIAS_SEMANA[:6]][int(semana) % 7]} às {quando}"
        if dia.isdigit():
            return f"todo dia {dia} às {quando}"
    return expressao


@submenu
def menu_agendador():
    def garantir_cron() -> bool:
        return garantir_cmd("crontab", "cronie")

    def nova():
        if not garantir_cron():
            return
        modelos = [("Otimização rápida (limpa caches)", cmd_self("limpar")),
                   ("Atualizar Termux, pacotes e o Termux-Toons", cmd_self("atualizar")),
                   ("Backup da pasta do Termux em Downloads (.tar.gz)",
                    f"tar -czf {shlex.quote(str(pasta_saida('Backups')))}/termux-$(date +%Y%m%d).tar.gz "
                    f"-C {shlex.quote(str(HOME))} --exclude=./storage ."),
                   ("Checar os monitores (preço, sites...) uma vez", cmd_self("monitor", "--uma-vez")),
                   ("Comando que eu vou digitar", None)]
        i = escolher("O que rodar?", [m for m, _ in modelos])
        if i is None:
            return
        comando = modelos[i][1] or perguntar("Comando")
        if not comando:
            return
        frequencias = ["A cada X minutos", "A cada hora", "Todo dia num horário", "Dias úteis num horário",
                       "Uma vez por semana", "Uma vez por mês", "Expressão cron (avançado)"]
        f = escolher("Quando?", frequencias, 3)
        if f is None:
            return
        if f in (2, 3, 4, 5):
            hora = perguntar("Horário (hh:mm)", "03:00").replace("h", ":")
            m = re.fullmatch(r"(\d{1,2}):?(\d{2})?", hora)
            if not m or int(m.group(1)) > 23:
                raise ToonsError("Horário inválido.")
            h, mi = int(m.group(1)), int(m.group(2) or 0)
        if f == 0:
            expressao = f"*/{perguntar_int('A cada quantos minutos', 30, 1, 59)} * * * *"
        elif f == 1:
            expressao = f"{perguntar_int('Em que minuto da hora', 0, 0, 59)} * * * *"
        elif f == 2:
            expressao = f"{mi} {h} * * *"
        elif f == 3:
            expressao = f"{mi} {h} * * 1-5"
        elif f == 4:
            dia = escolher("Dia da semana", [d.capitalize() for d in DIAS_SEMANA])
            expressao = f"{mi} {h} * * {((dia or 0) + 1) % 7}"
        elif f == 5:
            expressao = f"{mi} {h} {perguntar_int('Dia do mês', 1, 1, 28)} * *"
        else:
            expressao = perguntar("Expressão (minuto hora dia mês dia-da-semana)", "0 3 * * *")
            if len(expressao.split()) != 5:
                raise ToonsError("A expressão tem 5 campos.")
        ident = uuid.uuid4().hex[:6]
        nome = perguntar("Nome da tarefa", modelos[i][0] if modelos[i][1] else comando[:30])
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_arq = shlex.quote(str(LOG_DIR / f"cron-{ident}.log"))
        linha = f"{expressao} ({comando}) >> {log_arq} 2>&1".replace("%", "\\%")  # no cron, % vira quebra de linha
        gravar_crontab(crontab_atual().rstrip("\n") + f"\n# toons:{ident} {nome}\n{linha}\n")
        ok(f"Agendado: {nome} ({descrever_cron(expressao)}).")
        if not servico_ativo("cron") and confirmar("O agendador (crond) está parado. Iniciar agora?", True):
            iniciar_servico("cron", "crond -n", reiniciar=True)

    def listar():
        tarefas = tarefas_agendadas(crontab_atual())
        if not tarefas:
            info("Nenhuma tarefa agendada pelo Termux-Toons.")
        for _, nome, expressao, comando in tarefas:
            print(f"  {CIANO}•{RST} {NEG}{nome}{RST} · {descrever_cron(expressao)}\n    {DIM}{comando[:90]}{RST}")
        print(f"\nAgendador: {'RODANDO' if servico_ativo('cron') else 'PARADO (nada roda!)'}")

    def escolher_tarefa(msg: str):
        tarefas = tarefas_agendadas(crontab_atual())
        if not tarefas:
            info("Nenhuma tarefa agendada.")
            return None
        i = escolher(msg, [f"{t[1]}  {DIM}{descrever_cron(t[2])}{RST}" for t in tarefas])
        return None if i is None else tarefas[i]

    def remover():
        t = escolher_tarefa("Remover qual?")
        if t and confirmar(f"Remover '{t[1]}'?", True):
            linhas, saida_linhas, pular = crontab_atual().splitlines(), [], 0
            for linha in linhas:
                if pular:
                    pular -= 1
                    continue
                if linha.startswith(f"# toons:{t[0]} "):
                    pular = 1
                    continue
                saida_linhas.append(linha)
            gravar_crontab("\n".join(saida_linhas))
            ok("Removida.")

    def rodar_agora():
        t = escolher_tarefa("Rodar qual agora?")
        if t:
            rodar(t[3].replace("\\%", "%"))

    def ver_log_tarefa():
        t = escolher_tarefa("Ver o log de qual?")
        if t:
            arq = LOG_DIR / f"cron-{t[0]}.log"
            print(arq.read_text("utf-8", errors="replace")[-4000:] if arq.exists() else "Ainda não rodou.")

    menu("⏲️ Tarefas agendadas (cron)", [
        ("Agendar uma tarefa", nova),
        ("Ver tarefas agendadas", listar),
        ("Rodar uma tarefa agora (teste)", rodar_agora),
        ("Ver o log de uma tarefa", ver_log_tarefa),
        ("Remover tarefa", remover),
        ("Editar o crontab à mão", lambda: garantir_cron() and rodar(["crontab", "-e"], mostrar=False)),
        *itens_servico("cron", "Agendador (crond)", lambda: garantir_cron() and
                       iniciar_servico("cron", "crond -n", reiniciar=True)),
    ], cabecalho=lambda: print(f"{DIM}O Android pode pausar o Termux: as tarefas rodam enquanto o agendador "
                               f"estiver ativo (ele segura o wake-lock).{RST}"))


# ── Servidores: Minecraft, Jellyfin, Navidrome ───────────────────────

def instalar_minecraft() -> None:
    info("Buscando a versão mais recente do servidor oficial (Java Edition)...")
    manifesto = pedir_json("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
    versao = perguntar("Versão do Minecraft", manifesto["latest"]["release"])
    entrada = next((v for v in manifesto["versions"] if v["id"] == versao), None)
    if not entrada:
        raise ToonsError(f"Versão '{versao}' não encontrada.")
    detalhes = pedir_json(entrada["url"])
    java = int(detalhes.get("javaVersion", {}).get("majorVersion", 21))
    versao_java = re.search(r'version "(\d+)', (rodar(["java", "-version"], capturar=True, timeout=30).stderr or "")
                            if tem("java") else "")
    if not versao_java or int(versao_java.group(1)) < java:
        info(f"Essa versão precisa do Java {java}.")
        if not instalar_pkg(f"openjdk-{java}") and java < 21:
            instalar_pkg("openjdk-21")
    MINECRAFT_DIR.mkdir(parents=True, exist_ok=True)
    baixar_arquivo(detalhes["downloads"]["server"]["url"], MINECRAFT_DIR / "server.jar")
    print("\nPara rodar o servidor é preciso aceitar a EULA do Minecraft: https://aka.ms/MinecraftEULA")
    if not confirmar("Você aceita a EULA?", False):
        raise ToonsError("Sem aceitar a EULA o servidor não inicia.")
    (MINECRAFT_DIR / "eula.txt").write_text("eula=true\n", "utf-8")
    propriedades = MINECRAFT_DIR / "server.properties"
    if not propriedades.exists():
        jogadores = perguntar_int("Máximo de jogadores", 5, 1, 50)
        original = confirmar("Exigir conta original do Minecraft (recomendado)?", True)
        propriedades.write_text(f"motd=Servidor no Termux\nmax-players={jogadores}\nonline-mode={str(original).lower()}"
                                "\nview-distance=6\nsimulation-distance=4\n", "utf-8")
    ok(f"Servidor {versao} instalado em {MINECRAFT_DIR}.")


def iniciar_minecraft() -> bool:
    if not (MINECRAFT_DIR / "server.jar").exists():
        instalar_minecraft()
    memoria = cfg().get("minecraft_memoria", "1G")
    cmd = f"cd {shlex.quote(str(MINECRAFT_DIR))} && java -Xms512M -Xmx{memoria} -jar server.jar nogui"
    if iniciar_servico("minecraft", cmd):
        info(f"Endereço para entrar (mesmo Wi-Fi): {NEG}{ip_local()}:25565{RST}. A primeira partida demora para "
             "gerar o mundo.")
        return True
    return False


def parar_minecraft() -> None:
    if not servico_ativo("minecraft"):
        info("O servidor não está rodando.")
        return
    info("Salvando o mundo e desligando...")
    rodar(["tmux", "send-keys", "-t", "=" + sessao("minecraft"), "stop", "Enter"], capturar=True)
    for _ in range(40):
        time.sleep(1)
        if not servico_ativo("minecraft"):
            ok("Servidor desligado.")
            return
    parar_servico("minecraft")


@submenu
def menu_servidores():
    c = cfg()

    def jellyfin():
        if not garantir_cmd("jellyfin", "jellyfin-server"):
            return
        garantir_storage()
        if iniciar_servico("jellyfin", 'jellyfin --datadir "$HOME/.local/share/jellyfin" '
                                       '--configdir "$HOME/.config/jellyfin"', reiniciar=True):
            info(f"Abra http://{ip_local()}:8096 (ou http://localhost:8096 aqui) e siga o assistente.\n"
                 "  Para a biblioteca, use pastas como /storage/emulated/0/Movies ou /storage/emulated/0/Download.")

    def navidrome():
        if not garantir_cmd("navidrome"):
            return
        garantir_storage()
        dados = HOME / ".navidrome"
        dados.mkdir(exist_ok=True)
        cmd = shlex.join(["navidrome", "--musicfolder", str(pasta_musicas()), "--datafolder", str(dados),
                          "--address", "0.0.0.0", "--port", "4533"])
        if iniciar_servico("navidrome", cmd, reiniciar=True):
            info(f"Abra http://{ip_local()}:4533 e crie o usuário administrador. Apps compatíveis: Tempo, "
                 "Symfonium, Ultrasonic (protocolo Subsonic).")

    menu("🖥️ Servidores no celular", [
        ("⛏️ Minecraft (Java): instalar ou atualizar", instalar_minecraft),
        ("⛏️ Minecraft: iniciar", iniciar_minecraft),
        ("⛏️ Minecraft: console (comandos do servidor; Ctrl+b d sai)", lambda: abrir_sessao("minecraft")),
        ("⛏️ Minecraft: desligar salvando o mundo", parar_minecraft),
        (lambda: f"⛏️ Minecraft: memória ({c.get('minecraft_memoria', '1G')})",
         lambda: (c.update(minecraft_memoria=perguntar("Memória máxima (ex.: 1G, 1536M, 2G)",
                                                       c.get("minecraft_memoria", "1G")).upper()), salvar_cfg())),
        ("🎬 Jellyfin: seus filmes e séries no navegador e na TV (porta 8096)", jellyfin),
        ("🎬 Jellyfin: parar", lambda: parar_servico("jellyfin")),
        ("🎵 Navidrome: sua música em qualquer app (porta 4533)", navidrome),
        ("🎵 Navidrome: parar", lambda: parar_servico("navidrome")),
    ], cabecalho=lambda: print(f"{DIM}Os servidores ficam no ar enquanto o Termux roda. Deixe o celular na tomada e "
                               f"sem otimização de bateria para o Termux.{RST}"))


@submenu
def menu_programacao():
    menu("🛠️ Programação e servidores", [
        ("🗃️ Banco de dados (SQLite, MariaDB, PostgreSQL)", menu_banco_de_dados),
        ("🐙 GitHub no celular (clonar, commit, push, issues)", menu_github),
        ("⏲️ Tarefas agendadas (cron)", menu_agendador),
        ("🖥️ Servidores (Minecraft, Jellyfin, Navidrome)", menu_servidores),
        ("💻 Ambiente de desenvolvimento (Neovim, compiladores)", menu_dev),
    ])


# ════════════════════════════════════════════════════════════════════
#  Configurações e diagnóstico
# ════════════════════════════════════════════════════════════════════

@submenu
def menu_config():
    c = cfg()

    def mostrar():
        for chave, valor in c.items():
            if chave in ("monitores", "compartilhamentos", "sites"):
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

    menu("⚙️ Configurações e diagnóstico", [
        ("🩺 Diagnóstico (o que está instalado e funcionando)", diagnostico),
        ("📦 Instalar os essenciais (python, tmux, termux-api, git)", instalar_essenciais),
        ("Ver configuração atual", mostrar),
        (lambda: f"Comando sh nos bots ({'permitido' if c['bot_permitir_shell'] else 'bloqueado'})", shell_bots),
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
    ("qrencode", "libqrencode", "QR code"), ("zbarimg", "zbar", "ler QR code"), ("tesseract", "tesseract", "OCR"),
    ("aria2c", "aria2", "downloads"), ("w3m", "w3m", "navegador texto"), ("browsh", "browsh", "Browsh (x11-repo)"),
    ("figlet", "figlet", "arte ASCII"), ("qpdf", "qpdf", "PDF"), ("gs", "ghostscript", "comprimir PDF"),
    ("pdftotext", "poppler", "PDF e livros"), ("gh", "gh", "GitHub"), ("crontab", "cronie", "tarefas agendadas"),
    ("scrcpy", "scrcpy", "espelhar tela (x11-repo)"), ("java", "openjdk-21", "Minecraft"),
]
MODULOS_OPCIONAIS = [("rich", "dashboard"), ("flask", "servidor web"), ("fastapi", "servidor web"),
                     ("uvicorn", "servidor web"), ("discord", "bot Discord"), ("mutagen", "capas de música"),
                     ("textual", "apps TUI"), ("PIL", "fotos e imagens"), ("cryptography", "cofre de senhas"),
                     ("anthropic", "Claude (IA na nuvem)")]


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


GRADIENTE_BANNER = [205, 170, 141, 111, 81]  # rosa → lilás → azul-claro (256 cores), de cima para baixo


def cabecalho() -> None:
    c = cfg()
    banner = [linha.rstrip() for linha in figlet(c["banner_texto"], c.get("banner_fonte") or "standard").splitlines()] \
        if c.get("banner_texto") and tem("figlet") else BANNER
    largura = max(map(_largura, banner), default=0)
    if largura > largura_tela():  # tela estreita demais para o desenho: só o nome
        banner = ["T E R M U X · T O O N S"]
        largura = _largura(banner[0])
    for i, linha in enumerate(banner):
        cor = GRADIENTE_BANNER[i * (len(GRADIENTE_BANNER) - 1) // max(1, len(banner) - 1)]
        # todas as linhas com a mesma largura: centralizadas pelo menu, o desenho não entorta
        print(f"{_c(f'38;5;{cor}')}{linha}{' ' * (largura - _largura(linha))}{RST}")
    ambiente = "Termux" if IS_TERMUX else "fora do Termux"
    print(f"{DIM}v{VERSION} · {ambiente} · serviços: {', '.join(servicos_ativos()) or 'nenhum'}{RST}")


# ── Busca no menu: acha uma opção pelo nome, mesmo com erro de digitação ──
# Cada item é (rótulo mostrado, palavras de busca, função que abre). As palavras
# extras cobrem o que não aparece no rótulo (ex.: "forca" dentro de 🎯 Jogos) e
# apelidos/erros comuns. A comparação ignora acento e maiúscula e usa similaridade
# (difflib), então "vdeos" encontra "vídeos" e "bateira" encontra "bateria".

def _indice_busca() -> list:
    return [
        ("🌐 Servidor web / API pessoal", "api rest flask fastapi servidor http token endpoint", menu_web),
        ("🤖 Bots Telegram / Discord 24h", "telegram discord bot chatbot robo", menu_bots),
        ("🔎 Scraping e monitoramento", "scraping monitorar monitoramento site preco alerta mudanca", menu_monitor),
        ("🛡️ Rede e segurança", "nmap ssh wireguard vpn porta firewall rede wifi scan seguranca", menu_rede),
        ("🐧 Linux de verdade (proot-distro)", "debian ubuntu arch alpine kali linux distro proot gnu", menu_proot),
        ("🖥️ Interface gráfica da distro (Termux:X11)", "x11 interface grafica desktop gui tela", menu_x11),
        ("🗄️ Arquivos e backup", "gerenciador arquivos nuvem rclone backup pasta compartilhar", menu_arquivos),
        ("🌐 Publicar página / site por link", "site html publicar pagina link servir web", publicar_site),
        ("🎵 Música, rádio e podcasts", "musica mp3 audio tocar playlist som", menu_musica),
        ("📻 Rádio online", "radio fm estacao radios ao vivo", menu_radio),
        ("🎙️ Podcasts", "podcast podcasts episodio", menu_podcasts),
        ("🎬 Vídeos (TikTok, YouTube)", "video videos youtube tiktok instagram baixar download yt-dlp", menu_videos),
        ("📺 Compartilhar filme por link", "filme video streaming link assistir compartilhar serie", menu_midia),
        ("🧮 Calculadora científica", "calcular calculadora conta matematica cientifica", menu_calculadora),
        ("🧰 Utilitários", "utilitarios ferramentas notas tarefas lembretes agenda senhas", menu_utilitarios),
        ("📝 Notas", "nota notas anotacao anotacoes bloco texto", menu_notas),
        ("⏰ Lembretes", "lembrete lembretes lembrar reminder avisar", menu_lembretes),
        ("⏱️ Relógio (alarme, cronômetro, timer)", "alarme cronometro timer temporizador despertador relogio", menu_relogio),
        ("📅 Agenda", "agenda compromisso evento eventos calendario", menu_agenda),
        ("📐 Conversor de unidades", "converter conversor unidade medida moeda temperatura peso distancia", menu_conversor),
        ("💰 Controle de gastos", "gasto gastos despesa dinheiro orcamento financeiro conta", menu_gastos),
        ("🔑 Cofre de senhas", "senha senhas password passwords cofre credencial login", menu_senhas),
        ("🌦️ Previsão do tempo", "tempo clima previsao chuva temperatura meteorologia", menu_tempo),
        ("🔳 QR code", "qr qrcode codigo ler gerar escanear", menu_qr),
        ("🌍 Tradutor", "traduzir traducao tradutor idioma lingua", menu_tradutor),
        ("📲 Celular e sistema", "celular sistema android adb bateria apps fotos", menu_celular),
        ("🔌 Depuração sem fio (ADB)", "adb depuracao wifi wireless android shell signal 9 pareamento", menu_adb),
        ("📖 Comandos do ADB (com descrição)", "comandos adb lista ajuda pm am dpm shell screencap screenrecord "
                                              "logcat dumpsys install push pull forward", menu_comandos_adb),
        ("📳 Termux:API", "termux api sensor sms notificacao camera localizacao vibrar lanterna volume", menu_termux_api),
        ("🔋 Saúde da bateria", "bateria carga ciclo saude temperatura energia percentual", menu_bateria),
        ("📊 Tempo de tela e dados por app", "tempo de tela uso internet dados app consumo gasto rede", menu_uso_celular),
        ("📦 Gerenciador de apps", "apps aplicativos bloatware desativar remover permissao apk abrir parar", menu_apps),
        ("🖼️ Fotos", "foto fotos organizar duplicadas parecidas comprimir gps localizacao galeria", menu_fotos),
        ("🔄 Conversor de arquivos", "converter imagem pdf video gif audio word excel powerpoint jpg png webp", menu_conversor_arquivos),
        ("🤖 Automação por eventos (Tasker)", "automacao tasker evento gatilho horario wifi carregador bateria", menu_automacao),
        ("📱 Espelhar a tela (scrcpy)", "espelhar scrcpy tela espelhamento mostrar", menu_espelhar),
        ("🖥️ Resolução da tela", "resolucao tela dpi densidade pixel diminuir baixar jogo app leve desempenho fps "
                                 "lag travando wm size", menu_resolucao),
        ("📡 Modem (AT / 3GPP)", "modem at comando 3gpp sinal operadora", menu_modem),
        ("🌐 Internet e comunicação", "internet email noticias downloads navegador chat links", menu_internet),
        ("📧 E-mail", "email e-mail gmail outlook yahoo icloud caixa entrada enviar anexo", menu_email),
        ("📰 Notícias (RSS)", "noticias noticia rss feed jornal g1 bbc folha", menu_noticias),
        ("⬇️ Downloads (aria2, torrent)", "download downloads baixar aria2 torrent magnet fila", menu_downloads),
        ("💬 Chat na rede local", "chat mensagem rede local lan conversar sem internet", menu_chat),
        ("🌐 Navegador no terminal", "navegador browser browsh w3m web site pesquisar", menu_navegador),
        ("🔗 Encurtador, pastebin e enviar arquivo", "encurtador link pastebin enviar arquivo url curto", menu_links),
        ("✨ Inteligência artificial", "ia ai inteligencia artificial claude chatgpt gemini llama voz ocr", menu_ia),
        ("💬 Assistente na nuvem (Claude, ChatGPT, Gemini)", "claude chatgpt gpt gemini assistente nuvem api conversar", menu_llm),
        ("🎤 Voz para texto e texto para voz", "voz texto whisper ditado transcrever audio fala tts falar", menu_voz),
        ("🔎 OCR: texto de foto ou print", "ocr texto foto imagem tesseract ler print extrair", menu_ocr),
        ("🎮 Diversão e aprendizado", "diversao jogos retro basic cursos livros aprender", menu_diversao),
        ("🎯 Jogos", "jogo jogos 2048 campo minado sudoku forca velha tetris snake adivinhe quiz recorde", menu_jogos),
        ("🎓 Aprender programação", "aprender python bash git basic curso licao exercicio programar programacao", menu_aprender),
        ("📖 Leitor de livros e audiolivro", "livro livros leitor epub pdf txt audiolivro ler", menu_livros),
        ("🎨 Arte ASCII, banner e tema do Termux", "arte ascii figlet banner tema cores dracula nord gruvbox", menu_arte),
        ("🔤 Fonte do terminal", "fonte fontes letra font ttf otf tipografia mono nerd font jetbrains terminal",
         trocar_fonte_terminal),
        ("👻 Trote / pegadinha (screamer)", "trote pegadinha screamer susto brincadeira", menu_trote),
        ("🛠️ Programação e servidores", "programacao dev sql github cron servidor banco de dados", menu_programacao),
        ("💻 Ambiente de desenvolvimento", "dev desenvolvimento neovim nvim lsp code-server vscode clang rust go ide", menu_dev),
        ("🗃️ Banco de dados (SQLite, MySQL, PostgreSQL)", "banco dados sqlite mariadb mysql postgresql sql csv", menu_banco_de_dados),
        ("🐙 GitHub (gh)", "github gh repositorio repo commit push pr issue clonar", menu_github),
        ("⏲️ Tarefas agendadas (cron)", "cron agendar tarefa agendada crontab horario periodico", menu_agendador),
        ("🖥️ Servidores (Minecraft, Jellyfin, Navidrome)", "minecraft jellyfin navidrome servidor server jogo media", menu_servidores),
        ("🔄 Atualização", "atualizar atualizacao upgrade pkg pip espelho repositorio", menu_atualizar),
        ("🧹 Otimização e limpeza", "limpar limpeza cache espaco otimizar lixo duplicados temporarios", menu_otimizacao),
        ("⚙️ Configurações e diagnóstico", "configuracao configuracoes diagnostico config token reset essenciais", menu_config),
    ]


_STOP_BUSCA = {"de", "da", "do", "e", "ou", "no", "na", "os", "as", "um", "uma", "por",
               "com", "para", "the", "a", "o"}


def _casa_palavra(palavra: str, token: str) -> float:
    """0 a 1 para uma palavra da busca contra um termo. Casa exato, começo igual
    (digitar o início: 'git'→'github', 'qr'→'qrcode') ou a palavra inteira dentro
    do termo valem alto; o resto vai pela semelhança (difflib), que perdoa trocas
    e letras faltando ('vdeos'→'videos')."""
    if palavra == token:
        return 1.0
    curto, longo = sorted((palavra, token), key=len)
    razao = len(curto) / len(longo)
    if len(curto) >= 2 and (token.startswith(palavra) or palavra.startswith(token)):
        return 0.82 + 0.18 * razao  # digitou o começo (evita casar só pela 1ª letra)
    if len(palavra) >= 3 and palavra in token:  # 'foto' dentro de 'fotos'
        return 0.74 + 0.16 * razao
    return difflib.SequenceMatcher(None, palavra, token).ratio()


def _pontua_busca(consulta: str, termos: str) -> float:
    """0 a 1: o quanto a consulta (já sem acento/minúscula) casa com os termos do item.
    Casa palavra a palavra; cada palavra vale pela melhor semelhança com um dos termos."""
    # tira palavrinhas de ligação (de, e, por...) que casariam com quase tudo
    tokens = {t for t in re.findall(r"[a-z0-9]+", termos) if len(t) >= 2 and t not in _STOP_BUSCA}
    palavras = [p for p in consulta.split() if p not in _STOP_BUSCA] or consulta.split()
    if not tokens or not palavras:
        return 0.0
    soma = 0.0
    for palavra in palavras:
        melhor = max(_casa_palavra(palavra, token) for token in tokens)
        soma += melhor
    return soma / len(palavras)


@submenu
def menu_busca():
    termo = perguntar("🔍 Buscar opção (ex.: 'vdeos', 'senha', 'bateria')").strip()
    if not termo:
        return
    consulta = sem_acento(termo).lower().strip()
    pontuados = ((_pontua_busca(consulta, f"{sem_acento(rotulo).lower()} {termos}"), rotulo, func)
                 for rotulo, termos, func in _indice_busca())
    achados = sorted((e for e in pontuados if e[0] >= 0.6), key=lambda e: e[0], reverse=True)[:12]
    if not achados:
        info(f"Nada parecido com '{termo}'. Tente outra palavra (ex.: 'jogo', 'foto', 'pdf', 'rede').")
        return
    i = escolher(f"Resultados para '{termo}'", [rotulo for _, rotulo, _ in achados])
    if i is None:
        return
    _, rotulo, func = achados[i]
    executar(func, rotulo)


def menu_principal() -> None:
    menu("Menu principal", [
        ("🔍 Buscar opção", menu_busca),
        ("🌐 Servidor web / API pessoal", menu_web),
        ("🤖 Bots Telegram / Discord 24h", menu_bots),
        ("🔎 Scraping e monitoramento", menu_monitor),
        ("🛡️ Rede e segurança", menu_rede),
        ("🐧 Linux de verdade", menu_proot),
        ("🗄️ Arquivos e backup", menu_arquivos),
        ("🎵 Música, rádio e podcasts", menu_musica),
        ("🎬 Vídeos", menu_videos),
        ("📺 Compartilhar filme por link", menu_midia),
        ("🧮 Calculadora científica", menu_calculadora),
        ("🧰 Utilitários", menu_utilitarios),
        ("📲 Celular e sistema", menu_celular),
        ("🌐 Internet", menu_internet),
        ("✨ Inteligência artificial", menu_ia),
        ("🎮 Diversão e aprendizado", menu_diversao),
        ("🛠️ Programação e servidores", menu_programacao),
        ("🔄 Atualização", menu_atualizar),
        ("🧹 Otimização e limpeza", menu_otimizacao),
        ("⚙️ Configurações e diagnóstico", menu_config),
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
    sub.add_parser("lembretes", help="serviço de lembretes e alarmes")
    sub.add_parser("bateria-log", help="registra a bateria e avisa (80%%, baixa, quente)")
    sub.add_parser("automacao", help="serviço de automação por eventos")
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
    p = sub.add_parser("trote", help="sobe a página do trote/screamer em primeiro plano")
    p.add_argument("--porta", type=int)
    p = sub.add_parser("tela", help="transmite a tela do celular para o navegador (link secreto)")
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
    p = sub.add_parser("resolucao", help="desfaz a última mudança de resolução ou volta a tela à de fábrica")
    p.add_argument("--vigiar", metavar="ID", help=argparse.SUPPRESS)  # o vigia que desfaz sem confirmação
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
        elif args.comando == "lembretes":
            rodar_lembretes()
        elif args.comando == "bateria-log":
            rodar_bateria()
        elif args.comando == "automacao":
            rodar_automacoes()
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
        elif args.comando == "trote":
            servir_trote(args.porta or cfg()["trote_porta"])
        elif args.comando == "tela":
            servir_tela(args.porta or cfg()["tela_porta"])
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
        elif args.comando == "resolucao":
            if args.vigiar:
                desfazer_resolucao(args.vigiar)
            elif desfazer_resolucao():
                ok("Mudança de resolução sem confirmação desfeita.")
            else:
                resolucao_original()
    except (ToonsError, BasicErro) as e:
        erro(str(e))
        return 1
    except KeyboardInterrupt:
        print()
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
