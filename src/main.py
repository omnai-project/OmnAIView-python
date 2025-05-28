#!/usr/bin/env python3
"""
Simple Tk-/matplotlib front-end that can talk to **multiple back-ends**
via a *Strategy Pattern*.
Start: python main.py [--logging]
Includes:
- graceful shutdown on window close (X click) and Ctrl+C
- correct WS URL for DevDataServer
- robust plotting with numeric conversion
- optional terminal logging of stream values with --logging flag
"""

import argparse
import asyncio
import queue
import threading
import signal
import sys
from functools import partial
from typing import Dict, List, Tuple

import matplotlib
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from websockets import connect

from datasources import Device, available_sources, get_strategy

# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--logging', action='store_true', help='Enable terminal logging of stream values')
args = parser.parse_args()
ENABLE_LOG = args.logging if 'args' in globals() else False

class DevDataClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OmnAIView DevDataClient")
        self.protocol("WM_DELETE_WINDOW", self._confirm_close)

        # Toolbar
        bar = ttk.Frame(self)
        bar.pack(side="top", fill="x")
        ttk.Button(bar, text="Connect to WebSocket", command=self._connect_dialog).pack(side="left", padx=4, pady=4)

        # Plot area
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Value")
        self.lines: Dict[str, plt.Line2D] = {}
        self.data_buffer: Dict[str, List[Tuple[float, float]]] = {}

        # Threading and communication
        self.ws_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.queue: queue.Queue = queue.Queue()

        # Strategy and state
        self.strategy = None
        self.host_port = ""
        self.active_uuids: List[str] = []

        # Animation: explicit save_count to suppress warning
        self.ani = animation.FuncAnimation(
            self.fig,
            self._update_plot,
            interval=100,
            cache_frame_data=False,
            save_count=50
        )

    def _confirm_close(self):
        if messagebox.askokcancel("Exit", "Do you really want to exit? "):
            self._cleanup_and_close()

    def _cleanup_and_close(self):
        self.stop_event.set()
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=1)
        self.quit()
        self.destroy()

    def _connect_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Connect")
        ttk.Label(dlg, text="Server (host:port):").grid(row=0, column=0, padx=6, pady=4, sticky="e")
        host_var = tk.StringVar(value="localhost:8080")
        ttk.Entry(dlg, textvariable=host_var).grid(row=0, column=1, pady=4)

        ttk.Label(dlg, text="Data source:").grid(row=1, column=0, padx=6, pady=4, sticky="e")
        src_var = tk.StringVar(value=available_sources()[0])
        ttk.Combobox(dlg, textvariable=src_var, values=available_sources(), state="readonly").grid(row=1, column=1)

        ttk.Button(dlg, text="Connect", command=lambda: self._on_connect_submit(dlg, host_var.get(), src_var.get())).grid(row=2, column=0, columnspan=2, pady=8)

    def _on_connect_submit(self, dlg, host_port, source_name):
        dlg.destroy()
        self.host_port = host_port
        self.strategy = get_strategy(source_name)
        try:
            devices = self.strategy.fetch_devices(host_port)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot load devices:\n{e}")
            return
        self._device_dialog(devices)

    def _device_dialog(self, devices: List[Device]):
        dlg = tk.Toplevel(self)
        dlg.title("Choose devices")
        vars_: Dict[str, tk.BooleanVar] = {}
        ttk.Label(dlg, text="Devices:").pack(anchor="w", padx=8, pady=4)
        for dev in devices:
            v = tk.BooleanVar()
            ttk.Checkbutton(dlg, text=dev.uuid, variable=v).pack(anchor="w", padx=20)
            vars_[dev.uuid] = v

        frm = ttk.Frame(dlg)
        frm.pack(fill="x", pady=6)
        ttk.Label(frm, text="Sample rate (Hz):").grid(row=0, column=0, sticky="e")
        rate_var = tk.IntVar(value=60)
        ttk.Entry(frm, textvariable=rate_var, width=6).grid(row=0, column=1, sticky="w", padx=4)

        ttk.Label(frm, text="Format:").grid(row=1, column=0, sticky="e")
        fmt_var = tk.StringVar(value=self.strategy.formats[0])
        ttk.Combobox(frm, textvariable=fmt_var, values=self.strategy.formats, state="readonly", width=6).grid(row=1, column=1, sticky="w", padx=4)

        ttk.Button(dlg, text="Start", command=partial(self._start, dlg, vars_, rate_var, fmt_var)).pack(pady=8)

    def _start(self, dlg, vars_, rate_var, fmt_var):
        uuids = [u for u, v in vars_.items() if v.get()]
        if not uuids:
            messagebox.showwarning("Warning", "Select at least one device")
            return
        dlg.destroy()
        self.active_uuids = uuids
        self.ax.clear()
        self.lines.clear()
        self.data_buffer.clear()
        for uid in uuids:
            (line,) = self.ax.plot([], [], label=uid)
            self.lines[uid] = line
            self.data_buffer[uid] = []
        self.ax.legend()

        # Correct WS URL
        if self.strategy.name == 'DevDataServer':
            uri = f"ws://{self.host_port}/v1/subscribe_ws"
        else:
            uri = self.strategy.build_ws_uri(self.host_port)
        cmd = self.strategy.build_subscribe_cmd(uuids, rate_var.get(), fmt_var.get())

        self.stop_event.clear()
        self.ws_thread = threading.Thread(target=self._ws_worker, args=(uri, cmd), daemon=True)
        self.ws_thread.start()

    def _ws_worker(self, uri: str, cmd: str):
        async def runner():
            async with connect(uri) as ws:
                await ws.send(cmd)
                while not self.stop_event.is_set():
                    raw = await ws.recv()
                    ts, val_dict = self.strategy.parse_ws_msg(raw)
                    values = [val_dict.get(uid, float('nan')) for uid in self.active_uuids]
                    try:
                        ts = float(ts)
                        values = [float(v) for v in values]
                    except Exception:
                        continue
                    # Conditional terminal logging
                    if ENABLE_LOG:
                        print(f"Timestamp: {ts}, Values: {values}")
                    self.queue.put((ts, values))
        try:
            asyncio.run(runner())
        except Exception as e:
            self.queue.put(("__error__", e))

    def _update_plot(self, _):
        while not self.queue.empty():
            ts, vals = self.queue.get_nowait()
            if ts == "__error__":
                messagebox.showerror("Error", str(vals))
                self.stop_event.set()
                return
            for uid, val in zip(self.active_uuids, vals):
                buf = self.data_buffer[uid]
                buf.append((ts, val))
                if len(buf) > 1000:
                    buf[:] = buf[-1000:]
                xs, ys = zip(*buf)
                self.lines[uid].set_data(xs, ys)
        if any(self.data_buffer.values()):
            self.ax.relim()
            self.ax.autoscale_view()
        self.canvas.draw_idle()

if __name__ == '__main__':
    matplotlib.use('TkAgg')
    app = DevDataClient()
    handler = lambda sig, frame: app._confirm_close()
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    app.mainloop()
    sys.exit(0)
