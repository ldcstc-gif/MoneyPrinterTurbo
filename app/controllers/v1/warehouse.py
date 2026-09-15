import json
import os
import pathlib

from fastapi import Path, Query, Request
from fastapi.responses import FileResponse, StreamingResponse

from app.controllers import base
from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.utils import utils

router = new_router()


@router.get("/warehouse", summary="Get warehouse video list")
def get_warehouse_list(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
):
    warehouse = utils.warehouse_dir()
    videos = []
    for f in sorted(os.listdir(warehouse), reverse=True):
        if f.endswith(".json"):
            continue
        file_path = os.path.join(warehouse, f)
        if not os.path.isfile(file_path):
            continue

        meta = {}
        meta_path = file_path + ".json"
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as mf:
                    meta = json.load(mf)
            except Exception:
                pass

        videos.append(
            {
                "file_name": f,
                "size": os.path.getsize(file_path),
                "created_at": meta.get("created_at", int(os.path.getmtime(file_path))),
                "video_subject": meta.get("video_subject", ""),
                "video_script": meta.get("video_script", ""),
                "video_aspect": meta.get("video_aspect", ""),
                "task_id": meta.get("task_id", ""),
            }
        )

    total = len(videos)
    start = (page - 1) * page_size
    end = start + page_size
    response = {
        "videos": videos[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return utils.get_response(200, response)


@router.delete("/warehouse/{file_name}", summary="Delete a video from warehouse")
def delete_warehouse_video(
    request: Request,
    file_name: str = Path(..., description="Video file name"),
):
    request_id = base.get_task_id(request)
    warehouse = utils.warehouse_dir()

    safe_name = os.path.basename(file_name)
    file_path = os.path.join(warehouse, safe_name)
    real_path = os.path.realpath(file_path)
    if not real_path.startswith(os.path.realpath(warehouse) + os.sep):
        raise HttpException(
            task_id="",
            status_code=403,
            message=f"{request_id}: access forbidden",
        )

    if not os.path.isfile(real_path):
        raise HttpException(
            task_id="",
            status_code=404,
            message=f"{request_id}: file not found",
        )

    os.remove(real_path)
    meta_path = real_path + ".json"
    if os.path.exists(meta_path):
        os.remove(meta_path)

    return utils.get_response(200)


@router.get("/warehouse/stream/{file_name}", summary="Stream a warehouse video")
async def stream_warehouse_video(
    request: Request,
    file_name: str = Path(..., description="Video file name"),
):
    request_id = base.get_task_id(request)
    warehouse = utils.warehouse_dir()

    safe_name = os.path.basename(file_name)
    file_path = os.path.join(warehouse, safe_name)
    real_path = os.path.realpath(file_path)
    if not real_path.startswith(os.path.realpath(warehouse) + os.sep):
        raise HttpException(
            task_id="", status_code=403, message=f"{request_id}: access forbidden"
        )
    if not os.path.isfile(real_path):
        raise HttpException(
            task_id="", status_code=404, message=f"{request_id}: file not found"
        )

    video_size = os.path.getsize(real_path)
    range_header = request.headers.get("Range")
    start, end = 0, video_size - 1
    length = video_size

    if range_header:
        range_ = range_header.split("bytes=")[1]
        start, end = [int(part) if part else None for part in range_.split("-")]
        if start is None:
            start = video_size - end
            end = video_size - 1
        if end is None:
            end = video_size - 1
        length = end - start + 1

    def file_iterator(fp, offset=0, bytes_to_read=None):
        with open(fp, "rb") as f:
            f.seek(offset, os.SEEK_SET)
            remaining = bytes_to_read or video_size
            while remaining > 0:
                chunk = min(4096, remaining)
                data = f.read(chunk)
                if not data:
                    break
                remaining -= len(data)
                yield data

    response = StreamingResponse(
        file_iterator(real_path, start, length), media_type="video/mp4"
    )
    response.headers["Content-Range"] = f"bytes {start}-{end}/{video_size}"
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Content-Length"] = str(length)
    response.status_code = 206
    return response


@router.get("/warehouse/download/{file_name}", summary="Download a warehouse video")
async def download_warehouse_video(
    request: Request,
    file_name: str = Path(..., description="Video file name"),
):
    request_id = base.get_task_id(request)
    warehouse = utils.warehouse_dir()

    safe_name = os.path.basename(file_name)
    file_path = os.path.join(warehouse, safe_name)
    real_path = os.path.realpath(file_path)
    if not real_path.startswith(os.path.realpath(warehouse) + os.sep):
        raise HttpException(
            task_id="", status_code=403, message=f"{request_id}: access forbidden"
        )
    if not os.path.isfile(real_path):
        raise HttpException(
            task_id="", status_code=404, message=f"{request_id}: file not found"
        )

    p = pathlib.Path(real_path)
    return FileResponse(
        path=real_path,
        headers={"Content-Disposition": f"attachment; filename={p.name}"},
        filename=p.name,
        media_type=f"video/{p.suffix[1:]}",
    )
