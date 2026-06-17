# tools

## `make_og_image.py`

Generates the social-share / Open Graph image at `assets/og-image.png` (1200×630).

```bash
python tools/make_og_image.py
```

It is pure standard library — no Pillow, cairo or matplotlib — and includes a
minimal TrueType rasteriser, so the card can be regenerated anywhere Python 3
runs. Edit the `main()` function to change the wording or colours.

### Fonts

The fonts in `tools/fonts/` are bundled so the image is reproducible. They are
licensed under the SIL Open Font License (OFL); the accompanying `*-OFL.txt`
files contain the full licence text.

- **Big Shoulders** — title
- **Instrument Sans** — label & subtitle
