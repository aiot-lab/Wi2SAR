"""
Basic Classes Module
====================
This module provides basic classes used in the project.
"""
import os
import numpy as np


def normalize_angles(azimuth, elevation):
    """
    Normalize azimuth and elevation angles.

    Parameters
    ----------
    azimuth : float
        The azimuth angle in degrees.
    elevation : float
        The elevation angle in degrees.

    Returns
    -------
    tuple
        Normalized azimuth (0-360) and elevation (-90 to 90).
    """
    azimuth = azimuth % 360
    if elevation > 90:
        elevation = 180 - elevation
        azimuth = (azimuth + 180) % 360
    elif elevation < -90:
        elevation = -180 - elevation
        azimuth = (azimuth + 180) % 360
    # assert -90 <= elevation <= 90
    return azimuth, elevation


class Location:
    """
    Class to represent a location with azimuth and elevation.
    """

    def __init__(self, azimuth, elevation):
        """
        Initialize a Location instance.

        Parameters
        ----------
        azimuth : float
            The azimuth angle in degrees.
        elevation : float
            The elevation angle in degrees.
        """
        self.azimuth, self.elevation = normalize_angles(azimuth, elevation)

    def set_location(self, azimuth, elevation):
        """
        Set the location with new azimuth and elevation.

        Parameters
        ----------
        azimuth : float
            The new azimuth angle in degrees.
        elevation : float
            The new elevation angle in degrees.
        """
        self.azimuth = azimuth
        self.elevation = elevation

    def relative_location(self, other):
        """
        Calculate the relative location to another location.

        Parameters
        ----------
        other : Location
            Another Location instance.

        Returns
        -------
        tuple
            Relative azimuth and elevation angles.
        """
        diff_azimuth = int(self.azimuth - other.azimuth)
        diff_elevation = int(self.elevation - other.elevation)
        return normalize_angles(diff_azimuth, diff_elevation)

    def abs_inferior_arc_to(self, other):
        """
        Calculate the inferior arc to another location.

        Parameters
        ----------
        other : Location
            Another Location instance.

        Returns
        -------
        float
            The inferior arc angle.
        """
        rel_arc = self.relative_location(other)
        if rel_arc[0] > 180:
            rel_arc = (360 - rel_arc[0], rel_arc[1])

        return rel_arc

    def __str__(self):
        return str((self.azimuth, self.elevation))

    def __hash__(self):
        return hash((self.azimuth, self.elevation))

    def __eq__(self, other):
        if isinstance(other, Location):
            return self.azimuth == other.azimuth and self.elevation == other.elevation
        return False

    def __repr__(self):
        return self.__str__()


class AntennaTag:
    """
    Class to represent an antenna tag with azimuth and elevation.
    """

    def __init__(self, tag, azimuth, elevation):
        """
        Initialize an AntennaTag instance.

        Parameters
        ----------
        tag : str
            The tag name.
        azimuth : float
            The azimuth angle in degrees.
        elevation : float
            The elevation angle in degrees.
        """
        self.tag = tag
        self.location = Location(azimuth, elevation)

    def __str__(self):
        return "{}@{}".format(self.tag, self.location)

    def __repr__(self):
        return self.__str__()

    def relative_location(self, other):
        """
        Calculate the relative location to another location.

        Parameters
        ----------
        other : Location
            Another Location instance.

        Returns
        -------
        tuple
            Relative azimuth and elevation angles.
        """
        return self.location.relative_location(other)


class IncidentSignal:
    """
    Class to represent an incident signal with various attributes.
    """

    def __init__(self, location, tx_power=None, frequency=None, bandwidth=None, distance=None):
        """
        Initialize an IncidentSignal instance.

        Parameters
        ----------
        location : Location
            The location of the signal.
        tx_power : float, optional
            The transmission power.
        frequency : float, optional
            The frequency of the signal.
        bandwidth : float, optional
            The bandwidth of the signal.
        distance : float, optional
            The distance from the source.
        """
        self.location = location
        self.tx_power = tx_power
        self.frequency = frequency
        self.bandwidth = bandwidth
        self.distance = distance


class AntennaLayout:
    """
    Class to represent an antenna layout with multiple antenna tags.
    """

    def __init__(self, antenna_tags):
        """
        Initialize an AntennaLayout instance.

        Parameters
        ----------
        antenna_tags : list
            List of AntennaTag instances.
        """
        self.antenna_tags = antenna_tags
        self.is_3d = any(tag.location.elevation != 0 for tag in antenna_tags)

    def __str__(self):
        return str(self.antenna_tags)

    def add_offset(self, offset):
        """
        Add an offset to the layout's antenna tags.

        Parameters
        ----------
        offset : tuple
            The offset to add (azimuth, elevation).

        Returns
        -------
        AntennaLayout
            A new AntennaLayout instance with updated tags.
        """
        updated_tags = []
        for tag in self.antenna_tags:
            new_azimuth = tag.location.azimuth + offset[0]
            new_azimuth = new_azimuth % 360
            new_elevation = tag.location.elevation + offset[1]
            if new_elevation > 90:
                new_elevation = 180 - new_elevation
                new_azimuth = (new_azimuth + 180) % 360
            elif new_elevation < -90:
                new_elevation = -180 - new_elevation
                new_azimuth = (new_azimuth + 180) % 360
            updated_tags.append(AntennaTag(tag.tag, new_azimuth, new_elevation))
        return AntennaLayout(updated_tags)

    def find_tag(self, tag_name):
        """
        Find an antenna tag by name.

        Parameters
        ----------
        tag_name : str
            The name of the tag to find.

        Returns
        -------
        AntennaTag or None
            The found AntennaTag instance or None if not found.
        """
        for tag in self.antenna_tags:
            if tag.tag == tag_name:
                return tag
        return None


class SignalDataset:
    """
    Class to represent a dataset of signals and RSSI data.
    """

    def __init__(self, incident_signals, layout, rssi_data=None):
        """
        Initialize a SignalDataset instance.

        Parameters
        ----------
        incident_signals : list
            List of IncidentSignal instances.
        layout : AntennaLayout
            The antenna layout.
        rssi_data : numpy.ndarray, optional
            The RSSI data matrix.
        """
        self.incident_signals = incident_signals
        self.layout = layout
        self.rssi_data = rssi_data


class BeamPattern:
    """
    Class to represent a beam pattern.
    """

    def __init__(self, data_dir: str = None, 
                beam_pattern: dict = None, 
                interpolated_beam_pattern: dict = None):
        """
        Initialize a BeamPattern instance.

        Parameters
        ----------
        data_dir : str
            The path to the beam pattern file.
        beam_pattern : dict
            Dictionary with location keys and list of RSSI values.
        interpolated_beam_pattern : dict
            Dictionary with location keys and list of interpolated RSSI values.
        """
        self.data_dir = data_dir
        self.beam_pattern = beam_pattern
        self.interpolated_beam_pattern = interpolated_beam_pattern

        if data_dir is not None:
            self.load_all(data_dir)

    def __str__(self):
        """
        Return a string representation of the beam pattern, sorted by elevation and azimuth.

        Returns
        -------
        str
            Sorted string representation of the beam pattern.
        """
        sorted_pattern = sorted(self.beam_pattern.items(), key=lambda x: (x[0][1], x[0][0]))
        return "\n".join([f"{k}: {v}" for k, v in sorted_pattern])

    def load_all(self, data_dir):
        """
        Load a beam pattern from a file.

        Parameters
        ----------
        path : str
            The path to the beam pattern file.
        """
        import pickle
        for member in ['beam_pattern', 'interpolated_beam_pattern']:
            path = os.path.join(data_dir, f'{member}.pkl')
            with open(path, 'rb') as f:
                setattr(self, member, pickle.load(f))

    def save(self, data_dir):
        """
        Save the beam pattern to a file.

        Parameters
        ----------
        path : str
            The path to the beam pattern file.
        """
        import pickle
        for member in ['beam_pattern', 'interpolated_beam_pattern']:
            path = os.path.join(data_dir, f'{member}.pkl')
            with open(path, 'wb') as f:
                pickle.dump(getattr(self, member), f)

class SphericalMapper:
    """
    Class to map 3D coordinates to 2D coordinates.
    """

    def __init__(self, azimuth_bin=1, elevation_bin=1, turn_to_zero_at_origin=False):
        """
        Initialize a SphericalMapper instance.

        Parameters
        ----------
        azimuth_bin : int
            The azimuth bin size.
        elevation_bin : int
            The elevation bin size.
        """
        self.mapper_matrix = None
        self.azimuth_bin = azimuth_bin
        self.elevation_bin = elevation_bin
        self.create_mapper_matrix(turn_to_zero_at_origin=turn_to_zero_at_origin)

    def create_mapper_matrix(self, turn_to_zero_at_origin=False):
        """
        Create a mapper matrix for 3D to 2D mapping.
        """
        self.mapper_matrix = np.empty((360, 360), dtype=object)
        if turn_to_zero_at_origin:
            for i in range(360):
                for j in range(360):
                    if j < 180:
                        self.mapper_matrix[i][j] = Location(i, j)
                    else:
                        self.mapper_matrix[i][j] = Location(i + 180, 360 - j)
        else:
            for i in range(360):
                for j in range(360):
                    if j < 180:
                        self.mapper_matrix[i][j] = Location(i, j - 90)
                    else:
                        self.mapper_matrix[i][j] = Location(i + 180, 270 - j)

    def offset(self, azimuth, elevation, start_from=(0, 0)):
        """
        Calculate the offset from a starting point.

        Parameters
        ----------
        azimuth : float
            The azimuth angle in degrees.
        elevation : float
            The elevation angle in degrees.
        start_from : tuple
            The starting point (azimuth, elevation).

        Returns
        -------
        tuple
            The offset (azimuth, elevation).
        """
        end_index_i = (start_from[0] + azimuth) % 360
        end_index_j = (start_from[1] + elevation) % 360
        return self.mapper_matrix[end_index_i, end_index_j].azimuth, self.mapper_matrix[
            end_index_i, end_index_j].elevation

    def index(self, azimuth, elevation):
        """
        Get the index of a location.

        Parameters
        ----------
        azimuth : float
            The azimuth angle in degrees.
        elevation : float
            The elevation angle in degrees.

        Returns
        -------
        tuple
            The index of the location.
        """
        for i in range(360):
            for j in range(360):
                if self.mapper_matrix[i, j].azimuth == azimuth and self.mapper_matrix[i, j].elevation == elevation:
                    return i, j

    def get_mapper_matrix(self):
        """
        Get the mapper matrix.

        Returns
        -------
        numpy.ndarray
            The mapper matrix.
        """
        return self.mapper_matrix

    # def turn_to_zero_at_origin(self):
    #     """
    #     Turn the mapper matrix to have the real loc origin at (0, 0).
    #     """
    #     self.mapper_matrix = np.roll(self.mapper_matrix, -90, axis=1)    
    
    def __str__(self):
        out = ""
        out += "{:10s}\t".format("Coordinate")
        for i in range(360):
            out += "{:10s}\t".format(str(i))
        out += "\n"
        for j in range(360):
            out += "{:10s}\t".format(str(j))
            for i in range(360):
                out += "{:10s}\t".format(str(self.mapper_matrix[i, j]))
            out += "\n"
        return out


if __name__ == "__main__":
    smapper = SphericalMapper(turn_to_zero_at_origin=False)
    print(smapper.offset(180, 90, start_from=(0, 0)))
