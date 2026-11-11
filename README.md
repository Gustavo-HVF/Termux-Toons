# LNUX

Um canivete suíço para o terminal, num programa Python só (`lnux.py`), que roda no **celular Android**
(com o [Termux](https://termux.dev)) e nas **distros Linux** (Debian/Ubuntu, Arch, Fedora, Alpine,
openSUSE e outras). Servidor web, bots, downloads de música e vídeo, player, rede, arquivos, IA, jogos e
muito mais, tudo por um menu no terminal.

```
╦   ╔╗╔ ╦ ╦ ═╗ ╦
║   ║║║ ║ ║ ╔╩╦╝
╩═╝ ╝╚╝ ╚═╝ ╩ ╚═
```

> O LNUX se chamava **Termux-Toons**. Quem já usava não perde nada: a pasta `~/.termux_toons` vira
> `~/.lnux` na primeira abertura (com configuração, notas, playlists e logs), o atalho `toons` e o
> `termux_toons.py` continuam funcionando, e os serviços e tarefas do cron criados antes seguem sendo
> reconhecidos.

Para abrir, o programa só precisa da biblioteca padrão do Python (3.9 ou mais novo). Cada função instala o
que precisa **perguntando antes**, pelo gerenciador de pacotes do seu sistema (`pkg`, `apt`, `pacman`,
`dnf`, `apk` ou `zypper`) ou pelo `pip`.

## Instalação

### No celular (Termux)

> Instale o **Termux** e o **Termux:API** pela mesma loja (F-Droid ou GitHub). A versão
> da Play Store está desatualizada e não conversa com o Termux:API do F-Droid.

```bash
pkg update && pkg upgrade
pkg install git python
git clone https://github.com/Gustavo-HVF/Termux-Toons LNUX
cd LNUX
bash instalar.sh        # instala tmux/termux-api, pede acesso ao armazenamento e cria o atalho "lnux"
lnux                    # ou: python lnux.py
```

### Numa distro Linux

```bash
git clone https://github.com/Gustavo-HVF/Termux-Toons LNUX
cd LNUX
bash instalar.sh        # instala python3, tmux, git, curl, xdg-utils e libnotify (pede a senha do sudo)
lnux                    # ou: python3 lnux.py
```

O `instalar.sh` reconhece `apt`, `pacman`, `dnf`, `apk` e `zypper`. Em outra distro, instale `python3`,
`tmux`, `git` e `curl` pelo seu sistema e rode `python3 lnux.py`.

## Qual sistema você usa

Na primeira vez, o LNUX pergunta **qual sistema você usa**, já sugerindo o que ele detectou (o Termux pelo
`$PREFIX`; as distros pelo `/etc/os-release`). É só confirmar com Enter ou escolher outro. A escolha fica
salva em `~/.lnux/config.json` e dá para trocar quando quiser em **⚙️ Sistema e manutenção → 🐧 Trocar o
sistema** (ou `lnux sistema debian` no terminal; `lnux sistema` mostra o que ele sabe do sistema em uso).

| Perfil | Para | Pacotes |
|---|---|---|
| Termux (Android) | o app Termux no celular ou tablet | `pkg` |
| Debian / Ubuntu | Debian, Ubuntu, Mint, Pop!_OS, elementary, Zorin, Kali, Raspberry Pi OS... | `apt` |
| Arch Linux | Arch, Manjaro, EndeavourOS, Garuda, CachyOS, Artix, SteamOS... | `pacman` |
| Fedora / RHEL | Fedora, Nobara, RHEL, CentOS Stream, Rocky, AlmaLinux | `dnf` |
| Alpine Linux | Alpine e postmarketOS (OpenRC) | `apk` |
| openSUSE | Tumbleweed, Leap e SUSE Linux Enterprise | `zypper` |
| Outro Linux | qualquer outra: funciona, mas os programas você instala à mão | — |

**O menu mostra só o que funciona no sistema escolhido.** Cada perfil diz os recursos que o sistema tem
(Termux:API, Android, área de trabalho, serviços do sistema...), e as opções que dependem de algo que ele não
tem somem do menu e da busca. As exclusivas do Android ganham um equivalente quando ele existe:

| No Termux (Android) | Numa distro Linux |
|---|---|
| 🐧 Linux de verdade (proot-distro) e desktop no Termux:X11 | 🐧 **Outras distros em contêineres** (Distrobox + Podman), com os apps delas no menu do computador |
| 🔌 Depuração sem fio (ADB no próprio celular) | 📱 **Android conectado** (o mesmo ADB, para um celular ligado por USB ou Wi-Fi): print, gravação, apps, tempo de tela, Android/data no gerenciador de arquivos |
| 📱 Termux:API | 🖥️ **Recursos do computador**: notificação (`notify-send`), webcam (`ffmpeg`), área de transferência (`wl-clipboard`/`xclip`), volume (`wpctl`/`pactl`) |
| Abrir no VLC/MX Player do Android | Abre no **VLC ou mpv** do computador |
| Ver outro celular no Termux:X11 (scrcpy) | **scrcpy** numa janela da área de trabalho |
| Servidor SSH na porta 8022 | O **serviço SSH do sistema** (porta 22), pelo systemd ou OpenRC |
| MariaDB/PostgreSQL rodando como usuário | O **serviço do banco** do sistema (prepara na primeira vez quando a distro pede) |
| cron no tmux | O **cron do sistema** |
| Backup do Termux | **Backup da pasta pessoal** (`~`), sem caches e sem a própria pasta Downloads |
| Captura de tráfego com root (`su`) | `tcpdump` com `sudo` |
| TRIM com root, telas do Android | `fstrim` com `sudo` |
| Word/Excel → PDF pelo LibreOffice dentro do proot | O **LibreOffice** da distro |
| Pastas `~/storage/downloads`, `~/storage/music`... | As pastas da pessoa (XDG): Downloads, Músicas, Vídeos, Imagens |

Ficam **só no Termux**, porque precisam do Android ou do app Termux: sensores, SMS, GPS, lanterna, vibração,
infravermelho (controle da TV por IR, TV-B-Gone, outros aparelhos; as Smart TVs pelo Wi-Fi funcionam nos dois),
modem (comandos AT), resolução da tela, transmitir a tela por link, limpar o cache de todos os apps, Termux:X11,
tema e fonte do Termux. O code-server e o Jellyfin/Navidrome aparecem onde a distro tem o pacote.

Os comandos do Termux usados pelo programa (`termux-open-url`, `termux-notification`, `termux-clipboard-set`,
`termux-tts-speak`, `termux-battery-status`, `termux-wifi-*`, `termux-camera-photo`,
`termux-microphone-record`...) viram o equivalente do Linux automaticamente: `lnux sistema` mostra quais estão
disponíveis no seu computador.

### Uma distro nova: só um arquivo

Tudo o que muda de um sistema para outro (gerenciador de pacotes, nome de cada pacote, pastas, `sudo`/`doas`,
serviços e recursos) fica num arquivo JSON em [`distros/`](distros/README.md). Para suportar outra distro,
copie um perfil parecido, ajuste e ponha em `distros/` ou em `~/.lnux/distros/`: o programa não precisa mudar.
O passo a passo está em [distros/README.md](distros/README.md), e `python3 tests/verificar_perfis.py meu.json`
diz o que falta no arquivo.

## Navegação

Tudo é escolhido com as **setas** (use a barra de teclas extras do Termux):

| Tecla | Ação |
|-------|------|
| `↑` `↓` | mover a seleção (dá a volta no fim da lista) |
| `Enter` ou `→` | abrir / escolher |
| `Esc`, `←` ou `q` | voltar / cancelar |
| `Espaço` | marcar itens em listas de seleção múltipla (`a` marca todos) |
| `←` `→` | alternar entre **Sim** e **Não** nas confirmações (ou aperte `s`/`n`) |
| `Home` `End` `PgUp` `PgDn` | pular para o início, fim ou página |

**Com o dedo** (bom no **Termux:Float**, que não tem a barra de setas): arraste o dedo para cima
ou para baixo para mover a seleção e **toque numa opção** para abrir. Nas listas que aparecem
no meio do texto, tocar escolhe (ou marca, nas de várias opções) e há **✔ pronto** e
**✖ cancelar** no fim; nas perguntas de Sim/Não, toque no botão.

Digitar o número da opção também funciona como atalho. Se preferir o modo antigo, de
digitar números, rode com `LNUX_NUMEROS=1 lnux` (ele também é usado automaticamente
quando não há um terminal interativo, por exemplo em scripts).

A primeira opção do menu, **🔍 Buscar**, acha qualquer função pelo nome sem você caçar
submenu por submenu: digite o que procura (**ignora acento e perdoa erro de digitação** —
`vdeos` encontra **Vídeos**, `bateira` encontra **Saúde da bateria**, `sudoko` leva aos
**Jogos**), escolha na lista e ele abre a opção direto.

## O que tem no menu

| # | Seção | O que faz |
|---|-------|-----------|
| 1 | 🌐 **Servidor web / API pessoal** | API com Flask, FastAPI ou só biblioteca padrão, acessível na rede Wi-Fi. Painel web em `/`, rotas protegidas por token (`/api/status`, `/api/bateria`, `/api/notificar`, `/api/falar`, `/api/vibrar`, `/api/lanterna`, `/api/local`, `/api/ia`). Expõe na internet com **Cloudflare Tunnel** (`cloudflared`) e mostra a URL `trycloudflare.com`. |
| 2 | 🤖 **Bots Telegram / Discord 24h** | Bot do Telegram feito só com a biblioteca padrão (long polling) e bot do Discord com `discord.py`. Rodam em sessão **tmux** com **termux-wake-lock** e reinício automático. Só respondem a IDs permitidos. Comandos: `/status /bateria /ip /local /foto /falar /notificar /vibrar /lanterna /tv /sms /ia /servicos /sh`. |
| 3 | 🔎 **Scraping e monitoramento** | Monitores de **preço** (alvo em R$), **notícias** (RSS/Atom), **status de site**, **texto que aparece/some** e **mudança de página**. Avisa por notificação, TTS e Telegram. Roda 24h no tmux. Os alertas de **chuva** e de **bateria** ficam em 🌦️ Previsão do tempo e em 🔋 Saúde da bateria. |
| 4 | 🛡️ **Rede e segurança** *(só em equipamentos seus!)* | **🔍 Diagnóstico de rede**: info de rede, descoberta de dispositivos e varredura de portas com **nmap**, DNS/ping/traceroute, teste de velocidade, redes Wi-Fi próximas, captura com tcpdump (root) ou leitura de `.pcap`, **🔐 servidor SSH** (porta 8022), geração de config **WireGuard** + QR code para o app, **🌉 Pontes de conexão** (cada uma na sua janela: **túnel SSH** `ssh -D` com proxy SOCKS pelo seu servidor, criação e envio da chave; **Tor** com teste, troca de identidade e site publicado como endereço **.onion**; **Smart DNS** com teste de velocidade e comparação de respostas dos DNS; links públicos para qualquer porta do celular pelo **Cloudflare Tunnel**, **ngrok** (instala e guarda o authtoken), **localtunnel**, **serveo** e **pinggy**, com QR code; e redes privadas **Tailscale** e **ZeroTier**, mostrando o IP do celular e como acessá-lo do PC de qualquer lugar), **proxy para usar a internet do celular no PC ou no Chromebook**, que também pode sair pelo túnel SSH ou pelo Tor, (HTTP, SOCKS5 e SOCKS4 numa porta só; o PC liga no roteador/hotspot do celular, no cabo USB ou no mesmo Wi-Fi; mostra o endereço de cada rede e o passo a passo do Windows e do Chromebook, serve um script automático `proxy.pac` e uma página de teste, senha opcional, só aceita aparelhos da rede local, não deixa chegar aos serviços internos do celular e mostra quanto cada aparelho já gastou). O **🌐 navegador pelo celular** fica em 🌐 Internet e o **modem (comandos AT)** em 📲 Celular e sistema. No Diagnóstico também ficam o **📈 ping com gráfico** (vários endereços ao vivo) e a **📶 internet usada por cada programa** (nethogs ou bandwhich, fora do Android); veja [Ferramentas de terminal](#ferramentas-de-terminal). |
| 5 | 🐧 **Linux com proot-distro** *(no Termux)* · **Outras distros em contêineres** *(nas distros)* | **Nas distros**: cria contêineres do Debian, Ubuntu, Arch, Fedora, Alpine, openSUSE ou Kali com o **Distrobox** (Podman), entra, roda comandos, atualiza e leva um app do contêiner para o menu do computador. **No Termux**: instala Debian, Ubuntu, Arch, Alpine, Fedora..., entra na distro, roda comandos, atualiza, cria usuário com sudo, faz backup, reseta e remove. **Interface gráfica no Termux:X11**: instala XFCE, LXQt ou MATE na distro, abre o desktop no app Termux:X11 com som, aceleração pela GPU (experimental) e atalho na tela inicial. |
| 6 | 🗄️ **Arquivos e backup** | **📂 Gerenciador de arquivos**: Estilo ZArchiver, com as setas: navega pelas pastas, **copia, recorta e cola, renomeia, apaga**, cria pastas, mostra os **dados do arquivo** (tamanho, data, permissões, dono), busca por nome, mostra o conteúdo de textos, abre com um app, edita no nano, **compacta em .zip e extrai** .zip/.tar.gz/.7z/.rar. Três níveis de acesso: Termux, **ADB pela depuração sem fio** (abre `Android/data` e `Android/obb`, que o Android 11+ esconde, **sem root**) e **root** (tudo, até `/data/data`). · **🌍 Publicar site**: uma página/site HTML num link (rede local ou internet, pelo túnel da Cloudflare; não lista pastas nem mostra arquivos ocultos; **até 5 sites no ar ao mesmo tempo**, cada um com o seu link) com **endereço fixo com o seu domínio** (em 🛡️ Rede e segurança → 🌉 Pontes → ☁️ Cloudflare; túnel criado no painel da Cloudflare: cola o token do painel, o app descobre sozinho os endereços cadastrados e o que cada um abre, testa cada um pela internet; o link não muda mais, nem depois de reiniciar o celular, e vale também para o servidor de filmes e a API), com **QR code do link** na tela e **opção de baixar a imagem** (.png na pasta Download) e **ver quem acessou**: para cada visitante, o **IP real** (mesmo pelo túnel da Cloudflare, lido do cabeçalho `CF-Connecting-IP`, que só vale quando vem do próprio túnel: no Wi-Fi ninguém consegue fingir outro IP ou país), o **país** (bandeira) e, com endereço fixo, a **cidade e o estado** (cabeçalhos de localização da Cloudflare), o **aparelho, o modelo e o navegador** (Android/iPhone/Windows com versão, Samsung Internet, Brave, navegador do Instagram/Facebook/TikTok...), o idioma, **de onde veio** (Instagram, WhatsApp...), as **páginas vistas** (imagens, CSS e JS não contam como visita) e quando chegou; separa as **prévias de link** (WhatsApp, Telegram...), os buscadores e as **varreduras** de quem procura falhas (e mostra o que tentaram abrir); os acessos feitos no próprio celular não entram na conta. Dá para ver **tudo o que um visitante abriu**, os últimos acessos, **acompanhar ao vivo**, consultar a **operadora e a cidade aproximada** do IP, salvar numa **planilha .csv** e **receber uma notificação quando alguém novo abrir o link**. Se outro site ocupar o mesmo espaço, as visitas do anterior ficam guardadas à parte. É o registro de acessos ao seu próprio site, que dá para limpar quando quiser. **📡 Compartilhar na rede** (HTTP rápido e **Samba**, porta 4450, experimental), **☁️ Nuvem e sincronização** (**rclone**: Drive, Dropbox, OneDrive... copiar/sincronizar e servir via WebDAV com senha; **Syncthing**) e **💾 backup**/restauração do Termux em `.tar.gz`. **Compartilhar pasta** pelo navegador agora deixa **mandar arquivos** para ela (opcional), pede **senha** se você quiser e mostra o **QR code** do link · **📦 croc**: manda arquivos ou texto para outro aparelho com um código. |
| 7 | 🎵 **Música, rádio e podcasts** | Organizado em **▶ Ouvir**, **⬇️ Baixar**, **📻 Rádio**, **🎙️ Podcasts** e **📚 Biblioteca e playlists**. Busca e toca por streaming, baixa no **formato que você escolher** (MP3, Opus, M4A, FLAC, WAV ou original), baixa por link (YouTube, SoundCloud, playlists) e por **link do Spotify** (procura a música no YouTube), mix/rádio por busca, **💿 álbuns** (busca pelo nome, mostra as faixas e toca o álbum inteiro em ordem, ou **baixa o álbum** numa pasta `Artista/Álbum (ano)` com as faixas numeradas) e **🎤 todas as músicas de um cantor ou banda** (toca as mais ouvidas ou a discografia inteira sem repetir, em ordem ou no aleatório; **baixa** as mais ouvidas, todos os álbuns ou só os que você escolher, cada álbum na sua pasta) — a lista de faixas vem do catálogo público do Deezer (sem conta nem chave), o áudio vem do YouTube, as etiquetas (artista, álbum, faixa, ano) saem certas e baixar de novo pula o que já está no celular, biblioteca local e playlists `.m3u`. **Player próprio**: tela *Tocando agora* com o nome da música e do artista, barra de tempo e a fila; continua tocando fora do menu, com **notificação de mídia** (anterior, pausar, tocar, pular, ⏩ +30 s e parar) e, se você quiser, **fala o nome de cada música** que começa. **Equalizador de 10 bandas** (31 Hz a 16 kHz) com pré-amplificador e presets, que vale para tudo o que tocar e pode ser gravado nas músicas baixadas. **Descobre a música de um arquivo pelo som** (mp3, mp4, opus...), com o Chromaprint e o AcoustID, e pergunta se quer tocar. · **rádio online do mundo todo** (mais de 50 mil estações: por país, idioma, gênero, mais ouvidas, surpresa, Brasil por gênero ou estado, favoritas), mostra a música que a rádio diz estar tocando e tem **legenda automática** da fala (whisper.cpp no celular), que pode ser traduzida para o português · **podcasts** (busca, seguir, ouvir e baixar episódios) · **🎤 letra da música** que está tocando, sincronizada linha por linha (LRCLIB). |
| 8 | 🎬 **Vídeos (TikTok, YouTube)** | Baixa vídeos no **formato e na qualidade que você escolher**, direto na **pasta Download do celular** (se o Termux não tiver a permissão, pede; o que tinha ficado preso numa pasta interna do Termux é levado para a pasta certa; mostra onde cada arquivo foi salvo e avisa a Galeria) (MP4, MKV, WebM ou só o áudio; 360p a 1080p) por link (TikTok, YouTube, Shorts, playlists e outros sites que o yt-dlp aceita), busca no YouTube e baixa, abre os vídeos baixados no player do Android e **assiste um link sem baixar** no VLC/MX Player (link direto de arquivo ou página do YouTube/TikTok, escolhendo a qualidade máxima: até 1080p, 720p ou 480p). **Reduz a resolução ou comprime um vídeo** (o único lugar com essa opção) que trava ou está grande demais para mandar (4K → 1440p, 1080p, 720p, 480p ou 360p), de um arquivo do celular ou **direto de um link, sem baixar o 4K**: imagem em H.264 (a mais leve de tocar), opção de baixar 60 para 30 quadros por segundo, cores de vídeo HDR ajustadas para a tela comum, todas as trilhas de áudio e legendas mantidas, modo **arquivo bem menor** para o WhatsApp, filme de cinema ou vídeo em pé sem esticar; mostra o andamento e quanto falta, ou converte em segundo plano e avisa com uma notificação (toque para abrir). Ao abrir um vídeo baixado em 4K, oferece fazer a cópia mais leve antes. |
| 9 | 📺 **Compartilhar filme por link** | Servidor de vídeo próprio: **catálogo da sua biblioteca do TorBox** (todos os filmes e séries num link só, com episódios e continuar assistindo); escolha um filme do celular **ou cole qualquer link de vídeo (sem baixar o filme)**: link direto de arquivo (servidor seu, nuvem, debrid...) ou página de vídeo (YouTube, Vimeo... pelo yt-dlp), receba um **link secreto** (com prazo opcional) e quem abrir assiste num **player próprio** no navegador: barra de progresso com prévia do tempo, **troca de trilha de áudio** (dublado/original), legendas (arquivo ao lado, extra ou **embutidas**) com tamanho e sincronia ajustáveis, velocidade, tela cheia, janela flutuante, **toque duplo para pular 10 s**, atalhos de teclado, **continuar de onde parou** e botão **Abrir no VLC**. MKV, áudio AC3/DTS e várias trilhas são **convertidos na hora** pelo ffmpeg (a imagem é só copiada; HEVC é recodificado só se o navegador não tocar). Também **converte para MP4** de vez, se preferir. Com o **endereço fixo** (seu domínio, em 🌉 Pontes → ☁️ Cloudflare), o link do filme e do catálogo não muda mais. Vídeo 4K travando? No player, **Ajustes → Qualidade** (1080p, 720p, 480p...) faz o celular converter na hora numa resolução menor, que pesa menos para tocar e para a internet; a escolha fica guardada no aparelho de quem assiste, e o player sugere isso quando o vídeo trava várias vezes. Ou faça antes uma cópia mais leve em **🎬 Vídeos → Reduzir a resolução**. Copia o link, manda pelo menu de compartilhar do Android (WhatsApp, Telegram...) ou mostra um QR code. Servidor, **túnel Cloudflare** (para quem está fora do seu Wi-Fi), porta e limpeza dos links ficam em **⚙️ Servidor, túnel e ajustes**. Apagar um link vale na hora. |
| 10 | 🧰 **Utilitários** | **🧮 Calculadora científica**: **Interface de calculadora com botões**: visor com a conta, a prévia do resultado e o modo DEG/RAD, e uma grade de botões que você percorre com as **setas** e aperta com **Enter** (o teclado também digita; Esc sai). Botões para trigonometria, `ln`/`log`, `e^x`, `√`, `∛`, potências, `n!`, `%`, `±`, `π`, `e`, `ans`, `EXP`, `mod`, fração, hexadecimal e histórico. Sem terminal interativo, abre o modo digitado. Na conta vale: `+ - * / ^`, `mod`, **fatorial** `5!`, **porcentagem** como no celular (`200+10%` = 220), `√9`, parênteses e **multiplicação implícita** (`2pi`, `3(4+5)`). Constantes `pi`, `e`, `tau`; **trigonometria** em graus ou radianos (`sin cos tan`, inversas, `sec csc cot`, hiperbólicas e inversas); `sqrt`, `raiz(x, n)`, `ln`, `log`, `log(x, base)`, `exp`, `mdc`, `mmc`, `comb`, `perm`; **estatística** (`soma`, `media`, `mediana`, `desvio`, `min`, `max`), `aleatorio`; números `1.5e3`, `0xFF`, `0b1010`; **variáveis** (`x = 5`), `ans` e histórico; comandos `hex`, `bin`, `oct` e `frac` para ver o resultado em outra base ou como fração. Não usa `eval`: só números e as funções da lista, com travas contra contas que travariam o celular. Não precisa instalar nada. · **Bloco de notas** (Markdown, tags, busca sem acento, exportar .zip) · **lista de afazeres** · **lembretes e alarmes** que tocam, vibram e falam (`18:30`, `amanhã 7h`, `25/12 08:00`, `em 10 min`; repetir todo dia, dias úteis, semanal ou mensal; serviço em segundo plano) · **cronômetro** com voltas, **timer** e **Pomodoro** em números grandes · **calendário** com as setas, **feriados nacionais** (Carnaval, Páscoa e Corpus Christi calculados), eventos e lembrete antes do evento · **conversor** de unidades (comprimento, massa, área com alqueire, volume, velocidade, tempo, dados, energia, pressão, temperatura) e **moedas** com a cotação do dia (funciona sem internet com a última cotação) · **controle de gastos** por categoria, orçamento do mês, histórico de 6 meses e planilha .csv · **cofre de senhas** criptografado (scrypt + AES), gerador de senha e frase-senha, verificação de senhas fracas/repetidas · **previsão do tempo** (Open-Meteo, por GPS ou cidade) e **alerta de chuva** · **QR code**: texto, **Wi-Fi** (conectar sem digitar a senha), **PIX copia e cola**, contato e **leitura** pela câmera · **tradutor** (detecta o idioma, traduz o que está copiado, fala a tradução) e **dicionário** português/inglês · **🔑 códigos 2FA** (como o Google Authenticator, guardados com senha) · **💹 criptomoedas e bolsa** (cotações e gráficos no terminal). |
| 11 | 🕵️ **Mensagens secretas** | Cada técnica com **ℹ️ Como funciona**, **codificar** e **decodificar** (o que sai fica em `Download/LNUX/Mensagens secretas`). **🖼️ Esteganografia** (esconder a mensagem): **texto dentro de uma foto** (bits menos significativos dos pixels, em PNG), **texto invisível** dentro de outro texto (caracteres de largura zero), **texto dentro de um áudio** WAV e **arquivo escondido dentro de uma foto** (a foto abre normal); com senha opcional, a mensagem é cifrada com AES antes · **🔒 Criptografia moderna**: **AES-256-GCM** com senha (chave pelo scrypt) para texto e para **arquivos**, modo **compatível com o OpenSSL** (abre em qualquer computador) e **bloco de uso único** (Vernam) · **📜 Cifras clássicas**: César (com **descobrir sem a chave** pela frequência das letras do português), ROT13, ROT47, Atbash, Vigenère, substituição com palavra-chave, cerca de trilhos, quadrado de Políbio, Bacon e A1Z26 · **🔢 Sistemas numéricos**: números entre binário, octal, decimal, hexadecimal e qualquer base de 2 a 36, e **texto ↔ binário/octal/decimal/hexa** (UTF-8) · **🔣 Alfabetos próprios**: invente um símbolo para cada letra e número (ou gere de emojis, runas, grego, símbolos ou setas, embaralhado), codifique, decodifique e **mande o alfabeto** a quem vai ler · **📡 Códigos**: Morse (com **o som em WAV**), Braille do português, Base64 e Base32. |
| 12 | 📲 **Celular e sistema** *(nas distros: 🖥️ Computador e Android conectado, com o ADB para um celular ligado por USB ou Wi-Fi e os recursos do computador no lugar do Termux:API)* | **Depuração sem fio (ADB)**: Conecta o `adb` do Termux ao **próprio celular** pela Depuração por Wi-Fi (Android 11+), **sem PC e sem root**: pareamento guiado (acha a porta sozinho), status, shell e comandos do Android, **impedir que o Android mate o Termux** (o erro *signal 9* dos processos fantasmas, Android 12+), print e gravação de tela, instalar APK, logcat, `pm grant` e liberar a porta 5555 para um computador. · **Termux:API**: sensores, SMS (enviar/ler), notificações, câmera, localização, vibração, lanterna, área de transferência e volume · **Painel do sistema** ao vivo com **rich** (CPU, RAM, disco, bateria, serviços) · **Saúde da bateria**: registro, gráfico de 24 h, ciclos estimados, consumo por hora e alertas de **80% carregando**, bateria baixa e temperatura · **tempo de tela** e **internet gasta por app** (móvel e Wi-Fi) pelo ADB sem fio · **gerenciador de apps** pelo ADB, sem root: abrir, forçar parada, permissões, extrair APK, **desativar/remover bloatware** (reversível) · **resolução da tela**: diminui a resolução do celular inteiro ou de **um app só** (Android 12+), com root ou pelo ADB sem fio; toda mudança **volta sozinha em 1 minuto** se você não confirmar · **fotos**: organizar por data, repetidas, **parecidas**, comprimir e **tirar a localização (GPS)** antes de compartilhar · **conversor de arquivos**: imagens (JPG/PNG/WEBP/PDF), várias imagens → PDF, vídeo → GIF/áudio, áudio do WhatsApp → MP3, PDF juntar/separar/comprimir/para imagens/para texto e Word/Excel/PowerPoint → PDF (LibreOffice na distro) · **automação por eventos** (um "Tasker"): horário, intervalo, entrar/sair de um Wi-Fi, carregador, bateria → notificação, voz, vibração, volume, lanterna, link, Telegram, TV ou comando · **espelhar a tela** com scrcpy (outro celular aqui no Termux:X11, ou este celular num PC) e **transmitir a tela por link**: quem abre o link vê a tela no navegador, na mesma rede ou **pela internet com o túnel da Cloudflare**, sem instalar nada; o controle pelo navegador (toques, arrastar, Voltar/Início, digitar) é opcional e começa bloqueado. · **Controle da TV**: liga/desliga e controle remoto na tela (volume, canal, setas, OK) pelo **infravermelho do celular** (qualquer TV, com busca automática do código) ou pelo **Wi-Fi** (Samsung, LG, Android TV/Google TV, Roku), com atalho na tela inicial, automação e bot; **desligar TVs por perto** (TV-B-Gone) · **controle de outros aparelhos** por infravermelho (soundbar/som, projetor, TV box e **ar-condicionado** por presets), no estilo dos controles universais do Flipper Zero. · **📶 Modem (comandos AT)** (3GPP, só no seu aparelho e com root): chamadas (ATD/ATA/ATH), SMS (CMGS/CMGL/CMGD), sinal e registro (CSQ/CREG/COPS), APN e dados (CGDCONT/CGACT/CGPADDR) e informações do aparelho (IMEI/fabricante/modelo) · **🖥️ Ficha do sistema** (estilo neofetch) e **⚙️ processos ao vivo** (estilo htop). |
| 13 | 🌐 **Internet e comunicação** | **E-mail** (Gmail, Outlook, Yahoo, iCloud...): caixa de entrada, não lidos, busca, ler, responder, anexos, apagar e enviar com anexo · **notícias** por RSS (g1, BBC, Agência Brasil, Folha, Tecnoblog...) com **modo leitura**, ouvir em voz alta e favoritos · **gerenciador de downloads** (aria2): links, **magnet** e **.torrent**, fila, pausar/continuar, acompanhar ao vivo · **chat na rede local** entre celulares, sem internet, com senha e envio de arquivos · **🌐 navegador pelo celular**: uma página web no celular em que você digita um endereço ou uma busca e o **celular carrega o site pela conexão dele** e devolve pronto (bom para pesquisar, ler notícias e Wikipédia; abre em qualquer aparelho pelo link, sem configurar), com os vídeos e músicas tocando no **VLC Web** com um toque (as pontes de conexão ficam em 🛡️ Rede e segurança) · **navegador no terminal**: **[Browsh](https://www.brow.sh/)** (sites modernos com o Firefox por trás, do `x11-repo`) e **w3m** (leve), pesquisa, modo leitura e salvar página · **encurtador de links**, **pastebin** e **enviar arquivo e gerar link** (temporário ou permanente), com QR code e histórico. |
| 14 | 🧩 **Apps Web** | Editores que abrem no navegador, do repositório [LNUX-APPs](https://github.com/Gustavo-HVF/LNUX-APPs): **🎬 Vídeo** (linha do tempo, cor, transições, títulos, legendas, exporta MP4), **✨ Efeitos** (animação de títulos e gráficos com quadros-chave, exporta GIF/PNG/MP4) e **🎚️ Som** (estúdio multipistas: gravar, editar, mixar, exporta WAV/MP3). O LNUX baixa, liga o servidor com a **ponte local** (pastas do aparelho, ffmpeg) e abre o app já com a chave; também abre em outro aparelho da rede (QR code) ou **pela internet, com um túnel** (link https). Também **🐧 conecta ao [TNUX](https://github.com/Gustavo-HVF/TNUX-DistroSystem)**, a área de trabalho no estilo do Linux Mint ligada a este aparelho. Veja [Apps Web](#apps-web). |
| 15 | 👤 **Meus dados na internet** | O que está **público sobre você**, num lugar só: **Receita Federal** (situação do CPF, comprovante do CNPJ, e-CAC; confere os dígitos do CPF e mostra a região onde foi emitido; dados abertos do seu **CNPJ/MEI**, que costumam expor o endereço de casa) e **Registrato** do Banco Central (contas, empréstimos e chaves PIX no seu CPF) · **Portal da Transparência** (servidor, Bolsa Família, BPC, diárias, sanções; consulta automática pelo CPF com a chave grátis da API) · **Tribunais de Justiça e TRFs** (Jus.br do CNJ com gov.br, o TJ do seu estado e o TRF da sua região com o CPF copiado, os 27 TJs e 6 TRFs, Jusbrasil e Escavador) · **Google** (nome exato, nome + cidade, PDFs e planilhas, CPF, e-mail, celular, @, imagens e notícias) · **LinkedIn, Instagram e Facebook** · **Diário Oficial** (DOU e os diários das prefeituras pelo **Querido Diário**, com o trecho e a cidade na tela) · **Lattes** · **vazamentos** (e-mail no Have I Been Pwned e **senha vazada** sem a senha sair do celular) · onde **pedir a remoção** dos seus dados. **Verificar tudo** faz as consultas e gera uma **página com todas as buscas prontas** para tocar.
| 16 | ✨ **Inteligência artificial** | **Assistente na nuvem**: **Claude** (SDK oficial `anthropic`, modelo padrão `claude-opus-5-5`), **ChatGPT** ou **Gemini** com a sua chave de API; conversa com histórico, mandar **foto**, resumir **PDF/livro/página/texto copiado**, salvar a conversa como nota · **voz para texto** com **whisper.cpp** compilado no celular (transcreve **áudios do WhatsApp** e **ditado**, sem mandar nada para a internet) e texto para voz (idioma e velocidade) · **OCR**: lê o texto de foto, imagem ou do último print (tesseract, português e inglês), e copia, traduz, salva ou pergunta à IA. · **Traduzir a tela**: tire um print e a tradução chega numa notificação (ou capture pelo ADB/root; modo contínuo para jogos). · **Remover o fundo** de foto ou vídeo e deixar só a pessoa, no próprio celular: fundo transparente, tela verde, branco, preto, desfocado ou outra imagem. · **IA local, sem internet**: Clona e **compila o llama.cpp no próprio celular**, baixa modelos GGUF de 1B a 3B (Gemma 3 1B, Llama 3.2 1B/3B, Qwen2.5 1.5B/3B, Qwen3 1.7B, Gemma 2 2B ou URL própria, com download retomável), conversa no terminal (`llama-cli`) ou sobe o `llama-server` (interface web + API compatível com OpenAI). O bot e a API usam o modelo com `/ia`. |
| 17 | 🎮 **Diversão e aprendizado** | **Jogos**: 2048, campo minado (3 níveis), sudoku com solução única, forca (6 temas), jogo da velha contra o celular (até "impossível"), Tetris, Snake, adivinhe o número e quiz de conhecimentos gerais, com recordes · **aprender programação**: lições de **Python**, **Bash** e **Git** com exercícios corrigidos na hora, **interpretador BASIC** retrô (PRINT, INPUT, IF/THEN, GOTO, GOSUB, FOR/NEXT, matrizes, SAVE/LOAD...) e gerador de **template para criar seu próprio jogo** · **leitor de livros** EPUB/PDF/TXT que lembra onde parou e lê em voz alta (audiolivro) · **arte ASCII**: texto grande (figlet) com arco-íris e imagem colorida no terminal (que pode virar o banner do menu) · **trote/pegadinha (screamer)**: publica um link (rede Wi-Fi ou túnel Cloudflare) com uma página que dá um susto em quem abrir — grito alto, imagem em tela cheia, tela piscando, vibração e notificações em sequência — **notificações de verdade do Android** pelo link da internet (túnel), quando a pessoa toca em "Permitir"; no link da rede Wi-Fi (sem HTTPS) o navegador bloqueia e aparece uma imitação dentro do site. Dá para personalizar no Termux o som, a imagem, a mensagem, o nome do site, a cor, o atraso, **quanto tempo dura o susto** (depois a página para tudo e revela que era trote) e ligar/desligar cada efeito (grito sintético e rosto embutidos quando você não escolhe os seus); o que você muda já vale no link publicado. A tela pisca no máximo 2 vezes por segundo (abaixo do limite de risco para epilepsia fotossensível) e não pisca nem treme para quem ativou "reduzir movimento" no celular. Use só com quem topa a brincadeira · **⌨️ Teste de digitação** (palavras por minuto, em português) e **🌌 telas de descanso** (Matrix, canos, aquário). |
| 18 | 🛠️ **Programação e servidores** | **Banco de dados**: SQLite (tabelas, SQL, importar/exportar CSV) e servidores **MariaDB/MySQL** e **PostgreSQL** · **GitHub** com o `gh`: seus repositórios, clonar, issues, PRs, criar repositório e assistente de **commit e push** · **⏲️ agendar comandos** com cron (limpeza, atualização, backup ou comando seu, com log) · **servidores**: **Minecraft Java** (instala a versão e o Java certos, EULA, console e desligar salvando), **Jellyfin** (filmes e séries) e **Navidrome** (música). · **Ambiente de desenvolvimento**: Instala git, Neovim, C/C++ (clang/clangd), Rust (rust-analyzer), Go (gopls), pyright, lua-language-server; gera um `init.lua` com **LSP nativo** (sem plugins), configura git e chave SSH, testa os compiladores e roda o **code-server** (VS Code no navegador). Também instala o **Textual**, para criar seus próprios apps de terminal · **📚 cola de comandos** (tldr), **🔌 testar uma API** (HTTP com JSON colorido e o comando curl equivalente), **🔍 ver JSON e Markdown**, **🎬 gravar o terminal** (asciinema) e **🐳 contêineres** Docker/Podman (nas distros). |
| 19 | ⚙️ **Sistema e manutenção** | Junta tudo o que é manutenção. **🐧 Trocar o sistema** e ver o que o LNUX sabe dele (perfil, pastas, recursos e equivalentes). **🔄 Atualização**: `pkg upgrade`, troca de espelho (`termux-change-repo`), repositórios extras (x11/root/tur), pacotes pip, `git pull` em vários repositórios e no próprio LNUX, limpeza de cache e **atualizar tudo** de uma vez (Termux, pip, distros e LNUX). O llama.cpp se atualiza em ✨ IA → IA local. · **🧹 Otimização e limpeza**: **Otimização rápida** (cache do apt, `~/.cache` com pip/yt-dlp/go, npm, temporários antigos, `__pycache__`, logs velhos e miniaturas da galeria) mostrando quanto liberou; escolher item a item; **limpar o cache de todos os apps** (`pm trim-caches` com root ou, **sem root, pela depuração sem fio** (📲 Celular e sistema → 🔌); se nenhum dos dois estiver disponível, abre a tela de armazenamento do Android); ver o que ocupa espaço; achar **arquivos grandes**, **duplicados** e pastas vazias; processos do Termux que mais usam RAM; parar todos os serviços; compilação dos apps e TRIM (root); atalhos para as telas de armazenamento e bateria. · **📦 Instalar dependências** por área, de uma vez (essenciais, música, vídeos; cada opção do menu também instala sozinha o que falta, perguntando antes) · **🎨 Aparência do terminal**: **tema de cores do Termux** (Dracula, Nord, Gruvbox...), **fonte do terminal** (usa uma fonte .ttf/.otf baixada no celular, até dentro de um .zip, e volta sozinha em 1 minuto se você não confirmar), mensagem de boas-vindas e banner original · **⚙️ Configurações e diagnóstico**: Ver e editar a configuração (`config.json`), liberar ou bloquear o comando `sh` dos bots, **diagnóstico** (programas e módulos instalados, Termux:API respondendo, serviços ativos) · **💽 Explorar o espaço** (estilo ncdu), **🐚 shell bonito** (zsh com Oh My Zsh ou o prompt Starship) e **🛎️ serviços e logs do sistema** (systemd ou OpenRC, nas distros). |

Antes de baixar, o programa **pergunta o formato** (e, no vídeo, a qualidade). A escolha fica lembrada e vira o
padrão da próxima vez:

| Música | Para quê |
|--------|----------|
| Opus | arquivo menor com ótima qualidade |
| MP3 320 kbps | toca em qualquer aparelho, som do carro, pendrive |
| M4A (AAC) | iPhone e aparelhos da Apple |
| FLAC | sem perdas (arquivo bem maior) |
| WAV | sem compressão, para editar |
| Original | como veio do site, sem converter (mais rápido) |

| Vídeo | Para quê |
|-------|----------|
| MP4 | toca em qualquer celular, TV e computador (prefere H.264 + AAC) |
| MKV | a melhor qualidade do site, sem converter |
| WebM | formato aberto (VP9/AV1), arquivos menores |
| Só o áudio (MP3) | quando só interessa o som |

Qualidade do vídeo: melhor disponível, 1080p, 720p, 480p ou 360p (o mais próximo sem passar dela). Por exemplo,
MP4 em 720p vira:

```bash
yt-dlp -f "bv*+ba/b" -S res:720,vcodec:h264,ext:mp4:m4a --merge-output-format mp4 --remux-video mp4 \
       --trim-filenames 150 -o "~/storage/downloads/%(title)s.%(ext)s" "<link>"
```

(`--trim-filenames` encurta nomes enormes, como os de legendas do TikTok; as pastas podem ser trocadas nos menus.)
Na linha de comando: `baixar --formato mp3 ...` e `video --formato mp4 --qualidade 720 ...`.

## Linha de comando

Os serviços em segundo plano chamam o próprio script; você também pode usar direto:

```bash
python lnux.py                      # menu
python lnux.py sistema               # o sistema em uso: perfil, pastas, recursos e equivalentes do Termux
python lnux.py sistema --listar      # os perfis disponíveis (distros/*.json e ~/.lnux/distros/*.json)
python lnux.py sistema arch          # troca o sistema (também pelo menu ⚙️ Sistema e manutenção)
python lnux.py ficha                 # a ficha do sistema (estilo neofetch)
python lnux.py apps                  # abre os Apps Web no navegador (liga o servidor e a ponte)
python lnux.py apps video            # abre direto um app (video, som, efeitos...)
python lnux.py tnux                  # abre o TNUX (área de trabalho no estilo do Linux Mint) ligado a este aparelho
python lnux.py tnux compartilhar     # o TNUX deste aparelho por um link https da Cloudflare (com QR code)
python lnux.py serve --framework stdlib --porta 8000
python lnux.py bot telegram
python lnux.py monitor [--uma-vez]
python lnux.py dashboard | tarefas | snake | doctor
python lnux.py basic [programa.bas]
python lnux.py baixar "https://youtu.be/..." "artista - música" "https://open.spotify.com/track/..."
python lnux.py video "https://www.tiktok.com/@user/video/..." "https://youtu.be/..."
python lnux.py compartilhar ~/storage/downloads/filme.mp4 --horas 24   # cria o link e liga o servidor
python lnux.py compartilhar "https://seu-servidor/Filme.mkv" --legenda filme.pt.srt
python lnux.py compartilhar "https://www.youtube.com/watch?v=..."      # página de vídeo também vale
python lnux.py assistir "https://seu-servidor/Filme.mkv"              # abre no VLC do celular
python lnux.py navegador --porta 8101   # navegador pelo celular em primeiro plano (crie o link pelo menu antes)
python lnux.py vlc-web              # baixa/atualiza do GitHub o VLC Web usado pelo navegador (--remover apaga)
python lnux.py midia                # servidor de vídeo em primeiro plano
python lnux.py site ~/storage/downloads/meu-site --porta 8097   # publica uma pasta como site
python lnux.py pasta ~/storage/downloads --porta 8090   # compartilha a pasta pelo navegador (envio e senha: pelo menu)
python lnux.py tela --porta 8093   # transmite a tela (crie o link pelo menu antes)
python lnux.py arquivos ~/storage/downloads   # gerenciador de arquivos
python lnux.py desktop debian   # abre o desktop da distro no Termux:X11
python lnux.py tocar                # biblioteca no aleatório
python lnux.py tocar lofi hip hop   # mix por busca
python lnux.py player pausar        # também: abrir, proxima, anterior, parar
python lnux.py baixar "artista - música" --equalizador   # grava o equalizador no arquivo
python lnux.py atualizar
python lnux.py limpar                # otimização rápida, sem perguntas
python lnux.py lembretes             # serviço de lembretes e alarmes
python lnux.py bateria-log           # registro da bateria e alertas (80%, baixa, quente)
python lnux.py automacao             # serviço de automação por eventos
python lnux.py resolucao             # desfaz a última mudança de resolução ou volta a tela à de fábrica
python lnux.py tv                    # liga/desliga a TV; também: ligar, desligar, vol+, vol-, mudo, controle
python lnux.py tv desligar --tv Quarto
python lnux.py tvbgone               # desliga as TVs por perto (TV-B-Gone)
python lnux.py aparelho "Som da sala" Vol_up   # som/projetor/ar por infravermelho ('controle' abre a tela)
```

## Mensagens secretas

Em **🕵️ Mensagens secretas** (menu principal) há três ideias diferentes, que dá para combinar:

- **Esconder** (esteganografia): a mensagem vai dentro de outra coisa e ninguém percebe que ela existe.
- **Cifrar** (criptografia): a mensagem fica à vista, mas embaralhada; só quem tem a senha lê.
- **Codificar**: escrever de outro jeito (binário, Morse, Braille, um alfabeto inventado). Não protege: quem
  conhece o código lê.

Cada técnica tem **ℹ️ Como funciona**, **codificar** e **decodificar**. O resultado aparece na tela com as opções
de copiar, salvar num `.txt` ou mostrar como QR code.

| Técnica | Detalhes |
|---|---|
| 🖼️ Texto dentro de uma foto | Troca o último bit de cada cor dos pixels (invisível a olho nu). Sai em PNG; **mande como arquivo**, porque enviada como foto ela é recomprimida e a mensagem some. Precisa do Pillow (instalado na hora, perguntando) |
| 👻 Texto invisível | A mensagem vira caracteres de largura zero, logo depois da 1ª letra de um texto comum ("Bom dia!"). Alguns apps apagam esses caracteres: teste antes |
| 🎵 Texto dentro de um áudio | O último bit de cada amostra de um WAV de 16 bits. MP3, OGG e outros são convertidos para WAV antes (ffmpeg) |
| 📎 Arquivo dentro de uma foto | O arquivo vai grudado no fim da foto, que continua abrindo normal |
| 🔒 AES-256 com senha | AES-256-GCM (também acusa se a mensagem foi alterada), chave pelo scrypt. Texto (`LNUX-AES1:...`) ou arquivo (`.lnuxcripto`). Usa a biblioteca `cryptography`, a mesma do cofre de senhas |
| 🧰 Compatível com o OpenSSL | `openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -a -A` abre a mensagem em qualquer computador |
| 🎲 Bloco de uso único | Vernam: XOR com uma chave aleatória do tamanho da mensagem, usada uma vez só |
| 📜 Cifras clássicas | César (+ descobrir sem a chave), ROT13, ROT47, Atbash, Vigenère, substituição, cerca de trilhos, Políbio, Bacon, A1Z26. Oferece tirar os acentos antes (elas só mudam a–z) |
| 🔢 Sistemas numéricos | Números entre as bases 2, 8, 10, 16 (e de 2 a 36); texto ↔ binário, octal, decimal e hexadecimal |
| 🔣 Alfabetos próprios | Guardados em `~/.lnux/alfabetos.json`. **📤 Mandar** gera um texto `lnux-alfabeto:...` que a outra pessoa cola em **📥 Receber** |
| 📡 Morse, Braille, Base64, Base32 | Morse com o som em `.wav`; Braille com os acentos do português, números (⠼) e maiúsculas (⠨) |

Nas opções de esconder, dar uma senha cifra a mensagem com AES-256 antes de esconder: mesmo quem souber onde
procurar não lê sem a senha. Os testes de todas as técnicas estão em `tests/testar_mensagens_secretas.py`.

## Apps Web

Menu **🧩 Apps Web**: editores de vídeo, som e animação que abrem no navegador do celular ou do computador. Eles
ficam num repositório à parte, o [LNUX-APPs](https://github.com/Gustavo-HVF/LNUX-APPs) (só HTML, CSS e
JavaScript), que o LNUX baixa na primeira vez em `~/.lnux/lnux-apps` (e atualiza em *🔄 Atualizar*).

| App | O que faz |
|-----|-----------|
| 🎬 Vídeo | Linha do tempo com várias trilhas de vídeo e áudio: cortar, aparar, mover, velocidade; cor com "looks" prontos; movimento e tamanho arrastando no monitor; transições; títulos animados e legendas SRT; exporta WebM, ou MP4 e GIF pelo ffmpeg |
| ✨ Efeitos | Animação de títulos e gráficos: camadas de texto, forma, partículas, imagem e vídeo; quadros-chave com suavização (freando, quicando, elástico); 12 animações prontas e 7 modelos; exporta GIF e PNG (com transparência) direto no navegador, WebM, ou MP4 pelo ffmpeg |
| 🎚️ Som | Estúdio multipistas: gravar pelo microfone, importar, cortar, fades, normalizar; mixer com EQ, compressor, eco e reverb por trilha; BPM, grade, metrônomo e loop; exporta WAV, ou MP3/OGG/FLAC/M4A pelo ffmpeg |

Ao abrir um app, o LNUX liga o servidor do LNUX-APPs em segundo plano (serviço `apps-web`, no tmux) com a
**ponte local**: com ela, os apps abrem e salvam direto nas pastas do aparelho, usam o ffmpeg e leem bateria e
área de transferência. A ponte só escuta neste aparelho, exige uma chave (que vai no endereço quando o LNUX
abre o app) e só mexe na pasta pessoal e no armazenamento interno, mais as pastas que você liberar em
*⚙️ Ponte*. Lá também dá para fazer a ponte ligar só nos apps que não funcionam sem ela.

*📡 Abrir em outro aparelho da rede* liga o servidor para o Wi-Fi e mostra o link com um QR code (quem tiver o
link usa a ponte deste aparelho: só em redes suas).

*🌍 Compartilhar pela internet (túnel)* gera um link **https** que abre os Apps Web **de qualquer lugar**, até
fora da sua rede Wi-Fi: no seu computador do trabalho, no celular de um amigo. O link vem com um QR code.

- Usa um túnel rápido da Cloudflare (`cloudflared`, grátis, sem conta), que o LNUX instala se faltar.
- Um servidor separado (serviço `apps-web-tunel`, porta 8096) atende o túnel, então o de sempre não muda.
- Esse servidor aceita **só aquele endereço** e **nunca roda programas**.
- Você escolhe o que compartilhar:
  - **Só os apps** (recomendado): quem abre usa os apps no navegador dele, sem acesso a este aparelho;
  - **Os apps e a ponte**: as pastas liberadas e o ffmpeg deste aparelho. O link leva a chave, então é só para
    você mesmo, e o LNUX pede confirmação.
- O endereço muda toda vez que o túnel liga. Com o *Endereço fixo* (túnel da Cloudflare com o seu domínio)
  apontado para a porta do túnel, o LNUX usa esse endereço no lugar.
- *🌍 Túnel: desligar* fecha o link. Este aparelho continua sendo o servidor: precisa ficar ligado e com internet.

Tema e layout ficam no botão ◐ de cada app; o projeto fica
guardado no navegador. Na linha de comando: `python lnux.py apps` (página inicial) ou `python lnux.py apps som`.

### 🐧 TNUX: conectar à área de trabalho no estilo do Linux Mint

Dentro de **🧩 Apps Web**, a opção **🐧 TNUX** liga este aparelho ao
[TNUX](https://github.com/Gustavo-HVF/TNUX-DistroSystem), do mesmo autor: um sistema com núcleo em C e uma área de
trabalho no estilo do Linux Mint (painel, menu, janelas, terminal, arquivos, editor, gerenciador de aplicativos)
que abre no navegador. Na primeira vez, o LNUX baixa o TNUX em `~/.lnux/tnux` e compila (precisa do `make` e de
um compilador C, que ele instala se faltar).

O TNUX roda no **modo ponte**: o terminal da área de trabalho é o shell deste aparelho, o gerenciador de
arquivos mostra as pastas daqui e o gerenciador de aplicativos instala programas de verdade. O próprio LNUX
aparece lá dentro, no programa **LNUX**, com as opções dele por categoria.

| Opção | O que faz |
|---|---|
| 🖥️ Abrir a área de trabalho | Liga o TNUX em segundo plano (serviço `tnux-desktop`, porta 8097) e abre no navegador, já com a chave |
| 📡 Abrir num computador da rede | Religa para o Wi-Fi e mostra o link com QR code. O computador que abrir também empresta o processador ao celular (`tnux pc`) |
| 🌍 Compartilhar pela internet | Um link **https** da Cloudflare (`cloudflared`, grátis e sem conta) que abre o TNUX deste aparelho de qualquer lugar, com QR code |
| ⌨️ O shell do TNUX aqui no terminal | O shell do TNUX (prompt, histórico, Tab) com os comandos rodando neste aparelho |
| 🧮 O computador processa para o celular | Mostra os computadores conectados e os comandos `tnux pc` (converter imagens, zip, comandos) |

- A área de trabalho exige uma **chave**, que muda toda vez que o TNUX liga. O LNUX a lê de `~/.tnux/ponte.json`
  e a põe no endereço ao abrir. **Quem tiver a chave controla este aparelho** (terminal, arquivos, programas).
- O link pela internet tem uma **chave própria**, que para de valer quando você desliga o link (*🌍 Link pela
  internet: desligar*).
- Na rede, a conexão não é cifrada: use só em redes suas.

Na linha de comando: `python lnux.py tnux` (abrir), `tnux rede`, `tnux compartilhar`, `tnux parar-link`,
`tnux parar`, `tnux terminal` e `tnux atualizar`.

## Ferramentas de terminal

Versões próprias, dentro do LNUX, das ideias dos programas de terminal mais usados do GitHub. Não são cópias:
cada uma foi escrita do zero em Python (quase sempre só com a biblioteca padrão) ou chama o programa original
quando ele é a melhor opção, instalando-o antes se faltar.

| Ferramenta | Inspirada em | Onde fica | O que faz |
|------------|--------------|-----------|-----------|
| 🖥️ Ficha do sistema | neofetch, fastfetch | 📲 Celular e sistema | Logo e cores do sistema, aparelho/modelo (Android), CPU, memória, disco, bateria, pacotes, shell e tempo ligado. Também `python lnux.py ficha`. |
| ⚙️ Processos ao vivo | htop, btop | 📲 Celular e sistema | Tela cheia que se atualiza sozinha: uso total de CPU e memória e os processos ordenados por CPU (`c`), memória (`m`) ou PID (`p`); `/` filtra, `k` encerra e `K` força. No Android só aparecem os processos do Termux (limite do sistema). |
| 💽 Explorar o espaço | ncdu, dust | ⚙️ Sistema › 🧹 Otimização | Pastas e arquivos por tamanho com barras; `Enter`/`→` entra, `←` volta, `d` apaga (pergunta antes), `o` abre. |
| 🐚 Shell bonito | Oh My Zsh, Starship | ⚙️ Sistema › 🎨 Aparência | Instala o zsh com Oh My Zsh (tema à escolha, sugestões enquanto digita e cores nos comandos) ou o prompt Starship (presets). Guarda uma cópia do `.zshrc` e tem **Desfazer**. |
| 🎬 Gravar o terminal | asciinema | 🛠️ Programação | Grava, assiste, apaga e manda para o asciinema.org (gera um link). Os `.cast` ficam em `Download/LNUX/Gravações do terminal`. |
| 📚 Cola de comandos | tldr | 🛠️ Programação | Exemplos práticos de qualquer comando, em português quando existe tradução. Baixa as páginas uma vez (≈ 8 mil comandos) e funciona sem internet. |
| 📦 croc | croc | 🗄️ Arquivos e backup | Manda arquivos ou um texto para outro aparelho, em qualquer rede, com um código de três palavras. |
| 🌐 Compartilhar pasta | python -m http.server, dufs | 🗄️ Arquivos › compartilhar na rede | Servidor próprio: lista e baixa (com retomada), **recebe arquivos** pelo navegador (arrastar e soltar, barra de progresso, nunca sobrescreve), **senha** opcional e QR code do link. Arquivos ocultos e caminhos para fora da pasta são recusados. Também `python lnux.py pasta`. |
| 📈 Ping com gráfico | gping | 🛡️ Rede › 🔍 Diagnóstico | Vários endereços ao mesmo tempo (o roteador, 1.1.1.1 e google.com, ou os que você digitar), cada um com gráfico ao vivo, mínimo, média, máximo e perda. |
| 📶 Internet por programa | nethogs, bandwhich | 🛡️ Rede › 🔍 Diagnóstico | Quanto cada programa está baixando e enviando agora. Precisa de root, por isso não aparece no Android. |
| 🔌 Testar uma API | HTTPie, curlie | 🛠️ Programação | GET/POST/PUT/PATCH/DELETE com cabeçalhos e corpo, resposta com JSON colorido, tempo e o **comando curl equivalente**; guarda o histórico para repetir. |
| 🔍 Ver JSON e Markdown | jq, fx, glow | 🛠️ Programação | Navega num JSON (arquivo, copiado ou da internet) mostrando o caminho no estilo do jq; lê Markdown formatado. |
| 🐳 Contêineres | lazydocker | 🛠️ Programação *(nas distros)* | Docker ou Podman: contêineres (logs, terminal, parar, iniciar, remover), imagens, baixar, rodar e limpar. |
| 🛎️ Serviços e logs | systemctl, journalctl | ⚙️ Sistema e manutenção *(nas distros)* | Status, iniciar, parar, ligar no boot e logs de cada serviço; os que falharam; erros desde que ligou; logs ao vivo. Funciona com systemd e com OpenRC (Alpine). |
| 🔑 Códigos 2FA | Google Authenticator, 2fa | 🧰 Utilitários | Códigos TOTP que se atualizam sozinhos. Adiciona pela foto do QR code, pelo link `otpauth://` ou pela chave; exporta em QR code. As contas ficam cifradas (AES-256-GCM) com a sua senha. |
| 🎤 Letra da música | sptlrx | 🎵 Música | A letra sincronizada da música que o player do LNUX está tocando, destacando a linha atual (do LRCLIB, guardada para a próxima vez); sem letra sincronizada, mostra a comum. |
| ⌨️ Teste de digitação | Monkeytype, ttyper | 🎮 Diversão | Palavras comuns do português (com ou sem acentos), 30 ou 60 segundos ou um número de palavras; palavras por minuto, precisão e recorde. |
| 💹 Cripto e bolsa | cointop, ticker | 🧰 Utilitários | As 20 maiores criptomoedas (preço em real, 24 h e 7 dias), busca com gráfico, e uma lista sua da bolsa (Ibovespa, ações, dólar) com a variação do dia e o gráfico do último mês. |
| 🌌 Telas de descanso | cmatrix, pipes.sh, asciiquarium | 🎮 Diversão | Chuva do Matrix, canos coloridos e aquário; qualquer tecla sai. |

Os dados de **cripto e bolsa** vêm do CoinGecko e do Yahoo Finance (gratuitos, sem cadastro) e servem para
acompanhar, não para operar: podem ter atraso e o Yahoo pode mudar o serviço sem avisar.

## Compartilhar um filme por link

1. Menu **📺 Compartilhar filme por link → Compartilhar um filme do celular**, escolha o arquivo, o título e o prazo.
2. O programa liga o servidor de vídeo (porta 8095) e mostra o link: `http://IP-do-celular:8095/v/<código secreto>`.
   Quem estiver **no mesmo Wi-Fi** já consegue assistir.
3. Para quem está **fora da sua rede**, ligue **⚙️ Servidor, túnel e ajustes → 🌍 Liberar na internet** (usa o `cloudflared`;
   o endereço público aparece na tela e vira o link que você envia).
4. Copie o link ou use **Enviar pelo WhatsApp, Telegram...**. Em **Meus links** dá para assistir no próprio
   celular, apagar um link (quem estiver com ele perde o acesso na hora); **Apagar TODOS os links** fica em
   **⚙️ Servidor, túnel e ajustes**.

### Transmitir de um link da internet, sem baixar

O filme não precisa estar no celular. Serve qualquer link de vídeo:

- **Link direto de um arquivo** — o mesmo tipo de link que você abriria no VLC: um servidor seu, Google Drive,
  Dropbox, OneDrive, serviços de debrid (TorBox, Real-Debrid, AllDebrid...), etc.
- **Página de vídeo** — YouTube, Vimeo, Dailymotion e os outros sites que o yt-dlp lê. O endereço do vídeo é
  achado na hora de assistir e renovado sozinho quando o site o expira. Quando o site entrega imagem e som
  separados (como o YouTube), o servidor junta os dois.

1. Menu **📺 → 🌐 Transmitir de um link da internet**, cole o link. O programa confere o link (sem baixar),
   mostra a duração, as trilhas de áudio e as legendas, e cria o link secreto como no passo a passo acima.
2. Enquanto a pessoa assiste, o celular busca só o pedaço do filme que está passando e repassa para ela. O
   endereço de origem nunca aparece para quem recebe o link.
3. Link direto que expirou (links de download costumam valer só algumas horas)? Gere outro e use **Meus links →
   Trocar o endereço do vídeo**: o link que você já enviou continua o mesmo.

Para só assistir no seu celular, use **🎬 Vídeos → Assistir um link sem baixar**: abre direto
no VLC ou em outro app de vídeo. Também aceita páginas do YouTube, TikTok etc. (o yt-dlp acha o vídeo).

### 🍿 Catálogo do TorBox: toda a sua biblioteca num link só

Em vez de criar um link para cada filme, o **📺 → 🍿 Catálogo do TorBox** mostra **todos os seus filmes e séries**
do TorBox (torrents, usenet e downloads da web) numa página no navegador:

1. No TorBox, vá em **Settings → API** e copie a *API Key*.
2. Menu **🍿 Catálogo do TorBox → Configurar a chave da API**, cole a chave (ela fica só no celular, no
   `config.json` com permissão 600, e nunca vai para o navegador).
3. **Abrir o catálogo neste celular** ou **Mostrar / enviar o link do catálogo** (com o túnel ligado, funciona fora do Wi-Fi).

Na página: busca, filtros (filmes, séries, baixando), ordenação, **episódios por temporada**, **continuar
assistindo** com a barra de progresso e capas geradas pelo nome. Clicou, abre no player com troca de áudio,
legendas `.srt` que vieram no torrent, botão de **voltar à biblioteca** e **próximo episódio**. O link de download
é pedido ao TorBox na hora de assistir (e renovado se expirar). Também dá para escolher um vídeo da biblioteca no
terminal e abrir no VLC do celular.

Quem tiver o link do catálogo vê **toda** a sua biblioteca: mande só para quem você confia. **Gerar um link novo**
corta o acesso do link antigo.

### O player

- **Trilha de áudio** (🎧): quando o filme tem mais de uma (dublado e original, por exemplo), quem assiste escolhe.
  Começa no áudio em português, se houver, e lembra a última escolha.
- **Legendas** (CC): `.srt`/`.vtt` ao lado do vídeo com o mesmo nome (`Filme.mkv` + `Filme.pt-BR.srt`), uma legenda
  extra que você indica ao criar o link (arquivo ou link) e as **embutidas** no MKV. Tamanho e sincronia
  (adiantar/atrasar) ajustáveis. Com áudio em português, liga sozinha só a legenda forçada.
- Barra de progresso com prévia do tempo, ±10 s (botões, setas ou **toque duplo** nas laterais da tela),
  velocidade, tela cheia (gira o celular sozinho), janela flutuante, atalhos (`espaço`, `←` `→`, `↑` `↓`, `F`,
  `M`, `C`, `A`, `0`–`9`) e **continuar de onde parou**.
- **Abrir no VLC** (em ⚙ Ajustes): abre o arquivo original no VLC, com todas as trilhas e legendas. O mesmo link
  terminado em `/video` serve para colar no VLC, Kodi ou numa TV.

Boas práticas e limites:

- O servidor só entrega os arquivos que você compartilhou, cada um por um código aleatório; não mostra pastas.
- O filme **sai do seu celular**: quem assiste usa o **upload** da sua internet (num link da internet, também o
  download). Mantenha o celular carregando (o `termux-wake-lock` é ativado sozinho). O túnel gratuito da
  Cloudflare é pensado para testes e pode ser lento.
- **Formatos:** MP4 (H.264 + AAC) e WebM tocam direto, com o arquivo original. MKV, áudio AC3/DTS/E-AC3 e
  arquivos com várias trilhas de áudio são **convertidos na hora** pelo ffmpeg: a imagem é copiada e só o áudio
  é recodificado, o que pesa pouco. HEVC/H.265 é copiado quando o navegador toca (Chrome, Edge e Safari
  recentes); nos outros, a imagem é recodificada em 720p, o que exige bastante do celular. Cada pessoa vendo um
  vídeo convertido usa um ffmpeg; o limite (3) fica em **Conversões ao mesmo tempo**.
- **iPhone/iPad (Safari):** toca MP4 direto (e troca a trilha de áudio do próprio MP4), mas não aceita a
  conversão na hora; para MKV, o player oferece **Abrir no VLC**. Ou use **Converter filme para MP4 compatível**:
  o modo *rápido* só troca o áudio (segundos/minutos); o *completo* recodifica o vídeo e, no celular, pode levar
  mais tempo que o filme.
- **Legendas embutidas num link:** para extraí-las o celular precisa ler o arquivo inteiro uma vez (fica em cache),
  por isso o programa pergunta antes quais preparar. Prefira o Wi-Fi.
- Compartilhe só o que você pode distribuir: vídeos seus, de domínio público, de licença livre ou com autorização
  de quem tem os direitos.

## Navegador pelo celular e VLC Web

*🌐 Internet* → **🌐 Navegador pelo celular**. Liga um servidor que é um
navegador dentro de uma página: quem abre o link (no mesmo Wi-Fi ou, com o túnel, de qualquer lugar) digita um
endereço ou uma busca, e o celular baixa o site pela conexão dele e devolve a página pronta.

- **Página inicial**: busca no DuckDuckGo, Bing, Google ou Wikipédia, atalhos que dá para editar, sites visitados
  recentemente (guardados só no aparelho de quem navega, com opção de desligar) e o cartão do VLC Web. Segue o
  tema claro/escuro do sistema e funciona sem internet no aparelho de quem abre.
- **Barra nas páginas**: voltar, avançar, início, endereço (com cadeado em https), recarregar, **▶ VLC** e um
  menu (copiar o endereço do site, abrir direto sem o celular, barra no topo ou embaixo, esconder a barra, sair
  deste aparelho). Ela se esconde ao rolar a página para baixo e fica num Shadow DOM, sem misturar com o CSS do site.
- **JavaScript pelo celular**: `fetch`, `XMLHttpRequest`, imagens e links criados por script, `history.pushState`
  e formulários também passam pelo celular. Caminhos como `/api/...` são levados para o site certo.
- **Endereços legíveis**: `/p/https/pt.wikipedia.org/wiki/Brasil`. Links relativos, redirecionamentos e listas de
  vídeo HLS (`.m3u8`) e DASH (`.mpd`) funcionam sozinhos. Os links antigos (`/r/...`) continuam valendo.
- **Cookies para o JavaScript dos sites**: os cookies ficam no celular, mas o navegador do visitante recebe uma
  cópia dos que o JavaScript pode ler (como o `csrftoken` do Instagram), presa ao caminho do site e com o nome
  marcado (`tt~site~nome`). A página só vê os do próprio site, os cookies `HttpOnly` nunca saem do celular, e o que
  o JavaScript grava (`document.cookie = ...`) volta para o celular e segue nos pedidos seguintes.
- **Vídeos de TikTok, Instagram, Facebook, YouTube, X e outros**: essas páginas costumam quebrar quando abertas
  pelo navegador (veja abaixo), mas o vídeo delas o celular acha com o **yt-dlp**. Abrir um link de vídeo desses
  sites (pela busca, por um link na página ou colando no cartão do VLC Web) mostra "Procurando o vídeo…" e abre
  o VLC Web tocando, ainda pela conexão do celular, com os cabeçalhos e cookies que o site exige para entregar o
  vídeo. *Abrir a página mesmo assim* mostra a página. Se o site pedir login, entre na conta pelo navegador: os
  cookies do visitante vão junto para o yt-dlp. Precisa do yt-dlp instalado (menu **▶ VLC Web → Instalar o yt-dlp**).

#### Por que TikTok, Instagram e Facebook abrem mal

Esses sites são aplicativos inteiros em JavaScript: conferem se estão no próprio endereço, usam WebSocket e
detectam robôs pela "impressão digital" da conexão segura (a do Python não é a de um navegador). Por isso o
navegador leva direto ao vídeo, pelo yt-dlp. Para usar essas redes por completo pela internet do celular, use o
**Proxy** (*Pontes de conexão → Proxy*): o navegador de verdade do PC faz tudo e só a conexão passa pelo celular,
ou experimente o modo completo (abaixo).

### 🧪 Modo completo (experimental)

Sites como o blockaway e o CroxyProxy abrem TikTok, Instagram e Facebook porque usam um motor que **reescreve o
JavaScript dos sites** (para eles acharem que estão no próprio endereço), guarda cookies e `localStorage` de cada
site e passa WebSocket. O modo completo traz um motor assim, aberto: o
**[Rammerhead](https://github.com/binary-person/rammerhead)** (MIT, sobre o `testcafe-hammerhead`), em Node.js,
rodando no próprio celular.

- Instale em *navegador pelo celular → 🧪 Modo completo → Instalar*: o LNUX instala o `nodejs-lts` e o
  Rammerhead pelo npm (algumas dezenas de MB) em `~/.lnux/motor-completo`. Ligue ali mesmo ou marque
  *Ligar junto com o navegador*.
- Com o motor ligado, a página inicial mostra a escolha **⚡ Leve / 🧪 Completo**. Ela vale para a busca, os
  atalhos e os visitados. A barra das páginas leves ganha *Abrir no modo completo*, e as páginas do modo completo
  ganham uma minibarra (**Início**, **▶ VLC** e **Leve**).
- O motor só escuta em `127.0.0.1`. O navegador pelo celular confere o link secreto, cria uma sessão do motor para
  cada aparelho (cookie `navrh`) e repassa os pedidos, inclusive WebSocket, sem os cabeçalhos do túnel que
  revelariam o IP de quem navega. O próprio motor recusa conexões para a rede local e para o celular, mesmo por
  nome de site ou redirecionamento.
- **Experimental**: pesa mais (memória e bateria), não foi testado no TikTok, Instagram e Facebook de verdade, e
  esses sites ainda podem detectar o acesso. A saída pelo túnel SSH ou Tor não vale para ele. Não compartilhe os
  endereços das páginas do modo completo: eles levam a sua sessão.

### ▶ VLC Web

O **[VLC Web](https://github.com/Gustavo-HVF/VLC-WEB)** é um reprodutor de mídia completo que roda no navegador
(legendas e busca de legendas, equalizador, troca de faixa de áudio, velocidade, filtros e conversão de MKV,
AVI, AC-3...). O navegador pelo celular **baixa o VLC Web do GitHub** (cerca de 1 MB, só na primeira vez) e o
serve no mesmo link, em `/vlc/`.

- O botão laranja **▶ VLC** da barra conta os vídeos e músicas achados na página (`<video>`, `<audio>`, links para
  arquivos de mídia, listas `.m3u8`/`.mpd` pedidas pelos players em JavaScript e links para páginas de vídeo do
  TikTok, YouTube, Instagram...). Um toque e eles abrem no VLC Web. *Procurar o vídeo desta página (yt-dlp)* tenta
  qualquer outra página. Colar no cartão do VLC Web o link de uma página (e não do arquivo) também usa o yt-dlp.
- Abrir um link de vídeo direto mostra uma página com **Assistir no VLC Web**, **Tocar aqui**, **Baixar** e
  **Copiar o link**.
- O vídeo **continua vindo pela conexão do celular**, com avanço por Range, por links `/m/...` assinados (valem
  para aquele site enquanto o link do navegador for o mesmo). Como o VLC Web e o vídeo ficam no mesmo endereço, ele
  lê as faixas de áudio e legendas, aplica efeitos e grava, o que costuma falhar com vídeos de outros sites.
- Dentro do VLC Web, os links de rede (*Mídia → Abrir transmissão de rede*, rádios, podcasts, busca de legendas e
  tradução pelo MyMemory) também passam pelo celular. *Mídia → Voltar ao navegador pelo celular* volta ao início.
- No menu do navegador, **▶ VLC Web** baixa ou atualiza a versão (o cartão da página inicial avisa quando há versão
  nova no GitHub), mostra o link de `/vlc/` e gera um **link pronto que abre um vídeo no VLC Web**, para mandar a
  alguém.

### Segurança do navegador

- Só abre quem tem o link (o `?t=...` vira um cookie e some da barra de endereço). *Gerar link novo* invalida o
  antigo e os links de vídeo feitos com ele.
- Nunca abre a rede local nem o próprio celular (127.0.0.1, 192.168.x.x, a API, o ADB...), nem `file://` ou
  `ftp://`, nem por redirecionamento.
- Cada aparelho tem os próprios cookies dos sites (quem entra numa conta não deixa os outros logados nela).
- Os cabeçalhos que o túnel da Cloudflare acrescenta (`CF-Connecting-IP`, `X-Forwarded-For`...) não vão para os
  sites: eles veem só o IP do celular.

## Traduzir a tela

Em *✨ Inteligência artificial → 🌐 Traduzir a tela*: escolha o idioma do texto que está na tela e:

- **Esperar eu tirar um print**: tire um print com os botões do celular (ligar + volume para baixo) no app que quer traduzir. O LNUX percebe o print novo, lê o texto com o OCR (tesseract) e traduz; a tradução aparece no Termux e **numa notificação**, então dá para ficar no app (ou usar o Termux:Float por cima dele).
- **Modo contínuo**: traduz cada print novo até você parar (Ctrl+C), bom para jogos e mangás.
- **Capturar direto (ADB ou root)**: conta alguns segundos para você trocar de app e captura a tela sozinho.
- **Último print**: traduz o print mais recente.

O idioma do OCR é baixado na primeira vez (inglês, espanhol, japonês, coreano, chinês, russo, árabe...). Prints em modo escuro são invertidos antes da leitura. A tradução usa a internet.

## Remover o fundo (deixar só a pessoa)

Em *✨ Inteligência artificial → ✂️ Remover o fundo*: escolha uma foto ou um vídeo e o fundo que vai no lugar: **transparente**, **tela verde** (para recortar no editor de vídeo), branco, preto, **desfocado** (modo retrato) ou **outra imagem** do celular.

- Roda **no próprio celular**, com um modelo de recorte de pessoas e o `onnxruntime` do Termux (`python-onnxruntime`, instalado na primeira vez com `numpy` e `Pillow`). Nada vai para a internet; só o modelo é baixado, uma vez: **Preciso** (U²-Net para pessoas, 176 MB) ou **Rápido** (MODNet, 25 MB, melhor para vídeo).
- **Foto** vira PNG transparente (ou JPG com o fundo novo) em `Download/LNUX/Sem fundo`, com uma prévia no terminal.
- **Vídeo** é recortado quadro a quadro (até 1280 px) e mantém o som. Transparente sai em WebM (a galeria mostra o fundo preto, editores mantêm a transparência); com fundo, sai em MP4. Leva alguns segundos por quadro no celular, e a tela mostra quanto falta.

## Meus dados na internet

Em *👤 Meus dados na internet* (menu principal): preencha o que quiser (nome completo, CPF, cidade, estado, e-mail,
celular, @ das redes e CNPJ do MEI) e veja o que está público sobre você. Cada busca também pede na hora o dado que
faltar. Feito para **pesquisar você mesmo(a)**.

- **Links oficiais e buscas prontas**: abrem no navegador do celular. Quando o site pede para digitar (Receita, TJ,
  TRF, Lattes, Querido Diário, Have I Been Pwned), o CPF, o CNPJ, o nome ou o e-mail já vai **copiado**: é só colar.
  Captcha e login gov.br continuam com você.
- **Consultas feitas aqui mesmo**, só com APIs públicas e mandando só o necessário: diários das prefeituras pelo
  [Querido Diário](https://queridodiario.ok.org.br/) (o nome), dados abertos do CNPJ pela
  [BrasilAPI](https://brasilapi.com.br/) (o CNPJ), o resumo do CPF no Portal da Transparência (o CPF, com a
  [chave grátis da API](https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email), que fica na
  configuração) e senha vazada pelo [Pwned Passwords](https://haveibeenpwned.com/Passwords) (só os 5 primeiros
  caracteres do hash SHA-1; a senha não sai do celular). A conferência do CPF (dígitos e região fiscal) é offline e
  aceita também o **CNPJ alfanumérico** (de julho de 2026 em diante).
- **🚀 Verificar tudo e gerar o relatório**: faz as consultas e salva uma página HTML em
  `Download/LNUX/Meus dados` com os resultados e todas as buscas prontas, agrupadas por fonte. O CPF aparece
  mascarado (`***.456.789-**`), mas os links levam os seus dados: apague quando não precisar mais.
- **Os dados ficam no celular**: só na memória, ou em `~/.lnux/meus_dados.json` (permissão `600`) se você
  escolher guardar. *🗑️ Apagar meus dados deste celular* apaga o arquivo, os relatórios e, se quiser, a chave da API.

## Compilar o whisper.cpp e o llama.cpp no celular

A voz para texto, a legenda da rádio e a IA local compilam o código no próprio celular (`clang` + `cmake`). Erro
`redefinition of 'vcvtnq_s32_f32'` no Termux de **32 bits** (`uname -m` mostra `armv7l` ou `armv8l`)? É uma
incompatibilidade do ggml, a base dos dois projetos, com o `arm_neon.h` do clang quando ele compila para um
processador ARMv8: o ggml declara a sua própria versão de funções que o clang também declara. O LNUX
corrige isso sozinho antes de compilar e, se ainda assim falhar, compila de novo com `-DGGML_NATIVE=OFF` (sem as
otimizações específicas do processador). Basta atualizar o LNUX e mandar instalar de novo.

À mão, sem atualizar: `cd ~/whisper.cpp && cmake -B build -DGGML_NATIVE=OFF && cmake --build build -j 4 --target
whisper-cli`.

## Depuração sem fio (ADB pelo Wi-Fi)

1. Ative as **Opções do desenvolvedor** (Configurações → Sobre o telefone → toque 7 vezes em *Número da versão*).
2. Menu **🔌 Depuração sem fio → Parear este celular**: ligue a *Depuração por Wi-Fi*, toque em *Parear dispositivo
   com código de pareamento* e digite o código no Termux. O Android fecha o código se você sair da tela, então use
   **tela dividida** (ou o Termux em janela flutuante). O pareamento é feito uma vez só.
3. Nas próximas vezes, só **Conectar** (a porta muda sempre que a depuração é religada; o programa tenta achá-la
   sozinho).
4. Use **Impedir que o Android mate o Termux** para acabar com o *Process completed (signal 9)* em serviços 24h.
5. **📖 Comandos do ADB** traz os comandos da [documentação oficial do adb](https://developer.android.com/tools/adb)
   em categorias (aparelhos e conexão, arquivos, instalar apps, `pm`, `am`, `dpm`, print e gravação, portas e
   diagnóstico, dicas). A descrição da opção selecionada aparece embaixo da lista; ao escolher, dá para rodar na
   hora, e ele pergunta o que faltar (o app sai de uma lista). Os que mudam o celular pedem confirmação já marcada
   em **Não**, e os que precisam de root, apagam o aparelho ou têm opção melhor no menu ficam só para consulta.

Erro `CANNOT LINK EXECUTABLE "adb": cannot locate symbol ...`? O `adb` foi atualizado e as bibliotecas dele não
(atualização pela metade). O menu oferece consertar sozinho; à mão: `pkg update && pkg upgrade` (se continuar,
`pkg install --reinstall android-tools abseil-cpp`).

Desligue a Depuração por Wi-Fi quando não estiver usando: enquanto ela está ligada, um aparelho pareado tem
acesso de "shell" ao celular.

## Resolução da tela

Em **📲 Celular e sistema → 🖥️ Resolução da tela** (precisa de root ou da depuração sem fio acima):

- **Tela inteira**: 90%, 75%, 67%, 50% ou a largura que você digitar. A densidade (dpi) muda na mesma proporção,
  então ícones e letras ficam do mesmo tamanho (e o *Tamanho da exibição* das configurações continua valendo).
  Menos pixels = jogos mais leves e menos bateria, com um pouco menos de nitidez.
- **Um app só** (Android 12+): escolha o app e a porcentagem; ele abre já na resolução nova. Usa as mudanças de
  compatibilidade do Android (`am compat enable DOWNSCALED`); se o celular não deixar, tenta o modo de jogo
  (Android 13+, só funciona em jogos).

**Toda mudança volta sozinha em 1 minuto se você não confirmar.** Depois de mudar aparece *Ficou bom? Manter
assim?* com a contagem regressiva, já marcado em **Não**: se a tela ficar estranha, não precisa tocar em nada
(ou só dê Enter). Quem desfaz é um vigia em outro processo, então volta mesmo que o LNUX feche no meio.
Para voltar depois: **Voltar a tela à resolução de fábrica** / **Voltar um app à resolução normal**, ou
`lnux resolucao` no terminal.

## Controle da TV

Em **📲 Celular e sistema → 📺 Controle da TV**, adicione a TV de um destes jeitos:

- **Infravermelho do celular** (o "sensor" de controle remoto que fica no topo de muitos Xiaomi, Redmi e POCO;
  precisa do app Termux:API): funciona com qualquer TV, até as antigas. Escolha a marca (Samsung, LG, TCL,
  Philips, AOC, Sony, Panasonic, Toshiba/Semp, Hisense, Sharp...) e teste o liga/desliga. Se não souber a marca ou
  não funcionar, a **busca automática** manda o sinal de desligar de mais de 300 controles, um por segundo (a
  biblioteca universal de TVs do Flipper Zero, baixada na primeira vez): quando a TV desligar, toque na tela e ela
  confirma qual foi. Também dá para importar o controle da sua TV num arquivo `.ir` (Flipper-IRDB) ou colar um
  código (Pronto, tempos em µs ou protocolo).
- **Wi-Fi** (Smart TV na mesma rede): procura as TVs sozinho. **Samsung** e **LG** pedem permissão na tela da TV
  na primeira vez; **Android TV / Google TV** usa a depuração por rede (ADB) das opções do desenvolvedor da TV;
  **Roku TV** funciona direto. Para **ligar** pelo Wi-Fi a TV precisa estar com "Ligar pela rede / pelo celular"
  ativo (Wake-on-LAN); o MAC dela é guardado sozinho.

Depois: **⏻ Ligar / desligar** e o **🎮 Controle remoto** na tela (toque nos botões, arraste o dedo para cima ou
para baixo para o volume, ou use o teclado). Pelo Wi-Fi ele confere se a TV está ligada antes, então "desligar"
não liga a TV sem querer; pelo infravermelho isso só é garantido nas marcas com códigos separados de ligar e
desligar (Samsung, LG, Sony, Panasonic, Toshiba). Também dá para usar:

- na **tela inicial** com o Termux:Widget (*Atalho na tela inicial*): "TV liga-desliga" funciona sem abrir o Termux;
- numa **automação** (ex.: todo dia às 23h → desligar a TV; ao sair do Wi-Fi de casa → desligar);
- no **bot** do Telegram/Discord: `/tv`, `/tv desligar`, `/tv mudo`, `/tv vol+`;
- no terminal: `lnux tv desligar`, `lnux tv controle`.

**Desligar TVs por perto (TV-B-Gone):** em *📺 Controle da TV → 📴 Desligar TVs por perto*, o celular dispara o sinal
de desligar de centenas de modelos, um atrás do outro — serve para desligar a TV de uma loja, academia ou sala de
espera. No terminal: `lnux tvbgone`.

## Controle de outros aparelhos (som, projetor, ar-condicionado)

Em **📲 Celular e sistema → 📡 Controle de outros aparelhos** dá para controlar, pelo **infravermelho**, no estilo dos
"controles universais" do Flipper Zero:

- **Soundbar / aparelho de som**: liga/desliga, volume, mudo, play/pausa, avançar/voltar.
- **Projetor / TV box / conversor**: liga/desliga, volume, mudo e, quando o controle tem, setas, OK, menu, voltar e
  fonte.
- **Ar-condicionado**: por **presets** (como no Flipper): desligar, mais/menos frio, mais/menos quente e
  desumidificar — não é grau a grau, porque cada marca manda a temperatura de um jeito próprio.

Adiciona igual à TV: escolhe a marca (da biblioteca universal do Flipper Zero, baixada na primeira vez), ou usa a
**busca automática**, ou **importa um `.ir`** / cola um código. A tela do 🎮 controle remoto mostra só os botões que
aquele aparelho tem; os outros ficam apagados. Também funciona na tela inicial (Termux:Widget) e no terminal
(`lnux aparelho "Som da sala" Vol_up`, `lnux aparelho "Ar da sala" controle`).

> **Clonar o controle apontando ele para o celular não dá**: o Android tem emissor de infravermelho, mas não tem
> receptor (nenhum celular comum tem). Para "copiar" um controle, importe o arquivo `.ir` dele (do Flipper-IRDB) ou
> cole o código. Coisas do Flipper que precisam do rádio/chips dele (433 MHz de portões e carros, RFID/NFC de
> aproximação, iButton, BadUSB) **não** funcionam num celular comum.

## Player de música e rádio

Tudo o que você manda tocar (busca, mix, biblioteca, playlist, rádio, podcast) abre a tela **🎵 Tocando agora**:

- Como o cartão de mídia do Android: a **capa** (a embutida no arquivo, a miniatura do YouTube ou o ícone da rádio, desenhada em cores no terminal com o Pillow), o **nome da música**, o artista e o álbum, os botões ⏮ ↺10 ⏸ 10↻ ⏭ e a barra de tempo; embaixo, o volume e a fila com a que está tocando marcada.
- **Dá para tocar na tela**: nos botões e na barra de tempo (o toque leva a música até aquele ponto).
- Teclas: `Espaço` pausa · `←` `→` voltam/avançam 10 s · `↑` `↓` volume · `n`/`p` próxima/anterior · `s` embaralha · `r` repete a fila ou a música · `e` abre o equalizador · `a` liga o **anúncio por voz** ("Tocando agora: Aquarela, de Toquinho") · `Esc` sai e **continua tocando** · `q` para.
- Fora da tela, a música segue com uma **notificação de mídia** do Android (precisa do pacote `termux-api` e do app Termux:API): a capa, a música em cima e o artista embaixo, uma barra de progresso em texto (`━━━●────── 3:57`) e os botões ⏮ ⏸ ▶ ⏭ e +10 s (o Termux:API desenha esse 5º botão com um ícone de "+"). Tocando, ela fica presa; **pausada, arraste para o lado para parar** a música. Volte à tela em *Música → 🎵 Tocando agora*; o menu principal mostra o que está tocando.
- O cartão de mídia completo do Android (barra de progresso de arrastar, *Saída de mídia*, nome do fone e o player nas configurações rápidas) só aparece para apps com uma *sessão de mídia*, e o `termux-notification` não cria uma. Por isso a notificação chega perto, mas não fica idêntica.

Na **rádio** a lista escolhida vira a fila, então `n`/`p` (e ⏭/⏮ da notificação) trocam de estação. A tela mostra a música que a rádio informa (quando informa), `f` guarda nas favoritas e:

- `l` liga a **legenda automática**: o áudio é cortado em trechos de 8 s e transcrito no próprio celular pelo whisper.cpp, no idioma da rádio (detectado sozinho), com alguns segundos de atraso. Instale antes em *✨ Inteligência artificial → 🎤 Voz para texto*; o modelo `tiny` ou `base` dá conta, os maiores ficam para trás.
- `t` traduz a legenda para o português (precisa de internet).

### Descobrir a música pelo som

Em *Música → 🔎 Descobrir a música de um arquivo*: escolha um áudio ou vídeo (mp3, mp4, opus, m4a...) e ele descobre o nome da música pelo som, mesmo que o arquivo se chame `VID_2026...mp4`. Mostra a música, o artista, o álbum e a certeza, outras opções parecidas e no fim pergunta **se você quer tocar** (o player mostra o nome descoberto).

- Usa o **Chromaprint**, que tira a impressão digital dos 2 primeiros minutos de som, e o **AcoustID**, um serviço aberto e gratuito para uso não comercial, com a base do MusicBrainz.
- Na primeira vez, o LNUX compila a biblioteca do Chromaprint (uns 2 minutos; o Termux não tem pacote dela) e pede uma **chave grátis do AcoustID**: entre em <https://acoustid.org/new-application>, registre um aplicativo com qualquer nome e cole a *API key*.
- Funciona com a música inteira (ou quase), como a de um disco ou de um clipe. Trechos curtos, gravações com barulho, versões ao vivo e remixes costumam não ser reconhecidos.

### Equalizador

Em *Música → 🎚️ Equalizador* (ou `e` no player): 10 bandas, de 31 Hz a 16 kHz, e o pré-amplificador, de -20 a +20 dB, como o do VLC.

- **Com o dedo**: arraste para cima ou para baixo numa banda (ou no pré-amplificador) para subir ou descer, 1 dB por linha arrastada. Tocar escolhe a banda, e tocar numa altura do controle já põe aquele valor.
- Pelo teclado: `←` `→` escolhem a banda (o pré-amplificador fica antes da de 31 Hz) e `↑` `↓` sobem ou descem 1 dB.
- Com muito reforço (mais de +9 dB somando o pré-amplificador), a tela avisa para baixar o pré-amplificador se o som distorcer.
- `p`/`P` trocam o preset (Graves, Agudos, Graves e agudos, Rock, Pop, Eletrônica, Reggae, Clássica, Voz e podcast, Fone de ouvido, Volume baixo). Os presets que reforçam baixam um pouco o pré-amplificador para não distorcer.
- `Espaço` liga e desliga, `0` zera a banda escolhida, `z` zera tudo e `Enter` sai. Fica salvo.
- **Ligado, tudo o que tocar passa por ele** (músicas, playlists, rádio, podcast), e a mudança vale na hora na música que está tocando.
- **Ao baixar** (buscar e baixar, por link ou do Spotify), depois do formato ele pergunta: *sem alteração* ou *com o equalizador*. Com o equalizador, o ffmpeg converte o arquivo de novo com o filtro, mantendo as etiquetas e a capa, e o nome ganha `(EQ Rock)`, por exemplo. Com o formato *Original* o arquivo sai em Opus, porque precisa ser convertido.

## Fonte do terminal

Em **⚙️ Sistema e manutenção → 🎨 Aparência do terminal → 🔤 Fonte do terminal**: baixe uma fonte no celular (ex.: JetBrains Mono,
Fira Code ou uma *Mono* das [Nerd Fonts](https://www.nerdfonts.com)) e escolha na lista. Ele acha `.ttf` e `.otf`
no Download, Documents e Fonts, **dentro de arquivos .zip** (é assim que o Google Fonts e as Nerd Fonts baixam) e
as monoespaçadas do próprio Android. Mostra o nome da fonte e avisa se ela não for monoespaçada (no terminal as
colunas ficariam tortas). A fonte vai para `~/.termux/font.ttf` e o Termux recarrega na hora; se você não
confirmar em 1 minuto, volta à fonte de antes. **Fonte do terminal: voltar à original** devolve a fonte que você
usava antes do LNUX (ou a padrão do Termux).

## Desktop da distro no Termux:X11

Menu **🐧 Linux de verdade → 🖥️ Interface gráfica da distro (Termux:X11)**:

1. **Instalar o app Termux:X11** — abre a página de download (baixe o `.apk` *universal* da versão nightly) e
   instala no Termux o servidor X (`termux-x11-nightly`, do `x11-repo`) e o som (`pulseaudio`).
2. **Instalar um ambiente gráfico na distro** — XFCE (recomendado), LXQt (mais leve) ou MATE, com os pacotes certos
   para Debian, Ubuntu, Arch, Alpine, Fedora ou openSUSE, e opcionalmente um navegador (no Ubuntu vai o Epiphany:
   o Firefox de lá é snap, que não roda no proot). Baixa de 300 MB a 1 GB.
3. **Abrir o desktop da distro** — liga o servidor X e o som, abre o app Termux:X11 e inicia o desktop (numa sessão
   tmux: continua rodando se você sair do menu). **Parar o desktop** encerra tudo.

Extras: escolher o **usuário** que abre o desktop (navegadores não gostam de root; crie um com *Criar usuário
não-root com sudo*), **aceleração pela GPU** (virgl, experimental) e **atalho na tela inicial** pelo app
Termux:Widget. Pela linha de comando: `python lnux.py desktop debian` (ou `--parar`).

## Gerenciador de arquivos

Menu **📂 Gerenciador de arquivos** (ou `python lnux.py arquivos [pasta]`). Enter abre a pasta ou mostra
as ações do arquivo; Esc sobe uma pasta; **⚙ Ações nesta pasta** tem colar, marcar vários itens, nova pasta,
**Ir para...** (Download, DCIM, Android/data, cartão SD, raiz do sistema...), busca, ocultos e ordenação.

O que ele consegue ver depende do **nível de acesso** (⚙ → Nível de acesso):

| Acesso | O que abre | Precisa de |
|--------|------------|------------|
| Termux | armazenamento interno, cartão SD, a pasta do Termux | `termux-setup-storage` |
| ADB (depuração sem fio) | tudo acima **+ `Android/data` e `Android/obb`** (saves de jogos, arquivos de apps), `/data/local/tmp` e partes do sistema | parear uma vez em 📲 Celular e sistema → 🔌 Depuração sem fio |
| Root | **tudo**, inclusive `/data/data` (dados privados de cada app) | celular com root |

Sem root, nenhum app (nem o ZArchiver ou o Termux) consegue ler os dados privados de outros apps em `/data/data`:
isso o Android só libera para o root. O que dá para ganhar sem root é o acesso do ADB, que já abre as pastas
`Android/data` e `Android/obb`. Copiar entre níveis funciona: dá para tirar um arquivo de `Android/data` e colar
no Download, ou o contrário.

## Serviços 24h (tmux)

Tudo que fica rodando (servidor web, túnel, bots, monitoramento, llama-server, code-server,
compartilhamentos, player, lembretes, registro da bateria, automação, downloads, agendador,
bancos de dados e servidores) vira uma sessão tmux chamada `lnux-<nome>`, com log em
`~/.lnux/logs/`. O menu de cada seção tem *iniciar / parar / status e log / abrir a
sessão* (para sair da sessão sem parar o serviço: `Ctrl+b` e depois `d`).

O `termux-wake-lock` é ativado ao iniciar um serviço e liberado quando o último para. Para
ficar no ar 24h, desative também a **otimização de bateria** do Termux nas configurações do
Android.

## Segurança

- A configuração fica em `~/.lnux/config.json` com permissão `600`.
- A API exige token (`Authorization: Bearer <token>`); só `/` e `/api/ping` são públicas.
  Use o túnel da Cloudflare sabendo que a API fica exposta na internet.
- Os bots ignoram quem não estiver na lista de IDs permitidos e respondem com o ID da
  pessoa, para facilitar o cadastro. O comando `/sh` vem **desligado**.
- O llama-server sobe em `127.0.0.1` por padrão (não tem senha).
- As ferramentas de rede exigem aceitar um aviso: use só em redes e aparelhos seus ou com
  autorização do dono.

## Arquivos

```
~/.lnux/                   # era ~/.termux_toons (o nome antigo vira um atalho para esta pasta)
├── config.json            # tokens, portas, monitores e o sistema escolhido ("sistema": "debian"...)
├── distros/               # perfis de sistema seus (opcional; um com o mesmo id substitui o original)
├── lnux-apps/             # 🧩 os Apps Web (clone do LNUX-APPs)
├── tnux/                  # 🐧 o TNUX (clone do TNUX-DistroSystem, compilado em build/)
├── logs/                  # um log por serviço
├── tarefas.json           # gerenciador de tarefas
├── alfabetos.json         # 🔣 alfabetos próprios das Mensagens secretas
├── 2fa.lnuxcripto         # 🔑 contas dos códigos 2FA (cifradas com AES-256 e a sua senha)
├── tldr/                  # 📚 páginas do tldr baixadas (para usar sem internet)
├── api_historico.json     # 🔌 últimas requisições do Testar uma API
├── meus_dados.json        # 👤 Meus dados na internet (só se você escolher guardar)
├── resolucao_pendente.json  # mudança de resolução esperando confirmação (some ao confirmar ou desfazer)
├── monitores_estado.json  # último resultado de cada monitor
├── cache/legendas/        # legendas embutidas já extraídas
├── cache/letras/          # 🎤 letras de música já baixadas
├── vlc-web/               # VLC Web baixado do GitHub para o navegador pelo celular
├── motor-completo/        # modo completo do navegador (Rammerhead pelo npm, sessões e o segredo)
├── playlists/             # playlists .m3u
├── basic/                 # programas BASIC salvos
└── recordes.json
~/.lnux-apps/               # 🧩 a ponte dos Apps Web: ponte.json (chave, pastas liberadas; permissão 600) e tmp/
~/.tnux/                    # 🐧 o TNUX: ponte.json (porta e chave da área de trabalho ligada; permissão 600) e logs
~/llama.cpp/               # código e build do llama.cpp
~/llama-models/            # modelos .gguf
```

Defina `LNUX_DEBUG=1` para ver o traceback completo de erros inesperados e `LNUX_SISTEMA=fedora` para usar
um perfil sem salvar a escolha (bom para testes). As variáveis antigas `TOONS_*` continuam valendo.

## Para quem mexe no código

Antes de cada commit, rode o verificador dos menus. Ele só lê o código (não executa nada) e acusa opções
duplicadas em menus diferentes, menus que nenhuma opção abre e entradas da 🔍 Busca que apontam para o lugar
errado:

```bash
python3 tests/verificar_menus.py            # duplicatas, busca, menus soltos e submenus vazios em cada sistema
python3 tests/verificar_menus.py --arvore   # também mostra a árvore inteira, com o que cada opção exige
python3 tests/verificar_perfis.py           # confere os perfis de distros/ contra o que o código usa
python3 tests/testar_menus_por_sistema.py   # abre todos os menus em cada sistema, sem executar nenhuma ação
python3 tests/testar_mensagens_secretas.py  # codificar e decodificar de cada técnica de 🕵️ Mensagens secretas
python3 tests/testar_ferramentas_novas.py   # as ferramentas de terminal (gráficos, 2FA, servidor de pasta, parsers...)
python3 tests/testar_apps_web.py            # 🧩 Apps Web: catálogo, link com a chave, o servidor do LNUX-APPs e o túnel
python3 tests/testar_tnux.py                # 🐧 TNUX: baixar e compilar, ligar, a chave, o link pela internet e a rede
python3 tests/verificar_compatibilidade.py  # o código continua abrindo no Python 3.9 (Debian 12 usa o 3.11, Ubuntu 22.04 o 3.10)
```

Uma opção que só funciona em alguns sistemas se marca com `so_em("recurso", função)` (ex.:
`so_em("termux_api", menu_sms)`, `so_em("!termux", backup_pessoal)`, `so_em("pacote:jellyfin-server", ...)`), e
`por_sistema("rótulo no Termux", "rótulo no Linux")` troca o nome mostrado. Os recursos estão na lista `RECURSOS`
do `lnux.py`.

Para juntar opções relacionadas numa subcategoria sem criar uma função nova, use
`grupo("Título", [(rótulo, função), ...])` como o alvo de um item de menu. O histórico da reorganização do menu
está em [docs/relatorio-modulo-1.md](docs/relatorio-modulo-1.md), e o da troca para LNUX com várias distros em
[docs/relatorio-modulo-2.md](docs/relatorio-modulo-2.md); o das Mensagens secretas em [docs/relatorio-modulo-5.md](docs/relatorio-modulo-5.md) e o das ferramentas de terminal em [docs/relatorio-modulo-6.md](docs/relatorio-modulo-6.md).
