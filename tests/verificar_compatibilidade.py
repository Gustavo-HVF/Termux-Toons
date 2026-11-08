#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificador de compatibilidade com o Python 3.9 (o mínimo prometido no README).

Cada sistema traz um Python diferente: o Debian 12 vem com o 3.11, o Ubuntu 22.04 com o 3.10, o Termux e o
Arch com os mais novos. Quem escreve o código quase sempre usa um Python novo, e aí é fácil usar sem perceber
algo que não existe nos mais antigos: o LNUX nem abriria nesses sistemas. Este verificador lê o código (não
executa nada) e acusa, em qualquer versão do Python:

  • sintaxe nova que o próprio Python sabe reconhecer (match/case, except*, def f[T]...): ast com
    feature_version=(3, 9);
  • f-strings no estilo do Python 3.12 (PEP 701), que o ast NÃO acusa: dentro das chaves {...}, uma barra
    invertida, um comentário ou as mesmas aspas da f-string de fora (ex.: f'{' x' if a else ""}' ou
    f"{"/".join(p)}"). No 3.11 ou mais antigo, isso é erro de sintaxe e o arquivo inteiro não abre;
  • funções e módulos da biblioteca padrão que só existem do 3.10 em diante (lista NOVIDADES abaixo).

Uso:
    python3 tests/verificar_compatibilidade.py              # lnux.py, termux_toons.py e tests/*.py
    python3 tests/verificar_compatibilidade.py arquivo.py   # outros arquivos

Sai com código 1 se achar algum problema.
"""
from __future__ import annotations

import ast
import io
import sys
import tokenize
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MINIMO = (3, 9)

# O que só existe a partir de uma versão: "módulo.nome" (ou só "nome", para os embutidos) → versão.
NOVIDADES = {
    "itertools.pairwise": "3.10", "aiter": "3.10", "anext": "3.10", "EncodingWarning": "3.10",
    "tomllib": "3.11", "ExceptionGroup": "3.11", "BaseExceptionGroup": "3.11", "typing.Self": "3.11",
    "typing.LiteralString": "3.11", "typing.Never": "3.11", "typing.assert_never": "3.11",
    "typing.reveal_type": "3.11", "datetime.UTC": "3.11", "enum.StrEnum": "3.11", "hashlib.file_digest": "3.11",
    "asyncio.TaskGroup": "3.11", "asyncio.timeout": "3.11", "asyncio.Runner": "3.11", "contextlib.chdir": "3.11",
    "math.cbrt": "3.11", "math.exp2": "3.11", "operator.call": "3.11",
    "itertools.batched": "3.12", "typing.override": "3.12", "math.sumprod": "3.12", "calendar.Month": "3.12",
    "calendar.Day": "3.12", "os.path.splitroot": "3.12",
}
# Argumentos nomeados novos: (função, argumento) → versão. A função é o último nome da chamada.
ARGUMENTOS_NOVOS = {
    ("zip", "strict"): "3.10", ("dataclass", "slots"): "3.10", ("dataclass", "kw_only"): "3.10",
    ("bisect", "key"): "3.10", ("bisect_left", "key"): "3.10", ("bisect_right", "key"): "3.10",
    ("insort", "key"): "3.10", ("insort_left", "key"): "3.10", ("insort_right", "key"): "3.10",
    ("rmtree", "onexc"): "3.12", ("NamedTemporaryFile", "delete_on_close"): "3.12",
}


def _nome_completo(no: ast.AST) -> str:
    """os.path.splitroot → 'os.path.splitroot'; o que não for nome.nome... vira ''."""
    partes = []
    while isinstance(no, ast.Attribute):
        partes.append(no.attr)
        no = no.value
    if not isinstance(no, ast.Name):
        return ""
    partes.append(no.id)
    return ".".join(reversed(partes))


def _aspas(texto: str) -> str:
    """As aspas que abrem uma string ou f-string: ', ", ''' ou \"\"\" (sem o prefixo f, r, b...)."""
    corpo = texto.lstrip("rRbBuUfF")
    return corpo[:3] if corpo[:3] in ('"""', "'''") else corpo[:1]


def _fecha_a_de_fora(interna: str, de_fora: list) -> bool:
    """No 3.11 ou mais antigo, a f-string de fora termina nas primeiras aspas iguais às dela. Então aspas
    internas do mesmo tipo só passam quando a de fora é tripla e a de dentro não (f\"\"\"{"a"}\"\"\" vale)."""
    return any(interna[0] == fora[0] and (len(fora) == 1 or len(interna) == 3) for fora in de_fora)


def fstrings_novas(fonte: str) -> list:
    """Linhas com f-strings que só funcionam no Python 3.12+. Precisa do tokenizador do 3.12+, que separa as
    partes da f-string; nas versões antigas o próprio ast.parse já recusa esses casos."""
    if not hasattr(tokenize, "FSTRING_START"):
        return []
    achados, pilha = [], []  # pilha: as aspas de cada f-string aberta (a de fora primeiro)
    for tok in tokenize.generate_tokens(io.StringIO(fonte).readline):
        motivo = ""
        if tok.type == tokenize.FSTRING_START:
            if pilha and _fecha_a_de_fora(_aspas(tok.string), pilha):
                motivo = "f-string dentro de outra com as mesmas aspas"
            pilha.append(_aspas(tok.string))
        elif tok.type == tokenize.FSTRING_END:
            pilha.pop()
        elif not pilha:
            continue
        elif tok.type == tokenize.FSTRING_MIDDLE:
            # Texto da f-string. Na de fora a barra vale (f"a\n{x}"); numa f-string que está dentro das
            # chaves de outra, esse texto faz parte da expressão da de fora, e aí a barra não vale.
            if len(pilha) > 1 and "\\" in tok.string:
                motivo = "barra invertida dentro das chaves {...}"
        elif tok.type == tokenize.STRING:
            if "\\" in tok.string:
                motivo = "barra invertida dentro das chaves {...}"
            elif _fecha_a_de_fora(_aspas(tok.string), pilha):
                motivo = "as mesmas aspas da f-string dentro das chaves {...}"
        elif tok.type == tokenize.COMMENT:
            motivo = "comentário dentro das chaves {...}"
        if motivo:
            achados.append((tok.start[0], motivo))
    return achados


def conferir(caminho: Path) -> list:
    fonte = caminho.read_text(encoding="utf-8")
    try:
        arvore = ast.parse(fonte, str(caminho), feature_version=MINIMO)
    except SyntaxError as e:
        return [(e.lineno or 0, f"sintaxe que o Python {MINIMO[0]}.{MINIMO[1]} não entende: {e.msg}")]
    problemas = [(linha, f"{motivo} (só funciona no Python 3.12 ou mais novo)")
                 for linha, motivo in fstrings_novas(fonte)]
    for no in ast.walk(arvore):
        nomes = []
        if isinstance(no, ast.Import):
            nomes = [a.name for a in no.names]
        elif isinstance(no, ast.ImportFrom) and no.module:
            nomes = [no.module] + [f"{no.module}.{a.name}" for a in no.names]
        elif isinstance(no, ast.Attribute):
            nomes = [_nome_completo(no)]
        elif isinstance(no, ast.Name) and isinstance(no.ctx, ast.Load):
            nomes = [no.id]
        for nome in nomes:
            if nome in NOVIDADES:
                problemas.append((no.lineno, f"{nome} só existe no Python {NOVIDADES[nome]} ou mais novo"))
        if isinstance(no, ast.Call):
            funcao = _nome_completo(no.func).rpartition(".")[2]
            for k in no.keywords:
                versao = ARGUMENTOS_NOVOS.get((funcao, k.arg))
                if versao:
                    problemas.append((no.lineno, f"{funcao}({k.arg}=...) só existe no Python {versao} ou mais novo"))
            # isinstance(x, int | str) só funciona no 3.10+ (nas anotações tudo bem: viram texto com o
            # "from __future__ import annotations")
            if funcao in ("isinstance", "issubclass") and len(no.args) == 2 and \
                    isinstance(no.args[1], ast.BinOp) and isinstance(no.args[1].op, ast.BitOr):
                problemas.append((no.lineno, f"{funcao}(x, A | B) só funciona no Python 3.10 ou mais novo; "
                                             f"use uma tupla: (A, B)"))
    return sorted(set(problemas))


def main(argumentos: list) -> int:
    arquivos = [Path(a) for a in argumentos] or \
        [RAIZ / "lnux.py", RAIZ / "termux_toons.py", *sorted((RAIZ / "tests").glob("*.py"))]
    falhou = False
    for arq in arquivos:
        problemas = conferir(arq)
        nome = arq.relative_to(RAIZ) if arq.is_absolute() and RAIZ in arq.parents else arq
        if problemas:
            falhou = True
            print(f"✖ {nome}:")
            for linha, motivo in problemas:
                print(f"    linha {linha}: {motivo}")
    if not falhou:
        print(f"✔ {len(arquivos)} arquivos compatíveis com o Python {MINIMO[0]}.{MINIMO[1]} ou mais novo "
              f"(conferido no Python {sys.version_info[0]}.{sys.version_info[1]}).")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
