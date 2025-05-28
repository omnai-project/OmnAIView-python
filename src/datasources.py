"""
datasources.py
==============

All protocol-specific logic lives here.  Add further data sources by
sub-classing `DataSourceStrategy` and decorating the class with
`@register`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Tuple

import json
import random
import requests

# ----------------------------------------------------------------------
# Domain object
# ----------------------------------------------------------------------
@dataclass
class Device:
    uuid: str
    color: str          # hex "#rrggbb"


# ----------------------------------------------------------------------
# Strategy base class
# ----------------------------------------------------------------------
class DataSourceStrategy(ABC):
    """Common interface every data source must fulfil."""

    name: str                          # appears in the GUI drop-down
    formats: List[str]                 # allowed data formats (json/csv …)

    # --- REST ----------------------------------------------------------
    @abstractmethod
    def fetch_devices(self, host_port: str) -> List[Device]:
        ...

    # --- WebSocket handshake ------------------------------------------
    @abstractmethod
    def build_ws_uri(self, host_port: str) -> str:
        ...

    @abstractmethod
    def build_subscribe_cmd(
        self, uuids: List[str], rate: int, fmt: str
    ) -> str | bytes:
        """Return the exact payload that has to be sent after the WS is open.
        May be text (str) or binary (bytes)."""

    # --- WebSocket frame parsing --------------------------------------
    @abstractmethod
    def parse_ws_msg(
        self, raw: str | bytes
    ) -> Tuple[float, Dict[str, float]]:
        """Convert a raw frame into
           (timestamp, {uuid: value, …})."""
        ...

    # helper for concrete strategies
    def _to_hex(self, maybe_rgb):
        if isinstance(maybe_rgb, dict):
            return f"#{maybe_rgb['r']:02x}{maybe_rgb['g']:02x}{maybe_rgb['b']:02x}"
        return maybe_rgb
    
    def server_sends_initial_msg(self) -> bool:
        """Return True if the server always sends *one* informational frame
        immediately after the WebSocket is opened and the client must wait
        (and optionally inspect it) before sending its subscribe command."""
        return False            # default: talk first

    def handle_initial_msg(self, raw: str | bytes) -> None:
        """Called with that very first frame when
        server_sends_initial_msg() is True.
        Default behaviour: just ignore it."""
        return

# ----------------------------------------------------------------------
# Strategy registry  (simple plugin container)
# ----------------------------------------------------------------------
_registry: Dict[str, type[DataSourceStrategy]] = {}


def register(cls: type[DataSourceStrategy]):
    """Class decorator -> auto-add to registry."""
    _registry[cls.name] = cls
    return cls


def available_sources() -> List[str]:
    return list(_registry.keys())


def get_strategy(name: str) -> DataSourceStrategy:
    return _registry[name]()



# ======================================================================
#  Concrete Strategies
# ======================================================================

# ----------------------------------------------------------------------
# 1) DevDataServer  (existing backend)
# ----------------------------------------------------------------------
@register
class DevDataServerStrategy(DataSourceStrategy):
    name = "DevDataServer"
    formats = ["json", "csv"]

    # ---------- REST ----------
    def fetch_devices(self, host_port: str) -> List[Device]:
        url = f"http://{host_port}/v1/get_devices"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        devices = []
        for ds in resp.json()["datastreams"]:
            devices.append(
                Device(
                    uuid=ds["UUID"],
                    color=self._to_hex(ds["color"]),
                )
            )
        return devices

    # ---------- WS Handshake ----------
    def build_ws_uri(self, host_port: str) -> str:
        return f"ws://{host_port}/v1/subscribe_ws"

    def build_subscribe_cmd(self, uuids, rate, fmt):
        # Remember order for CSV parsing
        self._uuids = uuids
        return " ".join(uuids + [str(rate), fmt])

    # ---------- WS Frame parsing ----------
    def parse_ws_msg(self, raw):
        # Server always sends UTF-8 text frames
        if isinstance(raw, bytes):
            raw = raw.decode()

        # ---------- JSON ----------
        if raw.startswith("{"):
            obj = json.loads(raw)
            ts_UNIX = obj["timestamp"]
            values = obj["data"][0]          # list in *subscription* order
        else:
             # ---------- CSV ----------
            parts = raw.split(",")
            ts = float(parts[0])
            values = list(map(float, parts[1:]))
        ts = int(ts_UNIX * 1000) # transform UNIX timestamps into correct integer values
        return ts, dict(zip(self._uuids, values))


# ----------------------------------------------------------------------
# 2) OmnAIScope DataServer  (new backend)
# ----------------------------------------------------------------------

@register
class OmnAIScopeStrategy(DataSourceStrategy):
    """
    Implements the interface exactly as described in the AsyncAPI file with OmnAIScope-DataServer v0.4.0
      * REST  GET /UUID
      * WS    ws://host/ws
      * SUB   identical text command like DevDataServer
      * DATA  JSON  {"data":[{"timestamp":..., "value":[...] }], "datastreams":[...]}
             CSV   <unix_ts>,v1,v2,…
             binary (protobuf)  -- not parsed here
    """

    name = "OmnAIScope DataServer"
    formats = ["json", "csv", "binary"]

    # ---------- REST ----------
    def fetch_devices(self, host_port: str) -> List[Device]:
        url = f"http://{host_port}/UUID"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        body = resp.json()

        ds_list = body.get("devices") or []
        color_list = body.get("colors") or []

        devices: List[Device] = []
        for idx, ds in enumerate(ds_list):
            uid = ds.get("UUID") or ds.get("uuid")
            # Get colors 
            if idx < len(color_list):
                col = color_list[idx].get("color", {})
                color_hex = f"#{col.get('r', 0):02x}{col.get('g', 0):02x}{col.get('b', 0):02x}"
            else:
                color_hex = f"#{random.randint(0, 0xFFFFFF):06x}"
            devices.append(Device(uuid=uid, color=color_hex))
        return devices

    # ---------- WS handshake ----------
    def build_ws_uri(self, host_port: str) -> str:
        return f"ws://{host_port}/ws"

    def build_subscribe_cmd(self, uuids, rate, fmt):
        self._uuids = uuids
        return " ".join(uuids + [str(rate), fmt])

    # ---------- WS-Frame parsing ----------
    def parse_ws_msg(self, raw: str | bytes):
        # → JSON ---------------------------------------------------------
        if (isinstance(raw, bytes) and raw and raw[0] in b"{[") or (
            isinstance(raw, str) and raw and raw[0] in "{["
        ):
            if isinstance(raw, bytes):
                raw = raw.decode()
            obj = json.loads(raw)

            # JSON-Frame
            if "data" in obj and "devices" in obj:
                sample = obj["data"][0]
                ts = sample["timestamp"]
                values = sample["value"]
                ds_order = obj["devices"]
                return ts, dict(zip(ds_order, values))

        # → CSV ----------------------------------------------------------
        if isinstance(raw, bytes):
            raw = raw.decode()
        if "," in raw:
            parts = raw.split(",")
            ts = float(parts[0])
            values = list(map(float, parts[1:]))
            return ts, dict(zip(self._uuids, values))

        # → Binary / unknown  (skip)
        raise ValueError("Unsupported or malformed frame received from OmnAIScope.")
    
    # ---------- WS “server-talks-first” ----------
    def server_sends_initial_msg(self) -> bool:
        return True             # <- OmnAIScope does send one frame first

    def handle_initial_msg(self, raw):
        # We don’t care what it is for now – but you could log or parse it.
        if isinstance(raw, bytes):
            raw = raw.decode(errors="ignore")
        print(f"[OmnAIScope] initial server frame: {raw!r}")