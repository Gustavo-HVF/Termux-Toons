# Módulo 1: limpeza e organização do menu

Relatório "antes e depois" da reorganização do menu. Nada foi tirado do programa: as opções duplicadas
passaram a existir num lugar só, e as opções soltas foram agrupadas em subcategorias.

## Resumo

| | Antes | Depois |
|---|---|---|
| Entradas no menu principal | 21 | 18 |
| Categorias duplicadas | 5 (em 12 lugares) | 0 |
| Opções duplicadas | 6 | 0 |
| Subcategorias novas | – | 12 (10 com `grupo()` + Sistema e manutenção + Aparência do terminal) |
| Entradas da 🔍 Busca apontando para o lugar errado | 1 | 0 |
| Verificação automática dos menus | não havia | `tests/verificar_menus.py` |

## Menu principal

| Antes (21) | Depois (18) |
|---|---|
| 🔍 Buscar opção | 🔍 Buscar opção |
| 🌐 Servidor web / API pessoal | 🌐 Servidor web / API pessoal |
| 🤖 Bots Telegram / Discord 24h | 🤖 Bots Telegram / Discord 24h |
| 🔎 Scraping e monitoramento | 🔎 Scraping e monitoramento |
| 🛡️ Rede e segurança | 🛡️ Rede e segurança |
| 🐧 Linux de verdade | 🐧 Linux de verdade |
| 🗄️ Arquivos e backup | 🗄️ Arquivos e backup |
| 🎵 Música, rádio e podcasts | 🎵 Música, rádio e podcasts |
| 🎬 Vídeos | 🎬 Vídeos |
| 📺 Compartilhar filme por link | 📺 Compartilhar filme por link |
| 🧮 Calculadora científica | *(foi para 🧰 Utilitários)* |
| 🧰 Utilitários | 🧰 Utilitários (calculadora, notas, senhas...) |
| 📲 Celular e sistema | 📲 Celular e sistema |
| 🌐 Internet | 🌐 Internet |
| 👤 Meus dados na internet | 👤 Meus dados na internet |
| ✨ Inteligência artificial | ✨ Inteligência artificial |
| 🎮 Diversão e aprendizado | 🎮 Diversão e aprendizado |
| 🛠️ Programação e servidores | 🛠️ Programação e servidores |
| 🔄 Atualização | ⚙️ **Sistema e manutenção** (nova), com: |
| 🧹 Otimização e limpeza | 🔄 Atualização · 🧹 Otimização e limpeza · 📦 Instalar dependências |
| ⚙️ Configurações e diagnóstico | · 🎨 Aparência do terminal · ⚙️ Configurações e diagnóstico |

## Removido (duplicatas): ficou só a versão mais completa

### Categorias que apareciam em mais de um lugar

| Categoria | Estava em | Ficou só em |
|---|---|---|
| 🌉 Pontes de conexão | 🛡️ Rede e segurança · 🌐 Internet | 🛡️ Rede e segurança |
| 🌐 Navegador pelo celular | 🌐 Internet · 🌉 Pontes de conexão | 🌐 Internet |
| 🌐 Traduzir a tela | ✨ IA · ✨ IA → 🔍 OCR · 🧰 Utilitários → 🌍 Tradutor | ✨ Inteligência artificial |
| 🔗 Endereço fixo (Cloudflare) | 🗄️ Arquivos · 📺 Compartilhar filme · 🌉 Pontes → ☁️ Cloudflare | 🌉 Pontes → ☁️ Cloudflare (os menus de site e de filmes mostram uma dica de onde ele fica) |
| 📺 Controle da TV | 📲 Celular e sistema · 📲 → 📱 Termux:API ("Infravermelho: controle da TV") | 📲 Celular e sistema |

### Opções que faziam a mesma coisa

| Opção removida | Onde estava | O que ficou no lugar |
|---|---|---|
| 📉 Reduzir a resolução de um filme | 📺 Compartilhar filme | 🎬 Vídeos → 📉 Reduzir a resolução / comprimir (é a mesma função) |
| 🎬 Comprimir vídeo (720p/480p) | 📲 → 🔁 Conversor de arquivos | 🎬 Vídeos → 📉 Reduzir a resolução / comprimir, que ganhou o modo **"arquivo bem menor"** (a compressão forte do antigo "Comprimir", CRF 27–30 e áudio 128 kbps), mantendo trilhas, legendas, ajuste de HDR e 60→30 quadros, que o "Comprimir" não tinha. Também aceita manter a mesma resolução e só comprimir. Na linha de comando: `reduzir-video ... --menor` |
| Limpar cache de pacotes | 🔄 Atualização | 🧹 Otimização e limpeza → ⚡ Otimização rápida, que já limpava o cache do apt e o `~/.cache` (onde fica o cache do pip) e agora também faz o `apt autoremove`, que só a outra fazia |
| Monitor do tipo "Bateria abaixo de um limite" | 🔎 Scraping → Adicionar monitor | 🔋 Saúde da bateria → Configurar alertas (80%, bateria baixa e temperatura, com histórico). Os monitores desse tipo já cadastrados continuam funcionando |
| Monitor do tipo "Chuva prevista" | 🔎 Scraping → Adicionar monitor | 🌦️ Previsão do tempo → Criar alerta de chuva (usa a mesma função). Os já cadastrados continuam funcionando |
| Instalar dependências (yt-dlp, ffmpeg...) | 🎵 Música · 🎬 Vídeos · "Instalar os essenciais" em ⚙️ Configurações | ⚙️ Sistema e manutenção → 📦 Instalar dependências, onde se marca o que instalar (essenciais, música, vídeos). Cada opção do menu continua instalando sozinha o que falta, perguntando antes |

### Parecidas, mas não duplicadas (ficaram)

- **Túnel da Cloudflare** no servidor web, nos filmes, no catálogo do TorBox, no site publicado e no trote:
  cada um publica a porta do seu serviço. O nome foi padronizado para **"🌍 Liberar na internet (túnel)"**,
  "🌍 Túnel: desligar" e "🌍 Túnel: mostrar o endereço".
- **SMS pelo Termux:API** e **SMS pelo modem (AT)**: são caminhos diferentes (o app × o modem, com root).
- **Notícias RSS** (ler, em 🌐 Internet) e **monitor de RSS** (avisar quando sai notícia nova, em 🔎 Scraping).
- **Lista de tarefas** e **Tarefas agendadas** foram renomeadas para não serem confundidas:
  "✅ Lista de afazeres" e "⏲️ Agendar comandos (cron)".

## Movido (opções soltas ou fora do lugar)

| Opção | De | Para |
|---|---|---|
| 🧮 Calculadora científica | menu principal (uma categoria com uma ferramenta só) | 🧰 Utilitários |
| 📡 Modem: comandos AT | 🛡️ Rede e segurança | 📲 Celular e sistema (agora com o ícone 📶) |
| Tema de cores, fonte do terminal, mensagem de boas-vindas, banner original | 🎮 Diversão → 🎨 Arte ASCII | ⚙️ Sistema e manutenção → 🎨 Aparência do terminal |

## Criado (subcategorias para as opções soltas)

| Onde | Subcategoria nova | Opções que entraram |
|---|---|---|
| 🛡️ Rede e segurança | 🔍 Diagnóstico de rede | informações de rede, descobrir dispositivos, portas, DNS/ping/traceroute, velocidade, Wi-Fi próximas, tráfego (7) |
| 🛡️ Rede e segurança | 🔐 Servidor SSH | instalar e definir senha, iniciar, parar, autorizar chave (4) |
| 🗄️ Arquivos e backup | 🌍 Publicar site | publicar, ver links, QR code, liberar na internet, ver quem acessou, avisar visitante novo, limpar visitas, tirar do ar (8) |
| 🗄️ Arquivos e backup | ☁️ Nuvem e sincronização | rclone (4) e Syncthing (2) |
| 🗄️ Arquivos e backup | 📡 Compartilhar na rede | pasta via HTTP (4) e Samba (2) |
| 🗄️ Arquivos e backup | 💾 Backup do Termux | fazer e restaurar (2) |
| 🎵 Música | ▶ Ouvir | buscar e tocar, álbum, cantor ou banda, mix (4) |
| 🎵 Música | ⬇️ Baixar músicas | busca, álbum, cantor ou banda, link, Spotify (5) |
| 🎵 Música | 📚 Biblioteca e playlists | biblioteca (2) e playlists (2) |
| 📺 Compartilhar filme | ⚙️ Servidor, túnel e ajustes | servidor (4), túnel (3), apagar expirados/todos (2), porta, conversões ao mesmo tempo (11) |
| menu principal | ⚙️ Sistema e manutenção | Atualização, Otimização e limpeza, 📦 Instalar dependências (nova), 🎨 Aparência do terminal, Configurações |
| ⚙️ Sistema e manutenção | 🎨 Aparência do terminal | tema, fonte, voltar à fonte original, boas-vindas, banner original |

## Erros corrigidos no caminho

- **🔍 Busca:** "💬 Assistente na nuvem (Claude, ChatGPT, Gemini)" abria a **IA local (llama.cpp)**. Agora
  "💬 Conversar com a IA na nuvem" abre a conversa direto, e a IA local tem a sua própria entrada.
- **🔍 Busca:** "⏱️ Relógio (alarme, cronômetro, timer)" levava a um menu sem alarme (o alarme fica em
  Lembretes). Agora são "⏱️ Cronômetro, timer e Pomodoro" e "⏰ Lembretes e alarmes".
- **🔍 Busca:** não achava as Pontes de conexão, o Endereço fixo, o Navegador pelo celular, o catálogo do
  TorBox, o Reduzir a resolução, a Lista de afazeres nem a IA local. Essas entradas foram acrescentadas.
- **README:** dizia que "Assistir um link" ficava no menu 📺 (fica em 🎬 Vídeos) e que o menu do ADB limpava
  o cache de todos os apps (fica em 🧹 Otimização). Também foram atualizados os caminhos que mudaram.
- **Dicas na tela:** as mensagens que mandavam para "Túnel para a internet", "Site publicado: liberar para a
  internet" e "Reduzir a resolução de um filme" agora citam os caminhos novos.

## Como foi verificado

- `python3 -m py_compile termux_toons.py`: o arquivo compila.
- `python3 tests/verificar_menus.py`: nenhuma duplicata, nenhum menu solto e busca coerente
  (86 menus, 10 subcategorias e 638 opções conferidas). Rodando o mesmo verificador na versão anterior, ele
  acusa as 6 duplicatas e o erro da busca descritos acima.
- **Teste de uso:** todas as 18 categorias e todas as subcategorias novas foram abertas pelo modo de números e
  pelo modo de setas (num terminal simulado), sem erro. A busca foi testada com "aparencia" e "assistente".
- **Conversão de verdade:** um vídeo 1080p de teste foi reduzido no modo "arquivo bem menor" para 720p
  (4,7 MB → 349 KB) pelo menu, e para 480p pela linha de comando (`reduzir-video --menor`).
- **Não testado aqui:** as funções que dependem do Android/Termux (Termux:API, ADB, root), porque o teste
  rodou num Linux comum. Elas não foram alteradas, só mudaram de lugar no menu.

## Arquivos

| Arquivo | O que mudou |
|---|---|
| `termux_toons.py` | menus reorganizados, `grupo()` (novo), `menu_sistema()`, `menu_aparencia()` e `instalar_dependencias()` (novos), modo "arquivo bem menor" no Reduzir a resolução (`--menor`), índice da busca corrigido, dicas na tela e resumo do topo atualizados |
| `README.md` | tabela "O que tem no menu" com as 17 categorias novas, caminhos corrigidos e seção "Para quem mexe no código" |
| `tests/verificar_menus.py` | novo: verificador automático dos menus |
| `docs/relatorio-modulo-1.md` | novo: este relatório |
