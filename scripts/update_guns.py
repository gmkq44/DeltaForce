#!/usr/bin/env python3
"""Fetch community gun build codes (改枪码) from g.aitags.cn and write guns.json.

Codes are created in-game and only go stale after game updates, so this runs weekly.
For each weapon the newest builds are kept.
"""
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "guns.json"
CST = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
BASE = "https://g.aitags.cn/weapons/"
PER_WEAPON = 3

# slug -> (display name, category)
WEAPONS = {
    "m4a1": ("M4A1 突击步枪", "rifle"),
    "tenglong": ("腾龙 突击步枪", "rifle"),
    "k416": ("K416 突击步枪", "rifle"),
    "akm": ("AKM 突击步枪", "rifle"),
    "ak-12": ("AK-12 突击步枪", "rifle"),
    "aug": ("AUG 突击步枪", "rifle"),
    "mp5": ("MP5 冲锋枪", "smg"),
    "mp7": ("MP7 冲锋枪", "smg"),
    "p90": ("P90 冲锋枪", "smg"),
    "uzi": ("UZI 冲锋枪", "smg"),
    "vector": ("Vector 冲锋枪", "smg"),
    "sr-25": ("SR-25 射手步枪", "marksman"),
    "awm": ("AWM 狙击步枪", "sniper"),
}

CODE_RE = re.compile(r"((?:[^\s|]{2,20}-(?:烽火地带|全面战场)-)?[0-9A-Z]{18,25})")


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def fetch(slug):
    req = urllib.request.Request(BASE + slug, headers={"User-Agent": UA})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S)
    builds = []
    for i, row in enumerate(rows):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 4:
            continue
        m = CODE_RE.search(text(cells[0]))
        if not m:
            continue
        code = m.group(1)
        date = re.search(r"\d{4}-\d{2}-\d{2}", text(cells[3]))
        copies = re.search(r"\d{4}-\d{2}-\d{2}\s*(\d+)", text(cells[3]))
        image = None
        # The following row holds the attachment screenshot
        if i + 1 < len(rows):
            img = re.search(r'<img[^>]+src="([^"]+)"', rows[i + 1])
            image = img.group(1) if img else None
        desc, price = text(cells[1]), text(cells[2])
        mode = "全面战场" if "全面战场" in code + desc + price else "烽火地带"
        builds.append({
            "code": code,
            "mode": mode,
            "desc": re.sub(r"[（(]全面战场[)）]", "", desc).strip(),
            "price": price if re.fullmatch(r"[\d.]+\s*[Ww万]", price) else "",
            "date": date.group(0) if date else "",
            "copies": int(copies.group(1)) if copies else 0,
            "image": image,
        })
    return builds


def main():
    guns, errors = [], []
    for slug, (name, category) in WEAPONS.items():
        try:
            builds = fetch(slug)
        except Exception as e:
            errors.append(f"{slug}: {e}")
            continue
        builds.sort(key=lambda b: (b["date"], b["copies"]), reverse=True)
        for n, b in enumerate(builds[:PER_WEAPON], 1):
            guns.append({"id": f"{slug}-{n}", "name": name, "category": category,
                         "source": BASE + slug, **b})
    if errors:
        print("Warnings:", "; ".join(errors), file=sys.stderr)
    if not guns:
        sys.exit("No builds fetched.")
    data = {"updatedAt": datetime.now(CST).isoformat(timespec="seconds"),
            "source": "g.aitags.cn", "guns": guns}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"Wrote {len(guns)} builds for {len({g['name'] for g in guns})} weapons.")


if __name__ == "__main__":
    main()
