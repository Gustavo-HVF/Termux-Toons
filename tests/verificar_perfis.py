#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificador dos perfis de sistema (distros/*.json).

Confere cada perfil contra o que o lnux.py usa (lido do código, sem executar nada):
  • campos obrigatórios, esquema, id igual ao nome do arquivo, ids sem repetição;
  • recursos conhecidos (a lista RECURSOS do lnux.py);
  • comandos do gerenciador de pacotes como listas de texto;
  • as pastas que o núcleo pede (downloads, musicas, videos...);
  • nos perfis Linux, TODO pacote que o código instala tem tradução explícita em "nomes" (o nome na distro,
    ou null se ela não tem) — é isso que diz a quem cria um perfil novo o que falta;
  • serviços (ssh, cron, mariadb, postgresql) para quem declara o recurso servicos_sistema.

Uso:
    python3 tests/verificar_perfis.py                    # todos os perfis de distros/
    python3 tests/verificar_perfis.py meu-perfil.json    # um perfil novo, antes de pôr na pasta

Sai com código 1 se achar algum problema.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LNUX = RAIZ / "lnux.py"
PASTA = RAIZ / "distros"

CAMPOS = ("esquema", "id", "nome", "familia", "recursos", "pacotes", "caminhos")
ACOES_PACOTES = ("instalar", "atualizar_indice", "atualizar_sistema", "limpar_cache", "remover_orfaos")
PASTAS = ("downloads", "musicas", "videos", "imagens", "dcim", "documentos", "capturas_de_tela", "compartilhado",
          "temporarios", "prefixo")
SERVICOS = ("ssh", "cron", "mariadb", "postgresql")
ACOES_SERVICOS = ("iniciar", "parar", "ligar_no_boot", "status")


def ler_codigo() -> tuple:
    """(recursos conhecidos, esquema, nomes de pacote que o código pede) a partir do lnux.py."""
    arvore = ast.parse(LNUX.read_text(encoding="utf-8"))
    recursos, esquema, pacotes = set(), None, set()

    def textos(nos):
        return [n.value for n in nos if isinstance(n, ast.Constant) and isinstance(n.value, str)]

    for n in ast.walk(arvore):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            alvo = n.targets[0].id
            if alvo == "RECURSOS" and isinstance(n.value, ast.Dict):
                recursos = set(textos(n.value.keys))
            elif alvo == "ESQUEMA_PERFIL" and isinstance(n.value, ast.Constant):
                esquema = n.value.value
            elif alvo == "FERRAMENTAS" and isinstance(n.value, ast.List):
                pacotes.update(el.elts[1].value for el in n.value.elts if isinstance(el, ast.Tuple))
            elif alvo == "PACOTES_DOS_EQUIVALENTES" and isinstance(n.value, ast.Dict):
                for v in n.value.values:
                    pacotes.update(textos([v.body, v.orelse]) if isinstance(v, ast.IfExp) else textos([v]))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            nome, args = n.func.id, textos(n.args)
            kw = {k.arg: k.value.value for k in n.keywords if isinstance(k.value, ast.Constant)}
            if nome in ("instalar_pkg", "instalar_de_repo"):
                for a in args:
                    pacotes.update(a.split())
            elif nome == "garantir_cmd":
                pacote = args[1] if len(args) > 1 else kw.get("pacote") or (args[0] if args else None)
                if pacote:
                    pacotes.update(pacote.split())
                if kw.get("repo"):
                    pacotes.add(kw["repo"])
            elif nome == "garantir_modulo" and kw.get("pkg_nome"):
                pacotes.add(kw["pkg_nome"])
            elif nome == "tem_recurso" or nome == "so_em":
                for a in args[:1]:
                    pacotes.update(p.split(":", 1)[1] for p in a.split("|") if p.strip().lstrip("!").startswith("pacote:"))
        if isinstance(n, ast.Tuple) and len(n.elts) == 2 and all(isinstance(e, ast.Constant) for e in n.elts):
            if n.elts[0].value == "yt-dlp" and str(n.elts[1].value).startswith("python-"):
                pacotes.add(n.elts[1].value)  # ("yt-dlp", "python-yt-dlp") em garantir_deps_musica
    return recursos, esquema, pacotes


def conferir(arq: Path, dados: dict, recursos: set, esquema: str, pacotes: set) -> list:
    erros = []
    faltam = [c for c in CAMPOS if c not in dados]
    if faltam:
        return [f"faltam os campos {', '.join(faltam)}"]
    if dados["esquema"] != esquema:
        erros.append(f"esquema '{dados['esquema']}' (o lnux.py lê '{esquema}')")
    if dados["id"] != arq.stem:
        erros.append(f"o id '{dados['id']}' não é o nome do arquivo ('{arq.stem}')")
    if dados["familia"] not in ("termux", "linux"):
        erros.append(f"familia '{dados['familia']}' (use 'termux' ou 'linux')")
    for r in set(dados["recursos"]) - recursos:
        erros.append(f"recurso desconhecido '{r}' (os que existem: {', '.join(sorted(recursos))})")
    pac = dados["pacotes"]
    for acao in ACOES_PACOTES:
        valor = pac.get(acao)
        if valor is not None and not (isinstance(valor, list) and all(isinstance(x, str) for x in valor)):
            erros.append(f"pacotes.{acao} precisa ser uma lista de textos ou null")
    if pac.get("instalar") is None and dados["id"] != "outro":
        erros.append("pacotes.instalar está vazio: o LNUX não vai conseguir instalar nada")
    for pasta in PASTAS:
        if pasta not in dados["caminhos"]:
            erros.append(f"caminhos.{pasta} não foi definido")
    for prefixo in dados.get("elevar") or []:
        if not (isinstance(prefixo, list) and prefixo and all(isinstance(x, str) for x in prefixo)):
            erros.append("cada item de 'elevar' precisa ser uma lista de textos, ex.: [\"sudo\"]")
    if dados["familia"] == "linux" and not dados.get("detectar") and dados["id"] != "outro":
        erros.append("sem regras em 'detectar' (os_release/comandos): o LNUX nunca vai sugerir este perfil")
    if dados["familia"] == "linux":
        nomes = pac.get("nomes") or {}
        for p in sorted(pacotes - set(nomes)):
            erros.append(f"pacotes.nomes não diz como se chama '{p}' nesta distro (use o nome ou null)")
        for p in pac.get("essenciais") or []:
            if p not in nomes:
                erros.append(f"o essencial '{p}' não está em pacotes.nomes")
            elif nomes[p] is None:
                erros.append(f"o essencial '{p}' está como null (não existe): tire de 'essenciais'")
        for nome_pip, valor in (pac.get("modulos_python") or {}).items():
            if not isinstance(valor, str):
                erros.append(f"modulos_python.{nome_pip} precisa ser o nome do pacote (texto)")
    if "servicos_sistema" in dados["recursos"]:
        servicos = dados.get("servicos") or {}
        for acao in ACOES_SERVICOS:
            modelo = (servicos.get("comandos") or {}).get(acao)
            if not (isinstance(modelo, list) and any("{servico}" in x for x in modelo)):
                erros.append(f"servicos.comandos.{acao} precisa ser uma lista com '{{servico}}' no lugar do nome")
        for chave in SERVICOS:
            if not (servicos.get("nomes") or {}).get(chave):
                erros.append(f"servicos.nomes.{chave} não foi definido (o nome do serviço nesta distro)")
    return erros


def main(argv: list) -> int:
    recursos, esquema, pacotes = ler_codigo()
    arquivos = [Path(a) for a in argv] or sorted(PASTA.glob("*.json"))
    ids, falhou = {}, False
    print(f"O lnux.py pede {len(pacotes)} pacotes e conhece {len(recursos)} recursos.")
    for arq in arquivos:
        try:
            dados = json.loads(arq.read_text("utf-8"))
        except (OSError, ValueError) as e:
            print(f"✖ {arq.name}: não é um JSON válido ({e})")
            falhou = True
            continue
        erros = conferir(arq, dados, recursos, esquema, pacotes)
        if dados.get("id") in ids:
            erros.append(f"id repetido (também em {ids[dados['id']]})")
        ids[dados.get("id")] = arq.name
        nomes = dados.get("pacotes", {}).get("nomes") or {}
        indisponiveis = sum(1 for v in nomes.values() if v is None)
        if erros:
            falhou = True
            print(f"✖ {arq.name}:")
            for e in erros:
                print(f"    • {e}")
        else:
            print(f"✔ {arq.name:<14} {dados['nome']:<20} {len(nomes):>3} pacotes traduzidos, "
                  f"{indisponiveis} sem equivalente na distro")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
