# Font Assets

All fonts in this directory are open-source (OFL or Apache 2.0 licensed).
They are bundled in-repo for offline reliability (no network calls at runtime).

## Font inventory

| File | Family | Style | License | Source |
|------|--------|-------|---------|--------|
| PlayfairDisplay-Bold.ttf | Playfair Display | Bold | SIL OFL 1.1 | Google Fonts |
| PlayfairDisplay-Regular.ttf | Playfair Display | Regular | SIL OFL 1.1 | Google Fonts |
| Lato-Regular.ttf | Lato | Regular | SIL OFL 1.1 | Google Fonts |
| Lato-Italic.ttf | Lato | Italic | SIL OFL 1.1 | Google Fonts |
| Lato-Bold.ttf | Lato | Bold | SIL OFL 1.1 | Google Fonts |
| BebasNeue-Regular.ttf | Bebas Neue | Bold/Display | SIL OFL 1.1 | Google Fonts |
| ComicNeue-Regular.ttf | Comic Neue | Regular | SIL OFL 1.1 | Google Fonts |
| Montserrat-Bold.ttf | Montserrat | Bold | SIL OFL 1.1 | Google Fonts |
| Montserrat-Regular.ttf | Montserrat | Regular | SIL OFL 1.1 | Google Fonts |
| OpenSans-Regular.ttf | Open Sans | Regular | SIL OFL 1.1 | Google Fonts |
| Lobster-Regular.ttf | Lobster | Regular | SIL OFL 1.1 | Google Fonts |
| SourceSans3-Regular.ttf | Source Sans 3 | Regular | SIL OFL 1.1 | Google Fonts |
| JetBrainsMono-Regular.ttf | JetBrains Mono | Regular | SIL OFL 1.1 | JetBrains |

## Download instructions

All fonts are available at https://fonts.google.com/ (search by family name).
For JetBrains Mono: https://www.jetbrains.com/lp/mono/

### Quick download via curl (Linux/macOS)
```bash
# Example for Lato
curl -L "https://fonts.gstatic.com/s/lato/v24/S6uyw4BMUTPHjx4wXiWtFCc.woff2" -o Lato-Regular.ttf
```

For production deployment, download once and commit the TTF files.
The files are NOT committed to git-lfs — keep total font directory under 10 MB.

## Usage in code

```python
from pathlib import Path
_FONTS_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"
font_path = _FONTS_DIR / "PlayfairDisplay-Bold.ttf"
```

## License text

SIL Open Font License 1.1: https://scripts.sil.org/OFL
Apache 2.0: https://www.apache.org/licenses/LICENSE-2.0

All fonts are freely redistributable for commercial use.
