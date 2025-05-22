# DevDataClient for the **OmnAIView-DevDataServer**

A minimal desktop client that uses **Tkinter** and **matplotlib** to show live measurement curves streamed by the DevDataServer [https://github.com/AI-Gruppe/OmnAIView-DevDataServer.git].
It purpose is to show a minimal example of a python frontend that receives timeseries data via a websocket from a backend. 


---

## 1  Prerequisites

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

## 2  Start the DevDataServer (backend)

``` bash
git clone https://github.com/AI-Gruppe/OmnAIView-DevDataServer.git
cd OmnAIView-DevDataServer/example_python
python main.py
```

# → “Server running on port 8080 (HTTP & WebSocket)”
Tip: If you run the server on a different host or port, remember the address; you’ll need it in the client.

## 3 Launch the GUI
``` bash
python main.py      # inside the DevDataClient folder
```
## 4 Workflow
Click “Connect to Websocket”
A dialog pops up. Enter the server address in the form ip:port, e.g. localhost:8080, then confirm.

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