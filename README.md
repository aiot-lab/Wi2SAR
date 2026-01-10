# "Take Me Home, Wi-Fi Drone": A Drone-based Wireless System for Wilderness Search and Rescue

## Overview

This repository contains the source code for the Direction Finding Module in our Wi-Fi Drone System. Our paper is under review in Mobicom 2026.

---

## Repository Structure

```
.
├── data/                       # Beam pattern datasets (different cases)
│   ├── case5-3d/              # Example case with 3D antenna layout
│   │   ├── sheet.tsv          # Reference beam pattern RSSI data
│   │   ├── test.tsv           # Test RSSI measurements
│   │   └── layout.yaml        # Antenna array layout configuration
├── module/                     # Core algorithm modules
│   ├── basic_classes.py       # Basic data structures
│   ├── data_processing.py     # Data processing for direction finding
│   ├── evaluation.py          # Performance evaluation
│   ├── plot.py                # Visualization utilities
│   └── rssi_update.py         # Real-time RSSI updates
├── tests/                      # Pytest test suite
│   ├── conftest.py            # Test fixtures
│   ├── test_case5_3d.tsv      # Test measurement data
│   └── test_direction_finding.py  # Algorithm tests
├── rt-scripts/                 # Raspberry Pi runtime scripts
│   ├── df_start.sh            # Start direction finding
│   └── df_stop.sh             # Stop direction finding
├── main.py                     # Main direction finding script
├── main_get_rssi.py           # Real-time RSSI collection script
├── quick-start.ipynb          # Interactive tutorial notebook
├── pyproject.toml             # Project configuration
├── requirements.txt           # Package dependencies
└── README.md                  # This file
```

---

## Quick Start

### For Users (Running the System)

If you want to use the direction finding system for your own measurements:

#### 1. Install Dependencies

**Using uv (recommended, faster):**
```bash
pip install uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

**Using pip:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

#### 2. Run Offline Direction Finding

Process pre-collected RSSI data:

```bash
python main.py --log INFO --data-dir ./data/case5-3d --pos-elevation --calibration
```

**Parameters:**
- `--data-dir`: Path to beam pattern case folder (e.g., `./data/case5-3d`)
- `--pos-elevation`: Enable elevation angle estimation
- `--calibration`: Enable RSSI calibration
- `--log`: Logging level (DEBUG, INFO, WARNING, ERROR)

**Example Output:**
```
2024-09-21 08:20:09 - Reading measured RSSI from ./data/case5-3d/test.tsv
True angle: (180, 30) for test
...
a_BcRxB Score: 0.9999999998/1 (1.00)
direction_finding took: 0.169 sec
```

#### 3. Run on Raspberry Pi (Real-time Mode)

For real-time RSSI collection and direction finding:

```bash
bash ./rt-scripts/df_start.sh
```

This runs:
```bash
python main.py --log DEBUG --data-dir ./data/case5-3d --realtime --calibration --pos-elevation --no-plot
```

#### 4. Interactive Tutorial

Explore the Jupyter notebook for an interactive walkthrough:

```bash
jupyter notebook quick-start.ipynb
```

---

### For Developers (Contributing & Testing)

If you're developing new features or contributing to the project:

#### 1. Install Development Dependencies

Install the package with development tools (pytest, black, flake8):

**Using uv:**
```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

**Using pip:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

#### 2. Run Tests

The project uses pytest for testing. Tests use the existing beam pattern cases in `data/`.

**Run all tests:**
```bash
pytest tests/ -v
```

**Run specific test class:**
```bash
pytest tests/test_direction_finding.py::TestLayoutLoading -v
```

**Run with coverage:**
```bash
pytest tests/ --cov=module --cov-report=html
```

**Test structure:**
- Beam pattern data from `data/case5-3d/` (layout.yaml, sheet.tsv)
- Test measurements stored in `tests/test_case5_3d.tsv`
- Fixtures in `tests/conftest.py` provide reusable test components

#### 3. Code Quality

**Format code with black:**
```bash
black module/ tests/ main.py
```

**Check code style:**
```bash
flake8 module/ tests/ main.py
```

#### 4. Add New Beam Pattern Cases

To add a new test case:

1. Create a new folder: `data/your-case-name/`
2. Add required files:
   - `layout.yaml` - Antenna configuration
   - `sheet.tsv` - Reference beam pattern measurements
   - `test.tsv` - Test measurements

3. Use it in tests or scripts:
   ```bash
   python main.py --data-dir ./data/your-case-name --pos-elevation --calibration
   ```

---

## Project Links

- **Website:** https://aiot-lab.github.io/Wi2SAR
- **Documentation:** https://aiot-lab.github.io/Wi2SAR
- **Repository:** https://github.com/aiot-lab/Wi2SAR
- **Organization:** https://aiot.hku.hk

---

## Citation

If you use this code in your research, please cite our paper (under review):

```bibtex
@inproceedings{wi2sar2026,
  title={"Take Me Home, Wi-Fi Drone": A Drone-based Wireless System for Wilderness Search and Rescue},
  author={Hou, Weiying and Yu, Luca Jiang-Tao and Wu, Chenshu},
  booktitle={ACM MobiCom},
  year={2026}
}
```

---

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.
