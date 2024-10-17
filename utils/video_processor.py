import os
import logging
import yt_dlp
from moviepy.editor import VideoFileClip, concatenate_videoclips
import time

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def download_youtube_video(youtube_url, output_path):
    ydl_opts = {
        'format': 'best',  # Download best quality video
        'outtmpl': output_path,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        logger.info(f"Successfully downloaded video from YouTube: {youtube_url}")
        return output_path
    except Exception as e:
        logger.error(f"Error downloading YouTube video: {str(e)}")
        raise

def process_videos(personal_video_path, youtube_url, output_path):
    start_time = time.time()
    try:
        # Download YouTube video
        youtube_video_path = os.path.join(os.path.dirname(output_path), 'youtube_video.mp4')
        youtube_video_path = download_youtube_video(youtube_url, youtube_video_path)
        
        logger.info(f"YouTube video downloaded to: {youtube_video_path}")
        
        # Load personal video
        logger.info(f"Loading personal video from: {personal_video_path}")
        personal_clip = VideoFileClip(personal_video_path)
        
        # Load YouTube video
        logger.info(f"Loading YouTube video from: {youtube_video_path}")
        youtube_clip = VideoFileClip(youtube_video_path)
        
        # Concatenate the videos
        logger.info("Concatenating videos")
        final_clip = concatenate_videoclips([personal_clip, youtube_clip])
        
        # Write the result to a file
        logger.info(f"Writing final video to: {output_path}")
        final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', logger=logger)
        
        # Clean up temporary files
        logger.info("Cleaning up temporary files")
        os.remove(youtube_video_path)
        
        # Close the clips to release resources
        personal_clip.close()
        youtube_clip.close()
        final_clip.close()
        
        end_time = time.time()
        logger.info(f"Video processing completed successfully in {end_time - start_time:.2f} seconds")
        return output_path
    except Exception as e:
        end_time = time.time()
        logger.error(f"Error in process_videos: {str(e)}")
        logger.error(f"Video processing failed after {end_time - start_time:.2f} seconds")
        raise
