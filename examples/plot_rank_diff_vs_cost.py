"""Scatter plot of average |rank_diff| vs average cost_ratio per method, with error bars.

rank_diff is computed as |subset_rank - original_rank| (unsigned displacement).
Each point represents one benchmarking method; the ideal method sits at (0, 0):
cheap and rank-preserving.

Method index mapping (from run_benchmarkers_on_competition.py):
    INSTANCE_SELECTOR_CLASSES  = [Variance, Random, Discrimination]
    STOPPING_CRITERION_CLASSES = [MinAccuracy, Wilcoxon, Percentage]
    methods = [(sel, stop) for sel in selectors for stop in criteria]  →  9 combos
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pltpublish as pub
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import polars as pl

pub.setup()

METHOD_NAMES = {
    1: "nMinAccuracy",
    2: "Wilcoxon",
    3: "Percentage",
    4: "MinAccuracy",
    5: "Wilcoxon",
    6: "Percentage",
    7: "MinAccuracy",
    8: "Wilcoxon",
    9: "Percentage",
}
SELECTOR_COLOR = {
    "Variance": "#4C72B0",
    "Random": "#DD8452",
    "Discrimination": "#55A868",
}

METHOD_SELECTOR = {
    1: "Variance",
    2: "Variance",
    3: "Variance",
    4: "Random",
    5: "Random",
    6: "Random",
    7: "Discrimination",
    8: "Discrimination",
    9: "Discrimination",
}

METHOD_CRITERION = {
    1: "MinAccuracy",
    2: "Wilcoxon",
    3: "Percentage",
    4: "MinAccuracy",
    5: "Wilcoxon",
    6: "Percentage",
    7: "MinAccuracy",
    8: "Wilcoxon",
    9: "Percentage",
}

CRITERION_MARKER = {
    "MinAccuracy": "o",
    "Wilcoxon": "s",
    "Percentage": "^",
}


def main(csv_path: str, output: str | None, ci: float = 0.95) -> None:
    df = pl.read_csv(csv_path).with_columns((pl.col("subset_rank") - pl.col("original_rank")).abs().alias("rank_diff"))

    stats = (
        df.group_by("method_idx")
        .agg(
            pl.col("cost_ratio").mean().alias("cost_mean"),
            pl.col("cost_ratio").std().alias("cost_std"),
            pl.col("cost_ratio").count().alias("cost_n"),
            pl.col("rank_diff").mean().alias("rank_mean"),
            pl.col("rank_diff").std().alias("rank_std"),
            pl.col("rank_diff").count().alias("rank_n"),
        )
        .sort("method_idx")
    )

    z = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}.get(ci, 1.960)

    cost_means = np.array(stats["cost_mean"].to_list())
    cost_ci = z * (stats["cost_std"] / stats["cost_n"].cast(pl.Float64).sqrt()).to_numpy()
    rank_means = np.array(stats["rank_mean"].to_list())
    rank_ci = z * (stats["rank_std"] / stats["rank_n"].cast(pl.Float64).sqrt()).to_numpy()
    methods = stats["method_idx"].to_list()

    fig, ax = plt.subplots(figsize=(10, 7))

    for i, m in enumerate(methods):
        color = SELECTOR_COLOR[METHOD_SELECTOR.get(m, "Variance")]
        marker = CRITERION_MARKER[METHOD_CRITERION.get(m, "MinAccuracy")]
        ax.errorbar(
            cost_means[i],
            rank_means[i],
            xerr=cost_ci[i],
            yerr=rank_ci[i],
            fmt=marker,
            color=color,
            ecolor=color,
            elinewidth=1.5,
            capsize=5,
            capthick=1.5,
            markersize=9,
            markeredgecolor="black",
            markeredgewidth=0.8,
            zorder=3,
        )
        # # Offset label slightly so it doesn't overlap the marker
        # ax.annotate(
        #     METHOD_NAMES.get(m, f"Method {m}"),
        #     xy=(cost_means[i], rank_means[i]),
        #     xytext=(6, 4),
        #     textcoords="offset points",
        #     fontsize=7.5,
        #     color="black",
        #     zorder=4,
        # )

    # Legend for selectors (color) and stopping criteria (marker shape)
    selector_handles = [Patch(facecolor=c, edgecolor="black", label=sel) for sel, c in SELECTOR_COLOR.items()]
    criterion_handles = [
        Line2D([0], [0], marker=mk, color="gray", linestyle="None", markersize=8, markeredgecolor="black", markeredgewidth=0.8, label=crit)
        for crit, mk in CRITERION_MARKER.items()
    ]
    sel_legend = ax.legend(handles=selector_handles, title="Instance Selector", loc="upper left")
    ax.add_artist(sel_legend)
    ax.legend(handles=criterion_handles, title="Stopping Criterion", loc="upper right")

    ax.set_xlabel("Average Cost Ratio  (actual / total cost)", fontsize=11)
    ax.set_ylabel("Average |Rank Difference|", fontsize=11)
    competition = Path(csv_path).stem.replace("experiment_results_", "")
    ax.set_title(
        f"Rank Accuracy vs. Cost Trade-off — {competition}\n(error bars = {int(ci * 100)} % CI; bottom-left is ideal)",
        fontsize=12,
    )
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.grid(linestyle="--", alpha=0.4)

    fig.tight_layout()

    if output:
        pub.save_fig(output)
        print(f"Saved to {output}")
    else:
        plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot rank diff vs cost ratio per method.")
    parser.add_argument("csv", help="Path to experiment_results_*.csv")
    parser.add_argument("-o", "--output", default=None, help="Save figure to this path instead of showing it")
    parser.add_argument("--ci", type=float, default=0.95, help="Confidence interval level (0.90 / 0.95 / 0.99)")
    args = parser.parse_args()
    main(args.csv, args.output, args.ci)
