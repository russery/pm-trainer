import PySimpleGUI as sg
import numpy as np
from workout_profile import Workout

def _get_zone(power):
    for i in range (0,len(ProfilePlot.ZONES)-1):
        if (power > ProfilePlot.ZONES[i]) and (power <= ProfilePlot.ZONES[i+1]):
            return i
    return None

class ProfilePlot():
    ZONES = [0, 0.75, 0.9,1.05,1.2,100]
    ZONE_COLORS = ["blue", "green", "yellow", "orange", "red"]

    def __init__(self, graph):
        self.graph = graph

    def plot_blocks(self,all_blocks):
        dur = 0
        gwidth, gheight = self.graph.Size
        gheight = gheight * 0.5 # TODO: get max power in all blocks and use this to set Y scale factor
        for block in all_blocks:
            print (block)
            width = block[0]
            start = block[1]
            end = block[2]
            zone = _get_zone(np.average([start,end]))
            color = ProfilePlot.ZONE_COLORS[zone]
            startx = dur*gwidth
            starty = start*gheight
            endx = (dur+width) * gwidth
            endy = end*gheight
            print(startx, starty, endx, endy, gwidth, gheight)
            poly = self.graph.draw_polygon((
                (startx,0), (startx,starty), (endx,endy), (endx,0)),
                fill_color=color)
            dur += width


if __name__ == '__main__':
    workout = Workout("workouts/short_stack.yaml")
    all_blocks = workout.get_all_blocks()

    layout = [[sg.Graph(
        canvas_size=(800, 200),
        graph_bottom_left=(0, 0),
        graph_top_right=(800, 200),
        background_color='gray',
        enable_events=True,
        key='-PROFILE-')]]
    window = sg.Window('Workout Profile', layout, finalize=True)

    plot = ProfilePlot(graph=window['-PROFILE-'])
    plot.plot_blocks(all_blocks)
        

    while True:
        event, values = window.read()
        print(event, values)
        if event == sg.WIN_CLOSED:
            break
    window.close()
