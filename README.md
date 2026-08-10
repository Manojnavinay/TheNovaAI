# TheNovaAi

A lightweight, local-first PC voice assistant written in Python.

TheNovaAi combines:

* 🎤 Speech recognition
* 🧠 Groq-powered AI (Not Grok)
* 🔊 Piper TTS
* 👂 OpenWakeWord (Currently: Hey Nova)
* 🖥️ PC application control
* ⌨️ Keyboard/media controls
* 🌐 Web and YouTube search
* ⚡ Windows system controls

---

## Requirements

### Operating System

Currently designed for **Windows**.

### Python

Install **64-bit Python 3.14**.

Check your installation:

```powershell
py --version
```

---

# Installation

## 1. Download the Zip

Download the Zip from releases and extract it.

---

## 2. Install Python dependencies

Open PowerShell inside the project folder and run:

```powershell
py -m pip install sounddevice SpeechRecognition numpy openwakeword piper-tts pynput groq onnxruntime customtkinter pystray pillow
```

### What these packages do

| Package             | Purpose                           |
| ------------------- | --------------------------------- |
| `sounddevice`       | Microphone input and audio output |
| `SpeechRecognition` | Speech-to-text                    |
| `numpy`             | Audio processing                  |
| `openwakeword`      | Wake-word detection               |
| `piper-tts`         | Offline text-to-speech            |
| `pynput`            | Keyboard and media-key control    |
| `groq`              | Groq AI API                       |
| `onnxruntime`       | OpenWakeWord ONNX inference       |
| `customtkinter`     | Desktop UI Lib                    |
| `pystray`           | For System Tray Icon              |
| `pillow`            | Image processing                  |

---

# Project Files

The project should have a structure similar to:

```text
TheNovaAi/
│
├── Main.py
├── assistant_core.py
├── settings_window.py
├── Apps.json
├── config.json
├── theme.json
|
├── SpeechRecog/
|   ├── Hey_Nova.onnx
│   └── hey_jarvis_v0.1.onnx
│
└── Voices/
    ├── name.onnx
    └── name.onnx.json
```

---

~~# 3. Download the Wake Word Model~~

~~TheNovaAi currently uses the OpenWakeWord:~~

~~```text~~
~~Hey Jarvis~~
~~```~~

~~Place:~~

~~```text~~
~~hey_jarvis_v0.1.onnx~~
~~```~~

~~inside:~~

~~```text~~
Models/
~~```~~

~~The Python code should reference it using a relative path rather than an absolute path.~~

Already implemented

---

# 4. ~~Install a~~ Piper Voice

TheNovaAi uses Piper for offline text-to-speech. And the voice is already in the Folder

~~Place the voice files inside:~~

~~```text
Voices/
~~```~~

~~For example:~~

~~```text
Voices/
├── en_US-hfc_male-medium.onnx
└── en_US-hfc_male-medium.onnx.json
~~```~~

~~You can then use a relative path:~~

~~```python
VOICE_MODEL = "Voices/en_US-hfc_male-medium.onnx"
~~```~~

~~### Relative paths vs absolute paths~~

~~**Recommended:**~~

~~```python
VOICE_MODEL = "Voices/en_US-hfc_male-medium.onnx"
~~```~~

~~Avoid:~~

~~```python
VOICE_MODEL = r"C:\Users\Someone\Desktop\TheNovaAi\Voices\en_US-hfc_male-medium.onnx"
~~```~~

~~Relative paths allow the project to work on another computer without changing the username or folder location.~~

~~For even better portability, the project should eventually resolve paths relative to the Python file itself.~~

---

# 5. Configure Apps

Applications are stored in:

```text
Apps.json
```

Example:

```json
{
    "Edge": {
        "path": "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        "process": "msedge.exe",
        "aliases": [
            "edge",
            "microsoft edge"
        ]
    },

    "Nuclear": {
        "path": "C:\\Users\\YourName\\AppData\\Local\\Nuclear\\nuclear-music-player.exe",
        "process": "nuclear-music-player.exe",
        "aliases": [
            "nuclear",
            "nuclear music",
            "music player"
        ]
    }
}
```

### Adding an application

You can now add apps from the settings --> Apps tab

**OR**

Add another entry in the json:

```json
"ExampleApp": {
    "path": "C:\\Path\\To\\ExampleApp.exe",
    "process": "ExampleApp.exe",
    "aliases": [
        "example",
        "example app"
    ]
}
```

You do **not** need to modify the Python code.

> Make sure the JSON remains valid. A missing comma or quotation mark will prevent the program from starting.

---

# 6. Configure the Groq API

TheNovaAi uses Groq for its AI responses.

You need your **own Groq API key**. You can get yours from [here](https://console.groq.com/keys)

Put your API key into `Config.json`. Do not SHARE the API key with anybody.

If a key is accidentally exposed, revoke it and create a new one.

---

# 7. Microphone

TheNovaAi currently uses a specific audio input device.

The project contains:

```python
device=1
```

that number may be different on another computer.

If the microphone does not work, check the available devices with:

```python
import sounddevice as sd

print(sd.query_devices())
```

Find the desired microphone and update the configured device number in the config file.

~~A future version will make this configurable without editing the Python source.~~
Done, you can edit it in the `config.json` and from the program itself, settings --> Config Tab

---

# Running TheNovaAi

Once everything is installed run the following inside the Ai folder:

```powershell
py main.py
```
Right Click in the folder where main.py is located --> click Open in terminal --> run `py main.py`

The program will start to listen for `Hey Nova` to be spoken, program is minimized into the tray by default

---

# Example Commands

### Applications

```text
Open Edge (to use a different browser it must be added into the Apps.json)
Open Nuclear (music app)
Close Edge
```

### Websites

```text
Open YouTube
Open WhatsApp Web
Search the web for Minecraft shaders
```

### YouTube

```text
Search for Minecraft in YouTube 
```

### Media

```text
Turn the volume up
Turn the volume down
Mute the computer
Pause the music
Next track
Previous track
```

### System

```text
Shut down the computer
Restart the computer
Hibernate the computer
```

### Pause

```text
Close/Exit/Or something similar
```
*OR* click the pause button

### Exit

Right click the `tray icon` --> `Quit Nova`
*OR*
Click `Quit Nova` in the program window

---

# Troubleshooting

## `ModuleNotFoundError`

If you see something like:

```text
ModuleNotFoundError: No module named 'sounddevice'
```

install the dependencies again:

```powershell
py -m pip install sounddevice SpeechRecognition numpy openwakeword piper-tts pynput groq onnxruntime
```

---

## Wake word model not found

Make sure:

```text
Models/Hey_Nova.onnx
```

exists and that the Python path matches the actual filename in Ai.py.

---

## Piper voice not found

Make sure both the `.onnx` voice file and its `.json` configuration file are present in `Voices/`.

---

## Microphone not working

Check your audio devices:

```python
import sounddevice as sd

print(sd.query_devices())
```

Then make sure TheNovaAi is using the correct input device.

---

## Groq API errors

Check that:

1. Your API key is valid.
2. The `GROQ_API_KEY` variable is set in config.
3. Your computer has an Internet connection.
4. Your selected Groq model is available to your account.

---

# Current Architecture

```text
Microphone
    │
    ▼
OpenWakeWord
    │
    │ "Hey Nova"
    ▼
Speech Recognition
    │
    ▼
Groq AI
    │
    ├── PC action
    └── Natural response
          │
          ▼
       Piper TTS
          │
          ▼
       Speakers
```

Application information is stored separately in:

```text
Apps.json
```

This allows applications and aliases to be added without modifying the core assistant logic.

---

# Future Plans

Planned improvements include:

* [x] GUI
* [x] Config file
* [x] Easier microphone selection
* [x] Custom wake word (currently not user customizable)
* [ ] More PC commands
* [ ] More application integrations
* [ ] Better speech detection
* [ ] User-specific voice recognition
* [ ] Memory
* [ ] Standalone `.exe`
* [ ] Installer
* [ ] Customizable assistant responses

---

## License

Idk
