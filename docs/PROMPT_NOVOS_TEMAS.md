# Prompt — novos temas secretos do PagFlow

> **Como usar:** cole este prompt em um agente com acesso a este repositório e
> preencha os campos do bloco final. Ele foi escrito para reproduzir o padrão de
> qualidade dos temas já existentes (escuro, claro, Graduation, Ozzy, Lana e Açaí)
> sem tocar na lógica operacional nem no contrato de geometria.

**TL;DR**
- Leia o kit, os tokens/CSS e os temas existentes antes de propor.
- Extraia todos os tokens; nada de cor hardcoded.
- Prototipe ideias visuais novas **sem código**, envie print e espere o aval.
- Aplique um tema por vez; geometria, `ope.py`, `funcoes.py` e `envios.py` são intocáveis.
- Audite 1280×960, 1076×807 e 900×675; contraste, clipping, estados e persistência.
- Reaudite contra o print aprovado; atualize docs; relate testes e riscos.

---

## 1. Papel e missão

Você é **designer de produto sênior + engenheiro PyQt6**. Sua missão é criar e
aplicar **um** novo tema secreto no PagFlow, do primeiro token à captura final,
com o mesmo rigor dos temas existentes.

O PagFlow é um app desktop Windows (PyQt6) que consolida pagamentos SAP de XLS
para XLSX. A interface é uma camada puramente visual: **não altere** `ope.py`,
`funcoes.py` nem `envios.py`, e **não mude** a geometria, os fluxos ou as regras
de negócio.

O tema é uma “pele” completa: cores, tipografia, fundo, logo, componentes,
estados, diálogo de Configurações e persistência. Ele é um **easter egg**:
ativado por uma única palavra, sem aparecer em listas antes do desbloqueio.

---

## 2. Inegociáveis (leia antes de qualquer linha de código)

1. **Um tema por vez.** Termine, audite e aprove um tema antes de começar outro.
2. **Nada de variante clara/escura** para temas secretos: cada um é uma direção
   visual única. O alternador do topo continua funcionando e devolve o app ao
   tema principal (`dark` ou `light`) quando o usuário clica no lado oposto.
3. **O tema escuro é o principal.** O botão **Restaurar padrão PagFlow** sempre
   devolve `dark`, sem apagar os temas desbloqueados.
4. **Código de ativação:** uma única palavra, normalizada (sem acento, caixa
   baixa, só alfanumérico). O código não pode aparecer na UI, no README nem em
   nenhuma lista antes de ser usado.
5. **Geometria intocável.** O contrato da seção 4 vale para todos os temas.
6. **Nada de cor hardcoded** fora dos tokens do tema. Use `C()` e os campos de
   `Theme`/`ThemeArt`; campos vazios caem no token principal.
7. **Não revele os códigos existentes.** Se precisar consultá-los, leia
   `CODE_TO_THEME`/`temas_extra.py`; nunca os reproduza em documentação pública.
8. **Testes nunca usam o `QSettings` real.** Ver “Persistência e testes” na
   seção 7.
9. **Antes de aplicar, protótipo + print + aprovação explícita do usuário.**
10. **Não faça commit** sem o pedido do usuário. Ao final, informe arquivos
    alterados, testes e qualquer risco.

---

## 3. Leitura obrigatória (fontes de verdade)

Leia, nesta ordem, antes de propor qualquer coisa:

1. `design/temas-secretos/GUIA_PARA_AGENTE.md` — contrato visual do kit.
2. `design/temas-secretos/tokens/*.json` — tokens exatos do tema de referência.
3. `design/temas-secretos/screens/*.css` — composição, medidas, gradientes e
   estados que o Qt precisa reproduzir.
4. `design/temas-secretos/exports/*.png` — referência visual em 1280×960.
5. `main.py` — `Theme`, `ThemeArt`, `StarField`, `LogoMark`, `PillButton`,
   `IconButton`, `ThemeToggle`, `SegmentedControl`, `ViewSwitch`, `StatusBar`,
   `ThemeCard`, `SettingsDialog`, `build_qss`, `_THEME_COVERS`,
   `_paint_theme_cover`.
6. `temas_extra.py` — dados puros dos temas existentes (sem UI).
7. `assets/fonts/` e `assets/images/` — fontes OFL e artes já empacotadas.

Se o kit não trouxer um token, uma fonte ou uma decisão de layout, **pare e
pergunte**. Não invente valores “parecidos”.

---

## 4. Contrato de geometria (1280×960, 4:3)

| Elemento | x | y | largura | altura |
|---|---:|---:|---:|---:|
| janela | 0 | 0 | 1280 | 960 |
| header (cartão de marca) | 20 | 44 | 1240 | 52 |
| switch de telas | 506 | 106 | 268 | 30 |
| campo 1 — nome | 20 | 171 | 1240 | 32 |
| campo 2 — pasta | 20 | 242 | 1196 | 32 |
| segmented — abas | 20 | 313 | 1240 | 32 |
| select — personalização | 20 | 384 | 1240 | 32 |
| campo 5 — destino | 20 | 455 | 1196 | 32 |
| divisor | 20 | 861 | 1240 | 1 |
| ações — limpar/gerar | 20/1108 | 874 | 130/152 | 36 |
| status | 20 | 918 | 1240 | 32 |

Margens do layout raiz: **20, 12, 20, 10**. Header: 52 px. Campos: 32 px.
Botões: 36 px. Status: 32 px. O app é redimensionável, mas a proporção 4:3 e
essas âncoras precisam continuar coerentes em 1076×807 e 900×675.

**Nunca** “ganhe espaço” mudando altura de header, campo, botão ou status.

---

## 5. Onde cada coisa mora

- **Tokens de cor e estados:** `Theme` (40 campos) em `main.py`.
- **Tipografia, motivos, padrões e superfícies específicas:** `ThemeArt`.
- **Dados do tema secreto:** lista `EXTRA_THEMES` em `temas_extra.py` no formato
  `{"key": ..., "theme": {...}, "art": {...}}`.
- **Registro:** inclua o tema em `EXTRA_THEMES` e em `THEME_ORDER`; o código e
  os aliases vêm de `art.secret_code`/`art.aliases` e alimentam `CODE_TO_THEME`.
- **Ordem e códigos:** `THEME_ORDER`, `CODE_TO_THEME`, `normalize_code`,
  `unlocked_keys`, `save_unlocked`, `available_themes`.
- **Fundo:** `StarField._background()` + `_paint_clouds/_paint_grain/
  _paint_paper/_paint_dotgrid` e `draw_motif`/`draw_gear`/`draw_key`.
- **Capa de fundo (se o tema pedir):** `_THEME_COVERS`, `theme_cover()` e
  `_paint_theme_cover()`.
- **Diálogo:** `SettingsDialog` (760×600, mínimo 720×560; abas Geral,
  Aparência, Inserir código, Sobre).
- **Persistência:** `QSettings("PagFlow", "PagFlow")` com as chaves `tema`,
  `temas_desbloqueados` e `reduzir_animacoes`.

---

## 6. Processo em sete etapas (com checkpoints)

### Etapa 1 — Extrair o tema do kit

- Abra o JSON e o CSS do tema de referência.
- Monte a tabela completa de tokens: fundo, superfícies, texto, accent, campos,
  estados (ok/err/warn/info), primário, chip, badge, view switch, segmented,
  status, sombra.
- Liste o que é **arte** (fontes, logo, motivo, padrão, gradientes de estado,
  capa) e o que é **cor**.
- **Checkpoint:** mostre a tabela e diga o que ficou ambíguo. Não codifique ainda.

### Etapa 2 — Tipografia

- Escolha as famílias por papel: display, UI, mono, seção, botão, status,
  badge, meta.
- Carregue as TTFs em `assets/fonts/` via `load_theme_fonts()`; o fallback é
  **Segoe UI**.
- Use `F(px, weight, tracking, family, caps, italic)` e `tracking_px(em, size)`.
- **Nunca** coloque `font-family` global no QSS: isso sobrescreve as fontes de
  display. Defina a fonte do app e dos widgets com `setFont`.
- Meça tudo com `QFontMetrics`: largura, altura, ascent/descent, clipping.
- Anton em 14–16 px tem traço fino; para nomes de cartão de tema use a fonte de
  UI. Títulos de marca podem continuar na display.
- **Checkpoint:** renderize o header e uma seção com cada família; mostre
  tamanhos e tracking.

### Etapa 3 — Fundo e motivo

- Implemente o padrão do tema no `StarField` (nuvens, grão, papel, dotgrid ou
  novo padrão aprovado).
- Desenhe o motivo do logo em `draw_motif` (flower, bolt, cherry, berry, sheet
  ou novo motivo aprovado).
- Use `QPainterPath`, gradientes e `C()`; nada de imagem solta se o kit for
  vetorial.
- Respeite `stars`/`pattern`: o tema escuro tem estrelas animadas; os secretos,
  padrões próprios.
- Cacheie o fundo por largura, altura e DPR; não reconstrua a cada quadro.
- **Checkpoint:** captura do fundo puro em 1280×960, sem widgets.

### Etapa 4 — Componentes

Passe por todos, um a um:

- header/logo/brand title/badge;
- campos, placeholders, foco, ícones de pasta;
- segmented control e view switch (ativo, hover, foco);
- botões primário/secundário, disabled, hover, pressed;
- status bar (mensagem, dot, erro/sucesso);
- toggle de tema e engrenagem de Configurações;
- cartões de tema e abas do diálogo;
- feedback de código inválido/válido;
- sombras e scrim.

Regras:

- estados de foco visíveis;
- texto nunca cortado nem sobreposto;
- nada de `#fff`/`#000` fixos;
- ícones desenhados em QPainter ou SVG coerentes com o tema;
- o toggle mantém os ícones legíveis nos dois lados e o knob não “engole” o
  ícone inativo;
- o botão **Restaurar padrão PagFlow** fica visível e não é coberto pelos
  cartões (use grid com rolagem e cartões de 74 px).

### Etapa 5 — Capa de fundo (somente se o briefing pedir)

Se o tema tiver uma arte de capa aprovada:

1. Prototipe **sem alterar o código** (monkeypatch em runtime) e envie o print.
2. Espere aprovação explícita. Só então:
   - salve a arte em `assets/images/theme-art-NN.jpg` (nome **neutro**, sem
     revelar o código do tema); é um bitmap real, nunca uma recriação em
     CSS/QSS;
   - registre em `_THEME_COVERS`: `(arquivo, lado_em_px_em_1280, opacidade)`;
   - a capa é desenhada por `_paint_theme_cover`, **atrás de todo o conteúdo**,
     ancorada em `x = largura - 20 - tamanho`, `y = 44`;
   - use camada com DPR, `SmoothPixmapTransform` e as máscaras:
     vertical `0.00/0.55/0.82/1.00` → `255/235/120/0`;
     horizontal `0.00/0.28/0.93/1.00` → `0/210/255/0`;
   - escale proporcionalmente (`tamanho = min(base, largura * base / 1280)`);
   - cacheie por arquivo; se faltar a imagem, o tema funciona sem ela.
3. Referências atuais: Graduation 560 px/40%; Ozzy 540 px/55%. Cada tema tem
   sua opacidade — capas escuras pedem mais, capas claras pedem menos.
4. Cuidado com capas de título tipográfico grande: elas podem brigar com o
   header. Se o teste mostrar colisão, proponha recorte/desfoque **e peça
   aprovação**; não decida sozinho.

### Etapa 6 — Auditoria

Rode o harness offscreen:

- `WA_DontShowOnScreen`, janela forçada em 1280×960;
- espere ~500 ms para o cross-fade terminar;
- `grab()` e compare com `exports/`;
- repita em 1076×807 e 900×675;
- confira a tabela de geometria da seção 4;
- verifique contraste, clipping, sobreposição, estados e foco.

Testes funcionais mínimos:

- tema bloqueado não troca;
- código inválido não altera nada e mostra feedback;
- código válido desbloqueia, aplica e persiste;
- reabrir mantém;
- **Restaurar padrão** volta ao escuro e mantém desbloqueios;
- **Esquecer temas** limpa e volta ao escuro;
- toggle escuro↔claro;
- **Reduzir animações** funciona;
- troca A→B→A não deixa cache/arte “presa”;
- fonte ausente cai para Segoe UI;
- capa ausente não quebra o tema;
- `PagFlow.spec` inclui as pastas de assets.

### Etapa 7 — Aplicar, documentar e reauditar

- Aplique as mudanças em `main.py`/`temas_extra.py`/assets.
- Rode de novo a captura em 1280×960 e compare com o print aprovado; se não
  estiver **pixel a pixel** igual (ou visualmente idêntico), corrija.
- Atualize `docs/temas-secretos/<tema>.png`, a folha `visao-geral.png` e
  remova protótipos temporários.
- Rode a suíte funcional e a geometria.
- Relate arquivos, testes, decisões e riscos.

---

## 7. Receitas técnicas que evitam retrabalho

### QSS × `setFont`

- Não use `QWidget { font-family: ... }` global.
- Defina `app.setFont(F(11, family=ui_font))` e `self.setFont(...)`.
- Para display/brand/seção/badge/status, aplique `setFont` no widget.
- QSS cuida de cor, fundo, borda, raio, padding e estados; fonte é `setFont`.

### Alturas e clipping

- Header de marca: 52 px; título e subtítulo dividem a faixa.
  Nos temas secretos, o título pode ganhar respiro (`brand_dy`):
  título `26+dy`, subtítulo `25-dy`; no escuro/claro, `dy=0`.
  Valores de referência já usados: Ozzy 5, Graduation 4, Açaí 4, Lana 3.
  Ajuste pela métrica real da display font, não por chute.
- Labels de feedback: `adjustSize()` + `setMinimumHeight(max(52, sizeHint))`.
- Grid de Aparência: cartões de 74 px, espaçamento 8, `QScrollArea`; não deixe
  o botão de restaurar competir com os cartões.
- Meça o texto com `QFontMetrics` antes de considerar pronto.

### Fundo e performance

- `_bg_cache` é recriado só quando muda tema, largura, altura ou DPR.
- Estrelas repintam apenas os retângulos delas.
- Evite `QGraphicsBlurEffect` em widgets grandes; prefira arte pré-processada.
- Capas: uma camada por rebuild, não por frame.

### Persistência e testes

- Isole o `QSettings` em um INI temporário **antes** de importar o app:
  ```python
  ini = Path(tempfile.mkdtemp()) / "s.ini"
  QSettings.setDefaultFormat(QSettings.Format.IniFormat)
  QSettings.setPath(QSettings.Format.IniFormat,
                    QSettings.Scope.UserScope, str(ini.parent))
  # depois de importar main:
  main.QSettings = lambda *a, **k: RealSettings(str(ini), RealSettings.Format.IniFormat)
  ```
- Nunca chame `settings.clear()` no registro real: isso apaga caminhos,
  assunto e corpo de e-mails do usuário.
- Teste reabertura com o mesmo INI e, no fim, confirme que o tema salvo é o
  esperado.

### Empacotamento

- `PagFlow.spec` precisa de `datas=[('assets/fonts','assets/fonts'),
  ('assets/images','assets/images')]`.
- No modo `frozen`, resolva caminhos com `sys._MEIPASS`.
- Novos imports lazy precisam entrar em `hiddenimports`.

### OneDrive / arquivo mudando entre leitura e edição

Se o arquivo for alterado entre o read e o write (comum no OneDrive), releia e
refaça a edição. Para patches grandes, use um script com contagem exata de
ocorrências e `assert`, em vez de editar às cegas.

---

## 8. Barra de qualidade

- **Contraste:** texto normal ≥ 4.5:1; texto grande ≥ 3:1; ícones e bordas de
  foco visíveis. Confira botão primário, status, placeholder e texto mudo.
- **Legibilidade:** nada de fonte display em corpo pequeno; nada de tracking
  negativo; nada de caixa alta em parágrafos.
- **Layout:** zero clipping, zero sobreposição, zero “pulo” ao trocar de tema.
- **Consistência:** todos os estados (hover, pressed, disabled, focus) existem
  e são distintos.
- **Movimento:** cross-fade de 260 ms; respeito a `reduzir_animacoes`; sem
  animação decorativa não aprovada.
- **Acessibilidade:** tab order, foco por teclado, contraste, áreas de clique.
- **Performance:** troca de tema instantânea; sem reconstrução de fundo por
  frame; sem efeitos caros em widgets grandes.
- **Resiliência:** fonte ausente, capa ausente e asset corrompido não quebram.

---

## 9. Protocolo de validação e aprovação

1. **Protótipo sem código** para qualquer ideia visual nova (capa, padrão,
   composição). Capture em 1280×960 e envie o print.
2. **Espere o “aprovado” explícito.** Não aplique enquanto houver dúvida.
3. Aplique **um** tema; não mexa nos outros.
4. Reaudite e compare com o print aprovado. Se não bater, conserte antes de
   dizer que terminou.
5. Mostre o resultado final e um resumo curto de testes.
6. Se algo do briefing for ambíguo, pergunte em uma rodada objetiva, com uma
   recomendação.

---

## 10. Armadilhas já encontradas (não repita)

- QSS global de `font-family` sobrescrevendo display fonts.
- Título de marca encostando na borda do header em fontes altas (Anton,
  Playfair) — use `brand_dy`.
- Cartões de Aparência estourando/sobrepondo o botão de restaurar.
- Feedback de código cortado em duas linhas.
- Engrenagem parecendo um sol; ícones do toggle sumindo no tema claro.
- Capa muito translúcida ou muito opaca em relação à referência.
- Capa com título tipográfico enorme colidindo com o header (caso Lana):
  prototipe e peça decisão antes de recortar/desfocar.
- `t.key` usado como “é claro?” em vez de `art.is_light`.
- Scrim aparecendo no snapshot do cross-fade.
- Teste limpando o `QSettings` real e apagando dados do usuário.
- Protótipo aprovado e implementação diferente: sempre compare pixel a pixel.

---

## 11. Definition of Done

- [ ] Código de uma palavra, normalizado, fora de listas/README.
- [ ] `Theme` completo (40 campos) e `ThemeArt` com tudo que o tema precisa.
- [ ] Fontes carregadas, fallback Segoe UI, sem QSS global de família.
- [ ] Fundo, motivo e padrão próprios; cache correto.
- [ ] Todos os componentes e estados tematizados.
- [ ] Capa (se houver) aprovada, em `assets/images/theme-art-NN.jpg`, com
      `_THEME_COVERS`, máscaras, escala e fallback.
- [ ] Geometria 1280×960 exata; 1076×807 e 900×675 sem quebra.
- [ ] Contraste, clipping e overflow conferidos.
- [ ] Bloqueio, desbloqueio, persistência, restaurar, esquecer e toggle testados.
- [ ] Reduzir animações testado.
- [ ] Fonte/capa ausentes testadas.
- [ ] `PagFlow.spec` empacota os assets.
- [ ] Docs e folha de contato atualizadas; protótipos removidos.
- [ ] `ope.py`, `funcoes.py` e `envios.py` intocados.
- [ ] Relatório final com arquivos, testes e riscos.

---

## 12. Formato do relatório final

Responda em português, curto e verificável:

1. O que foi aplicado (tema, código, modo, capa).
2. Arquivos alterados (com links).
3. Testes executados e resultado (geometria, funcional, fallback, resize).
4. Decisões de design não óbvias.
5. Riscos/caveats (dados de usuário, assets, licenças de arte).
6. Uma imagem final em 1280×960.

---

## Anexo A — Campos que não podem faltar

**`Theme` (40 campos):**
`key`, `label`, `bg_top`, `bg_bottom`, `glow`, `glow_alpha`, `surface`,
`surface_alpha`, `surface_alt`, `border`, `border_strong`, `text`,
`text_secondary`, `text_muted`, `accent`, `accent_hover`, `accent_pressed`,
`on_accent`, `accent_soft`, `accent_soft_text`, `field_bg`, `field_focus`,
`field_border`, `placeholder`, `ok_bg`, `ok_fg`, `err_bg`, `err_fg`, `warn_bg`,
`warn_fg`, `info_bg`, `info_fg`, `primary_from`, `primary_to`,
`primary_hover_from`, `primary_hover_to`, `primary_pressed_from`,
`primary_pressed_to`, `stars`, `shadow_alpha`.

**`ThemeArt` (por papel):** identidade (`is_light`, `secret_code`, `aliases`);
tipografia (`display_font`, `ui_font`, `mono_font`, `section_font`,
`button_font`, `status_font`, `status_size`, `status_transform`,
`status_tracking`); marca (`brand_label`, `brand_suffix`,
`brand_suffix_style`, `brand_suffix_color`, `brand_transform`,
`brand_tracking`, `brand_size`, `brand_dy`); seções (`section_transform`,
`section_tracking`, `section_size`); botões (`button_transform`,
`button_tracking`, `button_size`); logo (`logo_motif`, `logo_from`,
`logo_to`, `logo_mid`, `logo_mid_pos`, `logo_fg`, `logo_border`); fundo
(`pattern`); superfícies (`primary_text`, `card_from`, `card_to`,
`card_edge_from`, `card_edge_to`, `card_edge_height`, `card_alpha`,
`card_edge_alpha`); chip (`chip_from`, `chip_to`, `chip_fg`); badge
(`badge_bg`, `badge_fg`, `badge_border`, `badge_font`, `badge_transform`,
`badge_tracking`); meta (`meta_font`, `meta_transform`, `meta_tracking`);
status (`status_bg`, `status_border`, `status_fg`, `status_dot`); view switch
(`view_active_*`); segmented (`seg_active_*`); diálogo
(`dialog_title_size`); descrição (`description`).

---

## 13. Preencha antes de começar

```text
TEMA:            {{nome do tema}}
CÓDIGO:          {{uma palavra}}
MODO:            {{claro | escuro}}
REFERÊNCIA:      {{caminho do JSON/CSS/export no design/temas-secretos}}
PALETA:          {{tokens principais, se não vierem do kit}}
TIPOGRAFIA:      {{display / UI / mono}}
MOTIVO:          {{flower | bolt | cherry | berry | sheet | novo}}
PADRÃO:          {{clouds | grain | paper | dotgrid | novo}}
CAPA:            {{sim/não; arquivo; opacidade; tamanho; ancoragem}}
OBSERVAÇÕES:     {{restrições, referências, o que evitar}}
```
