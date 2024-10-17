import os
import yt_dlp
from moviepy.editor import VideoFileClip, concatenate_videoclips

def download_youtube_video(youtube_url, output_path):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

def process_videos(personal_video_path, youtube_url, output_path):
    # Download YouTube audio
    youtube_audio_path = os.path.join(os.path.dirname(output_path), 'youtube_audio.mp3')
    download_youtube_video(youtube_url, youtube_audio_path)

    # Load personal video
    personal_clip = VideoFileClip(personal_video_path)

    # Load YouTube audio
    youtube_audio = VideoFileClip(youtube_audio_path).audio

    # Set the audio of the personal video to the YouTube audio
    final_clip = personal_clip.set_audio(youtube_audio)

    # Write the result to a file
    final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac')

    # Clean up temporary files
    os.remove(youtube_audio_path)

    return output_path
