#!/usr/bin/env python3
import argparse
import sys
import os
import requests
from pathlib import Path

SOVITS_API_URL = "http://127.0.0.1:9880"

def setup_argparse():
    parser = argparse.ArgumentParser(description="Step 4: Auto-Ref GPT-SoVITS v2 Pipeline")
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

def generate_sovits_audio(text, ref_audio_path, output_path):
    # 构建严谨的 GPT-SoVITS 必须参数，不带任何空字段
    params = {
        "text": text,
        "text_lang": "zh",
        "ref_audio_path": str(ref_audio_path),
        "prompt_text": "vibe coding",  # 拿原片第一句的关键词作为冷启动引导提示词
        "prompt_lang": "en"            # 原片是英文，所以提示词语言设为 en
    }
    response = requests.get(SOVITS_API_URL, params=params, timeout=40)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
    else:
        raise RuntimeError(f"SoVITS服务端抛出异常，HTTP状态码: {response.status_code}")

def main():
    args = setup_argparse()
    work_dir = Path(args.work_dir).resolve()

    trans_srt = work_dir / "trans.srt"
    tts_dir = work_dir / "tts_clips"
    tts_dir.mkdir(exist_ok=True)

    if not trans_srt.exists():
        print("❌ 错误: 未找到 trans.srt")
        sys.exit(1)

    # 动态就地取材：优先找你工作目录下的纯人声轨，如果没有，就用降噪前的原始音轨
    ref_audio = work_dir / "vocal.wav"
    if not ref_audio.exists():
        ref_audio = work_dir / "audio.wav"
    if not ref_audio.exists():
        # 如果还是没有，遍历工作区找任意一个现成的 wav 作为 API 的“药引子”
        wav_files = list(work_dir.glob("*.wav"))
        if wav_files:
            ref_audio = wav_files[0]
        else:
            print("❌ 错误: 在工作目录下未找到任何可以作为参考的 .wav 音频文件！")
            sys.exit(1)

    print(f"🎯 成功锁定本地闭环参考音频: {ref_audio.name}")

    blocks = parse_srt(trans_srt)
    total = len(blocks)
    
    print(f"🚀 开始 GPT-SoVITS v2 闭环批量配音 (共 {total} 句)...")
    
    for i, b in enumerate(blocks):
        idx = b['index'].zfill(3)
        out_file = tts_dir / f"{idx}.mp3"
        
        if out_file.exists() and out_file.stat().st_size > 5000:
            continue

        print(f"⏳ [{i+1}/{total}] GPT-SoVITS 正在合成 -> 句子 {idx}")
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                generate_sovits_audio(b['text'], ref_audio, out_file)
                break
            except Exception as e:
                if attempt == max_retries:
                    print(f"❌ 句子 {idx} 本地SoVITS生成最终失败: {e}")
                    sys.exit(1)
                import time
                time.sleep(1)

    print(f"🎉 GPT-SoVITS 配音全部清洗完成！无缝存放于: {tts_dir}")

if __name__ == "__main__":
    main()
