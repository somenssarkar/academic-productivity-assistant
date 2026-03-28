import os
import json
import httpx


def youtube_search(query: str, max_results: int = 3) -> str:
    """Search YouTube for educational videos matching the query.

    Args:
        query: Search terms (e.g., "quadratic equations grade 10 tutorial")
        max_results: Number of results to return (default 3)

    Returns:
        JSON string with video titles, URLs, channel names, and durations.
    """
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return json.dumps({"error": "YOUTUBE_API_KEY not set", "videos": []})

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "videoCategoryId": "27",  # Education category
        "maxResults": max_results,
        "key": api_key,
        "safeSearch": "strict",
    }

    try:
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as e:
        return json.dumps({"error": str(e), "videos": []})

    videos = []
    video_ids = [item["id"]["videoId"] for item in data.get("items", [])]

    # Fetch durations via videos.list
    if video_ids:
        details_url = "https://www.googleapis.com/youtube/v3/videos"
        details_params = {
            "part": "contentDetails,snippet",
            "id": ",".join(video_ids),
            "key": api_key,
        }
        try:
            details_resp = httpx.get(details_url, params=details_params, timeout=10.0)
            details_resp.raise_for_status()
            details_data = details_resp.json()
            duration_map = {
                v["id"]: _parse_iso_duration(v["contentDetails"]["duration"])
                for v in details_data.get("items", [])
            }
        except httpx.HTTPError:
            duration_map = {}
    else:
        duration_map = {}

    for item in data.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]
        videos.append({
            "title": snippet["title"],
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "channel": snippet["channelTitle"],
            "duration": duration_map.get(video_id, "Unknown"),
            "description": snippet["description"][:200],
        })

    return json.dumps({"videos": videos})


def _parse_iso_duration(duration: str) -> str:
    """Convert ISO 8601 duration (PT8M24S) to human-readable (8:24)."""
    import re
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return "Unknown"
    hours, minutes, seconds = match.groups(default="0")
    if int(hours) > 0:
        return f"{hours}:{int(minutes):02d}:{int(seconds):02d}"
    return f"{int(minutes)}:{int(seconds):02d}"
