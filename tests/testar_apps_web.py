#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes da categoria 🧩 Apps Web do LNUX (a ligação com o repositório LNUX-APPs).

Usa uma pasta pessoal TEMPORÁRIA. Confere o catálogo (apps.json), quando o link leva a chave da ponte e,
se houver uma cópia do LNUX-APPs por perto (variável LNUX_APPS_LOCAL, ou uma pasta lnux-apps / LNUX-APPs
ao lado deste repositório), sobe o servidor dela de verdade e confere como o LNUX reconhece o servidor
com e sem a ponte e com a chave errada.

Uso:  python3 tests/testar_apps_web.py
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CASA = Path(tempfile.mkdtemp(prefix="lnux-teste-apps-"))
os.environ["HOME"] = str(CASA)
os.environ["LNUX_SISTEMA"] = "debian"
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import lnux  # noqa: E402

lnux.log = lambda msg: None
CASOS = []


def caso(nome):
    def registrar(f):
        CASOS.append((nome, f))
        return f
    return registrar


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def copia_local() -> Path | None:
    for c in [os.environ.get("LNUX_APPS_LOCAL"), RAIZ.parent / "lnux-apps", RAIZ.parent / "LNUX-APPs"]:
        if c and (Path(c) / "servidor" / "lnux_apps.py").is_file():
            return Path(c)
    return None


@caso("Catálogo: lê o apps.json e ignora entradas sem id ou sem caminho")
def _():
    pasta = CASA / "falso-lnux-apps"
    pasta.mkdir()
    (pasta / "apps.json").write_text(json.dumps({"apps": [
        {"id": "video", "nome": "Vídeo", "caminho": "apps/video/", "estado": "pronto", "ponte": "opcional"},
        {"nome": "sem id", "caminho": "x/"}, {"id": "sem-caminho"}, "lixo",
        {"id": "pdf", "nome": "PDF", "caminho": "apps/pdf/", "estado": "planejado"},
    ]}), "utf-8")
    antes = lnux.LNUX_APPS_DIR
    lnux.LNUX_APPS_DIR = pasta
    try:
        assert [a["id"] for a in lnux.lnux_apps_catalogo()] == ["video", "pdf"]
        (pasta / "apps.json").write_text("{quebrado", "utf-8")
        assert lnux.lnux_apps_catalogo() == []
    finally:
        lnux.LNUX_APPS_DIR = antes


@caso("Link: leva a chave da ponte quando o app usa a ponte (e não leva quando a ponte é só 'se precisar')")
def _():
    abertos, pedidos = [], []
    original = (lnux.garantir_servidor_apps, lnux.abrir_link, lnux.lnux_apps_config)
    lnux.garantir_servidor_apps = lambda com_ponte, na_rede=False: pedidos.append(com_ponte) or 8095
    lnux.abrir_link = abertos.append
    lnux.lnux_apps_config = lambda: {"token": "chave-de-teste-123456789012"}
    try:
        opcional = {"id": "som", "nome": "Som", "caminho": "apps/som/", "ponte": "opcional"}
        necessaria = {"id": "papo", "nome": "Papo", "caminho": "apps/papo/", "ponte": "necessaria"}
        lnux.cfg()["apps_ponte"] = "sempre"
        lnux.abrir_app_web(opcional)
        assert abertos[-1] == "http://127.0.0.1:8095/apps/som/#token=chave-de-teste-123456789012" and pedidos[-1] is True
        lnux.cfg()["apps_ponte"] = "precisa"
        lnux.abrir_app_web(opcional)
        assert abertos[-1] == "http://127.0.0.1:8095/apps/som/" and pedidos[-1] is False
        lnux.abrir_app_web(necessaria)
        assert abertos[-1].endswith("/apps/papo/#token=chave-de-teste-123456789012") and pedidos[-1] is True
        lnux.abrir_app_web(None)  # página inicial: sempre com a ponte
        assert abertos[-1] == "http://127.0.0.1:8095/#token=chave-de-teste-123456789012"
    finally:
        lnux.garantir_servidor_apps, lnux.abrir_link, lnux.lnux_apps_config = original
        lnux.cfg()["apps_ponte"] = "sempre"


@caso("Servidor: reconhece o do LNUX-APPs com ponte, sem ponte, com a chave errada, e nada numa porta vazia")
def _():
    assert lnux.lnux_apps_estado(porta_livre()) is None
    local = copia_local()
    if not local:
        return "pulado (sem uma cópia do LNUX-APPs por perto; use LNUX_APPS_LOCAL=pasta)"
    dados = CASA / ".lnux-apps"
    env = {**os.environ, "LNUX_APPS_DADOS": str(dados)}
    servidor = local / "servidor" / "lnux_apps.py"
    token = subprocess.run([sys.executable, str(servidor), "--mostrar-token"], env=env, capture_output=True, text=True).stdout.strip()
    for sem_ponte in (False, True):
        porta = porta_livre()
        proc = subprocess.Popen([sys.executable, str(servidor), "--porta", str(porta), *(["--sem-ponte"] if sem_ponte else [])],
                                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(50):
                if lnux.lnux_apps_estado(porta, token):
                    break
                time.sleep(0.1)
            estado = lnux.lnux_apps_estado(porta, token)
            if sem_ponte:
                assert estado == {"ponte": False, "versao": estado["versao"], "motivo": estado["motivo"]}
            else:
                assert estado["ponte"] is True and "recursos" in estado
                assert lnux.lnux_apps_estado(porta, "errada" * 5) == {"ponte": True, "chave_diferente": True}
        finally:
            proc.terminate()
            proc.wait(timeout=10)


@caso("Túnel: liga o cloudflared, sobe o servidor do túnel aceitando só aquele endereço, sem comandos; com a ponte só se pedir")
def _():
    local = copia_local()
    if not local:
        return "pulado (sem uma cópia do LNUX-APPs por perto; use LNUX_APPS_LOCAL=pasta)"
    import urllib.request
    ativos, comandos = {}, []

    def iniciar(nome, comando, reiniciar=False, wake_lock=True, com_log=True):
        comandos.append((nome, comando))
        if comando.startswith("cloudflared"):  # o cloudflared de mentira: só escreve no log o endereço que ganhou
            lnux.log_de(nome).parent.mkdir(parents=True, exist_ok=True)
            lnux.log_de(nome).write_text("INF |  https://abc-teste.trycloudflare.com  |\n", "utf-8")
            ativos[nome] = None
        else:
            ativos[nome] = subprocess.Popen(comando, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return True

    def parar(nome):
        p = ativos.pop(nome, None)
        if p:
            os.killpg(p.pid, 15)
            p.wait(timeout=10)

    def estado(porta, host, token=""):
        h = {"Host": host, **({"X-Ponte-Token": token} if token else {})}
        try:
            with urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{porta}/api/estado", headers=h), timeout=3) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, None

    nomes = ("garantir_lnux_apps", "LNUX_APPS_DIR", "garantir_cmd", "iniciar_servico", "parar_servico", "servico_ativo", "escolher", "confirmar", "mostrar_qr", "endereco_fixo", "host_fixo")
    original = {n: getattr(lnux, n) for n in nomes}
    respostas = []
    lnux.garantir_lnux_apps = lambda: True
    lnux.LNUX_APPS_DIR = local
    lnux.garantir_cmd = lambda *a, **k: True
    lnux.iniciar_servico, lnux.parar_servico = iniciar, parar
    lnux.servico_ativo = lambda nome: nome in ativos
    lnux.escolher = lambda msg, opcoes, padrao=None: respostas.pop(0)
    lnux.confirmar = lambda msg, padrao=False: True
    lnux.mostrar_qr = lambda *a, **k: None
    lnux.endereco_fixo = lnux.host_fixo = lambda porta: None
    try:
        porta = porta_livre()
        lnux.cfg()["apps_porta_tunel"] = porta
        token = lnux.lnux_apps_config().get("token", "")
        # só os apps (o padrão)
        respostas[:] = [0]
        lnux.apps_web_tunel()
        cloud = next(c for n, c in comandos if n == lnux.SERVICO_TUNEL_APPS)
        serv = next(c for n, c in comandos if n == lnux.SERVICO_APPS_TUNEL)
        assert f"--url http://localhost:{porta}" in cloud, cloud
        assert "--permitir-host abc-teste.trycloudflare.com" in serv and "--sem-comandos" in serv and "--sem-ponte" in serv, serv
        assert lnux.apps_web_tunel_link() == "https://abc-teste.trycloudflare.com/"
        status, r = estado(porta, "abc-teste.trycloudflare.com")
        assert status == 200 and r["ponte"] is False, (status, r)
        with urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{porta}/apps/companhia/", headers={"Host": "abc-teste.trycloudflare.com"}), timeout=3) as rr:
            assert rr.status == 200 and b"Companhia" in rr.read()
        # chamando de novo com o túnel ligado: mostra o link e desliga quando pede
        respostas[:] = [2]
        lnux.apps_web_tunel()
        assert not ativos and lnux.apps_web_tunel_link() is None
        # com a ponte: o link leva a chave; o servidor aceita só o endereço do túnel e nunca roda comandos
        comandos.clear()
        respostas[:] = [1]
        lnux.apps_web_tunel()
        serv = next(c for n, c in comandos if n == lnux.SERVICO_APPS_TUNEL)
        assert "--sem-ponte" not in serv and "--sem-comandos" in serv, serv
        assert lnux.apps_web_tunel_link() == f"https://abc-teste.trycloudflare.com/#token={token}"
        status, r = estado(porta, "abc-teste.trycloudflare.com", token)
        assert status == 200 and r["ponte"] is True and r["recursos"]["comandos"] is False, (status, r)
        assert estado(porta, "abc-teste.trycloudflare.com")[0] == 401  # sem a chave, nada
        assert estado(porta, "outro.trycloudflare.com", token)[0] == 403  # outro endereço, nada
    finally:
        for n in list(ativos):
            parar(n)
        for n, v in original.items():
            setattr(lnux, n, v)


def main() -> int:
    ok = falhou = pulados = 0
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
    print(f"\n{ok} ok · {falhou} falharam · {pulados} pulados")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
