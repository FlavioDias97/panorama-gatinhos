# Gatinhos 🐈‍⬛🐈

Um plugin para o [Panorama](https://github.com/Frenvius/panorama-term) que usa todos os
pontos de extensão de plugins declarativos de uma vez. Serve para deixar o Panorama com
cara de gato e como modelo para quem quer fazer o próprio plugin.

*English: a Panorama plugin with two cat themes, two fonts, a made-up language with its
own grammar and an extension mapping. Install it by cloning this repository into
Panorama's plugins folder as `gatinhos` (commands below).*

## O que vem

| Tipo | O quê |
| --- | --- |
| Tema escuro | **Gatinho Preto Dark**: pelo quase preto, olhos âmbar e nariz rosa |
| Tema claro | **Gatinho Laranja Light**: creme com laranja de gato rajado |
| Fonte (código e terminal) | **Comic Mono**, monoespaçada |
| Fonte (interface) | **Fredoka**, redonda e fofa |
| Linguagem nova | **MiauScript** (`.miau`), com gramática própria em `syntaxes/` |
| Extensão associada | `.conf` colorido como **INI** (pense no `kitty.conf`) |

Os temas mudam as cores do app, do código e as 16 cores ANSI do terminal.

## Instalar

O plugin é esta pasta inteira, e ela precisa se chamar `gatinhos` (igual ao `id` do
`plugin.json`). O jeito mais simples é clonar direto na pasta de plugins do Panorama.

**Linux**

```sh
git clone https://github.com/FlavioDias97/panorama-gatinhos ~/.config/panorama/plugins/gatinhos
```

**macOS**

```sh
git clone https://github.com/FlavioDias97/panorama-gatinhos "$HOME/Library/Application Support/panorama/plugins/gatinhos"
```

**Windows** (PowerShell)

```powershell
git clone https://github.com/FlavioDias97/panorama-gatinhos "$env:APPDATA\panorama\plugins\gatinhos"
```

Sem git: baixe o ZIP (botão **Code → Download ZIP**), extraia na pasta de plugins e
renomeie a pasta extraída de `panorama-gatinhos-main` para `gatinhos`.

O plugin aparece na hora em **Settings → Plugins**, sem reiniciar. Se você roda o
Panorama a partir do código (`bun run dev`), troque `panorama` por `panorama-dev` no
caminho.

## Usar

Em **Settings → Appearance**:

- **Dark theme** → *Gatinho Preto Dark*, **Light theme** → *Gatinho Laranja Light*
  (em *System*, o Panorama alterna entre os dois junto com o sistema);
- **Interface font** → *Fredoka*;
- **Code font** e **Terminal font** → *Comic Mono*.

Abra `exemplos/gato.miau` e `exemplos/kitty.conf` no editor do Panorama para ver as
linguagens.

## Atualizar e remover

```sh
git -C ~/.config/panorama/plugins/gatinhos pull   # atualizar
rm -rf ~/.config/panorama/plugins/gatinhos        # remover
```

Para só desligar sem remover, use o interruptor em **Settings → Plugins**; o Panorama
volta para o próprio tema e as próprias fontes.

## Fazer o seu

Tudo está no `plugin.json`: copie este repositório, troque o `id` (e o nome da pasta),
e mexa no que quiser. A referência completa de cada campo está no guia de plugins do
Panorama: [português](https://github.com/FlavioDias97/panorama-term/blob/plugins/docs/PLUGINS.pt-BR.md)
· [English](https://github.com/FlavioDias97/panorama-term/blob/plugins/docs/PLUGINS.md).

```
gatinhos/
├── plugin.json                         manifesto: temas, fontes e linguagens
├── fonts/                              Comic Mono e Fredoka, com as licenças
├── syntaxes/miauscript.tmLanguage.json gramática TextMate do MiauScript
└── exemplos/                           gato.miau e kitty.conf
```

## Licença

MIT. As fontes mantêm as próprias licenças: Comic Mono (MIT,
`fonts/LICENSE-ComicMono.txt`) e Fredoka (SIL Open Font License 1.1,
`fonts/LICENSE-Fredoka.txt`).
