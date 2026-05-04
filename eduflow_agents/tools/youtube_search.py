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
    # Fetch more candidates than requested so filtering still yields enough results.
    fetch_count = max(max_results * 2, 6)
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": fetch_count,
        "key": api_key,
        "safeSearch": "strict",
    }

    try:
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as e:
        return json.dumps({"error": str(e), "videos": []})

    video_ids = [item["id"]["videoId"] for item in data.get("items", [])]
    if not video_ids:
        return json.dumps({"videos": []})

    # Layer 1: videos.list only returns videos that are public and actually exist.
    # Deleted or private videos are silently absent from this response.
    details_url = "https://www.googleapis.com/youtube/v3/videos"
    details_params = {
        "part": "contentDetails,snippet",
        "id": ",".join(video_ids),
        "key": api_key,
    }
    try:
        details_resp = httpx.get(details_url, params=details_params, timeout=10.0)
        details_resp.raise_for_status()
        confirmed = {v["id"]: v for v in details_resp.json().get("items", [])}
    except httpx.HTTPError:
        confirmed = {}

    videos = []
    for item in data.get("items", []):
        if len(videos) >= max_results:
            break
        video_id = item["id"]["videoId"]

        # Layer 1 filter: skip videos not confirmed by videos.list (deleted/private).
        if video_id not in confirmed:
            continue

        # Layer 2 filter: oEmbed check — confirms the video is actually playable.
        # Catches age-restricted, TOS-removed, and copyright-blocked videos that
        # videos.list still returns but users cannot watch.
        if not _is_playable(video_id):
            continue

        snippet = item["snippet"]
        duration = _parse_iso_duration(
            confirmed[video_id]["contentDetails"]["duration"]
        )
        videos.append({
            "title": snippet["title"],
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "channel": snippet["channelTitle"],
            "duration": duration,
            "description": snippet["description"][:200],
        })

    return json.dumps({"videos": videos})


def _is_playable(video_id: str) -> bool:
    """Check video is playable via YouTube's oEmbed endpoint (no API key needed).

    Returns True if the video is watchable, False if YouTube reports it unavailable.
    On any network error, returns True to avoid over-filtering good videos.
    """
    try:
        r = httpx.get(
            "https://www.youtube.com/oembed",
            params={
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "format": "json",
            },
            timeout=5.0,
        )
        return r.status_code == 200
    except Exception:
        return True


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
