#!/usr/bin/env python3
"""Render reviewed sports evidence as deterministic, accessible SVG graphics.

No network calls, image-generation models, or inferred sports statistics are used.
Requires Pillow and fonttools. Pass local licensed font files so measurements and
embedded subsets agree: --font-latin ... --font-cjk ... --font-hi ... .
The embedded font retains its copyright and licensing name records.
Use --group GROUP to render a completed group; --attach updates only its figures.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import math
from pathlib import Path
import re
from xml.sax.saxutils import escape, quoteattr

from PIL import ImageFont
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("en", "ko", "es", "ja", "pt-BR", "fr", "de", "hi")
WIDTH = 960
MARGIN = 64
INK = "#172F40"
MUTED = "#536C7B"
LINE = "#D6E2E8"
TEAL = "#087D85"
BLUE = "#3762B4"
GOLD = "#E7A33B"
MODEL_LABEL = {
    "en": "Opta model estimate", "ko": "Opta 모델 추정치", "es": "Estimación del modelo Opta",
    "ja": "Optaモデルの推定値", "pt-BR": "Estimativa do modelo Opta", "fr": "Estimation du modèle Opta",
    "de": "Schätzung des Opta-Modells", "hi": "Opta मॉडल का अनुमान",
}


def load(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(f"Expected an object: {path}")
    return result


def number(value: float, locale: str) -> str:
    output = str(int(value)) if float(value).is_integer() else f"{value:g}"
    return output.replace(".", ",") if locale in {"es", "pt-BR", "fr", "de"} else output


class Graphic:
    def __init__(self, locale: str, labels: dict, facts: dict, font_path: Path):
        self.locale, self.labels, self.facts, self.font_path = locale, labels, facts, font_path
        self.elements = []
        self.characters = set(" 0123456789")
        self.bounds = []
        self.fonts = {}
        self.counter = 0

    def font(self, size: int):
        if size not in self.fonts:
            self.fonts[size] = ImageFont.truetype(str(self.font_path), size)
        return self.fonts[size]

    def width(self, text: str, size: int) -> float:
        return self.font(size).getlength(text)

    def wrap(self, text: str, width: float, size: int) -> list[str]:
        # Reserve room for synthetic bold and differences in glyph rasterization.
        limit = width / 1.06
        result = []
        for paragraph in text.splitlines() or [""]:
            tokens = re.findall(r"\S+\s*", paragraph)
            line = ""
            for token in tokens:
                if self.width(token.rstrip(), size) > limit:
                    if line.strip():
                        result.append(line.strip())
                        line = ""
                    # Unspaced Japanese/CJK sentences need character boundaries.
                    for char in token:
                        if line and self.width(line + char, size) > limit:
                            result.append(line.rstrip())
                            line = char
                        else:
                            line += char
                elif line and self.width(line + token, size) > limit:
                    result.append(line.rstrip())
                    line = token
                else:
                    line += token
            result.append(line.rstrip())
        return result

    def text(self, x: float, y: float, value: str, *, size: int = 28, color: str = INK,
             weight: int = 400, anchor: str = "start") -> None:
        if self.locale == "hi":
            value = value.replace("′", " मिनट")
        self.characters.update(value)
        self.counter += 1
        actual_width = self.width(value, size) * (1.04 if weight >= 600 else 1)
        left = x if anchor == "start" else x - actual_width if anchor == "end" else x - actual_width / 2
        self.bounds.append((left, y - size, left + actual_width, y + size * .42, value))
        self.elements.append(f'<text id="t{self.counter}" x="{x:g}" y="{y:g}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(value)}</text>')

    def block(self, x: float, y: float, width: float, value: str, *, size: int = 28,
              color: str = INK, weight: int = 400, gap: float = 1.45) -> float:
        lines = self.wrap(value, width, size)
        for i, line in enumerate(lines):
            self.text(x, y + size + i * size * gap, line, size=size, color=color, weight=weight)
        return y + len(lines) * size * gap

    def rect(self, x, y, width, height, fill, *, radius=0, stroke=None):
        outline = f' stroke="{stroke}" stroke-width="2"' if stroke else ""
        self.elements.append(f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" rx="{radius:g}" fill="{fill}"{outline}/>')

    def line(self, x1, y1, x2, y2, *, color=LINE, width=2, dash=None):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.elements.append(f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke="{color}" stroke-width="{width}"{extra}/>')

    def header(self, context: str) -> float:
        self.text(MARGIN, 48, "QUICKIRIS  /  " + self.facts["league"], size=22, weight=700, color=TEAL)
        y = self.block(MARGIN, 72, WIDTH - 2 * MARGIN, self.labels["title"], size=42, weight=700, gap=1.32)
        return self.block(MARGIN, y + 18, WIDTH - 2 * MARGIN, context, size=27, color=MUTED) + 30

    def footer(self, y: float, footer: str) -> float:
        self.line(MARGIN, y, WIDTH - MARGIN, y)
        y = self.block(MARGIN, y + 18, WIDTH - 2 * MARGIN, self.labels["caption"], size=24, color=MUTED)
        return self.block(MARGIN, y + 16, WIDTH - 2 * MARGIN, footer, size=22, color=MUTED) + 34

    def font_css(self) -> str:
        font = TTFont(self.font_path)
        # These charts use the font's default metrics; a static instance is much
        # smaller than embedding all variable axes in each standalone graphic.
        if "fvar" in font:
            axes = {axis.axisTag: axis.defaultValue for axis in font["fvar"].axes}
            font = instantiateVariableFont(font, axes, inplace=True)
        family = font["name"].getDebugName(16) or font["name"].getDebugName(1)
        missing = self.characters - {chr(code) for code in font.getBestCmap()}
        if missing:
            raise ValueError(f"Font lacks characters for {self.locale}: {sorted(missing)!r}")
        options = subset.Options()
        options.drop_tables += ["FFTM"]
        options.name_IDs = ["*"]
        options.name_legacy = True
        options.name_languages = ["*"]
        options.layout_features = ["*"]
        sub = subset.Subsetter(options=options)
        sub.populate(text="".join(sorted(self.characters)))
        sub.subset(font)
        font.flavor = "woff"
        output = io.BytesIO()
        font.save(output)
        encoded = base64.b64encode(output.getvalue()).decode("ascii")
        # The named fallback also makes local renderers that do not support
        # embedded @font-face use the same font as the layout measurement.
        fallback = json.dumps(family, ensure_ascii=False)
        return "@font-face{font-family:QuickIrisChart;src:url(data:font/woff;base64," + encoded + ") format('woff');font-weight:400}text{font-family:QuickIrisChart," + escape(fallback) + ",sans-serif}"

    def finish(self, height: float) -> str:
        height = math.ceil(height)
        for left, top, right, bottom, value in self.bounds:
            if left < 20 or right > WIDTH - 20 or top < 0 or bottom > height:
                raise ValueError(f"Text exceeds graphic bounds ({self.locale}): {value!r}; {(left, top, right, bottom)} / {height}")
        facts_json = json.dumps({"translation_group": self.facts["translation_group"], "chart": self.facts.get("chart"),
                                "source_urls": [source["url"] for source in self.facts.get("sources", [])]}, ensure_ascii=False, separators=(",", ":"))
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="chart-title chart-description" lang="{self.locale}" xml:lang="{self.locale}">
<title id="chart-title">{escape(self.labels['title'])}</title>
<desc id="chart-description">{escape(self.labels['alt'] + ' ' + self.labels['caption'])}</desc>
<metadata>{escape(facts_json)}</metadata>
<defs><style>{self.font_css()}</style></defs>
<rect width="{WIDTH}" height="{height}" fill="#FFFFFF"/>
{chr(10).join(self.elements)}
</svg>
'''


def watch_points(g: Graphic) -> str:
    stages = g.facts["chart"]["stages"]
    questions = g.labels["questions"]
    if len(stages) != 3 or len(questions) != 3 or g.facts["chart"].get("numbers"):
        raise ValueError("Watch-point schematic requires three questions and no invented figures")
    y = g.header(g.labels["footer"])
    for i, (stage, question) in enumerate(zip(stages, questions)):
        label = g.labels["labels"][stage]
        question_lines = g.wrap(question, 685, 29)
        label_lines = g.wrap(label, 685, 33)
        card_height = 44 + len(label_lines) * 33 * 1.35 + 16 + len(question_lines) * 29 * 1.45 + 26
        g.rect(MARGIN, y, WIDTH - 2 * MARGIN, card_height, "#F2F7F9", radius=14)
        g.rect(MARGIN, y, 7, card_height, (TEAL, BLUE, GOLD)[i], radius=3)
        g.text(98, y + 64, f"0{i+1}", size=35, weight=700, color=TEAL)
        cursor = g.block(178, y + 26, 685, label, size=33, weight=700, gap=1.35)
        g.block(178, cursor + 14, 685, question, size=29, color=INK)
        y += card_height + 22
    height = g.footer(y + 4, "NBA · 2026-10-20 · OKC @ SAS")
    return g.finish(height)


def player_scoring(g: Graphic) -> str:
    chart = g.facts["chart"]
    players, categories = chart["players"], chart["categories"]
    if len(players) != 2 or categories != ["two_point_points", "three_point_points", "free_throw_points"]:
        raise ValueError("Unsupported player-scoring schema")
    for player in players:
        expected = [2 * (player["fgm"] - player["tpm"]), 3 * player["tpm"], player["ftm"]]
        values = [player[key] for key in categories]
        if values != expected or sum(values) != player["points"] or any(value < 0 for value in values):
            raise ValueError(f"Inconsistent scoring arithmetic for {player['name']}")
    ui = g.labels["labels"]
    y = g.header(g.labels["footer"])
    start, end, maximum = 76, 884, 30
    for player in players:
        g.text(start, y + 34, player["name"], size=34, weight=700)
        g.text(end, y + 34, f'{ui["total"]}: {player["points"]}', size=33, weight=700, anchor="end", color=TEAL)
        y += 59
        current = start
        g.rect(start, y, end - start, 68, "#EEF3F6", radius=0)
        for key, color in zip(categories, (TEAL, BLUE, GOLD)):
            value = player[key]
            width = (end - start) * value / maximum
            if width:
                g.rect(current, y, width, 68, color)
                g.text(current + width / 2, y + 46, str(value), size=32, weight=700, anchor="middle", color=INK if color == GOLD else "#FFFFFF")
            current += width
        zeroes = [key for key in categories if player[key] == 0]
        if zeroes:
            g.block(start, y + 78, end - start, " · ".join(f"{ui[key]}: 0" for key in zeroes), size=23, color=MUTED)
        y += 134
    axis_y = y - 22
    g.line(start, axis_y, end, axis_y, color=MUTED)
    for tick in range(0, maximum + 1, 5):
        x = start + (end - start) * tick / maximum
        g.line(x, axis_y, x, axis_y + 9, color=MUTED)
        g.text(x, axis_y + 39, str(tick), size=23, anchor="middle", color=MUTED)
    g.text((start + end) / 2, axis_y + 77, ui["points"], size=25, anchor="middle", color=MUTED)
    y = axis_y + 115
    for key, color in zip(categories, (TEAL, BLUE, GOLD)):
        g.rect(start, y + 6, 23, 23, color, radius=3)
        y = g.block(start + 41, y, end - start - 41, ui[key], size=27) + 15
    return g.finish(g.footer(y + 10, g.labels["footer"]))


def chance_comparison(g: Graphic) -> str:
    chart = g.facts["chart"]
    facts = g.facts["facts"]
    values = {metric["key"]: metric["value"] for metric in chart["metrics"]}
    if values != {"goals": facts["goals"], "xg": facts["xg"]} or facts["matches"] != 6:
        raise ValueError("Chance comparison must match the reviewed six-match window")
    ui = g.labels["labels"]
    y = g.header(ui["period"] + " · 2026/27 · 2026-10-16")
    start, end, maximum = 76, 884, 12
    for key, color in (("goals", TEAL), ("xg", "#9AAFC4")):
        y = g.block(start, y, end - start, ui[key], size=33, weight=700) + 20
        if key == "xg":
            y = g.block(start, y - 7, end - start, MODEL_LABEL[g.locale], size=24, color=MUTED) + 12
        g.rect(start, y, end - start, 72, "#F0F4F7")
        width = (end - start) * values[key] / maximum
        g.rect(start, y, width, 72, color)
        g.text(start + width - 17, y + 49, number(values[key], g.locale), size=38, weight=700, anchor="end", color="#FFFFFF" if key == "goals" else INK)
        y += 118
    g.line(start, y, end, y, color=MUTED)
    for tick in range(0, maximum + 1, 2):
        x = start + (end - start) * tick / maximum
        g.line(x, y, x, y + 9, color=MUTED)
        g.text(x, y + 40, str(tick), size=24, anchor="middle", color=MUTED)
    y = g.block(start, y + 68, end - start, ui["axis"], size=25, color=MUTED) + 37
    return g.finish(g.footer(y, ui["source"] + " · Opta"))


def score_timeline(g: Graphic) -> str:
    # The EPL author supplies a reviewed event schema; accept no inferred times.
    chart = g.facts["chart"]
    checkpoints = [point for point in chart["milestones"] if point["key"] != "kickoff"]
    if not isinstance(checkpoints, list) or len(checkpoints) != 4:
        raise ValueError("Score timeline requires the four reviewed score checkpoints")
    ui = g.labels["labels"]
    if [point["key"] for point in checkpoints] != ["halftime", "first_goal", "second_goal", "fulltime"]:
        raise ValueError("Timeline must use half-time, both goals and full-time")
    if checkpoints[-1]["minute"] is not None:
        raise ValueError("Unverified full-time elapsed time must remain unset")
    final = g.facts["facts"]["final_score"]
    if {key: checkpoints[-1][key] for key in ("home", "away")} != final:
        raise ValueError("Final-score checkpoint does not match evidence")
    y = g.header("2026-10-17 · Premier League")
    g.text(141, y + 27, ui["axis"], size=25, color=MUTED)
    g.text(600, y + 27, ui["home"], size=27, weight=700, anchor="middle")
    g.text(820, y + 27, ui["away"], size=27, weight=700, anchor="middle", color=BLUE)
    start_y = y + 87
    g.line(100, start_y + 15, 100, start_y + 3 * 130 + 15, color=LINE, width=5)
    for i, point in enumerate(checkpoints):
        row = start_y + i * 130
        time_key = point.get("key", point.get("label", ""))
        time_label = ui.get(time_key, point.get("time", time_key))
        home = point.get("home_score", point.get("home"))
        away = point.get("away_score", point.get("away"))
        if not isinstance(home, int) or not isinstance(away, int):
            raise ValueError("Timeline checkpoint needs integer home and away scores")
        g.elements.append(f'<circle cx="100" cy="{row+15}" r="12" fill="{TEAL}" stroke="#FFFFFF" stroke-width="4"/>')
        g.text(141, row + 27, str(time_label), size=31, weight=700, color=MUTED)
        g.text(600, row + 34, str(home), size=57, weight=700, anchor="middle")
        g.text(710, row + 28, "–", size=33, anchor="middle", color=MUTED)
        g.text(820, row + 34, str(away), size=57, weight=700, anchor="middle", color=BLUE)
        detail = g.labels.get("events", {}).get(time_key, "")
        if detail:
            g.block(141, row + 51, 678, detail, size=27)
    y = start_y + 4 * 130 - 12
    return g.finish(g.footer(y, ui["source"]))


def render_group(group: str, args) -> list[Path]:
    evidence = Path(args.evidence)
    facts = load(evidence / f"{group}.json")
    if facts["translation_group"] != group:
        raise ValueError("Evidence group does not match filename")
    raw_labels = load(evidence / f"{group}-chart-labels.json")
    languages = raw_labels.get("languages", raw_labels)
    if set(languages) != set(LOCALES):
        raise ValueError(f"{group}: expected exactly the eight selected languages")
    kind = facts["chart"]["type"]
    renderers = {"watch_points_diagram": watch_points, "stacked_bar": player_scoring,
                 "bar_comparison": chance_comparison, "score_timeline": score_timeline,
                 "timeline": score_timeline, "score_event_timeline": score_timeline}
    if kind not in renderers:
        raise ValueError(f"Unsupported reviewed chart type: {kind}")
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    result = []
    for locale in LOCALES:
        labels = languages[locale]
        font = Path(args.font_hi if locale == "hi" else args.font_cjk if locale in {"ko", "ja"} else args.font_latin)
        graphic = Graphic(locale, labels, facts, font)
        svg = renderers[kind](graphic)
        filename = f"{group}-{locale.lower()}.svg"
        target = output / filename
        target.write_text(svg, encoding="utf-8")
        result.append(target)
        if args.attach:
            candidates = []
            for path in Path(args.content).glob("*.json"):
                article = load(path)
                if article.get("translation_group") == group and article.get("language", "").lower() == locale.lower():
                    candidates.append((path, article))
            if len(candidates) != 1:
                raise ValueError(f"Expected one completed article for {group}/{locale}; got {len(candidates)}")
            path, article = candidates[0]
            article["figures"] = [{"src": f"{args.base_url.rstrip('/')}/assets/charts/{filename}",
                                   "alt": labels["alt"], "caption": labels["caption"]}]
            path.write_text(json.dumps(article, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", default=ROOT / "experiment" / "evidence", type=Path)
    parser.add_argument("--content", default=ROOT / "content", type=Path)
    parser.add_argument("--out", default=ROOT / "assets" / "charts", type=Path)
    parser.add_argument("--group", action="append", help="Render only this completed translation group")
    parser.add_argument("--base-url", default="https://atin84.github.io")
    parser.add_argument("--font-latin", required=True, type=Path)
    parser.add_argument("--font-cjk", required=True, type=Path)
    parser.add_argument("--font-hi", required=True, type=Path)
    parser.add_argument("--attach", action="store_true", help="Attach figures to completed article JSONs")
    args = parser.parse_args()
    groups = args.group or sorted(path.name.removesuffix("-chart-labels.json") for path in args.evidence.glob("*-chart-labels.json"))
    paths = [path for group in groups for path in render_group(group, args)]
    print(f"Rendered {len(paths)} verified-data SVG files across {len(groups)} article groups.")


if __name__ == "__main__":
    main()
