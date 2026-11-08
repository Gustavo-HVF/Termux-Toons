#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testa cada técnica de 🕵️ Mensagens secretas: codificar e decodificar tem que devolver a mensagem original,
e os casos errados (senha errada, nada escondido, mensagem que não cabe) têm que dar um erro claro.

Uso:
    python3 tests/testar_mensagens_secretas.py

Usa uma pasta temporária (a sua configuração não é tocada). As partes que precisam do Pillow (foto),
da biblioteca cryptography (AES) ou do comando openssl são puladas, com aviso, se eles não existirem.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
import traceback
import wave
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
os.environ["HOME"] = tempfile.mkdtemp(prefix="lnux-teste-")
sys.path.insert(0, str(RAIZ))
import lnux  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="lnux-segredos-"))
MENSAGENS = ["Ataque ao amanhecer!", "Olá, coração: ação às 7h30 — ônibus nº 42?", "a", "ZzYy 123 xyz",
             "emoji 🕵️ e 中文 também"]
resultados = {"ok": 0, "falhou": 0, "pulado": 0}


def caso(nome: str):
    """Decorador: roda o teste, conta e mostra o resultado."""
    def registrar(func):
        try:
            func()
        except Pulado as e:
            resultados["pulado"] += 1
            print(f"  ⏭  {nome}: pulado ({e})")
        except Exception:  # noqa: BLE001
            resultados["falhou"] += 1
            print(f"  ✖ {nome}\n{traceback.format_exc(limit=3)}")
        else:
            resultados["ok"] += 1
            print(f"  ✔ {nome}")
        return func
    return registrar


class Pulado(Exception):
    pass


def exige_modulo(nome: str):
    if importlib.util.find_spec(nome) is None:
        raise Pulado(f"sem o módulo {nome}")


def espera_erro(funcao, *args, contem: str = ""):
    try:
        funcao(*args)
    except lnux.LnuxError as e:
        assert contem.lower() in str(e).lower(), f"erro diferente do esperado: {e}"
        return
    raise AssertionError(f"{funcao.__name__} deveria ter dado erro")


# ── cifras clássicas ─────────────────────────────────────────────────

@caso("César: exemplo clássico e ida e volta com vários deslocamentos")
def _():
    assert lnux.cifra_cesar("abc xyz", 3) == "def abc"
    assert lnux.cifra_cesar("Ataque", 3) == "Dwdtxh"
    for k in (1, 3, 13, 25, -7):
        for m in MENSAGENS:
            assert lnux.cifra_cesar(lnux.cifra_cesar(m, k), -k) == m


@caso("César: descobrir sem a chave acha o deslocamento certo")
def _():
    original = "a reuniao sera amanha no lugar de sempre depois da escola"
    melhor_k, melhor_texto = lnux.cesar_quebrar(lnux.cifra_cesar(original, 11))[0]
    assert melhor_k == 11 and melhor_texto == original, (melhor_k, melhor_texto)


@caso("ROT13, ROT47 e Atbash se desfazem aplicando de novo")
def _():
    assert lnux.cifra_cesar("Hello", 13) == "Uryyb"
    assert lnux.rot47("Hello, World!") == "w6==@[ (@C=5P"
    assert lnux.atbash("abc XYZ") == "zyx CBA"
    for m in MENSAGENS:
        assert lnux.cifra_cesar(lnux.cifra_cesar(m, 13), 13) == m
        assert lnux.rot47(lnux.rot47(m)) == m
        assert lnux.atbash(lnux.atbash(m)) == m


@caso("Vigenère: exemplo da literatura e ida e volta")
def _():
    assert lnux.cifra_vigenere("ATTACKATDAWN", "LEMON") == "LXFOPVEFRNHR"
    for m in MENSAGENS:
        assert lnux.cifra_vigenere(lnux.cifra_vigenere(m, "Segredo"), "Segredo", decifrar=True) == m
    espera_erro(lnux.cifra_vigenere, "abc", "123", contem="letra")


@caso("Substituição com palavra-chave")
def _():
    assert lnux.alfabeto_com_palavra("lnux") == "lnuxabcdefghijkmopqrstvwyz"
    assert lnux.cifra_substituicao("abc", "lnux") == "lnu"
    for m in MENSAGENS:
        assert lnux.cifra_substituicao(lnux.cifra_substituicao(m, "zebra"), "zebra", decifrar=True) == m


@caso("Cerca de trilhos: exemplo clássico e ida e volta com 2 a 6 trilhos")
def _():
    assert lnux.cerca_codificar("WEAREDISCOVEREDFLEEATONCE", 3) == "WECRLTEERDSOEEFEAOCAIVDEN"
    for n in range(2, 7):
        for m in MENSAGENS:
            assert lnux.cerca_decodificar(lnux.cerca_codificar(m, n), n) == m


@caso("Políbio, Bacon e A1Z26 (só letras, sem acento)")
def _():
    assert lnux.polibio_codificar("abc") == "11 12 13"
    assert lnux.bacon_codificar("ab") == "AAAAA AAAAB"
    assert lnux.a1z26_codificar("abc xyz") == "1-2-3 24-25-26"
    for m in ("ataque ao amanhecer", "codigo secreto", "xyz"):
        assert lnux.polibio_decodificar(lnux.polibio_codificar(m)) == m
        assert lnux.bacon_decodificar(lnux.bacon_codificar(m)) == m
        assert lnux.a1z26_decodificar(lnux.a1z26_codificar(m)) == m
    assert lnux.polibio_decodificar(lnux.polibio_codificar("jogo")) == "iogo"  # o j divide a casa com o i


# ── códigos ──────────────────────────────────────────────────────────

@caso("Morse: SOS, frase com números e o som em WAV")
def _():
    assert lnux.morse_codificar("SOS") == "... --- ..."
    assert lnux.morse_decodificar("... --- ... / ... --- ...") == "sos sos"
    assert lnux.morse_decodificar(lnux.morse_codificar("Encontro as 19h, ok?")) == "encontro as 19h, ok?"
    assert lnux.morse_decodificar("·– ·") == "ae"  # ponto e travessão de celular também valem
    arq = lnux.morse_som("... --- ...", TMP / "sos.wav")
    with wave.open(str(arq)) as w:
        assert w.getnframes() > 0 and w.getsampwidth() == 2


@caso("Braille: letras, acentos, números e maiúsculas")
def _():
    assert lnux.braille_codificar("abc") == "⠁⠃⠉"
    assert lnux.braille_codificar("12") == "⠼⠁⠃"
    for m in ("Olá, coração", "Rua 25 de Março, 123", "ação é já!"):
        assert lnux.braille_decodificar(lnux.braille_codificar(m)) == m, m


@caso("Base64 e Base32 (com acentos e emoji)")
def _():
    assert lnux.base64_codificar("Olá") == "T2zDoQ=="
    for m in MENSAGENS:
        assert lnux.base64_decodificar(lnux.base64_codificar(m)) == m
        assert lnux.base32_decodificar(lnux.base32_codificar(m)) == m
    assert lnux.base64_decodificar("T2zDoQ") == "Olá"  # sem o '=' do fim também vale
    assert lnux.base64_decodificar(lnux.base64.urlsafe_b64encode("ação?>".encode()).decode()) == "ação?>"
    espera_erro(lnux.base64_decodificar, "@@@", contem="base64")


# ── sistemas numéricos ───────────────────────────────────────────────

@caso("Números: 255 em todas as bases e a volta, com prefixos e negativos")
def _():
    assert [lnux.numero_na_base(255, b) for b in (2, 8, 10, 16, 36)] == ["11111111", "377", "255", "ff", "73"]
    assert lnux.ler_numero_na_base("0xFF", 16) == 255 and lnux.ler_numero_na_base("1111 1111", 2) == 255
    assert lnux.ler_numero_na_base("-0b101", 2) == -5 and lnux.numero_na_base(-5, 2) == "-101"
    assert lnux.ler_numero_na_base("0", 8) == 0 and lnux.numero_na_base(0, 16) == "0"
    espera_erro(lnux.ler_numero_na_base, "102", 2, contem="não é um número válido")


@caso("Texto ↔ binário, octal, decimal e hexadecimal (UTF-8)")
def _():
    assert lnux.texto_para_base("A", 2) == "01000001"
    assert lnux.texto_para_base("Hi", 16) == "48 69"
    assert lnux.texto_para_base("é", 10) == "195 169"  # acento: dois bytes no UTF-8
    for base in (2, 8, 10, 16):
        for m in MENSAGENS:
            assert lnux.base_para_texto(lnux.texto_para_base(m, base), base) == m
    assert lnux.base_para_texto("0100100001101001", 2) == "Hi"  # tudo junto
    assert lnux.base_para_texto("4869", 16) == "Hi"
    espera_erro(lnux.base_para_texto, "999", 10, contem="não formam")


# ── criptografia moderna ─────────────────────────────────────────────

@caso("AES-256-GCM: texto, senha errada, mensagem alterada e arquivo")
def _():
    exige_modulo("cryptography")
    for m in MENSAGENS:
        cifrado = lnux.aes_cifrar_texto(m, "uma senha bem longa")
        assert cifrado.startswith(lnux.PREFIXO_AES)
        assert lnux.aes_decifrar_texto(cifrado, "uma senha bem longa") == m
    a, b = lnux.aes_cifrar_texto("igual", "x" * 10), lnux.aes_cifrar_texto("igual", "x" * 10)
    assert a != b  # sal e nonce novos a cada vez
    espera_erro(lnux.aes_decifrar_texto, a, "senha errada", contem="senha errada")
    pacote = bytearray(lnux.base64.b64decode(a[len(lnux.PREFIXO_AES):]))
    pacote[-1] ^= 1  # muda um bit da mensagem cifrada
    adulterado = lnux.PREFIXO_AES + lnux.base64.b64encode(bytes(pacote)).decode()
    espera_erro(lnux.aes_decifrar_texto, adulterado, "x" * 10, contem="alterada")
    original = TMP / "contrato.pdf"
    original.write_bytes(os.urandom(50_000))
    cifrado_arq = lnux.aes_cifrar_arquivo(original, "senha-do-arquivo")
    assert cifrado_arq.name == "contrato.pdf.lnuxcripto"
    aberto = lnux.aes_decifrar_arquivo(cifrado_arq, "senha-do-arquivo", TMP / "aberto.pdf")
    assert aberto.read_bytes() == original.read_bytes()
    espera_erro(lnux.aes_decifrar_arquivo, cifrado_arq, "outra", contem="senha errada")


@caso("OpenSSL: o LNUX cifra e o próprio comando openssl abre (e o contrário)")
def _():
    if not shutil.which("openssl"):
        raise Pulado("sem o comando openssl")
    import subprocess
    m = "Encontro às 19h na praça"
    cifrado = lnux.openssl_cifrar(m, "senha-openssl")
    proc = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "600000", "-a", "-A",
                           "-pass", "pass:senha-openssl"], input=(cifrado + "\n").encode(), capture_output=True)
    assert proc.stdout.decode() == m, proc.stderr
    vindo = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "600000", "-salt", "-a", "-A",
                            "-pass", "pass:outra"], input=m.encode(), capture_output=True).stdout.decode()
    assert lnux.openssl_decifrar(vindo, "outra") == m
    espera_erro(lnux.openssl_decifrar, vindo, "errada", contem="senha")


@caso("Vernam: ida e volta, chave do tamanho certo e chave errada")
def _():
    for m in MENSAGENS:
        cifrado, chave = lnux.vernam_cifrar(m)
        assert lnux.vernam_decifrar(cifrado, chave) == m
        assert len(lnux.base64.b64decode(chave)) == len(m.encode())
    cifrado, _ = lnux.vernam_cifrar("segredo")
    espera_erro(lnux.vernam_decifrar, cifrado, lnux.base64.b64encode(b"ab").decode(), contem="menor")


# ── esteganografia ───────────────────────────────────────────────────

def foto_de_teste(nome: str, modo: str = "RGB", tamanho=(120, 90)) -> Path:
    from PIL import Image
    img = Image.new(modo, tamanho)
    img.putdata([((x * 7) % 256, (y * 5) % 256, (x * y) % 256, 255)[:len(modo)]
                 for y in range(tamanho[1]) for x in range(tamanho[0])])
    caminho = TMP / nome
    img.save(caminho)
    return caminho


@caso("Foto (PNG): esconde e revela, com e sem senha, de JPG e de PNG com transparência")
def _():
    exige_modulo("PIL")
    from PIL import Image
    for origem in (foto_de_teste("praia.jpg"), foto_de_teste("logo.png", "RGBA")):
        for m in MENSAGENS:
            destino = lnux.imagem_esconder(origem, m.encode(), TMP / f"{origem.stem}_secreta.png")
            dados, cifrado = lnux.imagem_revelar(destino)
            assert dados.decode() == m and not cifrado
        antes, depois = Image.open(origem).convert("RGB"), Image.open(destino).convert("RGB")
        diferenca = max(abs(a - b) for a, b in zip(antes.tobytes(), depois.tobytes()))
        assert diferenca <= 1 or origem.suffix == ".jpg", diferenca  # só o último bit muda
    exige_modulo("cryptography")
    destino = lnux.imagem_esconder(TMP / "logo.png", lnux.aes_cifrar_bytes(b"com senha", "abc12345"),
                                   TMP / "logo_cifrada.png", cifrado=True)
    dados, cifrado = lnux.imagem_revelar(destino)
    assert cifrado and lnux.aes_decifrar_bytes(dados, "abc12345") == b"com senha"


@caso("Foto: erro claro quando não cabe e quando não há nada escondido")
def _():
    exige_modulo("PIL")
    pequena = foto_de_teste("mini.png", tamanho=(8, 8))
    espera_erro(lnux.imagem_esconder, pequena, b"x" * 100, TMP / "x.png", contem="não cabe")
    espera_erro(lnux.imagem_revelar, foto_de_teste("normal.png"), contem="não há mensagem")


@caso("Áudio (WAV de 16 bits): esconde, revela e quase não muda o som")
def _():
    import math
    import struct
    origem = TMP / "musica.wav"
    with wave.open(str(origem), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"".join(struct.pack("<hh", int(8000 * math.sin(i / 20)), int(8000 * math.cos(i / 30)))
                               for i in range(44100)))
    for m in MENSAGENS:
        destino = lnux.audio_esconder(origem, m.encode(), TMP / "musica_secreta.wav")
        dados, cifrado = lnux.audio_revelar(destino)
        assert dados.decode() == m and not cifrado
    with wave.open(str(origem)) as a, wave.open(str(destino)) as b:
        amostras_a = struct.unpack(f"<{a.getnframes() * 2}h", a.readframes(a.getnframes()))
        amostras_b = struct.unpack(f"<{b.getnframes() * 2}h", b.readframes(b.getnframes()))
    assert max(abs(x - y) for x, y in zip(amostras_a, amostras_b)) <= 1
    espera_erro(lnux.audio_revelar, origem, contem="não há mensagem")


@caso("Texto invisível: esconde depois da 1ª letra, revela e some ao limpar")
def _():
    for m in MENSAGENS:
        com_segredo = lnux.invisivel_esconder("Bom dia, pessoal!", m.encode())
        assert lnux.tirar_invisiveis(com_segredo) == "Bom dia, pessoal!"
        dados, cifrado = lnux.invisivel_revelar(com_segredo)
        assert dados.decode() == m and not cifrado
    espera_erro(lnux.invisivel_revelar, "Bom dia, pessoal!", contem="invisível")
    so_segredo = lnux.invisivel_esconder("", b"capa vazia")
    assert lnux.invisivel_revelar(so_segredo)[0] == b"capa vazia"


@caso("Arquivo dentro de foto: a foto continua abrindo e o arquivo volta inteiro (com e sem senha)")
def _():
    exige_modulo("PIL")
    from PIL import Image
    foto = foto_de_teste("ferias.jpg")
    segredo = TMP / "planos.zip"
    segredo.write_bytes(os.urandom(30_000))
    destino = lnux.anexar_arquivo(foto, segredo, TMP / "ferias_com_anexo.jpg")
    Image.open(destino).load()  # a foto continua uma foto válida
    nome, conteudo, cifrado = lnux.extrair_anexo(destino)
    assert nome == "planos.zip" and conteudo == segredo.read_bytes() and not cifrado
    exige_modulo("cryptography")
    destino = lnux.anexar_arquivo(foto, segredo, TMP / "ferias_cifrada.jpg", senha="senha do zip")
    nome, conteudo, cifrado = lnux.extrair_anexo(destino)
    assert cifrado and lnux.aes_decifrar_bytes(conteudo, "senha do zip") == segredo.read_bytes()
    espera_erro(lnux.extrair_anexo, foto, contem="não tem um arquivo escondido")


# ── alfabetos próprios ───────────────────────────────────────────────

@caso("Alfabetos: os conjuntos prontos têm símbolos únicos e sem modificadores invisíveis")
def _():
    for nome, simbolos in lnux.CONJUNTOS_DE_SIMBOLOS.items():
        assert len(set(simbolos)) == len(simbolos), f"{nome}: símbolo repetido"
        assert len(simbolos) >= 26, f"{nome}: só {len(simbolos)} símbolos"
        assert not any(c in simbolos for c in "️‍"), f"{nome}: tem modificador invisível"


@caso("Alfabetos: gerar, codificar e decodificar (acentos viram a letra simples)")
def _():
    for nome, simbolos in lnux.CONJUNTOS_DE_SIMBOLOS.items():
        mapa = lnux.alfabeto_gerado(simbolos, embaralhar=True)
        lnux.validar_alfabeto(mapa)
        m = "encontro as 19h no lugar de sempre!"
        assert lnux.alfabeto_decodificar(lnux.alfabeto_codificar(m, mapa), mapa) == m, nome
    mapa = lnux.alfabeto_gerado(lnux.CONJUNTOS_DE_SIMBOLOS["Emojis"])
    assert lnux.alfabeto_decodificar(lnux.alfabeto_codificar("Ação", mapa), mapa) == "acao"


@caso("Alfabetos: símbolos de vários caracteres e a validação dos ambíguos")
def _():
    mapa = {"a": "<3", "b": "</3", "c": "XD"}
    lnux.validar_alfabeto(mapa)
    assert lnux.alfabeto_decodificar(lnux.alfabeto_codificar("abc cab", mapa), mapa) == "abc cab"
    espera_erro(lnux.validar_alfabeto, {"a": "x", "b": "xy"}, contem="começo")
    espera_erro(lnux.validar_alfabeto, {"a": "*", "b": "*"}, contem="repetido")
    espera_erro(lnux.validar_alfabeto, {"a": "b"}, contem="não troca")
    espera_erro(lnux.validar_alfabeto, {"a": "a b"}, contem="espaço")


@caso("Alfabetos: mandar e receber pelo texto 'lnux-alfabeto:'")
def _():
    mapa = lnux.alfabeto_gerado(lnux.CONJUNTOS_DE_SIMBOLOS["Runas (Futhark antigo)"], embaralhar=True)
    texto = lnux.alfabeto_para_texto("runas do grupo", mapa)
    assert texto.startswith(lnux.PREFIXO_ALFABETO)
    nome, recebido = lnux.alfabeto_de_texto(texto)
    assert nome == "runas do grupo" and recebido == mapa
    espera_erro(lnux.alfabeto_de_texto, "lnux-alfabeto:quebrado", contem="incompleto")
    espera_erro(lnux.alfabeto_de_texto, "outra coisa", contem="começa com")


if __name__ == "__main__":
    print(f"\n{resultados['ok']} ok · {resultados['falhou']} falharam · {resultados['pulado']} pulados")
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if resultados["falhou"] else 0)
