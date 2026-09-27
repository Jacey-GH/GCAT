"""Load and clean the two standard GCAT object catalogs."""

from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = PROJECT_DIR / "data"

# Each numeric source field has a separate GCAT uncertainty flag.
NUMERIC_FLAG_COLUMNS = {
    "Mass": "MassFlag",
    "Perigee": "PF",
    "Apogee": "AF",
    "Inc": "IF",
}


def _read_gcat(path: Path) -> pd.DataFrame:
    """Read one GCAT TSV without losing coded blanks or uncertainty markers."""
    frame = pd.read_csv(
        path,
        sep="\t",
        dtype=str,
        skiprows=[1],
        keep_default_na=False,
        quoting=3,
    )
    frame.columns = [column.lstrip("#").strip() for column in frame.columns]
    for column in frame.columns:
        frame[column] = frame[column].str.strip()
    return frame


def _add_numeric_and_quality_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Add nullable numeric values and explicit reliability classifications."""
    cleaned = frame.copy()

    orbital_preview = {
        column: pd.to_numeric(cleaned[column], errors="coerce").astype("Float64")
        for column in ("Perigee", "Apogee", "Inc")
    }
    unavailable_zero_orbit = (
        orbital_preview["Perigee"].eq(0)
        & orbital_preview["Apogee"].eq(0)
        & orbital_preview["Inc"].eq(0)
        & cleaned["OpOrbit"].eq("-")
    )

    for source_column, flag_column in NUMERIC_FLAG_COLUMNS.items():
        numeric_column = f"{source_column}_numeric"
        quality_column = f"{source_column}_quality"
        reliable_column = f"{source_column}_is_reliable"

        numeric = pd.to_numeric(
            cleaned[source_column], errors="coerce"
        ).astype("Float64")

        # GCAT uses Mass = 0 to mean that mass was not estimated.
        if source_column == "Mass":
            numeric = numeric.mask(numeric.eq(0))
        elif source_column in {"Perigee", "Apogee", "Inc"}:
            # A simultaneous all-zero orbit with no orbit class is unavailable,
            # not a physical Earth orbit. Preserve the original text columns.
            numeric = numeric.mask(unavailable_zero_orbit)

        unavailable = numeric.isna()
        uncertain = cleaned[flag_column].eq("?") & ~unavailable

        quality = pd.Series(
            "reliable", index=cleaned.index, dtype="string"
        )
        quality = quality.mask(uncertain, "uncertain")
        quality = quality.mask(unavailable, "unavailable")

        cleaned[numeric_column] = numeric
        cleaned[quality_column] = quality
        cleaned[reliable_column] = quality.eq("reliable")

    return cleaned


def load_gcat_objects(data_dir: str | Path = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """Return the combined, cleaned satcat and satcat100k DataFrame.

    Original GCAT columns remain stripped strings, including ``MassFlag``,
    ``PF``, ``AF``, and ``IF``. For each dashboard numeric field, the result
    adds ``*_numeric``, ``*_quality``, and ``*_is_reliable`` columns.
    """
    data_dir = Path(data_dir)
    objects = pd.concat(
        [
            _read_gcat(data_dir / "satcat.tsv"),
            _read_gcat(data_dir / "satcat100k.tsv"),
        ],
        ignore_index=True,
    )
    return _add_numeric_and_quality_columns(objects)
