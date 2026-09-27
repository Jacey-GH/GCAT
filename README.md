# GCAT ADR candidate screening dashboard

## Live Dashboard

[Open the GCAT ADR Candidate Screening Dashboard](https://izwmv46vbkko7kkomcbuaq.streamlit.app/)

This Streamlit app screens freely orbiting, large rocket stages from Jonathan
C. McDowell's General Catalog of Artificial Space Objects (GCAT).

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run adr_dashboard.py
```

## Required data

The app loads these two tab-separated GCAT object catalogs from `data/`:

- `data/satcat.tsv`
- `data/satcat100k.tsv`

They are included in this deployment folder so a hosted app does not depend on
the separate course dataset repository or on the process working directory.

Source: <https://planet4589.org/space/gcat/>
