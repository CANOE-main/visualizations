# make_net_emissions_plot.py
# Creates a two-panel stacked-area plot of net emissions by source & scenario.

import pandas as pd
import matplotlib.pyplot as plt
import re
from pathlib import Path
from typing import Iterable

# -----------------------------
# Configuration (edit if needed)
# -----------------------------
FILE_NET_ZERO = "emissions.csv"          # 'nz' scenario in your upload
FILE_CURRENT  = "emissions_ref.csv"      # 'reference' scenario in your upload
REGION = "prince edward island"
UNIT   = "Mt CO2-equiv/yr"

# If you only want specific top-level sources, list them (case-insensitive).
# Leave as None to include whatever top-level sources exist in the files.
TOP_LEVEL_SOURCES: Iterable[str] | None = [
    "electricity", "industrial", "transportation", "commercial", "residential", "agriculture"
]

# Friendly names for the two scenarios (derived from the CSVs' `scenario` column)
SCENARIO_LABELS = {
    "nz": "Net-Zero Scenario",
    "reference": "Current Policy Scenario"
}

OUTPUT = "net_emissions_by_source.png"

# -----------------------------
# Helpers
# -----------------------------
def _read_one(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # keep just Canada, target unit
    df = df[(df["region"].str.lower() == REGION.lower()) & (df["unit"] == UNIT)].copy()

    # Keep *top-level* variables like "emissions|industrial"
    is_top_level = df["variable"].str.match(r"^emissions\|[^|]+$")
    df = df[is_top_level].copy()

    # Extract top-level source name (e.g., "industrial")
    df["source_raw"] = df["variable"].str.split("|").str[1].str.lower()

    # Map scenario to friendly label
    scen_val = str(df["scenario"].iloc[0]).lower() if not df.empty else ""
    df["Scenario"] = SCENARIO_LABELS.get(scen_val, df["scenario"].iloc[0].title())

    # Title-case for legend
    df["Source"] = df["source_raw"].str.title()
    return df[["time", "value", "Source", "Scenario", "source_raw"]]


def _load_and_prepare(paths: list[str | Path]) -> pd.DataFrame:
    frames = [_read_one(p) for p in paths]
    out = pd.concat(frames, ignore_index=True)

    if TOP_LEVEL_SOURCES is not None:
        keep = {s.lower() for s in TOP_LEVEL_SOURCES}
        out = out[out["source_raw"].isin(keep)].copy()

    # Aggregate (if any duplicates exist) to get one value per year/source/scenario
    out = (
        out.groupby(["Scenario", "Source", "time"], as_index=False)["value"]
           .sum()
           .rename(columns={"time": "Year", "value": "Emissions"})
           .sort_values(["Scenario", "Year"])
    )
    return out


def _plot_two_panel(df: pd.DataFrame, output_path: str | Path):
    # Ensure consistent source order across panels
    all_sources = list(df["Source"].drop_duplicates())
    # Optional: put them in a nicer order if we know the common ones:
    preferred = ["Electricity", "Industrial", "Transport", "Commercial", "Residential", "Agriculture"]
    order = [s for s in preferred if s in all_sources] + [s for s in all_sources if s not in preferred]

    scenarios = df["Scenario"].drop_duplicates().tolist()
    scenarios.sort(key=lambda s: 0 if "Current" in s else 1)  # put Current Policy first if present

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True, dpi=150)

    # If only one scenario was found, make the second panel empty but keep layout stable
    while len(scenarios) < 2:
        scenarios.append("")

    for ax, scen in zip(axes, scenarios):
        if scen == "" or scen not in df["Scenario"].unique():
            ax.set_axis_off()
            continue

        part = df[df["Scenario"] == scen].copy()
        pivot = (
            part.pivot_table(index="Year", columns="Source", values="Emissions", aggfunc="sum")
                .reindex(columns=order)
                .fillna(0.0)
        )
        years = pivot.index.values
        series = [pivot[col].values for col in pivot.columns]

        # Stacked area (default Matplotlib colors; no style/color specified)
        ax.stackplot(years, series, labels=pivot.columns)

        ax.set_title(scen)
        ax.set_xlabel("Year")
        if ax is axes[0]:
            ax.set_ylabel("Emissions (million tonnes)")
        ax.grid(axis="y", linestyle=":", linewidth=0.5)
        ax.set_xlim(years.min(), years.max())

    # One legend, outside the plots
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="center left", bbox_to_anchor=(1.02, 0.5), title="Source")
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    plt.savefig(output_path, bbox_inches="tight")
    print(f"Saved: {output_path}")


def main():
    df = _load_and_prepare([FILE_NET_ZERO, FILE_CURRENT])
    _plot_two_panel(df, OUTPUT)


if __name__ == "__main__":
    main()
