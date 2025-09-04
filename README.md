# "Take Me Home, Wi-Fi Drone": Design and Implementation of an Autonomous Wi-Fi Drone System for Wilderness Search and Rescue

## Repository Structure
This repository contains the source code for the Direction Finding Module in our Wi-Fi Drone System. Our paper is under review in Mobicom 2026.

The repository is structured as follows:
```
.
├── data
│   ├── case5-3d
│   │   ├── sheet.tsv ... Measured RSSI data for reference beam pattern
│   │   ├── test.tsv ... Measured RSSI data for testing
│   │   └── layout.yaml ... Layout of the antenna array
├── module
│   ├── evaluation.py ... Evaluation module for performance evaluation
│   ├── data_processing.py ... Data processing module for direction finding
│   ├── plot.py ... Plotting module for visualization
|   ├── rssi_update.py ... Real-time RSSI update module
├── main.py ... Main script for direction finding
├── main_get_rssi.py ... Main script for real-time RSSI update
├── requirements.txt ... Required Python packages
├── df_start.sh ... Script to start the main script on Raspberry Pi
└── README.md
```

## Usage

### Running the Main Script Offline

To run the main script for offline signal processing, place the data files in the `data/case5-3d/test.tsv` and run the following command:

```sh
python main.py --log DEBUG --data-dir ./data/case5-3d --pos-elevation --calibration
```
Example output:

```
No beam pattern file found. Recalculating beam pattern.
....
2024-09-21 08:20:09.953 | INFO     | __main__:main:354 - Running batch processing.
2024-09-21 08:20:09 - Reading measured RSSI from ./data/case5-3d/test.tsv
True angle: (180, 30) for test
2024-09-21 08:20:09.957 | INFO     | module.evaluation:calculate_similarity_matrix:346 - Convert beam pattern from dict to 2D array
2024-09-21 08:20:09.975 | INFO     | module.evaluation:calculate_similarity_matrix:362 - No smoothing applied to the beam pattern
2024-09-21 08:20:10.122 | DEBUG    | module.evaluation:performance_judge:571 - True angle: (180, 30),Predicted angle: (180, 30),Dist: 0.00,Score: 1.00
2024-09-21 08:20:10.123 | INFO     | module.evaluation:performance_judge:578 - Mean distance (rad): 0.00
2024-09-21 08:20:10 - a_BcRxB Score: 0.9999999998/1 (1.00)
2024-09-21 08:20:10 - direction_finding took: 0.1692049503326416 sec
Press Enter to close the plots and exit...
2024-09-21 08:20:44 - Shutting down.
```

### Running the Main Script on Raspberry Pi
To run the main script for real-time signal processing on Raspberry Pi, run the following command:

```sh
bash ./df_start.sh
```
This script will start the main script with the following parameters:
```sh
python main.py --log DEBUG --data-dir ./data/case5-3d --pos-elevation --calibration --real-time
```
