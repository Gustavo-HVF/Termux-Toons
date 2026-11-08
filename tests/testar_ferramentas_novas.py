#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testa as ferramentas do Módulo 6 (as partes que não dependem da tela):
ficha do sistema, processos, espaço em disco, shell bonito, serviços (systemctl/OpenRC), servidor de pasta
com envio, ping, API HTTP, JSON/Markdown, contêineres, tldr, 2FA (vetores oficiais das RFC 4226 e 6238),
letra sincronizada (LRC), digitação, cotações e telas de descanso.

Uso:
    python3 tests/testar_ferramentas_novas.py

Usa uma pasta pessoal temporária e um servidor local numa porta livre; não acessa a internet.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import sys
import tempfile
import threading
import traceback
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
os.environ["HOME"] = tempfile.mkdtemp(prefix="lnux-teste-")
os.environ["LNUX_SISTEMA"] = "debian"
sys.path.insert(0, str(RAIZ))
import lnux  # noqa: E402

lnux.log = lambda msg: None  # o servidor de pasta anota cada pedido: aqui não precisa

TMP = Path(tempfile.mkdtemp(prefix="lnux-m6-"))
resultados = {"ok": 0, "falhou": 0}


def caso(nome: str):
    def registrar(func):
        try:
            func()
        except Exception:  # noqa: BLE001
            resultados["falhou"] += 1
            print(f"  ✖ {nome}\n{traceback.format_exc(limit=3)}")
        else:
            resultados["ok"] += 1
            print(f"  ✔ {nome}")
        return func
    return registrar


def visivel(texto: str) -> int:
    return lnux._largura(lnux._sem_ansi(texto))


# ── gráficos de terminal ─────────────────────────────────────────────

@caso("Gráficos: sparkline (com pings perdidos) e gráfico em colunas")
def _():
    assert lnux.sparkline([1, 2, 3, 4, 5, 6, 7, 8]) == "▁▂▃▄▅▆▇█"
    assert lnux.sparkline([5, None, 5]) == "▁✕▁"
    assert lnux.sparkline([None, None]) == "✕✕"
    assert len(lnux.sparkline(range(100), 20)) == 20
    linhas = lnux.grafico_em_colunas([1, 5, 3, 9, 2] * 20, 40, 6)
    assert len(linhas) == 6 and all(len(l) == 40 for l in linhas)
    assert linhas[0].strip() and linhas[-1].count(" ") < 40  # o máximo chega ao topo e todas as colunas aparecem


# ── sistema ──────────────────────────────────────────────────────────

@caso("Ficha do sistema: as informações principais aparecem")
def _():
    rotulos = dict(lnux.informacoes_do_sistema())
    for chave in ("Sistema", "Kernel", "CPU", "Memória", "Disco (~)", "LNUX"):
        assert rotulos.get(chave), chave
    lnux.confirmar = lambda *a, **k: False
    lnux.ficha_do_sistema()


@caso("Processos: o próprio teste aparece e o % de CPU é calculado")
def _():
    processos = lnux.ler_processos()
    assert os.getpid() in processos and processos[os.getpid()]["memoria"] > 0
    antes = {1: {"tiques": 100}, 2: {"tiques": 50}}
    agora = {1: {"tiques": 200}, 2: {"tiques": 50}, 3: {"tiques": 10}}
    cpu = lnux.calcular_cpu(antes, agora, 1.0)
    tiques = os.sysconf("SC_CLK_TCK")
    assert abs(cpu[1] - 100 * 100 / tiques) < 1e-6 and cpu[2] == 0 and 3 not in cpu


@caso("Espaço em disco: pastas somadas, do maior para o menor, com cache")
def _():
    base = TMP / "disco"
    (base / "grande").mkdir(parents=True)
    (base / "grande" / "a.bin").write_bytes(b"x" * 50_000)
    (base / "pequena").mkdir()
    (base / "pequena" / "b.txt").write_bytes(b"y" * 100)
    (base / "solto.dat").write_bytes(b"z" * 5_000)
    cache = {}
    itens = lnux.tamanhos_da_pasta(base, cache)
    assert [p.name for _, p, _ in itens] == ["grande", "solto.dat", "pequena"]
    assert itens[0][0] == 50_000 and itens[0][2] is True and base / "grande" in cache


@caso("Shell bonito: as linhas do LNUX entram uma vez só e saem ao desfazer")
def _():
    rc = TMP / ".bashrc"
    rc.write_text("export PATH=$PATH:~/bin\n")
    for _ in range(2):
        lnux._acrescentar_ao_rc(rc, ['eval "$(starship init bash)"'], "starship")
    assert rc.read_text().count("starship init") == 1
    assert lnux._tirar_do_rc(rc, "starship") and rc.read_text() == "export PATH=$PATH:~/bin\n"
    assert not lnux._tirar_do_rc(rc, "starship")


@caso("Serviços: lê a lista do systemctl e do rc-status (OpenRC)")
def _():
    systemd = ("  cron.service       loaded active   running Regular background program processing daemon\n"
               "● nginx.service      loaded failed   failed  A high performance web server\n"
               "  ssh.service        loaded inactive dead    OpenBSD Secure Shell server\n")
    lista = lnux.parse_systemctl(systemd)
    assert [s["nome"] for s in lista] == ["cron.service", "nginx.service", "ssh.service"]
    assert lista[1]["ativo"] == "failed" and lista[0]["descricao"].startswith("Regular")
    openrc = ("Runlevel: default\n crond                                [  started  ]\n"
              " sshd                                 [  stopped  ]\n")
    rc = lnux.parse_rc_status(openrc)
    assert [(s["nome"], s["ativo"]) for s in rc] == [("crond", "active"), ("sshd", "inactive")]


# ── servidor de pasta com envio ──────────────────────────────────────

def servidor(permitir_envio: bool, senha: str = ""):
    raiz = Path(tempfile.mkdtemp(prefix="lnux-pasta-"))
    (raiz / "musica.mp3").write_bytes(bytes(range(256)) * 40)
    (raiz / ".segredo").write_text("não pode")
    (raiz / "sub").mkdir()
    s = lnux.ServidorDePasta(("127.0.0.1", 0), raiz, permitir_envio, senha)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, raiz, f"http://127.0.0.1:{s.server_address[1]}"


def pedido(url: str, metodo: str = "GET", corpo: bytes | None = None, cabecalhos: dict | None = None):
    req = urllib.request.Request(url, data=corpo, method=metodo, headers=cabecalhos or {})
    abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with abridor.open(req, timeout=10) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


@caso("Pasta: lista, baixa, baixa um pedaço (Range) e esconde os arquivos ocultos")
def _():
    s, raiz, url = servidor(permitir_envio=False)
    try:
        status, corpo, _ = pedido(url + "/")
        assert status == 200 and b"musica.mp3" in corpo and b".segredo" not in corpo and b"Mandar arquivos" not in corpo
        status, corpo, _ = pedido(url + "/musica.mp3")
        assert status == 200 and corpo == (raiz / "musica.mp3").read_bytes()
        status, corpo, cab = pedido(url + "/musica.mp3", cabecalhos={"Range": "bytes=10-19"})
        assert status == 206 and corpo == bytes(range(10, 20)) and cab["Content-Range"].startswith("bytes 10-19/")
        assert pedido(url + "/.segredo")[0] == 404
        assert pedido(url + "/sub")[0] in (200, 301)
    finally:
        s.shutdown()


@caso("Pasta: não deixa sair da pasta (.., %2e%2e, atalho para fora)")
def _():
    s, raiz, url = servidor(permitir_envio=True)
    try:
        os.symlink("/etc", raiz / "fora")
        for caminho in ("/../../etc/passwd", "/%2e%2e/%2e%2e/etc/passwd", "/fora/passwd", "/sub/../../etc/hostname"):
            status, corpo, _ = pedido(url + caminho)
            assert status == 404 and b"root:" not in corpo, caminho
        assert pedido(url + "/%2e%2e/escapou.txt", "PUT", b"x")[0] == 400
        assert not (raiz.parent / "escapou.txt").exists()
    finally:
        s.shutdown()


@caso("Pasta: envio pelo navegador (PUT), sem sobrescrever, e desligado quando pedido")
def _():
    s, raiz, url = servidor(permitir_envio=True)
    try:
        status, corpo, _ = pedido(url + "/")
        assert b"Mandar arquivos" in corpo
        assert pedido(url + "/foto%20nova.jpg", "PUT", b"primeira")[0] == 201
        assert pedido(url + "/foto%20nova.jpg", "PUT", b"segunda")[0] == 201
        assert (raiz / "foto nova.jpg").read_bytes() == b"primeira"
        assert (raiz / "foto nova (2).jpg").read_bytes() == b"segunda"
        assert pedido(url + "/sub/dentro.txt", "PUT", b"ok")[0] == 201 and (raiz / "sub" / "dentro.txt").exists()
        assert pedido(url + "/.escondido", "PUT", b"x")[0] == 400
    finally:
        s.shutdown()
    s, raiz, url = servidor(permitir_envio=False)
    try:
        assert pedido(url + "/x.txt", "PUT", b"x")[0] == 403 and not (raiz / "x.txt").exists()
    finally:
        s.shutdown()


@caso("Pasta: com senha, pede login e aceita só a senha certa")
def _():
    s, _, url = servidor(permitir_envio=False, senha="abacaxi")
    try:
        status, _, cab = pedido(url + "/")
        assert status == 401 and "Basic" in cab.get("WWW-Authenticate", "")
        errada = "Basic " + base64.b64encode(b"x:banana").decode()
        certa = "Basic " + base64.b64encode(b"qualquer:abacaxi").decode()
        assert pedido(url + "/", cabecalhos={"Authorization": errada})[0] == 401
        assert pedido(url + "/", cabecalhos={"Authorization": certa})[0] == 200
    finally:
        s.shutdown()


# ── rede ─────────────────────────────────────────────────────────────

@caso("Ping: lê o tempo do Linux, do Android, do BusyBox e respostas sem tempo")
def _():
    assert lnux.parse_ping("64 bytes from 1.1.1.1: icmp_seq=1 ttl=57 time=12.3 ms") == 12.3
    assert lnux.parse_ping("64 bytes from 8.8.8.8: seq=0 ttl=117 time=9,8 ms") == 9.8
    assert lnux.parse_ping("Reply from 192.168.0.1: bytes=32 time<1 ms TTL=64") == 1.0
    assert lnux.parse_ping("1 packets transmitted, 0 received, 100% packet loss") is None


@caso("API HTTP: GET e POST num servidor local, JSON colorido e o comando curl")
def _():
    s, raiz, url = servidor(permitir_envio=True)
    try:
        (raiz / "dados.json").write_text('{"nome": "LNUX", "versao": 2, "ok": true, "lista": [1, null]}')
        r = lnux.requisicao_http("GET", url + "/dados.json")
        assert r["status"] == 200 and json.loads(r["corpo"])["nome"] == "LNUX"
        assert lnux.requisicao_http("GET", url + "/nao-existe")["status"] == 404
        r = lnux.requisicao_http("PUT", url + "/novo.json", {"Content-Type": "application/json"}, b'{"a": 1}')
        assert r["status"] == 201
        colorido = lnux.colorir_json(json.dumps(json.loads((raiz / "dados.json").read_text()), indent=2))
        assert json.loads(lnux._sem_ansi(colorido))["versao"] == 2 and "\033[" in colorido or not lnux._COR
        curl = lnux.como_curl("POST", "https://x.y/api", {"Authorization": "Bearer t"}, '{"a": 1}')
        assert curl == """curl -i -X POST -H 'Authorization: Bearer t' --data '{"a": 1}' https://x.y/api"""
    finally:
        s.shutdown()


@caso("JSON: filhos, resumo e caminho no estilo do jq; Markdown sem o rich")
def _():
    dados = {"usuarios": [{"nome": "Ana", "idade": 30}], "total": 1, "meta-dados": {}}
    filhos = lnux.json_filhos(dados)
    assert [k for _, k, _ in filhos] == ["usuarios", "total", "meta-dados"]
    assert lnux.json_resumo(dados["usuarios"]) == "[…] 1 item(ns)" and lnux.json_resumo("x" * 100).endswith("…")
    assert lnux.json_caminho(["usuarios", 0, "nome"]) == ".usuarios[0].nome"
    assert lnux.json_caminho(["meta-dados"]) == '["meta-dados"]' and lnux.json_caminho([]) == "."
    linhas = [lnux._sem_ansi(l) for l in lnux.markdown_simples("# Título\n- item **forte**\n```\ncodigo\n```\n> nota")]
    assert "TÍTULO" in linhas and "• item forte" in linhas and "  codigo" in linhas and "│ nota" in linhas


@caso("Contêineres: lê a lista do podman (JSON) e do docker (uma linha por contêiner)")
def _():
    podman = '[{"Id": "abc123def4567890", "Names": ["web"], "Image": "nginx", "State": "running", "Status": "Up 2h"}]'
    docker = ('{"ID":"f00baa","Names":"banco","Image":"postgres:16","State":"exited","Status":"Exited (0) 3 days ago"}\n'
              '{"ID":"c0ffee","Names":"cache","Image":"redis","State":"running","Status":"Up 5 min"}')
    a = [lnux.normalizar_conteiner(c) for c in lnux.parse_lista_json(podman)]
    b = [lnux.normalizar_conteiner(c) for c in lnux.parse_lista_json(docker)]
    assert a == [{"id": "abc123def456", "nome": "web", "imagem": "nginx", "estado": "running", "status": "Up 2h",
                  "rodando": True}]
    assert [c["nome"] for c in b] == ["banco", "cache"] and [c["rodando"] for c in b] == [False, True]
    assert lnux.parse_lista_json("  ") == []


# ── tldr ─────────────────────────────────────────────────────────────

@caso("tldr: mostra a página em português quando existe e cai no inglês quando não")
def _():
    base = TMP / "tldr"
    for idioma, texto in (("pages.pt_BR", "# tar\n\n> Arquivador.\n\n- Criar um arquivo:\n\n`tar cf {{alvo.tar}} {{arquivos}}`\n"),
                          ("pages", "# tar\n\n> Archiving utility.\n")):
        (base / idioma / "common").mkdir(parents=True, exist_ok=True)
        (base / idioma / "common" / "tar.md").write_text(texto)
    (base / "pages" / "linux").mkdir(parents=True)
    (base / "pages" / "linux" / "apt.md").write_text("# apt\n\n> Package manager.\n")
    assert "pages.pt_BR" in str(lnux.tldr_achar("tar", base)) and "pages/linux" in str(lnux.tldr_achar("APT", base))
    assert lnux.tldr_achar("nao-existe", base) is None and lnux.tldr_nomes(base) == ["apt", "tar"]
    linhas = [lnux._sem_ansi(l) for l in lnux.tldr_renderizar((base / "pages.pt_BR/common/tar.md").read_text())]
    assert linhas[0] == "tar" and "Arquivador." in linhas and "• Criar um arquivo:" in linhas
    assert "    tar cf alvo.tar arquivos" in linhas


# ── 2FA ──────────────────────────────────────────────────────────────

@caso("2FA: HOTP com os vetores da RFC 4226")
def _():
    esperado = ["755224", "287082", "359152", "969429", "338314", "254676", "287922", "162583", "399871", "520489"]
    assert [lnux.hotp(b"12345678901234567890", i) for i in range(10)] == esperado


@caso("2FA: TOTP com os vetores da RFC 6238 (SHA-1, SHA-256 e SHA-512, 8 dígitos)")
def _():
    segredos = {"sha1": b"12345678901234567890", "sha256": b"12345678901234567890123456789012",
                "sha512": b"1234567890123456789012345678901234567890123456789012345678901234"}
    vetores = {59: ("94287082", "46119246", "90693936"), 1111111109: ("07081804", "68084774", "25091201"),
               1234567890: ("89005924", "91819424", "93441116"), 2000000000: ("69279037", "90698825", "38618901"),
               20000000000: ("65353130", "77737706", "47863826")}
    for instante, codigos in vetores.items():
        for (algoritmo, segredo), codigo in zip(segredos.items(), codigos):
            b32 = base64.b32encode(segredo).decode()
            assert lnux.totp(b32, instante, 8, 30, algoritmo) == codigo, (instante, algoritmo)


@caso("2FA: lê e monta o link otpauth:// do QR code; recusa chave inválida")
def _():
    uri = "otpauth://totp/GitHub:ana%40exemplo.com?secret=JBSWY3DPEHPK3PXP&issuer=GitHub&period=30"
    conta = lnux.ler_otpauth(uri)
    assert conta == {"emissor": "GitHub", "conta": "ana@exemplo.com", "segredo": "JBSWY3DPEHPK3PXP", "digitos": 6,
                     "periodo": 30, "algoritmo": "sha1"}
    assert lnux.ler_otpauth(lnux.montar_otpauth(conta)) == conta
    for ruim in ("https://github.com", "otpauth://totp/x?issuer=y", "otpauth://totp/x?secret=1111"):
        try:
            lnux.ler_otpauth(ruim)
        except lnux.LnuxError:
            continue
        raise AssertionError(ruim)


# ── letra, digitação e cotações ──────────────────────────────────────

@caso("Letra: lê o formato LRC (vários tempos por verso) e acha o verso do momento")
def _():
    lrc = "[ar:Artista]\n[00:12.50]Primeiro verso\n[00:15.00][01:15.00]Refrão\n[00:20.123]Terceiro\n[00:25]\n"
    versos = lnux.parse_lrc(lrc)
    assert [v for _, v in versos] == ["Primeiro verso", "Refrão", "Terceiro", "", "Refrão"]
    assert versos[0][0] == 12.5 and abs(versos[2][0] - 20.123) < 1e-9 and versos[-1][0] == 75.0
    assert [lnux.verso_atual(versos, t) for t in (0, 12.5, 16, 70, 999)] == [-1, 0, 1, 3, 4]
    faixa = {"titulo": "Garota de Ipanema (Official Video)", "subtitulo": "Tom Jobim · Getz/Gilberto"}
    assert lnux._artista_e_musica(faixa) == ("Tom Jobim", "Garota de Ipanema")
    assert lnux._artista_e_musica({"titulo": "Djavan - Oceano", "subtitulo": ""}) == ("Djavan", "Oceano")


@caso("Digitação: palavras por minuto, precisão e quebra de linha com cores")
def _():
    alvo = "casa azul " * 6  # 60 caracteres
    r = lnux.resultado_digitacao(alvo, alvo, 60, 62, 2)
    assert r["ppm"] == 12.0 and r["precisao"] == round(100 * 60 / 62, 1)
    r = lnux.resultado_digitacao("abcde", "abxde", 6, 5, 1)
    assert r["certos"] == 4 and r["ppm"] == 8.0
    a, b = lnux.texto_para_digitar(30, semente=7), lnux.texto_para_digitar(30, semente=7)
    assert a == b and len(a.split()) == 30
    assert lnux.texto_para_digitar(30, sem_acentos=True, semente=1).isascii()
    linhas = lnux.quebrar_colorido("um dois tres quatro", [f"<{c}>" for c in "um dois tres quatro"], 9)
    assert ["".join(l[1] for l in linha.split(">") if l) for linha in linhas] == ["um dois ", "tres ", "quatro"]


@caso("Cotações: lê o mercado do CoinGecko e o gráfico do Yahoo Finance")
def _():
    mercado = [{"id": "bitcoin", "name": "Bitcoin", "symbol": "btc", "current_price": 350000.5,
                "price_change_percentage_24h": -1.5, "sparkline_in_7d": {"price": [1, 2, 3]}}]
    assert lnux.parse_mercado_cripto(mercado)[0] == {"id": "bitcoin", "nome": "Bitcoin", "simbolo": "BTC",
                                                     "preco": 350000.5, "variacao_24h": -1.5, "grafico_7d": [1, 2, 3]}
    yahoo = {"chart": {"result": [{"meta": {"symbol": "PETR4.SA", "shortName": "PETROBRAS PN", "currency": "BRL",
                                            "regularMarketPrice": 38.2, "chartPreviousClose": 37.9},
                                   "indicators": {"quote": [{"close": [37.0, None, 38.2]}]}}]}}
    a = lnux.parse_yahoo(yahoo)
    assert a["nome"] == "PETROBRAS PN" and a["preco"] == 38.2 and a["fechamentos"] == [37.0, 38.2]
    try:
        lnux.parse_yahoo({"chart": {"result": None, "error": {"code": "Not Found"}}})
    except lnux.LnuxError:
        pass
    else:
        raise AssertionError("código inexistente deveria dar erro")


# ── telas de descanso ────────────────────────────────────────────────

@caso("Telas de descanso: cada quadro ocupa a tela certinho (linhas e colunas)")
def _():
    for classe in (lnux.ChuvaMatrix, lnux.Canos, lnux.Aquario):
        animacao = classe(50, 15, semente=3)
        for _ in range(60):
            animacao.passo()
        quadro = animacao.quadro()
        assert len(quadro) == 15, classe.__name__
        larguras = {visivel(l) for l in quadro}
        assert max(larguras) <= 50, (classe.__name__, larguras)
    canos = lnux.Canos(30, 10, semente=1)
    for _ in range(200):
        canos.passo()
    desenho = "".join(lnux._sem_ansi(l) for l in canos.quadro())
    assert set(desenho) - set(" ━┃┏┓┗┛") == set(), set(desenho)


if __name__ == "__main__":
    print(f"\n{resultados['ok']} ok · {resultados['falhou']} falharam")
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if resultados["falhou"] else 0)
