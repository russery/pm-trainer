"""
Creates a vertical "bug" indicator with a centered target indicator
and a current value indicator.

Copyright (C) 2021  Robert Ussery

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import PySimpleGUI as sg

class BugIndicator():
    '''
    The bug indicator, which plots one or more bugs on it.
    '''
    class Bug():
        '''
        A bug to be plotted on the bug indicator.
        '''
        def __init__(self, graph, name, height_px, width_px, left, color, level_percent):
            self.name = name
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
            '''
            Move the bug to the given position on the graph.
            Saturate the position to [0.0-1.0].
            '''
            if level_percent < 0.0:
                level_percent = 0
            elif level_percent > 1.0:
                level_percent = 1.0
            _, max_height_px = graph.Size
            bug_move_px = max_height_px * (level_percent - self.level_percent)
            graph.move_figure(self.line, 0, bug_move_px)
            graph.move_figure(self.polygon, 0, bug_move_px)
            self.level_percent = level_percent

    def __init__(self, graph):
        self.graph = graph
        self.bugs = {}

    def add_bug(self, name, height_px=10, width_px=15, left=True, color="red", level_percent=0.5):
        '''
        Adds a new named bug to the graph or overwrites an existing one.
        '''
        new_bug = BugIndicator.Bug(self.graph, name, height_px,
                                   width_px, left, color, level_percent)
        self.bugs[name] = new_bug

    def update(self, name, value):
        '''
        Update the bug's position, accessing the bug by name.
        '''
        self.bugs[name].move(self.graph, value)
