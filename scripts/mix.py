#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import json
import shutil
from pathlib import Path
import numpy as np
import soundfile as sf

def setup_argparse():
    parser = argparse.ArgumentParser(description="Step 5: Dynamic Stereo Mix & Auto Sync to Windows")
    parser.add_argument("--work-dir", type=str, required=True, help="Path to working directory")
    return parser.parse_args()

def get_video_info(video_path: Path):
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(video_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    duration = float(data["format"]["duration"])
    width, height = 1920, 1080
    for stream in data["streams"]:
        if stream["codec_type"] == "video":
            width = int(stream["width"])
            height = int(stream["height"])
            break
    return duration, width, height

def parse_srt(file_path: Path):
    lines = file_path.read_text(encoding="utf-8").strip().split('\n\n')
    blocks = []
    def to_seconds(t_str):
        h, m, s = t_str.strip().split(':')
        s, ms = s.split(',')
        return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000.0
    for block in lines:
        if not block.strip(): continue
        parts = block.split('\n', 2)
        if len(parts) >= 3:
            time_parts = parts[1].split('-->')
            blocks.append({
                "index": parts[0].strip(),
                "start": to_seconds(time_parts[0]),
                "end": to_seconds(time_parts[1]),
                "text": parts[2].replace('\n', ' ')
            })
    return blocks

def main():
    args = setup_argparse()
    work_dir = Path(args.work_dir).resolve()

    input_video = work_dir / "video.mp4"
    bgm_wav = work_dir / "bgm.wav"
    trans_srt = work_dir / "trans.srt"
    tts_dir = work_dir / "tts_clips"

    vocal_dub_wav = work_dir / "vocal_dub.wav"
    final_audio_wav = work_dir / "final_mixed_audio.wav"
    output_video = work_dir / "output_dub.mp4"
    done_marker = work_dir / ".done_mix"

    win_download_dir = Path("/mnt/c/Users/Xia20/Downloads")
    dest_filename = f"{work_dir.name}_dub.mp4"
    win_final_output = win_download_dir / dest_filename

    if done_marker.exists() and output_video.exists():
        print(f"✅ [跳过] 发现成品视频。")
        if win_download_dir.exists() and not win_final_output.exists():
            print(f"🚚 补充同步至 Windows 下载文件夹: {win_final_output}")
            shutil.copy2(output_video, win_final_output)
        return

    print("🚀 开始最终阶段的硬核自适应对口型混音合成...")
    video_duration, width, height = get_video_info(input_video)
    srt_blocks = parse_srt(trans_srt)

    sample_rate = 44100
    total_samples = int(video_duration * sample_rate) + sample_rate
    master_vocal = np.zeros((total_samples, 2), dtype=np.float32)

    print("⏳ 正在计算动态伸缩时间轴，全力防止语音悬空与重叠混响...")
    
    for idx_info, b in enumerate(srt_blocks):
        idx = b['index'].zfill(3)
        start_time = b['start']
        end_time = b['end']
        
        if idx_info < len(srt_blocks) - 1:
            next_start = srt_blocks[idx_info + 1]['start']
            if next_start < start_time: 
                next_start = start_time + 0.3
            target_dur = next_start - start_time
        else:
            target_dur = end_time - start_time
            
        target_dur = max(target_dur, 0.2)

        clip_path = tts_dir / f"{idx}.mp3"
        if not clip_path.exists(): continue

        clip_info = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(clip_path)],
            capture_output=True, text=True, check=True
        )
        clip_dur = float(json.loads(clip_info.stdout)["format"]["duration"])
        temp_wav = work_dir / f"temp_{idx}.wav"

        if clip_dur > target_dur:
            speed = min(clip_dur / target_dur, 2.5)
            filter_str = f"atempo={speed:.4f},pan=stereo|c0=c0|c1=c0,aresample={sample_rate}"
        elif clip_dur < target_dur * 0.75:
            speed = max(clip_dur / target_dur, 0.85)
            filter_str = f"atempo={speed:.4f},pan=stereo|c0=c0|c1=c0,aresample={sample_rate}"
        else:
            filter_str = f"pan=stereo|c0=c0|c1=c0,aresample={sample_rate}"

        subprocess.run([
            "ffmpeg", "-y", "-i", str(clip_path),
            "-af", filter_str, "-c:a", "pcm_s16le", str(temp_wav)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        audio_data, sr = sf.read(str(temp_wav))
        temp_wav.unlink()

        start_idx = int(start_time * sample_rate)
        
        max_allowed_samples = int(target_dur * sample_rate)
        if len(audio_data) > max_allowed_samples:
            audio_data = audio_data[:max_allowed_samples]

        end_idx = start_idx + len(audio_data)

        if end_idx > total_samples:
            audio_data = audio_data[:total_samples - start_idx]
            end_idx = total_samples

        master_vocal[start_idx:end_idx] = audio_data[:end_idx - start_idx]

    sf.write(str(vocal_dub_wav), master_vocal, sample_rate)
    print("✅ 纯净不重叠的中文配音母轨就绪。")

    if not bgm_wav.exists():
        subprocess.run(["ffmpeg", "-y", "-i", str(input_video), "-vn", "-acodec", "pcm_s16le", str(bgm_wav)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    duck_filter = "[1:a]asplit=2[sc][vocal];[0:a][sc]sidechaincompress=threshold=0.15:ratio=4:attack=20:release=200[bgm_ducked];[bgm_ducked][vocal]amix=inputs=2:duration=first[aout]"

    subprocess.run([
        "ffmpeg", "-y", "-i", str(bgm_wav), "-i", str(vocal_dub_wav),
        "-filter_complex", duck_filter, "-map", "[aout]",
        "-c:a", "pcm_s16le", str(final_audio_wav)
    ], check=True, stdout=subprocess.DEVNULL, stderr=sys.stderr)
    print("✅ 智能闪避立体声合并完毕。")

    print("⏳ 正在去重并硬烧录多行整齐字幕...")
    escaped_srt = str(trans_srt).replace("\\", "/").replace(":", "\\:")
    subtitle_style = "FontName=Noto Sans CJK SC,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,Bold=1,Outline=2,Shadow=1,Alignment=2,MarginV=30"

    vf_chain = (
        f"crop=iw*0.98:ih*0.98:iw*0.01:ih*0.01,"
        f"scale={width}:{height},"
        f"eq=brightness=0.01:contrast=1.02,"
        f"subtitles='{escaped_srt}':force_style='{subtitle_style}'"
    )

    # 关键修复点：去掉了 "-c:v" 前面的空格
    cmd_video = [
        "ffmpeg", "-y", "-i", str(input_video), "-i", str(final_audio_wav),
        "-vf", vf_chain, "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(output_video)
    ]

    subprocess.run(cmd_video, check=True, stdout=subprocess.DEVNULL, stderr=sys.stderr)

    if vocal_dub_wav.exists(): vocal_dub_wav.unlink()
    if final_audio_wav.exists(): final_audio_wav.unlink()

    done_marker.touch()
    print(f"🎉 本地视频完美渲染完成！")

    if win_download_dir.exists():
        try:
            print(f"🚚 正在跨系统同步至 Windows 下载文件夹: {win_final_output}")
            shutil.copy2(output_video, win_final_output)
            print("✨ 【双系统闭环】大功告成！你现在可以直接在 Windows 的‘下载’文件夹中使用了！")
        except Exception as e:
            print(f"⚠️ 跨系统复制失败，请检查 Windows 权限或路径: {e}")
    else:
        print(f"⚠️ 未找到 Windows 下载目录 /mnt/c/Users/Xia20/Downloads")

if __name__ == "__main__":
    main()
