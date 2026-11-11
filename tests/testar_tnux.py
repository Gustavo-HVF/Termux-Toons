#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes da ligação do LNUX com o TNUX (🧩 Apps Web › 🐧 TNUX).

Usa uma pasta pessoal TEMPORÁRIA e um servidor tmux só do teste. Precisa de uma cópia do TNUX por perto
(variável TNUX_LOCAL, ou uma pasta TNUX-DistroSystem / tnux ao lado deste repositório): o LNUX "baixa" dela
com git, compila (make), liga a área de trabalho como serviço e confere a chave, a porta, a API e o link
pela internet (com um cloudflared de mentira, que escreve as mesmas mensagens do verdadeiro).

Uso:  python3 tests/testar_tnux.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

CASA = Path(tempfile.mkdtemp(prefix="lnux-teste-tnux-"))
os.environ["HOME"] = str(CASA)
os.environ["LNUX_SISTEMA"] = "debian"
os.environ["TMUX_TMPDIR"] = str(CASA)          # um servidor tmux só deste teste
os.environ.pop("TMUX", None)
os.environ.pop("DISPLAY", None)
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import lnux  # noqa: E402

lnux.log = lambda msg: None
lnux.abrir_link = lambda url: ABERTOS.append(url)
ABERTOS = []
CASOS = []

CLOUDFLARED_FALSO = """#!/bin/sh
echo "2026-11-11T14:12:54Z INF Requesting new quick Tunnel on trycloudflare.com..." >&2
sleep 0.3
echo "2026-11-11T14:12:55Z INF |  https://teste-do-lnux.trycloudflare.com                                   |" >&2
exec sleep 600
"""


def caso(nome):
    def registrar(f):
        CASOS.append((nome, f))
        return f
    return registrar


def copia_local() -> Path | None:
    for c in [os.environ.get("TNUX_LOCAL"), RAIZ.parent / "TNUX-DistroSystem", RAIZ.parent / "tnux"]:
        if c and (Path(c) / "ponte" / "tnuxd.c").is_file() and (Path(c) / ".git").is_dir():
            return Path(c)
    return None


LOCAL = copia_local()
if LOCAL:
    lnux.TNUX_REPO = str(LOCAL)    # o git clona da pasta local, como clonaria do GitHub


@caso("Sem o TNUX baixado: nada fica ligado e o menu sabe disso")
def _():
    assert not lnux.tnux_baixado() and not lnux.tnux_instalado()
    assert lnux.tnux_ponte() is None
    assert lnux.tnux_link_internet() is None


@caso("Não baixa sem perguntar: recusando, não clona nada")
def _():
    original = lnux.confirmar
    lnux.confirmar = lambda *a, **k: False
    try:
        assert lnux.garantir_tnux() is False
        assert not lnux.TNUX_DIR.exists()
    finally:
        lnux.confirmar = original


@caso("Baixa com git e compila (make): o tnux e o tnuxd ficam prontos")
def _():
    if not LOCAL:
        return "pulado: sem uma cópia do TNUX ao lado (defina TNUX_LOCAL)"
    lnux.confirmar = lambda *a, **k: True
    assert lnux.garantir_tnux() is True
    assert lnux.tnux_instalado(), "faltam os binários"
    assert lnux.tnux_tem("--tunel"), "a cópia não tem o túnel"
    r = subprocess.run([str(lnux.tnux_binario("tnux")), "versao"], capture_output=True, text=True)
    assert r.returncode == 0 and "TNUX" in r.stdout, r.stdout


@caso("Abre a área de trabalho: liga o serviço e abre o navegador com a chave")
def _():
    if not lnux.tnux_instalado():
        return "pulado: o TNUX não foi compilado"
    lnux.tnux_abrir()
    assert lnux.servico_ativo(lnux.SERVICO_TNUX), "o serviço não ficou de pé"
    ponte = lnux.tnux_ponte()
    assert ponte and ponte["token"] and ponte["porta"] >= lnux.TNUX_PORTA, ponte
    assert ABERTOS and ABERTOS[-1] == f"http://127.0.0.1:{ponte['porta']}/#token={ponte['token']}", ABERTOS
    with urllib.request.urlopen(f"http://127.0.0.1:{ponte['porta']}/", timeout=5) as r:
        assert b"TNUX" in r.read()
    info = lnux.tnux_api("/api/info")
    assert info and info["modo"] == "ponte" and info["casa"] == str(CASA), info
    assert info["lnux"] == str(Path(lnux.__file__).resolve()), f"o TNUX não achou este LNUX: {info['lnux']!r}"


@caso("Sem a chave, a área de trabalho não deixa mexer no aparelho")
def _():
    ponte = lnux.tnux_ponte()
    if not ponte:
        return "pulado: o TNUX não está ligado"
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{ponte['porta']}/api/info", timeout=5)
        raise AssertionError("respondeu sem a chave")
    except urllib.error.HTTPError as e:
        assert e.code == 401, e.code
    assert lnux.tnux_api("/api/info", ponte={**ponte, "token": "chave-errada-0123456789"}).get("status") == 401


@caso("Abrir de novo reaproveita o TNUX ligado (mesma chave)")
def _():
    antes = lnux.tnux_ponte()
    if not antes:
        return "pulado: o TNUX não está ligado"
    lnux.tnux_abrir()
    assert lnux.tnux_ponte() == antes


@caso("Compartilhar pela internet: liga o túnel, mostra o link e desliga")
def _():
    if not lnux.tnux_ponte():
        return "pulado: o TNUX não está ligado"
    pasta = CASA / "bin"
    pasta.mkdir(exist_ok=True)
    (pasta / "cloudflared").write_text(CLOUDFLARED_FALSO)
    (pasta / "cloudflared").chmod(0o755)
    # o tnuxd precisa achar o cloudflared: o TNUX procura também em ~/.local/bin
    (CASA / ".local" / "bin").mkdir(parents=True, exist_ok=True)
    shutil.copy(pasta / "cloudflared", CASA / ".local" / "bin" / "cloudflared")
    os.environ["PATH"] = f"{pasta}:{os.environ['PATH']}"
    escolhas = []
    original = lnux.escolher
    lnux.escolher = lambda msg, opcoes, *a, **k: escolhas.append(opcoes) or 0     # "Deixar ligado"
    try:
        lnux.tnux_compartilhar()
    finally:
        lnux.escolher = original
    link = lnux.tnux_link_internet()
    assert link and link.startswith("https://teste-do-lnux.trycloudflare.com/#token="), link
    chave = link.split("#token=")[1]
    assert chave != lnux.tnux_ponte()["token"], "o link devia ter uma chave própria"
    assert escolhas and "Copiar o link" in escolhas[0], escolhas
    lnux.tnux_compartilhar_parar()
    assert lnux.tnux_link_internet() is None


@caso("Na rede: religa para o Wi-Fi e o link leva o IP do aparelho")
def _():
    if not lnux.tnux_ponte():
        return "pulado: o TNUX não está ligado"
    antes = lnux.tnux_ponte()
    lnux.confirmar = lambda *a, **k: True
    mostrados = []
    original = lnux.mostrar_qr
    lnux.mostrar_qr = lambda conteudo, *a, **k: mostrados.append(conteudo)
    try:
        lnux.tnux_na_rede()
    finally:
        lnux.mostrar_qr = original
    depois = lnux.tnux_ponte()
    assert depois and depois["token"] != antes["token"], "devia ter religado (com outra chave)"
    assert mostrados and mostrados[0] == f"http://{lnux.ip_local()}:{depois['porta']}/#token={depois['token']}", mostrados
    assert lnux.cfg().get("tnux_na_rede_ativo") is True


@caso("Desligar: o serviço para e a chave deixa de existir")
def _():
    if not lnux.servico_ativo(lnux.SERVICO_TNUX):
        return "pulado: o TNUX não está ligado"
    porta = lnux.tnux_ponte()["porta"]
    lnux.parar_servico(lnux.SERVICO_TNUX)
    for _ in range(20):
        if lnux.tnux_ponte() is None:
            break
        time.sleep(0.25)
    assert lnux.tnux_ponte() is None
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{porta}/", timeout=2)
        raise AssertionError("ainda respondendo")
    except OSError:
        pass


@caso("Linha de comando: lnux tnux tem as ações do menu")
def _():
    r = subprocess.run([sys.executable, str(RAIZ / "lnux.py"), "tnux", "--help"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    for acao in ("abrir", "rede", "compartilhar", "parar-link", "parar", "terminal", "atualizar"):
        assert acao in r.stdout, acao


def main() -> int:
    ok = falhou = pulados = 0
    try:
        for nome, f in CASOS:
            try:
                r = f()
                if isinstance(r, str) and r.startswith("pulado"):
                    pulados += 1
                    print(f"  ⏭  {nome}: {r}")
                else:
                    ok += 1
                    print(f"  ✔ {nome}")
            except Exception as e:
                import traceback
                falhou += 1
                print(f"  ✖ {nome}\n    {type(e).__name__}: {e}")
                traceback.print_exc(limit=3)
    finally:
        subprocess.run(["tmux", "kill-server"], capture_output=True)
        shutil.rmtree(CASA, ignore_errors=True)
    print(f"\n{ok} ok · {falhou} falharam · {pulados} pulados")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
