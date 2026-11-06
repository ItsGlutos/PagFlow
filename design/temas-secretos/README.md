# Temas secretos · PagFlow

Kit de **design** com quatro direções visuais extraídas de
`temas pagflow.figcraft` e traduzidas para a estrutura real do PagFlow.
Nada foi integrado ao aplicativo: as telas são HTML/CSS estáticos, sem
JavaScript e sem regra de negócio.

> **Status:** design only. O `main.py`, `ope.py`, `funcoes.py` e `envios.py`
> continuam intocados. A implementação fica para o agente que seguir o
> [`GUIA_PARA_AGENTE.md`](GUIA_PARA_AGENTE.md).

---

## O que tem aqui

```
design/temas-secretos/
├─ README.md                    ← este arquivo
├─ GUIA_PARA_AGENTE.md          ← briefing completo para a implementação futura
├─ assets/
│  └─ fonts/                    ← TTFs + licenças OFL usadas nas telas
├─ tokens/
│  ├─ README.md                 ← schema dos tokens
│  ├─ graduation.json           ← tokens compatíveis com a dataclass Theme
│  ├─ ozzy.json
│  ├─ lana.json
│  └─ acai.json
├─ screens/
│  ├─ index.html                ← galeria com as quatro direções
│  ├─ _shared/                  ← base.css, settings.css, fonts.css
│  ├─ graduation.css            ← variáveis e acabamentos do tema
│  ├─ ozzy.css
│  ├─ lana.css
│  ├─ acai.css
│  ├─ 01-graduation-principal.html
│  ├─ 01-graduation-configuracoes.html
│  ├─ 02-ozzy-principal.html
│  ├─ 02-ozzy-configuracoes.html
│  ├─ 03-lana-principal.html
│  ├─ 03-lana-configuracoes.html
│  ├─ 04-acai-principal.html
│  └─ 04-acai-configuracoes.html
├─ exports/                     ← 8 PNGs 1280×960 + index.png da galeria
└─ _build/                      ← geradores e rasterizador (ferramentas de design)
```

Abra **`screens/index.html`** no navegador para ver a galeria. Cada tela também
funciona sozinha: clique duas vezes no HTML, sem servidor e sem instalar nada.

---

## As quatro direções

| # | Tema | Código | Modo | Assinatura visual |
|---|---|---|---|---|
| 01 | **Graduation** | `graduation` | claro | Nuvens pastel, rosa choque, azul-céu, amarelo de verão; clima de capa de 2007. |
| 02 | **Ozzy** | `ozzy` | escuro | Preto de palco, vermelho sangue, amarelo high gain; tipografia de pôster e textura de scanline. |
| 03 | **Lana Del Rey** | `lana` | claro | Papel marfim, cereja vintage, rosa blush; serifas editoriais e disco de vinil ao fundo. |
| 04 | **Açaí** | `acai` | escuro | Roxo profundo, dourado, brilho premium; grade de pontos e anéis concêntricos. |

Os códigos são **nomes dos temas**, não senhas. A ativação ignora maiúsculas,
acentos e espaços: `Lana Del Rey`, `lana del rey`, `LANADELREY` e `lana` chegam
ao mesmo tema. O mesmo vale para `Açaí`/`acai`. O guia traz os aliases extras.

---

## O botão de configurações

As telas já preveem o botão no **canto superior direito**, imediatamente à
esquerda do alternador escuro/claro. Ele abre o diálogo **Configurações**, com
quatro abas:

- **Geral** — preferências básicas (placeholder de design).
- **Aparência** — temas principais e temas já desbloqueados (nunca lista os
  secretos antes da hora).
- **Inserir código** — a aba em destaque nas telas: campo de código, botão
  **Ativar tema**, feedback de sucesso/erro e o tema atual.
- **Sobre** — versão e créditos.

A aba **Inserir código** é a feature quase secreta. O fluxo desenhado é:

1. O usuário clica na engrenagem.
2. Vai até **Inserir código**.
3. Digita o nome do tema (ex.: `graduation`).
4. O tema é aplicado na hora, fica salvo em `QSettings` e volta na próxima
   abertura.
5. Um código inválido mostra feedback textual e vermelho, sem alterar nada.

As telas de configuração mostram os dois estados: **sucesso** em Graduation,
Lana e Açaí; **erro** em Ozzy. O guia documenta as mensagens exatas.

---

## Fidelidade à estrutura atual

As telas **não** copiam o layout do `.figcraft`. Elas mantêm, ponto a ponto, a
estrutura do PagFlow atual:

- Janela de cliente **1280×960** (4:3), com margens 20/12/20/10.
- Barra superior de **24 px** com o crédito à esquerda e os controles à direita.
- Cartão de marca de **52 px** (logo 30×30, título 16 px, subtítulo 9 px, badge).
- Seletor central de **30 px** com “Gerar Excel” e “Envio de e-mails”.
- Os **cinco passos na mesma ordem**, com chip de 20 px, título de 11 px,
  campos de **32 px** e intervalos de 14 px.
- Controle segmentado de **32 px**, select de **32 px**, botões de **36 px**.
- Divisor, ações na base (Limpar campos / Gerar Excel) e barra de status de
  **32 px**.
- Nenhuma sidebar, hero, nav lateral, barra de título Mac, footer extra ou
  reorganização de campos.

O que veio do `.figcraft` foi só a **linguagem visual**: paletas, tipografias,
texturas, gradientes, motivos e tom. O fundo pode ganhar nuvens, palco, papel
ou grade de pontos, mas o conteúdo continua exatamente onde está.

> O espaço vertical grande entre o passo 5 e o divisor é **intencional**: é o
> `addStretch(1)` do layout atual em 1280×960. Ele encolhe em janelas menores e
> não deve ser “corrigido” na implementação.

---

## Como as telas foram feitas

- HTML + CSS puro, **sem JavaScript**.
- Layout em pixels, com as mesmas alturas e margens do app.
- Fontes locais em `assets/fonts/` (OFL) para o render não depender da máquina.
- Ilustrações e motivos são **abstrações CSS** (nuvens, anel de vinil, grade,
  silhueta de morcego). Nenhuma capa ou arte de terceiros foi embutida.
- Os tokens em `tokens/*.json` são a ponte entre o design e o `Theme` do
  `main.py`.

---

## Regerar as telas

Pré-requisitos: Python 3 e Edge ou Chrome instalados.

```powershell
# 1. Reescrever os HTMLs a partir do template
python design/temas-secretos/_build/generate_screens.py

# 2. Rasterizar os PNGs 1280×960 + galeria
powershell -ExecutionPolicy Bypass -File design/temas-secretos/_build/render_screens.ps1

# 3. Regerar os tokens (se você editar as paletas no gerador)
python design/temas-secretos/_build/generate_tokens.py
```

Os comandos acima só mexem em `design/temas-secretos/`. Eles não alteram o app.

---

## Próximo passo

Leia o [`GUIA_PARA_AGENTE.md`](GUIA_PARA_AGENTE.md). Ele contém:

- as regras invioláveis de estrutura;
- o mapa tela → widget do `main.py`;
- a proposta de `ThemeArt`, registro de temas e persistência;
- o passo a passo do botão de configurações e da aba **Inserir código**;
- os códigos e aliases;
- os cuidados com fontes, QSS, gradientes e `QPainter`;
- o checklist de testes e a definição de pronto.

---

## Créditos e inspirações

As direções visuais são tributos declarados no arquivo original:
Graduation (Takashi Murakami / Kanye West, 2007), Ozzy Osbourne
(No More Tours), Lana Del Rey (Born to Die / Summertime Sadness) e Açaí
(identidade própria do PagFlow). O kit não distribui capas, logotipos ou
fotografias; usa apenas cor, tipografia, textura e formas abstratas.

Feito por Gustavo Pinheiro para o PagFlow.
