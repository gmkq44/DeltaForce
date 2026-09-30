#!/usr/bin/env python3
"""Fetch today's Delta Force map passwords and write data.json.

Primary source: tmini.net (text, includes location notes and images).
Fallback: kkrb.net (JSON, passwords only).
Yesterday's codes are carried over from the previous data.json.
"""
import http.cookiejar
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data.json"
CST = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

MAP_IDS = {
    "AZ3核电站": "az3_nuclear",
    "零号大坝": "zero_dam",
    "长弓溪谷": "longbow_creek",
    "巴克什": "bakhesh",
    "航天基地": "space_base",
    "潮汐监狱": "tide_prison",
    "AZ3彩六联动房": "az3_r6",
}
KKRB_KEYS = {"az3": "AZ3核电站", "db": "零号大坝", "cgxg": "长弓溪谷", "bks": "巴克什",
             "htjd": "航天基地", "cxjy": "潮汐监狱", "az3r6": "AZ3彩六联动房"}


def fetch_tmini():
    req = urllib.request.Request("https://www.tmini.net/api/sjzmm?ckey=&type=", headers={"User-Agent": UA})
    text = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
    maps = []
    for block in text.split("地图名称:")[1:]:
        name = block.splitlines()[0].strip()
        code = re.search(r"密码:\s*(\d{4})", block)
        if not name or not code:
            continue
        desc = re.search(r"位置描述:\s*(.*)", block)
        maps.append({
            "mapName": name,
            "code": code.group(1),
            "desc": desc.group(1).strip() if desc else "",
            "images": re.findall(r"图\d+:\s*(https?://\S+)", block),
        })
    return maps


def fetch_kkrb():
    base = "https://www.kkrb.net"
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    opener.addheaders = [("User-Agent", UA), ("Referer", base + "/"), ("Origin", base),
                         ("X-Requested-With", "XMLHttpRequest")]
    opener.open(base + "/", timeout=20)
    opener.open(urllib.request.Request(base + "/getMenu", data=b"globalData=false"), timeout=20)
    res = json.loads(opener.open(urllib.request.Request(base + "/getBonusDoorData", data=b""), timeout=20).read())
    if res.get("code") != 1:
        raise RuntimeError(res.get("msg", "kkrb error"))
    return [{"mapName": KKRB_KEYS.get(k, k), "code": str(v.get("password", "")), "desc": "", "images": []}
            for k, v in res["data"].items() if str(v.get("password", "")).isdigit()]


def main():
    maps, source, errors = [], None, []
    for name, fn in (("tmini", fetch_tmini), ("kkrb", fetch_kkrb)):
        try:
            maps = fn()
            if maps:
                source = name
                break
        except Exception as e:
            errors.append(f"{name}: {e}")
    if not maps:
        sys.exit("All sources failed: " + "; ".join(errors))

    today = datetime.now(CST).strftime("%Y-%m-%d")
    old = json.loads(DATA_FILE.read_text("utf-8")) if DATA_FILE.exists() else {}
    old_maps = {m["mapName"]: m for m in old.get("maps", [])}
    same_day = old.get("date") == today

    for m in maps:
        prev = old_maps.get(m["mapName"], {})
        m["id"] = MAP_IDS.get(m["mapName"], prev.get("id") or re.sub(r"\W", "_", m["mapName"]))
        # Same day: keep existing yesterday code; new day: yesterday = the old today
        m["yesterdayCode"] = prev.get("yesterdayCode", "") if same_day else prev.get("code", "")
        if not m["desc"]:
            m["desc"], m["images"] = prev.get("desc", ""), prev.get("images", [])

    if same_day and [(m["mapName"], m["code"]) for m in maps] == \
            [(m["mapName"], m["code"]) for m in old.get("maps", [])]:
        print("No change.")
        return

    data = {"date": today, "updatedAt": datetime.now(CST).isoformat(timespec="seconds"),
            "source": source, "maps": maps}
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"Updated {len(maps)} maps from {source} for {today}.")


if __name__ == "__main__":
    main()
