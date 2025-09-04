import numpy as np
# from scipy.fft import fft2, ifft2
from loguru import logger

from module.basic_classes import Location, SphericalMapper
from module.plot import plotly_subplots
import plotly.graph_objects as go
import plotly.subplots

from module.plot import plot_beam_pattern_2d, plot_beam_pattern_3d, plot_similarity_matrix, wait_for_user

NOISE_LEVEL_DB = -127

from contextlib import contextmanager
import time

SKIP_TIMEIT_OUTPUT = True

@contextmanager
def timeit(name=""):
    start = time.time()  # Record the start time
    try:
        yield  # Yield control back to the block using the context
    finally:
        end = time.time()  # Record the end time
        if not SKIP_TIMEIT_OUTPUT:
            print(f"[{name}] Time elapsed: {end - start:.2f} seconds")


def cross_correlation_2d_fft(input_A, input_B, input_type="AB"):
    """
    Calculate cross-correlation of two 2D arrays using FFT.

    Parameters
    ----------
    A : numpy.ndarray
        The first 2D array.
    B : numpy.ndarray
        The second 2D array.
    input_type: str
        The input type ("AB", "fAB", "AfB", "fAfB").
    
    Returns
    -------
    tuple
        The cross-correlation of the two arrays.
    """
    if "fA" in input_type:
        fA = input_A
    else:
        fA = np.fft.rfft2(input_A)
    if "fB" in input_type:
        fB = input_B
    else:
        fB = np.fft.rfft2(input_B)
    fM = fA * np.conj(fB)
    M = np.fft.irfft2(fM).real
    return M


def conv2d_fft(input_A, input_B, input_type="AB"):
    """
    Calculate convolution of two 2D arrays using FFT.

    Parameters
    ----------
    A : numpy.ndarray
        The first 2D array.
    B : numpy.ndarray
        The second 2D array.
    input_type: str
        The input type ("AB", "fAB", "AfB", "fAfB").
    
    Returns
    -------
    tuple
        The convolution of the two arrays.
    """
    if "fA" in input_type:
        fA = input_A
    else:
        fA = np.fft.rfft2(input_A)
    # fA = np.fft.rfft2(A)
    if "fB" in input_type:
        fB = input_B
    else:
        fB = np.fft.rfft2(input_B)
    # fB = np.fft.rfft2(B)
    fM = fA * fB
    M = np.fft.irfft2(fM).real
    return M


def create_sinc_win(grid_size=360, r_zero=30):
    half_size = grid_size // 2
    x = np.linspace(-half_size, half_size, grid_size)
    y = np.linspace(-half_size, half_size, grid_size)
    x, y = np.meshgrid(x, y)

    # sinc function
    z = np.sinc(np.sqrt(x ** 2 + y ** 2) / r_zero)
    z = np.roll(z, 180, axis=1)
    z = np.roll(z, 180, axis=0)
    x += half_size
    y += half_size
    return x, y, z


def find_max_idx_2d(arr, map_start_from=(0, 0), loc_origin_at_zero=False):
    """
    Find the maximum value in a 2D array, and map the index to the original coordinate system.

    Parameters
    ----------
    arr : numpy.ndarray
        The 2D array.
    map_start_from : tuple
        The starting point of the mapping.
    """
    with timeit("Find max"):
        max_idx = np.unravel_index(np.argmax(arr), arr.shape)
        max_val = arr[max_idx]
    with timeit("SphericalMapper"):
        if "smapper" in find_max_idx_2d.__dict__:
            smapper = find_max_idx_2d.smapper
        else:
            smapper = SphericalMapper()
            find_max_idx_2d.smapper = smapper
            
        if loc_origin_at_zero:
            if "smapper_at_zero" in find_max_idx_2d.__dict__:
                smapper_at_zero = find_max_idx_2d.smapper
            else:
                smapper_at_zero = SphericalMapper(turn_to_zero_at_origin=loc_origin_at_zero)
                find_max_idx_2d.smapper_at_zero = smapper_at_zero
                
            real_loc = smapper_at_zero.offset(max_idx[0], max_idx[1], start_from=map_start_from)
        real_loc = smapper.offset(max_idx[0], max_idx[1], start_from=map_start_from)
    return max_idx, max_val, real_loc


def add_subfigure(subfigs, xaxis, yaxis, data, row, col, title, max_idx=None, max_val=None, real_loc=None):
    fig_id = (row - 1) * 4 + col - 1
    subfigs.add_trace(
        go.Surface(
            x=xaxis, y=yaxis,
            z=data.T, colorscale="viridis", showscale=False
        ),
        row=row, col=col
    )
    if max_idx is not None and max_val is not None and real_loc is not None:
        subfigs.add_trace(
            go.Scatter3d(x=[max_idx[0]], y=[max_idx[1]], z=[max_val], mode='markers', marker=dict(size=5, color='red')),
            row=row, col=col)
        title += f" max {max_idx} is {real_loc}"
    subfigs.layout.annotations[fig_id].update(text=title)


def bp_form_cyclic_matrix(old_matrix):
    new_matrix = np.zeros((old_matrix.shape[0], old_matrix.shape[1] * 2 - 2))
    new_matrix[:, :old_matrix.shape[1]] = old_matrix
    # remove upper and lower bound
    old_matrix_to_cat = old_matrix[:, 1:-1]
    assert old_matrix_to_cat.shape[1] == 179
    old_matrix_to_cat_roll_a = np.roll(old_matrix_to_cat, 180, axis=0)
    old_matrix_to_cat_roll_a_flip = np.flip(old_matrix_to_cat_roll_a, axis=1)
    new_matrix[:, old_matrix.shape[1]:] = old_matrix_to_cat_roll_a_flip
    assert new_matrix.shape[1] == 360 and new_matrix.shape[0] == 360
    return new_matrix


def calculate_similarity_matrix(layout, measured_rssi, beam_pattern_avg, plot_fig=True, std_method="z-score",
                                algorithm_list=["a_BcRxB"], pos_elevation=True, smooth_method="none"):
    """
    Calculate the similarity matrix for angle prediction.

    Parameters
    ----------
    layout : AntennaLayout
        The antenna layout.
    measured_rssi : numpy.ndarray
        The measured RSSI values.
    beam_pattern_avg : dict
        The average RSSI values of the beam pattern.
    plot_fig : bool
        Whether to plot the similarity
    std_method : str
        The standardization method ("min-max", "z-score", "max-abs", "none").
    algorithm_list : list
        The list of algorithms to use for angle prediction.
    Returns
    -------
    dict
        A dictionary of angles and their similarity scores.

    Notes
    -----
    This function offsets the layout, effectively rotating the beam pattern by -offset.
    Since the initial beam pattern is relative to the incident signal = 0, rotating the
    layout by -offset makes the beam pattern relative to the incident signal = offset.
    """

    ALG_NAMES = {
        "a_BcRxB": "argmax (Beam pattern conv Rssi xcorr Beam pattern)",
        "a_BcR": "argmax (Beam pattern conv Rssi)",
    }

    alg_results = {}
    for alg in algorithm_list:
        alg_results[alg] = {}

    def standardization(arr, method="z-score"):
        """
        Standardize the RSSI values.

        Parameters
        ----------
        arr : numpy.ndarray
            The RSSI values.
        method : str
            The standardization method ("min-max", "z-score", "max-abs", "none").
        """

        def min_max_normalize(arr):
            return (arr - arr.min()) / (arr.max() - arr.min())

        def z_score_normalize(arr):
            if arr.std() == 0:
                return arr
            
            return (arr - arr.mean()) / arr.std()
        
        def z_score_nonzero_normalize(arr):
            # only perform z-score normalization on non-zero elements
            arr_copy = arr.copy()
            # avoid division by zero
            if arr_copy[arr_copy != 0].std() == 0:
                return arr
            
            arr_copy[arr_copy != 0] = (arr_copy[arr_copy != 0] - arr_copy[arr_copy != 0].mean()) / arr_copy[arr_copy != 0].std()
            return arr_copy
        
        def rm_mean_l2_normalize_nonzero(arr):
            # only perform normalization on non-zero elements
            arr_copy = arr.copy()
            # remove mean
            arr_copy[arr_copy != 0] = arr_copy[arr_copy != 0] - arr_copy[arr_copy != 0].mean()
            # l2 normalization
            arr_copy[arr_copy != 0] = arr_copy[arr_copy != 0] / np.linalg.norm(arr_copy[arr_copy != 0])
            return arr_copy
            
            
        def max_abs_normalize(arr):
            return arr / np.abs(arr).max()

        if method == "min-max":
            return min_max_normalize(arr)
        elif method == "z-score":
            return z_score_normalize(arr)
        elif method == "z-score-nonzero":
            return z_score_nonzero_normalize(arr)
        elif method == "rm-mean-l2-nonzero":
            return rm_mean_l2_normalize_nonzero(arr)
        elif method == "max-abs":
            return max_abs_normalize(arr)
        elif method == "pad_zero_min_and_z-score":
            arr_copy = arr.copy()
            arr_copy[arr_copy == 0] = np.min(arr_copy[arr_copy != 0])   # pad zero with min value   
            # print(f"arr_copy: {arr_copy} before normalization, type: {arr_copy.dtype}")
            return z_score_normalize(arr_copy)
        elif method == "none":
            return arr
        else:
            raise ValueError("Invalid method.")

    
    measured_rssi_calibrated = measured_rssi - NOISE_LEVEL_DB
    
    FEATURE_PAD_MISSING_VALUES = True
    FEATURE_SMOOTH_NON_ZERO_VALUES = True
    WIN_BUFFER = 5
    
    if FEATURE_PAD_MISSING_VALUES:
        # save last non-zero rssi value for each antenna
        # buffer size is 5, use a deque to store the last 5 measurements
        # if zero value is on the antenna, use the mean value to pad the missing values
        # then record the original value in the buffer        
        import collections
        
        if "rssi_buffer" in calculate_similarity_matrix.__dict__:
            rssi_buffer = calculate_similarity_matrix.rssi_buffer
        else:
            rssi_buffer = collections.defaultdict(collections.deque)
            # initialize the buffer for each antenna
            for i in range(len(layout.antenna_tags)):
                l = layout.antenna_tags[i]
                rssi_buffer[l] = collections.deque(maxlen=WIN_BUFFER)
        
        for i, l in enumerate(layout.antenna_tags):
            original_rssi = measured_rssi_calibrated[i].copy()
            # if the current value is zero, pad the missing values with the mean value
            if len(rssi_buffer[l]) > 0:
                if measured_rssi_calibrated[i] == 0:
                    # calculate the mean value of non-zero values in the buffer
                    buffered_non_zero = [val for val in rssi_buffer[l] if val != 0]
                    if len(buffered_non_zero) == 0:
                        mean_val_non_zero = 0
                    else:
                        mean_val_non_zero = np.mean(buffered_non_zero)
                    measured_rssi_calibrated[i] = mean_val_non_zero
                    # logger.debug(f"Pad missing value on ant {i} with mean value: {mean_val_non_zero}, buffer: {rssi_buffer[l]}")
                else:
                    if FEATURE_SMOOTH_NON_ZERO_VALUES:
                        # if the current value is not zero, use mean value to replace it
                        buffered_non_zero = [val for val in rssi_buffer[l] if val != 0]
                        if len(buffered_non_zero) == 0:
                            mean_val_non_zero = 0
                        else:
                            mean_val_non_zero = np.mean(buffered_non_zero)
                        measured_rssi_calibrated[i] = mean_val_non_zero
                        # logger.debug(f"Smooth non-zero value on ant {i} with mean value: {mean_val_non_zero}, buffer: {rssi_buffer[l]}")
            # buffer the last 5 values
            rssi_buffer[l].append(original_rssi)
            
        calculate_similarity_matrix.rssi_buffer = rssi_buffer
            
    measured_rssi_normalized = standardization(measured_rssi_calibrated, method=std_method)

    if layout.is_3d:
        ###########################################################################################
        # Prepare the 3D beam pattern and measured RSSI
        ###########################################################################################
        # convert beam_pattern_avg from dict to 2D array
        
        # cache beam_pattern_avg_array to avoid recalculation
        if "beam_pattern_avg_array" not in calculate_similarity_matrix.__dict__:
            with timeit("Calculate beam_pattern_avg_array"):
                beam_pattern_avg_array = np.zeros((360, 181))
                logger.info("Convert beam pattern from dict to 2D array")
                for azimuth, elevation in beam_pattern_avg:
                    beam_pattern_avg_array[azimuth, elevation + 90] = beam_pattern_avg[(azimuth, elevation)]
                
                if smooth_method == "gaussian":
                    logger.info("Smooth the beam pattern by Gaussian filter")
                    import scipy.ndimage
                    # smooth the beam pattern by averaging the values of the neighboring cells
                    sigma = 5
                    beam_pattern_avg_array = scipy.ndimage.gaussian_filter(beam_pattern_avg_array, sigma=sigma)
                elif smooth_method == "median":
                    import scipy.ndimage
                    # smooth the beam pattern by averaging the values of the neighboring cells
                    size = 3
                    beam_pattern_avg_array = scipy.ndimage.median_filter(beam_pattern_avg_array, size=size)
                else:
                    logger.info("No smoothing applied to the beam pattern")
                    
                beam_pattern_avg_array = standardization(beam_pattern_avg_array, method=std_method)
                beam_pattern_avg_array_cyclic = bp_form_cyclic_matrix(beam_pattern_avg_array)
                beam_pattern_avg_array_cyclic_fft = np.fft.rfft2(beam_pattern_avg_array_cyclic)
                
                # cache above calculation
                calculate_similarity_matrix.beam_pattern_avg_array = beam_pattern_avg_array
                calculate_similarity_matrix.beam_pattern_avg_array_cyclic = beam_pattern_avg_array_cyclic
                calculate_similarity_matrix.beam_pattern_avg_array_cyclic_fft = beam_pattern_avg_array_cyclic_fft
        else:
            with timeit("Use cached beam_pattern"):
                beam_pattern_avg_array = calculate_similarity_matrix.beam_pattern_avg_array
                beam_pattern_avg_array_cyclic = calculate_similarity_matrix.beam_pattern_avg_array_cyclic
                beam_pattern_avg_array_cyclic_fft = calculate_similarity_matrix.beam_pattern_avg_array_cyclic_fft
            
        with timeit("Prepare measured_rssi_normalized_pad"):
            # Measured RSSI
            measured_rssi_normalized_pad_cyclic = np.zeros(beam_pattern_avg_array_cyclic.shape)
            for i, l in enumerate(layout.antenna_tags):
                azimuth = l.location.azimuth
                elevation = l.location.elevation
                measured_rssi_normalized_pad_cyclic[azimuth, elevation + 90] = measured_rssi_normalized[i]
                    
        ###########################################################################################
        # Prepare the 3D beam pattern and measured RSSI
        ###########################################################################################
            
            ###########################################################################################
            # Use Beampattern to recover the incident signal
            ###########################################################################################
        if "a_BcRxB" in algorithm_list or "a_BcR" in algorithm_list:
            with timeit("Calculate a_BcRxB"):
                with timeit("Convolution Twice"):
                    beam_pattern_conv_measured_rssi_normalized_pad_cyclic = conv2d_fft(beam_pattern_avg_array_cyclic_fft,
                                                                                    measured_rssi_normalized_pad_cyclic,
                                                                                    input_type="fAB")
                    bp_conv_rssi_x_beam_pattern = cross_correlation_2d_fft(beam_pattern_conv_measured_rssi_normalized_pad_cyclic,
                                                                        beam_pattern_avg_array_cyclic_fft,
                                                                        input_type="AfB")
                    
                if pos_elevation:
                    min_val = np.min(bp_conv_rssi_x_beam_pattern)
                    bp_conv_rssi_x_beam_pattern[:, :90] = min_val
                    bp_conv_rssi_x_beam_pattern[:, 270:] = min_val
                argmax_bp_conv_rssi_x_beam_pattern = find_max_idx_2d(bp_conv_rssi_x_beam_pattern, map_start_from=(0, 0))
                alg_results["a_BcRxB"] = {"pred": argmax_bp_conv_rssi_x_beam_pattern}
                
        return alg_results, measured_rssi_calibrated

    else:
        similarity_scores = []
        angles = list(range(0, 360, 1))

        for offset in angles:
            # Offset the layout: rotate the beam pattern by -offset
            # Since initial beam pattern is relative to the incident signal = 0
            # then if we rotate the layout by -offset, the beam pattern will be relative to the incident signal = offset
            offset_tags = layout.add_offset((-offset, 0)).antenna_tags
            offset_rssi = [beam_pattern_avg[(tag.location.azimuth, tag.location.elevation)] for tag in offset_tags]

            # Normalize the sample RSSI values
            offset_rssi_normalized = standardization(np.array(offset_rssi), std_method)

            similarity = calculate_similarity(measured_rssi_normalized, offset_rssi_normalized, "cosine")
            similarity_scores.append(similarity)

        similarity_scores = np.array(similarity_scores)
        normalized_similarity = (similarity_scores - similarity_scores.min()) / (
                    similarity_scores.max() - similarity_scores.min())

        similarity_matrix = dict(zip(angles, normalized_similarity))

        if plot_fig:
            plot_similarity_matrix(similarity_matrix)
        return similarity_matrix


def calculate_similarity(rssi, sample_rssi, method="euclidean"):
    """
    Calculate similarity between two RSSI vectors.

    Parameters
    ----------
    rssi : numpy.ndarray
        The RSSI values to compare.
    sample_rssi : numpy.ndarray
        The sample RSSI values.
    method : str
        The similarity calculation method ("cosine" or "euclidean").

    Returns
    -------
    float
        The similarity score.
    """
    rssi = np.array(rssi)
    sample_rssi = np.array(sample_rssi)
    if method == "cosine":
        return np.dot(rssi, sample_rssi) / (np.linalg.norm(rssi) * np.linalg.norm(sample_rssi))
    elif method == "euclidean":
        return np.linalg.norm(rssi - sample_rssi)

def haversine_distance(loc1, loc2, radius=1):
    """
    Calculate the great-circle distance between two points on the surface of a sphere using the Haversine formula.
    
    Parameters:
    loc1, loc2: Location
        The locations of the two points.
    
    Returns:
    Great-circle distance
    """
    theta1, phi1 = np.radians(loc1.elevation), np.radians(loc1.azimuth)
    theta2, phi2 = np.radians(loc2.elevation), np.radians(loc2.azimuth)

    delta_theta = theta2 - theta1
    delta_phi = phi2 - phi1

    a = np.sin(delta_theta / 2) ** 2 + np.cos(theta1) * np.cos(theta2) * np.sin(delta_phi / 2) ** 2 + 1e-10
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    distance = radius * c

    return distance


def performance_judge(true_angles, predicted_angles):
    """
    Judge the performance of the angle prediction.

    Parameters
    ----------
    true_angles : list
        List of true angles.
    predicted_angles : list
        List of predicted angles.

    Returns
    -------
    float
        The performance score.
    """
    score = 0
    dist_all = []
    
    for true_angle, predicted_angle in zip(true_angles, predicted_angles):
        assert isinstance(true_angle, Location)
        assert isinstance(predicted_angle, Location)
    
        if true_angle is not None:
            # Use the Haversine formula to calculate the great-circle distance
            distance = haversine_distance(true_angle, predicted_angle, radius=1)
            dist_all.append(distance)
            # score_this = 1 - distance
            score_this = np.cos(distance)
            logger.debug(
                f"True angle: {true_angle},"
                f"Predicted angle: {predicted_angle},"
                f"Dist: {distance:.2f},"
                f"Score: {score_this:.2f}")
            score += score_this

    logger.info(f"Mean distance (rad): {np.mean(dist_all):.2f}")

    return score
