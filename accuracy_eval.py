import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

GROUND_TRUTH_PATH = "data/cell1_roi5_ground_truth_smoothed.csv"
DSB_PATH = "data/cell1_roi5_automatic.csv"


def load_data(gt_path: str, dsb_path: str):
    """Load ground truth and DSB dataframes."""
    gt = pd.read_csv(gt_path)
    dsb = pd.read_csv(dsb_path)
    return gt, dsb


def find_nearest_neighbors(gt_pts: np.ndarray, dsb_pts: np.ndarray):
    """
    For each point in dsb_pts, find the index and distance of the nearest point in gt_pts.
    Returns:
        indices: int array of shape (n_dsb,)
        distances: float array of same shape
    """
    n = dsb_pts.shape[0]
    indices = np.empty(n, dtype=int)
    distances = np.empty(n, dtype=float)

    for i, pt in enumerate(dsb_pts):
        deltas = gt_pts - pt
        dist2 = np.einsum("ij,ij->i", deltas, deltas)
        j = np.argmin(dist2)
        indices[i] = j
        distances[i] = np.sqrt(dist2[j])

    return indices, distances


def merge_ground_truth(gt: pd.DataFrame, dsb: pd.DataFrame, max_dist: float = 500.0):
    """Match each DSB spine to the nearest GT spine and merge volumes/C.O.M., filtering out outliers."""
    # Column names
    dsb_coords = ["Head Centroid X (nm)", "Head Centroid Y (nm)", "Head Centroid Z (nm)"]
    gt_coords = ["com_x", "com_y", "com_z"]

    gt_pts = gt[gt_coords].to_numpy(dtype=float)
    dsb_pts = dsb[dsb_coords].to_numpy(dtype=float)

    idxs, dists = find_nearest_neighbors(gt_pts, dsb_pts)

    # Build merged columns
    merged = dsb.copy()
    merged["GT_name"] = gt.loc[idxs, "name"].values
    merged["GT_volume"] = gt.loc[idxs, "volume"].values
    merged[["GT_com_x", "GT_com_y", "GT_com_z"]] = gt_pts[idxs]
    merged["distance_nm"] = dists

    # Filter out matches farther than threshold
    merged = merged[merged["distance_nm"] < max_dist].reset_index(drop=True)

    # Volume differences
    merged["volume_diff"] = merged["Head Volume (μm³)"] - merged["GT_volume"]
    merged["volume_percent_diff"] = (
        merged["volume_diff"] / merged["Head Volume (μm³)"] * 100
    )

    return merged


def plot_histogram(data: pd.Series, title: str, x_label: str, bins: int = 50):
    plt.figure()
    plt.hist(data, bins=bins)
    plt.title(title)
    plt.xlabel(x_label)
    ax = plt.gca()  # Get current axes
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))  # Integer y-axis
    plt.ylabel("Count")
    plt.show()


def plot_scatter_with_identity(x: pd.Series, y: pd.Series, xlabel: str, ylabel: str, title: str):
    plt.figure()
    plt.scatter(x, y, alpha=0.7)
    mn, mx = min(x.min(), y.min()), max(x.max(), y.max())
    plt.plot([mn, mx], [mn, mx], linestyle="--", color="red")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.show()


def plot_bland_altman(x: pd.Series, y: pd.Series, labels=None):
    """
    Creates a Bland–Altman plot comparing x & y.
    If labels is provided, it's a sequence of text labels for each point.
    """
    mean_vals = (x + y) / 2
    diffs = x - y

    plt.figure()
    plt.scatter(mean_vals, diffs, alpha=0.7)

    # Annotate points if labels are given
    # for i, txt in enumerate(labels):
    #     plt.text(mean_vals[i], diffs[i], txt, fontsize=6, ha="left", va="bottom")

    plt.axhline(0, linestyle="--", color="red")
    plt.title("Bland–Altman Plot of DSB Accuracy")
    plt.xlabel("Mean Volume (μm³)")
    plt.ylabel("Volume Difference (DSB - GT) (μm³)")
    plt.show()


def main():
    gt_df, dsb_df = load_data(GROUND_TRUTH_PATH, DSB_PATH)
    merged = merge_ground_truth(gt_df, dsb_df)

    # Histograms
    plot_histogram(
        merged["volume_percent_diff"],
        title="Volume % Difference (DSB vs GT)",
        x_label="Percent Difference (%)",
        bins=15
    )
    plot_histogram(
        merged["volume_diff"],
        title="Volume Difference (DSB – GT) μm³",
        x_label="Difference (μm³)",
        bins=15
    )

    # Scatter DSB vs GT
    plot_scatter_with_identity(
        merged["GT_volume"],
        merged["Head Volume (μm³)"],
        xlabel="Ground Truth Volume (μm³)",
        ylabel="DSB Volume (μm³)",
        title="DSB vs Ground Truth Head Volume"
    )

    # Bland–Altman
    plot_bland_altman(
        merged["Head Volume (μm³)"],
        merged["GT_volume"],
        labels=[
            # f"{row.GT_name}, idx {row['Head Index']}"
            # for _, row in merged.iterrows()
        ]
    )


if __name__ == "__main__":
    main()
