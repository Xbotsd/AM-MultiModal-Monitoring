# AM-MultiModal-Monitoring
**Laser Powder Bed Fusion (LPBF) In-Situ Monitoring System**

This repository contains the official code for the paper: "A Unified Kalman Filter Framework with Offline Edge Intelligence for Multi-Modal In-Situ Monitoring in LPBF and DED".

## Project Structure
- 1_acoustic: Acoustic emission classification (EPFL dataset)
- 2_laser_ultrasound: Laser ultrasound classification (Cranfield dataset)
- 3_fusion: Unified Kalman filter multi-modal fusion
- 4_phase_pointcloud: Phase unwrapping and point cloud defect detection
- 5_control: Closed-loop control and offline edge diagnosis
- 6_visualization: Statistical analysis and figure generation

## Quick Start
1. Install dependencies:
   pip install -r requirements.txt

2. Run a specific module (e.g., acoustic experiment):
   python CODE/1_acoustic/run_eplf_v12.py

## Datasets
- EPFL Acoustic Dataset: https://zenodo.org/records/10449883
- Cranfield LUT Dataset: https://doi.org/10.17862/cranfield.rd.15190191
