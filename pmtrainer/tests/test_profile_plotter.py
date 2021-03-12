import unittest
import PySimpleGUI as sg
import numpy as np
from ..profile_plotter import plot_blocks, plot_trace
from ..workout_profile import Workout

class TestProfilePlotter(unittest.TestCase):
    def setUp(self):
        self.workout = Workout("workouts/short_stack.yaml")
        self.blocks = self.workout.get_all_blocks()

        layout = [[sg.Graph(
            canvas_size=(900, 100),
            graph_bottom_left=(0, 0),
            graph_top_right=(900, 100),
            background_color='black',
            enable_events=True,
            key='-PROFILE-')]]
        self.window = sg.Window('Workout Profile', layout, finalize=True)

    def test_profile_plotter(self):
        '''
        Plot a workout profile and a power trace
        '''
        min_power, max_power = self.workout.get_min_max_power()
        min_power *= 0.8
        max_power *= 1.2
        plot_blocks(self.window['-PROFILE-'], self.blocks, (min_power, max_power))

        power = -0.2
        for t in np.arange(-0.1, 1.1, 0.003):
            event, _ = self.window.read(timeout=1)
            if event == sg.WIN_CLOSED:
                self.window.close()
                break
            if t < 0.7:
                power += 0.01
            else:
                power = np.random.random_sample()*2.0
            plot_trace(self.window['-PROFILE-'], (t,power), (min_power, max_power))
        self.window.close()
