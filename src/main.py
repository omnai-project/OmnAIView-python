#!/usr/bin/env python3
"""
Simple Tk-/matplotlib front-end that can talk to **multiple back-ends**
(DevDataServer, OmnAIScope DataServer, …) via a *Strategy Pattern*.
Start:  python main.py
"""

import asyncio
import json
import queue
import threading
from functools import partial
from typing import Dict, List, Tuple
import os 
import datetime 

import matplotlib
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from websockets import connect
import requests

from src.datasources import (
    Device,
    available_sources,
    get_strategy,
)

# ------------------------------------------------------------
# GUI-Class
# ------------------------------------------------------------
class DevDataClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OmnAIView DevDataClient")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # ­­­– Toolbar –­­­
        bar = ttk.Frame(self)
        bar.pack(side="top", fill="x")
        ttk.Button(bar, text="Connect to Websocket",
                   command=self._connect_dialog).pack(side="left", padx=4, pady=4)
        # Record data : Data is saved in RAM until flushed 
        self.rec_btn = ttk.Button(bar, text="● Record",
            command=self._toggle_recording, state="disabled")
        self.rec_btn.pack(side="left", padx=4, pady=4)
        # Analyse data : This is currently fixed to one analysis on a specific server 
        self.analyse_btn = ttk.Button(bar, text="Analysis",       
           command=self._run_analysis, state="disabled") 
        self.analyse_btn.pack(side="left", padx=4, pady=4)

        # ­­­– Plot-Window –­­­
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Value")
        self.lines: Dict[str, matplotlib.lines.Line2D] = {}
        self.data_buffer: Dict[str, List[Tuple[float, float]]] = {}

        # ­­­– async-Communication –­­­
        self.ws_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.queue: "queue.Queue[Tuple[float, List[float]]]" = queue.Queue()

        # ­­­– Strategy (set after connect) –­­­
        self.strategy = None
        self.host_port = ""
        self.active_uuids: List[str] = []
        
        # State Management of Toolbar 
        self.recording   = False
        self.record_data = []           # List[ List[float] ]
        self.record_fh   = None
        self.last_record_file = None 

        # Animation of the data
        self.ani = animation.FuncAnimation(
            self.fig,
            self._update_plot,
            interval=100,
            blit=False,
            cache_frame_data=False,
        )

    # --------------------------------------------------------
    # Step 1 – IP/Port *and* data-source selection
    # --------------------------------------------------------
    def _connect_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Connect")

        ttk.Label(dlg, text="WebSocket-Server (ip:port):") \
            .grid(row=0, column=0, padx=6, pady=4, sticky="e")
        host_var = tk.StringVar(value="localhost:8080")
        ttk.Entry(dlg, textvariable=host_var, width=20) \
            .grid(row=0, column=1, pady=4)

        ttk.Label(dlg, text="Data source:") \
            .grid(row=1, column=0, padx=6, pady=4, sticky="e")
        src_var = tk.StringVar(value=available_sources()[0])
        ttk.Combobox(
            dlg, textvariable=src_var,
            values=available_sources(),
            state="readonly", width=18
        ).grid(row=1, column=1, pady=4)

        ttk.Button(
            dlg, text="Connect",
            command=lambda: self._on_connect_submit(
                dlg, host_var.get().strip(), src_var.get())
        ).grid(row=2, column=0, columnspan=2, pady=8)

    def _on_connect_submit(self, dlg, host_port, source_name):
        dlg.destroy()
        self.strategy = get_strategy(source_name)   # ← concrete Strategy
        self.host_port = host_port
        try:
            devices = self.strategy.fetch_devices(host_port)
        except Exception as e:
            messagebox.showerror("Error", f"Device list cannot be loaded:\n{e}")
            return
        self._device_dialog(devices)

    # --------------------------------------------------------
    # Step 2 – choose devices + options
    # --------------------------------------------------------
    def _device_dialog(self, devices: List[Device]):
        dlg = tk.Toplevel(self)
        dlg.title("Choose devices")
        ttk.Label(dlg, text="Devices:").pack(anchor="w", padx=8, pady=4)

        vars_: Dict[str, tk.BooleanVar] = {}
        for dev in devices:
            v = tk.BooleanVar(value=False)
            ttk.Checkbutton(dlg, text=dev.uuid, variable=v) \
                .pack(anchor="w", padx=20)
            vars_[dev.uuid] = v

        frm = ttk.Frame(dlg)
        frm.pack(fill="x", pady=6)
        ttk.Label(frm, text="Samplerate (Hz):") \
            .grid(row=0, column=0, sticky="e")
        rate_var = tk.IntVar(value=60)
        ttk.Entry(frm, textvariable=rate_var, width=8) \
            .grid(row=0, column=1, sticky="w", padx=4)

        ttk.Label(frm, text="Format:") \
            .grid(row=1, column=0, sticky="e")
        fmt_var = tk.StringVar(value=self.strategy.formats[0])
        ttk.Combobox(frm, textvariable=fmt_var,
                     values=self.strategy.formats,
                     state="readonly", width=7) \
            .grid(row=1, column=1, sticky="w", padx=4)

        ttk.Button(dlg, text="Start measurement",
                   command=partial(
                       self._start_measurement,
                       dlg, vars_, devices, rate_var, fmt_var)
                   ).pack(pady=8)

    # --------------------------------------------------------
    # Step 3 – WebSocket thread start
    # --------------------------------------------------------
    def _start_measurement(self, dlg, vars_, devices, rate_var, fmt_var):
        uuids = [uid for uid, v in vars_.items() if v.get()]
        if not uuids:
            messagebox.showwarning("Warning", "Please choose at least one device.")
            return
        dlg.destroy()

        self.active_uuids = uuids

        # reset plot
        self.ax.clear()
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Value")
        self.lines.clear()
        self.data_buffer.clear()

        for dev in devices:
            if dev.uuid in uuids:
                (line,) = self.ax.plot([], [], label=dev.uuid, color=dev.color)
                self.lines[dev.uuid] = line
                self.data_buffer[dev.uuid] = []
        self.ax.legend(loc="upper right")

        # start websocket thread
        self.stop_event.clear()
        self.ws_thread = threading.Thread(
            target=self._ws_worker,
            args=(
                self.strategy.build_ws_uri(self.host_port),
                self.strategy.build_subscribe_cmd(
                    uuids, rate_var.get(), fmt_var.get()
                ),
            ),
            daemon=True)
        self.ws_thread.start()
        # change toolbar states
        self.rec_btn.config(state="normal")
        self.analyse_btn.config(state="disabled")

    # --------------------------------------------------------
    # Background Thread – WebSocket client (asyncio)
    # connects to websocket and receives the data 
    # --------------------------------------------------------
    def _ws_worker(self, uri: str, subscribe_cmd: str | bytes):
        async def _runner():
            async with connect(uri) as ws:
                # ---- optional “server-talks-first” handshake -------------------
                if self.strategy.server_sends_initial_msg():
                    first_frame = await ws.recv()                # wait & store
                    self.strategy.handle_initial_msg(first_frame)  # may ignore
                # ---- now send the normal subscribe command --------------------
                await ws.send(subscribe_cmd)
                try:
                    while not self.stop_event.is_set():
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        except asyncio.TimeoutError:
                            continue            # regelmäßig Stop-Flag prüfen
                        ts, val_dict = self.strategy.parse_ws_msg(raw)
                        values = [val_dict.get(uid, float("nan"))
                                for uid in self.active_uuids]
                        self.queue.put((ts, values))
                finally:
                    await ws.close()  

        try:
            asyncio.run(_runner())
        except Exception as e:
            self.queue.put(("__error__", e))
            
    # --------------------------------------------------------
    # Record-Handling (record a measurement)
    # --------------------------------------------------------       
    
    def _toggle_recording(self):
        if self.recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # new name for new file via timestamp
        fname = f"testdatei_{ts}.json"
        self.record_fh = open(fname, "w", encoding="utf-8")
        self.record_data.clear()
        self.recording = True
        self.rec_btn.config(text="■ Stop")
        print(f"[Recorder] started: {fname}")

    def _stop_recording(self):
        if not self.recording:
            return
        # dump JSON and close
        json.dump({"signal": self.record_data}, self.record_fh, indent=2)
        self.record_fh.close()
        # set name of last file recorded / this is dummy code seriously not a pretty solution for this 
        self.last_record_file = self.record_fh.name     
        self.analyse_btn.config(state="normal")
        # recording state 
        self.recording = False
        self.rec_btn.config(text="● Record")
        print(f"[Recorder] stopped: {self.record_fh.name}")
    
    # --------------------------------------------------------
    # send last recording as pure JSON to /mean and show result
    # --------------------------------------------------------
    def _run_analysis(self):
        if not self.last_record_file or not os.path.exists(self.last_record_file):
            messagebox.showinfo("Analysis", "No recording available.")
            return

        # 1) load JSON file
        try:
            with open(self.last_record_file, "r", encoding="utf-8") as fh:
                payload = json.load(fh)         
        except Exception as exc:
            messagebox.showerror("Analysis", f"Cannot read file:\n{exc}")
            return

        # 2) POST as application/json 
        url = "http://127.0.0.1:8000/mean"
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            mean_val = resp.json().get("mean_value")
        except Exception as exc:
            messagebox.showerror("Analysis", f"Request failed:\n{exc}")
            return
        
        messagebox.showinfo("Analysis", f"Mittelwert : {mean_val}")



    # --------------------------------------------------------
    # Plot-Update (every 100 ms)
    # --------------------------------------------------------
    def _update_plot(self, _):
        while not self.queue.empty():
            item = self.queue.get_nowait()
            if item[0] == "__error__":
                messagebox.showerror("WebSocket-Error", str(item[1]))
                self.stop_event.set()
                return
            ts, values = item
            # Record data until flushed
            if self.recording:
                self.record_data.append([ts, *values]) 
            for uid, val in zip(self.active_uuids, values):
                self.data_buffer[uid].append((ts, val))
                # keep only last 1000 datapoints
                if len(self.data_buffer[uid]) > 1000:
                    self.data_buffer[uid] = self.data_buffer[uid][-1000:]
                xs, ys = zip(*self.data_buffer[uid])
                self.lines[uid].set_data(xs, ys)

        # scale axis automatically
        if any(self.data_buffer[uid] for uid in self.active_uuids):
            self.ax.relim()
            self.ax.autoscale_view()
        self.canvas.draw_idle()

    # --------------------------------------------------------
    # Clean up when closed
    # --------------------------------------------------------
    def _on_close(self):
        self.stop_event.set()
        # ensure data is flushed when app is closed 
        if self.recording:                       
            self._stop_recording()
        self.destroy()


# ------------------------------------------------------------
# start point
# ------------------------------------------------------------
if __name__ == "__main__":
    matplotlib.use("TkAgg")
    DevDataClient().mainloop()
