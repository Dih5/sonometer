#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""Listen to sound intensity using a microphone"""

import datetime
import csv
from threading import Lock

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
    def __init__(self, interval, chunk=1024, data_type=pyaudio.paInt16, channels=1, rate=44100):
        self.interval = interval
        self.chunk = chunk
        self.data_type = data_type
        self.channels = channels
        self.rate = rate

        self.p = pyaudio.PyAudio()
        self.selected_api = 0  # TODO: This is a fixed selection
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
        if self.audio_stream is None:
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
    def __init__(self, interval=0.3, plot_f=None, master=None, title="TkListener"):
        super().__init__(master=master)
        self.master.title(title)
        self.pack()
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.active_subplot = self.figure.add_subplot(111)
        self.plot_f = plot_f

        # Create a tk.DrawingArea
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.show()
        self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)

        self.listener = Listener(interval)
        self.listener.start(self.plot_callback)

    def restart_listener(self, interval):
        self.listener.stop()
        self.listener.interval = interval
        #self.listener.start(self.plot_callback)

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
# From this point code could be moved to a new file to avoid repetition in freqmeter.py


def data_to_intensity(data):
    return np.linalg.norm(np.fromstring(data, np.int16), 2)


lock = Lock()


class controlled_execution:
    def __enter__(self):
        return lock.__enter__()

    def __exit__(self, type, value, traceback):
        return lock.__exit__(type, value, traceback)


class Streak:
    def __init__(self, points_max):
        self.start_x = None
        self.end_x = None
        self.data = []
        self.points_max = points_max
        pass

    def __len__(self):
        return len(self.data)

    def add_first(self, start_x, start_y):
        self.start_x = start_x
        self.end_x = start_x
        self.data = [start_y]

    def add(self, y):
        if len(self.data) < self.points_max:
            self.end_x = (self.end_x + 1) % self.points_max
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
        points_max = self.points_max
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


class IntensityListener(TkListener):
    def __init__(self, master=None, points_max=80, interval=0.3):
        super().__init__(plot_f=self.intensity_plot, interval=interval, master=master, title="Sonometer")
        self.current_pos = 0
        self.points_max = points_max  # points kept in the plot

        self.recording = False  # Whether a streak is being recorded

        self.streaks = []  # Saved streaks of data

        self.intensity_data = [0] * self.points_max

        # Add specific controls

        self.varStatus = StringVar()
        self.varStatus.set("Sonometer started")
        self.lblStatus = Label(master=self, textvariable=self.varStatus)
        self.lblStatus.pack(side=BOTTOM)

        self.frmOperations = Frame(master=self)
        self.frmOperations.pack(side=BOTTOM)

        self.buttonClearPoints = Button(master=self.frmOperations, text='Clear points', command=self.clear_points)
        self.buttonClearPoints.pack(side=LEFT)

        self.buttonClearStreaks = Button(master=self.frmOperations, text='Clear streaks', command=self.clear_streaks)
        self.buttonClearStreaks.pack(side=LEFT)

        self.buttonStartStreak = Button(master=self.frmOperations, text='Start streak', command=self.start_streak)
        self.buttonStartStreak.pack(side=LEFT)

        self.buttonStopStreak = Button(master=self.frmOperations, text='Stop streak', command=self.stop_streak,
                                       state=DISABLED)
        self.buttonStopStreak.pack(side=LEFT)

        self.buttonCapture = Button(master=self.frmOperations, text='Plot capture', command=self.plot_capture)
        self.buttonCapture.pack(side=LEFT)

        self.buttonTest = Button(master=self.frmOperations, text='Test', command=self.test)
        self.buttonTest.pack(side=LEFT)

        self.frmConfig = Frame(master=self)
        self.frmConfig.pack(side=BOTTOM)

        self.varStreakLen = IntVar()
        self.varStreakLen.set(0)
        self.lblStreakLen = Label(master=self.frmConfig, text="Streak points")
        self.txtStreakLen = Entry(master=self.frmConfig, textvariable=self.varStreakLen)
        self.lblStreakLen.pack(side=LEFT)
        self.txtStreakLen.pack(side=LEFT)

        self.varStreakToCsv = BooleanVar()
        self.varStreakToCsv.set(True)
        self.chkStreakToCsv = Checkbutton(master=self.frmConfig, text="Save streaks", variable=self.varStreakToCsv)
        self.chkStreakToCsv.pack(side=LEFT)

    def test(self):
        print("asf")
        self.restart_listener(2.0)

    def clear_points(self):
        with controlled_execution():
            self.current_pos = 0
            self.intensity_data = [0] * self.points_max

    def clear_streaks(self):
        with controlled_execution():
            self.streaks = []

    def start_streak(self):
        with controlled_execution():
            self.streaks.append(Streak(self.points_max))
            self.recording = True
            self.buttonStopStreak["state"] = "normal"
            self.buttonStartStreak["state"] = "disabled"
            self.buttonClearPoints["state"] = "disabled"
            self.buttonClearStreaks["state"] = "disabled"

    def stop_streak(self):
        with controlled_execution():
            self.recording = False
            self.buttonStartStreak["state"] = "normal"
            self.buttonStopStreak["state"] = "disabled"
            self.buttonClearPoints["state"] = "enabled"
            self.buttonClearStreaks["state"] = "enabled"
            if self.varStreakToCsv.get():
                t = datetime.datetime.now().strftime("%S%M%H%d%m%y")
                file_name = 'data%s.csv' % t
                with open(file_name, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile, delimiter=',')
                    writer.writerow(self.streaks[-1].data)
                self.varStatus.set("Data saved as %s" % file_name)

    def plot_capture(self):
        with controlled_execution():
            t = datetime.datetime.now().strftime("%S%M%H%d%m%y")
            file_name = "sound" + t + ".pdf"
            self.figure.savefig(file_name)
            self.varStatus.set("Plot saved as " + file_name)

    def intensity_plot(self, in_data, plot):
        self.current_pos += 1
        self.current_pos %= self.points_max
        self.intensity_data[self.current_pos] = data_to_intensity(in_data)
        plot.clear()
        plot.plot(self.intensity_data, 'o')
        plot.plot([self.current_pos], [self.intensity_data[self.current_pos]], 'ro')
        if self.recording:
            if not self.streaks:
                print("Error: tried to record with no streak object")
            else:
                if len(self.streaks[-1]) == 0:
                    self.streaks[-1].add_first(self.current_pos, self.intensity_data[self.current_pos])
                else:
                    self.streaks[-1].add(self.intensity_data[self.current_pos])
                if 0 < self.varStreakLen.get() < len(self.streaks[-1]):
                    self.stop_streak()

        if self.streaks:
            for s in self.streaks[:-1]:
                s.plot(plot, 'yellow')
            self.streaks[-1].plot(plot)

        plot.ticklabel_format(style='sci', axis='y', scilimits=(0, 0))


def main():
    root = Tk()
    app = IntensityListener(root, interval=0.3, points_max=80)
    app.mainloop()


if __name__ == "__main__":
    main()
