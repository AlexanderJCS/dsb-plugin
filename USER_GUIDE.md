# User Guide

This document explains how to use the DSB plugin in Dragonfly. If you have not already, please read the installation instructions and install the plugin.

## Overview

The workflow for this plugin is split into two general steps: preprocessing and beheading. In the DSB user interface, this is denoted by two tabs with the same name. Preprocessing puts the raw data into an intermediate format that can be easily worked with by the plugin. Once preprocessing is finished, the preprocessing data can be loaded to start the beheading step, where a researcher overviews the suggested beheading point and slice direction given by an automatic algorithm, and optionally adjusts the beheading location.

## Preprocessing

The preprocessing step collects the raw data and organizes in a way that is quick and efficient to process. You may provide:

* **(Required)** An ROI (voxel segmentation) of the dendrite and dendritic spines *combined*. Note you may need to union the dendrite ROI and spines ROI if they are separate.
* **(Optional)** Annotations to display in the beheading step. It also allows DSB to infer the dendrite names when exporting the spine heads (in the beheading step).
* **(Optional)** A MultiROI to visualize alongside the dendrite mesh. Useful for visualizing postsynaptic densities (PSDs) to help one better understand where the synapse is.

> ✅ **Tip:** Click the checkbox next to the optional items to enable them, then you may select the annotation/MultiROI

In addition, you must specify an output file (with a `.dsb` file extension). This file will be loaded in the "Beheading" step so that preprocessing does not need to be performed every time DSB is run. The filesize depends on the dataset size, but is generally a couple hundred megabytes.

Once you specify the dendrite + spines and optionally annotations or MultiROI, click the "Run" button. The preprocessing time depends on the size of the dataset, but is generally 10-20 minutes. Once the "Run" button is pressed, minimal human intervention is required. Text on the bottom of the DSB window will display when the preprocessing step is complete.

## Beheading


