"""
asdf
"""

import PySimpleGUI as sg

class BugIndicator():
    class Bug():
        def __init__(self, graph, height_px=10, width_px=15, left=True, color="red", level_percent=0.5):
            self.height_px = height_px
            self.width_px = width_px
            self.left = left
            self.line = None
            self.polygon = None
            self.color = color
            self.level_percent = level_percent
            max_width_px, max_height_px = graph.Size
            bug_level_px = max_height_px * self.level_percent
            self.line = graph.draw_line((0,bug_level_px),
                (max_width_px,bug_level_px), self.color)
            if self.left:
                poly = (
                    (0, bug_level_px-(self.height_px/2)),
                    (0, bug_level_px+(self.height_px/2)),
                    (self.width_px, bug_level_px))
            else:
                poly = (
                    (max_width_px, bug_level_px-(self.height_px/2)),
                    (max_width_px, bug_level_px+(self.height_px/2)),
                    (max_width_px-self.width_px, bug_level_px))
            self.polygon = graph.draw_polygon(poly, fill_color=self.color)

        def move(self, graph, level_percent):
            max_width_px, max_height_px = graph.Size
            bug_move_px = max_height_px * (level_percent - self.level_percent)
            graph.move_figure(self.line, 0, bug_move_px)
            graph.move_figure(self.polygon, 0, bug_move_px)
            self.level_percent = level_percent

    def __init__(self, graph, value=0.5):
        self.graph = graph
        self.target_bug = BugIndicator.Bug(graph=graph, color="blue")
        self.output_bug = BugIndicator.Bug(graph=graph, color="red", left=False)

    def update(self, value):
        if value < 0.0:
            value = 0
        elif value > 1.0:
            value = 1.0
        self.output_bug.move(self.graph, value)

if __name__ == "__main__":
    layout = [[sg.Graph(
            canvas_size=(50, 100),
            graph_bottom_left=(0, 0),
            graph_top_right=(50, 100),
            background_color='gray',
            enable_events=True,
            key="-POWER-")]]
    window = sg.Window('Workout Profile', layout, finalize=True, keep_on_top=True)

    signal = -0.1
    bug = BugIndicator(window["-POWER-"])
    while True:
        bug.update(signal)
        signal +=0.01
        event, values = window.read(timeout=100)
        if event == sg.WIN_CLOSED:
            window.close()
            exit()
