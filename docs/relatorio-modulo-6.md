# Módulo 6: ferramentas inspiradas nos programas de terminal mais usados do GitHub

Levantei os programas de terminal mais populares do GitHub (pelas estrelas e por aparecerem nas listas
"awesome") que ainda não tinham equivalente no LNUX, e propus 19 ferramentas. Você aprovou **todas**.

Nenhuma é cópia: cada uma foi escrita do zero dentro do `lnux.py`, quase sempre só com a biblioteca padrão do
Python. Quando o programa original é a melhor opção (asciinema, croc, nethogs, Oh My Zsh, Starship), o LNUX
instala e usa o programa, perguntando antes, e cuida do resto (pastas, nomes de pacote em cada distro,
configuração, desfazer).

O código novo fica numa seção própria do `lnux.py`: **"28. Ferramentas inspiradas nos programas de terminal
mais usados do GitHub"** (logo depois das Mensagens secretas). Cada ferramenta entrou no menu onde a pessoa
procuraria por ela, e todas estão na 🔍 Busca.

## O que tem

| # | Ferramenta | Inspirada em | Onde fica no menu | Como foi feita |
|---|------------|--------------|-------------------|----------------|
| 1 | 🖥️ Ficha do sistema | neofetch, fastfetch | 📲 Celular e sistema | Própria: logo (Tux ou Android) com as cores da distro, sistema, aparelho, kernel, tempo ligado, pacotes, shell, terminal, CPU, memória, disco, bateria, IP, Python. Também `lnux.py ficha` |
| 2 | ⚙️ Processos ao vivo | htop, btop | 📲 Celular e sistema | Própria, lendo o `/proc`: CPU e memória de cada processo, ordenar (`c`/`m`/`p`), filtrar (`/`), encerrar (`k`) ou forçar (`K`), com sudo se o processo for de outro usuário |
| 3 | 💽 Explorar o espaço | ncdu, dust | ⚙️ Sistema › 🧹 Otimização e limpeza | Própria: pastas por tamanho com barras, entrar/voltar com as setas, apagar (pergunta antes) e abrir; guarda os tamanhos já calculados |
| 4 | 🐚 Shell bonito | Oh My Zsh, Starship | ⚙️ Sistema › 🎨 Aparência do terminal | Instala o zsh, clona o Oh My Zsh e os plugins de sugestão e de cores (clone raso), escolhe o tema; ou instala o Starship com um preset. As linhas que o LNUX põe no `.bashrc`/`.zshrc` são marcadas (`# LNUX:`) e o **Desfazer** tira só elas e volta a cópia `.zshrc.antes-do-lnux` |
| 5 | 🎬 Gravar o terminal | asciinema | 🛠️ Programação e servidores | Usa o asciinema: gravar, assistir, mandar para o asciinema.org e apagar; os `.cast` ficam em `Download/LNUX/Gravações do terminal` |
| 6 | 📚 Cola de comandos | tldr | 🛠️ Programação e servidores | Própria: baixa as páginas oficiais uma vez (o zip do projeto tldr-pages, ≈ 8 mil comandos) e mostra em português quando há tradução (pt_BR, depois pt_PT, depois inglês); sem as páginas baixadas, busca uma por vez na internet |
| 7 | 📦 croc | croc | 🗄️ Arquivos e backup | Usa o croc: mandar arquivos ou um texto com um código; receber (o código vai por variável de ambiente, não aparece na lista de processos) |
| 8 | 🌐 Compartilhar pasta | `python -m http.server`, dufs | 🗄️ Arquivos › compartilhar na rede | Servidor próprio (substitui o `http.server` que estava lá): baixar com retomada (Range), **mandar arquivos pelo navegador** (opcional; arrastar e soltar, barra de progresso, nunca sobrescreve), **senha** opcional e QR code. Também `lnux.py pasta` |
| 9 | 📈 Ping com gráfico | gping | 🛡️ Rede › 🔍 Diagnóstico | Própria: um ping por endereço em paralelo, gráfico ao vivo de cada um, mín/média/máx e perda |
| 10 | 📶 Internet por programa | nethogs, bandwhich | 🛡️ Rede › 🔍 Diagnóstico | Usa o bandwhich (se estiver instalado) ou o nethogs, com sudo |
| 11 | 🔌 Testar uma API | HTTPie, curlie | 🛠️ Programação e servidores | Própria: método, cabeçalhos e corpo; resposta com status, tempo, cabeçalhos e JSON colorido; mostra o comando `curl` equivalente; histórico para repetir |
| 12 | 🔍 Ver JSON e Markdown | jq, fx, glow | 🛠️ Programação e servidores | Própria: navega no JSON (arquivo, área de transferência ou link) mostrando o caminho no estilo do jq (`.itens[0].nome`); Markdown formatado pelo rich, ou por um formatador simples se o rich não estiver instalado |
| 13 | 🐳 Contêineres | lazydocker | 🛠️ Programação e servidores | Própria, sobre o Docker ou o Podman (o que tiver): logs, terminal, parar, iniciar, remover, imagens, baixar, rodar e limpar |
| 14 | 🛎️ Serviços e logs | systemctl, journalctl | ⚙️ Sistema e manutenção | Própria, sobre o systemd ou o OpenRC (Alpine): status, iniciar, parar, ligar no boot, logs, os que falharam, erros desde que ligou e logs ao vivo |
| 15 | 🔑 Códigos 2FA | Google Authenticator, 2fa | 🧰 Utilitários | Própria (HOTP/TOTP das RFC 4226 e 6238, SHA-1/256/512, 6 ou 8 dígitos): adicionar pelo QR code (foto, com o zbarimg), pelo link `otpauth://` ou pela chave; exportar como QR code; os códigos se atualizam sozinhos. As contas ficam cifradas com AES-256-GCM e a sua senha (o mesmo das Mensagens secretas) |
| 16 | 🎤 Letra da música | sptlrx | 🎵 Música | Própria: pega artista e título da música que o player do LNUX está tocando, busca no LRCLIB (gratuito, sem cadastro), guarda no cache e acompanha o tempo do player destacando o verso atual |
| 17 | ⌨️ Teste de digitação | Monkeytype, ttyper | 🎮 Diversão e aprendizado | Própria: palavras comuns do português, com ou sem acentos, 30/60 segundos ou 25/50 palavras; palavras por minuto, precisão e recorde por modo |
| 18 | 💹 Cripto e bolsa | cointop, ticker | 🧰 Utilitários | Própria: as 20 maiores criptomoedas em real (CoinGecko), busca com gráfico de 1 dia a 1 ano, favoritas; e uma lista da bolsa sua (Yahoo Finance: Ibovespa, ações `.SA`, dólar) com o gráfico do último mês |
| 19 | 🌌 Telas de descanso | cmatrix, pipes.sh, asciiquarium | 🎮 Diversão e aprendizado | Próprias: chuva do Matrix, canos coloridos e aquário; acompanham o tamanho do terminal e qualquer tecla sai |

Para os gráficos no terminal (ping, cotações, processos) escrevi duas funções que as outras partes também podem
usar: `sparkline()` (uma linha com `▁▂▃▄▅▆▇█`, deixando um espaço onde faltou o dado) e `grafico_em_colunas()`.

### O que foi substituído

| Antes | Agora |
|-------|-------|
| ⚙️ Sistema › Otimização › "Processos que mais usam RAM" (uma lista do `ps`) | ⚙️ Processos ao vivo, em 📲 Celular e sistema |
| ⚙️ Sistema › Otimização › "Ver o que ocupa espaço" (um `du` das pastas) | 💽 Explorar o espaço, no mesmo lugar |
| 🗄️ Arquivos › "Compartilhar pasta por HTTP" (`python -m http.server`, só baixar) | Servidor próprio com envio, senha e QR code |

O verificador dos menus continua sem acusar duplicatas: as duas opções antigas saíram do código.

### O que depende do sistema

| Ferramenta | Onde aparece | Por quê |
|------------|--------------|---------|
| 📶 Internet por programa | fora do Android | Precisa de root para ver os sockets de outros programas |
| 🐳 Contêineres | nas distros | Docker e Podman não rodam no Termux sem root |
| 🛎️ Serviços e logs | nas distros com systemd ou OpenRC | O Termux não tem gerenciador de serviços do sistema (os serviços do LNUX lá são as sessões tmux) |
| ⚙️ Processos ao vivo | todos | No Android 7 ou mais novo, o sistema só deixa ver os processos do próprio Termux; a tela avisa |

Pacotes novos nos perfis (`distros/*.json`), pelo nome do Termux:

| Pacote | Termux | Debian/Ubuntu | Arch | Fedora | Alpine | openSUSE |
|--------|--------|---------------|------|--------|--------|----------|
| zsh | zsh | zsh | zsh | zsh | zsh | zsh |
| starship | starship | — ¹ | starship | — ¹ | starship | starship |
| asciinema | asciinema | asciinema | asciinema | asciinema | asciinema | asciinema |
| croc | croc | — ¹ | croc | — ¹ | croc | — ¹ |
| nethogs | — | nethogs | nethogs | nethogs | nethogs | nethogs |
| ping (`iputils`) | inetutils | iputils-ping | iputils | iputils | (BusyBox) | iputils |

¹ Sem pacote no repositório oficial: o LNUX mostra e oferece o instalador oficial do projeto
(`curl -sS https://starship.rs/install.sh | sh` e `curl https://getcroc.schollz.com | bash`), perguntando antes.

### Segurança

- **Compartilhar pasta**: arquivos e pastas ocultos (`.ssh`, `.config`...) não aparecem nem podem ser baixados;
  caminhos com `..` (também codificados, como `%2e%2e`) e atalhos que apontam para fora da pasta são recusados;
  a senha é conferida em tempo constante; um envio nunca sobrescreve (vira `nome (2).ext`) e fica como
  `.enviando` até terminar, então um envio cortado não deixa um arquivo pela metade com o nome certo. O servidor
  escuta na rede local: o menu pergunta se quer senha (o padrão é sim) e avisa quando fica sem.
- **2FA**: as chaves só ficam no disco cifradas com a sua senha; sem ela, o arquivo `2fa.lnuxcripto` não serve
  para nada. Ao criar a senha, o menu avisa que sem ela não dá para ver nem recuperar os códigos; o **Exportar**
  (QR code) serve de cópia de segurança.
- **croc**: o código de recebimento vai pela variável `CROC_SECRET` (o jeito recomendado pelo croc), e não na
  linha de comando, que outros programas do aparelho conseguiriam ler.
- **Shell bonito**: antes de mexer no `.zshrc`, guarda uma cópia; o LNUX só apaga as linhas que ele mesmo marcou.

## Como foi verificado

Teste novo, `tests/testar_ferramentas_novas.py` (só biblioteca padrão; usa uma pasta pessoal temporária, então
não mexe nos seus arquivos): **22 casos, todos passando**.

| O que testa | |
|-------------|--|
| Gráficos | sparkline (com pings perdidos) e gráfico em colunas |
| Ficha do sistema | as informações principais aparecem |
| Processos | o próprio teste aparece na lista e o % de CPU é calculado |
| Espaço em disco | pastas somadas, do maior para o menor, com cache |
| Shell bonito | as linhas do LNUX entram uma vez só e saem ao desfazer |
| Serviços | lê a saída do `systemctl` e do `rc-status` (OpenRC) |
| Pasta (4 casos) | lista, baixa, baixa um pedaço (Range 206 e 416) e esconde ocultos · não deixa sair da pasta (`..`, `%2e%2e`, atalho para fora) · envio (PUT) sem sobrescrever, e 403 quando desligado · com senha: 401 sem login, 401 com a senha errada, 200 com a certa |
| Ping | lê o tempo do Linux, do Android, do BusyBox e respostas sem tempo |
| API HTTP | GET e POST num servidor local, JSON colorido e o comando curl exato |
| JSON e Markdown | filhos, resumo e caminho no estilo do jq; Markdown sem o rich |
| Contêineres | lê a lista do Podman (JSON) e do Docker (uma linha por contêiner) |
| tldr | mostra a página em português quando existe e cai no inglês quando não |
| 2FA (3 casos) | HOTP com os vetores da RFC 4226 · TOTP com os vetores da RFC 6238 (SHA-1, SHA-256, SHA-512, 8 dígitos) · lê e monta o link `otpauth://`, recusa chave inválida |
| Letra | formato LRC (vários tempos por verso) e o verso do momento |
| Digitação | palavras por minuto, precisão e quebra de linha com cores |
| Cotações | lê o mercado do CoinGecko e o gráfico do Yahoo Finance |
| Telas de descanso | cada quadro ocupa exatamente as linhas e colunas do terminal |

Além disso:

- **Telas de verdade, num terminal simulado (pty)**: processos ao vivo, explorar o espaço (entrar e voltar),
  ping com gráfico (127.0.0.1 e localhost), chuva do Matrix, aquário, teste de digitação e a tela dos códigos
  2FA abriram, responderam às teclas e saíram sem erro.
- **Comando real**: `python3 lnux.py pasta <pasta> --porta 8765`, com envio e senha ligados, testado pelo
  `curl`: sem senha 401, com senha 200, o download veio certo, o envio respondeu 201 e o arquivo apareceu na pasta.
- **tldr de verdade**: baixou as páginas do GitHub (8075 comandos) e mostrou a página do `tar` em português.
- Os testes que já existiam continuam passando: `verificar_menus.py` (nenhuma duplicata, busca coerente, nenhum
  menu solto, nenhum submenu vazio em nenhum sistema; agora são 806 opções, 163 que dependem do sistema),
  `verificar_perfis.py` (7 perfis), `testar_menus_por_sistema.py` (todos os menus abrem nos 7 sistemas) e
  `testar_mensagens_secretas.py` (24 casos). O `pyflakes` não acusa nada.

### Erros que os testes pegaram durante o trabalho

- A página do tldr usava `\` dentro de uma f-string, o que só funciona no Python 3.12 ou mais novo: quebraria no
  Debian 12 (Python 3.11). Reescrevi sem isso.
- Na chuva do Matrix, os caracteres katakana de meia largura desalinhavam as colunas; e os cantos dos canos
  saíam virados em algumas curvas (troquei a lógica por uma tabela de cantos).
- No teste de digitação, as cores quebravam a linha no lugar errado (as cores não ocupam espaço na tela, mas
  contavam no tamanho). Agora a quebra conta só o que aparece.
- O ping de endereços rápidos mostrava "0 ms": agora mostra uma casa decimal abaixo de 10 ms.
- Sem internet, a letra da música dizia "não achei a letra", como se ela não existisse. Agora mostra o erro de
  conexão.
- O contêiner de testes não tinha o `ping`: a ferramenta agora instala o pacote certo de cada distro (por isso
  a chave `iputils` nos perfis).

### Um defeito antigo que apareceu no caminho: o LNUX não abria no Python 3.11

Testando as ferramentas novas com Pythons mais antigos, descobri que o `lnux.py` inteiro **não abria no
Python 3.11 nem nos anteriores**, ou seja, no Debian 12 e no Ubuntu 22.04, embora o README prometa o 3.9.
O defeito era antigo (do navegador pelo celular, bem antes deste módulo): uma f-string que reaproveitava as
mesmas aspas dentro das chaves, `f'{' data-completo="1"' if completo else ""}'`, algo que só o Python 3.12
aceita. Como eu testava só no 3.13, nada acusava.

- **Corrigido** em `_script_do_navegador` (o HTML gerado é idêntico ao de antes; conferido).
- **Conferido no 3.9, 3.10, 3.11 e 3.13**: todas as baterias de teste acima rodaram nas quatro versões e
  passaram (o 3.9 e o 3.10 instalados à parte só para o teste).
- **Verificador novo**, `tests/verificar_compatibilidade.py`, que roda em qualquer versão do Python e acusa o que
  não funcionaria no 3.9: f-strings no estilo do 3.12 (aspas repetidas, barra invertida ou comentário dentro das
  chaves; o próprio `ast` do Python não acusa isso), sintaxe nova (como `match`) e funções da biblioteca padrão
  que só existem do 3.10 em diante (`tomllib`, `itertools.batched`, `zip(strict=...)`, `isinstance(x, A | B)`...).
  Calibrei a parte das f-strings comparando com o Python 3.11 de verdade em 25 casos: nenhuma divergência.
  Hoje ele não acusa nada no código, e acusa a linha certa na versão de antes da correção.

## O que não foi feito ou não pôde ser testado

- **CoinGecko, Yahoo Finance e LRCLIB**: a rede do ambiente onde trabalhei bloqueia esses sites, então as
  cotações e a letra da música não foram testadas com dados reais. Os leitores dos dados foram testados com
  respostas no formato que esses serviços documentam. O Yahoo Finance não tem API oficial e pode mudar sem
  aviso; se isso acontecer, só essa parte precisa ser ajustada (`parse_yahoo`).
- **Não testei num Android de verdade** nem nas distros de verdade além do contêiner Debian em que trabalhei:
  as outras distros foram testadas pela simulação de perfil (`LNUX_SISTEMA=arch` etc.). Os nomes de pacote
  novos foram escolhidos pelo que conheço dos repositórios de cada distro, sem poder instalar em cada uma: um ou
  outro pode ter outro nome ou não existir numa versão. Se faltar, o perfil se corrige editando só o
  `distros/<id>.json`.
- **Instalações que mexem no sistema não foram rodadas aqui**: Oh My Zsh, Starship, asciinema, croc, nethogs e
  bandwhich (a lógica de colocar e tirar as linhas dos arquivos do shell foi testada numa pasta temporária).
  O croc precisa de outro aparelho para testar o envio de ponta a ponta.
- **Docker/Podman e systemd/OpenRC** não existem no contêiner de testes: a leitura das saídas foi testada com
  exemplos no formato que esses programas imprimem, mas os botões (parar, iniciar, logs) não foram apertados de verdade.
- **2FA pela foto do QR code**: a leitura usa o `zbarimg`; não testei com uma foto real (o link `otpauth://` e a
  chave digitada foram testados).

## Arquivos

| Arquivo | O que mudou |
|---------|-------------|
| `lnux.py` | Seção nova "28. Ferramentas inspiradas nos programas de terminal..." com as 19 ferramentas; itens nos menus de 📲 Celular, 🗄️ Arquivos, 🛡️ Rede, 🎵 Música, 🧰 Utilitários, 🎮 Diversão, 🛠️ Programação e ⚙️ Sistema; 19 entradas novas na 🔍 Busca; subcomandos `pasta` e `ficha`; correção da f-string que impedia o LNUX de abrir no Python 3.11 ou mais antigo; instaladores oficiais do Starship e do croc; saíram as opções antigas de processos e de espaço; "Compartilhar pasta" usa o servidor novo; cabeçalho do arquivo atualizado |
| `distros/termux.json`, `debian.json`, `arch.json`, `fedora.json`, `alpine.json`, `opensuse.json`, `outro.json` | Nomes dos pacotes zsh, starship, asciinema, croc, nethogs e iputils |
| `tests/testar_ferramentas_novas.py` | Novo: os 22 casos acima |
| `tests/verificar_compatibilidade.py` | Novo: confere se o código continua abrindo no Python 3.9 ou mais novo |
| `README.md` | Seção nova "Ferramentas de terminal", novidades na tabela do menu, `lnux.py ficha` e `lnux.py pasta`, arquivos novos em `~/.lnux` e os dois testes novos |
| `docs/relatorio-modulo-6.md` | Este relatório |
