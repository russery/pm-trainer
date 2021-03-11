"""
Draws a workout power profile and plots traces on top of it.
"""
import PySimpleGUI as sg
import numpy as np
from workout_profile import Workout, get_zone

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

    min_power, max_power = workout.get_min_max_power()
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
            