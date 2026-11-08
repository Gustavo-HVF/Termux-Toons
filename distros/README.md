# Perfis de sistema do LNUX

Cada arquivo `<id>.json` desta pasta descreve um sistema em que o LNUX roda: o gerenciador de pacotes, o
nome de cada pacote nele, as pastas da pessoa, como virar root, os serviços do sistema e os **recursos** que
ele tem (que decidem quais opções aparecem no menu).

**Para suportar uma distro nova, basta criar um arquivo**: o `lnux.py` não precisa mudar. Ponha o arquivo
aqui (para todo mundo, num pull request) ou em `~/.lnux/distros/` (só para você; um perfil com o mesmo `id`
de um daqui substitui o original).

| Arquivo | Sistema | Pacotes | Serviços |
|---|---|---|---|
| `termux.json` | Termux (Android) | `pkg` | tmux (sem serviços do sistema) |
| `debian.json` | Debian, Ubuntu e derivadas | `apt-get` | systemd |
| `arch.json` | Arch, Manjaro, EndeavourOS... | `pacman` | systemd |
| `fedora.json` | Fedora, RHEL, Rocky, Alma | `dnf` | systemd |
| `alpine.json` | Alpine, postmarketOS | `apk` | OpenRC |
| `opensuse.json` | openSUSE Tumbleweed/Leap, SLES | `zypper` | systemd |
| `outro.json` | qualquer outra (sem gerenciador conhecido) | — | — |

## Criar um perfil novo, passo a passo

1. Copie o perfil da distro mais parecida (ex.: `debian.json` → `void.json`).
2. Troque `id` (igual ao nome do arquivo), `nome` e `descricao`.
3. Em `detectar`, ponha o `ID` do `/etc/os-release` da distro (`grep ^ID /etc/os-release`) e o comando do
   gerenciador de pacotes.
4. Em `pacotes`, ajuste os comandos (`instalar`, `atualizar_indice`, `atualizar_sistema`, `limpar_cache`,
   `remover_orfaos`) e a `pasta_cache`.
5. Em `pacotes.nomes`, confira o nome de cada pacote na distro nova. Use `null` quando ela não tiver o pacote:
   o LNUX avisa e, quando se sabe, mostra como instalar à mão.
6. Em `servicos`, ajuste os comandos (systemd, OpenRC, runit...) e os nomes dos serviços.
7. Confira:

   ```bash
   python3 tests/verificar_perfis.py distros/void.json   # o que falta ou está errado no arquivo
   python3 tests/verificar_menus.py                      # o menu em cada sistema (nenhum submenu vazio)
   LNUX_SISTEMA=void python3 lnux.py sistema             # o que o LNUX entende do perfil
   ```

Exemplo de um perfil do Void Linux (o resto igual ao `debian.json`):

```json
{
  "id": "void",
  "nome": "Void Linux",
  "detectar": {"os_release": ["void"], "comandos": ["xbps-install"]},
  "pacotes": {
    "gerenciador": "xbps",
    "instalar": ["xbps-install", "-y"],
    "atualizar_indice": ["xbps-install", "-S"],
    "atualizar_sistema": ["xbps-install", "-Su", "-y"],
    "limpar_cache": ["xbps-remove", "-O"],
    "remover_orfaos": ["xbps-remove", "-o", "-y"]
  },
  "servicos": {
    "comandos": {"iniciar": ["sv", "up", "{servico}"], "parar": ["sv", "down", "{servico}"],
                 "ligar_no_boot": ["ln", "-sf", "/etc/sv/{servico}", "/var/service/"],
                 "status": ["sv", "status", "{servico}"]},
    "nomes": {"ssh": "sshd", "cron": "cronie", "mariadb": "mysqld", "postgresql": "postgresql"}
  }
}
```

## Os campos

| Campo | O que é |
|---|---|
| `esquema` | sempre `"lnux-perfil/1"` (o formato deste arquivo) |
| `id` | identificador curto, igual ao nome do arquivo; é o que fica salvo em `~/.lnux/config.json` |
| `nome`, `descricao` | o que aparece na escolha do sistema |
| `familia` | `"termux"` ou `"linux"`. Fora do Termux, os comandos `termux-*` usados pelo programa viram o equivalente do Linux |
| `detectar` | como sugerir este perfil: `termux: true`, `os_release` (lista de `ID`/`ID_LIKE` do `/etc/os-release`) e `comandos` (se um deles existir) |
| `recursos` | o que o sistema tem; veja a tabela abaixo |
| `elevar` | como virar root, em ordem de preferência: `[["sudo"], ["doas"]]`. Vazio no Termux |
| `pacotes.gerenciador` | nome mostrado ao usuário (`apt`, `pacman`...) |
| `pacotes.precisa_root` | `true` coloca o `sudo`/`doas` de `elevar` na frente dos comandos de pacote |
| `pacotes.instalar` ... | comandos do gerenciador, como listas (`["apt-get", "install", "-y"]`); `null` quando não há. `["sh", "-c", "..."]` serve para comandos com pipe |
| `pacotes.pasta_cache` | onde ficam os pacotes baixados (para mostrar quanto a limpeza libera) |
| `pacotes.essenciais` | o que "📦 Instalar dependências → Essenciais" instala (nomes canônicos) |
| `pacotes.nomes` | nome canônico (o do Termux) → nome na distro. Vários pacotes separados por espaço; `null` = não existe |
| `pacotes.modulos_python` | módulo do pip → pacote da distro (`"rich": "python3-rich"`). O que não estiver aqui vai pelo pip, só para o usuário |
| `caminhos` | pastas: `downloads`, `musicas`, `videos`, `imagens`, `dcim`, `documentos`, `capturas_de_tela`, `compartilhado`, `temporarios`, `prefixo`. `xdg:DOWNLOAD\|~/Downloads` usa a pasta XDG e, se ela não existir, a próxima opção |
| `servicos.comandos` | `iniciar`, `parar`, `ligar_no_boot` e `status`, com `{servico}` no lugar do nome |
| `servicos.nomes` | nome de cada serviço na distro: `ssh`, `cron`, `mariadb`, `postgresql` |
| `servicos.preparar` | passos para rodar uma vez antes de ligar o serviço (ex.: o `initdb` do PostgreSQL no Arch), com `se_faltar`: o arquivo que mostra que já foi feito |
| `dicas.repositorios_extras` | o que mostrar em "Repositórios extras da distro" (RPM Fusion, AUR, Packman...) |

## Os recursos

| Recurso | O que libera no menu |
|---|---|
| `termux` | o que é do app Termux: `pkg`, Termux:Widget, mensagem de boas-vindas, repositórios x11/root/tur |
| `android` | o aparelho é o próprio Android: telas de configuração, root com `su`, resolução da tela, transmitir a tela, modem |
| `termux_api` | sensores, SMS, GPS, lanterna, vibração (app Termux:API) |
| `infravermelho` | controle da TV e de outros aparelhos por IR, TV-B-Gone |
| `termux_x11` | desktop das distros no app Termux:X11 |
| `proot_distro` | 🐧 Linux de verdade (proot-distro) |
| `tema_termux` | tema de cores e fonte do app Termux |
| `adb` | controlar um Android pelo adb (o próprio celular, ou um ligado por USB/Wi-Fi) |
| `desktop` | área de trabalho Linux: abrir links/arquivos, notificações, área de transferência, VLC/mpv, scrcpy |
| `servicos_sistema` | SSH, cron, MariaDB e PostgreSQL como serviços do sistema |
| `distrobox` | 🐧 Outras distros em contêineres (Distrobox + Podman) |

`bateria` não vai no arquivo: o LNUX descobre na hora (`/sys/class/power_supply/BAT*` no Linux). No código, uma
opção que precisa de um recurso se marca com `so_em("recurso", função)`; `"!termux"` quer dizer "não ter" e
`"pacote:jellyfin-server"` quer dizer "a distro tem esse pacote".
