"""
analyze.py — 图片分析核心
可单独调用: python analyze.py /path/to/image.jpg
"""
import base64
import sys
from pathlib import Path

import httpx
import yaml


def load_config() -> dict:
    cfg_path = Path(__file__).parent / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_image(image_path: str) -> str:
    cfg = load_config()
    v = cfg["vision"]

    # 获取图片 MIME 类型
    suffix = Path(image_path).suffix.lower()
    mime = {"jpg": "image/jpeg", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp"}.get(suffix, "image/jpeg")

    b64 = encode_image(image_path)

    payload = {
        "model": v["model"],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    {"type": "text", "text": v["prompt"]},
                ],
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {v['api_key']}",
        "Content-Type": "application/json",
    }

    resp = httpx.post(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        json=payload,
        headers=headers,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python analyze.py <图片路径>")
        sys.exit(1)
    result = analyze_image(sys.argv[1])
    print(result)
