#!/usr/bin/env python3
"""Mirror the latest Iowa State (IEM) BUFKIT files for a list of stations and
models into a folder that GitHub Pages serves next to the viewer.

Usage:  python3 scripts/fetch_bufkit.py site/data

Iowa State keeps one file per station and model that is overwritten with every
new run, e.g.  https://meteor.geol.iastate.edu/data/bufkit/hrrr/hrrr_kgso.buf
so there is no run hour to guess. The initialization time is read from inside
each file instead, and written to data/manifest.json for the viewer.
"""
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("BUFKIT_BASE", "https://meteor.geol.iastate.edu/data/bufkit")

# Raleigh first (used to decide whether a model has a new run), then the rest.
# A station a model doesn't carry is skipped with a warning.
STATIONS = [
    "KRDU", "KGSO", "KINT", "KFAY", "KRWI",
    "KGSB", "KIXA", "KRCZ", "KECG", "KHAT",
    "KEWN", "KHKY", "KMHX", "KILM", "KSBY",
    "KOAJ", "KCLT", "KAVL", "KFVX", "KFLO",
    "KMYR", "KCHS", "KCAE", "KAGS", "KGSP",
    "KATL", "KTRI", "KISO", "KDAN", "KLYH",
    "KROA", "KBLF", "KLWB", "KPGV", "KSSC",
    "KCHO", "KIAD", "KORF", "KPHF",
]

# Base address of the published site, set by the workflow. When a model has no
# new run since the last deploy, its files are copied from the live site
# instead of being downloaded again.
PAGES_URL = os.environ.get("PAGES_URL", "").rstrip("/")

# folder / file prefix on the server, and how old (hours since initialization)
# the data may get before the Action log shows a stale-data warning.
MODELS = {
    "GFS":  {"dir": "gfs",  "prefix": "gfs3", "max_age": 14},
    "RAP":  {"dir": "rap",  "prefix": "rap",  "max_age": 4},
    "HRRR": {"dir": "hrrr", "prefix": "hrrr", "max_age": 4},
    "RRFS": {"dir": "rrfs", "prefix": "rrfs", "max_age": 14},
}

UA = "NWS-RAH-bufkit-viewer/1.0 (GitHub Actions mirror)"
TIME_RE = re.compile(r"TIME\s*=\s*(\d{2})(\d{2})(\d{2})/(\d{2})(\d{2})")


def get(url, tries=3):
    err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            err = e
        except Exception as e:  # network trouble: retry
            err = e
        time.sleep(2 * (i + 1))
    print(f"  ! {url}: {err}", file=sys.stderr)
    return None


def init_time(txt):
    """First TIME in a .buf file (the model initialization), or None if the
    text doesn't look like a BUFKIT file."""
    if not txt or "STID" not in txt:
        return None
    m = TIME_RE.search(txt)
    if not m:
        return None
    y, mo, d, h, mi = map(int, m.groups())
    return dt.datetime(2000 + y, mo, d, h, mi, tzinfo=dt.timezone.utc)


def fetch_model(name, cfg, out, old, now):
    def url(stn):
        return f"{BASE}/{cfg['dir']}/{cfg['prefix']}_{stn.lower()}.buf"

    prev = old.get(name, {}).get("inits", {})
    (out / name).mkdir(parents=True, exist_ok=True)
    inits, reused, reuse_ok = {}, 0, None   # reuse_ok: decided by the first station

    for stn in STATIONS:
        txt = None
        if reuse_ok and stn in prev:
            live = get(f"{PAGES_URL}/data/{name}/{stn}.buf", tries=1)
            lt = init_time(live)
            if lt and lt.isoformat() == prev[stn]:
                txt, reused = live, reused + 1
        if txt is None:
            txt = get(url(stn))
            time.sleep(0.3)
        t = init_time(txt)
        if t is None:
            print(f"WARNING: {name} {stn} missing", file=sys.stderr)
            continue
        (out / name / f"{stn}.buf").write_text(txt, encoding="utf-8")
        inits[stn] = t.isoformat()
        if reuse_ok is None:
            reuse_ok = bool(PAGES_URL) and prev.get(stn) == t.isoformat()

    if not inits:
        print(f"WARNING: no data found for {name}", file=sys.stderr)
        return None

    newest = max(dt.datetime.fromisoformat(v) for v in inits.values())
    age = (now - newest).total_seconds() / 3600
    if age > cfg["max_age"]:
        print(f"::warning::{name} data looks stale: newest run {newest:%Y-%m-%d %H:%M}Z is {age:.0f} h old")
    print(f"{name}: newest run {newest:%Y-%m-%d %H:%M}Z -> {len(inits)}/{len(STATIONS)} stations "
          f"({reused} reused from live site)")
    return {"init": newest.isoformat(), "inits": inits, "stations": list(inits)}


def main():
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "site/data")
    now = dt.datetime.now(dt.timezone.utc)
    manifest = {"updated": now.isoformat(timespec="minutes"), "stations": STATIONS, "models": {}}

    old = {}
    if PAGES_URL:
        try:
            old = json.loads(get(f"{PAGES_URL}/data/manifest.json", tries=1) or "{}").get("models", {})
        except Exception:
            old = {}

    for name, cfg in MODELS.items():
        res = fetch_model(name, cfg, out, old, now)
        if res:
            manifest["models"][name] = res

    if not manifest["models"]:
        sys.exit("No data downloaded; not publishing so the existing site stays as it is.")
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
