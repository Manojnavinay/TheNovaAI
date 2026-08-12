import threading
import queue

import customtkinter as ctk
from PIL import Image, ImageDraw
import pystray

import assistant_core as core

event_queue: "queue.Queue" = queue.Queue()

STATE_COLORS = {
    "idle": "#4a4a4a",
    "listening_wake": "#2b6cb0",
    "listening_command": "#2f855a",
    "processing": "#b7791f",
    "speaking": "#6b46c1",
    "paused": "#742a2a",
}


class GuiCallbacks(core.Callbacks):
    def log(self, speaker, text):
        event_queue.put(("log", speaker, text))

    def status(self, text):
        event_queue.put(("status", text))

    def state(self, state):
        event_queue.put(("state", state))

    def level(self, value):
        event_queue.put(("level", value))


def make_tray_image(color="#4a4a4a"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill=color)
    return img


class NovaApp:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("Nova")
        self.root.geometry("420x560")
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        self.status_var = ctk.StringVar(value="Starting...")
        status_label = ctk.CTkLabel(
            self.root, textvariable=self.status_var, font=("Segoe UI", 14, "bold")
        )
        status_label.pack(pady=(12, 4))

        self.chat_box = ctk.CTkTextbox(self.root, width=380, height=440, wrap="word")
        self.chat_box.pack(padx=12, pady=8, fill="both", expand=True)
        self.chat_box.configure(state="disabled")

        button_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        button_frame.pack(pady=(0, 12))

        self.pause_btn = ctk.CTkButton(
            button_frame, text="Pause", width=100, command=self.toggle_pause
        )
        self.pause_btn.grid(row=0, column=0, padx=6)

        quit_btn = ctk.CTkButton(
            button_frame,
            text="Quit Nova",
            width=100,
            fg_color="#a33",
            hover_color="#822",
            command=self.quit_app,
        )
        quit_btn.grid(row=0, column=1, padx=6)

        self.stop_event = threading.Event()
        self.pause_event = threading.Event()

        core.set_callbacks(GuiCallbacks())

        self.assistant_thread = threading.Thread(
            target=core.run, args=(self.stop_event, self.pause_event), daemon=True
        )
        self.assistant_thread.start()

        self.tray_icon = pystray.Icon(
            "nova",
            make_tray_image(),
            "Nova",
            menu=pystray.Menu(
                pystray.MenuItem("Open Nova", self.show_window, default=True),
                pystray.MenuItem(
                    "Pause",
                    self.tray_toggle_pause,
                    checked=lambda item: self.pause_event.is_set(),
                ),
                pystray.MenuItem("Quit", self.quit_app),
            ),
        )
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

        self.root.after(100, self.poll_queue)
        self.root.withdraw()  # start hidden, tray-only

    def poll_queue(self):
        try:
            while True:
                item = event_queue.get_nowait()
                kind = item[0]

                if kind == "log":
                    _, speaker, text = item
                    self.append_chat(speaker, text)

                elif kind == "status":
                    self.status_var.set(item[1])

                elif kind == "state":
                    state = item[1]
                    self.status_var.set(state.replace("_", " ").title())
                    self.tray_icon.icon = make_tray_image(
                        STATE_COLORS.get(state, "#4a4a4a")
                    )
        except queue.Empty:
            pass

        self.root.after(100, self.poll_queue)

    def append_chat(self, speaker, text):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", f"{speaker}: {text}\n\n")
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def show_window(self, icon=None, item=None):
        self.root.after(0, self.root.deiconify)

    def hide_window(self):
        self.root.withdraw()

    def toggle_pause(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_btn.configure(text="Pause")
        else:
            self.pause_event.set()
            self.pause_btn.configure(text="Resume")

    def tray_toggle_pause(self, icon=None, item=None):
        self.root.after(0, self.toggle_pause)

    def quit_app(self, icon=None, item=None):
        self.stop_event.set()
        self.pause_event.clear()
        self.tray_icon.stop()
        self.root.after(0, self.root.quit)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = NovaApp()
    app.run()
