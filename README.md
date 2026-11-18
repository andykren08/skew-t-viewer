# BUFKIT Skew-T Viewer (GitHub Pages)

`index.html` is the viewer. A scheduled GitHub Action downloads the latest three
runs of each model (GFS, RAP, HRRR, RRFS) from Iowa State (IEM) for the stations
listed in `scripts/fetch_bufkit.py`, compresses them, and publishes them next to
the viewer. The station, model and **run** dropdowns then work.

## Where the data comes from

| Model | folder | prefix |
|-------|--------|--------|
| GFS   | gfs    | gfs3   |
| RAP   | rap    | rap    |
| HRRR  | hrrr   | hrrr   |
| RRFS  | rrfs   | rrfs   |

- Newest run: `https://meteor.geol.iastate.edu/data/bufkit/<folder>/<prefix>_<station>.buf`
  (overwritten with every run; the run time is read from inside the file).
- Older runs: `https://mtarchive.geol.iastate.edu/YYYY/MM/DD/bufkit/HH/<folder>/<prefix>_<station>.buf`

Published layout: `data/<MODEL>/<YYYYMMDDHH>/<STATION>.buf.gz` plus
`data/manifest.json` (the runs and stations the dropdowns offer).

## How it stays light

- Each hourly run copies runs that are already on the live site and only
  downloads what is new, normally one new run per model.
- GFS and RRFS only change every 6 hours, so most hours nothing is downloaded for
  them.
- Files are gzip-compressed (about 3x smaller). The page opens one file at a time.
- The first deploy downloads all three runs for every model and station, so it
  takes several minutes. Later runs are much shorter.
- To change how many runs are kept, edit the `3` in the `KEEP = ...` line near the
  top of `scripts/fetch_bufkit.py`.

## Setup

1. Create a GitHub repository and upload everything in this folder, with
   `index.html` at the top level, `fetch_bufkit.py` in a `scripts` folder, and
   `update.yml` in `.github/workflows`, to the `main` branch.
2. Repository **Settings > Pages > Build and deployment > Source: GitHub Actions**.
3. Open the **Actions** tab, choose "Update BUFKIT data and deploy", and click
   **Run workflow**. When it finishes, the site is at
   `https://<account>.github.io/<repo>/`.
4. After that it refreshes on the schedule in `.github/workflows/update.yml`.

## Notes

- The Action log shows a stale-data warning (a yellow annotation on the run) when
  a model's newest run is older than expected, for example an HRRR more than 4
  hours old.
- A run that Iowa State doesn't have (for example a missing archived run) is left
  out of the Run dropdown, with a warning in the log.
- A station a model doesn't carry is left out of that model's station list.
- GitHub schedules can start 10-30 minutes late.
- The data files are compressed, so a current Chrome, Edge, Firefox or Safari
  is needed. Dragging a plain .buf file into the page still works anywhere.
- Pages sites are publicly readable. Check with NWS IT that github.com is allowed
  and that hosting this there is acceptable, and with Iowa State that automated
  hourly downloads are OK.

## Changing stations or models

Edit `STATIONS` and `MODELS` in `scripts/fetch_bufkit.py`. The dropdowns follow
the generated `data/manifest.json`, so nothing changes in `index.html`.

Without the `data` folder, `index.html` still works by dragging in .buf files.
