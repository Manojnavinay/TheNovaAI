import threading
import queue
import json
import math
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageDraw
import pystray

import assistant_core as core

event_queue: "queue.Queue" = queue.Queue()

# ---------- THEME ----------

THEME_PATH = core.BASE_DIR / "theme.json"

DEFAULT_THEME = {
    "appearance_mode": "dark",
    "color_theme": "blue",
    "accent_color": "#7c5cff",
    "state_colors": {
        "idle": "#4a4a52",
        "listening_wake": "#4f8cff",
        "listening_command": "#31c48d",
        "processing": "#f0a63a",
        "speaking": "#b06cf0",
        "paused": "#e05264",
    },
    "bubble": {
        "user_color": "#7c5cff",
        "assistant_color": "#232329",
        "text_color": "#f4f4f6",
        "corner_radius": 16,
        "wraplength": 280,
    },
    "window": {
        "bg": "#0b0b0d",
        "panel_bg": "#141417",
        "chat_background": ["#f2f2f2", "#0f0f12"],
    },
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

# ---------- COLOR HELPERS ----------

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c))) for c in rgb)


def lerp_color(c1, c2, t):
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return rgb_to_hex((r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t))


# ---------- CALLBACKS ----------

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
    PANEL_WIDTH = 220

    def __init__(self):
        ctk.set_appearance_mode(THEME["appearance_mode"])
        ctk.set_default_color_theme(THEME["color_theme"])

        self.root = ctk.CTk()
        self.root.title("Nova")
        self.root.geometry("440x640")
        self.root.minsize(360, 480)
        self.root.configure(fg_color=THEME["window"]["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        self.view_mode = "chat"
        self.panel_open = False
        self.current_state = "idle"
        self.current_level = 0.0
        self.orb_phase = 0.0

        self.build_topbar()
        self.build_stage()
        self.build_side_panel()
        self.switch_view("chat")
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
        self.root.after(50, self.animate_orb)
        self.root.withdraw()  # start hidden, tray-only

    # ---------- TOP BAR ----------

    def build_topbar(self):
        bar = ctk.CTkFrame(self.root, fg_color="transparent", height=48)
        bar.pack(fill="x", padx=8, pady=(8, 0))

        self.hamburger_btn = ctk.CTkButton(
            bar, text="\u2630", width=36, height=36,
            fg_color="transparent", hover_color=THEME["window"]["panel_bg"],
            text_color=THEME["bubble"]["text_color"],
            font=("Segoe UI", 16), command=self.toggle_panel
        )
        self.hamburger_btn.pack(side="left")

        title = ctk.CTkLabel(
            bar, text="Nova", font=("Segoe UI", 16, "bold"),
            text_color=THEME["bubble"]["text_color"]
        )
        title.pack(side="left", padx=(10, 0))

    # ---------- STAGE (chat / orb container) ----------

    def build_stage(self):
        self.stage = ctk.CTkFrame(self.root, fg_color="transparent")
        self.stage.pack(fill="both", expand=True)

        self.body = ctk.CTkFrame(self.stage, fg_color="transparent")
        self.body.pack(fill="both", expand=True)
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        self.build_chat_view()
        self.build_orb_view()

        self.chat_view.grid(row=0, column=0, sticky="nsew")
        self.orb_view.grid(row=0, column=0, sticky="nsew")

    def build_chat_view(self):
        self.chat_view = ctk.CTkFrame(self.body, fg_color="transparent")

        header = ctk.CTkFrame(self.chat_view, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(8, 4))

        pill_row = ctk.CTkFrame(header, fg_color="transparent")
        pill_row.pack(anchor="w", fill="x")

        self.status_dot = ctk.CTkLabel(
            pill_row, text="\u25cf", text_color=STATE_COLORS["idle"],
            font=("Segoe UI", 16), width=16
        )
        self.status_dot.pack(side="left")

        self.status_var = ctk.StringVar(value="Starting...")
        ctk.CTkLabel(
            pill_row, textvariable=self.status_var, font=("Segoe UI", 13),
            text_color=THEME["bubble"]["text_color"]
        ).pack(side="left", padx=(4, 0))

        self.level_bar = ctk.CTkProgressBar(
            header, height=5, progress_color=THEME["accent_color"]
        )
        self.level_bar.set(0)
        self.level_bar.pack(fill="x", pady=(8, 0))

        self.chat_frame = ctk.CTkScrollableFrame(
            self.chat_view, fg_color=tuple(THEME["window"]["chat_background"])
        )
        self.chat_frame.pack(padx=16, pady=8, fill="both", expand=True)

    def build_orb_view(self):
        self.orb_view = ctk.CTkFrame(self.body, fg_color="transparent")

        wrap = ctk.CTkFrame(self.orb_view, fg_color="transparent")
        wrap.place(relx=0.5, rely=0.45, anchor="center")

        self.orb_canvas = tk.Canvas(
            wrap, width=240, height=240,
            bg=THEME["window"]["bg"], highlightthickness=0, bd=0
        )
        self.orb_canvas.pack()

        self.orb_status_var = ctk.StringVar(value="Idle")
        ctk.CTkLabel(
            self.orb_view, textvariable=self.orb_status_var,
            font=("Segoe UI", 15), text_color=THEME["bubble"]["text_color"]
        ).place(relx=0.5, rely=0.72, anchor="center")

    def switch_view(self, mode):
        self.view_mode = mode
        if mode == "chat":
            self.chat_view.tkraise()
        else:
            self.orb_view.tkraise()
        self.mode_toggle_btn.configure(
            text="Switch to Orb Mode" if mode == "chat" else "Switch to Chat Mode"
        )

    def toggle_view_mode(self):
        self.switch_view("orb" if self.view_mode == "chat" else "chat")
        self.close_panel()

    # ---------- SIDE PANEL ----------

    def build_side_panel(self):
        self.panel = ctk.CTkFrame(
            self.stage, fg_color=THEME["window"]["panel_bg"], corner_radius=0
        )
        self.panel.place(x=-self.PANEL_WIDTH, y=0, relheight=1, width=self.PANEL_WIDTH)

        ctk.CTkLabel(
            self.panel, text="Menu", font=("Segoe UI", 14, "bold"),
            text_color=THEME["bubble"]["text_color"]
        ).pack(anchor="w", padx=16, pady=(20, 12))

        self.mode_toggle_btn = ctk.CTkButton(
            self.panel, text="Switch to Orb Mode",
            fg_color=THEME["accent_color"], command=self.toggle_view_mode
        )
        self.mode_toggle_btn.pack(fill="x", padx=16, pady=6)

        ctk.CTkButton(
            self.panel, text="Settings",
            fg_color=THEME["accent_color"], command=self.open_settings_from_panel
        ).pack(fill="x", padx=16, pady=6)

        self.pause_btn = ctk.CTkButton(
            self.panel, text="Pause",
            fg_color=THEME["accent_color"], command=self.toggle_pause
        )
        self.pause_btn.pack(fill="x", padx=16, pady=6)

        ctk.CTkButton(
            self.panel, text="Quit Nova", fg_color="#a33", hover_color="#822",
            command=self.quit_app
        ).pack(fill="x", padx=16, pady=(6, 6))

        # click-catcher: clicking the dimmed stage area closes the panel
        self.body.bind("<Button-1>", lambda e: self.close_panel())

    def toggle_panel(self):
        self.open_panel() if not self.panel_open else self.close_panel()

    def open_panel(self):
        self.panel_open = True
        self.panel.lift()
        self._animate_panel(0)

    def close_panel(self):
        if not self.panel_open:
            return
        self.panel_open = False
        self._animate_panel(-self.PANEL_WIDTH)

    def _animate_panel(self, target_x, steps=10, delay=12):
        start_x = self.panel.winfo_x()
        step = (target_x - start_x) / steps

        def _tick(i, x):
            if i >= steps:
                self.panel.place(x=target_x, y=0, relheight=1, width=self.PANEL_WIDTH)
                return
            x += step
            self.panel.place(x=x, y=0, relheight=1, width=self.PANEL_WIDTH)
            self.root.after(delay, lambda: _tick(i + 1, x))

        _tick(0, start_x)

    def open_settings_from_panel(self):
        self.close_panel()
        self.open_settings()

    def open_settings(self):
        from settings_window import SettingsWindow
        SettingsWindow(self.root)

    # ---------- CHAT BUBBLES ----------

    def add_bubble(self, speaker, text):
        is_user = speaker.lower() == "you"

        row = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        row.pack(fill="x", pady=4)

        bubble = ctk.CTkLabel(
            row, text=text, font=("Segoe UI", 13),
            fg_color=THEME["bubble"]["user_color"] if is_user else THEME["bubble"]["assistant_color"],
            text_color=THEME["bubble"]["text_color"],
            corner_radius=THEME["bubble"]["corner_radius"],
            justify="left", wraplength=THEME["bubble"]["wraplength"],
            padx=12, pady=8,
        )
        bubble.pack(side="right" if is_user else "left", padx=6)
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    # ---------- ORB ANIMATION ----------

    def animate_orb(self):
        self.orb_phase += 0.15
        base_color = STATE_COLORS.get(self.current_state, STATE_COLORS["idle"])

        amplitude = 8 + self.current_level * 22
        radius = 62 + amplitude * math.sin(self.orb_phase)
        radius = max(30, radius)

        cx, cy = 120, 120
        edge_color = lerp_color(base_color, THEME["window"]["bg"], 0.82)
        center_color = lerp_color(base_color, "#ffffff", 0.18)

        self.orb_canvas.delete("all")
        rings = 7
        for i in range(rings, 0, -1):
            t = i / rings
            r = radius * (0.35 + 0.65 * t)
            color = lerp_color(center_color, edge_color, t)
            self.orb_canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=color, outline=""
            )

        self.root.after(50, self.animate_orb)

    # ---------- EVENT LOOP ----------

    def poll_queue(self):
        try:
            while True:
                item = event_queue.get_nowait()
                kind = item[0]

                if kind == "log":
                    _, speaker, text = item
                    self.add_bubble(speaker, text)

                elif kind == "state":
                    state = item[1]
                    self.current_state = state
                    label = STATE_LABELS.get(state, state)

                    self.status_var.set(label)
                    self.orb_status_var.set(label)
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
                    self.current_level = item[1]
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
        self.close_panel()

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
