#!/usr/bin/env python3
import asyncio
import argparse
import sys
import subprocess
import numpy as np
import librosa
from pathlib import Path
import edge_tts

VOICE_MAPPING = {
    "female": {
        "voice": "zh-CN-XiaoxiaoNeural",
        "rate": "+10%",
        "pitch": "-4Hz",
        "description": "晓晓夏郎微调版"
    },
    "male": {
        "voice": "zh-CN-YunjianNeural",
        "rate": "+12%",
        "pitch": "+8Hz",
        "description": "云健黄金调校版"
    }
}

def setup_argparse():
    parser = argparse.ArgumentParser(description="Step 4: Smart Gender Detect & Voice/Pitch Assign")
    parser.add_argument("--work-dir", type=str, required=True, help="Path to working directory")
    parser.add_argument("--proxy", type=str, default="http://127.0.0.1:7890", help="Proxy address")
    return parser.parse_args()

def detect_gender(vocal_wav: Path):
    print(f"⏳ 正在分析原声轨道基频判断性别: {vocal_wav.name}")
    try:
        y, sr = librosa.load(str(vocal_wav), sr=22050, mono=True, duration=100)
        f0, voiced_flag, _ = librosa.pyin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C6'), sr=sr)
        voiced_f0 = f0[voiced_flag & ~np.isnan(f0)]
        
        if len(voiced_f0) < 100:
            print("⚠️ 有效语音片段不足，智能检测失败，回退到默认女性 (晓晓微调版)")
            return VOICE_MAPPING["female"]
            
        median_f0 = float(np.median(voiced_f0))
        print(f"🎵 检测到中立基频: {median_f0:.1f}Hz")
        
        gender = "female" if median_f0 > 160 else "male"
        voice_info = VOICE_MAPPING[gender]
        
        print(f"✅ 性别判断完成: {gender.upper()}，自动分配最强配音员: {voice_info['description']}")
        return voice_info
        
    except Exception as e:
        print(f"⚠️ 智能基频检测失败 ({e})，回退到默认女性 (晓晓微调版)")
        return VOICE_MAPPING["female"]

def parse_srt(file_path: Path):
    lines = file_path.read_text(encoding="utf-8").strip().split('\n\n')
    blocks = []
    for block in lines:
        parts = block.split('\n', 2)
        if len(parts) >= 3:
            blocks.append({
                "index": parts[0],
                "text": parts[2].replace('\n', ' ')
            })
    return blocks

async def generate_audio(text, voice, rate, pitch, output_path, proxy):
    communicate = edge_tts.Communicate(
        text,
        voice,
        rate=rate,
        pitch=pitch,
        volume="+0%",
        proxy=proxy
    )
    await communicate.save(str(output_path))

async def process_batch(blocks, tts_dir, voice_info, proxy):
    total = len(blocks)
    for i, b in enumerate(blocks):
        idx = b['index'].zfill(3)
        out_file = tts_dir / f"{idx}.mp3"

        print(f"⏳ [{i+1}/{total}] 正在使用 {voice_info['description']} 渲染第 {idx} 句...")
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                await asyncio.wait_for(generate_audio(b['text'], voice_info['voice'], voice_info['rate'], voice_info['pitch'], out_file, proxy), timeout=25.0)
                break
            except Exception as e:
                if attempt == max_retries:
                    print(f"❌ 句子 {idx} 本地Edge-TTS生成失败: {e}")
                    sys.exit(1)
                import time
                time.sleep(1)

def main():
    args = setup_argparse()
    work_dir = Path(args.work_dir).resolve()

    trans_srt = work_dir / "trans.srt"
    vocal_wav = work_dir / "demucs/htdemucs/audio/vocals.wav"
    if not vocal_wav.exists():
        vocal_wav = work_dir / "audio.wav"

    tts_dir = work_dir / "tts_clips"
    tts_dir.mkdir(exist_ok=True)

    if not trans_srt.exists():
        print("❌ 错误: 未找到翻译后的SRT字幕 trans.srt")
        sys.exit(1)

    target_voice_info = detect_gender(vocal_wav) if vocal_wav.exists() else VOICE_MAPPING["female"]

    blocks = parse_srt(trans_srt)
    print(f"🚀 开始智能配音爆破合成 (共 {len(blocks)} 句)...")
    asyncio.run(process_batch(blocks, tts_dir, target_voice_info, args.proxy))
    print(f"🎉 🎉 🎉 全部碎片段配音安全、高效地爆发生成！存放于: {tts_dir}")

if __name__ == "__main__":
    main()
