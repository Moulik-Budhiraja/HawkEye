
import numpy as np
import pandas as pd 
from taipy.gui import Gui
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin import db

# Fetch the service account key JSON file contents
cred = credentials.Certificate('serviceAccountKey.json')

# Initialize the app with a service account, granting admin privileges
firebase_admin.initialize_app(cred, {
     "databaseURL": "https://rythmhacks-4811d-default-rtdb.firebaseio.com/",
})

# As an admin, the app has access to read and write all data, regradless of Security Rules
blinkRef = db.reference('BlinkData')
blinkRefData = blinkRef.get()
print(blinkRefData)
blinkRefData = sorted(blinkRefData.items(), key=lambda x: x[1]['time'])
page = """
# HawkEye

<|layout|columns=1fr 1fr|
## Your Eyeblinks

## Time Between Eyeblinks

<|{eye_blink_data}|chart|mode=markers|x=Time|y[1]=Eye Blink|>

<|{blink_difference_data}|type=bar|chart|x=Keys|y=Values|>

|>

<|layout|columns=1fr 1fr |

## Left vs Right Eyeblinks

## Blink to Non-Blink Ratio

<|{per_eye_blink}|chart|type=pie|values=Blinks|labels=Eye|>

<|{blink_ratio}|chart|type=pie|values=Count|labels=Blinks|marker={marker}|>
|>

<|layout|columns=1fr 1fr|
## General Analytics
## Standard Deviation Between Eyeblinks

### <|{recommendation}|>
### <|{std} seconds deviation between each time you blinked your eyes|>
|>
"""
raw_timestamps = []
formatted_timestamps = [ ] # Time range of blinks
time_diff_counts = {}  # Dictionary to hold time differences and their counts
eye_blink = []
non_blink = []
right_blink_count = 0
left_blink_count = 0

def process_csv():
    global right_blink_count
    global left_blink_count
    for key, row in blinkRefData:
        blinked = row.get("blinked") # this is either True or False - blink or not
        eye = row.get("eye") # this is either left or right
        timestamp = row.get("time") # unix timestamp, convert to time 

        if blinked == "True":
            if eye == "left":
                left_blink_count += 1
                eye_blink.append("Left Blink")
            else:
                eye_blink.append("Right Blink")
                right_blink_count += 1
            
            raw_timestamps.append(timestamp)
            dt = datetime.fromtimestamp(float(timestamp))
            formatted_timestamps.append(dt.strftime('%H:%M:%S'))
        else:
            non_blink.append("No Blink")


# Calculate time between blinks
def time_between_blinks():
    for i in range(len(raw_timestamps) - 1):
        end_time = float(raw_timestamps[i + 1])
        initial_time = float(raw_timestamps[i])
        time_between =  round(end_time - initial_time, 2)
        print(end_time, initial_time, time_between)
        if time_between in time_diff_counts:
            time_diff_counts[time_between] += 1
        else:
            time_diff_counts[time_between] = 1


process_csv()
time_between_blinks()
std = np.std(list(time_diff_counts.keys()))
print(std)
# General data on time of blinks vs eye
eye_blink_data = pd.DataFrame({
  "Time" : formatted_timestamps,
  "Eye Blink" : eye_blink,
})

# Blinks per eye, right vs left
per_eye_blink = pd.DataFrame({
    "Eye" : ["Left", "Right"],
    "Blinks" : [left_blink_count, right_blink_count]
})

# Difference between the time between your blinks
blink_difference_data = pd.DataFrame(list(time_diff_counts.items()), columns=['Keys', 'Values'])

# Blink to non-blink ratio
blink_ratio = pd.DataFrame({
    "Blinks" : ["No Blinks", "Blinks"],
    "Count" : [len(eye_blink), len(non_blink)]
})

marker = {
    # Colors move around the Hue color disk
    "colors": ["black", "blue",]
}

if len(eye_blink) > len(non_blink):
    recommendation = "You blinked more than you didn't blink. Try to blink less."
else:
    recommendation = "You blinked less than you didn't blink. Try to blink more."

pages = {"/":"<|toggle|theme|>\n<center>\n<|navbar|>\n</center>",
         "View":page,}

Gui(pages=pages).run(use_reloader=True)