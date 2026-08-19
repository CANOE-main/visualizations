
# make_primary_energy_two_panel.py
# Single figure with side-by-side stacked-area plots; Current Policy on the LEFT, Net-Zero on the RIGHT.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

GENERATION_FILES = ["generation.csv", "generation_ref.csv"]
END_USE_FILES    = ["end_use_energy.csv", "end_use_energy_ref.csv"]

REGION = "prince edward island"
UNIT = "PJ"

EFFICIENCIES = {"coal": 0.33, "natural gas": 0.50, "nuclear": 0.33, "bioenergy": 0.30}
NON_THERMAL_1to1 = True

ORDER = ["Wind","Solar","Biomass","Other Renewables","Nuclear","Natural Gas","Petroleum","Coal"]
SCN_LABELS = {"reference": "Current Policy Scenario", "nz": "Net-Zero Scenario"}
SCN_ORDER  = ["reference", "nz"]  # <-- desired left-to-right order

def _load(paths):
    frames = []
    for p in paths:
        if Path(p).exists():
            frames.append(pd.read_csv(p))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["model","scenario","region","variable","unit","time","value"]
    )

def _primary_from_power(gen: pd.DataFrame) -> pd.DataFrame:
    gen = gen[(gen["region"].str.lower()==REGION.lower()) & (gen["unit"]==UNIT)].copy()
    rows = []
    for (scn, yr), g in gen.groupby(["scenario","time"]):
        def s(prefix): return g[g["variable"].str.startswith(prefix)]["value"].sum()
        e_coal  = s("secondary energy|electricity|coal")
        e_ng    = s("secondary energy|electricity|natural gas")
        e_nuke  = s("secondary energy|electricity|nuclear")
        e_bio   = s("secondary energy|electricity|bioenergy")
        e_hydro = s("secondary energy|electricity|hydro")
        e_solar = s("secondary energy|electricity|renewables|solar PV")
        e_wind  = s("secondary energy|electricity|renewables|wind onshore")

        p_coal = e_coal / max(EFFICIENCIES.get('coal',1.0), 1e-9)
        p_ng   = e_ng   / max(EFFICIENCIES.get('natural gas',1.0), 1e-9)
        p_nuke = e_nuke / max(EFFICIENCIES.get('nuclear',1.0), 1e-9)
        p_bio  = e_bio  / max(EFFICIENCIES.get('bioenergy',1.0), 1e-9)

        if NON_THERMAL_1to1:
            p_solar, p_wind, p_other = e_solar, e_wind, e_hydro
        else:
            ref = 0.33
            p_solar, p_wind, p_other = e_solar/ref, e_wind/ref, e_hydro/ref

        rows += [
            {"Scenario": scn, "Year": int(yr), "Category":"Coal", "Value": p_coal},
            {"Scenario": scn, "Year": int(yr), "Category":"Natural Gas", "Value": p_ng},
            {"Scenario": scn, "Year": int(yr), "Category":"Nuclear", "Value": p_nuke},
            {"Scenario": scn, "Year": int(yr), "Category":"Biomass", "Value": p_bio},
            {"Scenario": scn, "Year": int(yr), "Category":"Solar", "Value": p_solar},
            {"Scenario": scn, "Year": int(yr), "Category":"Wind", "Value": p_wind},
            {"Scenario": scn, "Year": int(yr), "Category":"Other Renewables", "Value": p_other},
        ]
    return pd.DataFrame(rows)

def _final_fuels(end: pd.DataFrame) -> pd.DataFrame:
    end = end[(end["region"].str.lower()==REGION.lower()) & (end["unit"]==UNIT)].copy()
    rows = []
    for (scn, yr), g in end.groupby(["scenario","time"]):
        petroleum = g[g["variable"].str.contains("gasoline|diesel|jet fuel|oil", case=False)]["value"].sum()
        natgas    = g[g["variable"].str.contains("natural gas", case=False)]["value"].sum()
        coal      = g[g["variable"].str.contains("coal", case=False)]["value"].sum()
        rows += [
            {"Scenario": scn, "Year": int(yr), "Category":"Petroleum", "Value": petroleum},
            {"Scenario": scn, "Year": int(yr), "Category":"Natural Gas", "Value": natgas},
            {"Scenario": scn, "Year": int(yr), "Category":"Coal", "Value": coal},
        ]
    return pd.DataFrame(rows)

def _plot_two_panel(df: pd.DataFrame, out_path: str):
    df = df.copy()
    df["Value"] = df["Value"] / 1000.0  # PJ -> EJ
    df["Category"] = pd.Categorical(df["Category"], categories=ORDER, ordered=True)

    # Enforce left-to-right scenario order: reference, then nz, keeping only those present
    present = list(dict.fromkeys(df["Scenario"].tolist()))
    scenarios = [s for s in SCN_ORDER if s in present] or present

    n = min(2, max(1, len(scenarios)))
    fig_w = 11 if n == 2 else 6
    fig, axes = plt.subplots(1, n, figsize=(fig_w, 4), sharey=True, dpi=150)
    if n == 1:
        axes = [axes]

    for ax, scen in zip(axes, scenarios[:n]):
        label = SCN_LABELS.get(scen.lower(), scen.title())
        part = df[df["Scenario"] == scen]
        pv = (part.pivot_table(index="Year", columns="Category", values="Value", aggfunc="sum")
                    .reindex(columns=ORDER).fillna(0.0))
        years = pv.index.values
        stacks = [pv[c].values for c in pv.columns]
        ax.stackplot(years, stacks, labels=pv.columns)
        ax.set_title(label)
        ax.set_xlabel("Year")
        if ax is axes[0]:
            ax.set_ylabel("Primary Energy Consumption (EJ)")
        ax.grid(axis="y", linestyle=":", linewidth=0.5)
        ax.set_xlim(years.min(), years.max())

    handles, labels = axes[-1].get_legend_handles_labels()
    fig.legend(handles, labels, title="Source", loc="center left", bbox_to_anchor=(1.02, 0.5))
    plt.tight_layout(rect=[0,0,0.85,1])
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()

def main():
    gen = _load(GENERATION_FILES)
    end = _load(END_USE_FILES)
    power = _primary_from_power(gen)
    fuels = _final_fuels(end)
    df = pd.concat([power, fuels], ignore_index=True)
    df = df.groupby(["Scenario","Year","Category"], as_index=False)["Value"].sum()
    _plot_two_panel(df, "primary_energy_two_panel.png")
    print("Saved: primary_energy_two_panel.png")

if __name__ == "__main__":
    main()
