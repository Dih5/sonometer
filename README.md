[![license MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/Dih5/sonometer/master/LICENSE.txt)
# sonometer
A program to listen to sound intensity using a microphone

## Requisites
This program requires a Python 3 interpreter with the following packages: pyaudio, numpy and matplotlib. Assuming you have [pip](https://pip.pypa.io/en/stable/installing/) just run:
```
pip install pyaudio numpy matplotlib
```
Perhaps using `pip3` instead. Also make sure you have tk support.

Unexperienced users and Windows users are advised to [download Anaconda](https://www.continuum.io/downloads) (choosing python 3.X) and run from the command line
```
pip install pyaudio
```
to add the only package its installations lacks of.
## Running
[Download](https://github.com/Dih5/sonometer/archive/master.zip) and call the scripts with your Python interpreter, e.g.,`python3 sonometer.py`.
## Troubleshooting
- Make sure the appropriate interpreter is being used. `Python --version` might help.
- If you had a previously installed python version you might need to clear the PYTHONPATH variable.
