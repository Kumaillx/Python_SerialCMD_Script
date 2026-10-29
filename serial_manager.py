import queue
import threading
import serial
import serial.tools.list_ports


class SerialManager:
    def __init__(self):
        self.ser = None
        self.rx_thread = None
        self.is_running = False
        self.rx_queue = queue.Queue()

    @staticmethod
    def get_available_ports():
        """Returns a list of detected serial port names."""
        return [p.device for p in serial.tools.list_ports.comports()]

    def is_connected(self) -> bool:
        return bool(self.ser and self.ser.is_open)

    def connect(self, port: str, baudrate: int = 115200):
        if self.is_connected():
            self.disconnect()

        self.ser = serial.Serial(port, baudrate, timeout=1)
        self.is_running = True

        self.rx_thread = threading.Thread(target=self._read_worker, daemon=True)
        self.rx_thread.start()

    def disconnect(self):
        self.is_running = False
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None

    def _read_worker(self):
        while self.is_running and self.ser and self.ser.is_open:
            try:
                raw_bytes = self.ser.readline()
                if raw_bytes:
                    line = raw_bytes.decode("utf-8", errors="replace").strip()
                    if line:
                        self.rx_queue.put(line)
            except Exception:
                break

    def send(self, cmd_text: str):
        """Sends an ASCII command terminated with newline."""
        if not self.is_connected():
            raise ConnectionError("Serial port is not connected.")

        cmd_payload = f"{cmd_text.strip()}\n".encode("utf-8")
        self.ser.write(cmd_payload)

    def read_message(self):
        """Pulls a single message from the queue if available, else returns None."""
        try:
            return self.rx_queue.get_nowait()
        except queue.Empty:
            return None