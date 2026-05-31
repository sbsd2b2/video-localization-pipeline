#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
from pathlib import Path

def setup_argparse():
    parser = argparse.ArgumentParser(description="Step 1: Download Video via yt-dlp")
    parser.add_argument("--work-dir", type=str, required=True, help="Path to working directory")
    parser.add_argument("--url", type=str, required=True, help="Target video URL")
    parser.add_argument("--proxy", type=str, default="http://127.0.0.1:7890", help="Proxy address")
    return parser.parse_args()

def main():
    args = setup_argparse()
    work_dir = Path(args.work_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    
    output_video = work_dir / "video.mp4"
    done_marker = work_dir / ".done_download"

    if done_marker.exists() and output_video.exists():
        print(f"✅ [跳过] 发现标记文件，视频已存在。")
        return

    print(f"🚀 开始高清匿名下载 (依赖 WARP 节点): {args.url}")
    
    cmd = [
        "yt-dlp",
        "--proxy", args.proxy,
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "-o", str(output_video),
    ]
    cmd.append(args.url)

    try:
        subprocess.run(cmd, check=True, text=True, stdout=sys.stdout, stderr=sys.stderr)
        if output_video.exists():
            done_marker.touch()
            print(f"\n✅ 下载完成！输出至: {output_video}")
        else:
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ yt-dlp 进程退出异常，错误码: {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    main()
