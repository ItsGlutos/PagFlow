# Tokens dos temas

Cada arquivo `*.json` tem dois blocos:

- **`theme`** — os 40 campos de cor/estado da dataclass `Theme` do `main.py`
  (`bg_top`, `surface`, `accent`, `ok_fg`, gradientes do botão primário etc.).
- **`art`** — a “película” visual que deve virar a dataclass `ThemeArt`:
  fontes, motivos do logo, pattern do fundo, gradientes de `ViewSwitch`,
  `SegmentedControl`, chip, badge, status, suffix da marca e código secreto.

## Como consumir

No `main.py`:

```python
Theme(**item["theme"], art=ThemeArt(**item["art"]))
```

Não leia os JSONs em tempo de execução no executável empacotado. Copie os
valores para `temas_extra.py` (ou gere esse arquivo durante o desenvolvimento).
Os JSONs são a documentação/fonte de verdade do design, não uma dependência de
produção.

## Observações

- Cores em HEX de 6 dígitos (`#RRGGBB`). Onde o design usa transparência, o
  `Theme` já tem `surface_alpha`; os gradientes de card/status devem receber
  alpha no código (`QColor.setAlpha`) se necessário.
- `aliases` é uma lista; `ThemeArt.aliases` é `tuple[str, ...]`. Converta com
  `tuple(...)` se quiser bater com a anotação de tipo.
- `secret_code` é o código canônico; a normalização ignora maiúsculas, acentos
  e espaços. O guia completo está em `../GUIA_PARA_AGENTE.md`.
- `pattern`: `clouds` (Graduation), `grain` (Ozzy), `paper` (Lana),
  `dotgrid` (Açaí). `stars`/`plain` ficam para dark/light.
- `logo_motif`: `flower`, `bolt`, `cherry`, `berry` (e `sheet` para o logo
  atual).
