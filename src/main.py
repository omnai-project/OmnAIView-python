#!/usr/bin/env python3
"""
DevDataClient mit:
- Popup beim Fenster-X (Tkinter)
- Terminal-Abfrage bei Ctrl+C
"""

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

class DevDataClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OmnAIView DevDataClient")
        # X-Button -> Popup
        self.protocol("WM_DELETE_WINDOW", self._confirm_close)

        # Toolbar
        bar = ttk.Frame(self)
        bar.pack(side="top", fill="x")
        ttk.Button(bar, text="Connect to Websocket",
                   command=self._connect_dialog).pack(side="left", padx=4, pady=4)

        # Plot area
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Value")
        self.lines: Dict[str, matplotlib.lines.Line2D] = {}
        self.data_buffer: Dict[str, List[Tuple[float, float]]] = {}

        # Thread communication
        self.ws_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.queue: queue.Queue = queue.Queue()

        # Strategy and state
        self.strategy = None
        self.host_port = ""
        self.active_uuids: List[str] = []

        # Animation
        self.ani = animation.FuncAnimation(
            self.fig,
            self._update_plot,
            interval=100,
            blit=False,
            cache_frame_data=False,
        )

    def _confirm_close(self):
        if messagebox.askokcancel("Exit", "Do you really want to exit?"):
            self._cleanup_and_close()

    def _cleanup_and_close(self):
        # Stop websocket thread
        self.stop_event.set()
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=1)
        # End mainloop and close
        self.quit()
        self.destroy()

    def _connect_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Connect")
        ttk.Label(dlg, text="WebSocket-Server (ip:port):").grid(row=0, column=0, padx=6, pady=4, sticky="e")
        host_var = tk.StringVar(value="localhost:8080")
        ttk.Entry(dlg, textvariable=host_var, width=20).grid(row=0, column=1, pady=4)

        ttk.Label(dlg, text="Data source:").grid(row=1, column=0, padx=6, pady=4, sticky="e")
        src_var = tk.StringVar(value=available_sources()[0])
        ttk.Combobox(dlg, textvariable=src_var,
                     values=available_sources(), state="readonly", width=18).grid(row=1, column=1, pady=4)

        ttk.Button(dlg, text="Connect",
                   command=lambda: self._on_connect_submit(dlg, host_var.get().strip(), src_var.get())
        ).grid(row=2, column=0, columnspan=2, pady=8)

    def _on_connect_submit(self, dlg, host_port, source_name):
        dlg.destroy()
        self.strategy = get_strategy(source_name)
        self.host_port = host_port
        try:
            devices = self.strategy.fetch_devices(host_port)
        except Exception as e:
            messagebox.showerror("Error", f"Device list cannot be loaded:\n{e}")
            return
        self._device_dialog(devices)

    def _device_dialog(self, devices: List[Device]):
        dlg = tk.Toplevel(self)
        dlg.title("Choose devices")
        ttk.Label(dlg, text="Devices:").pack(anchor="w", padx=8, pady=4)
        vars_: Dict[str, tk.BooleanVar] = {}
        for dev in devices:
            v = tk.BooleanVar()
            ttk.Checkbutton(dlg, text=dev.uuid, variable=v).pack(anchor="w", padx=20)
            vars_[dev.uuid] = v
        frm = ttk.Frame(dlg)
        frm.pack(fill="x", pady=6)
        ttk.Label(frm, text="Samplerate (Hz):").grid(row=0, column=0, sticky="e")
        rate_var = tk.IntVar(value=60)
        ttk.Entry(frm, textvariable=rate_var, width=8).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(frm, text="Format:").grid(row=1, column=0, sticky="e")
        fmt_var = tk.StringVar(value=self.strategy.formats[0])
        ttk.Combobox(frm, textvariable=fmt_var,
                     values=self.strategy.formats, state="readonly", width=7).grid(row=1, column=1, sticky="w", padx=4)
        ttk.Button(dlg, text="Start measurement",
                   command=partial(self._start_measurement, dlg, vars_, devices, rate_var, fmt_var)
        ).pack(pady=8)

    def _start_measurement(self, dlg, vars_, devices, rate_var, fmt_var):
        uuids = [uid for uid, v in vars_.items() if v.get()]
        if not uuids:
            messagebox.showwarning("Warning", "Please choose at least one device.")
            return
        dlg.destroy()
        self.active_uuids = uuids
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
        self.stop_event.clear()
        self.ws_thread = threading.Thread(
            target=self._ws_worker,
            args=(self.strategy.build_ws_uri(self.host_port),
                  self.strategy.build_subscribe_cmd(uuids, rate_var.get(), fmt_var.get())),
            daemon=True)
        self.ws_thread.start()

    def _ws_worker(self, uri: str, subscribe_cmd: str | bytes):
        async def runner():
            async with connect(uri) as ws:
                if self.strategy.server_sends_initial_msg():
                    frame = await ws.recv()
                    self.strategy.handle_initial_msg(frame)
                await ws.send(subscribe_cmd)
                try:
                    while not self.stop_event.is_set():
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        except asyncio.TimeoutError:
                            continue
                        ts, val_dict = self.strategy.parse_ws_msg(raw)
                        values = [val_dict.get(uid, float('nan')) for uid in self.active_uuids]
                        self.queue.put((ts, values))
                finally:
                    await ws.close()
        try:
            asyncio.run(runner())
        except Exception as e:
            self.queue.put(("__error__", e))

    def _update_plot(self, _):
        while not self.queue.empty():
            ts, values = self.queue.get_nowait()
            if ts == "__error__":
                messagebox.showerror("WebSocket-Error", str(values))
                self.stop_event.set()
                return
            for uid, val in zip(self.active_uuids, values):
                buffer = self.data_buffer[uid]
                buffer.append((ts, val))
                if len(buffer) > 1000:
                    buffer[:] = buffer[-1000:]
                xs, ys = zip(*buffer)
                self.lines[uid].set_data(xs, ys)
        if any(self.data_buffer[uid] for uid in self.active_uuids):
            self.ax.relim()
            self.ax.autoscale_view()
        self.canvas.draw_idle()

if __name__ == "__main__":
    matplotlib.use("TkAgg")
    app = DevDataClient()

    def sigint_handler(sig, frame):
        # Terminal prompt on Ctrl+C
        try:
            ans = input("Do you really want to exit? [y/N] ").strip().lower()
        except EOFError:
            ans = ''
        if ans in ('y', 'yes'):
            app._cleanup_and_close()
            sys.exit(0)
        else:
            print("Continuing...")

    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigint_handler)

    app.mainloop()
    sys.exit(0)
