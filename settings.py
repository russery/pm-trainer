"""
Handles all program settings.
"""
import configparser as cp

class Settings():
    '''
    Handles reading and writing settings from a file
    '''
    def __init__(self):
        self.config = cp.ConfigParser()

    def load_settings(self, filename=None, defaults=None):
        '''
        Load settings from a file, or a set of defaults
        '''
        if filename:
            self.config.read(filename)
            # TODO: Validate file format
        elif defaults:
            self.config.read_dict(defaults)


    def write_settings(self, filename):
        '''
        Flush settings to a file
        '''
        with open(filename, 'w') as configfile:
            self.config.write(configfile)

    def get(self, key):
        '''
        Return a setting based on its name
        '''
        return self.config["DEFAULT"][key]

    def set(self, key, value):
        '''
        Set a setting based on its name
        '''
        self.config["DEFAULT"][key] = value
