"""
Draws a workout power profile and plots traces on top of it.
"""
import numpy as np
from . import workout_profile

ZONE_COLORS = ["gray", "blue", "green", "yellow", "orange", "red"]

def plot_blocks(graph, all_blocks, y_lims):
    '''
    Plots all the workout block segments from a workout profile.
    Generates the color for each segment based on zone, and plots to fill the
    entire graph.
    y_lims is a tuple of (min, max) normalized power limits for the plot.
    '''
    dur = 0
    y_min, y_max = y_lims
    y_height = y_max - y_min
    max_width_px, max_height_px = graph.Size
    for block in all_blocks:
        width, start, end = block
        zone = workout_profile.get_zone(np.average([start,end]))
        color = ZONE_COLORS[zone]
        # Scale X and Y to plot pixels
        startx_px = dur*max_width_px
        endx_px = (dur+width) * max_width_px
        starty_px = ((start-y_min) / y_height) * max_height_px
        endy_px = ((end-y_min) / y_height) * max_height_px
        graph.draw_polygon((
            (startx_px,0), (startx_px,starty_px), (endx_px,endy_px), (endx_px,0)),
            fill_color=color)
        dur += width

def plot_trace(graph, point, y_lims, size=2, color="red"):
    '''
    Plots a trace onto the graph.
    y_lims is a tuple of (min, max) normalized (0-1.0) limits for the plot.
    '''
    y_min, y_max = y_lims
    y_height = y_max - y_min
    max_width_px, max_height_px = graph.Size
    x, y = point
    x_px = x * max_width_px
    y_px = ((y-y_min) / y_height) * max_height_px
    x_px = min(max_width_px, max(0, x_px)) # Saturate to plot limits
    y_px = min(max_height_px, max(0, y_px))
    graph.draw_point((x_px,y_px), size=size, color=color)
