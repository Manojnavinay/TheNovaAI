import sounddevice as sd
import speech_recognition as sr
import time
import numpy as np
import webbrowser
import urllib.parse
import subprocess
import random
import os
import sys
import json
import threading

from openwakeword.model import Model
from piper import PiperVoice
from pynput import keyboard
from pynput.keyboard import Key, Controller
from groq import Groq
from pathlib import Path

# ---------- CALLBACKS ----------
# The GUI (or CLI) supplies an object with log/status/state methods.
# Default implementation just prints, so this module still works standalone.

class Callbacks:
    def log(self, speaker: str, text: str):
        print(f"{speaker}: {text}")

    def status(self, text: str):
        print(text)

    def state(self, state: str):
        # state is one of: idle, listening_wake, listening_command,
        # processing, speaking, paused
        pass

def level(self, value: float):
        # normalized 0.0-1.0 mic input level
        pass

_callbacks = Callbacks()


def set_callbacks(cb: "Callbacks"):
    global _callbacks
    _callbacks = cb


# ---------- PATHS ----------

if getattr(sys, "frozen", False):
    BASE_DIR = Path(os.path.dirname(sys.executable))
else:
    BASE_DIR = Path(__file__).resolve().parent

# ---------- CONFIG ----------

with open(BASE_DIR / "Config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

API_KEY = config["api_key"]

INPUT_DEVICE = config["audio"]["input_device"]
SAMPLE_RATE = config["audio"]["sample_rate"]
WAKE_SAMPLE_RATE = config["audio"]["wake_sample_rate"]
WAKE_BLOCK_SIZE = config["audio"]["wake_block_size"]
WAKE_MODEL = str(BASE_DIR / config["wake_word"]["model"])
VAD_THRESHOLD = config["wake_word"]["vad_threshold"]
WAKE_THRESHOLD = config["wake_word"].get("wake_threshold", 0.3)
VOICE_MODEL = BASE_DIR / config["voice"]["model"]
VOICE_LENGTH_SCALE = config["voice"]["length_scale"]

AI_MODEL = config["ai"]["model"]

# ---------- SETUP ----------

voice = PiperVoice.load(str(VOICE_MODEL))
voice.config.length_scale = VOICE_LENGTH_SCALE

client = Groq(api_key=API_KEY)

with open(BASE_DIR / "Apps.json", "r", encoding="utf-8") as file:
    apps = json.load(file)

wake_model = Model(
    wakeword_models=[WAKE_MODEL],
    inference_framework="onnx",
    vad_threshold=VAD_THRESHOLD
)

wake_responses = [
    "Yeah?",
    "I'm listening.",
    "Go ahead.",
    "Yes?",
    "What can I do for you?",
    "I’m here.",
    "Yep?",
    "Go ahead.",
    "What’s up?",
    "Ready when you are.",
    "Listening.",
    "At your service.",
    "Nova ready.",
    "You called?",
    "What can Nova do for you?",
    "All systems ready.",
    "Yo! What’s up?",
    "Hey! I’m here.",
    "What’s going on?",
    "Yep, I’m listening.",
    "Shoot.",
    "I got you.",
    "What do you need?",
    "Alright, I’m listening.",
    "Nova has entered the chat.",
    "And we’re live.",
    "I heard you!",
    "Present!",
    "Nova at your service.",
    "I’m all ears.",
    "How may I assist?",
    "What would you like me to do?",
    "Awaiting your command.",
    "How can I assist you today?",
    "Standing by."
]

_last_wake_response = [None]

def pick_wake_response():
    choices = [r for r in wake_responses if r != _last_wake_response[0]]
    choice = random.choice(choices)
    _last_wake_response[0] = choice
    return choice

media_keyboard = Controller()

space_state = {"held": False}
_speaking = threading.Event()

def _on_space_press(key):
    if key == keyboard.Key.space:
        space_state["held"] = True


def _on_space_release(key):
    if key == keyboard.Key.space:
        space_state["held"] = False


global_key_listener = keyboard.Listener(
    on_press=_on_space_press,
    on_release=_on_space_release
)
global_key_listener.start()

# ---------- SPEAK ----------

def speak(text):
    _callbacks.log("Assistant", text)
    _callbacks.state("speaking")
    _speaking.set()

    chunks = voice.synthesize(text)
    stream = None

    try:
        for chunk in chunks:
            if stream is None:
                stream = sd.RawOutputStream(
                    samplerate=chunk.sample_rate,
                    channels=chunk.sample_channels,
                    dtype="int16"
                )
                stream.start()
            stream.write(chunk.audio_int16_bytes)
    finally:
        if stream is not None:
            stream.stop()
            stream.close()
        time.sleep(0.3)  # let any speaker bleed settle before listening again
        _speaking.clear()

# ---------- LISTEN (push-to-talk) ----------

def listen():
    _callbacks.status("Hold SPACE to talk...")
    audio_data = []

    while not space_state["held"]:
        time.sleep(0.01)

    def _capture_callback(indata, frames, time_info, status):
        audio_data.append(indata.copy())
        rms = np.sqrt(np.mean(indata.astype(np.float32) ** 2))
        _callbacks.level(min(float(rms) / 3000.0, 1.0))

    with sd.InputStream(
        samplerate=WAKE_SAMPLE_RATE,
        channels=1,
        dtype="int16",
        device=INPUT_DEVICE,
        blocksize=WAKE_BLOCK_SIZE,
        callback=_capture_callback
    ):
        while space_state["held"]:
            time.sleep(0.01)

    _callbacks.level(0.0)

    if not audio_data:
        return ""

    audio = np.concatenate(audio_data, axis=0)
    recorded_audio = sr.AudioData(audio.tobytes(), WAKE_SAMPLE_RATE, 2)
    recognizer = sr.Recognizer()

    try:
        text = recognizer.recognize_google(recorded_audio)
        _callbacks.log("You", text)
        return text
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as error:
        _callbacks.status(f"Speech recognition error: {error}")
        return ""

# ---------- WAKE WORD ----------

def wait_for_wake(stop_event: threading.Event):
    _callbacks.status("Listening for Hey Nova...")
    _callbacks.state("listening_wake")

    activated = False
    used_space = False

    import time as _t
    last_print = [0.0]

    def callback(indata, frames, time_info, status):
        nonlocal activated
        if activated or _speaking.is_set():
            return
        audio = indata[:, 0].astype(np.int16)
        _callbacks.level(min(float(np.sqrt(np.mean(audio.astype(np.float32) ** 2))) / 3000.0, 1.0))
        prediction = wake_model.predict(audio)
        for name, score in prediction.items():
            if _t.time() - last_print[0] > 0.5:
#                print(f"[debug] {name}: {score:.3f}")
                last_print[0] = _t.time()
            if score > WAKE_THRESHOLD:
                activated = True
                break

    with sd.InputStream(
        samplerate=16000,
        channels=1,
        dtype="int16",
        device=INPUT_DEVICE,
        blocksize=1280,
        callback=callback
    ):
        while not activated:
            if stop_event.is_set():
                return None
            if space_state["held"]:
                used_space = True
                activated = True
                break
            time.sleep(0.01)

    wake_model.reset()

    _callbacks.level(0.0)

    if used_space:
        _callbacks.status("Space pressed.")
        return "space"

    speak(pick_wake_response())
    return "wake"

def listen_after_wake():
    _callbacks.status("Listening...")

    sample_rate1 = 44100
    block_duration = 0.1
    block_size = int(sample_rate1 * block_duration)

    SILENCE_THRESHOLD = 500
    MAX_WAIT = 5.0
    SILENCE_DURATION = 1.5

    audio_data = []
    speech_started = False
    silence_time = 0.0
    wait_start = time.time()

    with sd.InputStream(
        samplerate=sample_rate1,
        channels=1,
        device=INPUT_DEVICE,
        dtype="int16",
        blocksize=block_size
    ) as stream:

        while True:
            audio, overflowed = stream.read(block_size)
            audio = audio.copy()
            audio_data.append(audio)

            rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
            _callbacks.level(min(float(rms) / 3000.0, 1.0))

            if rms > SILENCE_THRESHOLD:
                if not speech_started:
                    speech_started = True
                    silence_time = 0.0
            elif speech_started:
                silence_time += block_duration

            if not speech_started:
                if time.time() - wait_start >= MAX_WAIT:
                    return ""

            if speech_started and silence_time >= SILENCE_DURATION:
                break
            _callbacks.level(0.0)
            
    if not audio_data:
        return ""

    audio = np.concatenate(audio_data, axis=0)
    recorded_audio = sr.AudioData(audio.tobytes(), sample_rate1, 2)
    recognizer = sr.Recognizer()

    try:
        text = recognizer.recognize_google(recorded_audio)
        _callbacks.log("You", text)
        return text
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as error:
        _callbacks.status(f"Speech recognition error: {error}")
        return ""

# ---------- AI ----------

MAX_HISTORY_MESSAGES = 20  # ~10 back-and-forth turns, keeps context sane

conversation_history = []

def ask_ai(text):
    global conversation_history

    messages = [
        {
            "role": "system",
            "content": """
           You are a PC voice assistant.

You must ALWAYS respond in this format:

ACTION: <action>
VALUE: <value>
SAY: <what the assistant should say>

You may provide multiple ACTION/VALUE pairs when the user's request requires multiple actions.

Allowed actions:
- none
- open_url
- open_app
- close_app
- search_web
- search_youtube
- volume_up
- volume_down
- volume_mute
- media_play_pause
- media_next
- media_previous
- shutdown
- restart
- hibernate
- exit

Rules:
- Use only the allowed actions.
- Each ACTION must have its own VALUE.
- If no PC action is needed, use ACTION: none and leave VALUE empty.
- SAY must be short and natural.
- Do not use Markdown.
- URLs must be plain URLs.
- Do not add anything outside the ACTION, VALUE, and SAY lines.
- For SAY, use a short natural sentence appropriate to the request, not necessarily the example given. Do not mention ACTION, VALUE, or formatting.
- For open_app and close_app, VALUE must be the app's normal name, not an alias.

Example:

User: Open YouTube
ACTION: open_url
VALUE: https://www.youtube.com
SAY: Opening YouTube.

User: Search for Minecraft shaders
ACTION: search_web
VALUE: Minecraft shaders
SAY: Searching for Minecraft shaders.

User: Open Edge
ACTION: open_app
VALUE: edge
SAY: Opening Edge.

User: What is the capital of India?
ACTION: none
VALUE:
SAY: The capital of India is New Delhi.

User: Goodbye
ACTION: exit
VALUE:
SAY: Goodbye.

User: Close Edge
ACTION: close_app
VALUE: edge
SAY: Closing Edge.

User: Open YouTube and search for Minecraft
ACTION: search_youtube
VALUE: Minecraft
SAY: Searching YouTube for Minecraft.

User: Shut down the computer
ACTION: shutdown
VALUE:
SAY: Shutting down.

User: Restart the computer
ACTION: restart
VALUE:
SAY: Restarting the computer.

User: Hibernate the computer
ACTION: hibernate
VALUE:
SAY: Hibernating.
            """
        },
        *conversation_history,
        {
            "role": "user",
            "content": text
        }
    ]

    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=messages
    )

    reply = response.choices[0].message.content

    conversation_history.append({"role": "user", "content": text})
    conversation_history.append({"role": "assistant", "content": reply})

    if len(conversation_history) > MAX_HISTORY_MESSAGES:
        conversation_history[:] = conversation_history[-MAX_HISTORY_MESSAGES:]

    return reply

# ---------- EXECUTE ----------

def execute_action(response):
    lines = response.splitlines()

    actions = []
    current_action = None
    say = ""

    for line in lines:
        if line.startswith("ACTION:"):
            current_action = line.replace("ACTION:", "", 1).strip()
        elif line.startswith("VALUE:"):
            value = line.replace("VALUE:", "", 1).strip()
            if current_action:
                actions.append((current_action, value))
                current_action = None
        elif line.startswith("SAY:"):
            say = line.replace("SAY:", "", 1).strip()

    for action, value in actions:
        if action == "open_url":
            webbrowser.open(value)

        elif action == "search_web":
            url = "https://www.bing.com/search?q=" + urllib.parse.quote(value)
            webbrowser.open(url)

        elif action == "search_youtube":
            url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(value)
            webbrowser.open(url)

        elif action == "open_app":
            app = find_app(value)
            if app:
                subprocess.Popen(app["path"])
            else:
                _callbacks.status(f"App not allowed: {value}")

        elif action == "close_app":
            app = find_app(value)
            if app:
                subprocess.run(
                    ["taskkill", "/IM", app["process"], "/F"],
                    capture_output=True
                )
            else:
                _callbacks.status(f"App not allowed: {value}")

        elif action == "volume_up":
            media_keyboard.press(Key.media_volume_up)
            media_keyboard.release(Key.media_volume_up)

        elif action == "volume_down":
            media_keyboard.press(Key.media_volume_down)
            media_keyboard.release(Key.media_volume_down)

        elif action == "volume_mute":
            media_keyboard.press(Key.media_volume_mute)
            media_keyboard.release(Key.media_volume_mute)

        elif action == "media_play_pause":
            media_keyboard.press(Key.media_play_pause)
            media_keyboard.release(Key.media_play_pause)

        elif action == "media_next":
            media_keyboard.press(Key.media_next)
            media_keyboard.release(Key.media_next)

        elif action == "media_previous":
            media_keyboard.press(Key.media_previous)
            media_keyboard.release(Key.media_previous)

        elif action == "shutdown":
            subprocess.run(["shutdown", "/s", "/t", "0"])

        elif action == "restart":
            subprocess.run(["shutdown", "/r", "/t", "0"])

        elif action == "hibernate":
            subprocess.run(["shutdown", "/h"])

        elif action == "none":
            pass

        elif action == "exit":
            if say:
                speak(say)
            _callbacks.state("idle")
            return "pause"

        else:
            _callbacks.status(f"Unknown action: {action}")

    if say:
        speak(say)
    return False

# ---------- MAIN LOOP ----------

def run(stop_event: threading.Event, pause_event: threading.Event):
    """Runs the assistant loop until stop_event is set. Call this on a
    background thread — it blocks."""

    while not stop_event.is_set():

        if pause_event.is_set():
            _callbacks.state("paused")
            time.sleep(0.2)
            continue

        activation = wait_for_wake(stop_event)
        if activation is None:
            break  # stop was requested while waiting

        if activation == "wake":
            _callbacks.state("listening_command")
            command = listen_after_wake()
        else:
            _callbacks.state("listening_command")
            command = listen()

        if command:
            _callbacks.state("processing")
            response = ask_ai(command)
            result = execute_action(response)
            if result == "pause":
                pause_event.set()
        else:
            _callbacks.status("Didn't hear anything.")

        _callbacks.state("idle")


if __name__ == "__main__":
    # Lets you still run this file directly from a terminal, CLI-style.
    _stop = threading.Event()
    _pause = threading.Event()
    try:
        run(_stop, _pause)
    except KeyboardInterrupt:
        _stop.set()
