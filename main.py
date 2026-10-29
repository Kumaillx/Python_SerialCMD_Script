import tkinter as tk
from gui import MainApplicationWindow
from serial_manager import SerialManager


def main():
    root = tk.Tk()

    # Instantiate backend communication layer
    serial_mgr = SerialManager()

    # Mount GUI layer
    app = MainApplicationWindow(root, serial_mgr)

    # Ensure clean serial closure on window close
    def on_closing():
        serial_mgr.disconnect()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()