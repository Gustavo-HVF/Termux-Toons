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
| 13 | 🔄 **Atualização** | `pkg upgrade`, troca de espelho (`termux-change-repo`), repositórios extras (x11/root/tur), pacotes pip, recompilar llama.cpp, atualizar distros, `git pull` em vários repositórios e no próprio Termux-Toons, limpeza de cache. |

Os downloads de música usam exatamente:

```bash
yt-dlp -f bestaudio --extract-audio --audio-format opus --embed-thumbnail --add-metadata \
       -o "~/storage/downloads/%(title)s.%(ext)s" "<link>"
```

(a pasta pode ser trocada no menu de música).

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
python termux_toons.py tocar                # biblioteca no aleatório
python termux_toons.py tocar lofi hip hop   # mix por busca
python termux_toons.py atualizar
```

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
├── playlists/             # playlists .m3u
├── basic/                 # programas BASIC salvos
└── recordes.json
~/llama.cpp/               # código e build do llama.cpp
~/llama-models/            # modelos .gguf
```

Defina `TOONS_DEBUG=1` para ver o traceback completo de erros inesperados.
