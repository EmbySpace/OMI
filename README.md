# OMI — Open Mesh Informator
Open Mesh Informator is a Python script for automated weather report generation and broadcasting over LoRa mesh networks via MeshCore.

[![Hardware: ESP32](https://img.shields.io/badge/Hardware-ESP32-E7352C?logo=espressif&logoColor=white)](#)
[![Platform: Arduino](https://img.shields.io/badge/Platform-Arduino-00979D?logo=arduino&logoColor=white)](#)
[![Network: MeshCore](https://img.shields.io/badge/Network-MeshCore-523293)](#)

The script fetches current weather data, generates a short broadcast greeting using a local Ollama instance with Qwen2.5:3b, optimizes the payload size, splits longer messages into chunked packets, and sends them to the public mesh channel via MeshCore CLI over a wired USB/serial connection.

Features
Wired Connection: Interacts directly with the MeshCore node over USB/Serial. Radio frequencies and channel parameters must be pre-configured on the hardware node itself.

Public Channel Broadcast: Transmits generated weather updates directly to the main public mesh chat.

Cyrillic Homoglyph Optimization: Replaces overlapping Cyrillic characters with single-byte Latin equivalents, saving 15-20% of UTF-8 space.

Smart Punctuation Splitter: Splits long text by punctuation marks, adds chunk indexing like [1/2], and holds a 10-second delay between packet bursts.

LLM Output Sanitization: Strips non-ASCII artifacts, Chinese characters, newlines, and quotes from generated text.

Timeout Safeguards: Commands run with a 15-second execution timeout to prevent serial port freezes.

Offline Fallback: Falls back to a hardcoded template if the external weather service is unavailable.

TODO / Roadmap
Add Wi-Fi and Bluetooth connection support for wireless operation.

Native Meshtastic protocol integration.

Quick Start
Install dependencies:
pip install requests meshcore-cli

Pull the model in Ollama:
ollama pull qwen2.5:3b

Prepare the node interface if required:
meshcore-cli -s COM12 prepare

Set parameters in main_qwen2.5-3b.py:
SERIAL_PORT = "COM12"
MAX_BYTES = 110
OLLAMA_MODEL = "qwen2.5:3b"

Run the script:
python main_qwen2.5-3b.py

License
MIT
