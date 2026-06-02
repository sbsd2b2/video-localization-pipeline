<p align="center">
  <img src="/banner.png" alt="Video Localization Pipeline Banner" width="100%">
</p>

# Video Localization Pipeline

An automated pipeline for translating, dubbing, and synchronizing video content into multiple languages using speech recognition, machine translation, and voice synthesis.

---

## Why this project exists

Most video translation tools are either manual, fragmented, or require heavy post-processing.

This project aims to provide a fully automated pipeline that:

- Extracts audio and speech from videos
- Performs transcription (ASR)
- Translates subtitles into target languages
- Generates natural speech using TTS
- Re-synchronizes audio with original video timing

---

## Features

- End-to-end video localization pipeline
- Whisper-based speech recognition support
- Multi-language translation workflow
- TTS voice generation (supports multiple engines)
- Subtitle generation and alignment
- Modular architecture for easy extension

---

## Pipeline Overview

Video → Audio Extraction → ASR → Translation → TTS → Audio Re-sync → Final Video

---

## Use Cases

- YouTube video translation and dubbing
- Educational course localization
- Anime / game fan translation pipelines
- Multilingual content production for creators

---

## Status

The project is actively maintained and currently supports a fully functional end-to-end pipeline including ASR, translation, TTS, and video reconstruction.

Core features are stable, while optimization is ongoing in voice quality and alignment accuracy.

---

## Roadmap

- Improve voice naturalness and prosody
- Add real-time streaming support
- Enhance speaker diarization accuracy
- Build a lightweight web UI for non-technical users


## License

This project is released under the MIT License for research and educational purposes.


## Architecture Diagram

Below is a simplified architecture of the system:

```text
              ┌────────────────────┐
              │     Input Video    │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │  Audio Extraction  │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │   Speech-to-Text   │
              │     (ASR/Whisper)  │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │    Translation     │
              │   (Multi-language) │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │  Text-to-Speech    │
              │       (TTS)        │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │ Audio Re-sync      │
              │ + Video Merge      │
              └─────────┬──────────┘
                        │
                        ▼
              ┌────────────────────┐
              │  Final Output      │
              │  Localized Video   │
              └────────────────────┘


