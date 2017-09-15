#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""Listen to sound intensity using a microphone"""

import datetime
import threading
import csv

import pyaudio  # pacman -S portaudio jack2 && pip install pyaudio
import numpy as np
import matplotlib

matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from tkinter import *
from tkinter.ttk import *

__author__ = 'Dih5'
__version__ = "0.1.0"

chunk = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1

RATE = 44100  # samples per second
interval = 0.3  # seconds sampled for a point

points_max = 80  # points kept in the plot

recording = False  # Whether capturing data to take its mean

streaks = []  # Saved streaks of data

lock = threading.Lock()  # A lock for thread synchronization


# FIXME: Using the lock leads to interlock death. When two threads ask for it no one returns, I don't know why
class controlled_execution:
    def __enter__(self):
        # return lock.__enter__()
        return

    def __exit__(self, type, value, traceback):
        # return lock.__exit__(type, value, traceback)
        return


class Streak:
    def __init__(self):
        self.start_x = None
        self.end_x = None
        self.data = []
        pass

    def __len__(self):
        return len(self.data)

    def add_first(self, start_x, start_y):
        self.start_x = start_x
        self.end_x = start_x
        self.data = [start_y]

    def add(self, y):
        if len(self.data) < points_max:
            self.end_x = (self.end_x + 1) % points_max
        self.data.append(y)

    def mean(self):
        return np.mean(self.data) if len(self) > 0 else 0

    def err(self):
        return np.std(self.data, ddof=1) / np.sqrt(len(self.data)) if len(self) > 1 else 0

    def plot(self, place, color='green', labeled=True):
        if len(self) < 2:
            return
        mean = self.mean()
        err = self.err()
        if len(self) >= points_max:  # Covers all plot
            place.plot([0, points_max - 1], [mean, mean], '-', color=color)
            place.fill_between([0, points_max - 1], [mean - err, mean - err], [mean, mean], facecolor=color,
                               alpha=0.5)
            place.fill_between([0, points_max - 1], [mean, mean], [mean + err, mean + err], facecolor=color,
                               alpha=0.5)
            if labeled:
                place.text(points_max / 2, mean + err, u"%.2f ± %.2f" % (mean, err))
        elif self.end_x > self.start_x:  # No anomalies
            place.plot([self.start_x, self.end_x], [mean, mean], '-', color=color)
            place.fill_between([self.start_x, self.end_x], [mean - err, mean - err], [mean, mean],
                               facecolor=color, alpha=0.5)
            place.fill_between([self.start_x, self.end_x], [mean, mean], [mean + err, mean + err],
                               facecolor=color, alpha=0.5)
            if labeled:
                place.text(self.start_x, mean + err, u"%.2f ± %.2f" % (mean, err))
        elif self.end_x < self.start_x:  # Wraps circularly
            place.plot([0, self.end_x], [mean, mean], '-', color=color)
            place.fill_between([0, self.end_x], [mean - err, mean - err], [mean, mean],
                               facecolor=color, alpha=0.5)
            place.fill_between([0, self.end_x], [mean, mean], [mean + err, mean + err],
                               facecolor=color, alpha=0.5)
            place.plot([self.start_x, points_max - 1], [mean, mean], '-', color=color)
            place.fill_between([self.start_x, points_max - 1], [mean - err, mean - err], [mean, mean],
                               facecolor=color, alpha=0.5)
            active_subplot.fill_between([self.start_x, points_max - 1], [mean, mean], [mean + err, mean + err],
                                        facecolor=color, alpha=0.5)
            if labeled:
                place.text(0, mean + err, u"%.2f ± %.2f" % (mean, err))


def data_to_intensity(data):
    return np.linalg.norm(np.fromstring(data, np.int16), 2)


p = pyaudio.PyAudio()

api_list = [p.get_host_api_info_by_index(x) for x in range(0, p.get_host_api_count())]
selected_api = 0
devices_in_api = api_list[selected_api]['deviceCount']
print("Available api(s): ")
print(api_list)

recording_device_list = []
for x in range(0, devices_in_api):
    device = p.get_device_info_by_host_api_device_index(selected_api, x)
    if device['maxInputChannels']:
        recording_device_list.append(device)

print("Available recording device(s): ")
print(recording_device_list)

root = Tk()
root.wm_title("Sound intensity listener")
figure = Figure(figsize=(5, 4), dpi=100)
active_subplot = figure.add_subplot(111)
intensity_data = [0] * points_max
current_pos = 0

active_subplot.plot(intensity_data, 'o')

# Create a tk.DrawingArea
canvas = FigureCanvasTkAgg(figure, master=root)
canvas.show()
canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)


# Select device

# def _change_device(*args):
#     global audio_stream, current_pos, intensity_data
#     with controlled_execution():
#         audio_stream.stop_stream()
#         time.sleep(1)
#         audio_stream.close()
#         index = recording_device_list[cmbDevice.current()]['index']
#         print("setting device " + str(index))
#         current_pos = 0
#         intensity_data = [0] * points_max
#         audio_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True,
#                               frames_per_buffer=int(RATE * interval),
#                               stream_callback=input_callback, input_device_index=index)
#         audio_stream.start_stream()
#
#
# varDevice = StringVar()
# varDevice.set(p.get_default_input_device_info()['name'])
# cmbDevice = Combobox(master=root, textvariable=varDevice, width=70)
# device_cmb_list = [x['name'] for x in recording_device_list]
# cmbDevice["values"] = device_cmb_list
# cmbDevice.pack(side=BOTTOM)
#
# cmbDevice.bind("<<ComboboxSelected>>", _change_device)


def _clear_points():
    global intensity_data, current_pos
    with controlled_execution():
        current_pos = 0
        intensity_data = [0] * points_max


def _clear_streaks():
    global streaks
    with controlled_execution():
        streaks = []


def _start_streak():
    global streaks, recording
    with controlled_execution():
        streaks.append(Streak())
        recording = True
        buttonStopStreak["state"] = "normal"
        buttonStartStreak["state"] = "disabled"
        buttonClearPoints["state"] = "disabled"
        buttonClearStreaks["state"] = "disabled"


def _stop_streak():
    global recording, streaks
    with controlled_execution():
        recording = False
        buttonStartStreak["state"] = "normal"
        buttonStopStreak["state"] = "disabled"
        buttonClearPoints["state"] = "enabled"
        buttonClearStreaks["state"] = "enabled"
        if varStreakToCsv.get():
            t = datetime.datetime.now().strftime("%S%M%H%d%m%y")
            with open('data%s.csv' % t, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                writer.writerow(streaks[-1].data)


frmOperations = Frame(master=root)
frmOperations.pack(side=BOTTOM)

buttonClearPoints = Button(master=frmOperations, text='Clear points', command=_clear_points)
buttonClearPoints.pack(side=LEFT)

buttonClearStreaks = Button(master=frmOperations, text='Clear streaks', command=_clear_streaks)
buttonClearStreaks.pack(side=LEFT)

buttonStartStreak = Button(master=frmOperations, text='Start streak', command=_start_streak)
buttonStartStreak.pack(side=LEFT)

buttonStopStreak = Button(master=frmOperations, text='Stop streak', command=_stop_streak, state=DISABLED)
buttonStopStreak.pack(side=LEFT)

varStreak = StringVar()
varStreak.set("No data yet")
lblStreak = Label(master=frmOperations, textvariable=varStreak)
lblStreak.pack(side=RIGHT)

frmConfig = Frame(master=root)
frmConfig.pack(side=BOTTOM)

varStreakLen = IntVar()
varStreakLen.set(0)
lblStreakLen = Label(master=frmConfig, text="Streak time")
txtStreakLen = Entry(master=frmConfig, textvariable=varStreakLen)
lblStreakLen.pack(side=LEFT)
txtStreakLen.pack(side=LEFT)

varStreakToCsv = BooleanVar()
varStreakToCsv.set(True)
chkStreakToCsv = Checkbutton(master=frmConfig, text="Save streaks", variable=varStreakToCsv)
chkStreakToCsv.pack(side=LEFT)


def _plot_capture():
    global canvas
    with controlled_execution():
        t = datetime.datetime.now().strftime("%S%M%H%d%m%y")
        figure.savefig("sound" + t + ".pdf")


buttonCapture = Button(master=frmOperations, text='Plot capture', command=_plot_capture)
buttonCapture.pack(side=LEFT)


# To be called when audio is read
def input_callback(in_data, frame_count, time_info, status_flags):
    global intensity_data, current_pos, active_subplot, canvas, streaks
    with controlled_execution():
        current_pos += 1
        current_pos %= points_max
        intensity_data[current_pos] = data_to_intensity(in_data)
        active_subplot.clear()
        active_subplot.plot(intensity_data, 'o')
        active_subplot.plot([current_pos], [intensity_data[current_pos]], 'ro')
        if recording:
            if not streaks:
                print("Error: tried to record with no streak object")
            else:
                if len(streaks[-1]) == 0:
                    streaks[-1].add_first(current_pos, intensity_data[current_pos])
                else:
                    streaks[-1].add(intensity_data[current_pos])

                if 0 < varStreakLen.get() < len(streaks[-1]):
                    _stop_streak()

        if streaks:
            for s in streaks[:-1]:
                s.plot(active_subplot, 'yellow')
            streaks[-1].plot(active_subplot)
            varStreak.set("Last streak = %.2f ± %.2f" % (streaks[-1].mean(), streaks[-1].err()))

        active_subplot.ticklabel_format(style='sci', axis='y', scilimits=(0, 0))

        try:
            canvas.draw()
        except TclError:
            print("Canvas is no longer available. Stopping input stream.")
            # Might happen if callbacked before stream destruction
            return None, pyaudio.paAbort
        return None, pyaudio.paContinue


# Stream file
audio_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=int(RATE * interval),
                      stream_callback=input_callback)

audio_stream.start_stream()

root.mainloop()

# If you put root.destroy() here, it will cause an error if
# the window is closed with the window manager.


audio_stream.stop_stream()

audio_stream.close()

p.terminate()
