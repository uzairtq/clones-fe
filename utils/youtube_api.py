from urllib.parse import urlparse, parse_qs

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

    return {
        'title': f'YouTube Video {video_id}',
        'thumbnail': f'https://img.youtube.com/vi/{video_id}/0.jpg',
        'duration': 'Unknown'  # We can't get the duration without the API
    }
