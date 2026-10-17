Embedded chart fonts
====================

The sports SVG graphics in ../charts/ contain WOFF subsets of the following
fonts. The subsets retain their original copyright and license name records.
The complete applicable font licenses are also distributed in this directory.
Font licenses apply to the embedded font software, not to the sports data or
article text. QuickIrisChart is only the CSS family alias used by the renderer.

DejaVu Sans 2.37
  Source input: DejaVuSans.ttf, from the system fonts-dejavu-core package.
  Project: https://github.com/dejavu-fonts/dejavu-fonts
  License: Bitstream Vera / Arev font licenses; DejaVu changes are public domain.
  Full notices: DejaVuSans-LICENSE.txt
  Reference: https://dejavu-fonts.github.io/License.html
  Used for: English, Spanish, Brazilian Portuguese, French, German.

Noto Sans CJK KR 2.004
  Source input: NotoSansCJKkr-Regular.otf.
  Project font path: Sans/OTF/Korean/NotoSansCJKkr-Regular.otf
  Project: https://github.com/notofonts/noto-cjk
  Copyright: 2014-2021 Adobe; exact notice is retained in the font and license file.
  License: SIL Open Font License 1.1.
  Full notices: NotoSansCJK-OFL.txt
  Upstream license: https://github.com/notofonts/noto-cjk/blob/main/Sans/LICENSE
  Used for: Korean and Japanese.

Noto Sans Devanagari 2.007
  Source input: NotoSansDevanagari[wdth,wght].ttf from Google Fonts.
  Source: https://github.com/google/fonts/tree/main/ofl/notosansdevanagari
  Copyright: 2022 The Noto Project Authors.
  License: SIL Open Font License 1.1.
  Full notices: NotoSansDevanagari-OFL.txt
  Upstream license: https://github.com/google/fonts/blob/main/ofl/notosansdevanagari/OFL.txt
  Used for: Hindi.

Modifications by this project: the renderer selects the glyphs used by each
chart and converts the subset to WOFF. For the variable Devanagari input it first
instantiates the font at its default axes. It does not redraw the glyphs.
The original copyright and license notices continue to apply to these subsets.
No reserved font name is declared in the two supplied Noto license headers.

License files were checked against the official sources on 2026-10-17.
build.py copies this directory's .txt files into the public site output.
