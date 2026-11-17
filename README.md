# BUFKIT Skew-T Viewer (GitHub Pages)

`index.html` is the viewer. A scheduled GitHub Action downloads the newest PSU
BUFKIT files (GFS, RAP, HRRR, RRFS for KRDU, KGSO, KINT, KFAY, KRWI) and
publishes them next to it, so the station and model dropdowns work.

## Setup

1. Create a GitHub repository and upload everything in this folder, including the
   hidden `.github` folder, to the `main` branch.
2. Repository **Settings > Pages > Build and deployment > Source: GitHub Actions**.
3. Open the **Actions** tab, choose "Update BUFKIT data and deploy", and click
   **Run workflow**. When it finishes, the site is at
   `https://<account>.github.io/<repo>/`.
4. After that it refreshes on the schedule in `.github/workflows/update.yml`.

## Before relying on it

- Open one file link for each model in a browser to confirm the address pattern,
  for example `https://www.meteo.psu.edu/bufkit/data/RAP/12/rap_krdu.buf`.
  The GFS (`GFS/00/gfs3_krdu.buf`) and RRFS (`RRFS/06/rrfs_krdu.buf`) patterns were
  confirmed; the RAP and HRRR folder and file names are assumed. If one is wrong, edit `MODELS` at the top of
  `scripts/fetch_bufkit.py`. The Action log says which models were found.
- GitHub schedules can start 10-30 minutes late.
- A model that PSU doesn't have on a given run is simply left out of the dropdown
  until a later run finds it.
- Pages sites are publicly readable. Check with NWS IT that github.com is allowed
  and that hosting this there is acceptable, and with PSU that automated hourly
  downloads are OK.

## Changing stations or models

Edit `STATIONS` and `MODELS` in `scripts/fetch_bufkit.py`. The dropdowns follow
the generated `data/manifest.json`, so nothing changes in `index.html`.

Without the `data` folder, `index.html` still works by dragging in .buf files.
