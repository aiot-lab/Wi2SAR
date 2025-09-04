"""
Plot Module
===========
This module provides functions for plotting beam patterns and similarity matrices.
"""

import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.subplots
import numpy as np
import logging

logger = logging.getLogger(__name__)

beam_pattern_fig = None
similarity_matrix_fig = None


def plot_beam_pattern_2d(beam_pattern):
    """
    Plot the beam pattern in polar coordinates.

    Parameters
    ----------
    beam_pattern : dict
        The beam pattern to plot. Keys are angles, values are lists of RSSI values.
    """
    global beam_pattern_fig
    if beam_pattern_fig is not None:
        plt.close(beam_pattern_fig)
    beam_pattern_fig = plt.figure()
    ax = plt.subplot(111, polar=True)

    angles = [k[0] for k in list(beam_pattern.keys())]
    angle_rad = np.array(angles) / 180 * np.pi
    values = [np.mean(v) for k, v in beam_pattern.items()]
    angle_sorted = np.argsort(angle_rad)
    angle_rad = angle_rad[angle_sorted]
    values = np.array(values)[angle_sorted]
    angle_rad = np.append(angle_rad, angle_rad[0])
    values = np.append(values, values[0])
    std_dev = [np.std(v) for k, v in beam_pattern.items()]
    std_dev = np.array(std_dev)[angle_sorted]
    std_dev = np.append(std_dev, std_dev[0])
    ax.fill_between(angle_rad, values - std_dev, values + std_dev, color='b', alpha=0.1)

    # Make the plot non-blocking
    plt.draw()
    plt.pause(0.001)
    logger.info("Beam pattern plot created.")

def plot_beam_pattern_3d(beam_pattern, zero_centered=True):
    """
    Plot the beam pattern in 3D with color representing RSSI using plotly.

    Parameters
    ----------
    beam_pattern : dict
        The beam pattern to plot. Keys are (azimuth, elevation) tuples, values are RSSI values.
    zero_centered : bool, optional
        If True, center the plot around azimuth=0 and elevation=0.
    """
    global beam_pattern_fig

    azimuths = []
    elevations = []
    values = []

    for (azimuth, elevation), rssi in beam_pattern.items():
        azimuths.append(azimuth)
        elevations.append(elevation)
        values.append(rssi)

    azimuths = np.array(azimuths)
    elevations = np.array(elevations)
    values = np.array(values)

    if zero_centered:
        azimuths = (azimuths + 180) % 360

    azimuths_unique = np.unique(azimuths)
    elevations_unique = np.unique(elevations)

    azimuths_grid, elevations_grid = np.meshgrid(azimuths_unique, elevations_unique)
    values_grid = np.zeros_like(azimuths_grid, dtype=float)

    for i in range(len(azimuths_unique)):
        for j in range(len(elevations_unique)):
            mask = (azimuths == azimuths_unique[i]) & (elevations == elevations_unique[j])
            if np.any(mask):
                values_grid[j, i] = values[mask][0]
            else:
                values_grid[j, i] = np.nan

    # Create a 3D surface plot using plotly
    fig = go.Figure(data=[go.Surface(z=values_grid, x=azimuths_grid, y=elevations_grid, colorscale='Viridis', showscale=True)])

    # Update the layout
    fig.update_layout(
        title='Beam Pattern',
        scene=dict(
            xaxis_title='Azimuth',
            yaxis_title='Elevation',
            zaxis_title='RSSI',
            xaxis=dict(
                tickmode='array',
                tickvals=[(i + 180) % 360 for i in range(-180, 181, 30)],
                ticktext=[str(i) for i in range(-180, 181, 30)]
            ),
            yaxis=dict(nticks=20),
            zaxis=dict(nticks=20),
        )
    )

    # Remove the edges
    fig.update_traces(contours_z=dict(show=False))

    fig.show()
    logger.info("Beam pattern plot created.")

def plot_similarity_matrix(similarity_matrix):
    """
    Plot the similarity matrix in polar coordinates.

    Parameters
    ----------
    similarity_matrix : dict
        The similarity matrix to plot. Keys are angles, values are similarity scores.
    """
    global similarity_matrix_fig
    if similarity_matrix_fig is not None:
        plt.close(similarity_matrix_fig)
    similarity_matrix_fig = plt.figure()
    ax = plt.subplot(111, polar=True)

    angles = np.array(list(similarity_matrix.keys())) / 180 * np.pi
    values = np.array(list(similarity_matrix.values()))
    angle_sorted = np.argsort(angles)
    angles = angles[angle_sorted]
    values = values[angle_sorted]
    angles = np.append(angles, angles[0])
    values = np.append(values, values[0])
    ax.fill(angles, values, 'b', alpha=0.1)

    # Make the plot non-blocking
    plt.draw()
    plt.pause(0.001)

def plotly_subplots(figures, titles, n_rows, n_cols):
    """
    Plot multiple figures (n_rows x n_cols) in subplots using plotly.

    Parameters
    ----------
    figures : list of go.Figure
        The figures to plot.
    titles : list of str
        The titles of the subplots.
    layout : dict
        The layout of the subplots.
    n_rows : int
        The number of rows of the subplot grid.
    n_cols : int
        The number of columns of the subplot grid.
    """
    fig = plotly.subplots.make_subplots(rows=n_rows, cols=n_cols, subplot_titles=titles)

    for i, figure in enumerate(figures):
        row = i // n_cols + 1
        col = i % n_cols + 1
        # add data and layout from each figure to the subplots
        for trace in figure.data:
            fig.add_trace(trace, row=row, col=col)
        for key, value in figure.layout.items():
            if key not in ['xaxis', 'yaxis', 'xaxis2', 'yaxis2']:
                fig.update_layout({f'{key}{col}': value})
            else:
                fig.update_layout({f'{key}{col // 2 + 1}': value})
    
    fig.show()

def wait_for_user():
    """
    Pause execution to let the user close the plots.
    """
    input("Press Enter to close the plots and exit...")
    plt.close('all')
    logger.info("User closed the plots.")
