"""
Draws a workout power profile and plots traces on top of it.
"""
import PySimpleGUI as sg
import numpy as np
from workout_profile import Workout

ZONES = [0, 0.6, 0.75, 0.9, 1.05, 1.18, 100]
ZONE_COLORS = ["gray", "blue", "green", "yellow", "orange", "red"]

def get_max_power(all_blocks):
    '''
    Returns the maximum power from a power profile.
    '''
    max_p = 0
    for block in all_blocks:
        _, start, end = block
        max_p = max(max_p, start, end)
    return max_p


def get_zone(pwr):
    '''
    Returns the power zone number, given a normalized power (0.0-1.0, where 1.0=FTP).
    '''
    for i in range (0,len(ZONES)-1):
        if ZONES[i] < pwr <= ZONES[i+1]:
            return i
    return None

def plot_blocks(graph, all_blocks, y_max):
    '''
    Plots all the workout block segments from a workout profile.
    Generates the color for each segment based on zone, and plots to fill the
    entire graph.
    y_max is the normalized maximum power to be displayed
    '''
    dur = 0
    gwidth, gheight = graph.Size
    gheight = gheight / y_max  # Scale Y of plot to max of power profile
    for block in all_blocks:
        width, start, end = block
        zone = get_zone(np.average([start,end]))
        color = ZONE_COLORS[zone]
        startx = dur*gwidth
        starty = start*gheight
        endx = (dur+width) * gwidth
        endy = end*gheight
        graph.draw_polygon((
            (startx,0), (startx,starty), (endx,endy), (endx,0)),
            fill_color=color)
        dur += width

def plot_trace(graph, point, y_max, size=2, color="red"):
    '''
    Plots a trace onto the graph.
    '''
    x, y = point
    gwidth, gheight = graph.Size
    gheight = gheight / y_max  # Scale Y of plot to max of power profile
    # TODO: Make Y scaling work for other trace types (e.g. heartrate)
    graph.draw_point((x*gwidth,y*gheight), size=size, color=color)


if __name__ == '__main__':
    import sys
    workout = Workout("workouts/short_stack.yaml")
    blocks = workout.get_all_blocks()

    layout = [[sg.Graph(
        canvas_size=(800, 200),
        graph_bottom_left=(0, 0),
        graph_top_right=(800, 200),
        background_color='gray',
        enable_events=True,
        key='-PROFILE-')]]
    window = sg.Window('Workout Profile', layout, finalize=True)

    max_power = get_max_power(blocks) * 1.2
    plot_blocks(window['-PROFILE-'], blocks, max_power)

    while True:
        for t in np.arange(0.0, 1.0, 0.001):
            event, values = window.read(timeout=100)
            if event == sg.WIN_CLOSED:
                window.close()
                sys.exit()

            power = np.random.random_sample()*2.0
            plot_trace(window['-PROFILE-'], (t,power), max_power)
            