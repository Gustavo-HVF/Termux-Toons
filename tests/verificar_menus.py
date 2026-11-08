#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificador dos menus do LNUX (só lê o código e os perfis, não executa nada).

Monta a árvore de menus a partir de `menu_principal` lendo o código-fonte (AST) e confere:

  1. Duplicatas: a mesma categoria/ação (função) aparecendo em menus diferentes.
  2. Busca: cada entrada do índice da 🔍 Busca (`_indice_busca`) aponta para algo que existe no menu, e o
     nome dela combina com o que a pessoa vai ver ao abrir.
  3. Menus que ninguém abre (funções com menu() fora da árvore).
  4. Sistemas: para cada perfil em distros/, quais opções aparecem (as marcadas com so_em/so_em_itens que o
     sistema não tem somem) e se algum submenu fica vazio naquele sistema.

Uso:
    python3 tests/verificar_menus.py              # confere o lnux.py da pasta acima
    python3 tests/verificar_menus.py --arvore     # também imprime a árvore inteira (com o que cada opção exige)
    python3 tests/verificar_menus.py caminho.py   # confere outro arquivo

Sai com código 1 se achar algum problema (bom para rodar antes de cada commit).
"""
from __future__ import annotations

import ast
import collections
import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PADRAO = RAIZ / "lnux.py"
PASTA_PERFIS = RAIZ / "distros"

# Funções genéricas que podem aparecer em vários menus sem ser duplicata
# (cada chamada recebe argumentos diferentes: parar o serviço X, abrir o link Y...).
GENERICAS = {
    "parar_servico", "status_servico", "abrir_sessao", "rodar", "info", "ok", "instalar_pkg", "mostrar_dados",
    "_explicar", "_abrir_link_android", "_testar_aparelho", "_usar_rede_privada", "usar_saida_no_proxy",
    "abrir_tunel", "abrir_link", "servico_do_sistema", "pronto", "_explicar_tecnica",
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
    """Lê o arquivo e entende os menus declarados com menu(...), grupo(...), so_em(...) e por_sistema(...)."""

    def __init__(self, caminho: Path):
        self.arvore_ast = ast.parse(caminho.read_text(encoding="utf-8"))
        self.funcoes = {n.name: n for n in self.arvore_ast.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.modulo = set(self.funcoes)

    # ── rótulos e alvos ──────────────────────────────────────────────
    @staticmethod
    def rotulo(no) -> str:
        """Texto do rótulo de um item (string, f-string, lambda que devolve texto ou por_sistema(termux, linux))."""
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
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == "por_sistema" and no.args:
            return " ¦ ".join(Leitor.rotulo(a) for a in no.args)
        return ast.unparse(no)[:60]

    @staticmethod
    def desembrulhar(no) -> tuple:
        """so_em("recurso", alvo) → (alvo, ("recurso",)). Aceita so_em dentro de so_em."""
        requisitos = []
        while isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == "so_em" and len(no.args) == 2:
            requisitos.append(no.args[0].value if isinstance(no.args[0], ast.Constant) else "?")
            no = no.args[1]
        return no, tuple(requisitos)

    def alvo(self, no):
        """('nome', direto?) da função que o item abre; None se não der para saber."""
        if isinstance(no, ast.Name):
            return no.id, True
        if isinstance(no, ast.Lambda) and isinstance(no.body, ast.Call) and isinstance(no.body.func, ast.Name):
            return no.body.func.id, False
        return None

    # ── listas de itens ──────────────────────────────────────────────
    def itens_da_lista(self, no, funcao, requisitos: tuple = ()) -> list:
        """Itens (rótulo_no, alvo_no, requisitos) de uma lista de menu; resolve variáveis montadas na função."""
        if isinstance(no, ast.Name):  # menu("...", itens): junta o que foi atribuído/somado/anexado a 'itens'
            elementos = []
            for n in ast.walk(funcao):
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == no.id for t in n.targets):
                    elementos += self.itens_da_lista(n.value, funcao, requisitos)
                elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id == no.id:
                    elementos += self.itens_da_lista(n.value, funcao, requisitos)
                elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "append"
                      and isinstance(n.func.value, ast.Name) and n.func.value.id == no.id and n.args):
                    elementos += self.itens_da_lista(ast.List(elts=[n.args[0]]), funcao, requisitos)
            return elementos
        if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Add):
            return self.itens_da_lista(no.left, funcao, requisitos) + self.itens_da_lista(no.right, funcao, requisitos)
        if not isinstance(no, (ast.List, ast.Tuple)):
            return []
        saida = []
        for el in no.elts:
            if isinstance(el, ast.Tuple) and len(el.elts) == 2:
                saida.append((el.elts[0], el.elts[1], requisitos))
            elif isinstance(el, ast.Starred) and isinstance(el.value, ast.Call):
                chamada, req = el.value, requisitos
                if isinstance(chamada.func, ast.Name) and chamada.func.id == "so_em_itens" and len(chamada.args) == 2:
                    req = requisitos + (chamada.args[0].value,)
                    chamada = chamada.args[1]
                if isinstance(chamada, ast.Call) and isinstance(chamada.func, ast.Name) and \
                        chamada.func.id == "itens_servico":
                    rot = Leitor.rotulo(chamada.args[1]) if len(chamada.args) > 1 else "serviço"
                    saida.append((ast.Constant(f"{rot}: iniciar / parar / status / sessão"), chamada.args[2], req))
        return saida

    def menus_da_funcao(self, nome: str) -> list:
        """[(título, [(rótulo, alvo_no, requisitos)])] das chamadas menu(...) dentro da função (sem as dos grupos)."""
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


class No:
    """Uma opção da árvore de menus."""

    def __init__(self, prof: int, caminho: tuple, rotulo: str, alvo: str, requisitos: tuple, pai):
        self.prof, self.caminho, self.rotulo, self.alvo = prof, caminho, rotulo, alvo
        self.requisitos, self.pai, self.filhos = requisitos, pai, []


def montar_arvore(leitor: Leitor):
    """Percorre a partir de menu_principal. Devolve (nós, referências, funções visitadas)."""
    nos = []
    referencias = collections.defaultdict(list)   # nome_função → [(menu onde aparece, rótulo)]
    visitados = set()

    def visitar_itens(titulo_menu: str, itens: list, funcao_dona: str, caminho: tuple, prof: int, pai, herdados: tuple):
        funcao = leitor.funcoes[funcao_dona]
        locais = {n.name for n in ast.walk(funcao) if isinstance(n, ast.FunctionDef) and n is not funcao}
        for rot_no, alvo_no, req_lista in itens:
            rot = Leitor.rotulo(rot_no)
            alvo_no, req_item = Leitor.desembrulhar(alvo_no)
            requisitos = herdados + req_lista + req_item
            # ferramenta("Título", explicação, codificar, decodificar, extras=...): um grupo com "Como funciona",
            # codificar e decodificar (as técnicas de 🕵️ Mensagens secretas)
            if isinstance(alvo_no, ast.Call) and isinstance(alvo_no.func, ast.Name) and alvo_no.func.id == "ferramenta":
                titulo_f = Leitor.rotulo(alvo_no.args[0])
                no = No(prof, caminho, rot, f"grupo «{titulo_f}»", requisitos, pai)
                nos.append(no)
                if pai:
                    pai.filhos.append(no)
                extras = next((k.value for k in alvo_no.keywords if k.arg == "extras"), ast.Tuple(elts=[]))
                itens_f = [(ast.Constant("ℹ️ Como funciona"), ast.Name("_explicar_tecnica"), ()),
                           (ast.Constant("🔒 Codificar"), alvo_no.args[2], ()),
                           (ast.Constant("🔓 Decodificar"), alvo_no.args[3], ())]
                visitar_itens(titulo_f, itens_f + leitor.itens_da_lista(extras, funcao), funcao_dona,
                              caminho + (titulo_f,), prof + 1, no, requisitos)
                continue
            # grupo("Título", [...]) dentro do menu: um submenu sem função própria
            if isinstance(alvo_no, ast.Call) and isinstance(alvo_no.func, ast.Name) and alvo_no.func.id == "grupo":
                titulo_grupo = Leitor.rotulo(alvo_no.args[0])
                no = No(prof, caminho, rot, f"grupo «{titulo_grupo}»", requisitos, pai)
                nos.append(no)
                if pai:
                    pai.filhos.append(no)
                visitar_itens(titulo_grupo, leitor.itens_da_lista(alvo_no.args[1], funcao), funcao_dona,
                              caminho + (titulo_grupo,), prof + 1, no, requisitos)
                continue
            alvo = leitor.alvo(alvo_no)
            nome = alvo[0] if alvo else ast.unparse(alvo_no)[:40]
            no = No(prof, caminho, rot, nome, requisitos, pai)
            nos.append(no)
            if pai:
                pai.filhos.append(no)
            if not alvo or nome in locais or nome not in leitor.modulo:
                continue
            if alvo[1] and nome not in GENERICAS:
                referencias[nome].append((" → ".join(caminho) or titulo_menu, rot))
            visitar_funcao(nome, caminho + (rot,), prof + 1, no, requisitos)

    def visitar_funcao(nome: str, caminho: tuple, prof: int, pai, herdados: tuple):
        if nome in visitados:
            return
        visitados.add(nome)
        for titulo_menu, itens in leitor.menus_da_funcao(nome):
            visitar_itens(titulo_menu, itens, nome, caminho, prof, pai, herdados)

    visitar_funcao("menu_principal", (), 0, None, ())
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
            alvo, _ = Leitor.desembrulhar(alvo)
            if isinstance(alvo, ast.Name):
                saida.append((Leitor.rotulo(rot), alvo.id))
            elif isinstance(alvo, ast.Call) and isinstance(alvo.func, ast.Name):
                saida.append((Leitor.rotulo(rot), alvo.func.id))
    return saida


# ── sistemas: o mesmo cálculo de tem_recurso() do lnux.py, a partir do arquivo do perfil ──

def carregar_perfis() -> dict:
    return {arq.stem: json.loads(arq.read_text("utf-8")) for arq in sorted(PASTA_PERFIS.glob("*.json"))}


def tem_recurso(expressao: str, perfil: dict) -> bool:
    for opcao in expressao.split("|"):
        opcao = opcao.strip()
        negar, nome = opcao.startswith("!"), opcao.lstrip("!")
        if nome.startswith("pacote:"):
            nomes = perfil["pacotes"].get("nomes") or {}
            pacote = nome[len("pacote:"):]
            existe = (nomes.get(pacote, pacote) is not None) and \
                (perfil["familia"] == "termux" or bool(perfil["pacotes"].get("instalar")))
        elif nome == "bateria":
            existe = True  # depende do aparelho (notebook tem, desktop não): conta como visível
        else:
            existe = nome in perfil["recursos"]
        if existe != negar:
            return True
    return False


def visivel(no: No, perfil: dict) -> bool:
    return all(tem_recurso(r, perfil) for r in no.requisitos)


def main(argv: list) -> int:
    caminho = Path(next((a for a in argv if not a.startswith("-")), PADRAO))
    leitor = Leitor(caminho)
    nos, referencias, visitados = montar_arvore(leitor)
    problemas = []

    if "--arvore" in argv:
        for no in nos:
            exige = f"  [{' & '.join(no.requisitos)}]" if no.requisitos else ""
            print(f"{'  ' * no.prof}- {no.rotulo}  →  {no.alvo}{exige}")
        print()

    # 1. duplicatas: a mesma função aberta por itens de menus diferentes
    for nome, usos in sorted(referencias.items()):
        menus = {m for m, _ in usos}
        if len(menus) > 1:
            lista = "; ".join(f"[{m}] {r}" for m, r in usos)
            problemas.append(f"DUPLICATA: '{nome}' aparece em {len(menus)} menus: {lista}")

    # 2. índice da busca
    rotulos_por_funcao = collections.defaultdict(list)
    for no in nos:
        rotulos_por_funcao[no.alvo].append(no.rotulo)
    for nome in visitados:
        for titulo_menu, _ in leitor.menus_da_funcao(nome):
            rotulos_por_funcao[nome].append(titulo_menu)
    alcancaveis = {no.alvo for no in nos} | visitados
    for rot, nome in indice_busca(leitor):
        if nome not in alcancaveis and not nome.startswith("_md_"):
            problemas.append(f"BUSCA: '{rot}' aponta para '{nome}', que não está em nenhum menu")
            continue
        vistos = rotulos_por_funcao.get(nome, [])
        if not vistos:
            continue
        palavras = normalizar(rot)
        melhor = max((len(palavras & normalizar(v)) / max(1, len(palavras)) for v in vistos), default=0)
        mesmo_emoji = any(emoji_inicial(rot) and emoji_inicial(rot) in v for v in vistos)
        if melhor < 0.34 and not mesmo_emoji:
            problemas.append(f"BUSCA: '{rot}' abre '{nome}', que no menu se chama: {vistos[0]!r}")

    # 3. funções com menu() que nenhum item abre
    for nome in sorted(leitor.funcoes):
        if nome in visitados or nome in ABERTAS_DE_OUTRO_JEITO or not leitor.menus_da_funcao(nome):
            continue
        problemas.append(f"SOLTO: '{nome}' tem um menu, mas nenhuma opção o abre")

    # 3a. duas funções de módulo com o mesmo nome: a de baixo substitui a de cima sem aviso
    contagem = collections.Counter(n.name for n in leitor.arvore_ast.body if isinstance(n, (ast.FunctionDef,
                                                                                           ast.AsyncFunctionDef)))
    for nome, vezes in sorted(contagem.items()):
        if vezes > 1:
            linhas = [str(n.lineno) for n in leitor.arvore_ast.body if isinstance(n, ast.FunctionDef) and n.name == nome]
            problemas.append(f"NOME REPETIDO: a função '{nome}' é definida {vezes} vezes (linhas {', '.join(linhas)}); "
                             f"a última substitui as outras")

    # 3b. função que abre um menu precisa de @submenu (sem ele, ao voltar a tela pede "Pressione Enter")
    ajudantes = {"menu_principal", "grupo", "_menu_ponte_publica", "_menu_categoria_adb", "_md_menu_grupo"}
    for nome in sorted(visitados - ajudantes):
        funcao = leitor.funcoes.get(nome)
        if funcao is not None and leitor.menus_da_funcao(nome) and \
                not any(ast.unparse(d) == "submenu" for d in funcao.decorator_list):
            problemas.append(f"DECORADOR: '{nome}' abre um menu, mas não tem @submenu logo acima do def")

    # 4. cada sistema: quantas opções aparecem e se algum submenu fica vazio
    perfis = carregar_perfis()
    conhecidos = {r for p in perfis.values() for r in p["recursos"]} | {"bateria"}
    for no in nos:
        for req in no.requisitos:
            for nome in (o.strip().lstrip("!") for o in req.split("|")):
                if not nome.startswith("pacote:") and nome not in conhecidos:
                    problemas.append(f"RECURSO: '{no.rotulo}' exige '{nome}', que nenhum perfil declara")
    resumo = []
    for ident, perfil in perfis.items():
        visiveis = [no for no in nos if visivel(no, perfil)]
        resumo.append(f"{ident}: {sum(1 for no in visiveis if not no.filhos)}")
        for no in visiveis:
            if no.filhos and not any(visivel(f, perfil) for f in no.filhos):
                problemas.append(f"VAZIO no perfil {ident}: '{no.rotulo}' aparece, mas todas as opções dele somem")

    total_acoes = sum(1 for no in nos if not no.alvo.startswith("grupo"))
    total_menus = sum(1 for nome in visitados if leitor.menus_da_funcao(nome))
    total_grupos = sum(1 for no in nos if no.alvo.startswith("grupo"))
    marcadas = sum(1 for no in nos if no.requisitos)
    print(f"Menus conferidos: {total_menus} menus, {total_grupos} subcategorias (grupo) e {total_acoes} opções "
          f"({marcadas} dependem do sistema).")
    print(f"Opções visíveis por sistema: {' · '.join(resumo)}")
    if problemas:
        print(f"\n{len(problemas)} problema(s):")
        for p in problemas:
            print(f"  ✖ {p}")
        return 1
    print("✔ Nenhuma duplicata, busca coerente, nenhum menu solto e nenhum submenu vazio em nenhum sistema.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
