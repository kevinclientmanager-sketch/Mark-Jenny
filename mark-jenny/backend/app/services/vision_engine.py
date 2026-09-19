"""
Vision Engine — Image analysis, screenshot reading, YouTube video understanding.
Uses local vision models and web scraping to understand visual content.
"""
import asyncio
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx
from app.core.config import get_settings

settings = get_settings()

VISION_CACHE_DIR = Path(settings.UPLOAD_DIR) / "vision_cache"
VISION_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class VisionEngine:
    def __init__(self):
        self._stats = {
            "images_analyzed": 0,
            "screenshots_read": 0,
            "videos_understood": 0,
            "last_analysis_at": None,
        }

    async def analyze_image(self, image_path: str, question: str = "What do you see?") -> Dict[str, Any]:
        """Analyze an image using local or cloud vision model."""
        path = Path(image_path)
        if not path.exists():
            return {"success": False, "error": "Image not found"}

        try:
            # Read image as base64
            with open(path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            # Try local Ollama vision model first
            result = await self._analyze_with_ollama(img_b64, question)
            if result["success"]:
                self._stats["images_analyzed"] += 1
                self._stats["last_analysis_at"] = datetime.utcnow().isoformat()
                return result

            # Fallback: basic metadata
            return await self._basic_image_info(path)

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _analyze_with_ollama(self, img_b64: str, question: str) -> Dict:
        """Use Ollama vision model to analyze image."""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llava:7b",
                        "prompt": question,
                        "images": [img_b64],
                        "stream": False,
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    return {"success": True, "analysis": data.get("response", ""), "model": "llava:7b"}
        except Exception:
            pass
        return {"success": False, "error": "Ollama not available"}

    async def _basic_image_info(self, path: Path) -> Dict:
        """Get basic image metadata without AI."""
        size = path.stat().st_size
        suffix = path.suffix.lower()
        return {
            "success": True,
            "analysis": f"Image file: {path.name}, Size: {size/1024:.1f}KB, Format: {suffix}",
            "model": "metadata-only",
        }

    async def read_screenshot(self, screenshot_path: str) -> Dict[str, Any]:
        """Read and understand a screenshot."""
        result = await self.analyze_image(screenshot_path, "Describe this screenshot in detail. What UI elements, text, buttons, and content do you see? What is the user looking at?")
        if result["success"]:
            self._stats["screenshots_read"] += 1
        return result

    async def understand_youtube(self, url: str) -> Dict[str, Any]:
        """Understand a YouTube video by extracting metadata, transcript, and thumbnails."""
        try:
            video_id = self._extract_video_id(url)
            if not video_id:
                return {"success": False, "error": "Invalid YouTube URL"}

            result = {
                "success": True,
                "video_id": video_id,
                "url": url,
                "metadata": {},
                "transcript": "",
                "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            }

            # Get video metadata via oembed
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json")
                if r.status_code == 200:
                    data = r.json()
                    result["metadata"] = {
                        "title": data.get("title", ""),
                        "author": data.get("author_name", ""),
                    }

            # Try to get transcript via youtube-transcript-api
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, "-c",
                    f"from youtube_transcript_api import YouTubeTranscriptApi; t = YouTubeTranscriptApi.get_transcript('{video_id}'); print(' '.join(x['text'] for x in t))",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
                if proc.returncode == 0:
                    result["transcript"] = stdout.decode().strip()
            except Exception:
                pass

            # Analyze thumbnail if vision available
            if result["thumbnail"]:
                try:
                    async with httpx.AsyncClient() as client:
                        r = await client.get(result["thumbnail"])
                        if r.status_code == 200:
                            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                                f.write(r.content)
                                thumb_path = f.name
                            thumb_analysis = await self.analyze_image(thumb_path, "What is this YouTube video about based on the thumbnail?")
                            result["thumbnail_analysis"] = thumb_analysis.get("analysis", "")
                            os.unlink(thumb_path)
                except Exception:
                    pass

            self._stats["videos_understood"] += 1
            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def understand_youtube_playlist(self, playlist_url: str) -> Dict[str, Any]:
        """Understand all videos in a YouTube playlist."""
        try:
            # Extract playlist ID
            match = re.search(r"list=([a-zA-Z0-9_-]+)", playlist_url)
            if not match:
                return {"success": False, "error": "Invalid playlist URL"}

            playlist_id = match.group(1)

            # Get playlist videos via oembed (limited)
            videos = []
            async with httpx.AsyncClient(timeout=30) as client:
                # Try yt-dlp for playlist extraction
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "yt-dlp", "--flat-playlist", "--print", "%(id)s|||%(title)s", playlist_url,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
                    if proc.returncode == 0:
                        for line in stdout.decode().strip().split("\n"):
                            if "|||" in line:
                                vid, title = line.split("|||", 1)
                                videos.append({"id": vid, "title": title, "url": f"https://www.youtube.com/watch?v={vid}"})
                except FileNotFoundError:
                    return {"success": False, "error": "yt-dlp not installed. Run: pip install yt-dlp"}

            # Understand each video
            understood = []
            for vid in videos[:20]:  # Limit to 20 videos
                understanding = await self.understand_youtube(vid["url"])
                understood.append({
                    "video": vid,
                    "understanding": understanding,
                })

            return {
                "success": True,
                "playlist_id": playlist_id,
                "total_videos": len(videos),
                "understood": understood,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def ocr_image(self, image_path: str) -> Dict[str, Any]:
        """Extract text from image using OCR."""
        path = Path(image_path)
        if not path.exists():
            return {"success": False, "error": "Image not found"}

        # Use local vision model for OCR
        result = await self.analyze_image(path, "Extract all text from this image exactly as it appears. Return only the text, nothing else.")
        return result

    async def compare_images(self, image1_path: str, image2_path: str) -> Dict[str, Any]:
        """Compare two images and describe differences."""
        img1 = Path(image1_path)
        img2 = Path(image2_path)

        if not img1.exists() or not img2.exists():
            return {"success": False, "error": "One or both images not found"}

        # Get analysis of both
        a1 = await self.analyze_image(image1_path, "Describe this image in detail.")
        a2 = await self.analyze_image(image2_path, "Describe this image in detail.")

        if a1["success"] and a2["success"]:
            # Ask vision model to compare
            combined = f"Image 1: {a1['analysis']}\n\nImage 2: {a2['analysis']}"
            comparison = await self.analyze_image(
                image1_path,
                f"Compare these two images. Image 1 analysis: {a1['analysis']}. What are the differences with Image 2: {a2['analysis']}?"
            )
            return {
                "success": True,
                "image1": a1["analysis"],
                "image2": a2["analysis"],
                "comparison": comparison.get("analysis", ""),
            }

        return {"success": False, "error": "Failed to analyze one or both images"}

    def _extract_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
            r"(?:embed/)([a-zA-Z0-9_-]{11})",
            r"([a-zA-Z0-9_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_stats(self) -> Dict:
        return self._stats


# Singleton
vision_engine = VisionEngine()
