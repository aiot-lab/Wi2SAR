# Copyright 2026 Weiying Hou, AIoT Lab, The University of Hong Kong
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Pytest Configuration and Fixtures
==================================
Fixtures for Wi²SAR direction finding algorithm testing.

Test Strategy:
- Layout and beam pattern: use data/case5-3d/ (real calibration data)
- Test measurements: use tests/test_case5_3d.tsv (separate test file)
"""

import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from module.data_processing import (
    load_layout,
    load_signals,
    construct_beam_pattern,
    read_measured_rssi_from_file,
)
from module.basic_classes import BeamPattern


# =============================================================================
# Path Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def beam_pattern_dir():
    """Path to beam pattern calibration data (layout.yaml, sheet.tsv)."""
    return Path(__file__).parent.parent / "data" / "case5-3d"


@pytest.fixture(scope="session")
def test_data_path():
    """Path to test measurement file in tests/ directory."""
    return Path(__file__).parent / "test_case5_3d.tsv"


# =============================================================================
# Core Data Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def layout(beam_pattern_dir):
    """Load antenna layout from YAML."""
    layout_file = beam_pattern_dir / "layout.yaml"
    return load_layout(str(layout_file))


@pytest.fixture(scope="session")
def beam_pattern(beam_pattern_dir, layout):
    """Build interpolated beam pattern from calibration data."""
    sheet_file = beam_pattern_dir / "sheet.tsv"
    
    dataset, rssi_calibration, bp_layout = load_signals(str(sheet_file), layout)
    bp = construct_beam_pattern(dataset, bp_layout, rssi_calibration, calibration=True)
    
    return bp


@pytest.fixture(scope="session")
def test_measurement(test_data_path, layout):
    """
    Load test measurement with known ground truth.
    
    Returns: (rssi_array, true_azimuth, true_elevation)
    """
    measured_list, measured_layout = read_measured_rssi_from_file(
        str(test_data_path), layout
    )
    
    # First measurement: (180, 30) degrees
    true_location, rssi_array = measured_list[0]
    true_azimuth = int(true_location.azimuth)
    true_elevation = int(true_location.elevation)
    
    return rssi_array, true_azimuth, true_elevation, measured_layout
