"""
Handles all program settings.

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
from os import path
import configparser as cp

class Settings():
    '''
    Handles reading and writing settings from a file
    '''
    def __init__(self, filename=None, defaults=None):
        self.config = cp.ConfigParser()
        self._active_section = "DEFAULT"
        self.config[self._active_section] = {}
        if filename:
            self.load_settings(filename=filename)
        if defaults:
            self.load_settings(defaults=defaults)

    def load_settings(self, filename=None, defaults=None):
        '''
        Load settings from a file, or a set of defaults
        '''
        if filename:
            self.config.read(filename)
        elif defaults:
            self.config.read_dict({"DEFAULT":defaults})

    def write_settings(self, filename):
        '''
        Flush settings to a file
        '''
        dirname = path.dirname(filename)
        if not path.isdir(dirname):
            path.mkdir(dirname)
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

    def delete(self, key):
        '''
        Remove a key from the config.
        '''
        self.config.remove_option(self.active_section, key)

    def create_section(self, section, settings=None):
        '''
        Create a new section, optionally populating settings
        '''
        if not settings:
            settings = {} # Create an empty dict to pass in
        self.config[section] = settings

    @property
    def active_section(self):
        '''
        Return the currently active section of the config.
        '''
        return self._active_section

    @active_section.setter
    def active_section(self, active_section):
        '''
        Set the active section of the config.
        '''
        if active_section in self.config.sections():
            self._active_section = active_section
        else:
            raise KeyError("Section name {} not found in settings config".format(active_section))
