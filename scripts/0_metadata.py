#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import json
import yaml
from pathlib import Path

def setup_argparse():
    parser = argparse.ArgumentParser(description="Step 0: Pre-fetch & Generate Metadata & Thumbnail")
    parser.add_argument("--work-dir", type=str, required=True, help="Path to working directory")
    parser.add_argument("--url", type=str, required=True, help="Target video URL")
    parser.add_argument("--proxy", type=str, default="http://127.0.0.1:7890", help="Proxy address")
    return parser.parse_args()

def generate_original_metadata(original_title, original_desc, prompt_template):
    # 预留给 Gemini 2.5 Flash 生成原创简介和标题的函数
    # 稍后集成真正的 Gemini API 时修改此处
    try:
        return {
            "title_original": original_title,
            "title_localized": f"【AI编程革命】{original_title} (原创重写版)",
            "description_original": original_desc,
            "description_localized": f"大家好，我是夏郎。本期视频，我们深入剖析最新的 AI 编程工具。\n\n我们将深入探讨... \n\n#AI编程 #代码助手 #技术解析",
            "tags": "AI编程,代码助手,技术解析,编程工具,软件开发,程序员必看"
        }
    except Exception as e:
        print(f"❌ 大模型处理简介生成失败: {e}")
        return None

def main():
    args = setup_argparse()
    work_dir = Path(args.work_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    done_marker = work_dir / ".done_metadata"
    meta_file = work_dir / "meta_orig.json"
    meta_final_file = work_dir / "meta_final.json"
    thumbnail_file = work_dir / "thumbnail.jpg"

    if done_marker.exists() and meta_final_file.exists():
        print(f"✅ [跳过] 发现标记文件，元数据和封面已完成。")
        return

    print(f"🚀 开始爬取原始元数据: {args.url}")

    cmd = [
        "yt-dlp",
        "--proxy", args.proxy,
        "--skip-download", 
        "--write-thumbnail",
        "--print-json", 
        "-o", f"{work_dir}/thumbnail.%(ext)s",
        args.url
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8")
        raw_meta = json.loads(result.stdout)
        
        orig_meta = {
            "title": raw_meta.get("title", ""),
            "description": raw_meta.get("description", ""),
            "tags": raw_meta.get("tags", []),
            "thumbnail_url": raw_meta.get("thumbnail", "")
        }
        meta_file.write_text(json.dumps(orig_meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 爬取到原始信息，保存在: {meta_file}")

        temp_webps = list(work_dir.glob("thumbnail.*"))
        if temp_webps:
            temp_webp = temp_webps[0]
            if temp_webp.suffix != ".jpg":
                print(f"⏳ 正在将原视频封面从 {temp_webp.suffix} 转为 jpg...")
                subprocess.run(["ffmpeg", "-y", "-i", str(temp_webp), str(thumbnail_file)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                temp_webp.unlink()
                print(f"✅ 静态封面已就绪: {thumbnail_file}")
            else:
                print(f"✅ 静态封面已就绪: {thumbnail_file}")

    except (subprocess.CalledProcessError, json.JSONDecodeError, IndexError) as e:
        print(f"\n❌ yt-dlp 爬取原视频元数据或封面失败: {e}")
        sys.exit(1)

    print(f"⏳ 正在请求大模型生成原创简介和标签...")
    
    PROMPT_TEMPLATE = """
    你是一个精通AI科技前沿动态的专业视频解说博主。请根据以下原始视频信息，利用你的网感语调和专业知识，生成完全原创的、适合B站博主的标题和简介文案。

    原始标题: {original_title}
    原始简介: {original_desc}
    """
    
    generated_meta = generate_original_metadata(orig_meta["title"], orig_meta["description"], PROMPT_TEMPLATE)
    
    if generated_meta:
        orig_meta.update(generated_meta)
        meta_final_file.write_text(json.dumps(orig_meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"🎉 🎉 🎉 元数据原创重写完成，并与封面一起存储在: {work_dir}")
        done_marker.touch()
    else:
        print(f"⚠️ 大模型原创重写简介失败，请检查 API 配置或手动完成该步骤。")

if __name__ == "__main__":
    main()
