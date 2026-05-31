#!/usr/bin/env python3
import asyncio
import argparse
import sys
from pathlib import Path
import edge_tts
import librosa
import numpy as np

def setup_argparse():
    parser = argparse.ArgumentParser(description="Step 4: Smart Gender Detect & Edge-TTS (Multilingual Edition)")
    parser.add_argument("--work-dir", type=str, required=True, help="Path to working directory")
    parser.add_argument("--proxy", type=str, default="http://127.0.0.1:7890", help="Proxy address")
    return parser.parse_args()

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

def detect_voice(audio_path: Path) -> str:
    print("⏳ 正在分析原视频基频，智能检测解说员性别...")
    try:
        y, sr = librosa.load(str(audio_path), sr=22050, mono=True, duration=60)
        f0, voiced_flag, _ = librosa.pyin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C6'), sr=sr)
        voiced_f0 = f0[voiced_flag & ~np.isnan(f0)]
        if len(voiced_f0) < 100:
            return "zh-CN-YunxiaoMultilingualNeural"
        median_f0 = float(np.median(voiced_f0))
        if median_f0 >= 170:
            print(f"🎵 检测到高基频 ({median_f0:.1f}Hz)，自动分配微软全新女声: 晓晓多语言")
            return "zh-CN-XiaoxiaoMultilingualNeural"
        else:
            print(f"🎵 检测到低基频 ({median_f0:.1f}Hz)，自动分配微软全新男声: 云霄多语言")
            return "zh-CN-YunxiaoMultilingualNeural"
    except Exception as e:
        print(f"⚠️ 基频检测失败 ({e})，回退到默认男声 (云霄)")
        return "zh-CN-YunxiaoMultilingualNeural"

async def generate_audio(text, voice, output_path, proxy):
    communicate = edge_tts.Communicate(text, voice, proxy=proxy)
    await communicate.save(str(output_path))

async def process_batch(blocks, tts_dir, voice, proxy):
    total = len(blocks)
    for i, b in enumerate(blocks):
        idx = b['index'].zfill(3)
        out_file = tts_dir / f"{idx}.mp3"
        
        # 为了测试新音色的完整效果，我们不跳过，直接强制覆盖旧的配音文件
        print(f"⏳ [{i+1}/{total}] 正在使用 {voice} 生成配音...")
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                await asyncio.wait_for(generate_audio(b['text'], voice, out_file, proxy), timeout=20.0)
                break
            except Exception as e:
                if attempt == max_retries:
                    print(f"❌ 句子 {idx} 生成失败: {e}")
                    sys.exit(1)
                print(f"⚠️ [超时] 第 {attempt} 次生成失败，触发熔断，2秒后重试...")
                await asyncio.sleep(2)

def main():
    args = setup_argparse()
    work_dir = Path(args.work_dir).resolve()

    trans_srt = work_dir / "trans.srt"
    bgm_wav = work_dir / "bgm.wav"
    tts_dir = work_dir / "tts_clips"
    tts_dir.mkdir(exist_ok=True)

    if not trans_srt.exists():
        print("❌ 错误: 未找到 trans.srt")
        sys.exit(1)

    # 智能判断声音
    target_voice = detect_voice(bgm_wav) if bgm_wav.exists() else "zh-CN-YunxiaoMultilingualNeural"

    blocks = parse_srt(trans_srt)
    print(f"🚀 开始 Edge-TTS 多语言版配音 (共 {len(blocks)} 句)...")
    asyncio.run(process_batch(blocks, tts_dir, target_voice, args.proxy))
    print(f"🎉 新配音全部替换完成！存放于: {tts_dir}")

if __name__ == "__main__":
    main()
