"""Sortable ADR candidate table built from the GCAT object catalogs.

Run from this folder with::

    uv run streamlit run adr_dashboard.py
"""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from gcat_loader import load_gcat_objects


MASS_CUTOFF_KG = 5_000


@st.cache_data(show_spinner="Loading GCAT object catalogs…")
def load_objects() -> pd.DataFrame:
    """Load the combined GCAT catalogs once per Streamlit session."""
    return load_gcat_objects()


def candidate_table(objects: pd.DataFrame) -> pd.DataFrame:
    """Return one sortable row per large, freely orbiting rocket stage."""
    candidate_mask = (
        objects["Type"].str.startswith("R", na=False)
        & objects["Status"].eq("O")
        & objects["Mass_is_reliable"].fillna(False)
        & objects["Mass_numeric"].ge(MASS_CUTOFF_KG).fillna(False)
    )

    candidates = (
        objects.loc[
            candidate_mask,
            [
                "JCAT",
                "Name",
                "Mass_numeric",
                "MassFlag",
                "Perigee_numeric",
                "PF",
                "Apogee_numeric",
                "AF",
                "Inc_numeric",
                "IF",
            ],
        ]
        .drop_duplicates(subset="JCAT")
        .rename(
            columns={
                "Mass_numeric": "Mass (kg)",
                "MassFlag": "Mass flag",
                "Perigee_numeric": "Perigee (km)",
                "PF": "Perigee flag",
                "Apogee_numeric": "Apogee (km)",
                "AF": "Apogee flag",
                "Inc_numeric": "Inc (deg)",
                "IF": "Inc flag",
            }
        )
        .sort_values(["Mass (kg)", "JCAT"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return candidates


def rounded_bounds(
    table: pd.DataFrame,
    value_column: str,
    step: float,
    flag_column: str | None = None,
) -> tuple[float, float]:
    """Return control bounds based only on available, reliable measurements."""
    values = table[value_column]
    reliable = values.notna()
    if flag_column is not None:
        reliable &= table[flag_column].ne("?")

    minimum = math.floor(float(values.loc[reliable].min()) / step) * step
    maximum = math.ceil(float(values.loc[reliable].max()) / step) * step
    return minimum, maximum


def apply_candidate_filters(
    table: pd.DataFrame,
    mass_range: tuple[float, float],
    perigee_range: tuple[float, float],
    apogee_range: tuple[float, float],
    inclination_range: tuple[float, float],
    include_uncertain_or_unavailable: bool,
) -> pd.DataFrame:
    """Apply dashboard ranges without treating questionable orbits as reliable."""
    matches = table["Mass (kg)"].between(*mass_range, inclusive="both")

    orbital_filters = (
        ("Perigee (km)", "Perigee flag", perigee_range),
        ("Apogee (km)", "Apogee flag", apogee_range),
        ("Inc (deg)", "Inc flag", inclination_range),
    )
    for value_column, flag_column, selected_range in orbital_filters:
        reliable = table[value_column].notna() & table[flag_column].ne("?")
        within_range = reliable & table[value_column].between(
            *selected_range, inclusive="both"
        )
        questionable = ~reliable
        if include_uncertain_or_unavailable:
            matches &= within_range | questionable
        else:
            matches &= within_range

    return table.loc[matches].reset_index(drop=True)


def main() -> None:
    """Render the ADR candidate table."""
    st.set_page_config(page_title="ADR rocket-stage candidates", layout="wide")
    st.title("Large rocket-stage candidates")
    st.caption(
        "Freely orbiting rocket stages with reliable mass of at least 5,000 kg. "
        "Click any column header to sort the table. Blank numeric cells remain "
        "missing; question marks in adjacent flag columns identify uncertain values."
    )

    table = candidate_table(load_objects())

    mass_bounds = rounded_bounds(table, "Mass (kg)", step=500)
    perigee_bounds = rounded_bounds(
        table, "Perigee (km)", step=500, flag_column="Perigee flag"
    )
    apogee_bounds = rounded_bounds(
        table, "Apogee (km)", step=500, flag_column="Apogee flag"
    )
    inclination_bounds = rounded_bounds(
        table, "Inc (deg)", step=1, flag_column="Inc flag"
    )

    st.subheader("Screening controls")
    first_column, second_column = st.columns(2)
    with first_column:
        mass_range = st.slider(
            "Mass (kg)",
            min_value=int(mass_bounds[0]),
            max_value=int(mass_bounds[1]),
            value=(int(mass_bounds[0]), int(mass_bounds[1])),
            step=500,
        )
        perigee_range = st.slider(
            "Perigee (km)",
            min_value=int(perigee_bounds[0]),
            max_value=int(perigee_bounds[1]),
            value=(int(perigee_bounds[0]), int(perigee_bounds[1])),
            step=500,
        )
    with second_column:
        apogee_range = st.slider(
            "Apogee (km)",
            min_value=int(apogee_bounds[0]),
            max_value=int(apogee_bounds[1]),
            value=(int(apogee_bounds[0]), int(apogee_bounds[1])),
            step=500,
        )
        inclination_range = st.slider(
            "Inclination (degrees)",
            min_value=float(inclination_bounds[0]),
            max_value=float(inclination_bounds[1]),
            value=(float(inclination_bounds[0]), float(inclination_bounds[1])),
            step=1.0,
        )

    include_questionable = st.checkbox(
        "Keep candidates with uncertain or unavailable orbital values",
        value=True,
        help=(
            "For a field marked uncertain or unavailable, retain the object "
            "without treating that field as a reliable match to the selected range."
        ),
    )

    filtered_table = apply_candidate_filters(
        table,
        mass_range=mass_range,
        perigee_range=perigee_range,
        apogee_range=apogee_range,
        inclination_range=inclination_range,
        include_uncertain_or_unavailable=include_questionable,
    )

    st.subheader(f"{len(filtered_table):,} matching candidates")
    st.caption(
        "Question marks are original GCAT uncertainty flags. Blank numeric cells "
        "are unavailable and are never converted to zero."
    )
    st.dataframe(
        filtered_table,
        hide_index=True,
        width="stretch",
        column_config={
            "JCAT": st.column_config.TextColumn(
                "JCAT", help="GCAT object identifier"
            ),
            "Name": st.column_config.TextColumn("Name"),
            "Mass (kg)": st.column_config.NumberColumn(
                "Mass (kg)", format="%.0f"
            ),
            "Mass flag": st.column_config.TextColumn(
                "Mass flag", help="? means GCAT marks the mass as uncertain"
            ),
            "Perigee (km)": st.column_config.NumberColumn(
                "Perigee (km)", format="%.0f"
            ),
            "Perigee flag": st.column_config.TextColumn(
                "Perigee flag", help="? means GCAT marks the perigee as uncertain"
            ),
            "Apogee (km)": st.column_config.NumberColumn(
                "Apogee (km)", format="%.0f"
            ),
            "Apogee flag": st.column_config.TextColumn(
                "Apogee flag", help="? means GCAT marks the apogee as uncertain"
            ),
            "Inc (deg)": st.column_config.NumberColumn(
                "Inc (deg)", format="%.2f"
            ),
            "Inc flag": st.column_config.TextColumn(
                "Inc flag", help="? means GCAT marks the inclination as uncertain"
            ),
        },
    )


if __name__ == "__main__":
    main()
