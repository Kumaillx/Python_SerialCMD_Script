import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk


class MainApplicationWindow(ttk.Frame):
    def __init__(self, parent, serial_manager):
        super().__init__(parent)
        self.parent = parent
        self.serial_mgr = serial_manager
        self.parent.title("Embedded Serial Command Center")
        self.parent.geometry("850x680")
        self.parent.minsize(720, 520)

        # State tracking flag to prevent feedback loops when syncing Slider <-> Entry
        self._updating_pwm = False

        self._build_ui()
        self._poll_incoming_messages()

    def _build_ui(self):
        # 1. Serial Connection Section
        conn_frame = ttk.LabelFrame(self.parent, text="Serial Connection", padding=10)
        conn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(conn_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5)
        self.port_cb = ttk.Combobox(conn_frame, width=15)
        self.port_cb.grid(row=0, column=1, padx=5, pady=5)
        self.refresh_ports()

        ttk.Button(conn_frame, text="⟳", width=3, command=self.refresh_ports).grid(
            row=0, column=2, padx=2
        )

        ttk.Label(conn_frame, text="Baud:").grid(row=0, column=3, padx=5, pady=5)
        self.baud_cb = ttk.Combobox(
            conn_frame,
            values=["9600", "19200", "38400", "57600", "115200"],
            width=10,
        )
        self.baud_cb.set("115200")
        self.baud_cb.grid(row=0, column=4, padx=5, pady=5)

        self.btn_connect = ttk.Button(
            conn_frame, text="Connect", command=self._toggle_connection
        )
        self.btn_connect.grid(row=0, column=5, padx=10, pady=5)

        # 2. Hardware Controls Section
        ctrl_frame = ttk.LabelFrame(self.parent, text="Hardware Controls", padding=10)
        ctrl_frame.pack(fill="x", padx=10, pady=5)

        # Commands: Read ABC & Read Coder
        ttk.Button(
            ctrl_frame, text="Read ABC", command=lambda: self._send_command("READ ABC")
        ).grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        ttk.Button(
            ctrl_frame, text="Read Coder", command=lambda: self._send_command("CODER READ")
        ).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Commands: GPIO Control
        ttk.Label(ctrl_frame, text="GPIO Pin:").grid(
            row=1, column=0, padx=5, pady=5, sticky="e"
        )
        self.gpio_pin_entry = ttk.Entry(ctrl_frame, width=6)
        self.gpio_pin_entry.insert(0, "13")
        self.gpio_pin_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Button(ctrl_frame, text="Set GPIO 1", command=lambda: self._set_gpio(1)).grid(
            row=1, column=2, padx=5, pady=5
        )
        ttk.Button(ctrl_frame, text="Set GPIO 0", command=lambda: self._set_gpio(0)).grid(
            row=1, column=3, padx=5, pady=5
        )

        # Commands: PWM Slider + Numerical Entry (Synced)
        ttk.Label(ctrl_frame, text="PWM (0-255):").grid(
            row=2, column=0, padx=5, pady=5, sticky="e"
        )

        # Initialize String Variable first to prevent callback AttributeError
        self.pwm_var = tk.StringVar(value="0")

        self.pwm_slider = ttk.Scale(
            ctrl_frame, from_=0, to=255, orient="horizontal", command=self._on_slider_moved
        )
        self.pwm_slider.set(0)
        self.pwm_slider.grid(row=2, column=1, columnspan=2, sticky="ew", padx=5)

        self.pwm_entry = ttk.Entry(ctrl_frame, textvariable=self.pwm_var, width=6)
        self.pwm_entry.grid(row=2, column=3, padx=5, pady=5)
        self.pwm_entry.bind("<KeyRelease>", self._on_entry_changed)
        self.pwm_entry.bind("<Return>", lambda e: self._send_pwm())

        ttk.Button(ctrl_frame, text="Send PWM", command=self._send_pwm).grid(
            row=2, column=4, padx=5, pady=5
        )

        # 3. Direct Command Line Terminal Bar
        cmd_frame = ttk.LabelFrame(self.parent, text="Direct Command Line", padding=10)
        cmd_frame.pack(fill="x", padx=10, pady=5)

        self.cmd_entry = ttk.Entry(cmd_frame)
        self.cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.cmd_entry.bind("<Return>", lambda e: self._send_cli())

        ttk.Button(cmd_frame, text="Send", command=self._send_cli).pack(side="right")

        # 4. Device Log Output Terminal
        log_frame = ttk.LabelFrame(self.parent, text="Incoming Device Logs", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_area = scrolledtext.ScrolledText(
            log_frame, bg="#1E1E1E", fg="#00FF66", font=("Consolas", 10), state="disabled"
        )
        self.log_area.pack(fill="both", expand=True)

        ttk.Button(log_frame, text="Clear Log", command=self._clear_logs).pack(
            anchor="e", pady=3
        )

    # --- PWM Bidirectional Sync ---
    def _on_slider_moved(self, value):
        if self._updating_pwm:
            return
        self._updating_pwm = True
        val_int = int(float(value))
        self.pwm_var.set(str(val_int))
        self._updating_pwm = False

    def _on_entry_changed(self, event):
        if self._updating_pwm:
            return
        text = self.pwm_var.get().strip()
        if text.isdigit():
            val = int(text)
            if 0 <= val <= 255:
                self._updating_pwm = True
                self.pwm_slider.set(val)
                self._updating_pwm = False

    # --- Connection Controls ---
    def refresh_ports(self):
        ports = self.serial_mgr.get_available_ports()
        self.port_cb["values"] = ports
        if ports:
            self.port_cb.current(0)

    def _toggle_connection(self):
        if self.serial_mgr.is_connected():
            self.serial_mgr.disconnect()
            self.btn_connect.config(text="Connect")
            self._log_terminal("[SYSTEM] Disconnected.")
        else:
            port = self.port_cb.get()
            baud = self.baud_cb.get()
            if not port:
                messagebox.showerror("Error", "No serial port selected!")
                return
            try:
                self.serial_mgr.connect(port, int(baud))
                self.btn_connect.config(text="Disconnect")
                self._log_terminal(f"[SYSTEM] Connected to {port} @ {baud} bps")
            except Exception as e:
                messagebox.showerror("Connection Error", str(e))

    # --- Command Actions ---
    def _send_command(self, cmd: str):
        try:
            self.serial_mgr.send(cmd)
            self._log_terminal(f"[TX] > {cmd}")
        except ConnectionError:
            messagebox.showwarning("Warning", "Serial port is not connected.")
        except Exception as e:
            messagebox.showerror("Transmission Error", str(e))

    def _send_cli(self):
        cmd = self.cmd_entry.get().strip()
        if cmd:
            self._send_command(cmd)
            self.cmd_entry.delete(0, tk.END)

    def _send_pwm(self):
        raw_val = self.pwm_var.get().strip()
        if not raw_val.isdigit() or not (0 <= int(raw_val) <= 255):
            messagebox.showerror("Value Error", "PWM value must be an integer between 0 and 255.")
            return
        self._send_command(f"PWM {raw_val}")

    def _set_gpio(self, state: int):
        pin = self.gpio_pin_entry.get().strip()
        if not pin.isdigit():
            messagebox.showerror("Input Error", "Please specify a numeric GPIO pin.")
            return
        self._send_command(f"GPIO {pin} {state}")

    # --- Log Management ---
    def _poll_incoming_messages(self):
        while True:
            msg = self.serial_mgr.read_message()
            if msg is None:
                break
            self._log_terminal(f"[RX] {msg}")
        self.parent.after(50, self._poll_incoming_messages)

    def _log_terminal(self, text: str):
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, text + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state="disabled")

    def _clear_logs(self):
        self.log_area.config(state="normal")
        self.log_area.delete("1.0", tk.END)
        self.log_area.config(state="disabled")