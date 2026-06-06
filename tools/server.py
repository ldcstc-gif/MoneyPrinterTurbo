"""
server.py — HTTP 上传服务
Tasker 上传图片 → 分析 → 推送回手机
"""
import os
import uuid
from pathlib import Path

import yaml
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from analyze import analyze_image
from notify import send_result

app = FastAPI(title="Camera AI Server")
UPLOAD_DIR = Path("/tmp/camera-ai-uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    cfg_path = Path(__file__).parent / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    x_token: str = Header(default=""),
):
    cfg = load_config()

    # 鉴权
    if x_token != cfg.get("upload_token", ""):
        raise HTTPException(status_code=401, detail="Invalid token")

    # 保存图片
    suffix = Path(file.filename or "img.jpg").suffix or ".jpg"
    save_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    content = await file.read()
    save_path.write_bytes(content)

    try:
        # 分析图片
        print(f"[分析] {save_path}")
        result = analyze_image(str(save_path))
        print(f"[结果] {result[:100]}...")

        # 推送回手机
        send_result(result)

        return JSONResponse({"status": "ok", "result": result})

    except Exception as e:
        print(f"[错误] {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 分析完删除临时图片
        save_path.unlink(missing_ok=True)


@app.get("/config/model")
def get_model():
    cfg = load_config()
    return {"model": cfg["vision"]["model"]}


@app.put("/config/model/{model_name}")
def set_model(model_name: str, x_token: str = Header(default="")):
    cfg = load_config()
    if x_token != cfg.get("upload_token", ""):
        raise HTTPException(status_code=401, detail="Invalid token")

    allowed = ["qwen-vl-max", "qwen-vl-plus", "qwen-vl-ocr"]
    if model_name not in allowed:
        raise HTTPException(status_code=400, detail=f"允许的模型: {allowed}")

    # 更新配置文件
    cfg_path = Path(__file__).parent / "config.yaml"
    text = cfg_path.read_text()
    import re
    text = re.sub(r'(model:\s*")[^"]*(")', f'\\g<1>{model_name}\\g<2>', text)
    cfg_path.write_text(text)

    return {"status": "ok", "model": model_name}


if __name__ == "__main__":
    import uvicorn
    cfg = load_config()
    uvicorn.run(app, host="0.0.0.0", port=cfg["server_port"])
