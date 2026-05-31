#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import gc
from pathlib import Path

def setup_argparse():
    parser = argparse.ArgumentParser(description="Step 2: Audio Separation and Transcription")
    parser.add_argument("--work-dir", type=str, required=True, help="Path to working directory")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size for WhisperX")
    return parser.parse_args()

def write_srt(result, save_path: Path):
    with open(save_path, "w", encoding="utf-8") as f:
        for index, segment in enumerate(result["segments"]):
            start = segment["start"]
            end = segment["end"]
            text = segment["text"].strip()
            def fmt(sec: float):
                return f"{int(sec//3600):02d}:{int((sec%3600)//60):02d}:{int(sec%60):02d},{int((sec-int(sec))*1000):03d}"
            f.write(f"{index + 1}\n{fmt(start)} --> {fmt(end)}\n{text}\n\n")

def main():
    args = setup_argparse()
    work_dir = Path(args.work_dir).resolve()
    
    input_video = work_dir / "video.mp4"
    done_marker = work_dir / ".done_transcribe"
    audio_wav = work_dir / "audio.wav"
    demucs_out = work_dir / "demucs" / "htdemucs" / "audio"
    vocal_wav = demucs_out / "vocals.wav"
    bgm_wav = demucs_out / "no_vocals.wav"
    src_srt = work_dir / "src.srt"

    if done_marker.exists() and src_srt.exists():
        print(f"✅ [跳过] 发现标记文件，转写已完成。")
        return

    if not input_video.exists():
        print(f"❌ 错误: 未找到输入视频 {input_video}")
        sys.exit(1)

    print(f"🚀 开始提取音频...")
    if not audio_wav.exists():
        subprocess.run(["ffmpeg", "-y", "-i", str(input_video), "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", str(audio_wav)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if not vocal_wav.exists():
        print("⏳ 调用 Demucs 分离人声...")
        subprocess.run(["demucs", "-n", "htdemucs", "--two-stems", "vocals", "-o", str(work_dir / "demucs"), str(audio_wav)], check=True)
        print("✅ Demucs 分离完成。")

    import whisperx
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"⏳ 加载 WhisperX 到 {device}...")
    model = whisperx.load_model("large-v2", device, compute_type="float16" if device=="cuda" else "int8")
    
    audio = whisperx.load_audio(str(vocal_wav))
    result = model.transcribe(audio, batch_size=args.batch_size)
    lang = result["language"]
    
    del model; gc.collect(); torch.cuda.empty_cache()

    print("⏳ 加载对齐模型...")
    model_a, metadata = whisperx.load_align_model(language_code=lang, device=device)
    result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
    
    write_srt(result, src_srt)
    del model_a; gc.collect(); torch.cuda.empty_cache()

    if bgm_wav.exists(): bgm_wav.rename(work_dir / "bgm.wav")
    done_marker.touch()
    print(f"🎉 转写完成: {src_srt}")

if __name__ == "__main__":
    main()
