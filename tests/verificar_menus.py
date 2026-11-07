#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificador dos menus do programa (só lê o código, não executa nada).

Monta a árvore de menus a partir de `menu_principal` lendo o código-fonte (AST) e confere:

  1. Duplicatas: a mesma categoria/ação (função) aparecendo em menus diferentes.
  2. Busca: cada entrada do índice da 🔍 Busca (`_indice_busca`) aponta para algo que
     existe no menu, e o nome dela combina com o que a pessoa vai ver ao abrir.
  3. Menus que ninguém abre (funções com menu() fora da árvore).

Uso:
    python3 tests/verificar_menus.py              # confere o programa da pasta acima
    python3 tests/verificar_menus.py --arvore     # também imprime a árvore inteira
    python3 tests/verificar_menus.py caminho.py   # confere outro arquivo

Sai com código 1 se achar algum problema (bom para rodar antes de cada commit).
"""
from __future__ import annotations

import ast
import collections
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PADRAO = RAIZ / "termux_toons.py"

# Funções genéricas que podem aparecer em vários menus sem ser duplicata
# (cada chamada recebe argumentos diferentes: parar o serviço X, abrir o link Y...).
GENERICAS = {
    "parar_servico", "status_servico", "abrir_sessao", "rodar", "info", "ok", "instalar_pkg", "mostrar_dados",
    "_explicar", "_abrir_link_android", "_testar_aparelho", "_usar_rede_privada", "usar_saida_no_proxy",
    "abrir_tunel", "abrir_link",
}

# Funções que abrem um menu mas são chamadas de outro jeito (dinâmico), não por um item de menu.
ABERTAS_DE_OUTRO_JEITO = {"_menu_ponte_publica", "_menu_categoria_adb", "_md_menu_grupo", "abrir_banco"}

STOP = {"de", "da", "do", "das", "dos", "e", "ou", "no", "na", "nos", "nas", "os", "as", "um", "uma", "por",
        "com", "para", "pelo", "pela", "sem", "seu", "sua", "meu", "minha", "the", "a", "o", "em", "ao"}


def normalizar(texto: str) -> set:
    """Palavras significativas de um rótulo, sem acento e em minúsculas."""
    sem = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return {p for p in re.findall(r"[a-z0-9]+", sem) if len(p) >= 3 and p not in STOP}


def emoji_inicial(texto: str) -> str:
    texto = texto.strip()
    return texto[0] if texto and not texto[0].isascii() else ""


class Leitor:
    """Lê o arquivo e entende os menus declarados com menu(...) e grupo(...)."""

    def __init__(self, caminho: Path):
        self.arvore_ast = ast.parse(caminho.read_text(encoding="utf-8"))
        self.funcoes = {n.name: n for n in self.arvore_ast.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.modulo = set(self.funcoes)

    # ── rótulos e alvos ──────────────────────────────────────────────
    @staticmethod
    def rotulo(no) -> str:
        """Texto do rótulo de um item (aceita string, f-string e lambda que devolve texto)."""
        if isinstance(no, ast.Lambda):
            no = no.body
        if isinstance(no, ast.Constant) and isinstance(no.value, str):
            return no.value
        if isinstance(no, ast.JoinedStr):
            return "".join(v.value for v in no.values if isinstance(v, ast.Constant))
        if isinstance(no, ast.BinOp):  # "texto" + algo
            return Leitor.rotulo(no.left)
        if isinstance(no, ast.IfExp):
            return Leitor.rotulo(no.body)
        return ast.unparse(no)[:60]

    def alvo(self, no):
        """('nome', direto?) da função que o item abre; None se não der para saber."""
        if isinstance(no, ast.Name):
            return no.id, True
        if isinstance(no, ast.Lambda) and isinstance(no.body, ast.Call) and isinstance(no.body.func, ast.Name):
            return no.body.func.id, False
        return None

    # ── listas de itens ──────────────────────────────────────────────
    def itens_da_lista(self, no, funcao) -> list:
        """Itens (rótulo_no, alvo_no) de uma lista de menu; resolve variáveis montadas na função."""
        if isinstance(no, ast.Name):  # menu("...", itens): junta o que foi atribuído/somado/anexado a 'itens'
            elementos = []
            for n in ast.walk(funcao):
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == no.id for t in n.targets):
                    elementos += self.itens_da_lista(n.value, funcao)
                elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id == no.id:
                    elementos += self.itens_da_lista(n.value, funcao)
                elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "append"
                      and isinstance(n.func.value, ast.Name) and n.func.value.id == no.id and n.args):
                    elementos += self.itens_da_lista(ast.List(elts=[n.args[0]]), funcao)
            return elementos
        if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Add):
            return self.itens_da_lista(no.left, funcao) + self.itens_da_lista(no.right, funcao)
        if not isinstance(no, (ast.List, ast.Tuple)):
            return []
        saida = []
        for el in no.elts:
            if isinstance(el, ast.Tuple) and len(el.elts) == 2:
                saida.append((el.elts[0], el.elts[1]))
            elif isinstance(el, ast.Starred) and isinstance(el.value, ast.Call):
                chamada = el.value
                if isinstance(chamada.func, ast.Name) and chamada.func.id == "itens_servico":
                    rot = Leitor.rotulo(chamada.args[1]) if len(chamada.args) > 1 else "serviço"
                    saida.append((ast.Constant(f"{rot}: iniciar / parar / status / sessão"), chamada.args[2]))
        return saida

    def menus_da_funcao(self, nome: str) -> list:
        """[(título, [(rótulo, alvo_no)])] das chamadas menu(...) dentro da função (sem as dos grupos)."""
        funcao = self.funcoes.get(nome)
        if funcao is None:
            return []
        achados = []
        for n in ast.walk(funcao):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)):
                continue
            if n.func.id == "menu" and len(n.args) >= 2:
                if self._dentro_de_grupo(funcao, n):
                    continue
                achados.append((Leitor.rotulo(n.args[0]), self.itens_da_lista(n.args[1], funcao)))
            elif n.func.id == "_menu_ponte_publica" and len(n.args) >= 2:
                # janela padrão das pontes públicas: as opções próprias de cada ponte vêm em extras=[...]
                extras = next((k.value for k in n.keywords if k.arg == "extras"), None)
                if extras is not None:
                    achados.append((Leitor.rotulo(n.args[1]), self.itens_da_lista(extras, funcao)))
        return achados

    @staticmethod
    def _dentro_de_grupo(funcao, alvo) -> bool:
        for n in ast.walk(funcao):
            if isinstance(n, ast.FunctionDef) and n is not funcao and n.name == "abrir":
                if any(m is alvo for m in ast.walk(n)):
                    return True
        return False


def montar_arvore(leitor: Leitor):
    """Percorre a partir de menu_principal. Devolve (nós, referências)."""
    nos = []                                      # (profundidade, caminho, rótulo, nome_alvo)
    referencias = collections.defaultdict(list)   # nome_função → [(menu onde aparece, rótulo)]
    visitados = set()

    def visitar_itens(titulo_menu: str, itens: list, funcao_dona: str, caminho: tuple, prof: int):
        funcao = leitor.funcoes[funcao_dona]
        locais = {n.name for n in ast.walk(funcao) if isinstance(n, ast.FunctionDef) and n is not funcao}
        for rot_no, alvo_no in itens:
            rot = Leitor.rotulo(rot_no)
            # grupo("Título", [...]) dentro do menu: um submenu sem função própria
            if isinstance(alvo_no, ast.Call) and isinstance(alvo_no.func, ast.Name) and alvo_no.func.id == "grupo":
                titulo_grupo = Leitor.rotulo(alvo_no.args[0])
                nos.append((prof, caminho, rot, f"grupo «{titulo_grupo}»"))
                visitar_itens(titulo_grupo, leitor.itens_da_lista(alvo_no.args[1], funcao), funcao_dona,
                              caminho + (titulo_grupo,), prof + 1)
                continue
            alvo = leitor.alvo(alvo_no)
            nome = alvo[0] if alvo else ast.unparse(alvo_no)[:40]
            nos.append((prof, caminho, rot, nome))
            if not alvo or nome in locais or nome not in leitor.modulo:
                continue
            if alvo[1] and nome not in GENERICAS:
                referencias[nome].append((" → ".join(caminho) or titulo_menu, rot))
            visitar_funcao(nome, caminho + (rot,), prof + 1)

    def visitar_funcao(nome: str, caminho: tuple, prof: int):
        if nome in visitados:
            return
        visitados.add(nome)
        for titulo_menu, itens in leitor.menus_da_funcao(nome):
            visitar_itens(titulo_menu, itens, nome, caminho, prof)

    visitar_funcao("menu_principal", (), 0)
    return nos, referencias, visitados


def indice_busca(leitor: Leitor) -> list:
    """[(rótulo, nome_função)] do _indice_busca."""
    funcao = leitor.funcoes.get("_indice_busca")
    if funcao is None:
        return []
    saida = []
    for n in ast.walk(funcao):
        if isinstance(n, ast.Tuple) and len(n.elts) == 3:
            rot, _, alvo = n.elts
            if isinstance(alvo, ast.Name):
                saida.append((Leitor.rotulo(rot), alvo.id))
            elif isinstance(alvo, ast.Call) and isinstance(alvo.func, ast.Name):
                saida.append((Leitor.rotulo(rot), alvo.func.id))
    return saida


def main(argv: list) -> int:
    caminho = Path(next((a for a in argv if not a.startswith("-")), PADRAO))
    leitor = Leitor(caminho)
    nos, referencias, visitados = montar_arvore(leitor)
    problemas = []

    if "--arvore" in argv:
        for prof, _, rot, alvo in nos:
            print(f"{'  ' * prof}- {rot}  →  {alvo}")
        print()

    # 1. duplicatas: a mesma função aberta por itens de menus diferentes
    for nome, usos in sorted(referencias.items()):
        menus = {m for m, _ in usos}
        if len(menus) > 1:
            lista = "; ".join(f"[{m}] {r}" for m, r in usos)
            problemas.append(f"DUPLICATA: '{nome}' aparece em {len(menus)} menus: {lista}")

    # 2. índice da busca
    rotulos_por_funcao = collections.defaultdict(list)
    for _, _, rot, alvo in nos:
        rotulos_por_funcao[alvo].append(rot)
    for nome in visitados:
        for titulo_menu, _ in leitor.menus_da_funcao(nome):
            rotulos_por_funcao[nome].append(titulo_menu)
    alcancaveis = {alvo for _, _, _, alvo in nos} | visitados
    for rot, nome in indice_busca(leitor):
        if nome not in alcancaveis and not nome.startswith("_md_"):
            problemas.append(f"BUSCA: '{rot}' aponta para '{nome}', que não está em nenhum menu")
            continue
        vistos = rotulos_por_funcao.get(nome, [])
        if not vistos:
            continue
        palavras = normalizar(rot)
        melhor = max((len(palavras & normalizar(v)) / max(1, len(palavras)) for v in vistos), default=0)
        mesmo_emoji = any(emoji_inicial(rot) and emoji_inicial(rot) == emoji_inicial(v) for v in vistos)
        if melhor < 0.34 and not mesmo_emoji:
            problemas.append(f"BUSCA: '{rot}' abre '{nome}', que no menu se chama: {vistos[0]!r}")

    # 3. funções com menu() que nenhum item abre
    for nome in sorted(leitor.funcoes):
        if nome in visitados or nome in ABERTAS_DE_OUTRO_JEITO or not leitor.menus_da_funcao(nome):
            continue
        problemas.append(f"SOLTO: '{nome}' tem um menu, mas nenhuma opção o abre")

    total_acoes = sum(1 for _, _, _, alvo in nos if not alvo.startswith("grupo"))
    total_menus = sum(1 for nome in visitados if leitor.menus_da_funcao(nome))
    total_grupos = sum(1 for _, _, _, alvo in nos if alvo.startswith("grupo"))
    print(f"Menus conferidos: {total_menus} menus, {total_grupos} subcategorias (grupo) e {total_acoes} opções.")
    if problemas:
        print(f"\n{len(problemas)} problema(s):")
        for p in problemas:
            print(f"  ✖ {p}")
        return 1
    print("✔ Nenhuma duplicata, busca coerente e nenhum menu solto.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
