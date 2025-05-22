#!/usr/bin/env python3
"""
Simple Tk-/matplotlib-Frontend for the OmnAIView-DevDataServer.
Start:  python main.py
"""

import asyncio
import json
import queue
import threading
import time
from dataclasses import dataclass
from functools import partial
from typing import Dict, List, Tuple

import requests
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import matplotlib
import matplotlib.animation as animation
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from websockets import connect


# ------------------------------------------------------------
# Datatypes 
# ------------------------------------------------------------
@dataclass
class Device:
    uuid: str
    color: str   # hex-RGB »#rrggbb«


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

        # Animation of the data
        self.ani = animation.FuncAnimation(
            self.fig,
            self._update_plot,
            interval=100,
            blit=False,
            cache_frame_data=False,
        )

    # --------------------------------------------------------
    # Step 1 – Set IP/Port
    # --------------------------------------------------------
    def _connect_dialog(self):
        target = simpledialog.askstring(
            "Connect", "WebSocket-Server (ip:port):", initialvalue="localhost:8080", parent=self)
        if not target:
            return
        try:
            devs = self._fetch_device_list(target)
        except Exception as e:
            messagebox.showerror("Error", f"Devicelist cant be loaded:\n{e}")
            return
        self._device_dialog(target, devs)

    # --------------------------------------------------------
    # Step 2 – fetch devices (HTTP GET /UUID)
    # This needs to implement the interface that was set for the specific server 
    # --------------------------------------------------------
    def _fetch_device_list(self, target: str) -> List[Device]:
        url = f"http://{target}/UUID"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        devices: List[Device] = []
        for ds in resp.json()["datastreams"]:
            rgb = ds["color"]
            devices.append(Device(
                uuid=ds["UUID"],
                color=f"#{rgb['r']:02x}{rgb['g']:02x}{rgb['b']:02x}"
            ))
        return devices

    # --------------------------------------------------------
    # Step 3 – Choose devices + options
    # --------------------------------------------------------
    def _device_dialog(self, target: str, devices: List[Device]):
        dlg = tk.Toplevel(self)
        dlg.title("Choose devices")
        ttk.Label(dlg, text="Devices:").pack(anchor="w", padx=8, pady=4)

        vars_: Dict[str, tk.BooleanVar] = {}
        for dev in devices:
            v = tk.BooleanVar(value=False)
            chk = ttk.Checkbutton(dlg, text=dev.uuid, variable=v)
            chk.pack(anchor="w", padx=20)
            vars_[dev.uuid] = v

        frm = ttk.Frame(dlg)
        frm.pack(fill="x", pady=6)
        ttk.Label(frm, text="Samplerate (Hz):").grid(row=0, column=0, sticky="e")
        rate_var = tk.IntVar(value=60)
        ttk.Entry(frm, textvariable=rate_var, width=8).grid(row=0, column=1, sticky="w", padx=4)

        ttk.Label(frm, text="Format:").grid(row=1, column=0, sticky="e")
        fmt_var = tk.StringVar(value="json")
        ttk.Combobox(frm, textvariable=fmt_var, state="readonly",
                     values=("json", "csv"), width=7).grid(row=1, column=1, sticky="w", padx=4)

        ttk.Button(dlg, text="Start measurement",
                   command=partial(self._start_measurement, dlg, target, vars_, devices, rate_var, fmt_var)
                   ).pack(pady=8)

    # --------------------------------------------------------
    # Step 4 – WebSocket - start thread 
    # --------------------------------------------------------
    def _start_measurement(self, dlg, target, vars_, devices, rate_var, fmt_var):
        uuids = [uid for uid, v in vars_.items() if v.get()]
        if not uuids:
            messagebox.showwarning("Warning:", "Please choose at least one device.")
            return
        dlg.destroy()

        # plot reset settings 
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
            args=(target, uuids, rate_var.get(), fmt_var.get()),
            daemon=True)
        self.ws_thread.start()

    # --------------------------------------------------------
    # Background Thread – WebSocket-Client (asyncio)
    # connects to websocket 
    # sends the uuid + options to the websocket 
    # receives the message from the websocket 
    # --------------------------------------------------------
    def _ws_worker(self, target: str, uuids: List[str], rate: int, fmt: str):
        async def _runner():
            uri = f"ws://{target}/ws"
            async with connect(uri) as ws:
                cmd = " ".join(uuids + [str(rate), fmt])
                await ws.send(cmd)
                while not self.stop_event.is_set():
                    msg = await ws.recv()
                    if fmt == "json":
                        obj = json.loads(msg)
                        ts = obj["timestamp"]
                        values = obj["data"][0]
                    else:  # csv
                        parts = msg.split(",")
                        ts = float(parts[0])
                        values = list(map(float, parts[1:]))
                    self.queue.put((ts, values))
        try:
            asyncio.run(_runner())
        except Exception as e:
            self.queue.put(("__error__", e))

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
            for dev_uuid, val in zip(self.lines.keys(), values):
                self.data_buffer[dev_uuid].append((ts, val))
                # only save the last 1000 datapoints 
                if len(self.data_buffer[dev_uuid]) > 1000:
                    self.data_buffer[dev_uuid] = self.data_buffer[dev_uuid][-1000:]
                xs, ys = zip(*self.data_buffer[dev_uuid])
                self.lines[dev_uuid].set_data(xs, ys)

        # Scale axis 
        if any(self.data_buffer[dev] for dev in self.data_buffer):
            all_x = [x for buf in self.data_buffer.values() for x, _ in buf]
            all_y = [y for buf in self.data_buffer.values() for _, y in buf]
            self.ax.set_xlim(min(all_x), max(all_x))
            ymin, ymax = min(all_y), max(all_y)
            if ymin == ymax:
                ymax += 1e-3
            self.ax.set_ylim(ymin, ymax)
        self.canvas.draw_idle()

    # --------------------------------------------------------
    # Clean up when closed 
    # --------------------------------------------------------
    def _on_close(self):
        self.stop_event.set()
        self.destroy()


# ------------------------------------------------------------
# start point 
# ------------------------------------------------------------
if __name__ == "__main__":
    matplotlib.use("TkAgg")   
    app = DevDataClient()
    app.mainloop()
