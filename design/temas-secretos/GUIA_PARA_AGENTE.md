# Guia para o agente · Temas secretos do PagFlow

> **Leia isto antes de tocar em qualquer arquivo do aplicativo.**
> Este documento é um briefing de implementação. O kit em `design/temas-secretos/`
> é a fonte de verdade visual; o `main.py` continua sendo a fonte de verdade
> estrutural. O objetivo é aplicar a pele dos quatro temas **sem** redesenhar o
> PagFlow.

---

## 0. Prompt curto (copie para o agente)

```text
Você vai implementar os quatro temas secretos do design/temas-secretos no PagFlow
(PyQt6, main.py). Leia GUIA_PARA_AGENTE.md inteiro, abra as telas HTML e os tokens
JSON, e preserve rigorosamente a estrutura atual: janela 1280x960 (4:3), barra
superior de 24 px, cartão de marca de 52 px, seletor de 30 px, os cinco passos na
mesma ordem, campos de 32 px, botões de 36 px e status de 32 px. Não crie sidebar,
hero, nav, footer, barra de título Mac nem reorganize campos.

A entrega é: (1) quatro temas registrados e ativáveis por código; (2) botão de
configurações no canto superior direito, à esquerda do alternador; (3) diálogo
Configurações com a aba "Inserir código"; (4) ativação por nome do tema, com
feedback de sucesso/erro, persistência em QSettings e lista de temas desbloqueados;
(5) aplicação dos tokens aos widgets existentes, incluindo fontes, fundos, logo,
ViewSwitch, SegmentedControl, PillButton e StatusBar.

Não altere ope.py, funcoes.py, envios.py nem a lógica de negócio. Não use imagens
de capas/artistas: os motivos são desenhados com QPainter/CSS. Se uma fonte não
estiver disponível, caia para Segoe UI sem quebrar o layout. Teste em 1280x960 e
no tamanho reajustado pela tela.
```

---

## 1. Regras invioláveis

1. **Estrutura primeiro.** O layout do app atual vence qualquer sugestão do
   `.figcraft`. Nada de sidebar, hero, nav lateral, barra de título Mac, footer
   extra, cards por passo ou campos em outra ordem.
2. **Geometria intacta.** Janela 1280×960 (4:3), margens 20/12/20/10, topbar 24,
   header 52, switch 30, chips 20, campos 32, botões 36, status 32.
3. **Textos e ordem intactos.** Os cinco passos continuam:
   `Nome do arquivo de saída`, `Pasta com os arquivos de entrada`,
   `Separação das abas`, `Personalização`, `Destino do arquivo final`.
   As opções do segmentado continuam `Marca`, `LNeg`, `Fornecedor`,
   `Não Separar` — a lógica usa `SegmentedControl.value()`, que compara o texto.
4. **Nada de regra de negócio.** `ope.py`, `funcoes.py`, `envios.py` e a thread
   de processamento não são tocados. Tema é só apresentação.
5. **Tokens, não cores soltas.** Toda cor/fonte nova entra via `Theme`/`ThemeArt`.
   Evite `QColor("#...")` espalhado em widgets; use `C(t.…)`.
6. **Temas secretos não aparecem antes de serem desbloqueados.** A aba
   “Aparência” só lista `dark`, `light` e os temas já desbloqueados. Nada de
   mostrar os nomes numa lista pública.
7. **Todos os temas preservam o mesmo esqueleto.** A diferença é cor, tipografia,
   textura, gradiente e motivo. Não mova um pixel de layout para “ficar mais
   bonito”.
8. **Acessibilidade.** Feedback de código tem texto + cor (não só cor), foco
   visível, contraste adequado e `Enter` funciona no campo.
9. **Sem assets de terceiros.** Nada de capas, fotos ou logos dos artistas. Os
   motivos (nuvem, morcego, cereja, açaí) são abstratos, desenhados com
   `QPainter`.
10. **Fallback de fonte.** Se a família não estiver instalada/carregada, use
    `Segoe UI` e mantenha o layout. O app não pode quebrar por causa de uma TTF.

---

## 2. O que ler, nesta ordem

1. `design/temas-secretos/README.md` — visão geral e códigos.
2. `design/temas-secretos/screens/index.html` — galeria das quatro direções.
3. As oito telas `screens/**/*.html` — a referência visual exata.
4. `design/temas-secretos/tokens/*.json` — os valores prontos para o `Theme`.
5. `design/temas-secretos/screens/*.css` — gradientes, texturas e detalhes.
6. `main.py` — a estrutura que **não** será redesenhada.

> O arquivo `temas pagflow.figcraft` na raiz é a inspiração original. **Não copie
> o layout dele.** Ele tem barra Mac, sidebar, hero e ordens diferentes; foi
> justamente isso que este kit corrigiu.

---

## 3. Mapa tela → código atual

| Tela / elemento do design | Onde vive hoje | O que fazer |
|---|---|---|
| `.topbar` + crédito | `App._build`, `top` (linha ~2731) | Adicionar a engrenagem antes do toggle; manter altura 24. |
| `.theme-toggle` | `ThemeToggle` (linha ~855) | Passar a refletir `art.is_light`; manter 58×26. |
| `.brand-card` + `.logo` + título | `App.header`, `LogoMark`, `QLabel#BrandTitle` | Aplicar `art.card_from/to`, motivo do logo e suffix do título. |
| `.brand-sub` | `QLabel#BrandSub` | Só cor/fonte; texto intacto. |
| `.badge` (`XLS → XLSX`) | `QLabel#Badge` | Cores/tokens; texto intacto. |
| `.view-switch` | `ViewSwitch` (linha ~1520) | Aplicar gradiente/cores de `view_active_*`. |
| `.form` | `App._build_gerar_page` (linha ~2820) | Nada de estrutura; só tokens via QSS. |
| `.step-row` / `.chip` / `.step-title` | `App._section` (linha ~2896) | Fonte/tamanho/cor; chip com gradiente. |
| `.field` | `QLineEdit#Field` em `build_qss` | Já usa tokens; revisar fonte e placeholder. |
| `.icon-field` | `IconButton` (linha ~785) | Cores/tokens; manter 36×32. |
| `.segmented` | `SegmentedControl` (linha ~968) | Aplicar `seg_active_*`; manter 32. |
| `.select` | `SelectField` (linha ~1235) | Cores/fonte; manter 32. |
| `.actions` | `_build_gerar_page`, `row_actions` | Manter 130/152×36; só pintura. |
| `.statusbar` | `StatusBar` (linha ~1342) | Fonte/tamanho/caixa alta por tema. |
| `.dialog` | **novo** `SettingsDialog` | Criar; 760×600, abas e aba “Inserir código”. |
| `.code-card` / `.code-aside` | **novo** dentro do diálogo | Layout de duas colunas; tokens. |
| `.feedback` | **novo** labels `FeedbackOk/Err` | Texto + cor; sucesso/erro. |

As linhas são aproximadas; use busca por nome de classe/função.

---

## 4. Arquitetura sugerida

### 4.1 Onde colocar os temas

O `main.py` já tem 129 KB. Para não inflar ainda mais, prefira um módulo novo:

```
temas_extra.py   ← dados puros (dicts) dos quatro temas
main.py          ← Theme, ThemeArt, ThemeToggle etc.
```

`temas_extra.py` **não importa `main`** (evita import circular). Ele só exporta
uma lista de dicts no formato dos JSONs de `tokens/`.

No topo do `main.py`:

```python
from temas_extra import EXTRA_THEMES as _EXTRA_THEME_DATA
```

Depois de definir `Theme`/`ThemeArt` e antes de `THEMES = {"dark": DARK, ...}`:

```python
EXTRA_THEMES = {
    item["key"]: Theme(**item["theme"], art=ThemeArt(**item["art"]))
    for item in _EXTRA_THEME_DATA
}
THEMES = {
    "dark": DARK,
    "light": LIGHT,
    **EXTRA_THEMES,
}
```

> Alternativa aceitável: colar as definições direto no `main.py`, depois de
> `LIGHT`. O importante é não alterar `DARK`/`LIGHT` nem o comportamento atual.
> **Não** leia os JSONs em tempo de execução no app empacotado; copie os valores
> para `temas_extra.py`.

### 4.2 `ThemeArt`: o que não cabe no `Theme`

`Theme` já cobre as cores. O que falta é “película”: fontes, motivos, gradientes
de estado, caixa alta, pattern de fundo. Adicione uma dataclass separada e um
campo com default no `Theme` — assim `DARK` e `LIGHT` continuam funcionando sem
serem reescritos.

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ThemeArt:
    is_light: bool = False
    secret_code: str = ""
    aliases: tuple[str, ...] = ()

    display_font: str = "Segoe UI"
    ui_font: str = "Segoe UI"
    mono_font: str = "Consolas"
    section_font: str = ""
    button_font: str = ""
    status_font: str = ""
    status_size: int = 11
    status_transform: str = "none"      # "none" | "uppercase"

    brand_label: str = "PagFlow"
    brand_suffix: str = ""
    brand_suffix_style: str = "normal"  # "normal" | "italic"
    brand_suffix_color: str = ""
    brand_transform: str = "none"
    brand_tracking: float = 0.0

    section_transform: str = "none"
    section_tracking: float = 0.0
    section_size: int = 11

    button_transform: str = "none"
    button_tracking: float = 0.0
    button_size: int = 12

    logo_motif: str = "sheet"           # sheet | flower | bolt | cherry | berry
    logo_from: str = ""
    logo_to: str = ""
    logo_fg: str = ""
    logo_border: str = ""

    pattern: str = "plain"              # plain | stars | clouds | grain | paper | dotgrid
    primary_text: str = ""              # cai para on_accent

    card_from: str = ""
    card_to: str = ""

    chip_from: str = ""
    chip_to: str = ""
    chip_fg: str = ""

    badge_bg: str = ""
    badge_fg: str = ""
    badge_border: str = ""

    status_bg: str = ""
    status_border: str = ""
    status_fg: str = ""
    status_dot: str = ""

    view_active_from: str = ""
    view_active_to: str = ""
    view_active_fg: str = ""
    view_active_border: str = ""

    seg_active_from: str = ""
    seg_active_to: str = ""
    seg_active_fg: str = ""
    seg_active_border: str = ""

    description: str = ""
```

No `Theme`:

```python
@dataclass(frozen=True)
class Theme:
    # … campos atuais …
    stars: bool
    shadow_alpha: int
    art: ThemeArt = field(default_factory=ThemeArt)
```

Em `DARK`/`LIGHT`, adicione apenas o pattern:

```python
DARK  = Theme(..., art=ThemeArt(pattern="stars"))
LIGHT = Theme(..., art=ThemeArt(pattern="plain"))
```

Os demais campos ficam no default e o comportamento atual não muda.

### 4.3 Registro e persistência

```python
CORE_THEME_KEYS = ("dark", "light")
UNLOCKED_SETTING = "temas_desbloqueados"


def unlocked_keys(settings: QSettings) -> set[str]:
    raw = str(settings.value(UNLOCKED_SETTING, "") or "")
    return {key for key in raw.split(",") if key in EXTRA_THEMES}


def save_unlocked(settings: QSettings, keys: set[str]) -> None:
    settings.setValue(UNLOCKED_SETTING, ",".join(sorted(keys)))


def available_themes(settings: QSettings) -> dict[str, Theme]:
    result = {key: THEMES[key] for key in CORE_THEME_KEYS}
    result.update({key: THEMES[key] for key in unlocked_keys(settings)})
    return result
```

No `App.__init__`:

```python
self._settings = QSettings("PagFlow", "PagFlow")
unlocked = unlocked_keys(self._settings)
saved = str(self._settings.value("tema", "dark"))
if saved not in THEMES or (saved in EXTRA_THEMES and saved not in unlocked):
    saved = "dark"
self._theme_key = saved
self.theme = THEMES[self._theme_key]
```

Em `_set_theme`, bloqueie tema não desbloqueado:

```python
def _set_theme(self, key: str) -> None:
    if key not in THEMES or key == self._theme_key:
        return
    if key in EXTRA_THEMES and key not in unlocked_keys(self._settings):
        return
    # … resto igual …
```

**Comportamento do toggle:** o alternador do topo continua sendo o switch
escuro↔claro. Quando um tema secreto está ativo:

- a posição do knob reflete `theme.art.is_light`;
- clicar no lado oposto troca para o `light` ou `dark` principal;
- clicar no mesmo lado não faz nada;
- o tema secreto não entra no ciclo do toggle. Ele é escolhido pelos códigos
  ou pela aba “Aparência” (temas já desbloqueados).

Em `ThemeToggle.set_theme`:

```python
target = 1.0 if theme.art.is_light else 0.0
```

Em `ThemeToggle.mouseReleaseEvent`, compare com o **modo atual**, não com a key
do tema (a key de um tema secreto é `graduation`, `ozzy` etc.):

```python
current_mode = "light" if self._theme.art.is_light else "dark"
if inside and target != current_mode:
    self.theme_requested.emit(target)
```

Assim, clicar no mesmo lado de um tema secreto não faz nada; clicar no lado
oposto cai para `light`/`dark` principal. O `_set_theme` já sabe aplicar os
temas principais.

---

## 5. Fontes

### 5.1 Carregar

Copie `assets/fonts/*.ttf` para o lado do executável (ex.: `assets/fonts/` no
projeto, incluindo no `.spec` do PyInstaller). Carregue antes de construir a UI:

```python
from pathlib import Path
from PyQt6.QtGui import QFontDatabase


def load_theme_fonts() -> None:
    base = Path(__file__).resolve().parent / "assets" / "fonts"
    if not base.is_dir():
        return
    for path in sorted(base.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(path))
```

Chame em `main()`, antes de `App()`. Não é necessário verificar o retorno; se
falhar, o Qt cai para a fonte padrão.

### 5.2 Aplicar no QSS

Troque o `font-family: "Segoe UI";` fixo de `build_qss` por:

```python
QWidget {{
    font-family: "{t.art.ui_font}";
    color: {t.text};
}}
```

E nos seletores específicos:

- `QLabel#BrandTitle` → `t.art.display_font`
- `QLabel#SectionTitle` → `t.art.section_font or t.art.ui_font`, com
  `font-size: {t.art.section_size}px`
- `QLabel#Meta`, `QLabel#Badge`, `QLabel#Chip` → `t.art.ui_font`
- `QLineEdit#Field`, `QTextEdit#Body`, `QTableWidget` → `t.art.ui_font`
- `QMessageBox`, `QToolTip` → `t.art.ui_font`

### 5.3 Fontes desenhadas à mão (`F()`)

Hoje `F()` usa `"Segoe UI"` como default. Para não passar `family=` em cada
`paintEvent`, use um global controlado por `_apply_theme`:

```python
_UI_FONT = "Segoe UI"


def F(px, weight=QFont.Weight.Normal, tracking=0.0, family=None):
    family = family or _UI_FONT
    ...
```

Em `_apply_theme`:

```python
global _UI_FONT
_UI_FONT = t.art.ui_font or "Segoe UI"
```

Onde o design pede a fonte de display/botão/status, passe explicitamente:

```python
font = F(t.art.button_size, QFont.Weight.DemiBold,
         family=t.art.button_font or t.art.ui_font)
```

### 5.4 Caixa alta e tracking sem quebrar a lógica

Qt QSS **não** tem `text-transform` nem `letter-spacing` confiável. Use
`QFont.setCapitalization`/`setLetterSpacing` (ou o helper `F(..., tracking=...)`)
e desenhe `text.upper()` na pintura. **Nunca** altere a string real das opções do
`SegmentedControl`, porque `value()` retorna o texto e o `set_value()` compara
por igualdade.

```python
font = F(11, QFont.Weight.DemiBold, tracking=1.2)
font.setCapitalization(QFont.Capitalization.AllUppercase)
label.setFont(font)
```

```python
font = F(t.art.section_size, QFont.Weight.DemiBold,
         family=t.art.section_font or t.art.ui_font)
if t.art.section_transform == "uppercase":
    font.setCapitalization(QFont.Capitalization.AllUppercase)
label.setFont(font)
```

Para `PillButton`, desenhe `self.text().upper()` quando
`t.art.button_transform == "uppercase"`. Para `StatusBar`, idem com
`t.art.status_transform`.

### 5.5 Fallback

Se `QFontDatabase.families()` não contiver a família, use `Segoe UI`:

```python
def resolve_family(name: str) -> str:
    return name if name in QFontDatabase.families() else "Segoe UI"
```

O layout não pode depender da presença da fonte.

---

## 6. Botão de configurações

### 6.1 Engrenagem no topo

A engrenagem fica **à esquerda do toggle**, no canto superior direito, dentro da
topbar de 24 px. O `IconButton` atual é 36×32, alto demais. Duas opções:

**A. Novo widget compacto (recomendado):**

```python
class TopIconButton(IconButton):
    def __init__(self, glyph, tooltip, parent=None):
        super().__init__(glyph, tooltip, parent)
        self.setFixedSize(24, 24)
```

Ajuste `paintEvent` para raio 7 e glifo em `QRectF(6.5, 6.5, 11, 11)`.

**B. Parâmetro `compact` no `IconButton`:**

```python
def __init__(self, glyph, tooltip, parent=None, compact=False):
    ...
    self.compact = compact
    self.setFixedSize(24, 24) if compact else self.setFixedSize(36, 32)
```

Adicione `draw_gear` em `main.py` (helper de QPainter):

```python
def draw_gear(p: QPainter, rect: QRectF, color: QColor, width: float = 1.3) -> None:
    p.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.setBrush(Qt.BrushStyle.NoBrush)
    c = rect.center()
    r = min(rect.width(), rect.height()) * 0.30
    p.drawEllipse(c, r, r)
    for i in range(8):
        a = math.radians(i * 45)
        p.drawLine(
            QPointF(c.x() + math.cos(a) * (r + 1.2), c.y() + math.sin(a) * (r + 1.2)),
            QPointF(c.x() + math.cos(a) * (r + 3.0), c.y() + math.sin(a) * (r + 3.0)),
        )
    p.setBrush(color)
    p.drawEllipse(c, 1.2, 1.2)
```

No `_build`:

```python
self.btn_config = IconButton("gear", "Configurações", top, compact=True)
self.btn_config.clicked.connect(self._open_settings)
top_layout.addWidget(self.btn_config, 0, Qt.AlignmentFlag.AlignVCenter)
top_layout.addSpacing(8)
top_layout.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignVCenter)
```

Inclua `self.btn_config` em `self._themed` e no `set_theme`.

### 6.2 Abrir o diálogo

```python
def _open_settings(self) -> None:
    dialog = SettingsDialog(self.theme, self._settings, self)
    dialog.theme_unlocked.connect(self._on_theme_unlocked)
    dialog.theme_selected.connect(self._set_theme)
    dialog.exec()

def _on_theme_unlocked(self, key: str) -> None:
    unlocked = unlocked_keys(self._settings) | {key}
    save_unlocked(self._settings, unlocked)
    self._set_theme(key)
```

### 6.3 Estrutura do `SettingsDialog`

- `QDialog`, modal, `setWindowTitle("Configurações")`, 760×600, mínimo 720×560.
- `QVBoxLayout` com margens 22/18/22/16 e espaçamento 8.
- Cabeçalho: eyebrow `PAGFLOW · AJUSTES`, título `Configurações`, subtítulo
  `Ajustes do aplicativo`, botão fechar 30×30.
- Abas: `Geral`, `Aparência`, `Inserir código`, `Sobre`, em `QPushButton`s
  checkable com `QButtonGroup` (não use `QTabWidget`; o visual fica fora do
  vocabulário do app). QSS `QPushButton#SettingsTab`.
- Adicione `QStackedWidget` ao import de `PyQt6.QtWidgets` (ele ainda não está
  no `main.py`).
- `QStackedWidget` com quatro páginas. A página “Inserir código” é a única
  obrigatória; “Geral” e “Sobre” podem ser placeholders; “Aparência” lista
  `dark`, `light` e os temas desbloqueados.
- Rodapé: nota `As alterações são aplicadas na hora.` + `PillButton("Fechar",
  "secondary", width=108)`.
- `showEvent`: limite o diálogo à área útil da tela (`availableGeometry()`) com
  uma folga de 40 px e centralize, como `ConfirmarEnvioDialog` já faz. Em telas
  pequenas/DPI alto, o diálogo não pode passar por baixo da barra de tarefas.

**Dimensões internas recomendadas**

| Elemento | Medida |
|---|---|
| Diálogo | 760×600 |
| Cabeçalho | 92 px |
| Abas | 42 px |
| Corpo | ~406 px (2 colunas, gap 16) |
| Card de código | coluna 1, ~1.48fr |
| Aside “Como funciona” | coluna 2, ~0.82fr |
| Rodapé | 60 px |
| Campo de código | 36 px |
| Botão Ativar tema | 142×36 |
| Botão Fechar | 108×36 |

### 6.4 Aba “Inserir código” — copy exata

- Eyebrow: `ACESSO RESTRITO`
- Título: `Ativar um tema pelo código`
- Texto: `Digite o nome de um tema para desbloqueá-lo e aplicá-lo agora. Os
  códigos não aparecem em nenhuma lista.`
- Label do campo: `CÓDIGO DO TEMA`
- Placeholder: `Digite o nome do tema`
- Botão: `Ativar tema` (com ícone de chave)
- Sucesso: título `Tema {label} ativado.` + `O tema foi aplicado e será lembrado
  na próxima abertura.`
- Erro: título `Código não reconhecido.` + `Confira o nome do tema e tente
  novamente. Nada foi alterado.`
- Rodapé do card: `TEMA ATUAL` + pill com o nome do tema.
- Aside: `COMO FUNCIONA` + três bullets:
  1. `Maiúsculas, acentos e espaços são ignorados.`
  2. `O tema fica salvo e volta na próxima abertura.`
  3. `Os códigos não aparecem em nenhuma lista.`
- Nota final: `Feature quase secreta. Nenhum tema é listado antes de ser ativado.`

O campo usa `QLineEdit#Field` com 36 px. O botão usa `PillButton` primário. O
feedback usa `QLabel#FeedbackOk`/`FeedbackErr` com `wordWrap(True)`.

QSS sugerido:

```css
QPushButton#SettingsTab {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 9px;
    min-height: 30px;
    padding: 0 14px;
    color: {t.text_secondary};
    font-size: 11px;
    font-weight: 500;
}
QPushButton#SettingsTab:hover {
    background: {t.surface_alt};
    color: {t.text};
}
QPushButton#SettingsTab:checked {
    background: {t.accent_soft};
    border-color: {t.accent};
    color: {t.accent_soft_text};
    font-weight: 600;
}
QFrame#SettingsCard {
    background: {t.surface_alt};
    border: 1px solid {t.border};
    border-radius: 12px;
}
QFrame#SettingsAside {
    background: {t.surface};
    border: 1px solid {t.border};
    border-radius: 12px;
}
QLabel#FeedbackOk {
    background: {t.ok_bg};
    border: 1px solid {t.ok_fg};
    border-radius: 9px;
    color: {t.ok_fg};
    padding: 9px 11px;
    font-size: 10px;
}
QLabel#FeedbackErr {
    background: {t.err_bg};
    border: 1px solid {t.err_fg};
    border-radius: 9px;
    color: {t.err_fg};
    padding: 9px 11px;
    font-size: 10px;
}
QLabel#ThemePill {
    background: {t.accent_soft};
    border: 1px solid {t.accent};
    border-radius: 7px;
    color: {t.accent_soft_text};
    padding: 3px 9px;
    font-size: 10px;
    font-weight: 600;
}
```

> Em `QFrame` com QSS, ligue `setAttribute(Qt.WidgetAttribute.WA_StyledBackground,
> True)` para o fundo ser pintado.

---

## 7. Ativação por código

### 7.1 Normalização

```python
import re
import unicodedata


def normalize_code(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return "".join(ch for ch in text.lower() if ch.isalnum())
```

Exemplos: `Açaí` → `acai`; `Lana Del Rey` → `lanadelrey`;
`graduation 2007` → `graduation2007`.

### 7.2 Mapa de códigos

Monte uma vez, no import do `main.py` ou no `SettingsDialog`:

```python
CODE_TO_THEME: dict[str, str] = {}
for key, theme in EXTRA_THEMES.items():
    for code in (theme.art.secret_code, *theme.art.aliases):
        if code:
            CODE_TO_THEME[normalize_code(code)] = key
```

| Tema | Código canônico | Aliases |
|---|---|---|
| Graduation | `graduation` | `graduation2007`, `murakami`, `goodmorning`, `kanyewest` |
| Ozzy | `ozzy` | `ozzyosbourne`, `princedarkness`, `nomoretours`, `blizzardofozz` |
| Lana Del Rey | `lana` | `lanadelrey`, `summertime`, `borntodie`, `hollywoodsadcore` |
| Açaí | `acai` | `acainight`, `premium`, `acairespecial` |

### 7.3 Aplicar

```python
def _activate_code(self) -> None:
    raw = self.code_input.text()
    key = CODE_TO_THEME.get(normalize_code(raw))
    if not key:
        self._show_feedback(
            "error",
            "Código não reconhecido.",
            "Confira o nome do tema e tente novamente. Nada foi alterado.",
        )
        return

    theme = EXTRA_THEMES[key]
    self.feedback_title.setText(f"Tema {theme.label} ativado.")
    self._show_feedback(
        "success",
        f"Tema {theme.label} ativado.",
        "O tema foi aplicado e será lembrado na próxima abertura.",
    )
    self.current_pill.setText(theme.label)
    self.theme_unlocked.emit(key)
```

Ligue também `self.code_input.returnPressed.connect(self._activate_code)`.

### 7.4 Feedback sem “piscar” errado

Ao trocar de estado, reaplique o QSS:

```python
def _show_feedback(self, state: str, title: str, detail: str) -> None:
    self.feedback.setObjectName("FeedbackOk" if state == "success" else "FeedbackErr")
    self.feedback.setText(f"<b>{title}</b><br>{detail}")
    self.feedback.style().unpolish(self.feedback)
    self.feedback.style().polish(self.feedback)
    self.feedback.setVisible(True)
```

Mantenha o texto de erro e sucesso visível; não dependa só da cor.

### 7.5 Segurança / produto

Isto **não é autenticação**. Os códigos são easter eggs de produto, não segredos
criptográficos. Não coloque os códigos em logs, telemetria ou mensagens de erro.
A lista de temas desbloqueados fica em `QSettings`; se o usuário limpar as
configurações, os temas voltam a ficar ocultos e o app cai para `dark` se o tema
salvo não estiver mais desbloqueado.

---

## 8. Aplicar os tokens aos widgets existentes

### 8.1 `build_qss`

O QSS atual já usa `t.text`, `t.accent`, `t.surface`, etc. As mudanças são:

1. Fonte global: `t.art.ui_font`.
2. `BrandTitle`: `t.art.display_font`, 16 px, `font-weight: 600`.
3. `SectionTitle`: `t.art.section_font or t.art.ui_font`, `t.art.section_size`.
4. `Chip`: fundo com gradiente `t.art.chip_from` → `t.art.chip_to` (fallback
   `t.accent`); texto `t.art.chip_fg or t.on_accent`; raio 10; 9 px.
5. `Badge`: `t.art.badge_bg`, `t.art.badge_fg`, `t.art.badge_border`
   (fallback `t.accent_soft`/`t.accent_soft_text`/transparente).
6. `Field`: já usa `t.field_bg`, `t.field_border`, `t.placeholder`.
7. `StatusBar` não é QSS; é `paintEvent` (ver 8.6).
8. Adicione os blocos do diálogo (`SettingsTab`, `SettingsCard`, `FeedbackOk`,
   `FeedbackErr`, `ThemePill`).

Cuidado com f-string: o `build_qss` usa `{{`/`}}`; mantenha o padrão.
Para tracking/capitalização, não dependa do QSS: aplique um `QFont` nos labels
criados em `_section` (e no `EnvioPage._section`), nos botões e no status.

### 8.2 Marca e logo

`App._apply_theme` deve atualizar o título com o suffix:

```python
suffix = ""
if t.art.brand_suffix:
    style = f"color:{t.art.brand_suffix_color or t.accent};"
    if t.art.brand_suffix_style == "italic":
        style += "font-style:italic;"
    suffix = f' <span style="{style}">{t.art.brand_suffix}</span>'
self.lbl_title.setText(f"{t.art.brand_label}{suffix}")
self.lbl_title.setTextFormat(Qt.TextFormat.RichText)
```

O `QLabel#BrandTitle` continua com 16 px e a mesma altura; o suffix não muda a
geometria do cartão.

`LogoMark.paintEvent`:

- 30×30, raio 9;
- fundo: `QLinearGradient` de `t.art.logo_from` para `t.art.logo_to` (fallback
  `t.primary_from` → `t.accent_pressed`);
- borda: `t.art.logo_border` (fallback transparente);
- glifo: `t.art.logo_motif` (`sheet`, `flower`, `bolt`, `cherry`, `berry`);
- cor do glifo: `t.art.logo_fg or t.on_accent`.

Desenhe os motivos com QPainterPath/ellipses, sem imagens. Mantenha o brilho
superior existente.

`Card` do header: se `t.art.card_from`/`card_to` existirem, pinte um gradiente
linear suave; senão use `t.surface` como hoje. Para Ozzy, desenhe a linha
superior vermelho→amarelo de 2 px (opcional, mas é a assinatura do tema).

### 8.2b `ThemeToggle`

Para o knob e os ícones acompanharem o tema:

```python
grad = QLinearGradient(knob_rect.topLeft(), knob_rect.bottomRight())
grad.setColorAt(0.0, C(t.primary_from))
grad.setColorAt(1.0, C(t.primary_to))

active = C(t.art.primary_text or t.on_accent)
idle = C(t.text_muted)
moon_color = active if self._pos < 0.5 else idle
sun_color = active if self._pos >= 0.5 else idle
```

Assim o knob dourado do Açaí, o amarelo do Ozzy, o rosa do Graduation e o
cereja do Lana aparecem sem novos campos. O track continua `surface_alt` com
borda `border`.

### 8.3 `ViewSwitch`

O thumb hoje usa `t.accent_soft` + borda `t.accent`. Para os temas com gradiente:

```python
if t.art.view_active_from:
    grad = QLinearGradient(thumb.topLeft(), thumb.bottomRight())
    grad.setColorAt(0.0, C(t.art.view_active_from))
    grad.setColorAt(1.0, C(t.art.view_active_to or t.art.view_active_from))
    p.setBrush(QBrush(grad))
else:
    p.setBrush(C(t.accent_soft))
p.setPen(QPen(C(t.art.view_active_border or t.accent), 1))
```

No `_sync_buttons`, o texto checado usa `t.art.view_active_fg or
t.accent_soft_text`. Mantenha altura 30, largura 268 e o thumb de 22 px.

### 8.4 `SegmentedControl`

Mesma lógica, com `seg_active_from/to/fg/border`. O trilho continua
`t.field_bg`/`t.field_border`; o thumb continua com raio de pílula. Mantenha 32
px e 4 opções.

### 8.5 `PillButton`

- Primário: gradiente `t.primary_from` → `t.primary_to`; texto
  `t.art.primary_text or t.on_accent`.
- Secundário: `t.surface`/`t.border`; texto `t.text_secondary`.
- `button_size`, `button_transform`, `button_tracking` do `ThemeArt`.
- Mantenha 36 px e as larguras 130/152 no formulário.
- O brilho/sheen atual pode ficar; é sutil e funciona nos dois modos.

### 8.6 `StatusBar`

- `paintEvent` usa `F(t.art.status_size, family=t.art.status_font or t.art.ui_font)`.
- Se `t.art.status_transform == "uppercase"`, desenhe `text.upper()`.
- Cores: `t.art.status_bg` (fallback `surface_alt`), `t.art.status_border`
  (fallback `border`), `t.art.status_fg` (fallback `text_secondary`) e
  `t.art.status_dot` (fallback `accent`).
- Mantenha 32 px e o ponto à esquerda.

### 8.7 Fundos (`StarField`)

Hoje `StarField` pinta gradiente + glow + estrelas. Adicione um switch por
`theme.art.pattern`:

| Pattern | Tema | Desenho |
|---|---|---|
| `stars` | dark | comportamento atual |
| `plain` | light | comportamento atual |
| `clouds` | Graduation | gradiente pastel + 3 blobs radiais + pontos brancos esparsos |
| `grain` | Ozzy | preto + glows vermelhos + scanlines de 1 px |
| `paper` | Lana | creme/rosa + grão de papel + anéis de vinil |
| `dotgrid` | Açaí | roxo + glows + grade de pontos + anel dourado |

Use `QRadialGradient`/`QLinearGradient` e um `QPixmap` de tile para grão/grade
(evite criar pincéis por frame). Cacheie o fundo por `(theme.key, size)`. Para
patterns estáticos, pare o `QTimer` de estrelas; só o `stars` anima.

As cores exatas estão em `screens/graduation.css`, `ozzy.css`, `lana.css` e
`acai.css`. Não invente; copie os stops.

### 8.8 Ícone da janela

`make_app_icon(theme)` usa `primary_from`/`accent_pressed`. Para os temas com
logo próprio, use `t.art.logo_from/to/fg` para o gradiente e o glifo. O ícone
tem 64×64; mantenha a proporção.

---

## 9. Página “Aparência” (opcional, mas recomendada)

- Mostra `Escuro` e `Claro` sempre.
- Mostra os temas desbloqueados, com um card/pílula por tema.
- **Não** mostra temas bloqueados, nem nomes, nem contagem.
- Clicar aplica o tema e fecha ou deixa o diálogo aberto.
- Um botão discreto “Esquecer temas desbloqueados” pode existir em “Sobre” ou no
  fim de “Aparência”. Se existir, peça confirmação e faça
  `settings.remove(UNLOCKED_SETTING)`; se o tema atual for secreto, volte para
  `dark`.

A aba “Geral” pode conter apenas um texto de versão e um checkbox de “reduzir
animações” (se o app já tiver `_reduced`); não invente preferências que não
existem.

---

## 10. Ordem de implementação sugerida

### Fase 1 — Dados e fontes (sem mudar a tela)

1. Criar `ThemeArt` e o campo `art` no `Theme`.
2. Criar `temas_extra.py` com os quatro dicts (copie de `tokens/*.json`).
3. Importar, construir `EXTRA_THEMES` e atualizar `THEMES`.
4. Carregar as fontes e trocar o `font-family` do QSS.
5. Rodar o app: dark/light devem estar idênticos; nenhum tema secreto ainda
   aparece.

### Fase 2 — Registro e persistência

1. `unlocked_keys`/`save_unlocked`/`available_themes`.
2. Ajustar `App.__init__` e `_set_theme`.
3. Ajustar `ThemeToggle` para `art.is_light`.
4. Testar manualmente setando `THEMES` e `QSettings` (sem UI ainda).

### Fase 3 — Botão e diálogo

1. Engrenagem no topo, 24×24, `draw_gear`.
2. `SettingsDialog` com as quatro abas e a página “Inserir código”.
3. QSS do diálogo.
4. Abrir/fechar, foco, `Esc`, `Enter`.

### Fase 4 — Ativação

1. `normalize_code` + `CODE_TO_THEME`.
2. `_activate_code`, feedback sucesso/erro.
3. `theme_unlocked` → `_on_theme_unlocked` → `_set_theme`.
4. Persistência e reabertura.

### Fase 5 — Pele visual

1. `build_qss` com fontes/tamanhos.
2. `ViewSwitch`, `SegmentedControl`, `PillButton`, `StatusBar`.
3. `LogoMark`, `Card`, título com suffix.
4. `StarField` com patterns.
5. `make_app_icon`.

### Fase 6 — Polimento

1. Comparar cada tela com `exports/*.png`.
2. Medir geometria (script da seção 11).
3. Testar fallback de fonte.
4. Testar os quatro códigos e aliases.
5. Testar tema inválido e persistência.

---

## 11. Checklist de testes

### 11.1 Geometria

Rode com a janela em 1280×960 e confira as posições (valores do app atual):

```text
header    y=44   h=52
switch    y=106  h=30
stack     y=146  h=764
entry 1   y=171  h=32
entry 2   y=242  h=32
seg       y=313  h=32
select    y=384  h=32
entry 5   y=455  h=32
divider   y=861  h=1
actions   y=874  h=36
status    y=918  h=32
```

Script rápido:

```python
for name in ["header", "switch", "stack", "status", "entry_nome",
             "entry_pasta", "seg", "select", "entry_destino",
             "btn_limpar", "btn_gerar", "divider"]:
    w = getattr(app, name)
    p = w.mapTo(app, w.rect().topLeft())
    print(name, p.x(), p.y(), w.width(), w.height())
```

Nenhum tema pode alterar esses valores. Se o layout “melhorar” visualmente mas
mover 1 px, está errado.

### 11.2 Códigos

- [ ] `graduation` aplica Graduation.
- [ ] `ozzy` aplica Ozzy.
- [ ] `lana` e `lana del rey` aplicam Lana.
- [ ] `açaí` e `acai` aplicam Açaí.
- [ ] `LANA DEL REY`, `AÇAÍ`, `graduation 2007` funcionam.
- [ ] Código inválido mostra erro, não muda o tema e não fecha o diálogo.
- [ ] Após reiniciar o app, o tema ativo volta.
- [ ] Após limpar `QSettings`, o tema secreto volta a ficar oculto e o app cai
      para dark/light.

### 11.3 UI

- [ ] Engrenagem no canto superior direito, à esquerda do toggle.
- [ ] Tooltip “Configurações”.
- [ ] Diálogo 760×600, modal, centralizado, `Esc` fecha.
- [ ] Aba “Inserir código” visível e ativa no design.
- [ ] Campo de código com foco; `Enter` ativa.
- [ ] Feedback de sucesso/erro visível e legível.
- [ ] “Tema atual” atualiza.
- [ ] Toggle escuro/claro continua funcionando.
- [ ] Tema secreto não é listado antes de desbloquear.
- [ ] Nenhuma sidebar/hero/footer novo.

### 11.4 Tipografia e fallback

- [ ] Fontes carregam no Windows.
- [ ] Sem as TTFs, o app usa Segoe UI e não quebra.
- [ ] Ozzy não altera a string das opções do segmentado (só a capitalização).
- [ ] Lana não aumenta a altura do cartão/linhas.
- [ ] Status de Ozzy em caixa alta não corta.

### 11.5 Negócio

- [ ] `python -m py_compile main.py temas_extra.py`.
- [ ] Fluxo “Gerar Excel” continua idêntico.
- [ ] Fluxo “Envio de e-mails” continua idêntico.
- [ ] Nenhuma alteração em `ope.py`, `funcoes.py`, `envios.py`.
- [ ] Nenhuma nova dependência além de PyQt6/pandas/openpyxl já existentes.

### 11.6 Visual

- [ ] Comparar `01-graduation-principal.png` com a tela real.
- [ ] Comparar `02-ozzy-principal.png` com a tela real.
- [ ] Comparar `03-lana-principal.png` com a tela real.
- [ ] Comparar `04-acai-principal.png` com a tela real.
- [ ] Comparar as quatro `*-configuracoes.png`.
- [ ] O fundo não atrapalha a leitura dos campos.
- [ ] O logo não deforma em 30×30 nem no ícone 64×64.

---

## 12. Critérios de aceite

1. Os quatro temas existem e são ativáveis por código.
2. O botão de configurações aparece no canto superior direito e abre o diálogo.
3. A aba “Inserir código” ativa, persiste e mostra sucesso/erro.
4. Temas secretos só aparecem na lista depois de desbloqueados.
5. A geometria de 1280×960 permanece idêntica à do app atual.
6. Dark/light continuam funcionando como antes.
7. Nenhuma regra de negócio foi alterada.
8. Fontes têm fallback e não quebram o layout.
9. Não há imagens/capas de terceiros; motivos são desenhados.
10. O visual bate com as telas de referência em `design/temas-secretos/`.

---

## 13. Rollback

Se algo der errado:

1. Reverta `main.py` para o commit anterior.
2. Remova `temas_extra.py`.
3. Remova as chaves `tema` e `temas_desbloqueados` do `QSettings` (opcional).
4. O kit em `design/temas-secretos/` é independente e pode ficar no repositório.

Nada de migração de dados, banco ou arquivos do usuário.

---

## 14. Commits sugeridos

```text
design: adiciona kit de temas secretos (HTML, tokens, guia)
feat(temas): adiciona ThemeArt e registra temas extras
feat(config): botão de configurações e aba Inserir código
feat(temas): aplica tokens aos widgets existentes
feat(temas): fundos, logos e tipografia por tema
test(temas): valida códigos, persistência e geometria
```

---

## 15. Apêndice A — Tabela rápida de tokens

Valores completos em `tokens/*.json`. Esta tabela é só para conferência rápida.

| Token | Graduation | Ozzy | Lana Del Rey | Açaí |
|---|---|---|---|---|
| `bg_top` | `#FBF7FF` | `#0B0A0A` | `#FFF8F8` | `#14001C` |
| `bg_bottom` | `#FFF0F7` | `#1A1010` | `#FFE8ED` | `#21042E` |
| `surface` | `#FFFFFF` | `#1D1B1B` | `#FFFDFC` | `#1F002B` |
| `text` | `#1C1033` | `#E8E1E0` | `#25181C` | `#F3E8FF` |
| `accent` | `#DB2777` | `#FBE500` | `#A10028` | `#A855F7` |
| `on_accent` | `#FFFFFF` | `#201C00` | `#FFFFFF` | `#FFFFFF` |
| `primary_from` | `#FF3388` | `#FBE500` | `#C81D3B` | `#F59E0B` |
| `primary_to` | `#A21CAF` | `#E8C900` | `#A10028` | `#FBBF24` |
| `primary_text` | `#FFFFFF` | `#201C00` | `#FFFFFF` | `#201C00` |
| `border` | `#E9D5FF` | `#373434` | `#E3BDBD` | `#4C1D6B` |
| `pattern` | `clouds` | `grain` | `paper` | `dotgrid` |
| `logo_motif` | `flower` | `bolt` | `cherry` | `berry` |

---

## 16. Apêndice B — Estrutura de `temas_extra.py`

```python
# temas_extra.py — dados puros; não importa main.py
EXTRA_THEMES = [
    {
        "key": "graduation",
        "theme": {
            # todos os 40 campos de cor/estado da dataclass Theme
            # (o 41º campo, art, vem do bloco "art" abaixo)
        },
        "art": {
            # todos os campos da dataclass ThemeArt
        },
    },
    # ozzy, lana, acai
]
```

No `main.py`:

```python
EXTRA_THEMES = {
    item["key"]: Theme(**item["theme"], art=ThemeArt(**item["art"]))
    for item in _EXTRA_THEME_DATA
}
```

Se preferir gerar o arquivo a partir dos JSONs durante o desenvolvimento:

```python
import json
from pathlib import Path

tokens = Path("design/temas-secretos/tokens")
data = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(tokens.glob("*.json"))]
# gere o texto de temas_extra.py e cole no projeto; não leia JSON em runtime.
```

---

## 17. Apêndice C — Cores exatas dos fundos

As CSS são a fonte de verdade. Resumo:

**Graduation** (`screens/graduation.css`)
- `linear-gradient(180deg, #FBF7FF, #FFF0F7)`
- blobs: rosa `rgba(255,51,136,.26)`, azul `rgba(56,189,248,.24)`, amarelo
  `rgba(255,196,0,.22)`
- grão de estrelinhas brancas a cada 118 px.

**Ozzy** (`screens/ozzy.css`)
- `linear-gradient(180deg, #0B0A0A, #1A1010)`
- glows `rgba(146,7,3,.46)` e `rgba(146,7,3,.30)`
- scanlines `rgba(255,255,255,.026)` a cada 3 px
- linha superior vermelho→amarelo.

**Lana Del Rey** (`screens/lana.css`)
- `linear-gradient(180deg, #FFF8F8, #FFE8ED)`
- glows `rgba(255,177,193,.42)` e `rgba(200,29,59,.14)`
- grão de papel `rgba(91,64,64,.07)` a cada 6 px
- anel de vinil à direita.

**Açaí** (`screens/acai.css`)
- `linear-gradient(180deg, #14001C, #21042E)`
- glows `rgba(126,34,206,.42)` e `rgba(245,158,11,.14)`
- grade de pontos `rgba(216,180,254,.14)` a cada 26 px
- anel dourado no topo direito.

---

## 18. Apêndice D — O que **não** fazer

- ❌ Copiar a barra de título Mac, sidebar, hero ou footer do `.figcraft`.
- ❌ Transformar cada passo em um card grande (o app atual não tem cards por passo).
- ❌ Mudar a ordem dos campos ou o texto dos labels.
- ❌ Alterar a string de `Marca`/`LNeg`/`Fornecedor`/`Não Separar`.
- ❌ Aumentar campos de 32 para 40, botões de 36 para 44, status de 32 para 40.
- ❌ Colocar uma lista pública com os quatro temas secretos.
- ❌ Usar capas, fotos ou logotipos dos artistas.
- ❌ Tocar em `ope.py`, `funcoes.py`, `envios.py`.
- ❌ Hardcodar cores nos widgets em vez de usar `Theme`/`ThemeArt`.
- ❌ Fazer o app depender de uma fonte instalada.
- ❌ Implementar tudo de uma vez sem testar a geometria entre as fases.

---

## 19. Definição de pronto

- [ ] Quatro temas registrados, com códigos e aliases.
- [ ] Botão de configurações no topo direito.
- [ ] Diálogo com as abas e a aba “Inserir código”.
- [ ] Ativação, feedback, persistência e reabertura.
- [ ] Lista de temas só com desbloqueados.
- [ ] Tokens aplicados a todos os widgets previstos.
- [ ] Fundos, logos e tipografia fiéis às telas.
- [ ] Geometria 1280×960 intacta.
- [ ] Dark/light intactos.
- [ ] Testes da seção 11 verdes.
- [ ] Nenhuma alteração de negócio.

Se você chegou até aqui e alguma decisão do design parecer “estranha” (por
exemplo, o espaço vertical grande antes das ações), **não conserte**: ele existe
no app atual e faz parte da estrutura que o usuário pediu para preservar.
