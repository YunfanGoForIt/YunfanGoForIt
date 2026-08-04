#!/usr/bin/env python3
"""Generate editorial-style SVG cards for the GitHub profile README."""

from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ASSETS = REPO / "assets"
README = REPO / "README.md"
FONTS = HERE / "fonts"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def b64_font(weight: str) -> str:
    path = FONTS / f"outfit-{weight}.woff2"
    return base64.b64encode(path.read_bytes()).decode("ascii")


def font_css() -> str:
    faces = []
    for weight in (400, 500, 700, 900):
        faces.append(
            f"@font-face{{font-family:'Outfit';font-weight:{weight};"
            f"src:url(data:font/woff2;base64,{b64_font(str(weight))}) format('woff2');}}"
        )
    return "\n".join(faces)


BG = "#0d1117"
INK = "#e6edf3"
MUTE = "#7d8590"
HAIR = "#21262d"
ACCENT = "#70a5fd"
STAR = "M6 0l1.85 3.78 4.17.61-3.02 2.94.71 4.16L6 9.45l-3.71 2.04.71-4.16L-.02 4.39l4.17-.61z"


def chrome(w: int, h: int) -> str:
    return f"""
  <defs>
    <radialGradient id="glowA" cx="8%" cy="0%" r="90%">
      <stop offset="0%" stop-color="{ACCENT}" stop-opacity="0.10"/>
      <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowB" cx="100%" cy="115%" r="80%">
      <stop offset="0%" stop-color="#f778ba" stop-opacity="0.06"/>
      <stop offset="100%" stop-color="#f778ba" stop-opacity="0"/>
    </radialGradient>
    <clipPath id="card"><rect width="{w}" height="{h}" rx="12"/></clipPath>
  </defs>
  <rect width="{w}" height="{h}" rx="12" fill="{BG}"/>
  <rect width="{w}" height="{h}" rx="12" fill="url(#glowA)"/>
  <rect width="{w}" height="{h}" rx="12" fill="url(#glowB)"/>
  <rect width="{w}" height="{h}" rx="12" fill="none" stroke="#30363d" stroke-width="1"/>
"""


def longest_streak(days: list[tuple[str, int]]) -> int:
    longest = cur = 0
    for _, c in sorted(days):
        cur = cur + 1 if c > 0 else 0
        longest = max(longest, cur)
    return longest


def language_stats(repos: list[dict]) -> list[tuple[str, float, str]]:
    agg: dict[str, int] = {}
    colors: dict[str, str] = {}
    for r in repos:
        for e in r.get("languages", {}).get("edges", []) or []:
            n = e["node"]["name"]
            agg[n] = agg.get(n, 0) + e["size"]
            colors[n] = e["node"].get("color") or "#30363d"
    total = sum(agg.values())
    if total <= 0:
        return [("Other", 100.0, "#30363d")]
    top = sorted(agg.items(), key=lambda x: -x[1])[:5]
    top_pct = [(n, s / total * 100, colors[n]) for n, s in top]
    other = 100 - sum(p for _, p, _ in top_pct)
    if other > 0.5:
        top_pct.append(("Other", other, "#30363d"))
    return top_pct


def write_metrics(data: dict) -> Path:
    repos = data["repositories"]["nodes"]
    total_stars = sum(r["stargazerCount"] for r in repos)
    total_contribs = data["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    n_repos = data["repositories"]["totalCount"]
    days = [
        (x["date"], x["contributionCount"])
        for w in data["contributionsCollection"]["contributionCalendar"]["weeks"]
        for x in w["contributionDays"]
    ]
    streak = longest_streak(days)
    segs = language_stats(repos)

    w, h = 880, 224
    stats = [
        (str(total_stars), "TOTAL STARS"),
        (str(total_contribs), "CONTRIBUTIONS · 12M"),
        (f"{streak}d", "LONGEST STREAK"),
        (str(n_repos), "REPOSITORIES"),
    ]
    cell_w = w / 4
    css = font_css()
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f"<style>{css}</style>",
        chrome(w, h),
    ]

    for i, (num, label) in enumerate(stats):
        cx = cell_w * i + cell_w / 2
        if i > 0:
            parts.append(
                f'<line x1="{cell_w * i}" y1="32" x2="{cell_w * i}" y2="120" stroke="{HAIR}" stroke-width="1"/>'
            )
        parts.append(f'<rect x="{cx - 10}" y="34" width="20" height="2" fill="{ACCENT}" opacity="0.85"/>')
        parts.append(
            f'<text x="{cx}" y="88" text-anchor="middle" font-family="Outfit" font-weight="900" font-size="46" fill="{INK}">{num}</text>'
        )
        parts.append(
            f'<text x="{cx}" y="114" text-anchor="middle" font-family="Outfit" font-weight="500" font-size="10" letter-spacing="3" fill="{MUTE}">{label}</text>'
        )

    parts.append(f'<line x1="24" y1="140" x2="{w - 24}" y2="140" stroke="{HAIR}" stroke-width="1"/>')
    parts.append(
        f'<text x="24" y="164" font-family="Outfit" font-weight="500" font-size="10" letter-spacing="3" fill="{MUTE}">MOST USED LANGUAGES</text>'
    )

    bar_x, bar_y, bar_w, bar_h = 24, 176, w - 48, 8
    x = bar_x
    bar_parts = []
    for _, p, c in segs:
        wseg = bar_w * p / 100
        bar_parts.append(f'<rect x="{x:.1f}" y="{bar_y}" width="{wseg:.1f}" height="{bar_h}" fill="{c}"/>')
        x += wseg
    parts.append(
        f'<clipPath id="barClip"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="4"/></clipPath>'
    )
    parts.append(f'<g clip-path="url(#barClip)">{"".join(bar_parts)}</g>')

    slot = bar_w / len(segs)
    for i, (n, p, c) in enumerate(segs):
        cx = bar_x + slot * i
        parts.append(f'<circle cx="{cx + 3}" cy="{bar_y + bar_h + 14}" r="3" fill="{c}"/>')
        parts.append(
            f'<text x="{cx + 11}" y="{bar_y + bar_h + 17.5}" font-family="Outfit" font-weight="400" font-size="10.5" fill="{MUTE}">{n} {p:.0f}%</text>'
        )
    parts.append("</svg>")

    out = ASSETS / "metrics.svg"
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


def write_projects(data: dict, featured: list[dict]) -> Path:
    by_name = {r["name"]: r for r in data["repositories"]["nodes"]}
    projects = []
    for item in featured:
        name = item["name"]
        repo = by_name.get(name, {})
        primary = repo.get("primaryLanguage") or {}
        projects.append(
            (
                name,
                item["description"],
                primary.get("name") or item.get("language") or "Other",
                primary.get("color") or item.get("color") or "#30363d",
                int(repo.get("stargazerCount") or 0),
            )
        )

    w, cell_h = 880, 96
    h = cell_h * 2 + 2
    css = font_css()
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f"<style>{css}</style>",
        chrome(w, h),
    ]
    cw = w / 2
    parts.append(f'<line x1="{cw}" y1="20" x2="{cw}" y2="{h - 20}" stroke="{HAIR}" stroke-width="1"/>')
    parts.append(
        f'<line x1="24" y1="{cell_h + 1}" x2="{w - 24}" y2="{cell_h + 1}" stroke="{HAIR}" stroke-width="1"/>'
    )

    for i, (name, desc, lang, lcolor, stars) in enumerate(projects):
        col, row = i % 2, i // 2
        ox, oy = col * cw, row * (cell_h + 1)
        tx, ty = ox + 28, oy + 36
        parts.append(
            f'<text x="{tx}" y="{ty}" font-family="Outfit" font-weight="700" font-size="17" fill="{INK}">{name}</text>'
        )
        if stars:
            sx = tx + len(name) * 10.5 + 16
            parts.append(
                f'<g transform="translate({sx},{ty - 11}) scale(1.05)"><path d="{STAR}" fill="{ACCENT}"/></g>'
            )
            parts.append(
                f'<text x="{sx + 15}" y="{ty}" font-family="Outfit" font-weight="500" font-size="12" fill="{MUTE}">{stars}</text>'
            )
        parts.append(
            f'<text x="{tx}" y="{ty + 24}" font-family="Outfit" font-weight="400" font-size="12.5" fill="{MUTE}">{desc}</text>'
        )
        parts.append(f'<circle cx="{tx + 4}" cy="{ty + 47}" r="4" fill="{lcolor}"/>')
        parts.append(
            f'<text x="{tx + 15}" y="{ty + 51}" font-family="Outfit" font-weight="500" font-size="11" letter-spacing="1.5" fill="{MUTE}">{lang.upper()}</text>'
        )
    parts.append("</svg>")

    out = ASSETS / "projects.svg"
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


def bump_readme_cache() -> None:
    if not README.exists():
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    text = README.read_text(encoding="utf-8")
    updated = re.sub(
        r"(assets/(?:metrics|projects)\.svg)\?v=[^\"'\s]+",
        rf"\1?v={stamp}",
        text,
    )
    if updated != text:
        README.write_text(updated, encoding="utf-8")
        print(f"README cache-bust → ?v={stamp}")


def main() -> None:
    data_path = HERE / "data.json"
    if not data_path.exists():
        raise SystemExit(f"Missing {data_path}; run fetch_data.py first")

    data = load_json(data_path)
    featured = load_json(HERE / "featured.json")
    ASSETS.mkdir(parents=True, exist_ok=True)

    m = write_metrics(data)
    p = write_projects(data, featured)
    bump_readme_cache()
    print(f"Wrote {m.relative_to(REPO)} + {p.relative_to(REPO)}")


if __name__ == "__main__":
    main()
