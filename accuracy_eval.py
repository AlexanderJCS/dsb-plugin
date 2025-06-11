"""
Generate the ground truth CSV using this script in the Dragonfly Python console:

multiroi = ...
csv = "name,volume,com_x,com_y,com_z"
for label in range(1, multiroi.getLabelCount() + 1):
    copy_roi = ROI()
    copy_roi.copyShapeFromStructuredGrid(multiroi)
    multiroi.addToVolumeROI(copy_roi, label)
    name = multiroi.getLabelName(label)
    vol = copy_roi.getVolume(0)*1e18  # m^3 -> um^3
    center_of_mass = copy_roi.getCenterOfMass(0)
    csv += f"\n\"{name}\",{vol},{center_of_mass.getX()*1e9},{center_of_mass.getY()*1e9},{center_of_mass.getZ()*1e9}"

with open(r"path/to/save/ground_truth.csv", "w") as f:
    f.write(csv)
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from meshparty import trimesh_vtk, trimesh_io
from pipeline import payload


GROUND_TRUTH_PATH = r"F:\DSB Files\cell1_roi5_ground_truth.csv"
DSB_PATH = r"F:\DSB Files\cell1_roi5_manual.csv"


def main():
    df_ground_truth = pd.read_csv(GROUND_TRUTH_PATH)
    df_dsb = pd.read_csv(DSB_PATH)

    print(df_dsb.columns)
    print(df_ground_truth.head())

    # For each row in the DSB file, find the corresponding ground truth entry by finding the closest point
    # The location of the head in the DSB file is given by the columns Head Centroid X (nm), etc.
    # The location of the head in the ground truth file is given by the columns com_x, com_y, com_z
    dsb_x_col = "Head Centroid X (nm)"
    dsb_y_col = "Head Centroid Y (nm)"
    dsb_z_col = "Head Centroid Z (nm)"
    gt_x_col = "com_x"
    gt_y_col = "com_y"
    gt_z_col = "com_z"

    # Build arrays
    pts_gt = df_ground_truth[[gt_x_col, gt_y_col, gt_z_col]].to_numpy(dtype=float)
    pts_dsb = df_dsb[[dsb_x_col, dsb_y_col, dsb_z_col]].to_numpy(dtype=float)

    n_dsb = pts_dsb.shape[0]
    idxs = np.empty(n_dsb, dtype=int)
    dists = np.empty(n_dsb, dtype=float)
    for i in range(n_dsb):
        diff = pts_gt - pts_dsb[i]
        dist2 = np.sum(diff ** 2, axis=1)
        j = np.argmin(dist2)
        idxs[i] = j
        dists[i] = np.sqrt(dist2[j])

    # Gather matched ground-truth info
    matched_names = df_ground_truth.loc[idxs, "name"].values
    matched_vols = df_ground_truth.loc[idxs, "volume"].values
    matched_coms = pts_gt[idxs]  # array of shape (n_dsb, 3)

    # Add to df_dsb
    df_dsb = df_dsb.copy()
    if matched_names is not None:
        df_dsb["GT_name"] = matched_names
    if matched_vols is not None:
        df_dsb["GT_volume"] = matched_vols
    df_dsb["GT_com_x"] = matched_coms[:, 0]
    df_dsb["GT_com_y"] = matched_coms[:, 1]
    df_dsb["GT_com_z"] = matched_coms[:, 2]
    df_dsb["distance_nm"] = dists

    # Remove entries with distances greater than 500nm, since they're likely not paired to the right spine
    df_dsb = df_dsb[df_dsb["distance_nm"] < 500]

    # Percent difference in volume between ground truth and DSB
    df_dsb["volume_percent_diff"] = (df_dsb["Head Volume (μm³)"] - df_dsb["GT_volume"]) / df_dsb["Head Volume (μm³)"] * 100

    df_dsb["volume_diff"] = df_dsb["Head Volume (μm³)"] - df_dsb["GT_volume"]

    print(df_dsb["volume_diff"][df_dsb["volume_diff"] < 0].count(), "spines have a smaller volume than ground truth")
    print(df_dsb["volume_diff"][df_dsb["volume_diff"] > 0].count(), "spines have a larger volume than ground truth")

    plt.hist(df_dsb["volume_percent_diff"], bins=50)
    plt.show()

    plt.hist(df_dsb["volume_diff"], bins=50)
    plt.show()

    plt.scatter(df_dsb["GT_volume"], df_dsb["Head Volume (μm³)"])
    # y=x line
    max_volume = max(df_dsb["Head Volume (μm³)"].max(), df_dsb["GT_volume"].max())
    min_volume = min(df_dsb["Head Volume (μm³)"].min(), df_dsb["GT_volume"].min())
    plt.plot([min_volume, max_volume], [min_volume, max_volume], color='red', linestyle='--')

    plt.xlabel("Ground Truth Head Volume (μm³)")
    plt.ylabel("DSB Head Volume (μm³)")
    plt.title("DSB vs Ground Truth Head Volume")

    plt.show()

    # Bland-Altman plot
    mean_volume = (df_dsb["Head Volume (μm³)"] + df_dsb["GT_volume"]) / 2
    volume_diff = df_dsb["Head Volume (μm³)"] - df_dsb["GT_volume"]
    plt.scatter(mean_volume, volume_diff)

    for i, (x, y) in enumerate(zip(mean_volume, volume_diff)):
        label = f"({df_dsb.loc[df_dsb.index[i], 'GT_name']}, idx {df_dsb.loc[df_dsb.index[i], 'Head Index']})"  # or another column name, or str(df_dsb.index[i])
        # Offset the text a bit so it doesn’t sit exactly on the point:
        plt.text(x, y, str(label), fontsize=6, ha='left', va='bottom')

    plt.axhline(0, color='red', linestyle='--')
    plt.xlabel("Mean Volume (μm³)")
    plt.ylabel("Volume Difference (μm³)")
    plt.title("Bland-Altman Plot")
    plt.show()


if __name__ == "__main__":
    main()
