import threading
import queue

import customtkinter as ctk
from PIL import Image, ImageDraw
import pystray

import assistant_core as core

event_queue: "queue.Queue" = queue.Queue()

import json

THEME_PATH = core.BASE_DIR / "theme.json"

DEFAULT_THEME = {
    "appearance_mode": "dark",
    "color_theme": "blue",
    "state_colors": {
        "idle": "#4a4a4a",
        "listening_wake": "#2b6cb0",
        "listening_command": "#2f855a",
        "processing": "#b7791f",
        "speaking": "#6b46c1",
        "paused": "#742a2a",
    },
    "bubble": {
        "user_color": "#2b6cb0",
        "assistant_color": "#3a3a3a",
        "text_color": "#ffffff",
        "corner_radius": 14,
        "wraplength": 280,
    },
    "window": {"chat_background": ["gray90", "gray14"]},
}

def _deep_merge(base, override):
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def load_theme():
    if THEME_PATH.exists():
        try:
            with open(THEME_PATH, "r", encoding="utf-8") as f:
                return _deep_merge(DEFAULT_THEME, json.load(f))
        except Exception as e:
            print(f"Couldn't load theme.json, using defaults: {e}")
    return DEFAULT_THEME

THEME = load_theme()
STATE_COLORS = THEME["state_colors"]

STATE_LABELS = {
    "idle": "Idle",
    "listening_wake": "Waiting for \u201cHey Nova\u201d",
    "listening_command": "Listening...",
    "processing": "Thinking...",
    "speaking": "Speaking...",
    "paused": "Paused",
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
        ctk.set_appearance_mode(THEME["appearance_mode"])
        ctk.set_default_color_theme(THEME["color_theme"])

        self.root = ctk.CTk()
        self.root.title("Nova")
        self.root.geometry("440x620")
        self.root.minsize(360, 480)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        self.build_header()
        self.build_chat_area()
        self.build_footer()

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

        self.root.after(80, self.poll_queue)
        self.root.withdraw()  # start hidden, tray-only

    # ---------- UI BUILDING ----------

    def build_header(self):
        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))

        title = ctk.CTkLabel(
            header, text="Nova", font=("Segoe UI", 22, "bold")
        )
        title.pack(anchor="w")

        pill_row = ctk.CTkFrame(header, fg_color="transparent")
        pill_row.pack(anchor="w", pady=(4, 0), fill="x")

        self.status_dot = ctk.CTkLabel(
            pill_row, text="\u25cf", text_color=STATE_COLORS["idle"],
            font=("Segoe UI", 16), width=16
        )
        self.status_dot.pack(side="left")

        self.status_var = ctk.StringVar(value="Starting...")
        status_label = ctk.CTkLabel(
            pill_row, textvariable=self.status_var, font=("Segoe UI", 13)
        )
        status_label.pack(side="left", padx=(4, 0))

        self.level_bar = ctk.CTkProgressBar(header, height=6)
        self.level_bar.set(0)
        self.level_bar.pack(fill="x", pady=(10, 0))

    def build_chat_area(self):
        self.chat_frame = ctk.CTkScrollableFrame(
            self.root, fg_color=tuple(THEME["window"]["chat_background"])
        )
        self.chat_frame.pack(padx=16, pady=8, fill="both", expand=True)

    def build_footer(self):
        footer = ctk.CTkFrame(self.root, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(0, 16))

        self.pause_btn = ctk.CTkButton(
            footer, text="Pause", command=self.toggle_pause
        )
        self.pause_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        quit_btn = ctk.CTkButton(
            footer,
            text="Quit Nova",
            fg_color="#a33",
            hover_color="#822",
            command=self.quit_app,
        )
        quit_btn.pack(side="left", expand=True, fill="x", padx=(6, 0))

    def add_bubble(self, speaker, text):
        is_user = speaker.lower() == "you"

        row = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        row.pack(fill="x", pady=4)

        bubble = ctk.CTkLabel(
            row,
            text=text,
            font=("Segoe UI", 13),
            fg_color=THEME["bubble"]["user_color"] if is_user else THEME["bubble"]["assistant_color"],
            text_color=THEME["bubble"]["text_color"],
            corner_radius=THEME["bubble"]["corner_radius"],
            justify="left",
            wraplength=THEME["bubble"]["wraplength"],
            padx=12,
            pady=8,
        )
        bubble.pack(side="right" if is_user else "left", padx=6)

        # auto-scroll to newest message
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    # ---------- EVENT LOOP ----------

    def poll_queue(self):
        try:
            while True:
                item = event_queue.get_nowait()
                kind = item[0]

                if kind == "log":
                    _, speaker, text = item
                    self.add_bubble(speaker, text)

                elif kind == "status":
                    pass  # status pill is driven by "state", not raw text

                elif kind == "state":
                    state = item[1]
                    self.status_var.set(STATE_LABELS.get(state, state))
                    self.status_dot.configure(
                        text_color=STATE_COLORS.get(state, "#4a4a4a")
                    )
                    self.tray_icon.icon = make_tray_image(
                        STATE_COLORS.get(state, "#4a4a4a")
                    )
                    if state == "paused":
                        self.pause_btn.configure(text="Resume")
                    elif state == "idle":
                        self.pause_btn.configure(text="Pause")

                elif kind == "level":
                    self.level_bar.set(item[1])
        except queue.Empty:
            pass

        self.root.after(80, self.poll_queue)

    # ---------- WINDOW / TRAY ----------

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
