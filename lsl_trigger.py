"""LSL Latched Trigger - ensures markers are captured by LabRecorder

Adapted from vMMR experiment
Solves the issue where transient markers are lost between LabRecorder samples.
"""

import threading
from pylsl import StreamInfo, StreamOutlet, local_clock


class LSLTrigger:
    """Latched marker outlet for robust marker delivery.

    Instead of pushing a single sample (transient), this keeps the marker
    value active for hold_duration (default 100ms), ensuring LabRecorder
    captures it even if sampling is asynchronous.

    Offline analysis detects leading edges (0->code) to recover event timing.
    """

    def __init__(self, enabled=False, stream_name="pps_markers",
                 source_id="pps_exp", keepalive_hz=1200,
                 nominal_srate=1200, hold_duration=0.100):
        self.enabled = enabled
        self.outlet = None
        self.keepalive_hz = keepalive_hz
        self.nominal_srate = nominal_srate
        self.hold_duration = float(hold_duration)
        self._lock = threading.Lock()
        self._current_value = 0
        self._expiry = None
        self._stop_event = threading.Event()
        self._keepalive_thread = None

        if not self.enabled:
            return

        self.keepalive_hz = float(keepalive_hz)
        self.nominal_srate = float(nominal_srate)

        info = StreamInfo(
            name=stream_name,
            type="Markers",
            channel_count=1,
            nominal_srate=self.nominal_srate,
            channel_format="int32",
            source_id=source_id
        )
        self.outlet = StreamOutlet(info)
        self._start_keepalive()

    def _start_keepalive(self):
        self._stop_event.clear()
        self._keepalive_thread = threading.Thread(
            target=self._keepalive, daemon=True
        )
        self._keepalive_thread.start()

    def _keepalive(self):
        interval = 1.0 / self.keepalive_hz
        while not self._stop_event.is_set():
            with self._lock:
                if self._expiry is not None and local_clock() >= self._expiry:
                    self._current_value = 0
                    self._expiry = None
                self.outlet.push_sample([self._current_value], pushthrough=True)
            self._stop_event.wait(interval)

    def set(self, code):
        """Send marker and latch it for hold_duration"""
        if self.outlet is None:
            return None
        ts = local_clock()
        with self._lock:
            self._current_value = int(code)
            self._expiry = ts + self.hold_duration
            self.outlet.push_sample([int(code)], pushthrough=True)
        return ts

    def clear(self):
        """Immediately clear marker (returns to 0)"""
        if self.outlet is None:
            return
        with self._lock:
            self._current_value = 0
            self._expiry = None
            self.outlet.push_sample([0], pushthrough=True)

    def stop(self):
        """Stop keepalive thread"""
        self._stop_event.set()
        if self._keepalive_thread is not None:
            self._keepalive_thread.join(timeout=1.0)
        self._keepalive_thread = None
