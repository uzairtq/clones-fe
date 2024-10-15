import os
from urllib.parse import urlparse, parse_qs
import googleapiclient.discovery
import isodate

def extract_video_id(url):
    parsed_url = urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query)['v'][0]
        if parsed_url.path[:7] == '/embed/':
            return parsed_url.path.split('/')[2]
        if parsed_url.path[:3] == '/v/':
            return parsed_url.path.split('/')[2]
    return None

def get_youtube_video_info(url):
    video_id = extract_video_id(url)
    if not video_id:
        return None

    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=os.environ.get("YOUTUBE_API_KEY"))

    try:
        request = youtube.videos().list(
            part="snippet,contentDetails",
            id=video_id
        )
        response = request.execute()

        if not response["items"]:
            return None

        video_info = response["items"][0]
        title = video_info["snippet"]["title"]
        duration_iso = video_info["contentDetails"]["duration"]
        duration = isodate.parse_duration(duration_iso)
        total_seconds = duration.total_seconds()
        minutes, seconds = divmod(total_seconds, 60)
        formatted_duration = f'{int(minutes)}:{int(seconds):02d}'
        thumbnail = video_info["snippet"]["thumbnails"]["default"]["url"]

        return {
            'title': title,
            'duration': formatted_duration,
            'thumbnail': thumbnail
        }
    except Exception as e:
        print(f"Error fetching YouTube video info: {str(e)}")
        return None
