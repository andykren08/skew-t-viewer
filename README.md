BUFKIT Skew-T Viewer (GitHub Pages)
`index.html` is the viewer. A scheduled GitHub Action downloads the latest Iowa
State (IEM) BUFKIT files (GFS, RAP, HRRR, RRFS for the stations listed in
`scripts/fetch_bufkit.py`) and publishes them next to it, so the station and
model dropdowns work.
Data address pattern (one file per station and model, overwritten each run):
    https://meteor.geol.iastate.edu/data/bufkit/<folder>/<prefix>_<station>.buf

Model	folder	prefix	example
GFS	gfs	gfs3	.../gfs/gfs3_kgso.buf
RAP	rap	rap	.../rap/rap_kgso.buf
HRRR	hrrr	hrrr	.../hrrr/hrrr_kgso.buf
RRFS	rrfs	rrfs	.../rrfs/rrfs_kgso.buf
Setup
Create a GitHub repository and upload everything in this folder, with
`index.html` at the top level, `fetch_bufkit.py` in a `scripts` folder, and
`update.yml` in `.github/workflows`, to the `main` branch.
Repository Settings > Pages > Build and deployment > Source: GitHub Actions.
Open the Actions tab, choose "Update BUFKIT data and deploy", and click
Run workflow. When it finishes, the site is at
`https://<account>.github.io/<repo>/`.
After that it refreshes on the schedule in `.github/workflows/update.yml`.
Before relying on it
Only the HRRR address pattern has been confirmed in a browser. Open one link for
each of the other models and check it loads. If one is wrong, edit `MODELS` at
the top of `scripts/fetch_bufkit.py`. The Action log says which models were found.
The Action log shows a stale-data warning (a yellow annotation on the run) when
a model's newest run is older than expected, for example an HRRR more than 4
hours old. The "Init" time next to the dropdowns shows each file's run.
GFS and RRFS only change every 6 hours. When a model has no new run, its files
are copied from the live site instead of downloaded again.
GitHub schedules can start 10-30 minutes late.
A station a model doesn't carry is left out of that model's station list.
Pages sites are publicly readable. Check with NWS IT that github.com is allowed
and that hosting this there is acceptable, and with Iowa State that automated
hourly downloads are OK.
Changing stations or models
Edit `STATIONS` and `MODELS` in `scripts/fetch_bufkit.py`. The dropdowns follow
the generated `data/manifest.json`, so nothing changes in `index.html`.
Without the `data` folder, `index.html` still works by dragging in .buf files.
