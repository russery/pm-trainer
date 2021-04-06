"""
Creates a TCX file and allows adding track points with activity data.

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

import xml.etree.ElementTree as et
from xml.dom import minidom
from enum import Enum
from datetime import datetime as dt

NAMESPACES = {
    "": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
    "ns2": "http://www.garmin.com/xmlschemas/UserProfile/v2",
    "ns3": "http://www.garmin.com/xmlschemas/ActivityExtension/v2",
    "ns5": "http://www.garmin.com/xmlschemas/ActivityGoals/v1",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance"
}

def _time_stamp():
    '''
    Returns a UTC timestamp string
    '''
    return dt.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

class Point():
    '''
    Holds all the possible data for a TCX TrackPoint, and implements
    a nice string conversion.
    '''
    def __init__(self, time=None, lat_deg=None, lon_deg=None, altitude_m=None,
                 distance_m=None, heartrate_bpm=None, cadence_rpm=None,
                 speed_mps=None, power_watts=None):
        self.time = time
        self.lat_deg = lat_deg
        self.lon_deg = lon_deg
        self.altitude_m = altitude_m
        self.distance_m = distance_m
        self.heartrate_bpm = heartrate_bpm
        self.cadence_rpm = cadence_rpm
        self.speed_mps = speed_mps
        self.power_watts = power_watts

    def __str__(self):
        vals = {
            "Time": {"Format": "{}", "Value": self.time},
            "Lat": {"Format": "{:-8.4f}", "Value": self.lat_deg},
            "Lon": {"Format": "{:-8.4f}", "Value": self.lon_deg},
            "Alt": {"Format": "{:4.1f}", "Value": self.altitude_m},
            "Dist": {"Format": "{:4.1f} ", "Value": self.distance_m},
            "HR": {"Format": "{:3.0f}", "Value": self.heartrate_bpm},
            "Cad": {"Format": "{:3.0f}", "Value": self.cadence_rpm},
            "Speed": {"Format": "{:4.1f}", "Value": self.speed_mps},
            "Power": {"Format": "{:4.0f}", "Value": self.power_watts}
        }
        out = ""
        for key, val in vals.items():
            if val["Value"] is None:
                val["Value"] = "None"
            else:
                val["Value"] = val["Format"].format(val["Value"])
            out += "{}: {}  ".format(key, val["Value"])

        return out

class Tcx():
    '''
    Creates a TCX xml tree, allows adding points to it, and handles
    reading to and writing from a file.
    '''
    class ActivityType(Enum):
        '''
        Type of activity, one of the TCX activity types
        '''
        RUNNING = 0
        BIKING = 1
        OTHER = 2
        MULTISPORT = 3

    def __init__(self):
        self.tcx = None
        self.file_name = None
        self.activity = None
        self.current_lap = None
        self.current_track = None
        self.points = None

    def open_log(self, fname):
        '''
        Opens an existing log file for reading or writing
        '''
        self.tcx = et.parse(fname).getroot()
        self.file_name = fname

    def start_log(self, fname):
        '''
        Starts a new log
        '''
        self.tcx = et.Element("TrainingCenterDatabase")
        for prefix, uri in NAMESPACES.items():
            self.tcx.set("xmlns{}{}".format("" if prefix=="" else ":", prefix), uri)
        self.tcx.set("xsi:schemaLocation",
                     NAMESPACES[""] +
                     " http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd")
        self.activity = et.SubElement(et.SubElement(self.tcx, "Activities"), "Activity")
        self.file_name = fname
        self.current_track = None
        self.current_lap = None
        self.points = None

    @property
    def activities(self):
        '''
        Returns the handle of any Activity tags in the file.
        '''
        return self.tcx.find("Activities", NAMESPACES)

    def set_current_activity(self, activity_index=0):
        '''
        Sets the current activity to the one specified by activity_index
        '''
        self.activity = self.activities.findall("Activity", NAMESPACES)[activity_index]

    def start_activity(self, activity_type):
        '''
        Starts an activity, track and lap.
        Assumes only one track and lap per activity.
        TODO: handle multiple tracks and laps?
        '''
        assert isinstance(activity_type, Tcx.ActivityType)
        self.activity.set("Sport", activity_type.name)
        et.SubElement(self.activity, "Id").text = _time_stamp()
        self.current_lap = et.SubElement(self.activity, "Lap")
        self.current_track = et.SubElement(self.current_lap, "Track")

    def add_point(self, point):
        '''
        Adds an activity point, including position, speed, altitude, heartrate,
        power, etc. (all optional).
        '''
        if point.time is None:
            point.time = _time_stamp() # Use current time if not provided
        point_record = et.SubElement(self.current_track, "Trackpoint")
        et.SubElement(point_record, "Time").text = point.time
        if (point.lat_deg is not None) and (point.lon_deg is not None):
            position = et.SubElement(point_record, "Position")
            et.SubElement(position, "LatitudeDegrees").text = str(point.lat_deg)
            et.SubElement(position, "LongitudeDegrees").text = str(point.lon_deg)
        if point.altitude_m is not None:
            et.SubElement(point_record, "AltitudeMeters").text = str(point.altitude_m)
        if point.distance_m is not None:
            et.SubElement(point_record, "DistanceMeters").text = str(point.distance_m)
        if point.heartrate_bpm is not None:
            hr = et.SubElement(point_record, "HeartRateBpm")
            et.SubElement(hr, "Value").text = str(point.heartrate_bpm)
        if point.cadence_rpm is not None:
            et.SubElement(point_record, "Cadence").text = str(point.cadence_rpm)
        if (point.speed_mps is not None) or (point.power_watts is not None):
            ext = et.SubElement(et.SubElement(point_record, "Extensions"),"TPX")
            ext.set("xmlns", "http://www.garmin.com/xmlschemas/ActivityExtension/v2")
            if point.speed_mps is not None:
                et.SubElement(ext, "Speed").text = str(point.speed_mps)
            if point.power_watts is not None:
                et.SubElement(ext, "Watts").text = str(point.power_watts)

    def get_next_point(self):
        '''
        Get the next point in the TCX file.
        Note that if points are added while iterating through points,
        the new points will not be returned.
        '''
        point = Point()
        if not self.points:
            # If not already set, grab the first point from the activity
            if not self.activity:
                self.set_current_activity()
            assert self.activity is not None
            self.points = self.activity.find("Lap", NAMESPACES).find(
                "Track", NAMESPACES).iterfind("Trackpoint", NAMESPACES)
        try:
            point_record = next(self.points)
        except StopIteration:
            self.points = None
            return None
        point.time = point_record.find("Time", NAMESPACES).text
        try:
            lat = point_record.find("Position", NAMESPACES).find("LatitudeDegrees", NAMESPACES)
            lon = point_record.find("Position", NAMESPACES).find("LongitudeDegrees", NAMESPACES)
            if lat is not None and lon is not None:
                point.lat_deg, point.lon_deg = float(lat.text), float(lon.text)
        except AttributeError:
            pass
        alt = point_record.find("AltitudeMeters", NAMESPACES)
        if alt is not None:
            point.altitude_m = float(alt.text)
        dist = point_record.find("DistanceMeters", NAMESPACES)
        if dist is not None:
            point.distance_m = float(dist.text)
        try:
            hr = point_record.find("HeartRateBpm", NAMESPACES).find("Value", NAMESPACES)
            if hr is not None:
                point.heartrate_bpm = int(hr.text)
        except AttributeError:
            pass
        cad = point_record.find("Cadence", NAMESPACES)
        if cad is not None:
            point.cadence_rpm = int(cad.text)
        try:
            spd = point_record.find("Extensions", NAMESPACES)
            if spd is not None:
                spd = spd.find("TPX", {"": NAMESPACES["ns3"]}).find(
                    "Speed", {"": NAMESPACES["ns3"]})
                if spd is not None:
                    point.speed_mps = float(spd.text)
        except AttributeError:
            pass
        try:
            pwr = point_record.find("Extensions", NAMESPACES)
            if pwr is not None:
                pwr = pwr.find("TPX", {"": NAMESPACES["ns3"]}).find(
                    "Watts", {"": NAMESPACES["ns3"]})
                if pwr is not None:
                    point.power_watts = int(pwr.text)
        except AttributeError:
            pass
        return point

    def set_lap_stats(self, total_time_s=None, distance_m=None):
        '''
        Adds total time and distance statistics to the Lap field,
        or updates them if already present.
        '''
        if total_time_s:
            time_tag = self.current_lap.find("TotalTimeSeconds", "")
            if time_tag is None:
                time_tag = et.SubElement(self.current_lap, "TotalTimeSeconds")
            time_tag.text = str(total_time_s)
        if distance_m:
            dist_tag = self.current_lap.find("DistanceMeters", "")
            if dist_tag is None:
                dist_tag = et.SubElement(self.current_lap, "DistanceMeters")
            dist_tag.text = str(distance_m)

    def get_lap_stats(self):
        '''
        Gets the total time and distance for the current lap if they are set.
        '''
        total_time_s = None
        time_tag = self.current_lap.find("TotalTimeSeconds", "")
        if time_tag is not None:
            total_time_s = time_tag.text
        distance_m = None
        dist_tag = self.current_lap.find("DistanceMeters", "")
        if dist_tag is not None:
            distance_m = dist_tag.text

        return total_time_s, distance_m

    def flush(self):
        '''
        Writes tcx file to disk.
        '''
        out = et.tostring(self.tcx, xml_declaration=True, encoding="utf-8")
        out = minidom.parseString(out).toprettyxml(indent="    ")
        with open(self.file_name, "w") as f:
            f.write(out)
