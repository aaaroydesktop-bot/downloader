from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import yt_dlp
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Nexus Universal Downloader API",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LinkRequest(BaseModel):
    url: HttpUrl


@app.post("/extract")
async def extract_media(request: LinkRequest):
    url_str = str(request.url)
    logger.info(f"Request: {url_str}")

    # 🔥 UPDATED yt-dlp config (IMPORTANT FIX)
# 🔥 UPDATED yt-dlp config (IMPORTANT FIX)
    ydl_opts = {
        'format': 'best[ext=mp4]',
        'quiet': True,
        'noplaylist': True,
        'geo_bypass': True,
        'cookiefile': 'cookies.txt', 
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_str, download=False)

        if not info:
            raise HTTPException(status_code=404, detail="No media found")

        # playlist handle
        if 'entries' in info:
            info = info['entries'][0]
        formats = info.get('formats', [])

        video_url = None
        ext = "mp4"

        # 🔥 ONLY real video (video + audio)
        for f in reversed(formats):
            if (
                f.get('ext') == 'mp4' and
                f.get('vcodec') != 'none' and
                f.get('acodec') != 'none'
            ):
                video_url = f.get('url')
                ext = "mp4"
                break

        # 🔥 fallback video-only (no audio)
        if not video_url:
            for f in reversed(formats):
                if f.get('vcodec') != 'none':
                    video_url = f.get('url')
                    ext = f.get('ext') or "mp4"
                    break

        # ❌ NO MORE fallback to info['url']

        if not video_url:
            raise HTTPException(status_code=404, detail="No video format found")

        # 🔥 detect media type
        if ext in ["mp4", "webm", "mkv"]:
            media_type = "video"
        elif ext in ["jpg", "jpeg", "png"]:
            media_type = "image"
        else:
            media_type = "video"

        return {
            "success": True,
            "title": info.get("title"),
            "url": video_url,
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "type": media_type,
            "ext": ext,
            "extractor": info.get("extractor_key"),
        }

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/")
def health():
    return {"status": "API running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))