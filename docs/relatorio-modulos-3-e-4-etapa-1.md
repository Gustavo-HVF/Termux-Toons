# Módulos 3 e 4, etapa 1: LNUX-APPs (base, ponte e lote de vídeo e som) e a categoria 🧩 Apps Web

## O que foi decidido antes

A conta **storytold** do GitHub é a organização da ArtCraft Team, com 66 repositórios. Os apps são os
**Crafting Apps**: 15 programas de criação profissionais, em Rust, cada um do porte de um Photoshop, Premiere,
Word, Excel ou AutoCAD (e todos com uma versão oficial em WebAssembly), mais o ArtCraft (estúdio de IA), o
AniCraft, o MaterialCraft e ferramentas internas. Licença: **MIT ou Apache-2.0**; o nome ArtCraft e os logos são
marcas, fora da licença.

Como reescrever todos completos não é possível, você escolheu:

- **versões leves de todos, em lotes**, com confirmação entre um lote e outro;
- o **primeiro lote: vídeo e som** (FilmCraft, EffectCraft, SoundCraft);
- **incluir o estúdio de IA** (ArtCraft) no último lote; o Craft Anything e os painéis de PRs deles ficam de
  fora.

Plano das etapas: **1)** base do LNUX-APPs + ponte + lote 1 + módulo 4 (esta); **2)** editor de código
(Monaco) e VLC-Web; **3)** os dois sites de mensagens com o servidor de códigos de verificação; **4 em diante)**
escritório, imagem, design/técnico e, por último, o estúdio de IA.

## O repositório LNUX-APPs

[github.com/Gustavo-HVF/LNUX-APPs](https://github.com/Gustavo-HVF/LNUX-APPs), licença MIT, com os créditos
da storytold em `CREDITOS.md` e um README próprio (instalação, uso, ponte, atalhos, o que falta).

### Base comum (`comum/`)

- **Temas** salvos no navegador e iguais em todos os apps: Do sistema, Escuro, Claro, Sépia, Oceano e Alto
  contraste. **Tamanho dos controles** (compacto, normal, confortável para toque) e **layout por app** (cada
  app tem 4; no celular, o layout de tela pequena entra sozinho). Tudo na janela **Aparência** (◐).
- Barra de menus com **atalhos de teclado** (no celular vira um botão ☰), **paleta de comandos**
  (`Ctrl+Shift+P`), diálogos, avisos, divisores arrastáveis entre painéis, **desfazer/refazer**.
- **Guardado no navegador** (IndexedDB): o projeto volta sozinho ao abrir o app de novo.
- **Abrir e salvar**: com a ponte, numa janela com as pastas do aparelho; sem ela, pelo navegador.
- `zip.js` (projetos num arquivo só) e `gif.js` (GIF animado feito no navegador), escritos aqui.
- **Página inicial** com busca e categorias, que lê o catálogo `apps.json` (prontos e "em breve").

### Ponte local (`servidor/lnux_apps.py`, só biblioteca padrão do Python)

| O que | Detalhes |
|---|---|
| Arquivos | listar, ler (com Range), gravar (sem sobrescrever, a não ser que peça), copiar, mover, apagar, envio temporário |
| ffmpeg | conversão em segundo plano com progresso e cancelamento, só por **perfis prontos** (MP4, WebM, GIF, MP3, OGG, Opus, M4A, FLAC, WAV); informações pelo ffprobe |
| Aparelho | bateria, área de transferência, notificação, falar, vibrar, dados do sistema (Termux:API ou os equivalentes do Linux) |
| Comandos | rodar um programa: **desligado** por padrão |

Segurança:
- escuta só em `127.0.0.1`;
- exige uma chave em cada pedido, guardada em `~/.lnux-apps/ponte.json` com permissão 600;
- recusa nomes de domínio no `Host`, o que bloqueia o *DNS rebinding*;
- recusa pedidos que mudam algo vindos de outra origem;
- só mexe nas pastas liberadas, seguindo atalhos até o destino real;
- o cookie das mídias tem `HttpOnly` e `SameSite=Strict`, e vale só para ler arquivos.

### Lote 1

| App | Inspirado em | O que tem |
|---|---|---|
| 🎬 Vídeo | FilmCraft | Mídias com miniatura; linha do tempo com trilhas de vídeo e áudio; mover (inclusive entre trilhas), aparar, separar (S), ferramenta de corte (C), apagar fechando o buraco, duplicar, copiar/colar, marcadores, ímã; monitor com arrastar e rodinha para mover e redimensionar; cor (7 looks + brilho, contraste, saturação, temperatura, matiz, desfoque, vinheta); transições de entrada/saída (dissolver, deslizar, cortina, zoom); velocidade; volume e fades; separar o áudio; títulos com 4 animações e terço inferior; legendas SRT (importar e exportar); exportar WebM, MP4 e GIF (pela ponte) e o quadro em PNG; 6 tamanhos de projeto, incluindo vertical e quadrado |
| ✨ Efeitos | EffectCraft | Camadas de texto, forma (retângulo, elipse, estrela, polígono, linha, anel), partículas (6 direções, confete, neve, explosão), imagem e vídeo; quadros-chave com 8 suavizações; ⏱ por propriedade (mexer no valor cria o quadro-chave no cursor); arrastar, redimensionar e girar no visor; "tremer"; desfoque, brilho, sombra, matiz, desenho do contorno; 11 modos de mistura; texto animado letra por letra (5 jeitos); 12 animações prontas e 7 modelos; exportar GIF e sequência PNG (com transparência) no navegador, WebM, MP4 pela ponte |
| 🎚️ Som | SoundCraft | Trilhas com forma de onda; gravar pelo microfone na trilha armada (com compensação de atraso); importar (e converter pela ponte o que o navegador não abre); mover, aparar, fades arrastando, separar, duplicar, copiar/colar, normalizar, tocar ao contrário; volume, pan, mudo, solo; EQ 3 bandas, compressor, eco e reverb por trilha; mixer com medidores; BPM, compasso, grade, metrônomo, loop; exportar WAV 16/24 bits ou MP3/OGG/Opus/FLAC/M4A, a mixagem ou uma trilha por arquivo |

## Módulo 4: categoria 🧩 Apps Web no LNUX

No menu principal, depois de 🌐 Internet. O LNUX:

- **baixa** o LNUX-APPs em `~/.lnux/lnux-apps` na primeira vez (com o git) e o **atualiza** quando você pede;
- monta a **lista de apps a partir do `apps.json`**: um app novo no LNUX-APPs aparece aqui sem mexer no LNUX;
- ao abrir um app, **liga o servidor sozinho** (serviço `apps-web`, no tmux) **com a ponte quando o app a usa**,
  ou só nos apps que não funcionam sem ela, se você preferir, e **abre o navegador já com a chave**. Se o
  servidor já estiver ligado do jeito certo, ele é reaproveitado; se não, é reiniciado. Se a porta estiver
  ocupada por outro programa, pergunta outra;
- *📡 Abrir em outro aparelho da rede*: liga para o Wi-Fi e mostra o link com QR code (com aviso);
- *⚙️ Ponte*: liberar e tirar pastas, ligar os comandos, ponte sempre ou só quando precisa, trocar a chave;
- `python lnux.py apps` e `python lnux.py apps som` na linha de comando; a 🔍 Busca acha "vídeo", "som",
  "efeitos", "filmcraft"...

## Como foi verificado

- **LNUX-APPs, `tests/testar_servidor.py`** (só Python): 17 casos, cobrindo:
  - os arquivos dos apps;
  - a chave (sem, errada, certa) e o *DNS rebinding*;
  - o cookie só para ler;
  - as pastas liberadas, com atalho para fora;
  - Range e as respostas 206 e 416;
  - gravar sem sobrescrever, mover, copiar e apagar;
  - o envio temporário;
  - a conversão de WAV para MP3 e OGG, com progresso;
  - os comandos desligados e ligados;
  - o modo sem ponte;
  - a chave com permissão 600;
  - a conexão reaproveitada.

  Passa no Python 3.9 e no 3.13.
- **LNUX-APPs, `tests/testar_navegador.py`**: sobe o servidor com pastas temporárias, gera mídias de teste
  com o ffmpeg e roda os três apps no **Chromium de verdade** (Playwright). São 69 verificações: Som 26,
  Vídeo 23 e Efeitos 20.
  - Exportações reais, conferidas fora do navegador:
    - **MP4 H.264 com som** do Vídeo e **MP4** do Efeitos, conferidos pelo ffprobe;
    - **WAV** e **MP3** do Som;
    - **GIF de 24 quadros** e **PNG com transparência** do Efeitos, conferidos pelo Pillow.
  - Também testados:
    - **gravação pelo microfone** (simulado);
    - recuperação depois de recarregar a página;
    - temas, layouts, paleta de comandos;
    - tela de celular sem rolar para o lado;
    - nenhum erro no console.
- Página inicial e os 6 temas nos três apps: sem erros.
- **LNUX, `tests/testar_apps_web.py`** (novo): catálogo, chave no link conforme o app e a configuração,
  reconhecimento do servidor com ponte, sem ponte e com chave errada. Passa no 3.9 e no 3.13.
- **Teste ao vivo do módulo 4**: abrir o Som pelo LNUX ligou o servidor no tmux com a ponte e abriu o link com
  a mesma chave do `ponte.json`; abrir de novo reaproveitou o servidor; o modo rede respondeu pelo IP; parar
  desligou.
- Todos os testes antigos do LNUX continuam passando nos 7 sistemas, e o verificador de compatibilidade
  confirma o Python 3.9.

### Erros que os testes pegaram durante o trabalho

- **Ponte:** quando a ponte respondia sem ler o corpo do pedido (no `/api/entrar`, por exemplo), os bytes que
  sobravam viravam o "próximo pedido" na mesma conexão. Corrigido e coberto por um teste que falha sem a
  correção.
- **Janela de pastas:** o Enter no campo do caminho apertava "Abrir", em vez de ir para a pasta.
- **Celular:**
  - a barra de menus não cabia na tela (agora vira ☰);
  - os grupos de botões das barras quebravam em colunas;
  - os nomes das trilhas e camadas saíam cortados.
- **Teclado:** o Enter e o Espaço num botão com foco também disparavam o atalho.
- **Som:** sem um fade mínimo, os cortes estalavam (agora todo clipe tem 4 ms nas pontas).

## O que não foi feito ou não pôde ser testado

- **As versões são leves.** Do que os originais têm, ficou de fora, entre outros:
  - **Vídeo:** edição de três pontos, curvas e rodas de cor, máscaras, chroma key, estabilização, mixer com
    automação e intercâmbio XML;
  - **Efeitos:** Lottie, expressões, máscaras, 3D, marionete e parentesco;
  - **Som:** MIDI, automação, plugins e punch-in.
- **Exportação de vídeo.** O vídeo é gravado enquanto toca (MediaRecorder): leva o tempo do vídeo e precisa da
  aba aberta na frente. O GIF e o PNG do Efeitos são feitos quadro a quadro e não têm esse limite.
- **Navegadores.** Só testei no Chromium. No Safari, a correção de cor do Vídeo não aparece, porque ele não
  suporta o filtro de canvas; e não há celular de verdade aqui. No Android, o Chrome deve funcionar como o
  Chromium testado.
- **Projetos grandes.** O IndexedDB tem limite de espaço do navegador. Se um vídeo grande não couber, o app
  avisa e sugere salvar o projeto num arquivo.
- **O LNUX-APPs precisa estar no GitHub para o "Baixar" do LNUX funcionar.** Nesta etapa vai um commit inicial
  na branch principal (só licença e README) e o resto num pull request. Até você aceitar o PR, o LNUX baixa
  só esse início, então dá para testar abrindo o PR.
- Instalar o git e o tmux sozinho, pelo LNUX, foi testado só nas distros simuladas (o contêiner já tinha os dois).

## Arquivos

**LNUX-APPs (novo):**
- `README.md`, `CREDITOS.md`, `LICENSE`, `.gitignore`
- `apps.json`, `index.html`
- `comum/lnux.css`, `comum/lnux.js`, `comum/zip.js`, `comum/gif.js`
- `servidor/lnux_apps.py`
- `apps/som/` (`index.html`, `som.css`, `motor.js`, `som.js`)
- `apps/video/` (`index.html`, `video.css`, `motor.js`, `video.js`)
- `apps/efeitos/` (`index.html`, `efeitos.css`, `motor.js`, `efeitos.js`)
- `tests/testar_servidor.py`, `tests/testar_navegador.py`
- `tests/navegador/testar_som.js`, `testar_video.js`, `testar_efeitos.js`

**LNUX:**

| Arquivo | O que mudou |
|---|---|
| `lnux.py` | Seção nova "29. Apps Web"; item 🧩 Apps Web no menu principal; subcomando `apps`; busca; cabeçalho |
| `tests/testar_apps_web.py` | Novo |
| `README.md` | Linha na tabela do menu, seção "Apps Web", `lnux.py apps`, pastas novas e o teste novo |
| `docs/relatorio-modulos-3-e-4-etapa-1.md` | Este relatório |
