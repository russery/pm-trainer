import unittest
import sys
import PySimpleGUI as sg
from ..bug_indicator import *


class TestBugIndicator(unittest.TestCase):
    def setUp(self):
        layout = [[sg.Graph(
                canvas_size=(50, 100),
                graph_bottom_left=(0, 0),
                graph_top_right=(50, 100),
                background_color='gray',
                enable_events=True,
                key="-POWER-")]]
        self.window = sg.Window('Workout Profile', layout, finalize=True, keep_on_top=True)


    def test_bug(self):
        signal = -0.1
        bug = BugIndicator(self.window["-POWER-"])
        bug.add_bug("target_power", color="blue", level_percent=0.5)
        bug.add_bug("current_power", color="red", level_percent=0.5, left=False)
        bug.add_bug("other_indicator", color="cyan")
        for _ in range(200):
            bug.update("current_power", signal)
            bug.update("other_indicator", 1.0-signal)
            signal +=0.01
            event, values = self.window.read(timeout=1)
            if event == sg.WIN_CLOSED:
                self.window.close()
                break
        self.window.close()
