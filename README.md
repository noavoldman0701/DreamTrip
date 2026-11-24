# DreamTrip
A Python / Streamlit travel budget planner. Run from the project folder:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On Windows, `py` can replace `python`. Open the local URL printed in the terminal.

Run the tests:

```bash
python -m unittest test_planner.py
```

## Project structure

| File | Purpose |
|------|---------|
| `app.py` | Streamlit interface: Home, Explore, Compare and Budget pages |
| `ui.py` | Visual building blocks: custom styles, logo, hero and page headers |
| `planner.py` | Destination data, exchange rates and cost calculations (no UI code) |
| `test_planner.py` | Unit tests for `planner.py` |
| `assets/style.css` | Custom look: fonts, colors, cards, sidebar menu |
| `assets/logo.svg` | DreamTrip logo |
| `assets/landmark.svg` | Line drawing used in the hero and the sidebar |
| `.streamlit/config.toml` | App color theme |

To use a photo in the Home banner, add `assets/hero.jpg` (or `.png` / `.webp`).
Without it, the line drawing is shown. Fonts load from Google Fonts when online.

Features: exact or flexible dates, category limits, 19 illustrative destinations across six regions, currency conversion via Frankfurter reference rates (manual fallback), cost comparison, maps, charts and external booking searches. All travel prices are illustrative USD assumptions, not live offers. Flight preferences, star ratings and hotel location are recorded but not verified or used to filter inventory. Flexible dates use the first feasible departure. No accounts, AI, or persistent storage. The UI uses Streamlit components with a custom CSS layer (`assets/style.css`). No destination photos are bundled. Booking links are search links, not verified offers. The exchange rates endpoint requires network access and is cached until restart.
