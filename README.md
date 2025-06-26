# DevDataClient for the **OmnAIView-DevDataServer**

A minimal desktop client that uses **Tkinter** and **matplotlib** to show live measurement curves streamed by an external server.
It purpose is to show a minimal example of a python frontend that receives timeseries data via a websocket from a backend.

The example shows how to receive data from a [DevDataServer](https://github.com/AI-Gruppe/OmnAIView-DevDataServer) as well as data from the [OmnAIDevServer](https://github.com/AI-Gruppe/OmnAIScope-DataServer) that provides data from a real life oscilloscope the OmnAIScope(https://omnaiscope.auto-intern.de/).

This example is part of the [OmnAIView](https://github.com/AI-Gruppe/OmnAIView) project an OpenSource project for an omnipotent Datavisualization and Dataanalyzing tool and shows an implementation in python instead of Angular. 

---
## DataServers
This project works with all OmnAI compatible Data-Sources. 
Two prominent ones being:
1) [OmnAIView-DevDataServer](https://github.com/AI-Gruppe/OmnAIView-DevDataServer)
2) [OmnAI-CLI Tool](omnaiscope.auto-intern.de/download)

### DevDataServer
Set up the DevDataServer according to its [own README.md](https://github.com/AI-Gruppe/OmnAIView-DevDataServer/blob/master/README.md)
 → “Server running on port 8080 (HTTP & WebSocket)”
Tip: If you run the server on a different host or port, remember the address; you’ll need it in the client.

## OmnAI-CLI Tool
This assumes you have a working OmnAIScope, that you can connect to your computer.
1) Download the executable from omnaiscope.auto-intern.de/download
2) Run the exe 
``` bash 
.\MiniOmni.exe -w 
```

This starts a websocket on port 8080. 

> Important note: The OmnAIBackend and the DevDataServer run on the same port so you are not able to use both at the same time without adjustments 
### More References for the OmnAI-CLI Tool
* YouTube: [Using the OmnAIScope on Windows as a signal recorder](https://www.youtube.com/watch?v=0I5KWNq08IA)
* YouTube: [Raspberry Pi Oscilloscope! Using the AUTO INTERN OmnAIScope as an analog signal recorder](https://www.youtube.com/watch?v=xMsWKSsuCRk)

## Launch the GUI
Make sure you have installed *Python3.12* (or newer). If you are running Linux, you additionally need to install `python3-tk`.

### Steps to Run the GUI
1) Clone the Repo
2) Navigate into the Base-Dir
3) Setup Virtual Environment
4) Install Dependencies
5) RUN!

``` bash
git clone https://github.com/AI-Gruppe/OmnAIView-python.git
cd OmnAIView-python
python3.12 -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
python ./src/main.py
```

If you are running Windows, the commands look a bit different:
```sh
git clone https://github.com/AI-Gruppe/OmnAIView-python.git
cd OmnAIView-python
python3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python .\src\main.py
```

### Logging 

If you want to log the values measured run the application with : 
```sh
python ./src/main.py --logging
```


## Workflow 
### Connect to Websocket 
Click “Connect to Websocket”
A dialog pops up. Choose your datasource. Enter the server address in the form ip:port, e.g. localhost:8080, then confirm.

The client fetches the device list via `get_devices`.
A second dialog appears, listing all available devices as check-boxes.

Select one or more devices, choose a sample rate (Hz) and the data format (json or csv), then press “Start Measurement”.

The pop-up closes and the live curves appear:

Legend keys = device UUIDs

Line colours = RGB values sent by the server

The upper toolbar remains visible so you can reconnect after closing the window.

### Recording 

Click record to take a measurment. Important: While recording data is saved in RAM, make sure to not overflow it.

### Analysing 
To analyze data the DevOmnAI-Analysis Server is used . To start the server follow its (own README)[https://github.com/AI-Gruppe/DevMathAnalysisServerOmnAI?tab=readme-ov-file#project-setup] . 

After recording press the analysis button. You should receive the mean of the recorded waveform in a popup window. 

Close the main window to end the WebSocket session cleanly.

## 5 Known limitations
Only one measurement session at a time.

No persistent recording – this client is a live scope.

Keeps the latest 1 000 samples per channel in memory; older points are discarded to save RAM.

## 6 License
MIT – see the original DevDataServer repository.
