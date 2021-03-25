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
        self._active_section = "DEFAULT"
        self.config[self._active_section] = {}

    def load_settings(self, filename=None, defaults=None):
        '''
        Load settings from a file, or a set of defaults
        '''
        if filename:
            self.config.read(filename)
            # TODO: Validate file format
        elif defaults:
            self.config.read_dict({"DEFAULT":defaults})


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
        return self.config[self.active_section][key]

    def set(self, key, value):
        '''
        Set a setting based on its name
        '''
        self.config[self.active_section][key] = value

    def create_section(self, section, settings={}):
        '''
        Create a new section, optionally populating settings
        '''
        self.config[section] = settings
    
    @property
    def active_section(self):
        return self._active_section

    @active_section.setter
    def active_section(self, active_section):
        if active_section in self.config.sections():
            self._active_section = active_section
        else:
            raise KeyError("Section name {} not found in settings config".format(active_section))
