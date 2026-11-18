#!/usr/bin/env python3
"""Mirror the latest few Iowa State (IEM) BUFKIT runs for a list of stations and
models into a folder that GitHub Pages serves next to the viewer.

Usage:  python3 scripts/fetch_bufkit.py site/data

Sources
  newest run : https://meteor.geol.iastate.edu/data/bufkit/<folder>/<prefix>_<stn>.buf
               (overwritten with every run; the run time is read from inside the file)
  older runs : https://mtarchive.geol.iastate.edu/YYYY/MM/DD/bufkit/HH/<folder>/<prefix>_<stn>.buf

Output
  data/<MODEL>/<YYYYMMDDHH>/<STN>.buf.gz   one gzip file per station and run
  data/manifest.json                       the runs and stations the viewer offers

Runs already published on the live site (PAGES_URL) are copied from there, so
in a normal hour only the one new run is downloaded from Iowa State.
"""
import datetime as dt
import gzip
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("BUFKIT_BASE", "https://meteor.geol.iastate.edu/data/bufkit")
ARCHIVE = os.environ.get("BUFKIT_ARCHIVE", "https://mtarchive.geol.iastate.edu").rstrip("/")
KEEP = int(os.environ.get("BUFKIT_KEEP_RUNS", "3"))   # runs kept per model

# Raleigh first, then the rest. A station a model doesn't carry is skipped.
STATIONS = [
    "KGSO", "KINT", "KRDU", "KFAY", "KRWI",
    "KIXA", "KGSB", "KRCZ", "KISO", "KPGV",
    "KCLT", "KHKY", "KTNB", "KAVL", "KLBT",
    "KDAN", "KLYH", "KROA", "KLWB", "KBLF",
    "KFLO", "KMYR", "KILM", "KMHX", "KOAJ",
]

# Base address of the published site, set by the workflow. Files already there
# are copied instead of downloaded again.
PAGES_URL = os.environ.get("PAGES_URL", "").rstrip("/")

# dir/prefix: folder and file prefix on the server. step: hours between runs.
# max_age: hours since the newest run's initialization before the Action log
# shows a stale-data warning.
MODELS = {
    "GFS":  {"dir": "gfs",  "prefix": "gfs3", "step": 6, "max_age": 14},
    "RAP":  {"dir": "rap",  "prefix": "rap",  "step": 1, "max_age": 4},
    "HRRR": {"dir": "hrrr", "prefix": "hrrr", "step": 1, "max_age": 4},
    "RRFS": {"dir": "rrfs", "prefix": "rrfs", "step": 6, "max_age": 14},
}

UA = "NWS-RAH-bufkit-viewer/1.0 (GitHub Actions mirror)"
TIME_RE = re.compile(r"TIME\s*=\s*(\d{2})(\d{2})(\d{2})/(\d{2})(\d{2})")


def get_bytes(url, tries=3):
    err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            err = e
        except Exception as e:  # network trouble: retry
            err = e
        time.sleep(2 * (i + 1))
    print(f"  ! {url}: {err}", file=sys.stderr)
    return None


def get_text(url, tries=3):
    b = get_bytes(url, tries)
    return b.decode("utf-8", "replace") if b is not None else None


def unpack(data):
    try:
        return gzip.decompress(data).decode("utf-8", "replace")
    except Exception:
        return None


def pack(txt):
    return gzip.compress(txt.encode("utf-8"), 9, mtime=0)


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


def run_id(t):
    return t.strftime("%Y%m%d%H")


def fetch_model(name, cfg, out, old, now):
    def latest_url(stn):
        return f"{BASE}/{cfg['dir']}/{cfg['prefix']}_{stn.lower()}.buf"

    def archive_url(stn, t):
        return (f"{ARCHIVE}/{t:%Y/%m/%d}/bufkit/{t:%H}/{cfg['dir']}/"
                f"{cfg['prefix']}_{stn.lower()}.buf")

    # 1. The newest run: the first station that answers on the "latest" address.
    probe_stn = probe_txt = t0 = None
    for stn in STATIONS:
        txt = get_text(latest_url(stn))
        if init_time(txt):
            probe_stn, probe_txt, t0 = stn, txt, init_time(txt)
            break
    if t0 is None:
        print(f"WARNING: no data found for {name}", file=sys.stderr)
        return None

    age = (now - t0).total_seconds() / 3600
    if age > cfg["max_age"]:
        print(f"::warning::{name} data looks stale: newest run {t0:%Y-%m-%d %H:%M}Z is {age:.0f} h old")

    # 2. The newest run and the previous ones, one folder per run.
    runs, reused, fetched = [], 0, 0
    for k in range(KEEP):
        t = t0 - dt.timedelta(hours=k * cfg["step"])
        rid = run_id(t)
        have = set(old.get(rid, []))
        folder = out / name / rid
        folder.mkdir(parents=True, exist_ok=True)
        done, misses = [], 0
        for stn in STATIONS:
            data = None
            if PAGES_URL and stn in have:
                b = get_bytes(f"{PAGES_URL}/data/{name}/{rid}/{stn}.buf.gz", tries=1)
                if b is not None and init_time(unpack(b)) == t:
                    data, reused = b, reused + 1
            if data is None:
                if k == 0 and stn == probe_stn:
                    txt = probe_txt
                else:
                    txt = get_text(latest_url(stn) if k == 0 else archive_url(stn, t))
                    time.sleep(0.3)
                    fetched += 1
                if init_time(txt) != t:
                    if k == 0:
                        print(f"WARNING: {name} {stn} missing or from a different run", file=sys.stderr)
                    elif not done:   # an archived run that isn't there: stop after two misses
                        misses += 1
                        if misses >= 2:
                            break
                    continue
                data = pack(txt)
            (folder / f"{stn}.buf.gz").write_bytes(data)
            done.append(stn)
        if done:
            runs.append({"id": rid, "init": t.isoformat(), "stations": done})
        else:
            folder.rmdir()
            print(f"WARNING: {name} run {rid} not available", file=sys.stderr)

    print(f"{name}: newest {t0:%Y-%m-%d %H:%M}Z, runs kept: "
          + ", ".join(f"{r['id'][-2:]}Z({len(r['stations'])})" for r in runs)
          + f"; {fetched} downloaded, {reused} reused from live site")
    return {"init": runs[0]["init"], "stations": runs[0]["stations"], "runs": runs}


def main():
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "site/data")
    now = dt.datetime.now(dt.timezone.utc)
    manifest = {"updated": now.isoformat(timespec="minutes"), "stations": STATIONS, "models": {}}

    prev = {}
    if PAGES_URL:
        try:
            m = json.loads(get_text(f"{PAGES_URL}/data/manifest.json", tries=1) or "{}")
            for name, mi in m.get("models", {}).items():
                prev[name] = {r["id"]: r["stations"] for r in mi.get("runs", [])}
        except Exception:
            prev = {}

    for name, cfg in MODELS.items():
        res = fetch_model(name, cfg, out, prev.get(name, {}), now)
        if res and res["runs"]:
            manifest["models"][name] = res

    if not manifest["models"]:
        sys.exit("No data downloaded; not publishing so the existing site stays as it is.")
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
