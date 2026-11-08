#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Abre todos os menus do LNUX em cada sistema (perfil de distros/) sem executar nenhuma ação.

Para cada perfil: troca o sistema, abre o menu principal e entra em cada submenu, anotando as opções que
aparecem. Nada é instalado nem alterado: os comandos (rodar), as perguntas e as escolhas são trocados por
versões de mentira, e só as funções de submenu são abertas (as ações não rodam). Usa uma pasta pessoal
temporária, então a sua configuração não é tocada.

Uso:
    python3 tests/testar_menus_por_sistema.py            # todos os perfis
    python3 tests/testar_menus_por_sistema.py debian -v  # um perfil, mostrando os menus
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
os.environ["HOME"] = tempfile.mkdtemp(prefix="lnux-teste-")  # antes de importar: o LNUX lê a pasta pessoal ao carregar
os.environ["LNUX_NUMEROS"] = "1"
sys.path.insert(0, str(RAIZ))
import lnux  # noqa: E402

# telas interativas que não são menus (abririam o próprio laço delas)
NAO_ABRIR = {"gerenciador_arquivos", "menu_calculadora", "tela_player", "tela_equalizador", "menu_busca",
             "tarefas_tui", "dashboard", "menu_trocar_sistema"}


def falsos() -> None:
    """Troca tudo o que conversa com a pessoa ou com o sistema por respostas fixas."""
    lnux.rodar = lambda cmd, **k: subprocess.CompletedProcess(cmd, 0, "", "")
    lnux.saida = lambda *a, **k: ""
    lnux.perguntar = lambda *a, **k: ""
    lnux.confirmar = lambda *a, **k: False
    lnux.escolher = lambda *a, **k: None
    lnux.escolher_varios = lambda *a, **k: []
    lnux.pausar = lambda *a, **k: None
    lnux.limpar = lambda *a, **k: None
    lnux._aceitar_aviso_rede = lambda *a, **k: True
    lnux.servicos_ativos = lambda: []
    lnux.servico_ativo = lambda nome: False


def percorrer(perfil_id: str, verboso: bool) -> tuple:
    """Abre os menus no perfil. Devolve (menus abertos, opções vistas, erros)."""
    lnux.aplicar_sistema(lnux.perfis()[perfil_id])
    abertos, erros = [], []
    vistos_titulos = set()
    contagem = {"opcoes": 0}

    def menu_falso(titulo_menu, itens, sair="Voltar", cabecalho=None, descricoes=None):
        visiveis, _ = lnux._so_disponiveis(itens, descricoes)
        if titulo_menu in vistos_titulos:
            return
        vistos_titulos.add(titulo_menu)
        abertos.append(titulo_menu)
        if verboso:
            print(f"  [{perfil_id}] {titulo_menu}: {len(visiveis)} opção(ões)")
        if cabecalho:
            try:
                cabecalho()
            except Exception as e:  # noqa: BLE001
                erros.append(f"{titulo_menu} (cabeçalho): {e!r}")
        for rotulo, func in visiveis:
            contagem["opcoes"] += 1
            try:
                texto = rotulo() if callable(rotulo) else rotulo
            except Exception as e:  # noqa: BLE001
                erros.append(f"{titulo_menu} → rótulo: {e!r}")
                continue
            if getattr(func, "_submenu", False) and getattr(func, "__name__", "") not in NAO_ABRIR:
                try:
                    func()
                except lnux.LnuxError:
                    pass  # erro esperado (ex.: falta um programa), o menu mostraria a mensagem
                except Exception as e:  # noqa: BLE001
                    erros.append(f"{titulo_menu} → {texto}: {e!r}\n{traceback.format_exc(limit=3)}")

    lnux.menu = menu_falso
    try:
        lnux.menu_principal()
    except Exception as e:  # noqa: BLE001
        erros.append(f"menu principal: {e!r}\n{traceback.format_exc(limit=4)}")
    return abertos, contagem["opcoes"], erros


def main(argv: list) -> int:
    falsos()
    verboso = "-v" in argv
    pedidos = [a for a in argv if not a.startswith("-")] or list(lnux.perfis())
    falhou = False
    for perfil_id in pedidos:
        abertos, opcoes, erros = percorrer(perfil_id, verboso)
        situacao = "✔" if not erros else "✖"
        print(f"{situacao} {perfil_id:<9} {len(abertos):>3} menus abertos, {opcoes:>4} opções visíveis")
        for e in erros:
            falhou = True
            print(f"    ✖ {e}")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
