#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""Listen to sound intensity using a microphone"""

# Partial rewrite of Object Orientated code, with better style
# TODO: Buttons are yet to be added to the GUI

# While this code is of better quality, if we are going to keep the two programs in one independent file each
# little is gained


import pyaudio  # pacman -S portaudio && pip install pyaudio
import numpy as np
import matplotlib

matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from tkinter import *
from tkinter.ttk import *

__author__ = 'Dih5'
__version__ = "0.1.0"


class Listener:
    def __init__(self, interval=1, chunk=1024, data_type=pyaudio.paInt16, channels=1, rate=44100):
        self.interval = interval
        self.chunk = chunk
        self.data_type = data_type
        self.channels = channels
        self.rate = rate

        self.p = pyaudio.PyAudio()
        self.selected_api = 0  # TODO: Fix selection
        self.selected_device = None
        self.audio_stream = None
        self.to_stop = False  # Whether to stop after next callback

    def list_api(self):
        """Return the list of available apis"""
        return [self.p.get_host_api_info_by_index(x) for x in range(0, self.p.get_host_api_count())]

    def device_list(self, api=None):
        """Return the list of input devices in the given api"""
        if api is None:
            api = self.selected_api
        devices_in_api = self.list_api()[api]['deviceCount']
        recording_device_list = []
        for x in range(0, devices_in_api):
            device = self.p.get_device_info_by_host_api_device_index(api, x)
            if device['maxInputChannels']:
                recording_device_list.append(device)
        return recording_device_list

    def start(self, callback):
        def wrapped_callback(in_data, frame_count, time_info, status_flags):
            callback(in_data)
            return None, pyaudio.paContinue

        if self.audio_stream is not None:
            return False
        if self.selected_device is not None:
            self.audio_stream = self.p.open(format=self.data_type, channels=self.channels, rate=self.rate, input=True,
                                            frames_per_buffer=int(self.rate * self.interval),
                                            stream_callback=wrapped_callback, input_device_index=self.selected_device)
        else:
            self.audio_stream = self.p.open(format=self.data_type, channels=self.channels, rate=self.rate, input=True,
                                            frames_per_buffer=int(self.rate * self.interval),
                                            stream_callback=wrapped_callback)

        self.audio_stream.start_stream()
        return True

    def stop(self):
        if self.audio_stream is not None:
            return False
        self.to_stop = True
        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.audio_stream = None
        return True

    def terminate(self):
        self.stop()
        self.p.terminate()


class TkListener(Frame):
    def __init__(self, plot_f=None, master=None, title="TkListener"):
        super().__init__(master=master)
        self.master.title(title)
        self.pack()
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.active_subplot = self.figure.add_subplot(111)
        self.plot_f = plot_f

        # Create a tk.DrawingArea
        self.canvas = FigureCanvasTkAgg(self.figure, master=master)
        self.canvas.show()
        self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)

        self.listener = Listener()
        self.listener.start(self.plot_callback)

    def plot_callback(self, in_data):
        """The callback function used to update the plot"""
        self.plot_f(in_data, self.active_subplot)
        try:
            self.canvas.draw()
        except TclError:
            print("Canvas is no longer available. Stopping input stream.")
            # Might happen if callbacked before stream destruction
            return None, pyaudio.paAbort
        return None, pyaudio.paContinue


# Specific intensity logic
# From this point code should be moved to a new file

current_pos = 0
points_max = 80  # points kept in the plot

recording = False  # Whether capturing data to take its mean

streaks = []  # Saved streaks of data

intensity_data = [0] * points_max


def data_to_intensity(data):
    return np.linalg.norm(np.fromstring(data, np.int16), 2)


class Streak:
    # TODO: No need to save all data, just update mean and err
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
            place.fill_between([self.start_x, points_max - 1], [mean, mean], [mean + err, mean + err],
                               facecolor=color, alpha=0.5)
            if labeled:
                place.text(0, mean + err, u"%.2f ± %.2f" % (mean, err))


def intensity_plot(in_data, plot):
    global current_pos, points_max, recording, streaks, intensity_data, current_pos
    current_pos += 1
    current_pos %= points_max
    intensity_data[current_pos] = data_to_intensity(in_data)
    plot.clear()
    plot.plot(intensity_data, 'o')
    plot.plot([current_pos], [intensity_data[current_pos]], 'ro')
    if recording:
        if not streaks:
            print("Error: tried to record with no streak object")
        else:
            if len(streaks[-1]) == 0:
                streaks[-1].add_first(current_pos, intensity_data[current_pos])
            else:
                streaks[-1].add(intensity_data[current_pos])

    if streaks:
        for s in streaks[:-1]:
            s.plot(plot, 'yellow')
        streaks[-1].plot(plot)


def main():
    root = Tk()
    app = TkListener(master=root, plot_f=intensity_plot)
    app.mainloop()


if __name__ == "__main__":
    main()
