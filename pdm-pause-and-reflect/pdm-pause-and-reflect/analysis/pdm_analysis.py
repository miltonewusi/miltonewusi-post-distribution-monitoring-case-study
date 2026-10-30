"""
PDM analysis: reproduces every table and chart used in the case study.

Usage:
    python analysis/pdm_analysis.py path/to/PDM_dataset.xlsx

The raw dataset is NOT published in this repository (it contains enumerator
contact details, GPS coordinates and free-text responses). Only aggregate
outputs are written to outputs/tables and assets.
"""
import json
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
TABLES, ASSETS = ROOT / "outputs" / "tables", ROOT / "assets"
TABLES.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(parents=True, exist_ok=True)

AGE_ORDER = ["18 to 35 years", "36 to 50 years", "51 to 65 years",
             "66 to 80 years", "81 years and above"]
LONG_WAIT = ["1 hour to 1:30 hour", "More than 1:30 hour"]


def load(path):
    raw = pd.read_excel(path)
    raw.columns = [str(c).strip() for c in raw.columns]
    col = lambda p: next(c for c in raw.columns if c.startswith(p))
    s = lambda p: raw[col(p)].astype("string").str.strip()
    d = pd.DataFrame({
        "district": s("B4."), "village": s("B5."),
        "sex": s("C1."), "respondent": s("C2."),
        "age": pd.to_numeric(raw[col("C3. What")]),
        "fair": s("D3."), "explained": s("D1."),
        "paid_fee": s("E1."), "shared": s("E2. After"),
        "amount_as_told": s("E4."), "package": s("E5."), "quality": s("E6."),
        "travel": s("F1."), "wait": s("F2."),
        "transport_php": pd.to_numeric(raw[col("F3.")]),
        "cash_difficulty": s("F4."), "used": s("J1."), "planted": s("J2."),
        "fertilizer": s("J4."), "appropriate": s("K1."),
        "training": s("K2."), "sufficient": s("K3."),
    })
    # Age bands are derived here (not taken from the source column) so the
    # logic is explicit and auditable.
    d["age_group"] = pd.cut(d["age"], [17, 35, 50, 65, 80, 200],
                            labels=AGE_ORDER).astype(str)
    # Optional local anonymisation (file is git-ignored; see data/README.md)
    mp = ROOT / "data" / "anonymise_map.json"
    if mp.exists():
        m = json.loads(mp.read_text())
        d["district"] = d["district"].replace(m.get("district", {}))
        d["village"] = d["village"].replace(m.get("village", {}))
    return d


def share(series, positive):
    """% of non-missing answers equal to `positive` (or in a list)."""
    s = series.dropna()
    if not len(s):
        return float("nan")
    pos = positive if isinstance(positive, list) else [positive]
    return round(100 * s.isin(pos).mean(), 1)


def indicators(d, by):
    g = d.groupby(by, observed=True)
    return pd.DataFrame({
        "n": g.size(),
        "input_quality_good_%": g["quality"].apply(lambda x: share(x, "Good quality")),
        "inputs_appropriate_%": g["appropriate"].apply(lambda x: share(x, "Yes")),
        "inputs_sufficient_%": g["sufficient"].apply(lambda x: share(x, "Yes")),
        "needed_training_%": g["training"].apply(lambda x: share(x, "Yes")),
        "used_inputs_%": g["used"].apply(lambda x: share(x, "Yes")),
        "planted_seeds_%": g["planted"].apply(lambda x: share(x, "Yes")),
        "applied_fertilizer_%": g["fertilizer"].apply(lambda x: share(x, "Yes")),
        "travel_over_1h_%": g["travel"].apply(lambda x: share(x, LONG_WAIT)),
        "wait_over_1h_%": g["wait"].apply(lambda x: share(x, LONG_WAIT)),
        "mean_transport_cost_LCU": g["transport_php"].mean().round(0),
        "cash_access_difficult_%": g["cash_difficulty"].apply(lambda x: share(x, "Yes")),
        "amount_differed_from_told_%": g["amount_as_told"].apply(lambda x: share(x, "No")),
    })


def main(path):
    d = load(path)

    # 1. Household profile by village
    prof = pd.crosstab(d.village, d.sex, margins=True, margins_name="Total")
    prof["Female_%"] = (100 * prof["Female"] / prof["Total"]).round(1)
    head = pd.crosstab(d.village, d.respondent == "Head of household",
                       margins=True, margins_name="Total")[True]
    prof["Head_of_household_%"] = (100 * head / prof["Total"]).round(1)
    prof.insert(0, "District",
                d.drop_duplicates("village").set_index("village")["district"])
    prof.to_csv(TABLES / "01_profile_by_village.csv")

    # 2. Age statistics by village
    def mode_txt(x):
        m = sorted(x.mode().tolist())
        return str(m[0]) if len(m) == 1 else f"{'/'.join(map(str, m))} (multimodal)"
    age = d.groupby("village")["age"].agg(
        n="count", mean="mean", median="median", mode=mode_txt, min="min", max="max")
    age.loc["All"] = [len(d), d.age.mean(), d.age.median(), mode_txt(d.age),
                      d.age.min(), d.age.max()]
    age["mean"] = age["mean"].astype(float).round(1)
    age.to_csv(TABLES / "02_age_stats_by_village.csv")

    # 3. Fairness of selection by age group (incl. non-response)
    fair = pd.crosstab(d.age_group, d.fair.fillna("No response"), margins=True,
                       margins_name="Total").reindex(AGE_ORDER + ["Total"])
    fair.to_csv(TABLES / "03_fairness_by_age_group.csv")

    # 4-6. Quality / utilisation indicators by district, age group, package
    mun = indicators(d, "district")
    mun.to_csv(TABLES / "04_indicators_by_district.csv")
    ag = indicators(d, "age_group").reindex(AGE_ORDER)
    ag.to_csv(TABLES / "05_indicators_by_age_group.csv")
    pk = indicators(d, "package")
    pk.to_csv(TABLES / "06_indicators_by_package.csv")

    # Package x district (shows the two are almost perfectly confounded)
    pd.crosstab(d.package, d.district, margins=True, margins_name="Total").to_csv(
        TABLES / "07_package_by_district.csv")

    # Overall headline figures
    indicators(d.assign(all="All respondents"), "all").to_csv(
        TABLES / "08_indicators_overall.csv")

    # Planting by district x package (answered only)
    pl = d.dropna(subset=["planted"])
    pd.crosstab([pl.district, pl.package], pl.planted).to_csv(
        TABLES / "09_planting_by_district_package.csv")

    # ---- charts ----
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False})
    c1, c2, c3 = "#2f6f9f", "#d9822b", "#7a8b99"

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    vals = pk["planted_seeds_%"]
    bars = ax.bar(vals.index, vals, color=[c1, c2, c1])
    for b, n in zip(bars, pk["n"]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5,
                f"{b.get_height():.0f}%\n(n={n})", ha="center", fontsize=9)
    ax.set_ylim(0, 120)
    ax.set_ylabel("% who had planted the seeds")
    ax.set_title("Seed planting by agri-input package")
    fig.tight_layout()
    fig.savefig(ASSETS / "planting_by_package.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    labels = ["Needed training\nor guidance", "Inputs sufficient",
              "Wait at site\n> 1 hour", "Travel to site\n> 1 hour"]
    keys = ["needed_training_%", "inputs_sufficient_%",
            "wait_over_1h_%", "travel_over_1h_%"]
    w = 0.38
    for i, (m, c) in enumerate(zip(mun.index, [c1, c2])):
        ax.bar([j + (i - 0.5) * w for j in range(len(keys))],
               [mun.loc[m, k] for k in keys], w,
               label=f"{m} (n={mun.loc[m, 'n']})", color=c)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(0, 125)
    ax.set_ylabel("% of respondents")
    ax.legend(frameon=False, fontsize=8, loc="upper right", ncol=2)
    ax.set_title("Support experience by district")
    fig.tight_layout()
    fig.savefig(ASSETS / "district_comparison.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    t = ag["needed_training_%"]
    short = ["18–35", "36–50", "51–65", "66–80", "81+"]
    bars = ax.bar(short, t, color=c3)
    for b, n in zip(bars, ag["n"]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5,
                f"{b.get_height():.0f}%\n(n={n})", ha="center", fontsize=9)
    ax.set_ylim(0, 120)
    ax.set_ylabel("% who needed training/guidance")
    ax.set_xlabel("Age group (years)")
    ax.set_title("Need for training by age group")
    fig.tight_layout()
    fig.savefig(ASSETS / "training_need_by_age.png", dpi=160)
    plt.close(fig)

    print("Done. Tables ->", TABLES)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
