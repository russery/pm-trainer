"""
Handles all program settings.
"""
import configparser as cp

DEFAULT_SETTINGS = {
   # User / session settings:
   "FTPWatts": 200,
   "Workout": "workouts/short_stack.yaml",

   # Window / system settings
   "LogDirectory": "logs",
   "UpdateRateHz": 10
}



class Settings():
    def __init__(self, filename=None):
        self.config = cp.ConfigParser()
        if filename:
            self.load_settings(file)
        else:
            self.config = DEFAULT_SETTINGS


    def load_settings(self, filename):
        '''
        Load settings from a file
        '''
        self.config.read(filename)
        # TODO: Validate file format

    def write_settings(self, filename):
        '''
        Flush settings to a file
        '''
        with open(filename, 'w') as configfile:
            self.config.write(configfile)

    def get_setting(self, key):
        return self.config[key]
        

if __name__ == "__main__":
    cfg = Settings()
    print(cfg.get_setting("FTPWatts"))
    print(cfg.config)