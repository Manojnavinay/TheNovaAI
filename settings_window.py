import json
from tkinter import colorchooser, filedialog

import customtkinter as ctk
import sounddevice as sd

import assistant_core as core

CONFIG_PATH = core.BASE_DIR / "Config.json"
APPS_PATH = core.BASE_DIR / "Apps.json"
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


def _load_json(path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _deep_merge(base, override):
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Nova Settings")
        self.geometry("480x600")
        self.minsize(420, 480)

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)

        self.theme_tab = self.tabs.add("Theme")
        self.config_tab = self.tabs.add("Config")
        self.apps_tab = self.tabs.add("Apps")

        self.theme_data = _deep_merge(DEFAULT_THEME, _load_json(THEME_PATH, {}))
        self.config_data = _load_json(CONFIG_PATH, {})
        self.apps_data = _load_json(APPS_PATH, {})

        self.build_theme_tab()
        self.build_config_tab()
        self.build_apps_tab()

    # ---------- THEME TAB ----------

    def build_theme_tab(self):
        tab = self.theme_tab

        ctk.CTkLabel(tab, text="Appearance Mode").pack(anchor="w", pady=(8, 0))
        self.appearance_var = ctk.StringVar(value=self.theme_data["appearance_mode"])
        ctk.CTkOptionMenu(
            tab, values=["dark", "light"], variable=self.appearance_var
        ).pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(tab, text="Accent Color Theme").pack(anchor="w")
        self.color_theme_var = ctk.StringVar(value=self.theme_data["color_theme"])
        ctk.CTkOptionMenu(
            tab, values=["blue", "green", "dark-blue"], variable=self.color_theme_var
        ).pack(fill="x", pady=(2, 12))

        ctk.CTkLabel(tab, text="Status Dot Colors", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(4, 4)
        )
        self.state_color_buttons = {}
        for state_name, color in self.theme_data["state_colors"].items():
            row = ctk.CTkFrame(tab, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=state_name, width=140, anchor="w").pack(side="left")
            btn = ctk.CTkButton(
                row, text=color, fg_color=color, width=100,
                command=lambda s=state_name: self.pick_color("state_colors", s)
            )
            btn.pack(side="left")
            self.state_color_buttons[state_name] = btn

        ctk.CTkLabel(tab, text="Chat Bubbles", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(12, 4)
        )
        self.bubble_buttons = {}
        for key, label in [
            ("user_color", "Your messages"),
            ("assistant_color", "Nova's messages"),
            ("text_color", "Text color"),
        ]:
            row = ctk.CTkFrame(tab, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label, width=140, anchor="w").pack(side="left")
            btn = ctk.CTkButton(
                row, text=self.theme_data["bubble"][key],
                fg_color=self.theme_data["bubble"][key], width=100,
                command=lambda k=key: self.pick_color("bubble", k)
            )
            btn.pack(side="left")
            self.bubble_buttons[key] = btn

        ctk.CTkLabel(tab, text="Bubble Roundness").pack(anchor="w", pady=(12, 0))
        self.corner_radius_var = ctk.IntVar(value=self.theme_data["bubble"]["corner_radius"])
        ctk.CTkSlider(
            tab, from_=0, to=30, number_of_steps=30, variable=self.corner_radius_var
        ).pack(fill="x", pady=(2, 8))

        ctk.CTkButton(tab, text="Save Theme", command=self.save_theme).pack(pady=16)
        self.theme_status = ctk.CTkLabel(tab, text="")
        self.theme_status.pack()

    def pick_color(self, section, key):
        current = self.theme_data[section][key]
        _, hex_color = colorchooser.askcolor(color=current, title=f"Choose color for {key}")
        if hex_color:
            self.theme_data[section][key] = hex_color
            if section == "state_colors":
                self.state_color_buttons[key].configure(text=hex_color, fg_color=hex_color)
            else:
                self.bubble_buttons[key].configure(text=hex_color, fg_color=hex_color)

    def save_theme(self):
        self.theme_data["appearance_mode"] = self.appearance_var.get()
        self.theme_data["color_theme"] = self.color_theme_var.get()
        self.theme_data["bubble"]["corner_radius"] = int(self.corner_radius_var.get())

        with open(THEME_PATH, "w", encoding="utf-8") as f:
            json.dump(self.theme_data, f, indent=2)

        self.theme_status.configure(text="Saved. Restart Nova to see changes.")

    # ---------- CONFIG TAB ----------

    def build_config_tab(self):
        tab = self.config_tab

        ctk.CTkLabel(tab, text="Groq API Key").pack(anchor="w", pady=(8, 0))
        key_row = ctk.CTkFrame(tab, fg_color="transparent")
        key_row.pack(fill="x", pady=(2, 8))
        self.api_key_var = ctk.StringVar(value=self.config_data.get("api_key", ""))
        self.api_key_entry = ctk.CTkEntry(key_row, textvariable=self.api_key_var, show="*")
        self.api_key_entry.pack(side="left", fill="x", expand=True)
        self.key_visible = False
        ctk.CTkButton(
            key_row, text="Show", width=60, command=self.toggle_key_visibility
        ).pack(side="left", padx=(6, 0))

        ctk.CTkLabel(tab, text="AI Model (Groq)").pack(anchor="w")
        self.ai_model_var = ctk.StringVar(value=self.config_data.get("ai", {}).get("model", ""))
        ctk.CTkEntry(tab, textvariable=self.ai_model_var).pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(tab, text="Microphone").pack(anchor="w")
        self.devices = self.list_input_devices()
        device_names = [name for _, name in self.devices] or ["No input devices found"]
        current_index = self.config_data.get("audio", {}).get("input_device", 0)
        current_name = next(
            (n for i, n in self.devices if i == current_index), device_names[0]
        )
        self.device_var = ctk.StringVar(value=current_name)
        ctk.CTkOptionMenu(tab, values=device_names, variable=self.device_var).pack(
            fill="x", pady=(2, 8)
        )

        ctk.CTkLabel(tab, text="Voice Speed (lower = faster)").pack(anchor="w")
        self.length_scale_var = ctk.DoubleVar(
            value=self.config_data.get("voice", {}).get("length_scale", 1.0)
        )
        ctk.CTkSlider(tab, from_=0.5, to=2.0, variable=self.length_scale_var).pack(
            fill="x", pady=(2, 8)
        )

        ctk.CTkLabel(tab, text="Wake Word Sensitivity (higher = stricter)").pack(anchor="w")
        self.wake_threshold_var = ctk.DoubleVar(
            value=self.config_data.get("wake_word", {}).get("wake_threshold", 0.3)
        )
        ctk.CTkSlider(tab, from_=0.1, to=0.9, variable=self.wake_threshold_var).pack(
            fill="x", pady=(2, 8)
        )

        ctk.CTkLabel(tab, text="Voice Activity Sensitivity").pack(anchor="w")
        self.vad_threshold_var = ctk.DoubleVar(
            value=self.config_data.get("wake_word", {}).get("vad_threshold", 0.5)
        )
        ctk.CTkSlider(tab, from_=0.0, to=1.0, variable=self.vad_threshold_var).pack(
            fill="x", pady=(2, 8)
        )

        ctk.CTkButton(tab, text="Save Config", command=self.save_config).pack(pady=16)
        self.config_status = ctk.CTkLabel(tab, text="")
        self.config_status.pack()

    def list_input_devices(self):
        devices = []
        try:
            for i, d in enumerate(sd.query_devices()):
                if d.get("max_input_channels", 0) > 0:
                    devices.append((i, f"{i}: {d['name']}"))
        except Exception as e:
            devices.append((0, f"(couldn't list devices: {e})"))
        return devices

    def toggle_key_visibility(self):
        self.key_visible = not self.key_visible
        self.api_key_entry.configure(show="" if self.key_visible else "*")

    def save_config(self):
        selected_name = self.device_var.get()
        device_index = next((i for i, n in self.devices if n == selected_name), 0)

        self.config_data["api_key"] = self.api_key_var.get()
        self.config_data.setdefault("ai", {})["model"] = self.ai_model_var.get()
        self.config_data.setdefault("audio", {})["input_device"] = device_index
        self.config_data.setdefault("voice", {})["length_scale"] = round(
            float(self.length_scale_var.get()), 2
        )
        wake_word = self.config_data.setdefault("wake_word", {})
        wake_word["wake_threshold"] = round(float(self.wake_threshold_var.get()), 2)
        wake_word["vad_threshold"] = round(float(self.vad_threshold_var.get()), 2)

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=2)

        self.config_status.configure(text="Saved. Restart Nova to apply.")

    # ---------- APPS TAB ----------

    def build_apps_tab(self):
        tab = self.apps_tab

        self.apps_list_frame = ctk.CTkScrollableFrame(tab, height=200)
        self.apps_list_frame.pack(fill="both", expand=True, pady=(8, 8))
        self.refresh_apps_list()

        ctk.CTkLabel(tab, text="Add / Edit App", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(4, 4)
        )

        ctk.CTkLabel(tab, text="Name").pack(anchor="w")
        self.app_name_var = ctk.StringVar()
        ctk.CTkEntry(tab, textvariable=self.app_name_var, placeholder_text="e.g. edge").pack(
            fill="x", pady=(0, 8)
        )

        ctk.CTkLabel(tab, text="Path to .exe").pack(anchor="w")
        path_row = ctk.CTkFrame(tab, fg_color="transparent")
        path_row.pack(fill="x", pady=(0, 8))
        self.app_path_var = ctk.StringVar()
        ctk.CTkEntry(path_row, textvariable=self.app_path_var).pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkButton(path_row, text="Browse", width=70, command=self.browse_app_path).pack(
            side="left", padx=(6, 0)
        )

        ctk.CTkLabel(tab, text="Process name").pack(anchor="w")
        self.app_process_var = ctk.StringVar()
        ctk.CTkEntry(
            tab, textvariable=self.app_process_var, placeholder_text="e.g. msedge.exe"
        ).pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(tab, text="Aliases (comma separated)").pack(anchor="w")
        self.app_aliases_var = ctk.StringVar()
        ctk.CTkEntry(
            tab, textvariable=self.app_aliases_var, placeholder_text="e.g. browser, chrome"
        ).pack(fill="x", pady=(0, 8))

        ctk.CTkButton(tab, text="Add / Update App", command=self.add_or_update_app).pack(
            pady=(8, 4)
        )

        self.apps_status = ctk.CTkLabel(tab, text="")
        self.apps_status.pack()

    def refresh_apps_list(self):
        for widget in self.apps_list_frame.winfo_children():
            widget.destroy()

        for name in self.apps_data:
            row = ctk.CTkFrame(self.apps_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=name, anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkButton(
                row, text="Edit", width=50,
                command=lambda n=name: self.load_app_into_form(n)
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                row, text="Remove", width=60, fg_color="#a33", hover_color="#822",
                command=lambda n=name: self.remove_app(n)
            ).pack(side="left", padx=2)

    def load_app_into_form(self, name):
        info = self.apps_data.get(name, {})
        self.app_name_var.set(name)
        self.app_path_var.set(info.get("path", ""))
        self.app_process_var.set(info.get("process", ""))
        self.app_aliases_var.set(", ".join(info.get("aliases", [])))

    def browse_app_path(self):
        path = filedialog.askopenfilename(
            title="Select application executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if path:
            self.app_path_var.set(path)

    def add_or_update_app(self):
        name = self.app_name_var.get().strip()
        if not name:
            self.apps_status.configure(text="App needs a name.")
            return

        aliases = [a.strip() for a in self.app_aliases_var.get().split(",") if a.strip()]

        self.apps_data[name] = {
            "path": self.app_path_var.get().strip(),
            "process": self.app_process_var.get().strip(),
            "aliases": aliases,
        }

        with open(APPS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.apps_data, f, indent=2)
            core.reload_apps()

        self.refresh_apps_list()
        self.apps_status.configure(text=f"Saved '{name}'. Restart Nova to apply.")

        self.app_name_var.set("")
        self.app_path_var.set("")
        self.app_process_var.set("")
        self.app_aliases_var.set("")

    def remove_app(self, name):
        if name in self.apps_data:
            del self.apps_data[name]
            with open(APPS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.apps_data, f, indent=2)
                core.reload_apps()
            self.refresh_apps_list()
            self.apps_status.configure(text=f"Removed '{name}'.")
