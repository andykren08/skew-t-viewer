#!/usr/bin/env python3
"""Mirror the newest PSU BUFKIT files for a few stations and models into a
folder that GitHub Pages serves next to the viewer.

Usage:  python3 scripts/fetch_bufkit.py site/data

PSU keeps one file per model run hour (e.g. .../GFS/00/gfs3_krdu.buf), so the
newest run is found by probing the recent run hours and comparing the
initialization time written inside each file.
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

BASE = os.environ.get("BUFKIT_BASE", "https://www.meteo.psu.edu/bufkit/data")
STATIONS = ["KRDU", "KGSO", "KINT", "KFAY", "KRWI", "KGSB", "KIXA", "KRCZ", "FFC", "KATL", "KAVL", "KCLT", "KDAN", "KBLF", "KLWB", "KLYH", "KROA"]

# dir/prefix: PSU folder and file prefix. step: hours between runs.
# lookback: how many hours back to look for a run (keeps requests to PSU small).
MODELS = {
    "GFS":  {"dir": "GFS",  "prefix": "gfs3", "step": 6, "lookback": 18},
    "RAP":  {"dir": "RAP",  "prefix": "rap",  "step": 1, "lookback": 6},
    "HRRR": {"dir": "HRRR", "prefix": "hrrr", "step": 1, "lookback": 6},
    "RRFS": {"dir": "RRFS", "prefix": "rrfs", "step": 6, "lookback": 18},
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


def main():
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "site/data")
    now = dt.datetime.now(dt.timezone.utc)
    manifest = {"updated": now.isoformat(timespec="minutes"),
                "stations": STATIONS, "models": {}}

    for name, cfg in MODELS.items():
        def url(hh, stn, cfg=cfg):
            return f"{BASE}/{cfg['dir']}/{hh:02d}/{cfg['prefix']}_{stn.lower()}.buf"

        hours = []
        for back in range(cfg["lookback"] + 1):
            h = (now - dt.timedelta(hours=back)).hour
            if h % cfg["step"] == 0 and h not in hours:
                hours.append(h)

        best = None
        for hh in hours:
            txt = get(url(hh, STATIONS[0]))
            t = init_time(txt)
            print(f"{name} {hh:02d}Z probe: {'init ' + t.isoformat() if t else 'none'}")
            if t and (best is None or t > best[0]):
                best = (t, hh, txt)
        if best is None:
            print(f"WARNING: no data found for {name}", file=sys.stderr)
            continue

        t, hh, first = best
        (out / name).mkdir(parents=True, exist_ok=True)
        got = []
        for stn in STATIONS:
            txt = first if stn == STATIONS[0] else get(url(hh, stn))
            if init_time(txt) != t:
                print(f"WARNING: {name} {stn} missing or from a different run", file=sys.stderr)
                continue
            (out / name / f"{stn}.buf").write_text(txt, encoding="utf-8")
            got.append(stn)
            time.sleep(0.5)
        manifest["models"][name] = {"init": t.isoformat(), "hour": f"{hh:02d}", "stations": got}
        print(f"{name}: {t.isoformat()} -> {len(got)}/{len(STATIONS)} stations")

    if not manifest["models"]:
        sys.exit("No data downloaded; not publishing so the existing site stays as it is.")
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
