#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compatibilidade: o Termux-Toons agora se chama LNUX e o programa é o lnux.py.

Este arquivo continua existindo para não quebrar o que foi criado antes da troca de nome: o atalho
'toons' do ~/.bashrc, os serviços 24h que o tmux reinicia, as tarefas do cron e os atalhos da tela
inicial (Termux:Widget) que chamam termux_toons.py. Ele só roda o lnux.py com os mesmos argumentos.
"""
import runpy
import sys
from pathlib import Path

LNUX = Path(__file__).resolve().with_name("lnux.py")

if __name__ == "__main__":
    sys.argv[0] = str(LNUX)
    runpy.run_path(str(LNUX), run_name="__main__")
