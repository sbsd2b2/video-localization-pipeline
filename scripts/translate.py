#!/usr/bin/env python3
import os
import sys
import argparse
import yaml
import json
from pathlib import Path
from openai import OpenAI

TERM_FIXES = {
    "cloud co-work": "Claude Co-work",
    "cloud code": "Claude Code",
    "Cloud": "Claude",
    "opuis": "Opus",
    "氛围编程": "Vibe Coding",
    "氛围代码": "Vibe Coding",
    "直觉编程": "Vibe Coding",
}

def setup_argparse():
    parser = argparse.ArgumentParser(description="Step 3: Secure DeepSeek V3 JSON Translate & Smart Auto-Wrap")
    parser.add_argument("--work-dir", type=str, required=True)
    return parser.parse_args()

def get_api_key():
    config_path = Path.home() / "VideoLingo/config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("api", {}).get("key")

def parse_src_srt(file_path: Path):
    """解析原始SRT，将文本和时间结构安全剥离"""
    lines = file_path.read_text(encoding="utf-8").strip().split('\n\n')
    blocks = []
    for block in lines:
        if not block.strip(): continue
        parts = block.split('\n', 2)
        if len(parts) >= 3:
            blocks.append({
                "index": parts[0].strip(),
                "time": parts[1].strip(),
                "text": parts[2].replace('\n', ' ').strip()
            })
    return blocks

def smart_wrap(text, max_len=22):
    """智能中文字幕换行算法，避免超长单行冲出屏幕"""
    if len(text) <= max_len:
        return text
    mid = len(text) // 2
    # 尝试在中间位置寻找标点符号进行自然换行
    for i in range(0, min(6, mid)):
        if text[mid-i] in [',', '，', ' ', '。', '！', '!', '？', '?']:
            return text[:mid-i+1].strip() + "\n" + text[mid-i+1:].strip()
        if text[mid+i] in [',', '，', ' ', '。', '！', '!', '？', '?']:
            return text[:mid+i+1].strip() + "\n" + text[mid+i+1:].strip()
    # 若无标点，硬性正中切开
    return text[:mid].strip() + "\n" + text[mid:].strip()

def apply_term_fixes(text: str) -> str:
    for wrong, correct in TERM_FIXES.items():
        text = text.replace(wrong, correct)
    return text

def main():
    args = setup_argparse()
    work_dir = Path(args.work_dir).resolve()
    src_srt = work_dir / "src.srt"
    trans_srt = work_dir / "trans.srt"

    if trans_srt.exists():
        print(f"✅ [跳过] 发现 trans.srt，翻译已完成。")
        return

    api_key = get_api_key()
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    # 读取原有SRT结构
    srt_blocks = parse_src_srt(src_srt)
    if not srt_blocks:
        print("❌ 错误: src.srt 为空或解析失败")
        sys.exit(1)

    # 分批处理文本，每批 15 句，改用稳健的纯数据 JSON 交互
    batch_size = 15
    batches = [srt_blocks[i:i + batch_size] for i in range(0, len(srt_blocks), batch_size)]

    print(f"🚀 开始 DeepSeek V3 安全隔离时间轴翻译机制 (共 {len(batches)} 个批次)...")
    
    translated_map = {}

    for i, batch in enumerate(batches):
        print(f"⏳ 正在安全翻译 Batch {i+1}/{len(batches)}...")
        
        # 构建隔离时间轴的纯文本JSON载荷
        payload = {"segments": [{"id": b["index"], "text": b["text"]} for b in batch]}
        
        user_prompt = f"请将以下科技解说字幕文本数组翻译为流畅、口语化、具有B站科技UP主网感的中文。请必须保持数组结构和id完全对应，绝不允许合并、遗漏或拆分任何句子！\n特别要求：严禁过度压缩文本，保持与原英文句相当的信息量、细节和口播长度，以便后续配音对齐视频主口型！\n\n待翻译JSON数据：\n{json.dumps(payload, ensure_ascii=False)}"

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个精通AI科技前沿动态的专业B站解说UP主。你必须以合法的 JSON 格式做出响应，格式与输入的JSON载荷完全一致。"},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            res_data = json.loads(response.choices[0].message.content.strip())
            for seg in res_data.get("segments", []):
                seg_id = str(seg.get("id"))
                clean_txt = apply_term_fixes(seg.get("text", "").strip())
                # 落地前执行智能换行保护
                translated_map[seg_id] = smart_wrap(clean_txt)
                
        except Exception as e:
            print(f"❌ Batch {i+1} 翻译遭遇异常: {e}，触发熔断兜底。")
            sys.exit(1)

    # 核心：使用原始最纯净的时间轴，强行组装中文SRT，杜绝任何重叠与幻觉
    final_output = []
    for b in srt_blocks:
        idx = b["index"]
        trans_txt = translated_map.get(idx, b["text"]) # 如果漏掉则回退原英文防止崩溃
        final_output.append(f"{idx}\n{b['time']}\n{trans_txt}")

    trans_srt.write_text("\n\n".join(final_output), encoding="utf-8")
    print(f"🎉 翻译与全自动换行规整完成！安全输出至: {trans_srt}")

if __name__ == "__main__":
    main()
