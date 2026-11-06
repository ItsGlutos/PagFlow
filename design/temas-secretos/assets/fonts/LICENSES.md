# Fontes incluídas

Todas as fontes deste kit vêm do Google Fonts e são distribuídas sob a
**SIL Open Font License 1.1 (OFL)**. Os arquivos de licença originais estão
nesta pasta (`OFL-*.txt`).

| Família | Arquivos | Uso no kit | Licença |
|---|---|---|---|
| Outfit | `Outfit-400.ttf`, `Outfit-600.ttf`, `Outfit-800.ttf` | Títulos e seções do tema Graduation | OFL 1.1 |
| Space Grotesk | `SpaceGrotesk-400.ttf`, `SpaceGrotesk-500.ttf`, `SpaceGrotesk-700.ttf` | Interface, meta e botões do Graduation/Ozzy | OFL 1.1 |
| Anton | `Anton-400.ttf` | Títulos do tema Ozzy | OFL 1.1 |
| JetBrains Mono | `JetBrainsMono-400.ttf`, `JetBrainsMono-700.ttf` | Códigos, status e meta do Ozzy | OFL 1.1 |
| Playfair Display | `PlayfairDisplay-400.ttf`, `PlayfairDisplay-600.ttf`, `PlayfairDisplay-700.ttf`, `PlayfairDisplay-400-italic.ttf`, `PlayfairDisplay-600-italic.ttf` | Títulos e seções do tema Lana Del Rey | OFL 1.1 |
| Plus Jakarta Sans | `PlusJakartaSans-400.ttf`, `PlusJakartaSans-500.ttf`, `PlusJakartaSans-600.ttf`, `PlusJakartaSans-700.ttf` | Interface do tema Lana Del Rey | OFL 1.1 |
| Sora | `Sora-400.ttf`, `Sora-600.ttf`, `Sora-700.ttf` | Interface e títulos do tema Açaí | OFL 1.1 |

## Como usar no PyQt6

```python
from pathlib import Path
from PyQt6.QtGui import QFontDatabase

FONT_DIR = Path(__file__).with_name("assets") / "fonts"
for path in sorted(FONT_DIR.glob("*.ttf")):
    QFontDatabase.addApplicationFont(str(path))
```

Carregue as fontes **antes** de criar `QApplication`/`App` (ou pelo menos antes
de construir os widgets). Se uma família não estiver disponível, o app deve cair
para `Segoe UI` sem quebrar o layout.

## Créditos

- Outfit — Rodrigo Fuenzalida
- Space Grotesk — Florian Karsten
- Anton — Vernon Adams
- JetBrains Mono — JetBrains
- Playfair Display — Claus Eggers Sørensen
- Plus Jakarta Sans — Tokotype
- Sora — Jonathan Barnbrook / Google Fonts

Consulte os arquivos `OFL-*.txt` para os termos completos.
