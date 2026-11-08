# Módulo 5: 🕵️ Mensagens secretas

Categoria nova no menu principal (entre 🧰 Utilitários e 📲 Celular e sistema), com **23 técnicas** em 6 grupos.
Cada técnica tem **ℹ️ Como funciona** (explicação curta), **codificar** e **decodificar**.
O resultado aparece na tela com três opções: copiar, salvar num `.txt` ou mostrar como QR code. Os arquivos ficam em
`Download/LNUX/Mensagens secretas`.

Funciona igual em todos os sistemas (Termux e distros): não depende de recurso do Android.

## O que tem

| Grupo | Técnica | Como funciona (resumo) |
|---|---|---|
| ℹ️ | Esconder, cifrar ou codificar? | Explica a diferença e como combinar (cifrar com senha e depois esconder) |
| 🖼️ Esteganografia | Texto dentro de uma foto | O último bit de cada cor (R, G, B) dos pixels; sai em PNG |
| | Texto invisível dentro de outro texto | Bits viram dois caracteres de largura zero, depois da 1ª letra de um texto comum |
| | Texto dentro de um áudio | O último bit de cada amostra de um WAV de 16 bits; MP3, OGG e outros são convertidos antes pelo ffmpeg |
| | Arquivo dentro de uma foto | O arquivo vai grudado no fim da foto, que continua abrindo normal |
| 🔒 Criptografia moderna | AES-256 com senha (texto) | AES-256-GCM (também acusa alteração), chave pelo scrypt; formato `LNUX-AES1:...` |
| | AES-256 com senha (arquivo) | O mesmo, para qualquer arquivo → `.lnuxcripto` |
| | Compatível com o OpenSSL | AES-256-CBC + PBKDF2 (600 mil rodadas): abre com o `openssl` em qualquer computador |
| | Bloco de uso único (Vernam) | XOR com chave aleatória do tamanho da mensagem; a única cifra comprovadamente inquebrável |
| 📜 Cifras clássicas | César | Desloca as letras; extra **🔎 Descobrir sem a chave** (testa os 25 deslocamentos e escolhe pela frequência das letras do português) |
| | ROT13, ROT47, Atbash | Aplicar de novo desfaz |
| | Vigenère | César diferente por letra, dado pela palavra-chave |
| | Substituição com palavra-chave | Alfabeto que começa pela palavra-chave |
| | Cerca de trilhos | Transposição em zigue-zague |
| | Quadrado de Políbio, Bacon, A1Z26 | Letras viram números, A/B ou posições |
| 🔢 Sistemas numéricos | Converter um número | Decimal → binário, octal, hexa (e qualquer base de 2 a 36); e de volta |
| | Texto ↔ binário, octal, decimal, hexadecimal | Os bytes UTF-8 do texto na base; aceita os números separados ou tudo junto |
| 🔣 Alfabetos próprios | Criar, codificar, decodificar, ver, mandar, receber, apagar | Um símbolo por letra e número: escolhidos à mão ou gerados de emojis, runas, grego, símbolos ou setas (embaralhados) |
| 📡 Códigos | Morse | Com o extra **🔊 Gerar o som** (bipes em WAV) |
| | Braille | Com os acentos do português, números (⠼) e maiúsculas (⠨) |
| | Base64, Base32 | Codificações (não protegem); o Base64 aceita também a versão de links |

### Outras formas que acrescentei

Além do que foi pedido:

- **Combinar esconder com cifrar:** todas as opções de esconder aceitam uma senha opcional que cifra a mensagem
  com AES-256 antes.
- **Arquivo dentro de uma foto:** um anexo de qualquer tamanho, que viaja dentro de uma foto normal.
- **Áudio:** esconder a mensagem num WAV.
- **Formato do OpenSSL:** para trocar mensagens cifradas com quem não tem o LNUX.
- **Bloco de uso único (Vernam).**
- **Quebrar o César** sem saber a chave.
- **Som do Morse** em WAV.
- **Braille** do português.
- **Mandar e receber alfabetos** (`lnux-alfabeto:...`), para que a outra pessoa consiga ler.

### Cuidados que o programa mostra

- **Foto, áudio ou foto com anexo:** mande como **arquivo**. Enviados como foto ou áudio, eles são recomprimidos e
  a mensagem some.
- **Texto invisível:** alguns apps apagam os caracteres de largura zero. Teste antes.
- **Cifras clássicas:** só mudam de a a z. O programa oferece tirar os acentos antes (ç→c, ã→a).
- **Alfabetos próprios:** as maiúsculas voltam minúsculas e os acentos se perdem.
- **Senhas curtas:** com menos de 8 caracteres, aparece um aviso. Ao cifrar, a senha é pedida duas vezes.
- **Alfabetos ambíguos:** o programa recusa símbolo repetido, um símbolo que é o começo de outro e uma letra que
  não é trocada sendo usada como símbolo.

## Como foi verificado

- **`tests/testar_mensagens_secretas.py` (novo): 24 testes, todos passando.**
  - Ida e volta de cada técnica, com acentos, emoji e caracteres chineses.
  - Exemplos conhecidos da literatura:
    - Vigenère `ATTACKATDAWN` com a chave `LEMON` → `LXFOPVEFRNHR`;
    - cerca de trilhos `WEAREDISCOVERED...`;
    - ROT13 de `Hello`.
  - Casos de erro:
    - senha errada e mensagem alterada no AES;
    - foto sem mensagem e mensagem que não cabe na foto;
    - chave errada no Vernam;
    - alfabeto ambíguo e Base64 inválido.
  - Compatibilidade nos dois sentidos com o comando `openssl` de verdade.
  - A foto e o áudio mudam no máximo 1 em cada valor.
  - A foto com anexo continua abrindo no Pillow.
- **Pelo menu de verdade**, no modo de números:
  - César com acentos;
  - criar um alfabeto de emojis e codificar com ele;
  - binário → decimal;
  - esconder e revelar numa foto da pasta Downloads.
- **`tests/verificar_menus.py`:** passou a entender `ferramenta(...)`. Agora vê 94 menus e 750 opções, sem
  duplicatas nem submenus vazios em nenhum sistema.
- **`tests/testar_menus_por_sistema.py`:** os 7 perfis abrem todos os menus, inclusive os novos.

### Um erro que os testes pegaram durante o trabalho

Duas funções novas, `ler_numero` e `_bits`, tinham o mesmo nome de funções que já existiam: a do conversor de
moedas e do controle de gastos, e a do infravermelho da TV. Por vir depois, a nova substituiria a antiga e quebraria
essas funções.

- As novas foram renomeadas para `ler_numero_na_base` e `_bits_dos_bytes`.
- O `tests/verificar_menus.py` ganhou a checagem **NOME REPETIDO**, que acusa isso daqui para a frente.

## O que não foi feito

- **Recuperar mensagens de fotos recomprimidas** (enviadas como foto pelo WhatsApp, por exemplo): não é possível com
  a técnica de bits menos significativos, que é a que mantém a foto idêntica a olho nu. Existem técnicas mais
  resistentes, no domínio da frequência do JPEG, mas elas guardam muito menos e alteram a imagem. Ficaram de fora.
- **Quebrar o Vigenère e as substituições automaticamente:** só o César tem "descobrir sem a chave".

## Arquivos

| Arquivo | O que mudou |
|---|---|
| `lnux.py` | Seção nova "27. Mensagens secretas": funções de cada técnica e menus `menu_mensagens_secretas`, `menu_esteganografia`, `menu_criptografia`, `menu_cifras_classicas`, `menu_sistemas_numericos`, `menu_alfabetos`, `menu_codigos`, mais o ajudante `ferramenta()`. Entrada no menu principal e 7 entradas na 🔍 Busca |
| `distros/*.json` (6 perfis Linux) | Tradução do pacote `openssl-tool` (o comando openssl do Termux) |
| `tests/testar_mensagens_secretas.py` | Novo |
| `tests/verificar_menus.py` | Entende `ferramenta(...)` e acusa funções com nome repetido |
| `README.md` | Linha 11 da tabela do menu, seção "Mensagens secretas", lista de testes e o `alfabetos.json` |
| `docs/relatorio-modulo-5.md` | Novo: este relatório |
