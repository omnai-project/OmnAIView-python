# DevDataClient for the **OmnAIView-DevDataServer**

A minimal desktop client that uses **Tkinter** and **matplotlib** to show live measurement curves streamed by an external server.
It purpose is to show a minimal example of a python frontend that receives timeseries data via a websocket from a backend.

The example shows how to receive data from a [DevDataServer](https://github.com/AI-Gruppe/OmnAIView-DevDataServer) as well as data from the [OmnAIDevServer](https://github.com/AI-Gruppe/OmnAIScope-DataServer) that provides data from a real life oscilloscope the OmnAIScope(https://omnaiscope.auto-intern.de/).

This example is part of the [OmnAIView](https://github.com/AI-Gruppe/OmnAIView) project an OpenSource project for an omnipotent Datavisualization and Dataanalyzing tool and shows an implementation in python instead of Angular. 

---
## 1 DevDataServer Setup 
### 1  Prerequisites for the DevDataServer 

Packages    
Install once inside a virtual-env:
``` bash 
python -m venv env
# Linux/macOS
source env/bin/activate
# Windows
env\Scripts\activate
pip install requests websockets matplotlib
``` 

### 2  Start the DevDataServer (backend)

``` bash
git clone https://github.com/AI-Gruppe/OmnAIView-DevDataServer.git
cd OmnAIView-DevDataServer/example_python
python main.py
```

### → “Server running on port 8080 (HTTP & WebSocket)”
Tip: If you run the server on a different host or port, remember the address; you’ll need it in the client.

## 2 OmnAIScope Server Setup 
### Download the executable from omnaiscope.auto-intern.de/download
### Run the exe 
``` bash 
.\MiniOmni.exe -w 
```

This starts a websocket on port 8080. 

## Important note: The OmnAIBackend and the DevDataServer run on the same port so you are not able to use both at the same time without adjustments 

## 3 Launch the GUI
``` bash
python main.py      # inside the DevDataClient folder
```
## 4 Workflow
Click “Connect to Websocket”
A dialog pops up. Choose your datasource. Enter the server address in the form ip:port, e.g. localhost:8080, then confirm.

The client fetches the device list via GET /UUID.
A second dialog appears, listing all available devices as check-boxes.

Select one or more devices, choose a sample rate (Hz) and the data format (json or csv), then press “Start Measurement”.

The pop-up closes and the live curves appear:

Legend keys = device UUIDs

Line colours = RGB values sent by the server

The upper toolbar remains visible so you can reconnect after closing the window.

Close the main window to end the WebSocket session cleanly.

## 5 Known limitations
Only one measurement session at a time.

No persistent recording – this client is a live scope.

Keeps the latest 1 000 samples per channel in memory; older points are discarded to save RAM.

## 6 License
MIT – see the original DevDataServer repository.