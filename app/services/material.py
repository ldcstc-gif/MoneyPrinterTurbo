import os
import random
import re
import subprocess
import sys
import threading
from typing import List
from urllib.parse import urlencode

import requests
from loguru import logger
from moviepy.video.io.VideoFileClip import VideoFileClip

from app.config import config
from app.models.schema import MaterialInfo, VideoAspect, VideoConcatMode
from app.utils import utils

# Thread-safe counter for API key rotation
_api_key_counter = 0
_api_key_lock = threading.Lock()


def get_api_key(cfg_key: str):
    api_keys = config.app.get(cfg_key)
    if not api_keys:
        raise ValueError(
            f"\n\n##### {cfg_key} is not set #####\n\nPlease set it in the config.toml file: {config.config_file}\n\n"
            f"{utils.to_json(config.app)}"
        )

    # if only one key is provided, return it
    if isinstance(api_keys, str):
        return api_keys

    global _api_key_counter
    with _api_key_lock:
        _api_key_counter += 1
        return api_keys[_api_key_counter % len(api_keys)]


def search_videos_pexels(
    search_term: str,
    minimum_duration: int,
    video_aspect: VideoAspect = VideoAspect.portrait,
) -> List[MaterialInfo]:
    aspect = VideoAspect(video_aspect)
    video_orientation = aspect.name
    video_width, video_height = aspect.to_resolution()
    api_key = get_api_key("pexels_api_keys")
    headers = {
        "Authorization": api_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    }
    # Build URL
    params = {"query": search_term, "per_page": 20, "orientation": video_orientation}
    query_url = f"https://api.pexels.com/videos/search?{urlencode(params)}"
    logger.info(f"searching videos: {query_url}, with proxies: {config.proxy}")

    try:
        r = requests.get(
            query_url,
            headers=headers,
            proxies=config.proxy,
            verify=False,
            timeout=(30, 60),
        )
        response = r.json()
        video_items = []
        if "videos" not in response:
            logger.error(f"search videos failed: {response}")
            return video_items
        videos = response["videos"]
        # loop through each video in the result
        for v in videos:
            duration = v["duration"]
            # check if video has desired minimum duration
            if duration < minimum_duration:
                continue
            video_files = v["video_files"]
            # loop through each url to determine the best quality
            for video in video_files:
                w = int(video["width"])
                h = int(video["height"])
                if w == video_width and h == video_height:
                    item = MaterialInfo()
                    item.provider = "pexels"
                    item.url = video["link"]
                    item.duration = duration
                    video_items.append(item)
                    break
        return video_items
    except Exception as e:
        logger.error(f"search videos failed: {str(e)}")

    return []


def search_videos_pixabay(
    search_term: str,
    minimum_duration: int,
    video_aspect: VideoAspect = VideoAspect.portrait,
) -> List[MaterialInfo]:
    aspect = VideoAspect(video_aspect)

    video_width, video_height = aspect.to_resolution()

    api_key = get_api_key("pixabay_api_keys")
    # Build URL
    params = {
        "q": search_term,
        "video_type": "all",  # Accepted values: "all", "film", "animation"
        "per_page": 50,
        "key": api_key,
    }
    query_url = f"https://pixabay.com/api/videos/?{urlencode(params)}"
    logger.info(f"searching videos: {query_url}, with proxies: {config.proxy}")

    try:
        r = requests.get(
            query_url, proxies=config.proxy, verify=False, timeout=(30, 60)
        )
        response = r.json()
        video_items = []
        if "hits" not in response:
            logger.error(f"search videos failed: {response}")
            return video_items
        videos = response["hits"]
        # loop through each video in the result
        for v in videos:
            duration = v["duration"]
            # check if video has desired minimum duration
            if duration < minimum_duration:
                continue
            video_files = v["videos"]
            # loop through each url to determine the best quality
            for video_type in video_files:
                video = video_files[video_type]
                w = int(video["width"])
                # h = int(video["height"])
                if w >= video_width:
                    item = MaterialInfo()
                    item.provider = "pixabay"
                    item.url = video["url"]
                    item.duration = duration
                    video_items.append(item)
                    break
        return video_items
    except Exception as e:
        logger.error(f"search videos failed: {str(e)}")

    return []


def search_videos_bilibili(
    search_term: str,
    minimum_duration: int,
    video_aspect: VideoAspect = VideoAspect.portrait,
) -> List[MaterialInfo]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com",
    }
    params = {
        "search_type": "video",
        "keyword": search_term,
        "page": 1,
        "pagesize": 20,
        "order": "totalrank",
    }
    logger.info(f"searching bilibili videos for: {search_term}")

    try:
        r = requests.get(
            "https://api.bilibili.com/x/web-interface/search/type",
            params=params,
            headers=headers,
            proxies=config.proxy,
            verify=False,
            timeout=(30, 60),
        )
        data = r.json()
        video_items = []
        if data.get("code") != 0:
            logger.error(f"bilibili search failed: {data.get('message', data)}")
            return video_items

        results = data.get("data", {}).get("result", [])
        for v in results:
            duration_str = v.get("duration", "0:0")
            parts = duration_str.split(":")
            try:
                duration = int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else 0
            except (ValueError, IndexError):
                duration = 0

            if duration < minimum_duration:
                continue

            bvid = v.get("bvid", "")
            if bvid:
                item = MaterialInfo()
                item.provider = "bilibili"
                item.url = f"https://www.bilibili.com/video/{bvid}"
                item.duration = duration
                video_items.append(item)

        logger.info(f"bilibili: found {len(video_items)} videos for '{search_term}'")
        return video_items
    except Exception as e:
        logger.error(f"bilibili search failed: {str(e)}")

    return []


def search_videos_douyin(
    search_term: str,
    minimum_duration: int,
    video_aspect: VideoAspect = VideoAspect.portrait,
) -> List[MaterialInfo]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com",
        "Accept": "application/json",
    }
    logger.info(f"searching douyin videos for: {search_term}")

    try:
        r = requests.get(
            "https://www.douyin.com/aweme/v1/web/search/item/",
            params={
                "keyword": search_term,
                "search_channel": "aweme_video_web",
                "count": 20,
                "offset": 0,
            },
            headers=headers,
            proxies=config.proxy,
            verify=False,
            timeout=(30, 60),
        )
        data = r.json()
        video_items = []

        for v in data.get("data", []):
            aweme = v.get("aweme_info", {})
            duration_ms = aweme.get("duration", 0)
            duration = duration_ms // 1000 if duration_ms > 1000 else duration_ms

            if duration < minimum_duration:
                continue

            aweme_id = aweme.get("aweme_id", "")
            if aweme_id:
                item = MaterialInfo()
                item.provider = "douyin"
                item.url = f"https://www.douyin.com/video/{aweme_id}"
                item.duration = duration
                video_items.append(item)

        logger.info(f"douyin: found {len(video_items)} videos for '{search_term}'")
        return video_items
    except Exception as e:
        logger.warning(f"douyin search requires browser cookies, falling back: {str(e)}")

    return []


def search_videos_xiaohongshu(
    search_term: str,
    minimum_duration: int,
    video_aspect: VideoAspect = VideoAspect.portrait,
) -> List[MaterialInfo]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.xiaohongshu.com",
        "Accept": "application/json",
    }
    logger.info(f"searching xiaohongshu videos for: {search_term}")

    try:
        r = requests.get(
            "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes",
            params={
                "keyword": search_term,
                "page": 1,
                "page_size": 20,
                "sort": "general",
                "note_type": 1,
            },
            headers=headers,
            proxies=config.proxy,
            verify=False,
            timeout=(30, 60),
        )
        data = r.json()
        video_items = []

        for v in data.get("data", {}).get("items", []):
            note_card = v.get("note_card", {})
            if note_card.get("type") != "video":
                continue

            note_id = v.get("id", "")
            if note_id:
                item = MaterialInfo()
                item.provider = "xiaohongshu"
                item.url = f"https://www.xiaohongshu.com/explore/{note_id}"
                item.duration = 30
                video_items.append(item)

        logger.info(f"xiaohongshu: found {len(video_items)} videos for '{search_term}'")
        return video_items
    except Exception as e:
        logger.warning(f"xiaohongshu search requires browser cookies, falling back: {str(e)}")

    return []


def save_video_with_ytdlp(video_url: str, save_dir: str = "") -> str:
    if not save_dir:
        save_dir = utils.storage_dir("cache_videos")
    os.makedirs(save_dir, exist_ok=True)

    video_id = f"vid-{utils.md5(video_url)}"
    video_path = os.path.join(save_dir, f"{video_id}.mp4")

    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
        logger.info(f"video already exists: {video_path}")
        return video_path

    try:
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "-f", "best[height<=720]/best",
            "-o", video_path,
            "--no-playlist",
            "--no-check-certificates",
            "--socket-timeout", "30",
            "--retries", "3",
            "--quiet",
            video_url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode == 0 and os.path.exists(video_path) and os.path.getsize(video_path) > 0:
            clip = None
            try:
                clip = VideoFileClip(video_path)
                if clip.duration > 0 and clip.fps > 0:
                    return video_path
            except Exception as e:
                logger.warning(f"invalid video file: {video_path} => {str(e)}")
                try:
                    os.remove(video_path)
                except Exception:
                    pass
            finally:
                if clip is not None:
                    try:
                        clip.close()
                    except Exception:
                        pass
        else:
            logger.error(f"yt-dlp failed for {video_url}: {result.stderr[:500]}")
    except subprocess.TimeoutExpired:
        logger.error(f"yt-dlp timed out for {video_url}")
    except Exception as e:
        logger.error(f"yt-dlp download failed: {str(e)}")

    return ""


_YTDLP_SOURCES = {"bilibili", "douyin", "xiaohongshu"}


def save_video(video_url: str, save_dir: str = "") -> str:
    if not save_dir:
        save_dir = utils.storage_dir("cache_videos")

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    url_without_query = video_url.split("?")[0]
    url_hash = utils.md5(url_without_query)
    video_id = f"vid-{url_hash}"
    video_path = f"{save_dir}/{video_id}.mp4"

    # if video already exists, return the path
    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
        logger.info(f"video already exists: {video_path}")
        return video_path

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    # if video does not exist, download it
    with open(video_path, "wb") as f:
        f.write(
            requests.get(
                video_url,
                headers=headers,
                proxies=config.proxy,
                verify=False,
                timeout=(60, 240),
            ).content
        )

    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
        clip = None
        try:
            clip = VideoFileClip(video_path)
            duration = clip.duration
            fps = clip.fps
            if duration > 0 and fps > 0:
                return video_path
        except Exception as e:
            logger.warning(f"invalid video file: {video_path} => {str(e)}")
            try:
                os.remove(video_path)
            except Exception:
                pass
        finally:
            if clip is not None:
                try:
                    clip.close()
                except Exception:
                    pass
    return ""


def download_videos(
    task_id: str,
    search_terms: List[str],
    source: str = "pexels",
    video_aspect: VideoAspect = VideoAspect.portrait,
    video_contact_mode: VideoConcatMode = VideoConcatMode.random,
    audio_duration: float = 0.0,
    max_clip_duration: int = 5,
) -> List[str]:
    _search_func_map = {
        "pexels": search_videos_pexels,
        "pixabay": search_videos_pixabay,
        "bilibili": search_videos_bilibili,
        "douyin": search_videos_douyin,
        "xiaohongshu": search_videos_xiaohongshu,
    }

    valid_video_items = []
    valid_video_urls = []
    found_duration = 0.0
    search_videos = _search_func_map.get(source, search_videos_pexels)
    use_ytdlp = source in _YTDLP_SOURCES

    for search_term in search_terms:
        video_items = search_videos(
            search_term=search_term,
            minimum_duration=max_clip_duration,
            video_aspect=video_aspect,
        )
        logger.info(f"found {len(video_items)} videos for '{search_term}'")

        for item in video_items:
            if item.url not in valid_video_urls:
                valid_video_items.append(item)
                valid_video_urls.append(item.url)
                found_duration += item.duration

    # Fallback: if Chinese platform returned nothing, try Pexels with localized keywords
    if not valid_video_items and source in _YTDLP_SOURCES:
        logger.warning(f"{source} search returned no results, falling back to pexels with Asian keywords")
        for search_term in search_terms:
            fallback_term = f"{search_term} Asian"
            video_items = search_videos_pexels(
                search_term=fallback_term,
                minimum_duration=max_clip_duration,
                video_aspect=video_aspect,
            )
            logger.info(f"pexels fallback: found {len(video_items)} videos for '{fallback_term}'")
            for item in video_items:
                if item.url not in valid_video_urls:
                    valid_video_items.append(item)
                    valid_video_urls.append(item.url)
                    found_duration += item.duration
        use_ytdlp = False

    logger.info(
        f"found total videos: {len(valid_video_items)}, required duration: {audio_duration} seconds, found duration: {found_duration} seconds"
    )
    video_paths = []

    material_directory = config.app.get("material_directory", "").strip()
    if material_directory == "task":
        material_directory = utils.task_dir(task_id)
    elif material_directory and not os.path.isdir(material_directory):
        material_directory = ""

    if video_contact_mode.value == VideoConcatMode.random.value:
        random.shuffle(valid_video_items)

    total_duration = 0.0
    for item in valid_video_items:
        try:
            logger.info(f"downloading video: {item.url}")
            if use_ytdlp:
                saved_video_path = save_video_with_ytdlp(
                    video_url=item.url, save_dir=material_directory
                )
            else:
                saved_video_path = save_video(
                    video_url=item.url, save_dir=material_directory
                )
            if saved_video_path:
                logger.info(f"video saved: {saved_video_path}")
                video_paths.append(saved_video_path)
                seconds = min(max_clip_duration, item.duration)
                total_duration += seconds
                if total_duration > audio_duration:
                    logger.info(
                        f"total duration of downloaded videos: {total_duration} seconds, skip downloading more"
                    )
                    break
        except Exception as e:
            logger.error(f"failed to download video: {utils.to_json(item)} => {str(e)}")
    logger.success(f"downloaded {len(video_paths)} videos")
    return video_paths


if __name__ == "__main__":
    download_videos(
        "test123", ["Money Exchange Medium"], audio_duration=100, source="pixabay"
    )
