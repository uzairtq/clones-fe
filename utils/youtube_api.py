import os
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs

# Replace with your actual YouTube API key
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', 'YOUR_YOUTUBE_API_KEY')

youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def get_youtube_video_info(url):
    video_id = extract_video_id(url)
    if not video_id:
        return None

    try:
        response = youtube.videos().list(
            part='snippet,contentDetails',
            id=video_id
        ).execute()

        if not response['items']:
            return None

        video_info = response['items'][0]
        snippet = video_info['snippet']
        content_details = video_info['contentDetails']

        return {
            'title': snippet['title'],
            'thumbnail': snippet['thumbnails']['high']['url'],
            'duration': content_details['duration']
        }
    except Exception as e:
        print(f"Error fetching YouTube video info: {e}")
        return None

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
