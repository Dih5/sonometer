#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""Listen to sound frequency using a microphone"""

import time
import threading

import pyaudio  # pip install pyaudio
import numpy as np
import matplotlib

matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib import ticker

from tkinter import *
from tkinter.ttk import *

__author__ = 'Dih5'
__version__ = "0.1.0"

chunk = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1

RATE = 44100  # samples per second
interval = 0.3  # seconds sampled for a point

points_max = 40  # points kept in the plot

recording = False  # Whether capturing data to take its mean

streaks = []  # Saved streaks of data

lock = threading.Lock()  # A lock for thread synchronization

freq_matrix = []


# FIXME: Using the lock leads to interlock death. When two threads ask for it no one returns, I don't know why
class controlled_execution:
    def __enter__(self):
        # return lock.__enter__()
        return

    def __exit__(self, type, value, traceback):
        # return lock.__exit__(type, value, traceback)
        return


def data_to_freq(data):
    return np.abs(np.fft.rfft(np.fromstring(data, np.int16)))


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
root.wm_title("Sound frequency listener")
figure = Figure(figsize=(5, 4), dpi=100)
active_subplot = figure.add_subplot(111)


# Create a tk.DrawingArea
canvas = FigureCanvasTkAgg(figure, master=root)
canvas.show()
canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)


# Select device

# def _change_device(*args):
#     global audio_stream
#     with controlled_execution():
#         audio_stream.stop_stream()
#         time.sleep(1)
#         audio_stream.close()
#         index = recording_device_list[cmbDevice.current()]['index']
#         _clear_data()
#         print("setting device " + str(index))
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


def _clear_data():
    global freq_matrix
    with controlled_execution():
        freq_matrix = []


frmOperations = Frame(master=root)
frmOperations.pack(side=BOTTOM)

buttonClearPoints = Button(master=frmOperations, text='Clear data', command=_clear_data)
buttonClearPoints.pack(side=LEFT)

# in rfft n input points produce n/2+1 complex points
sldScale = Scale(master=root, to=RATE * interval / 2 + 1, orient=HORIZONTAL, length=600)
sldScale.set(1000)
sldScale.pack(side=BOTTOM)


# To be called when audio is read
def input_callback(in_data, frame_count, time_info, status_flags):
    global active_subplot, canvas, streaks, colorbar
    with controlled_execution():
        active_subplot.clear()
        freq_matrix.append(data_to_freq(in_data))
        points_in_x = int(sldScale.get())
        try:
            contour_plot = active_subplot.contourf(np.fft.rfftfreq(int(interval * RATE), d=1. / RATE)[:points_in_x],
                                               np.arange(0, len(freq_matrix), 1)*interval,
                                               np.array(freq_matrix)[:, :points_in_x],
                                               locator=ticker.LogLocator(),
                                               cmap='summer')
            active_subplot.set_ylabel("time (s)")
            active_subplot.set_xlabel("frequency (Hz)")
        except IndexError:
            print("Warning: Tried to plot with no points. This may had happened if the data was cleaned.")
        # figure.colorbar(contour_plot)

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
