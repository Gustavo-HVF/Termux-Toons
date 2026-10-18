# Termux-Toons 📱🧰

Um canivete suíço em **um único arquivo Python** para transformar o celular Android
(com [Termux](https://termux.dev)) em servidor, estação de desenvolvimento, central de
automação, player de música e muito mais — tudo por um menu no terminal.

```
╔╦╗╔═╗╦═╗╔╦╗╦ ╦═╗ ╦  ╔╦╗╔═╗╔═╗╔╗╔╔═╗
 ║ ║╣ ╠╦╝║║║║ ║╔╩╦╝   ║ ║ ║║ ║║║║╚═╗
 ╩ ╚═╝╩╚═╩ ╩╚═╝╩ ╚═   ╩ ╚═╝╚═╝╝╚╝╚═╝
```

Para abrir, o programa só precisa da biblioteca padrão do Python. Cada função instala o
que precisa (`pkg install ...` ou `pip install ...`) **perguntando antes**.

## Instalação

> Instale o **Termux** e o **Termux:API** pela mesma loja (F-Droid ou GitHub). A versão
> da Play Store está desatualizada e não conversa com o Termux:API do F-Droid.

```bash
pkg update && pkg upgrade
pkg install git python
git clone https://github.com/Gustavo-HVF/Termux-Toons
cd Termux-Toons
bash instalar.sh        # instala tmux/termux-api, pede acesso ao armazenamento e cria o atalho "toons"
toons                   # ou: python termux_toons.py
```

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

Digitar o número da opção também funciona como atalho. Se preferir o modo antigo, de
digitar números, rode com `TOONS_NUMEROS=1 toons` (ele também é usado automaticamente
quando não há um terminal interativo, por exemplo em scripts).

## O que tem no menu

| # | Seção | O que faz |
|---|-------|-----------|
| 1 | 🌐 **Servidor web / API pessoal** | API com Flask, FastAPI ou só biblioteca padrão, acessível na rede Wi-Fi. Painel web em `/`, rotas protegidas por token (`/api/status`, `/api/bateria`, `/api/notificar`, `/api/falar`, `/api/vibrar`, `/api/lanterna`, `/api/local`, `/api/ia`). Expõe na internet com **Cloudflare Tunnel** (`cloudflared`) e mostra a URL `trycloudflare.com`. |
| 2 | 🤖 **Bots Telegram / Discord 24h** | Bot do Telegram feito só com a biblioteca padrão (long polling) e bot do Discord com `discord.py`. Rodam em sessão **tmux** com **termux-wake-lock** e reinício automático. Só respondem a IDs permitidos. Comandos: `/status /bateria /ip /local /foto /falar /notificar /vibrar /lanterna /sms /ia /servicos /sh`. |
| 3 | 📱 **Automação com Termux:API** | Bateria, sensores, SMS (enviar/ler), notificações, TTS, câmera, localização, vibração, lanterna, área de transferência, Wi-Fi, volume e alerta de bateria baixa. |
| 4 | 🧠 **LLMs locais (llama.cpp)** | Clona e **compila o llama.cpp no próprio celular**, baixa modelos GGUF de 1B a 3B (Gemma 3 1B, Llama 3.2 1B/3B, Qwen2.5 1.5B/3B, Qwen3 1.7B, Gemma 2 2B ou URL própria, com download retomável), conversa no terminal (`llama-cli`) ou sobe o `llama-server` (interface web + API compatível com OpenAI). O bot e a API usam o modelo com `/ia`. |
| 5 | 📊 **Interfaces TUI** | Dashboard ao vivo com **rich** (CPU, RAM, disco, bateria, serviços), gerenciador de tarefas com **curses** e atalho para o player de música. |
| 6 | 💻 **Ambiente de desenvolvimento** | Instala git, Neovim, C/C++ (clang/clangd), Rust (rust-analyzer), Go (gopls), pyright, lua-language-server; gera um `init.lua` com **LSP nativo** (sem plugins), configura git e chave SSH, testa os compiladores e roda o **code-server** (VS Code no navegador). |
| 7 | 🔎 **Scraping e monitoramento** | Monitores de **preço** (alvo em R$), **notícias** (RSS/Atom), **status de site**, **texto que aparece/some** e **mudança de página**. Avisa por notificação, TTS e Telegram. Roda 24h no tmux. |
| 8 | 🛡️ **Rede e segurança** *(só em equipamentos seus!)* | Info de rede, descoberta de dispositivos e varredura de portas com **nmap**, DNS/ping/traceroute, teste de velocidade, redes Wi-Fi próximas, captura com tcpdump (root) ou leitura de `.pcap`, **servidor SSH** (porta 8022) e geração de config **WireGuard** + QR code para o app. |
| 9 | 👾 **Retro** | Snake em curses, adivinhe o número, **interpretador BASIC** (PRINT, INPUT, IF/THEN, GOTO, GOSUB, FOR/NEXT, matrizes, SAVE/LOAD...) e gerador de **template para criar seu próprio jogo**. |
| 10 | 🐧 **Linux com proot-distro** | Instala Debian, Ubuntu, Arch, Alpine, Fedora..., entra na distro, roda comandos, atualiza, cria usuário com sudo, faz backup, reseta e remove. |
| 11 | 🗄️ **Arquivos e backup** | Compartilhamento HTTP rápido, **rclone** (Drive, Dropbox, OneDrive... copiar/sincronizar e servir via WebDAV com senha), **Syncthing**, **Samba** (porta 4450, experimental) e backup/restauração do Termux em `.tar.gz`. |
| 12 | 🎵 **Música (yt-dlp + mpv)** | Busca e toca por streaming, baixa no melhor áudio, baixa por link (YouTube, SoundCloud, playlists) e por **link do Spotify** (procura a música no YouTube), mix/rádio por busca, biblioteca local, playlists `.m3u` e player em segundo plano. |
| 13 | 🎬 **Vídeos (TikTok, YouTube)** | Baixa vídeos por link (TikTok, YouTube, Shorts, playlists e outros sites que o yt-dlp aceita), busca no YouTube e baixa, abre os vídeos baixados no player do Android e **assiste um link sem baixar** no VLC/MX Player (link direto do TorBox ou página do YouTube/TikTok). |
| 14 | 🔄 **Atualização** | `pkg upgrade`, troca de espelho (`termux-change-repo`), repositórios extras (x11/root/tur), pacotes pip, recompilar llama.cpp, atualizar distros, `git pull` em vários repositórios e no próprio Termux-Toons, limpeza de cache. |
| 15 | 🧹 **Otimização e limpeza** | **Otimização rápida** (cache do apt, `~/.cache` com pip/yt-dlp/go, npm, temporários antigos, `__pycache__`, logs velhos e miniaturas da galeria) mostrando quanto liberou; escolher item a item; **limpar o cache de todos os apps** (`pm trim-caches` com root; sem root abre a tela de armazenamento do Android); ver o que ocupa espaço; achar **arquivos grandes**, **duplicados** e pastas vazias; processos do Termux que mais usam RAM; parar todos os serviços; compilação dos apps e TRIM (root); atalhos para as telas de armazenamento e bateria. |
| 16 | 📺 **Compartilhar filme por link** | Servidor de vídeo próprio: escolha um filme do celular **ou cole um link do TorBox/Real-Debrid (sem baixar o filme)**, receba um **link secreto** (com prazo opcional) e quem abrir assiste num **player próprio** no navegador: barra de progresso com prévia do tempo, **troca de trilha de áudio** (dublado/original), legendas (arquivo ao lado, extra ou **embutidas**) com tamanho e sincronia ajustáveis, velocidade, tela cheia, janela flutuante, **toque duplo para pular 10 s**, atalhos de teclado, **continuar de onde parou** e botão **Abrir no VLC**. MKV, áudio AC3/DTS e várias trilhas são **convertidos na hora** pelo ffmpeg (a imagem é só copiada; HEVC é recodificado só se o navegador não tocar). Também **converte para MP4** de vez, se preferir. Copia o link, manda pelo menu de compartilhar do Android (WhatsApp, Telegram...) ou mostra um QR code. **Túnel Cloudflare** para quem está fora do seu Wi-Fi. Apagar um link vale na hora. |

Os downloads de música usam exatamente:

```bash
yt-dlp -f bestaudio --extract-audio --audio-format opus --embed-thumbnail --add-metadata \
       -o "~/storage/downloads/%(title)s.%(ext)s" "<link>"
```

(a pasta pode ser trocada no menu de música). Os vídeos usam:

```bash
yt-dlp -f "bv*+ba/best" --trim-filenames 150 -o "~/storage/downloads/%(title)s.%(ext)s" "<link>"
```

(`--trim-filenames` encurta nomes enormes, como os de legendas do TikTok; a pasta pode ser
trocada no menu de vídeos).

## Linha de comando

Os serviços em segundo plano chamam o próprio script; você também pode usar direto:

```bash
python termux_toons.py                      # menu
python termux_toons.py serve --framework stdlib --porta 8000
python termux_toons.py bot telegram
python termux_toons.py monitor [--uma-vez]
python termux_toons.py dashboard | tarefas | snake | doctor
python termux_toons.py basic [programa.bas]
python termux_toons.py baixar "https://youtu.be/..." "artista - música" "https://open.spotify.com/track/..."
python termux_toons.py video "https://www.tiktok.com/@user/video/..." "https://youtu.be/..."
python termux_toons.py compartilhar ~/storage/downloads/filme.mp4 --horas 24   # cria o link e liga o servidor
python termux_toons.py compartilhar "https://link-direto-do-torbox/Filme.mkv" --legenda filme.pt.srt
python termux_toons.py assistir "https://link-direto-do-torbox/Filme.mkv"      # abre no VLC do celular
python termux_toons.py midia                # servidor de vídeo em primeiro plano
python termux_toons.py tocar                # biblioteca no aleatório
python termux_toons.py tocar lofi hip hop   # mix por busca
python termux_toons.py atualizar
python termux_toons.py limpar                # otimização rápida, sem perguntas
```

## Compartilhar um filme por link

1. Menu **📺 Compartilhar filme por link → Compartilhar um filme do celular**, escolha o arquivo, o título e o prazo.
2. O programa liga o servidor de vídeo (porta 8095) e mostra o link: `http://IP-do-celular:8095/v/<código secreto>`.
   Quem estiver **no mesmo Wi-Fi** já consegue assistir.
3. Para quem está **fora da sua rede**, ligue **Túnel para a internet** no mesmo menu (usa o `cloudflared`;
   o endereço público aparece na tela e vira o link que você envia).
4. Copie o link ou use **Enviar pelo WhatsApp, Telegram...**. Em **Meus links** dá para assistir no próprio
   celular, apagar um link (quem estiver com ele perde o acesso na hora) ou **Apagar TODOS os links**.

### Transmitir de um link (TorBox, Real-Debrid...) sem baixar

Se o filme está no **TorBox** (ou Real-Debrid, AllDebrid, Premiumize, um servidor seu...), não precisa baixar:

1. No TorBox, abra o item, toque em **Download** e copie o link (o mesmo que você abre no VLC).
2. Menu **📺 → 🌐 Transmitir de um link**, cole o link. O programa confere o link (sem baixar), mostra a duração,
   as trilhas de áudio e as legendas, e cria o link secreto como no passo a passo acima.
3. Enquanto a pessoa assiste, o celular busca só o pedaço do filme que está passando e repassa para ela. O
   endereço do TorBox nunca aparece para quem recebe o link.
4. O link do TorBox expirou? Gere outro e use **Meus links → Trocar o endereço do vídeo**: o link que você já
   enviou continua o mesmo.

Para só assistir no seu celular, use **Assistir um link neste celular** (no menu 📺 ou no 🎬 Vídeos): abre direto
no VLC ou em outro app de vídeo. Também aceita páginas do YouTube, TikTok etc. (o yt-dlp acha o vídeo).

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
- O filme **sai do seu celular**: quem assiste usa o **upload** da sua internet (num link do TorBox, também o
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

## Serviços 24h (tmux)

Tudo que fica rodando (servidor web, túnel, bots, monitoramento, llama-server, code-server,
compartilhamentos, player) vira uma sessão tmux chamada `toons-<nome>`, com log em
`~/.termux_toons/logs/`. O menu de cada seção tem *iniciar / parar / status e log / abrir a
sessão* (para sair da sessão sem parar o serviço: `Ctrl+b` e depois `d`).

O `termux-wake-lock` é ativado ao iniciar um serviço e liberado quando o último para. Para
ficar no ar 24h, desative também a **otimização de bateria** do Termux nas configurações do
Android.

## Segurança

- A configuração fica em `~/.termux_toons/config.json` com permissão `600`.
- A API exige token (`Authorization: Bearer <token>`); só `/` e `/api/ping` são públicas.
  Use o túnel da Cloudflare sabendo que a API fica exposta na internet.
- Os bots ignoram quem não estiver na lista de IDs permitidos e respondem com o ID da
  pessoa, para facilitar o cadastro. O comando `/sh` vem **desligado**.
- O llama-server sobe em `127.0.0.1` por padrão (não tem senha).
- As ferramentas de rede exigem aceitar um aviso: use só em redes e aparelhos seus ou com
  autorização do dono.

## Arquivos

```
~/.termux_toons/
├── config.json            # tokens, portas, monitores...
├── logs/                  # um log por serviço
├── tarefas.json           # gerenciador de tarefas
├── monitores_estado.json  # último resultado de cada monitor
├── cache/legendas/        # legendas embutidas já extraídas
├── playlists/             # playlists .m3u
├── basic/                 # programas BASIC salvos
└── recordes.json
~/llama.cpp/               # código e build do llama.cpp
~/llama-models/            # modelos .gguf
```

Defina `TOONS_DEBUG=1` para ver o traceback completo de erros inesperados.
