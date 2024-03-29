'''
Generates workout profiles from a description file.

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
'''
import yaml

ZONES = [0, 0.6, 0.75, 0.9, 1.05, 1.18]
def get_zone(pwr):
    '''
    Returns the power zone number, given a normalized power (0.0-1.0, where 1.0=FTP).
    '''
    if pwr <= ZONES[0]:
        return 0
    for i in range(0,len(ZONES)-1):
        if ZONES[i] < pwr <= ZONES[i+1]:
            return i
    return len(ZONES)-1 # Highest zone

class Workout():
    '''
    Reads in workout profile files and tracks progress through
    the workout.
    '''
    class WorkoutError(Exception):
        '''
        Exceptions for workout profiles.
        '''
        def __init__(self, message=""):
            super().__init__(message)

    def __init__(self, workout_file):
        with open(workout_file) as f:
            self.workout = yaml.full_load(f)

        # Check workout duration:
        dur = 0
        for b in self.workout["blocks"]:
            dur += b["duration"]
        if abs(dur-1.0) > 0.001:
            raise Workout.WorkoutError(message="Invalid workout duration {} != 1.0".format(dur))

        self._duration_s = self.workout["duration_s"]

    def _get_current_block(self, curr_time_s):
        complete_fraction = curr_time_s / self._duration_s
        dur = 0
        ind = 0
        block = None
        for block in self.workout["blocks"]:
            dur += block["duration"]
            if dur >= complete_fraction:
                break
            ind += 1
        return ind, block

    def block_time_remaining(self, curr_time_s):
        '''
        Returns the time left in the current workout block in seconds
        '''
        if curr_time_s > self._duration_s:
            return 0
        ind, block = self._get_current_block(curr_time_s)
        block_duration_s = block["duration"] * self._duration_s
        if curr_time_s < 0:
            return block_duration_s
        dur = 0
        for i in range(0,ind):
            dur += self.workout["blocks"][i]["duration"]
        block_elapsed_s = curr_time_s - dur * self._duration_s
        return block_duration_s - block_elapsed_s

    def power_target(self, curr_time_s):
        '''
        Returns the target power for the current time in
        the current block.
        '''
        _, block = self._get_current_block(curr_time_s)
        start_power = block["start"]
        end_power = block["end"]
        _duration_s = block["duration"] * self._duration_s
        time_left_s = self.block_time_remaining(curr_time_s)
        block_slope = ((end_power - start_power) / _duration_s)
        power = block_slope * (_duration_s - time_left_s) + start_power
        return power

    def get_all_blocks(self):
        '''
        Returns all blocks from the workout as a list of tuples:
        [(duration, start power, end power),...]
        '''
        all_blocks = []
        for block in self.workout["blocks"]:
            cur_block = (block["duration"], block["start"], block["end"])
            all_blocks.append(cur_block)
        return all_blocks

    def get_min_max_power(self):
        '''
        Returns the minimum and maximum power from a power profile.
        '''
        max_p = 0
        min_p = float("inf")
        all_blocks = self.get_all_blocks()
        for block in all_blocks:
            _, start, end = block
            max_p = max(max_p, start, end)
            min_p = min(min_p, start, end)
        return min_p, max_p

    @property
    def duration_s(self):
        '''
        Returns the workout duration in seconds
        '''
        return self._duration_s

    @property
    def name(self):
        '''
        Returns the name of the workout.
        '''
        return self.workout["name"]

    @property
    def description(self):
        '''
        Returns the description of the workout.
        '''
        return self.workout["description"]
