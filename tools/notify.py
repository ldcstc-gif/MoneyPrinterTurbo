"""
notify.py — TTS 生成 + ntfy 推送
"""
import asyncio
import os
from pathlib import Path

import edge_tts
import httpx
import yaml


def load_config() -> dict:
    cfg_path = Path(__file__).parent / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


async def text_to_speech(text: str, output_path: str, voice: str) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def push_notification(text: str, audio_path: str | None = None) -> bool:
    cfg = load_config()
    n = cfg["ntfy"]
    url = f"{n['server']}/{n['topic']}"

    if audio_path and n.get("send_audio") and os.path.isfile(audio_path):
        # 上传音频文件到 ntfy（作为附件）
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        resp = httpx.put(
            url,
            content=audio_data,
            headers={
                "Title": "📷 运动相机分析",
                "Message": text[:200],  # ntfy 标题限长
                "Filename": "analysis.mp3",
                "Content-Type": "audio/mpeg",
                "Priority": "default",
            },
            timeout=30,
        )
    else:
        # 纯文字推送
        resp = httpx.post(
            url,
            data=text.encode("utf-8"),
            headers={
                "Title": "📷 运动相机分析",
                "Priority": "default",
            },
            timeout=30,
        )

    return resp.status_code == 200


def send_result(text: str) -> None:
    cfg = load_config()
    t = cfg["tts"]

    audio_dir = Path(t["output_dir"])
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = str(audio_dir / "latest.mp3")

    # 生成语音
    try:
        asyncio.run(text_to_speech(text, audio_path, t["voice"]))
    except Exception as e:
        print(f"[TTS 失败] {e}，将只发送文字")
        audio_path = None

    # 推送
    ok = push_notification(text, audio_path)
    print(f"[推送] {'成功' if ok else '失败'}: {text[:80]}...")
