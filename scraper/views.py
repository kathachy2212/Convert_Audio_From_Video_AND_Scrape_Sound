import os
import uuid
import shutil
import yt_dlp
import ffmpeg
import speech_recognition as sr
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import threading
import time

# Define base path relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Optional: logger class for yt_dlp
class MyLogger:
    def debug(self, msg): print("[DEBUG]", msg)
    def warning(self, msg): print("[WARNING]", msg)
    def error(self, msg): print("[ERROR]", msg)

@csrf_exempt
def index(request):
    return render(request, 'template/index.html')

@csrf_exempt
def scrape_video(request):
    if request.method == 'POST':
        url = request.POST.get('url')

        if url:
            try:
                # Unique ID for file naming
                unique_id = str(uuid.uuid4())
                media_dir = os.path.join(BASE_DIR, 'media')  # 📁 Only one directory now
                os.makedirs(media_dir, exist_ok=True)
                filename_base = os.path.join(media_dir, unique_id)

                ffmpeg_path = r'C:\ffmpeg\bin\ffmpeg.exe'
                if not os.path.isfile(ffmpeg_path):
                    return JsonResponse({'error': 'FFmpeg not found at specified path.'}, status=500)

                # yt_dlp options - download directly to media folder
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'ffmpeg_location': ffmpeg_path,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'outtmpl': f'{filename_base}.%(ext)s',  # 📍 No "downloads/" folder
                    'logger': MyLogger(),
                    'verbose': True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=True)
                    title = info_dict.get('title', 'Unknown title')
                    description = info_dict.get('description', 'No description available')
                    uploader = info_dict.get('uploader', 'Unknown uploader')
                    publish_date = info_dict.get('upload_date', 'Unknown date')
                    view_count = info_dict.get('view_count', 'No views data')

                mp3_path = f'{filename_base}.mp3'
                if not os.path.exists(mp3_path):
                    return JsonResponse({'error': f'MP3 file not found at {mp3_path}'}, status=500)

                # 🎤 Convert MP3 to WAV for transcription
                wav_path = f'{filename_base}.wav'
                ffmpeg.input(mp3_path).output(wav_path, ac=1, ar='16000').run()

                # 🧠 Transcribe WAV to text
                recognizer = sr.Recognizer()
                with sr.AudioFile(wav_path) as source:
                    audio_data = recognizer.record(source)
                    try:
                        transcript = recognizer.recognize_google(audio_data)
                    except sr.UnknownValueError:
                        transcript = "Audio was not clear enough for transcription."
                    except sr.RequestError as e:
                        transcript = f"Speech Recognition error: {e}"

                download_link = f'/media/{unique_id}.mp3'

                # Schedule deletion of both files after 10 minutes
                schedule_file_deletion(mp3_path, wav_path, delay=600)  # 10 minutes = 600 seconds

                return JsonResponse({
                    'title': title,
                    'description': description,
                    'uploader': uploader,
                    'publish_date': publish_date,
                    'view_count': view_count,
                    'download_link': download_link,
                    'transcript': transcript  # 👈 Sent to frontend
                })

            except Exception as e:
                print("[EXCEPTION]", str(e))
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)


def schedule_file_deletion(*files, delay=600):
    """
    Schedules the deletion of files after a delay (in seconds).
    By default, this will delete after 10 minutes (600 seconds).
    """
    def delete_later():
        print(f"Deletion scheduled for: {files} in {delay} seconds.")
        time.sleep(delay)
        for file in files:
            try:
                if os.path.exists(file):
                    os.remove(file)
                    print(f"Deleted file: {file}")
                else:
                    print(f"File not found for deletion: {file}")
            except Exception as e:
                print(f"Failed to delete {file}: {str(e)}")

    # Change daemon to False to ensure thread completes before program exits
    deletion_thread = threading.Thread(target=delete_later, daemon=False)
    deletion_thread.start()

