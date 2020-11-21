"""
Creates a TCX file and allows adding track points with activity data.
"""

import xml.etree.ElementTree as et
from xml.dom import minidom
from enum import Enum
from datetime import datetime as dt

def _time_stamp():
    '''
    Returns a UTC timestamp string
    '''
    return dt.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

class Tcx():
    '''
    Creates a TCX xml tree, allows adding points to it, and handles
    writing to a file.
    '''
    class ActivityType(Enum):
        '''
        Type of activity, one of the TCX activity types
        '''
        RUNNING = 0
        BIKING = 1
        OTHER = 2
        MULTISPORT = 3

    def __init__(self, file_name="{}.tcx".format(dt.now().strftime("%Y%m%d_%H%M%S"))):
        self.tcx = et.Element("TrainingCenterDatabase")
        self.tcx.set("xsi:schemaLocation",
                     "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 " \
                      "http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd")
        self.tcx.set("xmlns:ns5",
                     "http://www.garmin.com/xmlschemas/ActivityGoals/v1")
        self.tcx.set("xmlns:ns3",
                     "http://www.garmin.com/xmlschemas/ActivityExtension/v2")
        self.tcx.set("xmlns:ns2",
                     "http://www.garmin.com/xmlschemas/UserProfile/v2")
        self.tcx.set("xmlns",
                     "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2")
        self.tcx.set("xmlns:xsi",
                     "http://www.w3.org/2001/XMLSchema-instance")
        self.activities = et.SubElement(self.tcx, "Activities")
        self.file_name = file_name
        self.activity = None
        self.current_lap = None

    def start_activity(self, activity_type):
        '''
        Starts an activity, track and lap.
        Assumes only one track and lap per activity.
        TODO: handle multiple tracks and laps?
        '''
        assert isinstance(activity_type, Tcx.ActivityType)
        self.activity = et.SubElement(self.activities, "Activity")
        self.activity.set("Sport", activity_type.name)
        et.SubElement(self.activity, "Id").text = _time_stamp()
        self.current_lap = et.SubElement(et.SubElement(self.activity, "Track"), "Lap")


    def add_point(self, lat_deg=None, lon_deg=None, altitude_m=None, distance_m=None,
                  heartrate_bpm=None, cadence_rpm=None, speed_mps=None, power_watts=None):
        '''
        Adds an activity point, including position, speed, altitude, heartrate,
        power, etc. (all optional).
        '''
        point = et.SubElement(self.current_lap, "Trackpoint")
        et.SubElement(point, "Time").text = _time_stamp()
        if lat_deg and lon_deg:
            position = et.SubElement(point, "Position")
            et.SubElement(position, "LatitudeDegrees").text = str(lat_deg)
            et.SubElement(position, "LongitudeDegrees").text = str(lon_deg)
        if altitude_m:
            et.SubElement(point, "AltitudeMeters").text = str(altitude_m)
        if distance_m:
            et.SubElement(point, "DistanceMeters").text = str(distance_m)
        if heartrate_bpm:
            hr = et.SubElement(point, "HeartRateBpm")
            et.SubElement(hr, "Value").text = str(heartrate_bpm)
        if cadence_rpm:
            et.SubElement(point, "Cadence").text = str(cadence_rpm)
        if speed_mps or power_watts:
            ext = et.SubElement(et.SubElement(point, "Extensions"),"TPX")
            ext.set("xmlns", "http://www.garmin.com/xmlschemas/ActivityExtension/v2")
            if speed_mps:
                et.SubElement(ext, "Speed").text = str(speed_mps)
            if power_watts:
                et.SubElement(ext, "Watts").text = str(power_watts)

    def lap_stats(self, total_time_s=None, distance_m=None):
        '''
        Adds total time and distance statistics to the Lap field,
        or updates them if already present.
        '''
        if total_time_s:
            time_tag = self.current_lap.find("TotalTimeSeconds")
            if not time_tag:
                time_tag = et.SubElement(self.current_lap, "TotalTimeSeconds")
            time_tag.text = str(total_time_s)
        if distance_m:
            dist_tag = self.current_lap.find("DistanceMeters")
            if not dist_tag:
                dist_tag = et.SubElement(self.current_lap, "DistanceMeters")
            dist_tag.text = str(distance_m)

    def flush(self):
        '''
        Writes tcx file to disk.
        '''
        out = et.tostring(self.tcx, "utf-8")
        out = minidom.parseString(out).toprettyxml(indent="    ")
        with open(self.file_name, "w") as f:
            f.write(out)


if __name__ == "__main__":
    file = Tcx()
    file.start_activity(activity_type=Tcx.ActivityType.OTHER)
    file.add_point(
      lat_deg=51.5014600,
      lon_deg=-0.1402330,
      altitude_m=12.2,
      distance_m=2.0,
      heartrate_bpm=92,
      cadence_rpm=39,
      speed_mps=0.0,
      power_watts=92)
    file.lap_stats(total_time_s=10, distance_m=150)
    file.flush()
    file.add_point(
        heartrate_bpm=92,
        cadence_rpm=39,
        power_watts=92)
    file.lap_stats(total_time_s=104, distance_m=123)
    file.flush()
