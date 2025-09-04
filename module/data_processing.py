"""
Data Processing Module
======================
This module provides functions and classes for data processing in the project.
"""

import yaml
import csv
import numpy as np
import logging
from scipy.interpolate import interp1d, griddata

from module.basic_classes import Location, AntennaTag, IncidentSignal, AntennaLayout, SignalDataset, BeamPattern

logger = logging.getLogger(__name__)


def calc_calib_loc(loc):
    """
    Calculate the calibration location.

    Parameters
    ----------
    loc : module.basic_classes.Location
        The location to calibrate.

    Returns
    -------
    module.basic_classes.Location
        The calibrated location.
    """
    calib_loc = Location(loc.azimuth + 180, -loc.elevation)
    # logger.info(f"Calibrate location {loc} using {calib_loc}.")
    return calib_loc


def load_layout(file_path):
    """
    Load the antenna layout from a YAML file.

    Parameters
    ----------
    file_path : str
        Path to the layout file.

    Returns
    -------
    module.basic_classes.AntennaLayout
        An instance of AntennaLayout.
    """
    with open(file_path, "r") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    antenna_tags = [AntennaTag(line['loc_tag'], line['azimuth'], line['elevation']) for line in data]
    return AntennaLayout(antenna_tags)


def load_signals(file_path, layout):
    """
    Load the signals and RSSI data from a TSV file.

    Parameters
    ----------
    file_path : str
        Path to the signal file.
    layout : AntennaLayout
        The antenna layout.

    Returns
    -------
    tuple
        A SignalDataset instance, a dictionary with RSSI calibration values, and a beam pattern layout.
    """
    incident_signals = []
    rssi_data = []
    bp_rssi_calibration = {}
    bp_layout_tags = []

    with open(file_path) as f:
        reader = csv.reader(f, delimiter='\t')
        angle_dim = parse_header(bp_layout_tags, layout, reader)
        for row in reader:
            incident_angle = Location(int(row[0]), 0) if angle_dim == 1 else Location(int(row[0]), int(row[1]))
            incident_signal = IncidentSignal(incident_angle)
            incident_signals.append(incident_signal)
            rssi_data.append([int(r) for r in row[angle_dim:]])
            for i in range(len(bp_layout_tags)):
                if incident_angle == calc_calib_loc(bp_layout_tags[i].location):
                    bp_rssi_calibration[bp_layout_tags[i].tag] = int(row[angle_dim + i])
                    logger.info(
                        f"RSSI calibration for {bp_layout_tags[i].tag} using calibration location "
                        f"{calc_calib_loc(bp_layout_tags[i].location)}: {int(row[angle_dim + i])}"
                    )
                    break

    rssi_data = np.array(rssi_data)
    bp_layout = AntennaLayout(bp_layout_tags)
    return SignalDataset(incident_signals, layout, rssi_data), bp_rssi_calibration, bp_layout


def parse_header(bp_layout_tags, layout, reader):
    header = next(reader)
    angle_dim = find_angle_dim_from_header(header)
    # Create a bp_layout based on the tags in the header
    for tag_name in header[angle_dim:]:
        tag = layout.find_tag(tag_name)
        if tag:
            bp_layout_tags.append(tag)
        else:
            logger.warning(f"Tag {tag_name} not found in layout.")
    return angle_dim


def find_angle_dim_from_header(header):
    # deal with the header
    # if it's I | <tag1> | <tag2> | ... | <tagN> |, then the first column is the azimuth angle, elevation is 0
    # if it's A | E | <tag1> | <tag2> | ... | <tagN> |, then the first two columns are azimuth and elevation
    if header[0] == 'I':
        angle_dim = 1
    elif header[0] == 'A' and header[1] == 'E':
        angle_dim = 2
    else:
        raise ValueError(f"Invalid header format{header}. Supported formats should start with 'I' or 'A E'.")
    return angle_dim


def recalculate_rssi_calibration(measured_rssi_list, measured_layout):
    """
    Recalculate the RSSI calibration values from the measured RSSI list.

    Parameters
    ----------
    measured_rssi_list : list
        List of tuples with true angle (or None) and measured RSSI values.
    measured_layout : AntennaLayout
        The measured antenna layout.

    Returns
    -------
    dict
        A dictionary with recalculated RSSI calibration values.
    """
    measured_rssi_calibration = {}
    for true_angle, measured_rssi in measured_rssi_list:
        if true_angle is not None:
            for i, tag in enumerate(measured_layout.antenna_tags):
                true_incident_angle = Location(true_angle, 0)
                if true_incident_angle == calc_calib_loc(tag.location):
                    measured_rssi_calibration[tag.tag] = measured_rssi[i]

    logger.info(f"Recalculated RSSI calibration: {measured_rssi_calibration}")
    return measured_rssi_calibration


def construct_beam_pattern(dataset, layout, bp_rssi_calibration, calibration):
    """
    Construct the beam pattern model from the dataset.

    Parameters
    ----------
    dataset : SignalDataset
        The signal dataset.
    layout : AntennaLayout
        The antenna layout.
    bp_rssi_calibration : dict
        The RSSI calibration values.
    calibration: bool
        If calibrate RSSI
    Returns
    -------
    tuple
        A BeamPattern instance and a dictionary of relative locations to average RSSI values,
        both interpolated for every integer azimuth and elevation degree.
    """
    if calibration:
        rssi_calibrated = np.array([bp_rssi_calibration[tag.tag] for tag in layout.antenna_tags])
        rssi_data_calibrated = dataset.rssi_data - rssi_calibrated
    else:
        rssi_data_calibrated = dataset.rssi_data + 63

    beam_pattern = {}
    for i in range(len(dataset.incident_signals)):
        for j in range(len(layout.antenna_tags)):
            if dataset.rssi_data[i][j] <= -92:
                continue
            relative_loc = layout.antenna_tags[j].location.relative_location(dataset.incident_signals[i].location)
            if relative_loc not in beam_pattern:
                beam_pattern[relative_loc] = []
            beam_pattern[relative_loc].append(rssi_data_calibrated[i][j])
            # debug: layout.antenna_tags[j].location; dataset.incident_signals[i].location; relative_loc; RSSI
            logger.info(
                f"RSSI at {relative_loc}({layout.antenna_tags[j].location} - "
                f"{dataset.incident_signals[i].location}): {rssi_data_calibrated[i][j]}"
            )

    beam_pattern_avg = {k: np.mean(v) for k, v in beam_pattern.items()}
    # beam_pattern_std = {k: np.std(v) for k, v in beam_pattern.items()}
    
    if layout.is_3d:
        # Interpolation for every integer azimuth and elevation angle
        interpolated_beam_pattern_avg = {}
        points = np.array([[loc[0], loc[1]] for loc in beam_pattern_avg.keys()])
        values = np.array(list(beam_pattern_avg.values()))

        # Extend points and values for circular interpolation
        points_extended = np.vstack([points, points + [360, 0], points - [360, 0]])
        values_extended = np.tile(values, 3)

        grid_azimuth, grid_elevation = np.meshgrid(np.arange(0, 361, 1), np.arange(-90, 91, 1))
        grid_points = np.vstack([grid_azimuth.ravel(), grid_elevation.ravel()]).T
        interpolated_values = griddata(points_extended, values_extended, grid_points, method='cubic',
                                       fill_value=np.nan)

        for (az, el), val in zip(grid_points, interpolated_values):
            interpolated_beam_pattern_avg[(int(az) % 360, int(el))] = val
        
        # interpolated_beam_pattern_std = {}
        # std_values = np.array(list(beam_pattern_std.values()))
        # std_values_extended = np.tile(std_values, 3)
        # interpolated_std_values = griddata(points_extended, std_values_extended, grid_points, method='cubic',
        #                                    fill_value=np.nan)
        # for (az, el), val in zip(grid_points, interpolated_std_values):
        #     interpolated_beam_pattern_std[(int(az) % 360, int(el))] = val
        
        return BeamPattern(beam_pattern=beam_pattern, interpolated_beam_pattern=interpolated_beam_pattern_avg)
                            # beam_pattern_std=beam_pattern_std, interpolated_beam_pattern_std=interpolated_beam_pattern_std)
        #
        # # Interpolation for every integer azimuth and elevation angle
        # interpolated_beam_pattern_avg = {}
        # points = np.array([[loc[0], loc[1]] for loc in beam_pattern_avg.keys()])
        # values = np.array(list(beam_pattern_avg.values()))
        #
        # grid_azimuth, grid_elevation = np.meshgrid(np.arange(0, 361, 1), np.arange(-180, 181, 1))
        # grid_points = np.vstack([grid_azimuth.ravel(), grid_elevation.ravel()]).T
        # interpolated_values = griddata(points, values, grid_points, method='linear', fill_value=np.nan)
        #
        # for (az, el), val in zip(grid_points, interpolated_values):
        #     interpolated_beam_pattern_avg[(int(az), int(el))] = val
    else:
        # Interpolation for every integer azimuth angle
        interpolated_beam_pattern_avg = {}
        azimuths = np.array([loc[0] for loc in beam_pattern_avg.keys()])
        values = np.array(list(beam_pattern_avg.values()))

        # Ensure the azimuths cover the circular range by adding points at the wrap-around
        azimuths = np.concatenate([azimuths, azimuths + 360])
        values = np.concatenate([values, values])

        angles = np.arange(0, 361, 1)

        f = interp1d(azimuths, values, kind='cubic', fill_value='extrapolate')
        interp_values = f(angles)
        for angle, val in zip(angles, interp_values):
            interpolated_beam_pattern_avg[(angle, 0)] = val

        return BeamPattern(beam_pattern=beam_pattern, interpolated_beam_pattern=interpolated_beam_pattern_avg)


def read_measured_rssi_from_file(file_path, layout):
    """
    Read measured RSSI values from a file and create a measured layout.

    Parameters
    ----------
    file_path : str
        Path to the measure file.
    layout : AntennaLayout
        The antenna layout.

    Returns
    -------
    tuple
        A list of tuples with the true angle (or None) and measured RSSI values, and a measured layout.
    """
    measured_rssi_list = []
    measured_layout_tags = []

    with open(file_path, 'r') as f:
        reader = csv.reader(f, delimiter='\t')
        angle_dim = parse_header(measured_layout_tags, layout, reader)

        for row in reader:
            if row[0] == 'N':
                true_angle = None
            else:
                true_angle = Location(int(row[0]), 0) if angle_dim == 1 else Location(int(row[0]), int(row[1]))
            measured_rssi = np.array([float(val) for val in row[angle_dim:]])
            measured_rssi_list.append((true_angle, measured_rssi))

    measured_layout = AntennaLayout(measured_layout_tags)
    if angle_dim == 1:
        measured_layout.is_3d = False
    else:
        measured_layout.is_3d = True
    return measured_rssi_list, measured_layout


def prompt_user_for_measured_rssi(header):
    """
    Prompt the user to input multiple measured RSSI values.

    Parameters
    ----------
    header : list
        List of antenna tag names.

    Returns
    -------
    list
        A list of tuples with the true angle (or None) and measured RSSI values.
    """
    measured_rssi_list = []
    while True:
        user_input = input(
            f"Please enter true angle and values for {header} separated by commas, or 'done' to finish: ")
        if user_input.lower() == 'done':
            break
        values = user_input.split(',')
        if values[0].upper() == 'N':
            true_angle = None
        else:
            true_angle = int(values[0])
        measured_rssi = np.array([int(val) for val in values[1:]])
        measured_rssi_list.append((true_angle, measured_rssi))
    return measured_rssi_list


# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger.info("Data processing module loaded.")
