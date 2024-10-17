import os
import logging
import yt_dlp
from moviepy.editor import VideoFileClip, concatenate_videoclips

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def download_youtube_video(youtube_url, output_path):
    # Remove the .mp3 extension if it's already present
    output_path_without_ext = os.path.splitext(output_path)[0]
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path_without_ext,  # Use the path without extension
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'prefer_ffmpeg': True,
        'keepvideo': False
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        logger.info(f"Successfully downloaded audio from YouTube: {youtube_url}")
        
        # Ensure the final file has the .mp3 extension
        final_output_path = f"{output_path_without_ext}.mp3"
        if os.path.exists(final_output_path):
            logger.info(f"Audio file saved as: {final_output_path}")
        else:
            logger.error(f"Expected audio file not found: {final_output_path}")
        
        return final_output_path
    except Exception as e:
        logger.error(f"Error downloading YouTube audio: {str(e)}")
        raise

def process_videos(personal_video_path, youtube_url, output_path):
    try:
        # Download YouTube audio
        youtube_audio_path = os.path.join(os.path.dirname(output_path), 'youtube_audio.mp3')
        youtube_audio_path = download_youtube_video(youtube_url, youtube_audio_path)
        
        logger.info(f"YouTube audio downloaded to: {youtube_audio_path}")
        
        # Load personal video
        logger.info(f"Loading personal video from: {personal_video_path}")
        personal_clip = VideoFileClip(personal_video_path)
        
        # Load YouTube audio
        logger.info(f"Loading YouTube audio from: {youtube_audio_path}")
        youtube_audio = VideoFileClip(youtube_audio_path).audio
        
        # Set the audio of the personal video to the YouTube audio
        logger.info("Setting YouTube audio to personal video")
        final_clip = personal_clip.set_audio(youtube_audio)
        
        # Write the result to a file
        logger.info(f"Writing final video to: {output_path}")
        final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac')
        
        # Clean up temporary files
        logger.info("Cleaning up temporary files")
        os.remove(youtube_audio_path)
        
        logger.info("Video processing completed successfully")
        return output_path
    except Exception as e:
        logger.error(f"Error in process_videos: {str(e)}")
        raise
