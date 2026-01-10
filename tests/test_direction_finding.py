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
Direction Finding Algorithm Tests
==================================
Essential tests for Wi²SAR direction finding system.

Test Coverage:
1. Data Loading - layout, beam pattern construction
2. Core Algorithm - calculate_similarity_matrix accuracy
3. Utility Functions - normalize_angles, haversine_distance
4. Error Handling - invalid inputs
"""

import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from module.data_processing import load_layout, read_measured_rssi_from_file
from module.evaluation import calculate_similarity_matrix, performance_judge, haversine_distance
from module.basic_classes import Location, normalize_angles, BeamPattern


# =============================================================================
# Test 1: Data Loading
# =============================================================================

class TestDataLoading:
    """Tests for data loading functions."""
    
    def test_load_layout(self, layout):
        """Verify layout loads correctly with antenna tags."""
        assert layout is not None
        assert hasattr(layout, 'antenna_tags')
        assert len(layout.antenna_tags) > 0
        
        # Each antenna should have tag and location
        for antenna in layout.antenna_tags:
            assert hasattr(antenna, 'tag')
            assert hasattr(antenna, 'location')
    
    def test_beam_pattern_construction(self, beam_pattern):
        """Verify beam pattern is constructed and interpolated."""
        assert beam_pattern is not None
        assert isinstance(beam_pattern, BeamPattern)
        
        # Raw beam pattern
        assert beam_pattern.beam_pattern is not None
        assert len(beam_pattern.beam_pattern) > 0
        
        # Interpolated beam pattern (should have more entries)
        assert beam_pattern.interpolated_beam_pattern is not None
        assert len(beam_pattern.interpolated_beam_pattern) >= len(beam_pattern.beam_pattern)
    
    def test_load_test_measurement(self, test_measurement):
        """Verify test measurement loads with correct ground truth."""
        rssi_array, true_az, true_el, measured_layout = test_measurement
        
        # Check ground truth (known from test.tsv)
        assert true_az == 180
        assert true_el == 30
        
        # RSSI array should be numpy array with valid values
        assert isinstance(rssi_array, np.ndarray)
        assert len(rssi_array) == len(measured_layout.antenna_tags)
        assert all(-130 <= v <= 0 for v in rssi_array)


# =============================================================================
# Test 2: Core Algorithm - Direction Finding
# =============================================================================

class TestDirectionFinding:
    """Tests for direction finding accuracy."""
    
    def test_direction_finding_accuracy(self, layout, beam_pattern, test_measurement):
        """
        CORE TEST: Verify direction finding predicts correct angle.
        
        Ground truth: (180°, 30°)
        Expected: Algorithm should predict exact angle.
        """
        rssi_array, true_az, true_el, measured_layout = test_measurement
        
        # Run direction finding algorithm
        # Returns: (alg_results, measured_rssi_calibrated)
        # alg_results["a_BcRxB"]["pred"] = (max_idx, max_val, real_loc)
        results, _ = calculate_similarity_matrix(
            measured_layout,
            rssi_array,
            beam_pattern.interpolated_beam_pattern,
            plot_fig=False,
            std_method="z-score",
            algorithm_list=["a_BcRxB"],
            pos_elevation=True,
            smooth_method="none"
        )
        
        # Extract prediction: pred is (max_idx, max_val, real_loc)
        # real_loc is a tuple (azimuth, elevation), not a Location object
        pred_tuple = results["a_BcRxB"]["pred"]
        max_idx, max_val, real_loc = pred_tuple
        
        predicted_az = int(real_loc[0])
        predicted_el = int(real_loc[1])
        
        # Verify accuracy
        assert predicted_az == true_az, \
            f"Azimuth error: predicted {predicted_az}°, expected {true_az}°"
        assert predicted_el == true_el, \
            f"Elevation error: predicted {predicted_el}°, expected {true_el}°"
    
    def test_similarity_score_high(self, layout, beam_pattern, test_measurement):
        """Verify similarity score is reasonable for correct prediction."""
        rssi_array, _, _, measured_layout = test_measurement
        
        results, _ = calculate_similarity_matrix(
            measured_layout,
            rssi_array,
            beam_pattern.interpolated_beam_pattern,
            plot_fig=False,
            algorithm_list=["a_BcRxB"],
            pos_elevation=True
        )
        
        # pred is (max_idx, max_val, real_loc)
        _, max_val, _ = results["a_BcRxB"]["pred"]
        
        # max_val should be positive (higher = better match)
        assert max_val > 0, f"Similarity score should be positive: {max_val}"


# =============================================================================
# Test 3: Utility Functions
# =============================================================================

class TestUtilityFunctions:
    """Tests for helper functions."""
    
    def test_normalize_angles(self):
        """Test angle normalization to valid ranges."""
        # Standard cases
        assert normalize_angles(0, 0) == (0, 0)
        assert normalize_angles(360, 0) == (0, 0)
        assert normalize_angles(-90, 0) == (270, 0)
        assert normalize_angles(450, 0) == (90, 0)
        
        # Large values
        assert normalize_angles(720, 0) == (0, 0)
        assert normalize_angles(-720, 0) == (0, 0)
    
    def test_haversine_distance(self):
        """Test angular distance calculation."""
        # Same point = zero distance
        loc1 = Location(0, 0)
        loc2 = Location(0, 0)
        assert abs(haversine_distance(loc1, loc2)) < 1e-4
        
        # Symmetric
        loc3 = Location(45, 30)
        loc4 = Location(135, -15)
        d1 = haversine_distance(loc3, loc4)
        d2 = haversine_distance(loc4, loc3)
        assert abs(d1 - d2) < 1e-10
    
    def test_performance_judge(self):
        """Test performance evaluation function."""
        true_angles = [Location(180, 30), Location(0, 0)]
        predicted_angles = [Location(180, 30), Location(0, 0)]
        
        # Should complete without error
        performance_judge(true_angles, predicted_angles)


# =============================================================================
# Test 4: Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling with invalid inputs."""
    
    def test_invalid_layout_path(self):
        """Invalid layout path should raise FileNotFoundError."""
        with pytest.raises((FileNotFoundError, OSError)):
            load_layout("/nonexistent/path/layout.yaml")
    
    def test_invalid_data_path(self, layout):
        """Invalid data path should raise FileNotFoundError."""
        with pytest.raises((FileNotFoundError, OSError)):
            read_measured_rssi_from_file("/nonexistent/path/test.tsv", layout)
