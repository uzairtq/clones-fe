import os
import logging
from urllib.parse import urlparse, parse_qs
import googleapiclient.discovery
import isodate

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
        logger.error(f"Invalid YouTube URL: {url}")
        return None

    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=os.environ.get("YOUTUBE_API_KEY"))

    try:
        request = youtube.videos().list(
            part="snippet,contentDetails",
            id=video_id
        )
        response = request.execute()

        if not response["items"]:
            logger.error(f"No video found for ID: {video_id}")
            return None

        video_info = response["items"][0]
        title = video_info["snippet"]["title"]
        duration_iso = video_info["contentDetails"]["duration"]
        
        logger.debug(f"Duration ISO: {duration_iso}")
        
        try:
            duration = isodate.parse_duration(duration_iso)
            total_seconds = int(duration.total_seconds())
            logger.debug(f"Total seconds: {total_seconds}")
            
            minutes, seconds = divmod(total_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            
            if hours > 0:
                formatted_duration = f'{hours}:{minutes:02d}:{seconds:02d}'
            else:
                formatted_duration = f'{minutes}:{seconds:02d}'
            
            logger.debug(f"Formatted duration: {formatted_duration}")
        except Exception as duration_error:
            logger.error(f"Error parsing duration: {str(duration_error)}")
            formatted_duration = "00:00"  # Default duration if parsing fails
        
        thumbnail = video_info["snippet"]["thumbnails"]["medium"]["url"]

        return {
            'title': title,
            'duration': formatted_duration,
            'thumbnail': thumbnail
        }
    except Exception as e:
        logger.error(f"Error fetching YouTube video info: {str(e)}")
        return None
