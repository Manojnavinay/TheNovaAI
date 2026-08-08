# TheNovaAi

A lightweight, local-first PC voice assistant written in Python.

TheNovaAi combines:

* 🎤 Speech recognition
* 🧠 Groq-powered AI (Not Grok)
* 🔊 Piper TTS
* 👂 OpenWakeWord (Currently: Hey Jarvis)
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
py -m pip install sounddevice SpeechRecognition numpy openwakeword piper-tts pynput groq onnxruntime
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

The other Python modules used by the project are part of Python's standard library and do not need to be installed separately.

---

# Project Files

The project should have a structure similar to:

```text
TheNovaAi/
│
├── Ai.py
├── Apps.json
│
├── SpeechRecog/
│   └── hey_jarvis_v0.1.onnx
│
└── Voices/
    ├── name.onnx
    └── name.onnx.json
```

Your actual voice/model filenames may differ depending on which Piper voice you choose.

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

Add another entry:

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

You need your **own Groq API key**.

Put your API key directly into `Ai.py`. Do not SHARE the API key with anybody.

### Recommended method

Set an environment variable.

In PowerShell:

```powershell
$env:GROQ_API_KEY="YOUR_API_KEY_HERE"
```

Then the Python code can use:

```python
import os

client = Groq(
    api_key=os.environ["GROQ_API_KEY"]
)
```

Never commit your API key to GitHub.

If a key is accidentally exposed, revoke it and create a new one.

---

# 7. Microphone

TheNovaAi currently uses a specific audio input device.

If the project contains something like:

```python
device=1
```

that number may be different on another computer.

If the microphone does not work, check the available devices with:

```python
import sounddevice as sd

print(sd.query_devices())
```

Find the desired microphone and update the configured device number.

A future version will make this configurable without editing the Python source.

---

# Running TheNovaAi

Once everything is installed:

```powershell
py gemini.py
```

You should see something similar to:

```text
Listening for Hey Jarvis...
```

Say:

```text
Hey Jarvis
```

The assistant will respond and begin listening for your command.

---

# Example Commands

### Applications

```text
Open Edge
Open Nuclear
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
Open YouTube and search for Minecraft
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

### Exit

```text
Close
```

or another configured exit command.

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
Models/hey_jarvis_v0.1.onnx
```

exists and that the Python path matches the actual filename.

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
2. The `GROQ_API_KEY` environment variable is set.
3. Your computer has an Internet connection.
4. Your selected Groq model is available to your account.

---

# Security

**Never commit API keys to GitHub.**

Do not put this in the repository:

```python
Groq(api_key="gsk_...")
```

Use an environment variable instead.

You should also avoid committing personal paths such as:

```text
C:\Users\YourName\...
```

when they aren't necessary.

---

# Current Architecture

```text
Microphone
    │
    ▼
OpenWakeWord
    │
    │ "Hey Jarvis"
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

* [ ] GUI
* [ ] Config file
* [ ] Easier microphone selection
* [ ] Custom wake word
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

Add the project's license here before publishing the repository.
