'''
Generates workout profiles from a description file.
'''
import yaml

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
        try:
            with open(workout_file) as f:
                self.workout = yaml.full_load(f)
        except (yaml.scanner.ScannerError, FileNotFoundError) as e:
            raise Workout.WorkoutError(message="Error reading file \"{}\": {}".format(
                workout_file, e))

        # Check workout duration:
        dur = 0
        for b in self.workout["blocks"]:
            dur += b["duration"]
        if abs(dur-1.0) > 0.001:
            raise Workout.WorkoutError(message="Invalid workout duration {} != 1.0".format(dur))

        self.duration_s = self.workout["duration_s"]

    def _get_current_block(self, curr_time_s):
        complete_fraction = curr_time_s / self.duration_s
        dur = 0
        ind = 0
        for block in self.workout["blocks"]:
            dur += block["duration"]
            if dur >= complete_fraction:
                break
            ind += 1
        return ind, block

    def block_time_remaining(self, curr_time_s):
        '''
        Returns the time left in the current workout block
        '''
        ind, block = self._get_current_block(curr_time_s)
        block_duration_s = block["duration"] * self.duration_s
        dur = 0
        for i in range(0,ind):
            dur += self.workout["blocks"][i]["duration"]
        block_elapsed_s = curr_time_s - dur * self.duration_s
        return block_duration_s - block_elapsed_s

    def power_target(self, curr_time_s):
        '''
        Returns the target power for the current time in 
        the current block.
        '''
        _, block = self._get_current_block(curr_time_s)
        start_power = block["start"]
        end_power = block["end"]
        duration_s = block["duration"] * self.duration_s
        time_left_s = self.block_time_remaining(curr_time_s)
        block_slope = ((end_power - start_power) / duration_s)
        power = block_slope * (duration_s - time_left_s) + start_power
        return power

if __name__ == '__main__':
    workout = Workout("workouts/short_stack.yaml")
    time_s = 0
    while time_s < workout.duration_s:
        block_remaining = workout.block_time_remaining(time_s)
        power_percent = workout.power_target(time_s)
        print("{:5}  Remaining: {:5.0f}   Power: {:4.3f}".format(time_s, block_remaining, power_percent))
        time_s +=1
