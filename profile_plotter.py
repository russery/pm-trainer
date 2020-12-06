"""
Draws a workout power profile and plots traces on top of it.
"""
import PySimpleGUI as sg
import numpy as np
from workout_profile import Workout

ZONES = [0, 0.6, 0.75, 0.9, 1.05, 1.18, 100]
ZONE_COLORS = ["gray", "blue", "green", "yellow", "orange", "red"]

def get_min_max_power(all_blocks):
    '''
    Returns the minimum and maximum power from a power profile.
    '''
    max_p = 0
    min_p = 100
    for block in all_blocks:
        _, start, end = block
        max_p = max(max_p, start, end)
        min_p = min(min_p, start, end)
    return min_p, max_p


def get_zone(pwr):
    '''
    Returns the power zone number, given a normalized power (0.0-1.0, where 1.0=FTP).
    '''
    for i in range (0,len(ZONES)-1):
        if ZONES[i] < pwr <= ZONES[i+1]:
            return i
    return None

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
        zone = get_zone(np.average([start,end]))
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


if __name__ == '__main__':
    import sys
    workout = Workout("workouts/short_stack.yaml")
    blocks = workout.get_all_blocks()

    layout = [[sg.Graph(
        canvas_size=(900, 100),
        graph_bottom_left=(0, 0),
        graph_top_right=(900, 100),
        background_color='black',
        enable_events=True,
        key='-PROFILE-')]]
    window = sg.Window('Workout Profile', layout, finalize=True)

    min_power, max_power = get_min_max_power(blocks)
    min_power *= 0.8
    max_power *= 1.2
    plot_blocks(window['-PROFILE-'], blocks, (min_power, max_power))

    power = -0.5
    while True:
        for t in np.arange(-0.1, 1.1, 0.001):
            event, values = window.read(timeout=100)
            if event == sg.WIN_CLOSED:
                window.close()
                sys.exit()
            if t < 0.3:
                power += 0.005
            else:
                power = np.random.random_sample()*2.0
            plot_trace(window['-PROFILE-'], (t,power), (min_power, max_power))
            