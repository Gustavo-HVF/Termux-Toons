# Módulo 2: Termux-Toons vira LNUX, para várias distros

## Resumo

- O programa agora se chama **LNUX** (`lnux.py`, versão 2.0.0), com banner, mensagens, comentários e README novos.
- Na primeira abertura ele **pergunta qual sistema a pessoa usa**, já sugerindo o detectado. A escolha fica salva e
  pode ser trocada depois.
- Tudo o que muda de um sistema para outro mora em **um arquivo de perfil por sistema**, em `distros/<id>.json`.
  Para suportar uma distro nova basta criar um arquivo, sem mexer no `lnux.py` (testado com um perfil do Void Linux).
- **O menu mostra só o que funciona** no sistema escolhido: 151 das 663 opções dependem do sistema. As opções do
  Android ganham um equivalente no Linux quando ele existe e somem quando não existe.
- Quem já usava o Termux-Toons não perde nada: a pasta de dados, o atalho `toons`, o `termux_toons.py`, os serviços
  e as tarefas do cron continuam funcionando.

## 1. Renomear para LNUX

| O que | Antes | Depois |
|---|---|---|
| Programa | `termux_toons.py` | `lnux.py` (com `git mv`, para manter o histórico) |
| Compatibilidade | – | `termux_toons.py` pequeno que só roda o `lnux.py` (atalhos, tmux, cron e Termux:Widget antigos) |
| Banner | TERMUX TOONS | LNUX, e a linha embaixo mostra o sistema em uso |
| Pasta de dados | `~/.termux_toons` | `~/.lnux`; na primeira abertura a pasta antiga é renomeada e o nome antigo vira um atalho para a nova |
| Atalho | `toons` | `lnux` (o `instalar.sh` também faz o `toons` abrir o `lnux.py`) |
| Sessões tmux | `toons-<serviço>` | `lnux-<serviço>`; as `toons-` abertas antes continuam sendo vistas, paradas e abertas |
| Marca no crontab | `# toons:` | `# lnux:`; as tarefas antigas continuam reconhecidas |
| Variáveis | `TOONS_NUMEROS`, `TOONS_DEBUG` | `LNUX_NUMEROS`, `LNUX_DEBUG` (as antigas continuam valendo) e `LNUX_SISTEMA` (nova) |
| Classe de erro | `ToonsError` | `LnuxError` |
| Pastas de saída | `Download/Termux-Toons/...` | `Download/LNUX/...` |

**Nomes antigos mantidos de propósito**, para não quebrar o que já existe:

| Nome | Por que ficou |
|---|---|
| `"toons-chat"` (protocolo do chat na rede local) | Assim o LNUX conversa com quem ainda usa o Termux-Toons |
| Chaves `toons:` no navegador de quem assiste | Guardam o ponto onde cada pessoa parou o filme |
| Etiqueta `toons_eq` nas músicas | Evita equalizar duas vezes um arquivo que já foi equalizado |
| Cópias `*.antes-do-toons` | Cópias de segurança do tema, da fonte e da mensagem de boas-vindas; o nome igual garante que a volta ao original continue funcionando |
| Nome do controle para as TVs Samsung/LG | Trocar faria a TV pedir permissão de novo |
| `window.TERMUX_TOONS` | O VLC Web lê esse nome; foi acrescentado `window.LNUX` ao lado |
| Endereço do repositório no GitHub | Continua `Termux-Toons` até ser renomeado lá |

## 2 e 5. Escolha do sistema ao iniciar, salva na configuração

- Na primeira abertura aparece **"🐧 Qual sistema você usa?"**:
  - mostra o que foi detectado e por quê (por exemplo, "o sistema se identifica como Ubuntu 24.04.5 LTS");
  - a lista vem com o detectado já selecionado; Enter confirma.
- A escolha vai para `~/.lnux/config.json` (`"sistema": "debian"`).
- Para trocar depois, há três caminhos:
  - **⚙️ Sistema e manutenção → 🐧 Trocar o sistema**; o menu muda na hora;
  - `lnux sistema <id>` no terminal;
  - `LNUX_SISTEMA=<id>`, que vale só naquela execução, sem salvar.
- Os serviços em segundo plano não perguntam nada: usam o sistema salvo ou, se não houver, o detectado.
- `lnux sistema` e **ℹ️ O que o LNUX sabe deste sistema** mostram:
  - o perfil e o arquivo dele;
  - o que foi detectado;
  - o gerenciador de pacotes e as pastas;
  - os recursos;
  - quais equivalentes dos comandos do Termux estão disponíveis.

## 3. Camada de compatibilidade

| Parte | Como ficou |
|---|---|
| **Gerenciador de pacotes** | `instalar_pkg()` usa os comandos do perfil (`pkg`, `apt-get`, `pacman`, `dnf`, `apk`, `zypper`) e traduz cada nome de pacote. O código continua pedindo pelos nomes do Termux (`android-tools`, `libqrencode`...), e o perfil diz o nome na distro (`adb`, `qrencode`...) ou `null` quando ela não tem (aí o LNUX avisa e, quando se sabe, mostra como instalar à mão) |
| **Módulos Python** | Primeiro pelo pacote da distro (`python3-rich`, `python-pillow`...); o que não houver vai pelo pip só para o usuário (`~/.local`), avisando quando a distro protege o Python dela (PEP 668). Num venv, pip direto |
| **Root** | `sudo` ou `doas`, na ordem que o perfil indica; quem já é root não usa nenhum. Sem terminal (serviços), o sudo falha na hora em vez de travar esperando a senha. O `su` do Android só é usado no Android: no Linux ele pediria a senha do root |
| **Serviços do sistema** | `servico_do_sistema()` liga, desliga e mostra o SSH, o cron, o MariaDB e o PostgreSQL pelo systemd ou pelo OpenRC, com os comandos e os nomes do perfil. Prepara o banco na primeira vez quando a distro pede (`initdb` no Arch, `postgresql-setup` no Fedora) |
| **Caminhos** | Downloads, Músicas, Vídeos, Imagens, Documentos e capturas de tela: no Termux, `~/storage/...`; nas distros, as pastas XDG (as de `~/.config/user-dirs.dirs`, inclusive com nomes em português). Os caminhos do Termux salvos na configuração são traduzidos sozinhos |
| **Comandos do Termux** | `rodar()`, `_tapi()` e `tem()` trocam os `termux-*` pelo equivalente do Linux. O resto do código não mudou. Tabela abaixo |
| **Detecção** | Termux pelo `$PREFIX`/`TERMUX_VERSION`; distros pelo `ID` e `ID_LIKE` do `/etc/os-release` (Linux Mint, Pop!_OS, Manjaro e outras derivadas caem no perfil certo); por último, pelo gerenciador de pacotes que existir |

| Comando do Termux | Equivalente no Linux |
|---|---|
| `termux-open-url`, `termux-open` | `xdg-open` |
| `termux-share` | Texto vai para a área de transferência; com um arquivo, abre a pasta dele |
| `termux-clipboard-set` / `-get` | `wl-copy`/`wl-paste` (Wayland), `xclip` ou `xsel` (X11) |
| `termux-notification` | `notify-send`. As notificações fixas (player, andamento) não aparecem, porque no Linux virariam uma janela nova a cada atualização |
| `termux-tts-speak` | `espeak-ng` (voz `pt-br`) ou `spd-say` |
| `termux-battery-status` | `/sys/class/power_supply` (notebooks) |
| `termux-wifi-connectioninfo`, `-scaninfo`, `-enable` | `nmcli` |
| `termux-volume` | `wpctl`, `pactl` ou `amixer` |
| `termux-camera-photo` | `ffmpeg` com a webcam (`/dev/video*`) |
| `termux-microphone-record` | `ffmpeg` gravando do PulseAudio/PipeWire ou ALSA |
| `termux-wake-lock`, `-media-scan`, `-reload-settings`, `-setup-storage` | Nada a fazer no Linux (respondem "ok") |
| SMS, GPS, sensores, lanterna, vibração, infravermelho | Sem equivalente: as opções somem do menu |

## 4. O menu mostra só o que funciona

As opções que dependem do sistema se marcam com `so_em("recurso", função)`. Alguns exemplos:

| Marca | Significa |
|---|---|
| `so_em("termux_api", ...)` | Precisa do app Termux:API |
| `so_em("!termux", ...)` | Só fora do Termux |
| `so_em("pacote:jellyfin-server", ...)` | Só se a distro tem o pacote |

Já `por_sistema("rótulo no Termux", "rótulo no Linux")` troca o nome mostrado. O filtro vale para o menu e para a
🔍 Busca, e é refeito a cada volta: trocar o sistema muda o menu na hora.

| No Termux (Android) | Numa distro Linux |
|---|---|
| 🐧 Linux de verdade (proot-distro, Termux:X11) | 🐧 **Outras distros em contêineres** (menu novo, com o Distrobox e o Podman): criar Debian, Ubuntu, Arch, Fedora, Alpine, openSUSE ou Kali; entrar; rodar comandos; levar um app para o menu do computador; atualizar; parar; remover |
| 📲 Celular e sistema | 🖥️ **Computador e Android conectado** |
| 🔌 Depuração sem fio (ADB no próprio celular) | 📱 **Android conectado**: o mesmo ADB, para um celular por USB ou Wi-Fi (o pareamento pelo Wi-Fi também funciona do computador) |
| 📱 Termux:API | 🖥️ **Recursos do computador**: notificação, foto da webcam, área de transferência e volume |
| Abrir vídeo no VLC/MX Player do Android | No **VLC ou mpv** do computador |
| scrcpy no Termux:X11 | **scrcpy** numa janela da área de trabalho |
| SSH na porta 8022 | O **serviço SSH do sistema** (porta 22) |
| MariaDB/PostgreSQL como usuário | O **serviço do banco** do sistema; o PostgreSQL ganha um usuário com o seu nome |
| cron no tmux | O **cron do sistema** |
| Backup do Termux | **Backup da pasta pessoal** (sem caches, sem a pasta Downloads, opcionalmente sem modelos de IA e contêineres) |
| Gerenciador de arquivos: Termux, ADB, root | **Normal** (com atalhos para Downloads, Documentos e discos em `/media`) e **Android conectado** |
| tcpdump com `su` | **tcpdump com sudo**, na interface da rota padrão |
| TRIM com `su` | **fstrim com sudo** |
| Atualizar o Termux, trocar o espelho, repositórios x11/root/tur | **Atualizar o sistema** pelo gerenciador da distro, e **como ativar os repositórios extras** dela (RPM Fusion, AUR, Packman...) |
| LibreOffice dentro do proot | O **LibreOffice** da distro |
| Previsão do tempo pelo GPS | Pela busca de cidade |
| Controle da TV por infravermelho ou Wi-Fi | **Smart TV pelo Wi-Fi** (Samsung, LG, Android TV, Roku) |

**Ficam só no Termux**, porque não têm equivalente num computador:

| Grupo | O que fica de fora |
|---|---|
| Termux:API | Sensores, SMS, GPS, lanterna, vibração |
| Infravermelho | TV por IR, TV-B-Gone, controle de outros aparelhos |
| Recursos do próprio Android | Modem AT, resolução da tela, transmitir a tela por link, limpar o cache de todos os apps, otimizar apps, telas do Android |
| App Termux | Tema e fonte do Termux, mensagem de boas-vindas, Termux:Widget, Termux:X11 |

**Dependem da distro ter o pacote:**

| Programa | Onde aparece |
|---|---|
| Jellyfin | Arch |
| Navidrome | Arch e Alpine |
| lua-language-server | Arch e Alpine |
| llama.cpp pronto | Fedora |
| code-server | Nenhuma distro empacota: aparece "como instalar", com o script oficial |

## 6. Uma distro nova = um arquivo

| Arquivo | O que é |
|---|---|
| `distros/termux.json` | Termux (Android) |
| `distros/debian.json` | Debian e Ubuntu |
| `distros/arch.json` | Arch |
| `distros/fedora.json` | Fedora e RHEL |
| `distros/alpine.json` | Alpine |
| `distros/opensuse.json` | openSUSE |
| `distros/outro.json` | Qualquer outra distro |
| `distros/README.md` | O formato e o passo a passo para criar um perfil |

- **Onde pôr um perfil novo:** em `distros/` ou em `~/.lnux/distros/`. Um perfil com o mesmo id substitui o
  original.
- **O que cada perfil traz:**
  - os comandos do gerenciador de pacotes e o nome de 85 pacotes;
  - os módulos Python da distro;
  - as pastas e o jeito de virar root;
  - os serviços (systemd ou OpenRC);
  - os recursos;
  - a dica de repositórios extras.
- **Teste com o Void Linux:** um `void.json` em `~/.lnux/distros/`, com o gerenciador `xbps` e os serviços pelo
  `runit`, funcionou sem mudar nada no `lnux.py`: `xbps-install -y ...` para instalar e `sv up sshd` para o SSH.
- **Perfis embutidos:** se a pasta `distros/` não vier junto, o LNUX ainda abre com um perfil mínimo do Termux e
  outro de "Outro Linux".

## Como foi verificado

| Teste | O que confere | Resultado |
|---|---|---|
| `tests/verificar_menus.py` (atualizado) | Duplicatas, busca, menus soltos, `@submenu` faltando (checagem nova) e, para cada perfil, se algum submenu fica vazio | ✔ 87 menus, 663 opções, 151 dependem do sistema. Visíveis: Termux 556, Arch 493, Alpine 491, Fedora 489, Debian 488, openSUSE 488, Outro 475 |
| `tests/verificar_perfis.py` (novo) | Cada perfil contra o que o código usa: campos, recursos conhecidos, comandos, pastas, serviços e a tradução de cada um dos 83 pacotes que o código pede | ✔ nos 7 perfis. Com um perfil incompleto de propósito, ele aponta cada pacote e recurso que falta |
| `tests/testar_menus_por_sistema.py` (novo) | Importa o `lnux.py` e abre todos os menus e submenus em cada perfil, sem executar nenhuma ação (comandos e perguntas são falsos, numa pasta pessoal temporária) | ✔ nos 7 perfis: 115 menus no Termux, 111 nas distros |

**Testes manuais:**

- **Primeira abertura**, num terminal simulado: sugeriu Debian/Ubuntu para este Ubuntu 24.04, salvou com Enter e
  mostrou o menu adaptado.
- **Migração:** um `~/.termux_toons` com configuração e log virou `~/.lnux`, com o token preservado, e o nome
  antigo virou um atalho.
- **Comando montado em cada perfil**, para instalar `android-tools libqrencode ffmpeg termux-api`:

  | Perfil | Comando |
  |---|---|
  | Termux | `pkg install -y android-tools libqrencode ffmpeg termux-api` |
  | Debian | `apt-get install -y adb qrencode ffmpeg` |
  | Arch | `pacman -S --needed --noconfirm android-tools qrencode ffmpeg` |
  | Fedora | `dnf install -y android-tools qrencode ffmpeg-free` |
  | Alpine | `apk add android-tools libqrencode-tools ffmpeg` |
  | openSUSE | `zypper --non-interactive install android-tools qrencode ffmpeg` |

  Em todas as distros o `termux-api` é avisado como inexistente. Como usuário comum, entra o `sudo` (ou o `sudo -n`,
  sem terminal).
- **Tradução dos comandos do Termux**, com uma área de trabalho simulada:

  | O que o código pediu | O que rodou |
  |---|---|
  | Copiar | `xclip -selection clipboard` |
  | Colar | `xclip ... -o` |
  | Notificação | `notify-send -a LNUX ...` |
  | Abrir link | `xdg-open https://...` |
  | Falar | `espeak-ng -v pt-br -s 175 ...` |
  | Wi-Fi | `nmcli`, com o SSID e o BSSID certos |
  | SMS | "não tem equivalente em Debian / Ubuntu" |
- **`instalar.sh`:** com um `apt-get` falso, instalou os pacotes certos e trocou o atalho `toons` antigo para o
  `lnux.py`.
- **Execução real** no modo de números, abrindo todas as categorias com o perfil Termux e com o Debian: nenhum erro.
- **`pyflakes`:** nenhum nome indefinido.

## O que não foi possível e limitações

1. **Não testei num Android de verdade.** Esta sessão roda num Ubuntu. No caminho do Termux, os comandos montados
   são os mesmos de antes (`pkg install -y`, `termux-*` direto), mas vale abrir o LNUX no celular antes de usar
   no dia a dia.
2. **Também não testei em cada distro real.** Os nomes de pacote vieram do que eu conheço de cada uma. Alguns
   podem variar conforme a versão, e por isso deixei os incertos como `null` ou com o nome mais provável:

   | Distro | Pacotes incertos |
   |---|---|
   | Alpine | `postgresql16`, `cloudflared` |
   | openSUSE | `nodejs-default` |
   | Fedora | `ffmpeg-free` (o completo é do RPM Fusion) |

   Se um nome estiver errado, a instalação mostra o erro do gerenciador. Corrigir é editar uma linha do perfil;
   no caso dos módulos Python, o LNUX tenta o pip sozinho.
3. **Notificações com botões** (a do player, com pausar e pular) não existem no Linux. O player funciona, mas sem
   a notificação; o equivalente seria o MPRIS.
4. **Comandos do bot e da API que usam o Android** (`/lanterna`, `/sms`, `/local`, `/vibrar`) respondem com erro
   no Linux. O `/foto` usa a webcam.
5. **Textos internos:** muitas descrições dentro das funções ainda falam em "celular". Mudei os rótulos de menu,
   os cabeçalhos e as mensagens que aparecem no Linux; o resto pode ser ajustado aos poucos, sem afetar o
   funcionamento.
6. **Sem área de trabalho** (servidor sem `DISPLAY`/`WAYLAND_DISPLAY`), abrir links, notificar e copiar não têm
   onde aparecer. O LNUX mostra o link ou o texto no terminal.
7. **O repositório no GitHub continua se chamando Termux-Toons.** Renomear é em Settings → Rename, e o endereço
   antigo redireciona.
8. **Continua um arquivo só** (`lnux.py`), como antes, mais a pasta `distros/`.

## Arquivos

| Arquivo | O que mudou |
|---|---|
| `termux_toons.py` → `lnux.py` | Renomeado. Seção nova "Sistemas: perfis das distros e camada de compatibilidade" (perfis, detecção, escolha, pacotes, pip, root, serviços, tradução dos comandos do Termux, pastas). Menus marcados por recurso, equivalentes do Linux, menu do Distrobox, subcomando `sistema`, migração da pasta de dados, sessões tmux e cron com o nome novo, banner e textos |
| `termux_toons.py` | Novo: compatibilidade, só roda o `lnux.py` |
| `distros/*.json` (7) e `distros/README.md` | Novos: os perfis e a documentação do formato |
| `instalar.sh` | Reescrito: Termux, apt, pacman, dnf, apk e zypper; atalho `lnux` |
| `tests/verificar_menus.py` | Entende `so_em`, `so_em_itens` e `por_sistema`; confere cada perfil (submenus vazios) e o `@submenu` |
| `tests/verificar_perfis.py`, `tests/testar_menus_por_sistema.py` | Novos |
| `README.md` | LNUX, instalação nas distros, "Qual sistema você usa", tabela de equivalentes, "Uma distro nova: só um arquivo", linha de comando, arquivos e testes |
| `docs/relatorio-modulo-2.md` | Novo: este relatório |
