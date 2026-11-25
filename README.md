# Which National Park?

A standalone 10-choice national parks photo quiz. Open `index.html` in a browser. The quiz uses `parks-data.js` and the local pictures in `images/`; `park-photos.js` maps each park to its saved picture and NPS source page.

Questions are shuffled from the parks with a saved photo. Correct answers earn the current streak number multiplied by the whole seconds remaining on the 15-second timer. A wrong answer or timeout ends the run. The top-ten score list is stored in the current browser.

The visitor ranking uses 2025 National Park Service recreation visits, from the [NPS Visitor Use Statistics program](https://home.nps.gov/subjects/socialscience/visitor-use-statistics-dashboard.htm). Images are downloaded from each park's official NPS homepage; the quiz links to that page for source and image credit. If refreshing the pack, run `python3 download_nps_photos.py` from this folder.

For GitHub Pages, upload the files in this folder with `index.html` at the repository root. Keep `park-photos.js` and the `images` folder alongside it.
