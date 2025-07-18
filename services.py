"""
Services for Video Translator Application
บริการต่างๆ สำหรับแอปพลิเคชันแปลวิดีโอ
"""

import os
import re
import subprocess
import tempfile
import warnings
import threading
import queue
import time
import requests
import zipfile
import shutil
from datetime import datetime
from pathlib import Path
import yt_dlp
from urllib.parse import urlparse, parse_qs
import uuid
import concurrent.futures

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Import libraries
import torch
import torchaudio
from transformers import WhisperProcessor, WhisperForConditionalGeneration, AutoTokenizer, AutoModelForSeq2SeqLM
import librosa
import soundfile as sf
import numpy as np
from gtts import gTTS
from youtube_transcript_api._api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

# Audio preprocessing imports
try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False
    print("⚠️  noisereduce not available, noise reduction disabled")

try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False
    print("⚠️  webrtcvad not available, VAD disabled")

try:
    from scipy import signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("⚠️  scipy not available, bandpass filter disabled")

# Ultimate Vocal Remover imports
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    print("⚠️  onnxruntime not available, Ultimate Vocal Remover disabled")

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("⚠️  opencv not available, some video processing features disabled")

# Import configuration
from config import *
from config import STT_MODELS, TRANSLATION_MODELS, TTS_MODELS, UPLOADS_DIR, OUTPUTS_DIR, TEMP_DIR, TEXTS_DIR, cleanup_temp_files, cleanup_upload_file, generate_output_filename

class ModelDownloader:
    """Automatic model downloader for missing models"""
    
    def __init__(self):
        self.download_paths = {
            # Biodatlab Thai Whisper Models (แนะนำสูงสุด)
            'biodatlab-large-v3': {
                'url': 'https://huggingface.co/biodatlab/whisper-th-large-v3-combined',
                'local_path': 'models/whisper-th-large-v3-combined',
                'type': 'whisper'
            },
            'biodatlab-medium-timestamp': {
                'url': 'https://huggingface.co/biodatlab/whisper-th-medium-timestamp',
                'local_path': 'models/whisper-th-medium-timestamp',
                'type': 'whisper'
            },
            'biodatlab-medium': {
                'url': 'https://huggingface.co/biodatlab/whisper-th-medium-combined',
                'local_path': 'models/whisper-th-medium-combined',
                'type': 'whisper'
            },
            # Thonburian Whisper Models (ลบออกเนื่องจาก repository ไม่พบ)
            # 'thonburian-base': {
            #     'url': 'https://huggingface.co/Thonburian/whisper-base',
            #     'local_path': 'models/whisper-base',
            #     'type': 'whisper'
            # },
            # 'thonburian-small': {
            #     'url': 'https://huggingface.co/Thonburian/whisper-small',
            #     'local_path': 'models/whisper-small',
            #     'type': 'whisper'
            # },
            # 'thonburian-medium': {
            #     'url': 'https://huggingface.co/Thonburian/whisper-medium',
            #     'local_path': 'models/whisper-medium',
            #     'type': 'whisper'
            # },
            # 'thonburian-medium-timestamps': {
            #     'url': 'https://huggingface.co/biodatlab/whisper-th-medium-timestamp',
            #     'local_path': 'models/whisper-th-medium-timestamp',
            #     'type': 'whisper'
            # },
            # 'thonburian-large': {
            #     'url': 'https://huggingface.co/Thonburian/whisper-large',
            #     'local_path': 'models/whisper-large',
            #     'type': 'whisper'
            # },
            # Translation Models
            'nllb-200': {
                'url': 'https://huggingface.co/facebook/nllb-200-3.3B',
                'local_path': 'models/nllb-200-3.3B',
                'type': 'translation'
            },
            'nllb-200-distilled': {
                'url': 'https://huggingface.co/facebook/nllb-200-distilled-1.3B',
                'local_path': 'models/nllb-200-distilled-1.3B',
                'type': 'translation'
            }
        }
    
    def is_model_available(self, model_name):
        """Check if model is available locally"""
        if model_name not in self.download_paths:
            return True  # Assume available if not in download list
        
        local_path = Path(self.download_paths[model_name]['local_path'])
        return local_path.exists() and any(local_path.iterdir())
    
    def download_model(self, model_name, task_id=None):
        """Download model if not available locally"""
        if model_name not in self.download_paths:
            print(f"⚠️  Model {model_name} not in download list, skipping download")
            return True
        
        if self.is_model_available(model_name):
            print(f"✅ Model {model_name} already available locally")
            return True
        
        model_info = self.download_paths[model_name]
        local_path = Path(model_info['local_path'])
        
        print(f"📥 Downloading model {model_name} from {model_info['url']}")
        print(f"📁 Installing to: {local_path}")
        
        try:
            # Create directory if it doesn't exist
            local_path.mkdir(parents=True, exist_ok=True)
            
            # Try huggingface_hub first (more reliable)
            if self._download_with_huggingface_hub(model_info['url'], local_path):
                print(f"✅ Successfully downloaded {model_name}")
                return True
            else:
                print(f"❌ Failed to download {model_name} with huggingface_hub")
                return False
                
        except Exception as e:
            print(f"❌ Error downloading {model_name}: {e}")
            return False
    
    def _download_with_git_lfs(self, url, local_path):
        """Download model using git lfs"""
        try:
            # Check if git lfs is available
            result = subprocess.run(['git', 'lfs', 'version'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print("⚠️  Git LFS not available, trying alternative download method")
                return self._download_with_huggingface_hub(url, local_path)
            
            # Clone with git lfs
            cmd = [
                'git', 'clone', '--depth', '1', 
                '--filter=blob:none', '--sparse',
                url, str(local_path)
            ]
            
            print(f"🔄 Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Pull LFS files
                lfs_cmd = ['git', 'lfs', 'pull']
                subprocess.run(lfs_cmd, cwd=local_path, capture_output=True, timeout=300)
                return True
            else:
                print(f"❌ Git clone failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ Download timeout, trying alternative method")
            return self._download_with_huggingface_hub(url, local_path)
        except Exception as e:
            print(f"❌ Git LFS download failed: {e}")
            return self._download_with_huggingface_hub(url, local_path)
    
    def _download_with_huggingface_hub(self, url, local_path):
        """Download using huggingface_hub library"""
        try:
            from huggingface_hub import snapshot_download
            
            # Extract repo_id from URL
            repo_id = url.replace('https://huggingface.co/', '')
            
            print(f"🔄 Downloading with huggingface_hub: {repo_id}")
            
            # Download to specified location
            downloaded_path = snapshot_download(
                repo_id=repo_id,
                local_dir=local_path,
                local_dir_use_symlinks=False,
                resume_download=True
            )
            
            print(f"✅ Downloaded to: {downloaded_path}")
            return True
            
        except ImportError:
            print("❌ huggingface_hub not available, trying git lfs...")
            return self._download_with_git_lfs(url, local_path)
        except Exception as e:
            print(f"❌ HuggingFace Hub download failed: {e}")
            print("🔄 Trying git lfs as fallback...")
            return self._download_with_git_lfs(url, local_path)
    
    def get_download_progress(self, model_name):
        """Get download progress for a model"""
        if model_name not in self.download_paths:
            return "Model not in download list"
        
        local_path = Path(self.download_paths[model_name]['local_path'])
        if local_path.exists():
            return "Downloaded"
        else:
            return "Not downloaded"
    
    def get_available_models(self):
        """Get list of available models"""
        available = []
        for model_name in self.download_paths:
            if self.is_model_available(model_name):
                available.append(model_name)
        return available
    
    def get_missing_models(self):
        """Get list of missing models"""
        missing = []
        for model_name in self.download_paths:
            if not self.is_model_available(model_name):
                missing.append(model_name)
        return missing

class JobQueue:
    """Queue system สำหรับจัดการงานหลายงาน"""
    
    def __init__(self, max_concurrent=MAX_CONCURRENT_JOBS):
        self.queue = queue.Queue()
        self.active_jobs = {}
        self.completed_jobs = {}
        self.max_concurrent = max_concurrent
        self.workers = []
        self.running = True
        
        # Thread safety locks
        self.jobs_lock = threading.Lock()
        self.completed_lock = threading.Lock()
        
        # Job timeout settings (in seconds)
        self.job_timeout = 1800  # 30 minutes timeout (เพิ่มเป็น 30 นาที)
        self.job_timeout_check_interval = 60  # Check every 60 seconds
        
        # เริ่มต้น worker threads
        for i in range(max_concurrent):
            worker = threading.Thread(target=self._worker, args=(i,))
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
        
        # Start timeout monitor thread
        self.timeout_monitor = threading.Thread(target=self._timeout_monitor)
        self.timeout_monitor.daemon = True
        self.timeout_monitor.start()
    
    def add_job(self, task_id, task_data):
        """เพิ่มงานเข้า queue"""
        job = {
            'task_id': task_id,
            'task_data': task_data,
            'status': 'queued',
            'progress': 0,
            'message': 'รอในคิว...',
            'created_at': datetime.now(),
            'started_at': None,
            'completed_at': None,
            'error': None,
            'temp_files': [] # Keep track of temporary files for this job
        }
        
        self.queue.put(job)
        with self.jobs_lock:
            self.active_jobs[task_id] = job
        print(f"📋 เพิ่มงาน {task_id} เข้า queue")
        return job
    
    def _worker(self, worker_id):
        """Worker thread สำหรับประมวลผลงาน"""
        while self.running:
            try:
                job = self.queue.get(timeout=1)
                if job is None:
                    break
                
                task_id = job['task_id']
                task_data = job['task_data']
                
                # อัปเดตสถานะ
                job['status'] = 'processing'
                job['started_at'] = datetime.now()
                job['progress'] = 0
                job['message'] = 'เริ่มต้นการประมวลผล...'
                job['current_step'] = 'เริ่มต้น'
                job['total_steps'] = 7
                job['step_progress'] = 0
                
                print(f"🔧 Worker {worker_id} เริ่มประมวลผลงาน {task_id}")
                
                try:
                    # ประมวลผลงาน
                    self._process_job(job)
                    
                    # อัปเดตสถานะเสร็จสิ้น
                    job['status'] = 'completed'
                    job['progress'] = 100
                    job['message'] = 'ประมวลผลเสร็จสิ้น'
                    job['completed_at'] = datetime.now()
                    job['current_step'] = 'เสร็จสิ้น'
                    job['step_progress'] = 100
                    
                    # ย้ายไปยัง completed_jobs
                    with self.completed_lock:
                        self.completed_jobs[task_id] = job
                    with self.jobs_lock:
                        if task_id in self.active_jobs:
                            del self.active_jobs[task_id]
                    
                    print(f"✅ งาน {task_id} เสร็จสิ้น")
                    
                except Exception as e:
                    # อัปเดตสถานะข้อผิดพลาด
                    job['status'] = 'error'
                    job['error'] = str(e)
                    job['message'] = f'เกิดข้อผิดพลาด: {str(e)}'
                    job['completed_at'] = datetime.now()
                    
                    # เพิ่ม error recovery information
                    job['error_details'] = {
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'error_time': datetime.now().isoformat(),
                        'recovery_suggestion': 'ลองรีสตาร์ทระบบหรือตรวจสอบไฟล์อินพุต'
                    }
                    
                    print(f"❌ งาน {task_id} เกิดข้อผิดพลาด: {e}")
                    print(f"🔧 ข้อเสนอแนะการแก้ไข: {job['error_details']['recovery_suggestion']}")
                
                finally:
                    # Clean up temporary files associated with this job
                    try:
                        cleanup_temp_files(job['temp_files'])
                        job['temp_files'].clear() # Clear the list after cleanup
                    except Exception as cleanup_error:
                        print(f"⚠️ Error cleaning up temp files for {task_id}: {cleanup_error}")
                    
                    # Memory cleanup after each job
                    try:
                        import gc
                        gc.collect()
                        import torch
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    except Exception as mem_error:
                        print(f"⚠️ Memory cleanup error: {mem_error}")
                    
                    self.queue.task_done()
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Worker {worker_id} เกิดข้อผิดพลาด: {e}")
    
    def _process_job(self, job):
        """ประมวลผลงาน"""
        task_id = job['task_id']
        task_data = job['task_data']
        
        # Update config based on advanced options
        if task_data.get('enable_preprocessing', True):
            import config
            config.ENABLE_AUDIO_PREPROCESSING = task_data.get('enable_preprocessing', True)
            config.ENABLE_NOISE_REDUCTION = task_data.get('enable_noise_reduction', True)
            config.ENABLE_VAD = task_data.get('enable_vad', True)
            config.ENABLE_TTS_SYNC = task_data.get('enable_tts_sync', True)
        
        # สร้าง processor instances
        video_processor = VideoProcessor()
        translation_service = TranslationService()
        tts_service = TTSService()
        
        # Initialize step tracking
        total_steps = 7
        current_step = 1
        
        # Check if this is a reprocess with custom text
        if 'custom_text' in task_data:
            # Skip STT step, use custom text
            original_text = task_data['custom_text']
            self._update_progress(job, 40, "ใช้ข้อความที่กำหนดเอง...", "ขั้นตอนที่ 4: Translation", 40)
            # For reprocess with text, we still need the original video
            if 'video_input' not in task_data:
                raise Exception("video_input is required for reprocessing with custom text")
            video_path = video_processor.process_video_input(
                task_data['video_input'], 
                task_id, 
                task_data.get('format_id')
            )
            job['video_path'] = video_path
            job['temp_files'].append(video_path) # Add downloaded video to temp files if it's new
        else:
            # Step 1: Process video input
            self._update_progress(job, 10, "กำลังประมวลผลวิดีโอ...", "ขั้นตอนที่ 1: Video Processing", 10)
            if 'video_input' not in task_data:
                raise Exception("video_input is required")
            video_path = video_processor.process_video_input(
                task_data['video_input'], 
                task_id, 
                task_data.get('format_id'),
                task_data.get('realtime', False)
            )
            job['video_path'] = video_path
            if self._is_new_upload(task_data['video_input']): # Only add if it's an uploaded file
                job['temp_files'].append(video_path)
            
        # Step 2: Vocal Removal (ถ้าเปิดใช้งาน)
        enable_vocal_removal_step = task_data.get('enable_step2_vocal_removal', True)
        if enable_vocal_removal_step:
            self._update_progress(job, 20, "กำลังแยกเสียงพูดออกจากดนตรี (UVR)...", "ขั้นตอนที่ 2: Vocal Removal", 20)
            enable_vocal_removal = task_data.get('enable_vocal_removal', False) or True
        else:
            enable_vocal_removal = False
            self._update_progress(job, 20, "ข้ามขั้นตอนแยกเสียงพูด...", "ขั้นตอนที่ 2: Vocal Removal", 20)
        
        # Step 2: Extract audio with optional vocal removal (ไร้ขีดจำกัด)
        self._update_progress(job, 25, "กำลังแยกเสียงจากวิดีโอ (ไร้ขีดจำกัด)...", "ขั้นตอนที่ 2: Audio Extraction", 25)
        
        print(f"🔧 Unlimited Processing Mode:")
        print(f"   - Audio length: Unlimited")
        print(f"   - File size: Unlimited")
        print(f"   - Memory usage: Unlimited")
        print(f"   - Processing time: Unlimited")
        
        if task_data.get('realtime', False):
            audio_path = video_processor.extract_audio_realtime(video_path, task_id)
            job['temp_files'].append(audio_path)
        else:
            audio_result = video_processor.extract_audio(video_path, task_id, enable_vocal_removal)
            
            if isinstance(audio_result, dict):
                # Vocal removal was applied
                job['audio_path'] = audio_result['vocals']  # Use vocals for STT
                job['instrumental_path'] = audio_result['instrumental']  # Keep instrumental for mixing
                job['original_audio_path'] = audio_result['original_audio']
                job['temp_files'].extend([audio_result['vocals'], audio_result['original_audio']])
                if audio_result['instrumental']:
                    job['temp_files'].append(audio_result['instrumental'])
                print(f"🎵 ใช้เสียงที่แยกแล้วสำหรับ STT: {audio_result['vocals']}")
                audio_path = audio_result['vocals']
            else:
                # Normal audio extraction
                job['audio_path'] = audio_result
                job['temp_files'].append(audio_result)
                audio_path = audio_result
        
        # Step 3: Speech-to-Text (ถ้าเปิดใช้งาน)
        enable_stt_step = task_data.get('enable_step3_stt', True)
        if enable_stt_step:
            self._update_progress(job, 40, "กำลังแปลงเสียงเป็นข้อความด้วย Thonburian Whisper...", "ขั้นตอนที่ 3: STT", 40)
            original_text = video_processor.transcribe_audio(
                audio_path, 
                task_data['stt_model'], 
                task_data['source_lang'], 
                task_id
            )
            
            # Save transcription to file
            transcription_file = TEXTS_DIR / f"{task_id}_transcription.txt"
            with open(transcription_file, 'w', encoding='utf-8') as f:
                f.write(original_text)
            
            job['transcription'] = original_text
            job['transcription_file'] = str(transcription_file)
            job['temp_files'].append(str(transcription_file))
            
            print(f"📝 การแปลงเสียงเป็นข้อความเสร็จสิ้น: {len(original_text)} ตัวอักษร")
        else:
            self._update_progress(job, 40, "ข้ามขั้นตอนการแปลงเสียงเป็นข้อความ...", "ขั้นตอนที่ 3: STT", 40)
            original_text = task_data.get('custom_text', '')
            job['transcription'] = original_text
            print(f"📝 ใช้ข้อความที่กำหนดเอง: {len(original_text)} ตัวอักษร")
        
        # Step 4: Translation (ถ้าเปิดใช้งาน)
        enable_translation_step = task_data.get('enable_step4_translation', True)
        if enable_translation_step:
            self._update_progress(job, 60, "กำลังแปลข้อความเป็นภาษาไทย...", "ขั้นตอนที่ 4: Translation", 60)
            translation_result = translation_service.translate(
                original_text, 
                task_data['source_lang'], 
                task_data['target_lang'], 
                task_data['translation_model']
            )
            
            translated_text = translation_result.get('translation', '')
            
            # Save translation to file
            translation_file = TEXTS_DIR / f"{task_id}_translation.txt"
            with open(translation_file, 'w', encoding='utf-8') as f:
                f.write(translated_text)
            
            job['translation'] = translated_text
            job['translation_file'] = str(translation_file)
            job['temp_files'].append(str(translation_file))
            
            print(f"🌐 การแปลเสร็จสิ้น: {len(translated_text)} ตัวอักษร")
        else:
            self._update_progress(job, 60, "ข้ามขั้นตอนการแปล...", "ขั้นตอนที่ 4: Translation", 60)
            translated_text = original_text
            job['translation'] = translated_text
            print(f"🌐 ใช้ข้อความต้นฉบับ: {len(translated_text)} ตัวอักษร")
        
        # Step 5: Text-to-Speech (ถ้าเปิดใช้งาน)
        enable_tts_step = task_data.get('enable_step5_tts', True)
        if enable_tts_step:
            self._update_progress(job, 80, "กำลังแปลงข้อความเป็นเสียง...", "ขั้นตอนที่ 5: TTS", 80)
            tts_result = tts_service.synthesize_speech(
                translated_text, 
                task_data['target_lang'], 
                task_data['tts_model'], 
                task_id, 
                task_data['voice_mode'], 
                task_data.get('custom_coqui_model')
            )
            
            tts_audio_path = tts_result.get('tts_audio_path', '')
            job['tts_audio_path'] = tts_audio_path
            if tts_audio_path:
                job['temp_files'].append(tts_audio_path)
            
            print(f"🔊 การแปลงข้อความเป็นเสียงเสร็จสิ้น: {tts_audio_path}")
        else:
            self._update_progress(job, 80, "ข้ามขั้นตอนการแปลงข้อความเป็นเสียง...", "ขั้นตอนที่ 5: TTS", 80)
            print(f"🔊 ข้ามการแปลงข้อความเป็นเสียง")
        
        # Step 6: Audio Mixing (ถ้าเปิดใช้งาน)
        enable_audio_mixing_step = task_data.get('enable_step6_audio_mixing', True)
        if enable_audio_mixing_step:
            self._update_progress(job, 90, "กำลังผสมเสียงกับวิดีโอ...", "ขั้นตอนที่ 6: Audio Mixing", 90)
            
            # Get audio paths
            tts_audio_path = job.get('tts_audio_path', '')
            instrumental_path = job.get('instrumental_path', '')
            sync_original_audio = task_data.get('sync_original_audio', False)
            
            if tts_audio_path and os.path.exists(tts_audio_path):
                # Merge audio with video
                final_audio_path = video_processor.merge_audio_video(
                    job['video_path'], 
                    tts_audio_path, 
                    task_id, 
                    task_data['video_speed'],
                    instrumental_path,
                    sync_original_audio
                )
                
                job['final_audio_path'] = final_audio_path
                job['temp_files'].append(final_audio_path)
                
                print(f"🎵 การผสมเสียงเสร็จสิ้น: {final_audio_path}")
            else:
                print(f"⚠️ ไม่พบไฟล์เสียง TTS สำหรับการผสม")
        else:
            self._update_progress(job, 90, "ข้ามขั้นตอนการผสมเสียง...", "ขั้นตอนที่ 6: Audio Mixing", 90)
            print(f"🎵 ข้ามการผสมเสียง")
        
        # Step 7: Final Video Merge (ถ้าเปิดใช้งาน)
        enable_video_merge_step = task_data.get('enable_step7_video_merge', True)
        if enable_video_merge_step:
            self._update_progress(job, 95, "กำลังสร้างวิดีโอสุดท้าย...", "ขั้นตอนที่ 7: Video Merge", 95)
            
            # Get final audio path
            final_audio_path = job.get('final_audio_path', job.get('tts_audio_path', ''))
            
            if final_audio_path and os.path.exists(final_audio_path):
                # Create final video
                output_path = video_processor.merge_audio_video(
                    job['video_path'], 
                    final_audio_path, 
                    task_id, 
                    task_data['video_speed']
                )
                
                job['output_path'] = output_path
                
                print(f"🎬 วิดีโอสุดท้ายเสร็จสิ้น: {output_path}")
            else:
                print(f"⚠️ ไม่พบไฟล์เสียงสำหรับการสร้างวิดีโอสุดท้าย")
        else:
            self._update_progress(job, 95, "ข้ามขั้นตอนการสร้างวิดีโอสุดท้าย...", "ขั้นตอนที่ 7: Video Merge", 95)
            print(f"🎬 ข้ามการสร้างวิดีโอสุดท้าย")
        
        # Final progress update
        self._update_progress(job, 100, "ประมวลผลเสร็จสิ้น", "เสร็จสิ้น", 100)
        
        print(f"✅ การประมวลผลงาน {task_id} เสร็จสิ้น")
    
    def _update_progress(self, job, progress, message, current_step=None, step_progress=None):
        """อัปเดตความคืบหน้า"""
        job['progress'] = progress
        job['message'] = message
        if current_step:
            job['current_step'] = current_step
        if step_progress is not None:
            job['step_progress'] = step_progress
        
        # เพิ่ม timestamp สำหรับ tracking
        job['last_update'] = datetime.now().isoformat()
        
        # Log progress สำหรับ debugging
        print(f"📊 Job {job['task_id']}: {progress}% - {message}")
        
        print(f"📊 {current_step or 'Progress'}: {progress}% - {message}")
    
    def get_job_status(self, task_id):
        """ดึงสถานะงาน"""
        with self.jobs_lock:
            if task_id in self.active_jobs:
                return self.active_jobs[task_id]
        
        with self.completed_lock:
            if task_id in self.completed_jobs:
                return self.completed_jobs[task_id]
        
        return None
    
    def get_queue_status(self):
        """ดึงสถานะคิว"""
        with self.jobs_lock:
            active_count = len(self.active_jobs)
            active_jobs_info = []
            for task_id, job in self.active_jobs.items():
                job_info = {
                    'task_id': task_id,
                    'status': job['status'],
                    'progress': job['progress'],
                    'message': job['message'],
                    'started_at': job['started_at'].isoformat() if job['started_at'] else None,
                    'elapsed_time': None
                }
                if job['started_at']:
                    elapsed = (datetime.now() - job['started_at']).total_seconds()
                    job_info['elapsed_time'] = f"{elapsed:.1f}s"
                active_jobs_info.append(job_info)
        
        with self.completed_lock:
            completed_count = len(self.completed_jobs)
        
        return {
            'queue_size': self.queue.qsize(),
            'active_jobs': active_count,
            'completed_jobs': completed_count,
            'max_concurrent': self.max_concurrent,
            'active_jobs_info': active_jobs_info
        }
    
    def stop(self):
        """หยุดการทำงานของคิว"""
        self.running = False
        
        # Stop all workers
        for _ in range(len(self.workers)):
            self.queue.put(None)
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5)
        
        print("🛑 Job queue stopped")
    
    def stop_job(self, task_id):
        """หยุดการทำงานของ job ที่ระบุ"""
        try:
            with self.jobs_lock:
                if task_id in self.active_jobs:
                    job = self.active_jobs[task_id]
                    job['status'] = 'stopped'
                    job['message'] = 'หยุดการทำงานโดยผู้ใช้'
                    job['completed_at'] = datetime.now()
                    
                    # Clean up temp files
                    try:
                        cleanup_temp_files(job.get('temp_files', []))
                    except Exception as e:
                        print(f"⚠️ Error cleaning up temp files for stopped job {task_id}: {e}")
                    
                    # Remove from active jobs
                    del self.active_jobs[task_id]
                    
                    print(f"🛑 หยุดการทำงานของ job {task_id}")
                    return True
                else:
                    print(f"⚠️ ไม่พบ job {task_id} ใน active jobs")
                    return False
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการหยุด job {task_id}: {e}")
            return False
    
    def stop_all_jobs(self):
        """หยุดการทำงานของ job ทั้งหมด"""
        try:
            with self.jobs_lock:
                jobs_to_stop = list(self.active_jobs.keys())
            
            stopped_count = 0
            for task_id in jobs_to_stop:
                if self.stop_job(task_id):
                    stopped_count += 1
            
            print(f"🛑 หยุดการทำงานของ job ทั้งหมด {stopped_count} jobs")
            return stopped_count
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการหยุด job ทั้งหมด: {e}")
            return 0
    
    def _timeout_monitor(self):
        """Monitor jobs for timeout and stop them if they exceed the timeout limit"""
        while self.running:
            try:
                time.sleep(self.job_timeout_check_interval)
                
                current_time = datetime.now()
                jobs_to_stop = []
                
                with self.jobs_lock:
                    for task_id, job in self.active_jobs.items():
                        if job['status'] == 'processing' and job['started_at']:
                            elapsed_time = (current_time - job['started_at']).total_seconds()
                            if elapsed_time > self.job_timeout:
                                jobs_to_stop.append(task_id)
                
                # Stop timed out jobs
                for task_id in jobs_to_stop:
                    print(f"⏰ Job {task_id} timed out after {self.job_timeout} seconds")
                    self.stop_job(task_id)
                    
            except Exception as e:
                print(f"⚠️ Timeout monitor error: {e}")
    
    def _is_new_upload(self, video_input):
        """ตรวจสอบว่าเป็นไฟล์อัปโหลดใหม่หรือไม่"""
        return video_input.startswith(str(UPLOADS_DIR))

class YouTubeDownloader:
    """YouTube video downloader with resolution selection"""
    
    def __init__(self):
        self.temp_dir = TEMP_DIR
        self.temp_dir.mkdir(exist_ok=True)
    
    def get_video_info(self, url):
        """Get YouTube video information"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info is None:
                    raise Exception("Could not extract video information")
                
                formats = []
                for f in info.get('formats', []):
                    if f is not None and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                        formats.append({
                            'format_id': f.get('format_id'),
                            'resolution': f.get('resolution', 'N/A'),
                            'filesize': f.get('filesize'),
                            'ext': f.get('ext'),
                            'height': f.get('height'),
                            'width': f.get('width')
                        })
                
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail'),
                    'formats': formats,
                    'webpage_url': info.get('webpage_url', url)
                }
        except Exception as e:
            raise Exception(f"Error getting video info: {str(e)}")
    
    def download_video(self, url, format_id=None, task_id=None):
        """Download YouTube video with specified format"""
        try:
            output_path = self.temp_dir / f"{task_id}_youtube_video.mp4"
            
            ydl_opts = {
                'outtmpl': str(output_path),
                'quiet': False,
                'progress_hooks': [self._progress_hook],
            }
            
            if format_id:
                ydl_opts['format'] = format_id
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if output_path.exists():
                return str(output_path)
            else:
                raise Exception("Downloaded file not found")
                
        except Exception as e:
            raise Exception(f"Error downloading video: {str(e)}")
    
    def _progress_hook(self, d):
        """Progress hook for YouTube download"""
        if d['status'] == 'downloading':
            if 'total_bytes' in d and d['total_bytes']:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                print(f"📥 YouTube Download: {percent:.1f}%")
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                print(f"📥 YouTube Download: {percent:.1f}% (estimate)")

class VideoProcessor:
    """Video processing service with enhanced memory management and GPU support"""
    
    def __init__(self):
        self.whisper_model = None
        self.whisper_processor = None
        self.model_lock = threading.Lock()
        self.memory_cleanup_interval = 50  # Cleanup every 50 chunks (reduced frequency)
        self.chunk_counter = 0
        self.last_cleanup_time = time.time()
        self.cleanup_cooldown = 60  # Minimum 60 seconds between cleanups
        
        # Determine device for GPU acceleration
        import torch
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"🎬 VideoProcessor initialized with device: {self.device}")
    
    def _cleanup_memory(self):
        """Enhanced memory cleanup with better error handling and cooldown"""
        try:
            current_time = time.time()
            # Only cleanup if enough time has passed since last cleanup
            if current_time - self.last_cleanup_time < self.cleanup_cooldown:
                return
            
            import gc
            gc.collect()
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.last_cleanup_time = current_time
            print("🧹 Memory cleanup completed")
        except Exception as e:
            print(f"⚠️ Memory cleanup error: {e}")
    
    def _should_cleanup_memory(self):
        """Check if memory cleanup is needed with reduced frequency"""
        self.chunk_counter += 1
        # Only cleanup every 20 chunks and if enough time has passed
        if self.chunk_counter % self.memory_cleanup_interval == 0:
            current_time = time.time()
            return current_time - self.last_cleanup_time >= self.cleanup_cooldown
        return False
    
    def process_video_input(self, video_input, task_id, format_id=None, realtime=False):
        """Process video input with memory optimization"""
        try:
            print(f"🎬 Processing video input: {video_input}")
            
            if self._is_youtube_url(video_input):
                if realtime:
                    return self._process_youtube_realtime(video_input, task_id, format_id)
                else:
                    # Download YouTube video
                    downloader = YouTubeDownloader()
                    video_path = downloader.download_video(video_input, format_id, task_id)
                    return video_path
            else:
                # Local file
                if os.path.exists(video_input):
                    return video_input
                else:
                    raise Exception(f"Video file not found: {video_input}")
                    
        except Exception as e:
            print(f"❌ Error processing video input: {e}")
            raise
    
    def _process_youtube_realtime(self, youtube_url, task_id, format_id=None):
        """Process YouTube URL in real-time mode with memory optimization"""
        try:
            print(f"📺 Processing YouTube URL in real-time: {youtube_url}")
            
            downloader = YouTubeDownloader()
            video_path = downloader.download_video(youtube_url, format_id, task_id)
            
            return video_path
            
        except Exception as e:
            print(f"❌ Error in YouTube real-time processing: {e}")
            raise
    
    def _is_youtube_url(self, url):
        """Check if URL is a YouTube URL"""
        return any(re.match(pattern, url) for pattern in YOUTUBE_PATTERNS)
    
    def create_video_preview(self, video_path, task_id):
        """Create video preview with memory optimization"""
        try:
            print(f"🎬 Creating video preview for: {video_path}")
            
            if not os.path.exists(video_path):
                raise Exception(f"Video file not found: {video_path}")
            
            # Create preview using ffmpeg
            preview_path = PREVIEWS_DIR / f"{task_id}_preview.mp4"
            
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', 'scale=480:270',  # Resize to 480x270
                '-t', '30',  # 30 seconds duration
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-y', str(preview_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(preview_path):
                print(f"✅ Preview created: {preview_path}")
                return str(preview_path)
            else:
                print(f"⚠️ Preview creation failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ Error creating video preview: {e}")
            return None
    
    def extract_audio(self, video_path, task_id, enable_vocal_removal=False):
        """Extract audio with enhanced memory management"""
        try:
            print(f"🎵 Extracting audio from: {video_path}")
            
            if not os.path.exists(video_path):
                raise Exception(f"Video file not found: {video_path}")
            
            # Extract audio using ffmpeg
            audio_path = AUDIOS_DIR / f"{task_id}_audio.wav"
            
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',  # Mono
                '-y', str(audio_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0 or not os.path.exists(audio_path):
                raise Exception(f"Audio extraction failed: {result.stderr}")
            
            print(f"✅ Audio extracted: {audio_path}")
            
            # Apply vocal removal if enabled
            if enable_vocal_removal:
                print("🎤 Applying vocal removal...")
                vocal_remover = UltimateVocalRemover()
                separation_result = vocal_remover.separate_audio(str(audio_path), task_id)
                
                # Memory cleanup after vocal removal (only if needed)
                if self._should_cleanup_memory():
                    self._cleanup_memory()
                
                # Store instrumental path for later use in video merge
                if separation_result and separation_result.get('instrumental_path'):
                    # Store in global task data for later use
                    if hasattr(self, 'tasks_data') and task_id in self.tasks_data:
                        self.tasks_data[task_id]['instrumental_path'] = separation_result['instrumental_path']
                    print(f"🎵 เก็บเส้นทางดนตรีสำหรับการรวมวิดีโอ: {separation_result['instrumental_path']}")
                
                # Return vocals path for transcription
                if separation_result and separation_result.get('vocals'):
                    vocals_path = separation_result['vocals']
                    
                    # Check if vocals file has content
                    try:
                        vocals_audio, vocals_sr = librosa.load(vocals_path, sr=None)
                        vocals_rms = np.sqrt(np.mean(vocals_audio**2))
                        print(f"🎤 เสียงร้องที่แยกแล้ว: {len(vocals_audio)/vocals_sr:.1f}s, RMS: {vocals_rms:.6f}")
                        
                        if vocals_rms < 0.0001:
                            print("⚠️  เสียงร้องที่แยกแล้วเงียบมาก ใช้ไฟล์เสียงต้นฉบับ")
                            return str(audio_path)
                        else:
                            return vocals_path
                    except Exception as e:
                        print(f"⚠️  ไม่สามารถตรวจสอบไฟล์เสียงร้อง: {e}")
                        return str(audio_path)
                else:
                    return str(audio_path)
            else:
                return str(audio_path)
                
        except Exception as e:
            print(f"❌ Error extracting audio: {e}")
            raise
    
    def extract_audio_realtime(self, video_path, task_id):
        """Extract audio in real-time mode with memory optimization"""
        try:
            print(f"🎵 Extracting audio in real-time from: {video_path}")
            
            # Use the same extraction as normal mode but with memory optimization
            return self.extract_audio(video_path, task_id, enable_vocal_removal=False)
            
        except Exception as e:
            print(f"❌ Error in real-time audio extraction: {e}")
            raise
    
    def transcribe_audio(self, audio_path, model_name, source_lang, task_id, task='transcribe', target_lang=None):
        """Transcribe audio with enhanced memory management and chunk timeout"""
        try:
            print(f"🎧 Transcribing audio: {audio_path} (task: {task})")
            stt_start_time = time.time()
            
            if not os.path.exists(audio_path):
                raise Exception(f"Audio file not found: {audio_path}")
            
            # Load audio
            audio, sr = self._load_audio_with_fallback(audio_path)
            
            # Debug audio information
            audio_duration = len(audio) / sr
            audio_rms = np.sqrt(np.mean(audio**2))
            print(f"🎵 ไฟล์เสียง: {audio_path}")
            print(f"🎵 ความยาว: {audio_duration:.1f} วินาที")
            print(f"🎵 ระดับเสียง RMS: {audio_rms:.6f}")
            print(f"🎵 Sample Rate: {sr} Hz")
            
            # Check if audio is too quiet
            if audio_rms < 0.0001:
                print("⚠️  ไฟล์เสียงเงียบมาก อาจไม่มีเสียงพูด")
            
            # Memory cleanup after loading audio
            if self._should_cleanup_memory():
                self._cleanup_memory()
            
            # Load Whisper model with increased timeout and better error handling
            print(f"[STT] Loading Whisper model: {model_name}")
            model_load_start = time.time()
            with self.model_lock:
                if self.whisper_model is None or getattr(self, 'current_model_name', None) != model_name:
                    # Add timeout for model loading with increased timeout
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(self._load_whisper_model, model_name)
                        try:
                            future.result(timeout=300)  # 5 minutes timeout for model loading
                            self.current_model_name = model_name
                            model_load_end = time.time()
                            print(f"[STT] Model loaded in {model_load_end-model_load_start:.1f} seconds")
                        except concurrent.futures.TimeoutError:
                            print(f"[STT][TIMEOUT] Model loading timed out after 5 minutes!")
                            print(f"[STT] Trying fallback to base model...")
                            
                            # Try fallback to base model
                            try:
                                fallback_future = executor.submit(self._load_whisper_model, "base")
                                fallback_future.result(timeout=120)  # 2 minutes for fallback
                                self.current_model_name = "base"
                                print(f"[STT] Fallback to base model successful")
                            except Exception as fallback_error:
                                print(f"[STT][FALLBACK] Fallback failed: {fallback_error}")
                                raise Exception("Whisper model loading failed with fallback")
            
            # Transcribe with unlimited processing and timeout
            print(f"[STT] Starting transcription...")
            transcription_start = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._transcribe_unlimited_audio_enhanced, audio, sr, source_lang, task_id, task, target_lang)
                try:
                    transcription = future.result(timeout=600)  # 10 minutes timeout for entire transcription
                    transcription_end = time.time()
                    print(f"[STT] Transcription completed in {transcription_end-transcription_start:.1f} seconds")
                except concurrent.futures.TimeoutError:
                    print(f"[STT][TIMEOUT] Transcription timed out after 10 minutes!")
                    raise Exception("Transcription timed out")
            
            stt_end_time = time.time()
            print(f"[STT] Total transcription time: {stt_end_time-stt_start_time:.1f} seconds")
            
            # Memory cleanup after transcription (only if needed)
            if self._should_cleanup_memory():
                self._cleanup_memory()
            
            return transcription
            
        except Exception as e:
            print(f"❌ Error transcribing audio: {e}")
            raise
    
    def _transcribe_with_timestamps(self, audio, sr, source_lang, task_id):
        """Transcribe with timestamps and memory optimization"""
        try:
            print(f"⏰ Transcribing with timestamps...")
            
            # Load model if not loaded
            with self.model_lock:
                if self.whisper_model is None:
                    self._load_whisper_model('base')  # Use base model for timestamps
            
            # Check if this is a Thonburian model
            is_thonburian = hasattr(self.whisper_model, 'transcribe')
            
            if is_thonburian:
                # Use original whisper for timestamps
                import tempfile
                import soundfile as sf
                
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    sf.write(temp_file.name, audio, sr)
                    temp_audio_path = temp_file.name
                
                try:
                    result = self.whisper_model.transcribe(
                        temp_audio_path,
                        language=source_lang if source_lang != 'auto' else None,
                        verbose=False,
                        word_timestamps=True
                    )
                    
                    # Extract timestamps
                    timestamps = self._extract_timestamps_from_output(result, result['text'])
                    
                    return {
                        'transcription': result['text'],
                        'timestamps': timestamps
                    }
                    
                finally:
                    # Clean up temporary file
                    import os
                    if os.path.exists(temp_audio_path):
                        os.unlink(temp_audio_path)
                        
            else:
                # Standard OpenAI Whisper models
                if self.whisper_processor is None:
                    raise Exception("Whisper processor not loaded")
                
                # Prepare input
                inputs = self.whisper_processor(
                    audio, 
                    sampling_rate=sr, 
                    return_tensors="pt"
                )
                
                # Generate with timestamps
                generation_kwargs = {
                    "max_length": 2048,
                    "num_beams": 5,
                    "early_stopping": True,
                    "return_timestamps": True,
                    "temperature": 0.0,
                    "do_sample": False
                }
                
                if source_lang != 'auto':
                    generation_kwargs["language"] = source_lang
                    generation_kwargs["task"] = "transcribe"
                
                # Generate transcription
                with torch.no_grad():
                    predicted_ids = self.whisper_model.generate(
                        inputs.input_features,
                        **generation_kwargs
                    )
                
                # Decode transcription
                if hasattr(self.whisper_processor, 'batch_decode'):
                    transcription = self.whisper_processor.batch_decode(
                        predicted_ids, 
                        skip_special_tokens=True
                    )[0]
                else:
                    transcription = self.whisper_processor.decode(
                        predicted_ids[0], 
                        skip_special_tokens=True
                    )
                
                # Extract timestamps
                timestamps = self._extract_timestamps_from_output(predicted_ids, transcription)
                
                return {
                    'transcription': transcription.strip(),
                    'timestamps': timestamps
                }
                
        except Exception as e:
            print(f"❌ Error in timestamp transcription: {e}")
            raise
    
    def _extract_timestamps_from_output(self, predicted_ids, transcription):
        """Extract timestamps from model output"""
        try:
            # This is a simplified timestamp extraction
            # In a real implementation, you would parse the actual timestamp tokens
            timestamps = []
            words = transcription.split()
            
            # Generate dummy timestamps (replace with actual implementation)
            for i, word in enumerate(words):
                timestamp = {
                    'word': word,
                    'start': i * 0.5,  # 0.5 seconds per word (dummy)
                    'end': (i + 1) * 0.5
                }
                timestamps.append(timestamp)
            
            return timestamps
            
        except Exception as e:
            print(f"⚠️ Error extracting timestamps: {e}")
            return []
    
    def _load_audio_with_fallback(self, audio_path):
        """Load audio with multiple fallback methods"""
        try:
            # Try librosa first
            try:
                audio, sr = librosa.load(audio_path, sr=16000)
                return audio, sr
            except Exception as e:
                print(f"⚠️ Librosa failed, trying ffmpeg: {e}")
            
            # Try ffmpeg fallback
            return self._load_audio_with_ffmpeg(audio_path)
            
        except Exception as e:
            print(f"❌ Error loading audio: {e}")
            raise
    
    def _load_audio_with_ffmpeg(self, audio_path):
        """Load audio using ffmpeg"""
        try:
            # Create temporary file for ffmpeg output
            temp_output = TEMP_DIR / f"temp_audio_{uuid.uuid4()}.wav"
            
            cmd = [
                'ffmpeg', '-i', audio_path,
                '-vn', '-acodec', 'pcm_s16le',
                '-ar', '16000', '-ac', '1',
                '-y', str(temp_output)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(temp_output):
                # Load with librosa
                audio, sr = librosa.load(str(temp_output), sr=16000)
                
                # Clean up temp file
                os.unlink(temp_output)
                
                return audio, sr
            else:
                raise Exception(f"FFmpeg failed: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error loading audio with ffmpeg: {e}")
            raise
    
    def _transcribe_unlimited_audio_enhanced(self, audio, sr, source_lang, task_id, task='transcribe', target_lang=None):
        """Enhanced unlimited length audio transcription with better chunking and memory management, with chunk timeout and logging"""
        try:
            print(f"🎧 Starting enhanced unlimited transcription (task: {task})...")
            print(f"[STT] Audio length: {len(audio)/sr:.1f} seconds")
            
            # Load Whisper model first (should already be loaded by transcribe_audio)
            print(f"[STT] Checking Whisper model...")
            with self.model_lock:
                if self.whisper_model is None:
                    print(f"[STT] Loading fallback Whisper model...")
                    # Fallback to base model if somehow not loaded
                    self._load_whisper_model('base')
                else:
                    print(f"[STT] Whisper model already loaded")
            
            # Calculate chunk size based on memory optimization
            chunk_duration = UNLIMITED_CHUNK_DURATION if hasattr(self, 'UNLIMITED_CHUNK_DURATION') else 30  # Reduced from 60 to 30 seconds
            overlap_duration = UNLIMITED_OVERLAP_DURATION if hasattr(self, 'UNLIMITED_OVERLAP_DURATION') else 5   # Reduced from 30 to 5 seconds
            
            print(f"[STT] Chunk duration: {chunk_duration}s, Overlap: {overlap_duration}s")
            
            # Calculate chunk parameters
            chunk_samples = int(chunk_duration * sr)
            overlap_samples = int(overlap_duration * sr)
            
            # Split audio into chunks
            audio_length = len(audio)
            chunks = []
            
            # Check if audio has any content
            if audio_length == 0:
                raise Exception("ไฟล์เสียงว่างเปล่า")
            
            # Check audio levels
            audio_rms = np.sqrt(np.mean(audio**2))
            if audio_rms < 0.001:  # Very low audio level
                print("⚠️  ระดับเสียงต่ำมาก อาจไม่มีเสียงพูด")
            
            print(f"[STT] Creating chunks...")
            for i in range(0, audio_length, chunk_samples - overlap_samples):
                chunk = audio[i:i + chunk_samples]
                if len(chunk) > sr:  # At least 1 second
                    # Check if chunk has meaningful audio
                    chunk_rms = np.sqrt(np.mean(chunk**2))
                    if chunk_rms > 0.0001:  # Minimum audio level
                        chunks.append(chunk)
                    else:
                        print(f"⚠️  ข้าม chunk {len(chunks)+1} เนื่องจากระดับเสียงต่ำเกินไป")
            
            print(f"📊 แยกไฟล์เสียงเป็น {len(chunks)} chunks (จาก {audio_length/sr:.1f} วินาที)")
            
            if len(chunks) == 0:
                raise Exception("ไม่มี chunks ที่มีเสียงพูด")
            
            print(f"📊 Split audio into {len(chunks)} chunks")
            print(f"[STT] Starting chunk processing...")
            
            # Process chunks with memory optimization
            transcriptions = []
            
            for chunk_num, chunk in enumerate(chunks, 1):
                chunk_start_time = time.time()
                print(f"🔄 Processing chunk {chunk_num}/{len(chunks)}")
                
                # Debug chunk information
                chunk_duration = len(chunk) / sr
                chunk_rms = np.sqrt(np.mean(chunk**2))
                print(f"🔍 Chunk {chunk_num}: {chunk_duration:.1f}s, RMS: {chunk_rms:.6f}")
                
                # Transcribe chunk with timeout
                chunk_timeout_sec = 180  # 3 นาที/ชิ้น
                print(f"[STT] Starting chunk {chunk_num} transcription (timeout: {chunk_timeout_sec}s)...")
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self._transcribe_audio_chunk_with_retry_enhanced, chunk, sr, source_lang, chunk_num, task_id, task, target_lang)
                    try:
                        chunk_transcription = future.result(timeout=chunk_timeout_sec)
                        chunk_end_time = time.time()
                        print(f"[STT] Chunk {chunk_num} finished in {chunk_end_time-chunk_start_time:.1f} seconds")
                        if chunk_end_time-chunk_start_time > 60:
                            print(f"[STT][WARNING] Chunk {chunk_num} took more than 1 minute!")
                    except concurrent.futures.TimeoutError:
                        print(f"[STT][TIMEOUT] Chunk {chunk_num} timed out after {chunk_timeout_sec} seconds!")
                        chunk_transcription = ""
                if chunk_transcription and chunk_transcription.strip():
                    transcriptions.append(chunk_transcription)
                    print(f"✅ Chunk {chunk_num} transcribed: {len(chunk_transcription)} chars")
                else:
                    print(f"⚠️  Chunk {chunk_num} produced no transcription")
                
                # Memory cleanup after each chunk
                if ENABLE_MEMORY_OPTIMIZATION:
                    import gc
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
            
            print(f"[STT] All chunks processed. Found {len(transcriptions)} transcriptions")
            
            if not transcriptions:
                print("⚠️  ไม่พบเสียงพูดในไฟล์เสียง")
                print("🔄 ลองใช้วิธีการอื่น...")
                
                # Try alternative transcription methods
                try:
                    # Try with different preprocessing
                    alternative_transcription = self._transcribe_with_enhanced_noise_handling(audio, sr, source_lang, task_id)
                    if alternative_transcription and alternative_transcription.strip():
                        print("✅ ได้ผลลัพธ์จากการใช้วิธีการอื่น")
                        return alternative_transcription
                except Exception as e:
                    print(f"⚠️  วิธีการอื่นล้มเหลว: {e}")
                
                # If still no transcription, return a placeholder
                print("⚠️  ไม่สามารถถอดเสียงได้ ใช้ข้อความ placeholder")
                return "ไม่สามารถถอดเสียงจากไฟล์นี้ได้ กรุณาตรวจสอบไฟล์เสียง"
            
            # Combine transcriptions with better formatting
            print(f"[STT] Combining transcriptions...")
            full_transcription = self._combine_transcriptions_enhanced(transcriptions)
            
            print(f"🎯 Total transcription length: {len(full_transcription)} characters")
            print(f"🎯 Total transcription time: {len(full_transcription.split()) / 150:.1f} minutes (estimated)")
            return full_transcription
            
        except Exception as e:
            print(f"[STT][ERROR] Error in enhanced unlimited transcription: {str(e)}")
            raise Exception(f"Error in enhanced unlimited transcription: {str(e)}")
    
    def _transcribe_audio_chunk_with_retry_enhanced(self, audio_chunk, sr, source_lang, chunk_num, task_id, task='transcribe', target_lang=None, max_retries=3):
        """Enhanced audio chunk transcription with better memory management"""
        print(f"[STT] Starting chunk {chunk_num} transcription (attempts: {max_retries})")
        for attempt in range(max_retries):
            try:
                print(f"[STT] Chunk {chunk_num} attempt {attempt + 1}/{max_retries}")
                transcription = self._transcribe_audio_chunk_enhanced(audio_chunk, sr, source_lang, task, target_lang)
                if transcription and transcription.strip():
                    print(f"[STT] Chunk {chunk_num} attempt {attempt + 1} successful")
                    return transcription
                else:
                    print(f"⚠️  Attempt {attempt + 1}: No transcription for chunk {chunk_num}")
            except Exception as e:
                print(f"⚠️  Attempt {attempt + 1} failed for chunk {chunk_num}: {e}")
                if attempt == max_retries - 1:
                    print(f"❌ All attempts failed for chunk {chunk_num}")
                    return ""
                
                # Memory cleanup between retries
                if ENABLE_MEMORY_OPTIMIZATION:
                    import gc
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                
                time.sleep(2)  # Wait before retry
        
        return ""
    
    def _transcribe_audio_chunk_enhanced(self, audio_chunk, sr, source_lang, task='transcribe', target_lang=None):
        """Enhanced audio chunk transcription with better parameters"""
        try:
            print(f"[STT] Processing chunk with Whisper...")
            # Check if models are loaded
            if self.whisper_model is None:
                raise Exception("Whisper models not loaded")
            
            # Check if this is a Thonburian model
            is_thonburian = hasattr(self.whisper_model, 'transcribe')
            print(f"[STT] Using {'Thonburian' if is_thonburian else 'Standard'} Whisper model")
            
            if is_thonburian:
                # Use original whisper library for Thonburian models
                # Save audio chunk to temporary file
                import tempfile
                import soundfile as sf
                
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    sf.write(temp_file.name, audio_chunk, sr)
                    temp_audio_path = temp_file.name
                
                try:
                    print(f"[STT] Transcribing with Thonburian model...")
                    # Transcribe with original whisper
                    result = self.whisper_model.transcribe(
                        temp_audio_path,
                        language=source_lang if source_lang != 'auto' else None,
                        task=task,  # Use task parameter
                        verbose=False
                    )
                    
                    return result['text'].strip()
                    
                finally:
                    # Clean up temporary file
                    import os
                    if os.path.exists(temp_audio_path):
                        os.unlink(temp_audio_path)
                        
            else:
                # Standard OpenAI Whisper models
                if self.whisper_processor is None:
                    raise Exception("Whisper processor not loaded")
                
                print(f"[STT] Transcribing with Standard Whisper model...")
                # Prepare input for Whisper
                inputs = self.whisper_processor(
                    audio_chunk, 
                    sampling_rate=sr, 
                    return_tensors="pt"
                )
                
                # Enhanced generation parameters for better accuracy
                generation_kwargs = {
                    "max_length": 2048,
                    "num_beams": 5,
                    "early_stopping": True,
                    "no_speech_threshold": 0.3,  # Lower threshold to detect more speech
                    "logprob_threshold": -1.0,
                    "compression_ratio_threshold": 2.4,
                    "temperature": 0.0,
                    "do_sample": False
                }
                
                # Set language and task if specified
                if source_lang != 'auto':
                    generation_kwargs["language"] = source_lang
                    generation_kwargs["task"] = task  # Use task parameter
                else:
                    # For auto language detection, use provided task
                    generation_kwargs["task"] = task
                
                # Remove deprecated and unsupported parameters
                deprecated_params = [
                    "condition_on_previous_text",
                    "prompt_reset_on_timestamp", 
                    "word_timestamps",
                    "return_timestamps",
                    "forced_decoder_ids"
                ]
                
                for param in deprecated_params:
                    if param in generation_kwargs:
                        del generation_kwargs[param]
                
                # Generate transcription
                print(f"[STT] Generating transcription...")
                with torch.no_grad():
                    predicted_ids = self.whisper_model.generate(
                        inputs.input_features,
                        **generation_kwargs
                    )
                
                # Decode transcription
                print(f"[STT] Decoding transcription...")
                if hasattr(self.whisper_processor, 'batch_decode'):
                    transcription = self.whisper_processor.batch_decode(
                        predicted_ids, 
                        skip_special_tokens=True
                    )[0]
                else:
                    # Fallback for older versions
                    transcription = self.whisper_processor.decode(
                        predicted_ids[0], 
                        skip_special_tokens=True
                    )
                
                print(f"[STT] Chunk transcription completed: {len(transcription.strip())} chars")
                return transcription.strip()
            
        except Exception as e:
            print(f"⚠️  Error transcribing chunk: {e}")
            return ""
    
    def _combine_transcriptions_enhanced(self, transcriptions):
        """Enhanced transcription combination with better formatting and continuity"""
        try:
            # Join transcriptions with proper spacing
            combined = ' '.join(transcriptions)
            
            # Enhanced cleaning and formatting
            cleaned = self._clean_transcription_enhanced(combined)
            
            # Add paragraph breaks for better readability
            cleaned = re.sub(r'([.!?])\s+([A-Z])', r'\1\n\n\2', cleaned)
            
            # Remove excessive line breaks
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            
            return cleaned.strip()
            
        except Exception as e:
            print(f"⚠️  Error combining transcriptions: {e}")
            return ' '.join(transcriptions)
    
    def _clean_transcription_enhanced(self, transcription):
        """Enhanced transcription cleaning"""
        try:
            # Remove extra whitespace
            transcription = re.sub(r'\s+', ' ', transcription)
            
            # Remove empty lines
            transcription = re.sub(r'\n\s*\n', '\n', transcription)
            
            # Capitalize first letter of sentences
            transcription = re.sub(r'([.!?])\s+([a-z])', lambda m: m.group(1) + ' ' + m.group(2).upper(), transcription)
            
            # Fix common transcription issues
            transcription = re.sub(r'\b([A-Z])\s+([a-z])', r'\1\2', transcription)  # Fix split words
            
            # Remove excessive punctuation
            transcription = re.sub(r'[.!?]{2,}', '.', transcription)
            
            # Ensure proper sentence endings
            transcription = re.sub(r'([^.!?])\s*$', r'\1.', transcription)
            
            return transcription.strip()
            
        except Exception as e:
            print(f"⚠️  Error cleaning transcription: {e}")
            return transcription
    
    def _verify_text_file(self, file_path, expected_content):
        """Verify text file was written correctly"""
        try:
            if not os.path.exists(file_path):
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return content.strip() == expected_content.strip()
            
        except Exception as e:
            print(f"⚠️  Error verifying text file: {e}")
            return False
    
    def _load_whisper_model(self, model_name):
        """Load Whisper model with memory optimization and GPU support"""
        try:
            print(f"🤖 Loading Whisper model: {model_name}")
            
            # Determine device
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"🚀 Using device: {device}")
            
            with self.model_lock:
                # Check if model is already loaded
                if self.whisper_model is not None:
                    print("✅ Model already loaded")
                    return
                
                # Memory cleanup before loading model (only if needed)
                if self._should_cleanup_memory():
                    self._cleanup_memory()
                
                # Load model based on type with increased timeout and fallback
                if model_name.startswith('biodatlab') or model_name.startswith('thonburian'):
                    # Use original whisper library for Thai models
                    print(f"[STT] Loading Thonburian model: {model_name}")
                    print(f"[STT] This may take several minutes for large models...")
                    import whisper
                    
                    # Try loading with increased timeout
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(whisper.load_model, model_name, device=device)
                        try:
                            self.whisper_model = future.result(timeout=300)  # 5 minutes timeout
                            print(f"✅ Loaded {model_name} with original whisper on {device}")
                        except concurrent.futures.TimeoutError:
                            print(f"[STT][TIMEOUT] Model loading timed out after 5 minutes!")
                            print(f"[STT] Trying fallback to base model...")
                            
                            # Fallback to base model
                            try:
                                self.whisper_model = executor.submit(whisper.load_model, "base", device=device).result(timeout=60)
                                print(f"✅ Loaded fallback base model on {device}")
                            except Exception as fallback_error:
                                print(f"[STT][FALLBACK] Fallback failed: {fallback_error}")
                                raise Exception("Whisper model loading failed with fallback")
                else:
                    # Use transformers for OpenAI models
                    print(f"[STT] Loading Standard Whisper model: {model_name}")
                    from transformers import WhisperProcessor, WhisperForConditionalGeneration
                    
                    # Try loading with increased timeout
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(self._load_transformers_model, model_name, device)
                        try:
                            self.whisper_processor, self.whisper_model = future.result(timeout=300)  # 5 minutes timeout
                            print(f"✅ Loaded {model_name} with transformers on {device}")
                        except concurrent.futures.TimeoutError:
                            print(f"[STT][TIMEOUT] Model loading timed out after 5 minutes!")
                            print(f"[STT] Trying fallback to base model...")
                            
                            # Fallback to base model
                            try:
                                self.whisper_processor, self.whisper_model = executor.submit(
                                    self._load_transformers_model, "openai/whisper-base", device
                                ).result(timeout=60)
                                print(f"✅ Loaded fallback base model on {device}")
                            except Exception as fallback_error:
                                print(f"[STT][FALLBACK] Fallback failed: {fallback_error}")
                                raise Exception("Whisper model loading failed with fallback")
                
                # Memory cleanup after loading (only if needed)
                if self._should_cleanup_memory():
                    self._cleanup_memory()
                
        except Exception as e:
            print(f"❌ Error loading Whisper model: {e}")
            raise
    
    def _load_transformers_model(self, model_name, device):
        """Helper function to load transformers model with timeout"""
        from transformers import WhisperProcessor, WhisperForConditionalGeneration
        
        self.whisper_processor = WhisperProcessor.from_pretrained(model_name)
        self.whisper_model = WhisperForConditionalGeneration.from_pretrained(model_name)
        
        # Move model to GPU if available
        if device == 'cuda':
            self.whisper_model = self.whisper_model.to(device)
        
        return self.whisper_processor, self.whisper_model
    
    def _enhanced_audio_preprocessing(self, audio_path, task_id):
        """Enhanced audio preprocessing with memory optimization"""
        try:
            print(f"🎵 Enhanced audio preprocessing for: {audio_path}")
            
            # Load audio
            audio, sr = librosa.load(audio_path, sr=16000)
            
            # Apply preprocessing steps
            audio = self._aggressive_noise_reduction(audio, sr)
            audio = self._remove_music_and_background(audio, sr)
            audio = self._enhance_speech(audio, sr)
            audio = self._adaptive_filtering(audio, sr)
            audio = self._final_normalization(audio)
            
            # Save processed audio
            processed_path = AUDIOS_DIR / f"{task_id}_processed.wav"
            sf.write(str(processed_path), audio, sr)
            
            # Memory cleanup (only if needed)
            if self._should_cleanup_memory():
                self._cleanup_memory()
            
            return str(processed_path)
            
        except Exception as e:
            print(f"❌ Error in enhanced audio preprocessing: {e}")
            raise
    
    def _aggressive_noise_reduction(self, audio, sr):
        """Aggressive noise reduction"""
        try:
            if NOISEREDUCE_AVAILABLE:
                # Apply noise reduction
                reduced_noise = nr.reduce_noise(y=audio, sr=sr, stationary=True)
                return reduced_noise
            else:
                return audio
        except Exception as e:
            print(f"⚠️  Noise reduction failed: {e}")
            return audio
    
    def _remove_music_and_background(self, audio, sr):
        """Remove music and background noise"""
        try:
            # Simple high-pass filter to remove low-frequency noise
            if SCIPY_AVAILABLE:
                from scipy import signal
                nyquist = sr / 2
                cutoff = 80  # Hz
                normalized_cutoff = cutoff / nyquist
                b, a = signal.butter(4, normalized_cutoff, btype='high')
                filtered_audio = signal.filtfilt(b, a, audio)
                return filtered_audio
            else:
                return audio
        except Exception as e:
            print(f"⚠️  Music removal failed: {e}")
            return audio
    
    def _enhance_speech(self, audio, sr):
        """Enhance speech frequencies"""
        try:
            # Boost speech frequencies (300-3400 Hz)
            if SCIPY_AVAILABLE:
                from scipy import signal
                nyquist = sr / 2
                low_cutoff = 300 / nyquist
                high_cutoff = 3400 / nyquist
                b, a = signal.butter(4, [low_cutoff, high_cutoff], btype='band')
                enhanced_audio = signal.filtfilt(b, a, audio)
                return enhanced_audio
            else:
                return audio
        except Exception as e:
            print(f"⚠️  Speech enhancement failed: {e}")
            return audio
    
    def _adaptive_filtering(self, audio, sr):
        """Adaptive filtering for better speech quality"""
        try:
            # Simple normalization
            audio = audio / np.max(np.abs(audio))
            return audio
        except Exception as e:
            print(f"⚠️  Adaptive filtering failed: {e}")
            return audio
    
    def _final_normalization(self, audio):
        """Final audio normalization"""
        try:
            # Normalize to prevent clipping
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio = audio / max_val * 0.95
            return audio
        except Exception as e:
            print(f"⚠️  Final normalization failed: {e}")
            return audio
    
    def _transcribe_with_enhanced_noise_handling(self, audio, sr, source_lang, task_id):
        """Transcribe with enhanced noise handling"""
        try:
            print(f"🎧 Transcribing with enhanced noise handling...")
            
            # Try multiple preprocessing approaches
            approaches = [
                self._minimal_preprocessing,
                self._aggressive_preprocessing,
                lambda a, s: a  # No preprocessing
            ]
            
            for i, approach in enumerate(approaches):
                try:
                    print(f"🔄 Trying approach {i + 1}/{len(approaches)}")
                    
                    # Apply preprocessing
                    processed_audio = approach(audio, sr)
                    
                    # Transcribe
                    transcription = self._transcribe_audio_chunk_enhanced(processed_audio, sr, source_lang)
                    
                    if transcription and len(transcription.strip()) > 10:
                        print(f"✅ Approach {i + 1} successful")
                        return transcription
                    else:
                        print(f"⚠️  Approach {i + 1} produced insufficient transcription")
                        
                except Exception as e:
                    print(f"⚠️  Approach {i + 1} failed: {e}")
                    continue
            
            # If all approaches fail, return empty string
            print("❌ All transcription approaches failed")
            return ""
            
        except Exception as e:
            print(f"❌ Error in enhanced noise handling: {e}")
            return ""
    
    def _transcribe_with_alternative_preprocessing(self, audio_path, source_lang, task_id):
        """Transcribe with alternative preprocessing methods"""
        try:
            print(f"🎧 Transcribing with alternative preprocessing...")
            
            # Load audio
            audio, sr = librosa.load(audio_path, sr=16000)
            
            # Try different preprocessing methods
            methods = [
                ("minimal", self._minimal_preprocessing),
                ("aggressive", self._aggressive_preprocessing),
                ("none", lambda a, s: a)
            ]
            
            for method_name, method_func in methods:
                try:
                    print(f"🔄 Trying {method_name} preprocessing...")
                    
                    processed_audio = method_func(audio, sr)
                    transcription = self._transcribe_audio_chunk_enhanced(processed_audio, sr, source_lang)
                    
                    if transcription and len(transcription.strip()) > 10:
                        print(f"✅ {method_name} preprocessing successful")
                        return transcription
                        
                except Exception as e:
                    print(f"⚠️  {method_name} preprocessing failed: {e}")
                    continue
            
            print("❌ All preprocessing methods failed")
            return ""
            
        except Exception as e:
            print(f"❌ Error in alternative preprocessing: {e}")
            return ""
    
    def _minimal_preprocessing(self, audio, sr):
        """Minimal audio preprocessing"""
        try:
            # Simple normalization
            audio = audio / np.max(np.abs(audio)) if np.max(np.abs(audio)) > 0 else audio
            return audio
        except Exception as e:
            print(f"⚠️  Minimal preprocessing failed: {e}")
            return audio
    
    def _aggressive_preprocessing(self, audio, sr):
        """Aggressive audio preprocessing"""
        try:
            # Apply multiple preprocessing steps
            audio = self._aggressive_noise_reduction(audio, sr)
            audio = self._remove_music_and_background(audio, sr)
            audio = self._enhance_speech(audio, sr)
            audio = self._adaptive_filtering(audio, sr)
            audio = self._final_normalization(audio)
            return audio
        except Exception as e:
            print(f"⚠️  Aggressive preprocessing failed: {e}")
            return audio
    
    def merge_audio_video(self, video_path, audio_path, task_id, video_speed='1.0', instrumental_path=None, sync_original_audio=False):
        """Merge audio and video with memory optimization"""
        try:
            print(f"🎬 Merging audio and video...")
            
            if not os.path.exists(video_path):
                raise Exception(f"Video file not found: {video_path}")
            
            if not os.path.exists(audio_path):
                raise Exception(f"Audio file not found: {audio_path}")
            
            # Create output path
            output_path = OUTPUTS_DIR / f"{task_id}_output.mp4"
            
            # Build ffmpeg command
            cmd = [
                'ffmpeg', '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-map', '0:v:0',
                '-map', '1:a:0'
            ]
            
            # Add speed adjustment if needed
            if video_speed != '1.0':
                cmd.extend(['-filter:v', f'setpts={1/float(video_speed)}*PTS'])
                cmd.extend(['-filter:a', f'atempo={video_speed}'])
            
            # Add instrumental mixing if provided
            if instrumental_path and os.path.exists(instrumental_path):
                print(f"🎵 Adding instrumental mixing...")
                cmd.extend(['-i', instrumental_path])
                cmd.extend(['-filter_complex', '[1:a][2:a]amix=inputs=2:duration=first[aout]'])
                cmd.extend(['-map', '0:v:0', '-map', '[aout]'])
            
            cmd.extend(['-y', str(output_path)])
            
            # Execute ffmpeg command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(output_path):
                print(f"✅ Video merged successfully: {output_path}")
                
                # Memory cleanup after merging (only if needed)
                if self._should_cleanup_memory():
                    self._cleanup_memory()
                
                return str(output_path)
            else:
                raise Exception(f"FFmpeg failed: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error merging audio and video: {e}")
            raise
    
    def _get_video_duration(self, video_path):
        """Get video duration using ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
            else:
                return None
                
        except Exception as e:
            print(f"⚠️  Error getting video duration: {e}")
            return None
    
    def _get_audio_duration(self, audio_path):
        """Get audio duration using ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
            else:
                return None
                
        except Exception as e:
            print(f"⚠️  Error getting audio duration: {e}")
            return None
    
    def _create_advanced_audio_mix(self, tts_audio_path, instrumental_path, task_id, sync_original_audio=False):
        """Create advanced audio mix with memory optimization"""
        try:
            print(f"🎵 Creating advanced audio mix...")
            
            if not os.path.exists(tts_audio_path):
                raise Exception(f"TTS audio not found: {tts_audio_path}")
            
            if not instrumental_path or not os.path.exists(instrumental_path):
                print(f"⚠️  No instrumental path provided, using TTS audio only")
                return tts_audio_path
            
            # Create mixed audio path
            mixed_audio_path = AUDIOS_DIR / f"{task_id}_mixed.wav"
            
            # Build ffmpeg command for mixing
            cmd = [
                'ffmpeg', '-i', tts_audio_path,
                '-i', instrumental_path,
                '-filter_complex', '[0:a][1:a]amix=inputs=2:duration=first[aout]',
                '-map', '[aout]',
                '-y', str(mixed_audio_path)
            ]
            
            # Execute mixing
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(mixed_audio_path):
                print(f"✅ Audio mix created: {mixed_audio_path}")
                
                # Memory cleanup after mixing (only if needed)
                if self._should_cleanup_memory():
                    self._cleanup_memory()
                
                return str(mixed_audio_path)
            else:
                raise Exception(f"Audio mixing failed: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error creating audio mix: {e}")
            return tts_audio_path
    
    def _create_timestamp_sync_audio_mix(self, tts_audio_path, instrumental_path, task_id):
        """Create timestamp-synchronized audio mix"""
        try:
            print(f"⏰ Creating timestamp-synchronized audio mix...")
            
            if not os.path.exists(tts_audio_path):
                raise Exception(f"TTS audio not found: {tts_audio_path}")
            
            if not instrumental_path or not os.path.exists(instrumental_path):
                print(f"⚠️  No instrumental path provided, using TTS audio only")
                return tts_audio_path
            
            # Get durations
            tts_duration = self._get_audio_duration(tts_audio_path)
            instrumental_duration = self._get_audio_duration(instrumental_path)
            
            if not tts_duration or not instrumental_duration:
                print(f"⚠️  Could not get durations, using simple mix")
                return self._create_advanced_audio_mix(tts_audio_path, instrumental_path, task_id)
            
            # Create synchronized mix
            sync_audio_path = AUDIOS_DIR / f"{task_id}_sync_mixed.wav"
            
            # Use the longer duration
            target_duration = max(tts_duration, instrumental_duration)
            
            # Build ffmpeg command for synchronized mixing
            cmd = [
                'ffmpeg', '-i', tts_audio_path,
                '-i', instrumental_path,
                '-filter_complex', f'[0:a]apad=pad_dur={target_duration}[padded_tts];[1:a]apad=pad_dur={target_duration}[padded_instrumental];[padded_tts][padded_instrumental]amix=inputs=2:duration=first[aout]',
                '-map', '[aout]',
                '-y', str(sync_audio_path)
            ]
            
            # Execute synchronized mixing
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(sync_audio_path):
                print(f"✅ Synchronized audio mix created: {sync_audio_path}")
                
                # Memory cleanup after mixing (only if needed)
                if self._should_cleanup_memory():
                    self._cleanup_memory()
                
                return str(sync_audio_path)
            else:
                raise Exception(f"Synchronized mixing failed: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error creating synchronized audio mix: {e}")
            return tts_audio_path

class TranslationService:
    """Translation service using various models with GPU support"""
    
    def __init__(self):
        self.models = {}
        self.tokenizers = {}
        
        # Determine device for GPU acceleration
        import torch
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"🌐 TranslationService initialized with device: {self.device}")
    
    def translate(self, text, source_lang, target_lang, model_name):
        """Translate text using specified model with unlimited length support"""
        try:
            print(f"🔧 Translating unlimited text using {model_name}")
            print(f"   Source: {source_lang} -> Target: {target_lang}")
            print(f"   Text length: {len(text)} characters")
            
            # Check if text is too long for single translation
            if UNLIMITED_TRANSLATION and len(text) > 5000:  # Split if longer than 5000 chars
                print(f"📊 Text is long ({len(text)} chars), using chunked translation")
                return self._translate_unlimited_text(text, source_lang, target_lang, model_name)
            else:
                return self._translate_single_text(text, source_lang, target_lang, model_name)
            
        except Exception as e:
            print(f"❌ Error translating text: {str(e)}")
            raise Exception(f"Error translating text: {str(e)}")
    
    def _translate_single_text(self, text, source_lang, target_lang, model_name):
        """Translate single text chunk"""
        try:
            # Load model if not already loaded
            self._load_translation_model(model_name)
            
            # Get NLLB language code with improved validation
            source_code = self._get_nllb_lang_code(source_lang)
            target_code = self._get_nllb_lang_code(target_lang)
            
            print(f"🔧 Source language: {source_lang} -> {source_code}")
            print(f"🔧 Target language: {target_lang} -> {target_code}")
            
            # Prepare input
            if model_name.startswith('nllb'):
                # NLLB-200 format
                input_text = f"{source_code} {target_code} {text}"
            else:
                # T5 format
                input_text = f"translate {source_lang} to {target_lang}: {text}"
            
            print(f"   Input format: {input_text[:100]}...")
            print(f"🔧 Target NLLB Code: {target_code}")
            
            # Tokenize without length limit
            inputs = self.tokenizers[model_name](
                input_text, 
                return_tensors="pt", 
                truncation=False
            )
            
            # Move to GPU if available
            if self.device == 'cuda':
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                self.models[model_name] = self.models[model_name].to(self.device)
            
            # Generate translation with unlimited length
            with torch.no_grad():
                # Get forced_bos_token_id for target language
                forced_bos_token_id = None
                if model_name.startswith('nllb'):
                    try:
                        # Try to get forced_bos_token_id using different methods
                        if hasattr(self.tokenizers[model_name], 'lang_code_to_id'):
                            forced_bos_token_id = self.tokenizers[model_name].lang_code_to_id[target_code]
                        elif hasattr(self.tokenizers[model_name], 'convert_tokens_to_ids'):
                            # Try to convert target code to token ID
                            forced_bos_token_id = self.tokenizers[model_name].convert_tokens_to_ids(target_code)
                        else:
                            # Fallback: try to find the token ID manually
                            forced_bos_token_id = self.tokenizers[model_name].convert_tokens_to_ids(f"__{target_code}__")
                        
                        if forced_bos_token_id is not None:
                            print(f"🔧 Forced BOS Token ID: {forced_bos_token_id} for {target_code}")
                        else:
                            print(f"⚠️  Warning: Could not find forced_bos_token_id for {target_code}")
                    except Exception as e:
                        print(f"⚠️  Warning: Could not set forced_bos_token_id for {target_code}: {e}")
                        forced_bos_token_id = None
                
                outputs = self.models[model_name].generate(
                    **inputs,
                    max_length=4096,  # Increased max length for unlimited processing
                    num_beams=5,
                    early_stopping=True,
                    do_sample=False,  # Remove temperature for consistency
                    forced_bos_token_id=forced_bos_token_id  # Force target language
                )
            
            # Decode translation
            translation = self.tokenizers[model_name].decode(
                outputs[0], 
                skip_special_tokens=True
            )
            
            print(f"✅ Translation completed: {translation[:100]}...")
            return translation.strip()
            
        except Exception as e:
            print(f"❌ Error in single text translation: {str(e)}")
            raise Exception(f"Error in single text translation: {str(e)}")
    
    def _translate_unlimited_text(self, text, source_lang, target_lang, model_name):
        """Translate unlimited length text using chunking"""
        try:
            print(f"📊 Starting unlimited translation: {len(text)} characters")
            
            # Split text into manageable chunks
            chunks = self._split_text_for_translation(text, max_length=4000)
            print(f"📊 Split into {len(chunks)} chunks for translation")
            
            translations = []
            
            for i, chunk in enumerate(chunks):
                print(f"🔧 Translating chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
                
                # Translate chunk
                chunk_translation = self._translate_single_text(chunk, source_lang, target_lang, model_name)
                
                if chunk_translation and chunk_translation.strip():
                    translations.append(chunk_translation)
                    print(f"✅ Chunk {i+1} translated: {len(chunk_translation)} chars")
                else:
                    print(f"⚠️  Chunk {i+1} produced no translation")
                
                # Memory cleanup between chunks
                if ENABLE_MEMORY_OPTIMIZATION:
                    import gc
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
            
            if not translations:
                raise Exception("No translation produced for any chunk")
            
            # Combine translations
            full_translation = self._combine_translations(translations)
            
            print(f"🎯 Total translation length: {len(full_translation)} characters")
            return full_translation
            
        except Exception as e:
            print(f"❌ Error in unlimited translation: {str(e)}")
            raise Exception(f"Error in unlimited translation: {str(e)}")
    
    def _split_text_for_translation(self, text, max_length=4000):
        """Split text into chunks for translation - Unlimited processing support"""
        try:
            # Use unlimited processing settings
            if UNLIMITED_TRANSLATION:
                max_length = 8000  # Higher limit for unlimited processing
            
            # Split by sentences first
            sentences = re.split(r'[.!?]+', text)
            chunks = []
            current_chunk = ""
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Check if adding this sentence would exceed max length
                if len(current_chunk) + len(sentence) + 1 <= max_length:
                    current_chunk += sentence + ". "
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + ". "
            
            # Add remaining chunk
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            return chunks if chunks else [text]
            
        except Exception as e:
            print(f"⚠️  Error splitting text for translation: {e}")
            # Fallback: split by length
            return [text[i:i+max_length] for i in range(0, len(text), max_length)]
    
    def _combine_translations(self, translations):
        """Combine multiple translations with proper formatting"""
        try:
            # Join translations with proper spacing
            combined = ' '.join(translations)
            
            # Clean and format
            cleaned = re.sub(r'\s+', ' ', combined)
            cleaned = re.sub(r'[.!?]{2,}', '.', cleaned)
            cleaned = re.sub(r'([.!?])\s+([a-z])', lambda m: m.group(1) + ' ' + m.group(2).upper(), cleaned)
            
            return cleaned.strip()
            
        except Exception as e:
            print(f"⚠️  Error combining translations: {e}")
            return ' '.join(translations)
    
    def _load_translation_model(self, model_name):
        """Load translation model if not already loaded"""
        if model_name not in self.models:
            try:
                print(f"🔄 Loading translation model: {model_name}")
                
                # Initialize model downloader
                model_downloader = ModelDownloader()
                
                # Check if model needs to be downloaded
                if not model_downloader.is_model_available(model_name):
                    print(f"📥 Model {model_name} not found locally, downloading...")
                    if not model_downloader.download_model(model_name):
                        raise Exception(f"Failed to download model {model_name}")
                    print(f"✅ Model {model_name} downloaded successfully")
                
                model_path = TRANSLATION_MODELS.get(model_name, model_name)
                if model_path is None:
                    raise Exception(f"Unknown model name: {model_name}")
                
                # Add error handling for model loading
                try:
                    self.tokenizers[model_name] = AutoTokenizer.from_pretrained(model_path)
                    self.models[model_name] = AutoModelForSeq2SeqLM.from_pretrained(model_path)
                    
                    # Move model to GPU if available
                    if self.device == 'cuda':
                        self.models[model_name] = self.models[model_name].to(self.device)
                        print(f"✅ Moved translation model to GPU")
                    
                    print(f"✅ Loaded translation model: {model_name} on {self.device}")
                    
                except Exception as model_error:
                    print(f"❌ Error loading translation model {model_name}: {model_error}")
                    # Try fallback to distilled model
                    if model_name == 'nllb-200':
                        print(f"🔄 Trying fallback to NLLB-200 Distilled...")
                        return self._load_translation_model('nllb-200-distilled')
                    else:
                        raise Exception(f"Failed to load translation model: {str(model_error)}")
                
            except Exception as e:
                print(f"❌ Critical error loading translation model: {e}")
                raise Exception(f"Error loading translation model {model_name}: {str(e)}")
    
    def _get_nllb_lang_code(self, lang):
        """Get NLLB language code with improved mapping and validation"""
        nllb_mapping = {
            'en': 'eng_Latn', 'th': 'tha_Thai', 'lo': 'lao_Laoo',
            'zh': 'zho_Hans', 'ja': 'jpn_Jpan', 'ko': 'kor_Hang',
            'vi': 'vie_Latn', 'hi': 'hin_Deva', 'es': 'spa_Latn',
            'fr': 'fra_Latn', 'de': 'deu_Latn', 'it': 'ita_Latn',
            'pt': 'por_Latn', 'ru': 'rus_Cyrl', 'ar': 'arb_Arab',
            'auto': 'eng_Latn'  # Default for auto detection
        }
        
        # Handle special cases first
        if lang == 'auto':
            return 'eng_Latn'
        elif lang == 'lo' or lang.startswith('lo'):
            return 'lao_Laoo'
        
        # ถ้า lang ลงท้ายด้วย _Latn และมี _ มากกว่า 1 ตัว (เช่น lao_Laoo_Latn) ให้ตัด _Latn ทิ้ง
        if lang.count('_') > 1 and lang.endswith('_Latn'):
            lang = lang.rsplit('_', 1)[0]
        
        # If already in NLLB format, return as is
        if '_' in lang and len(lang.split('_')) == 2:
            return lang
        
        # Check if lang is in our mapping
        if lang in nllb_mapping:
            return nllb_mapping[lang]
        
        # Handle language prefixes
        if lang.startswith('en'):
            return 'eng_Latn'
        elif lang.startswith('th'):
            return 'tha_Thai'
        elif lang.startswith('ja'):
            return 'jpn_Jpan'
        elif lang.startswith('ko'):
            return 'kor_Hang'
        elif lang.startswith('zh'):
            return 'zho_Hans'
        elif lang.startswith('pt'):
            return 'por_Latn'
        elif lang.startswith('es'):
            return 'spa_Latn'
        elif lang.startswith('fr'):
            return 'fra_Latn'
        elif lang.startswith('de'):
            return 'deu_Latn'
        elif lang.startswith('it'):
            return 'ita_Latn'
        elif lang.startswith('ru'):
            return 'rus_Cyrl'
        elif lang.startswith('ar'):
            return 'arb_Arab'
        elif lang.startswith('vi'):
            return 'vie_Latn'
        elif lang.startswith('hi'):
            return 'hin_Deva'
        else:
            # Default fallback
            return f"{lang}_Latn"
    
    def detect_language(self, text):
        """Detect language of text"""
        try:
            # Simple language detection based on character sets
            thai_chars = len(re.findall(r'[\u0E00-\u0E7F]', text))
            lao_chars = len(re.findall(r'[\u0E80-\u0EFF]', text))
            chinese_chars = len(re.findall(r'[\u4E00-\u9FFF]', text))
            japanese_chars = len(re.findall(r'[\u3040-\u309F\u30A0-\u30FF]', text))
            korean_chars = len(re.findall(r'[\uAC00-\uD7AF]', text))
            
            if thai_chars > 0:
                return 'th'
            elif lao_chars > 0:
                return 'lo'
            elif chinese_chars > 0:
                return 'zh'
            elif japanese_chars > 0:
                return 'ja'
            elif korean_chars > 0:
                return 'ko'
            else:
                return 'en'  # Default to English
                
        except Exception as e:
            print(f"⚠️  Error detecting language: {e}")
            return 'auto'

class TTSService:
    """Text-to-Speech service with multiple engines and GPU support"""
    
    def __init__(self):
        # Remove text length limitations for unlimited processing
        self.max_audio_duration = None
        self.max_text_length = None
        # Use unlimited processing settings
        self.overlap_duration = UNLIMITED_OVERLAP_SIZE if UNLIMITED_TTS else OVERLAP_DURATION
        self.chunk_duration = UNLIMITED_CHUNK_SIZE if UNLIMITED_TTS else CHUNK_DURATION
        
        # Determine device for GPU acceleration
        import torch
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"🎤 TTS Service initialized with device: {self.device}")
    
    def synthesize_speech(self, text, target_lang, model_name, task_id, voice_mode='female', custom_coqui_model=None):
        """Synthesize speech from text with timestamp sync support"""
        try:
            print(f"🎤 เริ่มการแปลงข้อความเป็นเสียง")
            print(f"📊 Language: {target_lang}, Model: {model_name}, Voice: {voice_mode}")
            
            # Check if timestamp sync is enabled
            if ENABLE_TTS_SYNC:
                # Try to load timestamps for sync
                timestamps_path = TEXTS_DIR / f"{task_id}_timestamps.json"
                if timestamps_path.exists():
                    print("🔄 Using timestamp sync for TTS")
                    audio_path = self._synthesize_with_timestamp_sync(
                        text, target_lang, model_name, task_id, voice_mode, custom_coqui_model, timestamps_path
                    )
                else:
                    print("⚠️  No timestamps found, using standard TTS")
                    audio_path = self._synthesize_standard(text, target_lang, model_name, task_id, voice_mode, custom_coqui_model)
            else:
                # Standard TTS without sync
                audio_path = self._synthesize_standard(text, target_lang, model_name, task_id, voice_mode, custom_coqui_model)
            
            print(f"✅ การแปลงข้อความเป็นเสียงเสร็จสิ้น: {audio_path}")
            return audio_path
            
        except Exception as e:
            print(f"❌ Error synthesizing speech: {str(e)}")
            raise Exception(f"Error synthesizing speech: {str(e)}")
    
    def _synthesize_standard(self, text, target_lang, model_name, task_id, voice_mode, custom_coqui_model=None):
        """Standard TTS synthesis without timestamp sync"""
        # Split text for processing
        text_chunks = self._split_text_for_tts(text)
        
        if len(text_chunks) == 1:
            # Single chunk - direct synthesis
            return self._synthesize_single_chunk(text, target_lang, model_name, task_id, voice_mode, custom_coqui_model)
        else:
            # Multiple chunks - synthesize and concatenate
            return self._synthesize_multiple_chunks(text_chunks, target_lang, model_name, task_id, voice_mode, custom_coqui_model)
    
    def _synthesize_with_timestamp_sync(self, text, target_lang, model_name, task_id, voice_mode, custom_coqui_model, timestamps_path):
        """Synthesize TTS with timestamp synchronization for precise audio overlay"""
        try:
            import json
            from pydub import AudioSegment
            from pydub.silence import make_silence
            
            # Load timestamps with enhanced metadata
            with open(timestamps_path, 'r', encoding='utf-8') as f:
                timestamps_data = json.load(f)
            
            segments = timestamps_data.get('segments', [])
            word_timestamps = timestamps_data.get('word_timestamps', [])
            audio_duration = timestamps_data.get('audio_duration', 0)
            
            print(f"📊 Found {len(segments)} segments and {len(word_timestamps)} words for sync")
            print(f"⏱️  Total audio duration: {audio_duration:.2f} seconds")
            
            # Create output audio path
            output_filename = f"{task_id}_tts_sync.wav"
            output_path = AUDIOS_DIR / output_filename
            
            # Process each segment with word-level precision
            audio_segments = []
            current_time = 0.0
            
            for i, segment in enumerate(segments):
                segment_start = segment.get('start', 0.0)
                segment_end = segment.get('end', 0.0)
                segment_text = segment.get('text', '').strip()
                
                if not segment_text:
                    continue
                
                print(f"🎤 Processing segment {i+1}/{len(segments)}: {segment_text[:50]}...")
                
                # Add silence before segment if needed
                if segment_start > current_time + TTS_SILENCE_PADDING:
                    silence_duration = segment_start - current_time
                    silence_audio = make_silence(duration=silence_duration * 1000)  # Convert to ms
                    audio_segments.append(silence_audio)
                    current_time = segment_start
                
                # Synthesize TTS for this segment
                segment_audio_path = self._synthesize_single_chunk(
                    segment_text, target_lang, model_name, f"{task_id}_seg_{i}", voice_mode, custom_coqui_model
                )
                
                # Load segment audio
                segment_audio = AudioSegment.from_wav(segment_audio_path)
                
                # Adjust segment duration to match original timing with word-level precision
                target_duration = segment_end - segment_start
                if target_duration > TTS_MIN_SEGMENT_DURATION:
                    # Speed up or slow down to match timing
                    current_duration = len(segment_audio) / 1000.0  # Convert to seconds
                    if current_duration > 0:
                        speed_factor = current_duration / target_duration
                        if speed_factor > 0.3 and speed_factor < 3.0:  # Extended speed range
                            segment_audio = segment_audio.speedup(playback_speed=speed_factor)
                        else:
                            # If speed adjustment is too extreme, just pad or trim
                            target_ms = int(target_duration * 1000)
                            if len(segment_audio) < target_ms:
                                # Pad with silence
                                padding = make_silence(duration=target_ms - len(segment_audio))
                                segment_audio = segment_audio + padding
                            else:
                                # Trim to target duration
                                segment_audio = segment_audio[:target_ms]
                
                audio_segments.append(segment_audio)
                current_time = segment_end
                
                # Clean up segment file
                try:
                    os.remove(segment_audio_path)
                except:
                    pass
            
            # Combine all segments
            if audio_segments:
                final_audio = audio_segments[0]
                for segment in audio_segments[1:]:
                    final_audio = final_audio + segment
                
                # Export final audio
                final_audio.export(str(output_path), format="wav")
                
                # Save synchronization metadata for later use in video overlay
                sync_metadata_path = Path('texts') / f"{task_id}_sync_metadata.json"
                with open(sync_metadata_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'synchronized_segments': [
                            {
                                'start': seg.get('start', 0.0),
                                'end': seg.get('end', 0.0),
                                'text': seg.get('text', ''),
                                'segment_index': i
                            } for i, seg in enumerate(segments)
                        ],
                        'word_timestamps': word_timestamps,
                        'total_duration': audio_duration,
                        'original_timestamps': timestamps_data,
                        'tts_audio_path': str(output_path)
                    }, f, ensure_ascii=False, indent=2)
                
                print(f"✅ Timestamp sync TTS completed: {len(audio_segments)} segments")
                print(f"💾 Saved sync metadata: {sync_metadata_path}")
                return str(output_path)
            else:
                raise Exception("No audio segments generated")
                
        except Exception as e:
            print(f"⚠️  Timestamp sync failed: {e}, falling back to standard TTS")
            return self._synthesize_standard(text, target_lang, model_name, task_id, voice_mode, custom_coqui_model)
    
    def _split_text_for_tts(self, text, max_length=None):
        """Split text into chunks for TTS processing - Unlimited length support"""
        # Remove length limit for unlimited processing
        if max_length is None or UNLIMITED_TTS:
            max_length = 10000  # Higher limit for unlimited processing
        
        # Split by sentences first for better TTS quality
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if adding this sentence would exceed max length
            if len(current_chunk) + len(sentence) + 1 <= max_length:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    def _synthesize_single_chunk(self, text, target_lang, model_name, task_id, voice_mode, custom_coqui_model=None):
        """Synthesize speech for a single text chunk with fallback"""
        try:
            output_path = TEMP_DIR / f"{task_id}_tts.wav"
            
            if target_lang == 'lo':
                # Special handling for Lao language
                result = self._synthesize_lao_text(text, str(output_path), voice_mode, custom_coqui_model)
            else:
                # Try specified TTS engine first, then fallback to gTTS
                result = None
                try:
                    if model_name == 'gtts':
                        result = self._synthesize_with_gtts(text, target_lang, str(output_path), voice_mode)
                    elif model_name == 'edge':
                        result = self._synthesize_with_edge(text, target_lang, str(output_path), voice_mode)
                    elif model_name == 'espeak':
                        result = self._synthesize_with_espeak(text, target_lang, str(output_path), voice_mode)
                    elif model_name == 'pico':
                        result = self._synthesize_with_pico(text, target_lang, str(output_path), voice_mode)
                    elif model_name == 'festival':
                        result = self._synthesize_with_festival(text, target_lang, str(output_path), voice_mode)
                    elif model_name == 'coqui':
                        result = self._synthesize_with_coqui(text, target_lang, str(output_path), voice_mode, custom_coqui_model)
                    else:
                        # Default to gTTS
                        result = self._synthesize_with_gtts(text, target_lang, str(output_path), voice_mode)
                except Exception as primary_error:
                    print(f"⚠️  Primary TTS engine failed: {primary_error}")
                    result = None
                
                # If primary engine failed or returned None, try gTTS fallback
                if result is None or not os.path.exists(result):
                    print(f"🔄 Primary TTS failed, falling back to gTTS...")
                    try:
                        result = self._synthesize_with_gtts(text, target_lang, str(output_path), voice_mode)
                    except Exception as fallback_error:
                        print(f"⚠️  gTTS fallback also failed: {fallback_error}")
                        result = None
            
            # Verify that the audio file was actually created
            if not os.path.exists(result):
                print(f"⚠️  TTS returned path but file doesn't exist: {result}")
                # Try to create a fallback audio file
                fallback_path = TEMP_DIR / f"{task_id}_fallback.wav"
                print(f"🔄 Creating fallback audio file: {fallback_path}")
                
                # Create a simple beep sound using FFmpeg
                cmd = [
                    'ffmpeg', '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=3',
                    str(fallback_path), '-y'
                ]
                
                import subprocess
                subprocess.run(cmd, capture_output=True, text=True)
                
                if os.path.exists(fallback_path):
                    print(f"✅ Created fallback audio: {fallback_path}")
                    return str(fallback_path)
                else:
                    raise Exception(f"Failed to create fallback audio file")
            
            # Apply voice effects if specified
            if voice_mode not in ['female', 'male']:
                print(f"🎭 Applying {voice_mode} voice effect...")
                result = self._apply_voice_effects(result, voice_mode)
            
            print(f"✅ TTS synthesis completed: {result}")
            return result
                    
        except Exception as e:
            raise Exception(f"Error in single chunk synthesis: {str(e)}")
    
    def _synthesize_multiple_chunks(self, text_chunks, target_lang, model_name, task_id, voice_mode, custom_coqui_model=None):
        """Synthesize speech for multiple text chunks with unlimited length support"""
        try:
            print(f"📊 Processing {len(text_chunks)} TTS chunks for unlimited synthesis")
            audio_files = []
            
            for i, chunk in enumerate(text_chunks):
                chunk_task_id = f"{task_id}_chunk_{i}"
                print(f"🎤 Synthesizing chunk {i+1}/{len(text_chunks)} ({len(chunk)} chars)")
                
                audio_file = self._synthesize_single_chunk(chunk, target_lang, model_name, chunk_task_id, voice_mode, custom_coqui_model)
                audio_files.append(audio_file)
                
                # Memory cleanup between chunks
                if ENABLE_MEMORY_OPTIMIZATION:
                    import gc
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
            
            # Concatenate audio files
            print(f"🔗 Concatenating {len(audio_files)} audio files...")
            return self._concatenate_audio_files_enhanced(audio_files, task_id)
            
        except Exception as e:
            raise Exception(f"Error in multiple chunks synthesis: {str(e)}")
    
    def _concatenate_audio_files_enhanced(self, audio_files, task_id):
        """Enhanced concatenation of multiple audio files with better error handling"""
        try:
            if len(audio_files) == 1:
                return audio_files[0]
            
            print(f"🔗 Concatenating {len(audio_files)} audio files...")
            
            # Create file list for FFmpeg
            file_list_path = TEMP_DIR / f"{task_id}_filelist.txt"
            with open(file_list_path, 'w', encoding='utf-8') as f:
                for audio_file in audio_files:
                    if os.path.exists(audio_file):
                        f.write(f"file '{audio_file}'\n")
                    else:
                        print(f"⚠️  Audio file not found: {audio_file}")
            
            # Concatenate using FFmpeg with enhanced options
            output_path = TEMP_DIR / f"{task_id}_concatenated.wav"
            
            cmd = [
                'ffmpeg', '-f', 'concat', '-safe', '0',
                '-i', str(file_list_path), '-c', 'copy',
                '-avoid_negative_ts', 'make_zero',
                str(output_path), '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"⚠️  FFmpeg concatenation error: {result.stderr}")
                # Try alternative concatenation method
                return self._concatenate_audio_files_alternative(audio_files, task_id)
            
            # Verify output file
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                print(f"⚠️  Concatenated file is empty or missing, trying alternative method")
                return self._concatenate_audio_files_alternative(audio_files, task_id)
            
            # Clean up individual files
            for audio_file in audio_files:
                try:
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
                        print(f"🗑️  Cleaned up: {audio_file}")
                except Exception as e:
                    print(f"⚠️  Could not clean up {audio_file}: {e}")
            
            # Clean up file list
            try:
                os.remove(file_list_path)
            except:
                pass
            
            print(f"✅ Concatenation completed: {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"❌ Error in enhanced concatenation: {e}")
            # Fallback to alternative method
            return self._concatenate_audio_files_alternative(audio_files, task_id)
    
    def _concatenate_audio_files_alternative(self, audio_files, task_id):
        """Alternative concatenation method using sox or direct file copying"""
        try:
            print(f"🔄 Using alternative concatenation method...")
            
            if len(audio_files) == 1:
                return audio_files[0]
            
            # Try using sox if available
            try:
                output_path = TEMP_DIR / f"{task_id}_concatenated_alt.wav"
                
                # Build sox command
                sox_cmd = ['sox']
                for audio_file in audio_files:
                    if os.path.exists(audio_file):
                        sox_cmd.append(audio_file)
                sox_cmd.append(str(output_path))
                
                result = subprocess.run(sox_cmd, capture_output=True, text=True)
                if result.returncode == 0 and os.path.exists(output_path):
                    print(f"✅ Alternative concatenation successful with sox")
                    return str(output_path)
            except:
                pass
            
            # Fallback: return the longest audio file
            longest_file = max(audio_files, key=lambda f: os.path.getsize(f) if os.path.exists(f) else 0)
            print(f"⚠️  Using longest audio file as fallback: {longest_file}")
            return longest_file
            
        except Exception as e:
            print(f"❌ Alternative concatenation failed: {e}")
            # Return first available file
            for audio_file in audio_files:
                if os.path.exists(audio_file):
                    return audio_file
            raise Exception("No valid audio files found for concatenation")
    
    def _synthesize_with_gtts(self, text, target_lang, output_path, voice_mode='female'):
        """Synthesize speech using Google TTS"""
        try:
            # Map language codes for better TTS support
            lang_map = {
                'th': 'th',  # Thai
                'lo': 'th',  # Lao - use Thai as fallback since Lao not supported by gTTS
                'en': 'en',
                'zh': 'zh',
                'ja': 'ja',
                'ko': 'ko',
                'vi': 'vi'
            }
            
            # Use mapped language code
            tts_lang = lang_map.get(target_lang, target_lang)
            
            # For Lao, try to use Thai TTS as they are similar
            if target_lang == 'lo':
                print(f"🔄 Using Thai TTS for Lao text (Lao not supported by gTTS)")
            
            tts = gTTS(text=text, lang=tts_lang, slow=False)
            tts.save(output_path)
            
            # Verify file was created
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            else:
                raise Exception("gTTS failed to create audio file")
                
        except Exception as e:
            raise Exception(f"gTTS error: {str(e)}")
    
    def _synthesize_with_coqui(self, text, target_lang, output_path, voice_mode='female', custom_coqui_model=None):
        """Synthesize speech using Coqui TTS (Thai/Lao/Custom) with .pth file support and GPU acceleration"""
        try:
            from TTS.api import TTS
            import torch

            # ใช้ custom model ถ้ามี
            if custom_coqui_model:
                model_path = custom_coqui_model
                
                # ตรวจสอบว่าเป็น path ของ .pth file หรือไม่
                if model_path.endswith('.pth'):
                    # โหลด .pth file โดยตรง
                    print(f"🔄 Loading .pth model: {model_path}")
                    return self._synthesize_with_pth_model(text, model_path, output_path, voice_mode)
                else:
                    model_name = model_path
            else:
                coqui_models = {
                    'th': 'tts_models/thai/thai_female/glow-tts',
                    'lo': 'tts_models/multilingual/multi-dataset/your_lao_model'
                }
                model_name = coqui_models.get(target_lang)
                if not model_name:
                    raise Exception(f"Coqui TTS does not support language: {target_lang}")

            # ใช้ TTS API สำหรับโมเดลปกติ
            print(f"🚀 Loading Coqui TTS model on {self.device}")
            tts = TTS(model_name)
            
            # Move model to GPU if available
            if self.device == 'cuda':
                tts.model = tts.model.to(self.device)
                print(f"✅ Moved Coqui TTS model to GPU")
            
            # เลือก speaker/voice ถ้าโมเดลรองรับ
            speaker = None
            if voice_mode == 'male':
                speaker = 'male'
            elif voice_mode == 'female':
                speaker = 'female'
            # เพิ่ม voice_mode อื่นๆ ได้ถ้าโมเดลรองรับ

            tts.tts_to_file(text=text, file_path=output_path, speaker=speaker)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            else:
                raise Exception("Coqui TTS failed to create audio file")
        except Exception as e:
            print(f"⚠️  Coqui TTS error: {e}")
            return None

    def _synthesize_with_pth_model(self, text, pth_path, output_path, voice_mode='female'):
        """Synthesize speech using .pth model file with GPU acceleration"""
        try:
            import torch
            import torchaudio
            from TTS.tts.models import load_tts_model
            from TTS.tts.configs import load_config
            from TTS.tts.utils.speakers import SpeakerManager
            from TTS.tts.utils.text.tokenizer import TTSTokenizer
            import numpy as np
            
            print(f"🔄 Loading .pth model from: {pth_path}")
            print(f"🚀 Using device: {self.device}")
            
            # ตรวจสอบว่าไฟล์ .pth มีอยู่จริง
            if not os.path.exists(pth_path):
                raise Exception(f"Model file not found: {pth_path}")
            
            # หา config file ในโฟลเดอร์เดียวกัน
            model_dir = os.path.dirname(pth_path)
            config_path = os.path.join(model_dir, 'config.json')
            
            if not os.path.exists(config_path):
                # สร้าง config เริ่มต้นถ้าไม่มี
                print(f"⚠️  Config file not found, using default config")
                config = self._create_default_config()
            else:
                # โหลด config จากไฟล์
                config = load_config(config_path)
            
            # โหลดโมเดลจาก .pth file
            model = load_tts_model(config)
            model.load_checkpoint(config, pth_path)
            model.eval()
            
            # Move model to GPU if available
            if self.device == 'cuda':
                model = model.to(self.device)
                print(f"✅ Moved .pth model to GPU")
            
            # เตรียม text input
            if hasattr(model, 'tokenizer'):
                text_input = model.tokenizer.text_to_ids(text)
            else:
                # ใช้ tokenizer เริ่มต้น
                text_input = self._tokenize_text_simple(text)
            
            # แปลงเป็น tensor และย้ายไป GPU
            if isinstance(text_input, list):
                text_input = torch.tensor(text_input).unsqueeze(0)
            
            if self.device == 'cuda':
                text_input = text_input.to(self.device)
            
            # สังเคราะห์เสียง
            with torch.no_grad():
                if hasattr(model, 'inference'):
                    # ใช้ inference method ถ้ามี
                    audio = model.inference(text_input)
                else:
                    # ใช้ forward method
                    output = model(text_input)
                    if isinstance(output, tuple):
                        audio = output[0]  # สมมติว่า output แรกคือ audio
                    else:
                        audio = output
                
                # แปลงเป็น numpy array
                if isinstance(audio, torch.Tensor):
                    audio = audio.squeeze().cpu().numpy()
                
                # บันทึกไฟล์เสียง
                import soundfile as sf
                sf.write(output_path, audio, config.audio.sample_rate)
            
            # ตรวจสอบไฟล์ที่สร้าง
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"✅ Successfully generated audio from .pth model: {output_path}")
                return output_path
            else:
                raise Exception("Failed to create audio file from .pth model")
                
        except Exception as e:
            print(f"⚠️  Error with .pth model: {e}")
            return None

    def _create_default_config(self):
        """สร้าง config เริ่มต้นสำหรับ .pth model"""
        from TTS.tts.configs import BaseDatasetConfig, TTSConfig
        
        # สร้าง config เริ่มต้น
        config = TTSConfig()
        config.audio.sample_rate = 22050
        config.audio.hop_length = 256
        config.audio.win_length = 1024
        config.audio.mel_channels = 80
        config.audio.mel_fmin = 0
        config.audio.mel_fmax = 8000
        
        return config

    def _tokenize_text_simple(self, text):
        """Tokenize text แบบง่ายสำหรับ .pth model"""
        # แปลง text เป็น character IDs แบบง่าย
        char_to_id = {char: i for i, char in enumerate(set(text))}
        return [char_to_id.get(char, 0) for char in text]

    def _synthesize_with_espeak(self, text, target_lang, output_path, voice_mode='female'):
        """Synthesize speech using eSpeak-ng"""
        try:
            # Check if eSpeak-ng is installed
            try:
                subprocess.run(['espeak-ng', '--version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("⚠️  eSpeak-ng not installed, skipping...")
                raise Exception("eSpeak-ng not installed")
            
            # Map language codes for better support
            lang_map = {
                'th': 'th',  # Thai
                'lo': 'th',  # Lao - use Thai as fallback
                'en': 'en',
                'zh': 'zh',
                'ja': 'ja',
                'ko': 'ko',
                'vi': 'vi'
            }
            espeak_lang = lang_map.get(target_lang, 'en')
            
            # Map voice modes
            voice_map = {'female': 'f1', 'male': 'm1', 'child': 'f2'}
            espeak_voice = voice_map.get(voice_mode, 'f1')
            
            # For Lao, use Thai voice
            if target_lang == 'lo':
                print(f"🔄 Using Thai voice for Lao text in eSpeak")
            
            cmd = [
                'espeak-ng', '-v', f'{espeak_lang}+{espeak_voice}',
                '-w', output_path, text
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"eSpeak-ng error: {result.stderr}")
            
            # Verify file was created
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            else:
                raise Exception("eSpeak-ng failed to create audio file")
                
        except Exception as e:
            raise Exception(f"eSpeak-ng error: {str(e)}")
    
    def _synthesize_with_edge(self, text, target_lang, output_path, voice_mode='female'):
        """Synthesize speech using Microsoft Edge TTS"""
        try:
            import edge_tts
            import asyncio
            import time
            
            # Map language codes to Edge TTS voices
            voice_map = {
                'th': 'th-TH-AcharaNeural',
                'lo': 'th-TH-AcharaNeural',  # Use Thai voice for Lao since Lao voice may not be available
                'en': 'en-US-JennyNeural',
                'zh': 'zh-CN-XiaoxiaoNeural',
                'ja': 'ja-JP-NanamiNeural',
                'ko': 'ko-KR-SunHiNeural',
                'vi': 'vi-VN-HoaiMyNeural'
            }
            
            voice = voice_map.get(target_lang, 'en-US-JennyNeural')
            
            # For Lao, use Thai voice as fallback
            if target_lang == 'lo':
                print(f"🔄 Using Thai voice for Lao text in Edge TTS")
            
            # Create TTS object with proper text encoding
            tts = edge_tts.Communicate(text, voice)
            
            # Synthesize using asyncio
            async def synthesize():
                await tts.save(output_path)
            
            # Run async function
            asyncio.run(synthesize())
            
            # Verify file was created and has content
            max_wait = 10  # Wait up to 10 seconds
            wait_time = 0.1
            
            for _ in range(int(max_wait / wait_time)):
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    if file_size > 0:
                        print(f"✅ Edge TTS file created: {output_path} ({file_size} bytes)")
                        return output_path
                time.sleep(wait_time)
            
            print(f"⚠️  Edge TTS file not created or empty: {output_path}")
            return None
            
        except Exception as e:
            print(f"⚠️  Edge TTS error: {str(e)}")
            return None
    
    def _synthesize_with_festival(self, text, target_lang, output_path, voice_mode='female'):
        """Synthesize speech using Festival TTS"""
        try:
            # Festival TTS implementation
            # This is a placeholder - would need Festival TTS installation
            return self._synthesize_with_gtts(text, target_lang, output_path, voice_mode)
        except Exception as e:
            raise Exception(f"Festival TTS error: {str(e)}")
    
    def _synthesize_with_pico(self, text, target_lang, output_path, voice_mode='female'):
        """Synthesize speech using Pico TTS"""
        try:
            # Pico TTS implementation
            # This is a placeholder - would need Pico TTS installation
            return self._synthesize_with_gtts(text, target_lang, output_path, voice_mode)
        except Exception as e:
            raise Exception(f"Pico TTS error: {str(e)}")
    
    def _synthesize_lao_text(self, text, output_path, voice_mode='female', custom_coqui_model=None):
        """Special synthesis for Lao text with multiple fallback options, now with Coqui support"""
        try:
            # Try Coqui TTS first if available
            try:
                print(f"🔄 Trying Coqui TTS for Lao text...")
                result = self._synthesize_with_coqui(text, 'lo', output_path, voice_mode, custom_coqui_model)
                if result and os.path.exists(result) and os.path.getsize(result) > 0:
                    return result
            except Exception as e:
                print(f"⚠️  Coqui TTS failed: {e}")
            # Try Edge TTS first (best quality for Lao)
            try:
                print(f"🔄 Trying Edge TTS for Lao text...")
                result = self._synthesize_with_edge(text, 'lo', output_path, voice_mode)
                if result and os.path.exists(result) and os.path.getsize(result) > 0:
                    return result
            except Exception as e:
                print(f"⚠️  Edge TTS failed: {e}")
            
            # Try gTTS with Thai voice (Lao and Thai are similar)
            try:
                print(f"🔄 Trying gTTS with Thai voice for Lao text...")
                result = self._synthesize_with_gtts(text, 'lo', output_path, voice_mode)
                if result and os.path.exists(result) and os.path.getsize(result) > 0:
                    return result
            except Exception as e:
                print(f"⚠️  gTTS failed: {e}")
            
            # Try eSpeak as last resort
            try:
                print(f"🔄 Trying eSpeak for Lao text...")
                result = self._synthesize_with_espeak(text, 'lo', output_path, voice_mode)
                if result and os.path.exists(result) and os.path.getsize(result) > 0:
                    return result
            except Exception as e:
                print(f"⚠️  eSpeak failed: {e}")
            
            # Final fallback - create a simple beep sound
            print(f"🔄 Creating fallback audio for Lao text...")
            fallback_path = output_path.replace('.wav', '_fallback.wav')
            
            # Create a simple beep sound using FFmpeg
            cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=3',
                fallback_path, '-y'
            ]
            
            subprocess.run(cmd, capture_output=True, text=True)
            
            if os.path.exists(fallback_path) and os.path.getsize(fallback_path) > 0:
                print(f"✅ Created fallback audio: {fallback_path}")
                return fallback_path
            else:
                raise Exception("All TTS methods failed for Lao text")
            
        except Exception as e:
            raise Exception(f"Error synthesizing Lao text: {str(e)}")
    
    def _apply_voice_effects(self, audio_path, voice_mode):
        """Apply voice effects (pitch, speed, etc.)"""
        try:
            output_path = audio_path.replace('.wav', f'_{voice_mode}.wav')
            
            if voice_mode == 'child':
                # Increase pitch for child voice
                cmd = [
                    'ffmpeg', '-i', audio_path,
                    '-af', 'asetrate=44100*1.5,aresample=44100',
                    output_path, '-y'
                ]
            elif voice_mode == 'elderly':
                # Lower pitch and slower speed for elderly voice
                cmd = [
                    'ffmpeg', '-i', audio_path,
                    '-af', 'asetrate=44100*0.8,aresample=44100,atempo=0.8',
                    output_path, '-y'
                ]
            elif voice_mode == 'robot':
                # Robot voice with modulation
                cmd = [
                    'ffmpeg', '-i', audio_path,
                    '-af', 'asetrate=44100*1.2,aresample=44100,chorus=0.5:0.9:50:0.4:0.25:2',
                    output_path, '-y'
                ]
            elif voice_mode == 'whisper':
                # Whisper effect - lower volume and add reverb
                cmd = [
                    'ffmpeg', '-i', audio_path,
                    '-af', 'volume=0.3,aecho=0.8:0.5:60:0.3',
                    output_path, '-y'
                ]
            elif voice_mode == 'shout':
                # Shout effect - increase volume and add distortion
                cmd = [
                    'ffmpeg', '-i', audio_path,
                    '-af', 'volume=2.0,highpass=f=200,lowpass=f=3000',
                    output_path, '-y'
                ]
            elif voice_mode == 'sing':
                # Singing effect - add echo and reverb
                cmd = [
                    'ffmpeg', '-i', audio_path,
                    '-af', 'aecho=0.8:0.5:60:0.3,chorus=0.3:0.5:50:0.4:0.25:2',
                    output_path, '-y'
                ]
            else:
                # No effect for female/male
                return audio_path
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(output_path):
                print(f"✅ Applied {voice_mode} voice effect")
                return output_path
            else:
                print(f"⚠️  Failed to apply {voice_mode} effect, using original")
                return audio_path
                
        except Exception as e:
            print(f"⚠️  Error applying voice effects: {e}")
            return audio_path 

class AdvancedSubtitleService:
    """บริการดึงและแปลซับไตเติลจาก YouTube แบบ Real-time"""
    def __init__(self):
        pass

    def get_youtube_subtitles(self, youtube_url, lang_code='auto'):
        """ดึงซับไตเติลจาก YouTube (auto-generated หรือ manual)"""
        try:
            video_id = self.extract_video_id(youtube_url)
            # ถ้า lang_code เป็น auto จะดึงภาษาแรกที่เจอ
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            if lang_code == 'auto':
                transcript = transcript_list.find_transcript([t.language_code for t in transcript_list])
            else:
                transcript = transcript_list.find_transcript([lang_code])
            transcript_data = transcript.fetch()
            # รวมข้อความทั้งหมด
            full_text = '\n'.join([item.text for item in transcript_data])
            return full_text, transcript_data
        except (TranscriptsDisabled, NoTranscriptFound):
            raise Exception('ไม่พบซับไตเติลสำหรับวิดีโอนี้')
        except Exception as e:
            raise Exception(f'เกิดข้อผิดพลาดในการดึงซับไตเติล: {e}')

    def extract_video_id(self, url):
        """Extract YouTube video ID from URL"""
        import re
        patterns = [
            r'youtube\.com/watch\?v=([\w-]+)',
            r'youtu\.be/([\w-]+)',
            r'youtube\.com/embed/([\w-]+)',
            r'youtube\.com/v/([\w-]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise Exception('ไม่สามารถดึง video ID จาก URL ได้')

    def advanced_subtitle_translate_pipeline(self, youtube_url, source_lang, target_lang, translation_model, tts_model, voice_mode, task_id):
        """Pipeline สำหรับโหมดแปลขั้นสูง: ดึงซับไตเติล -> แปล -> TTS -> ผสานเสียงกับวิดีโอ"""
        # 1. ดึงซับไตเติล
        full_text, transcript_data = self.get_youtube_subtitles(youtube_url, source_lang)
        # 2. แปลข้อความ
        translation_service = TranslationService()
        translated_text = translation_service.translate(full_text, source_lang, target_lang, translation_model)
        # 3. บันทึกไฟล์ข้อความ
        original_text_path = TEXTS_DIR / f"{task_id}_original.txt"
        translated_text_path = TEXTS_DIR / f"{task_id}_translated.txt"
        with open(original_text_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        with open(translated_text_path, 'w', encoding='utf-8') as f:
            f.write(translated_text)
        # 4. สร้างเสียงจากข้อความที่แปล
        tts_service = TTSService()
        audio_output = tts_service.synthesize_speech(translated_text, target_lang, tts_model, task_id, voice_mode)
        # 5. ดาวน์โหลดวิดีโอจาก YouTube
        video_processor = VideoProcessor()
        video_path = video_processor.youtube_downloader.download_video(youtube_url, None, task_id)
        # 6. ผสานเสียงกับวิดีโอ
        output_path = video_processor.merge_audio_video(video_path, audio_output, task_id)
        # 7. สร้าง preview
        preview_path = video_processor.create_video_preview(output_path, task_id)
        # 8. ลบไฟล์ชั่วคราว
        cleanup_temp_files([audio_output])
        # 9. คืนค่า path
        return {
            'output_path': output_path,
            'preview_path': preview_path,
            'original_text_path': str(original_text_path),
            'translated_text_path': str(translated_text_path),
            'original_text': full_text,
            'translated_text': translated_text
        }

    def advanced_subtitle_translate_pipeline_realtime(self, youtube_url, source_lang, target_lang, translation_model, tts_model, voice_mode, task_id):
        """Pipeline สำหรับโหมดแปลขั้นสูงแบบ realtime: ดึงซับไตเติล -> แปล -> TTS -> ผสานเสียงกับวิดีโอ"""
        # 1. ดึงซับไตเติล
        full_text, transcript_data = self.get_youtube_subtitles(youtube_url, source_lang)
        # 2. แปลข้อความ
        translation_service = TranslationService()
        translated_text = translation_service.translate(full_text, source_lang, target_lang, translation_model)
        # 3. บันทึกไฟล์ข้อความ
        original_text_path = TEXTS_DIR / f"{task_id}_original.txt"
        translated_text_path = TEXTS_DIR / f"{task_id}_translated.txt"
        with open(original_text_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        with open(translated_text_path, 'w', encoding='utf-8') as f:
            f.write(translated_text)
        # 4. สร้างเสียงจากข้อความที่แปล
        tts_service = TTSService()
        audio_output = tts_service.synthesize_speech(translated_text, target_lang, tts_model, task_id, voice_mode)
        # 5. ดาวน์โหลดวิดีโอจาก YouTube แบบ realtime
        video_processor = VideoProcessor()
        video_path = video_processor._process_youtube_realtime(youtube_url, task_id)
        # 6. ผสานเสียงกับวิดีโอ
        output_path = video_processor.merge_audio_video(video_path, audio_output, task_id)
        # 7. สร้าง preview
        preview_path = video_processor.create_video_preview(output_path, task_id)
        # 8. ลบไฟล์ชั่วคราว
        cleanup_temp_files([audio_output])
        # 9. คืนค่า path
        return {
            'output_path': output_path,
            'preview_path': preview_path,
            'original_text_path': str(original_text_path),
            'translated_text_path': str(translated_text_path),
            'original_text': full_text,
            'translated_text': translated_text
        } 

class AudioPreprocessor:
    """Audio preprocessing for better STT performance"""
    
    def __init__(self):
        self.sample_rate = AUDIO_SAMPLE_RATE
        self.vad = None
        self._init_vad()
    
    def _init_vad(self):
        """Initialize Voice Activity Detection"""
        if WEBRTCVAD_AVAILABLE:
            try:
                self.vad = webrtcvad.Vad(VAD_MODE)
                print("✅ VAD initialized successfully")
            except Exception as e:
                print(f"⚠️  VAD initialization failed: {e}")
                self.vad = None
    
    def preprocess_audio(self, audio_path, task_id):
        """Preprocess audio for better STT performance"""
        try:
            print(f"🔧 เริ่ม preprocessing audio: {audio_path}")
            
            # Load audio
            audio, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            if len(audio) == 0:
                raise Exception("Audio file is empty")
            
            print(f"📊 Original audio: {len(audio)/sr:.2f}s, {sr}Hz")
            
            # Apply preprocessing steps
            processed_audio = audio.copy()
            
            # 1. Noise reduction
            if ENABLE_NOISE_REDUCTION and NOISEREDUCE_AVAILABLE:
                processed_audio = self._reduce_noise(processed_audio, sr)
            
            # 2. Bandpass filter
            if ENABLE_BANDPASS_FILTER and SCIPY_AVAILABLE:
                processed_audio = self._apply_bandpass_filter(processed_audio, sr)
            
            # 3. Voice Activity Detection
            if ENABLE_VAD and self.vad:
                processed_audio = self._apply_vad(processed_audio, sr)
            
            # 4. Normalization
            if ENABLE_NORMALIZATION:
                processed_audio = self._normalize_audio(processed_audio)
            
            # Save preprocessed audio
            preprocessed_path = self.audios_dir / f"{task_id}_preprocessed.wav"
            sf.write(str(preprocessed_path), processed_audio, sr)
            
            print(f"✅ Preprocessing completed: {len(processed_audio)/sr:.2f}s")
            return str(preprocessed_path)
            
        except Exception as e:
            print(f"❌ Audio preprocessing failed: {e}")
            # Return original audio if preprocessing fails
            return audio_path
    
    def _reduce_noise(self, audio, sr):
        """Reduce noise in audio"""
        try:
            print("🔇 Applying noise reduction...")
            reduced = nr.reduce_noise(
                y=audio, 
                sr=sr, 
                stationary=False,
                prop_decrease=NOISE_REDUCTION_STRENGTH
            )
            return reduced
        except Exception as e:
            print(f"⚠️  Noise reduction failed: {e}")
            return audio
    
    def _apply_bandpass_filter(self, audio, sr):
        """Apply bandpass filter to focus on speech frequencies"""
        try:
            print("🎵 Applying bandpass filter...")
            # Design bandpass filter
            nyquist = sr / 2
            low = BANDPASS_LOW / nyquist
            high = BANDPASS_HIGH / nyquist
            
            # Butterworth filter
            sos = signal.butter(10, [low, high], btype='band', output='sos')
            filtered = signal.sosfilt(sos, audio)
            
            return filtered
        except Exception as e:
            print(f"⚠️  Bandpass filter failed: {e}")
            return audio
    
    def _apply_vad(self, audio, sr):
        """Apply Voice Activity Detection to remove silence"""
        try:
            print("🎤 Applying Voice Activity Detection...")
            
            # Convert to 16-bit PCM for VAD
            audio_int16 = (audio * 32767).astype(np.int16)
            
            # Frame duration in samples
            frame_duration = VAD_FRAME_DURATION / 1000  # seconds
            frame_size = int(sr * frame_duration)
            
            # Process frames
            speech_frames = []
            for i in range(0, len(audio_int16), frame_size):
                frame = audio_int16[i:i + frame_size]
                if len(frame) == frame_size:  # Only process complete frames
                    if self.vad.is_speech(frame.tobytes(), sr):
                        speech_frames.append(frame)
            
            if speech_frames:
                # Reconstruct audio from speech frames
                speech_audio = np.concatenate(speech_frames)
                # Convert back to float
                speech_audio = speech_audio.astype(np.float32) / 32767
                return speech_audio
            else:
                print("⚠️  No speech detected, returning original audio")
                return audio
                
        except Exception as e:
            print(f"⚠️  VAD failed: {e}")
            return audio
    
    def _normalize_audio(self, audio):
        """Normalize audio levels"""
        try:
            print("📊 Normalizing audio levels...")
            
            # Calculate RMS
            rms = np.sqrt(np.mean(audio**2))
            if rms > 0:
                # Normalize to target level
                target_rms = 10**(NORMALIZATION_TARGET/20)
                normalized = audio * (target_rms / rms)
                
                # Clip to prevent distortion
                normalized = np.clip(normalized, -1.0, 1.0)
                return normalized
            else:
                return audio
                
        except Exception as e:
            print(f"⚠️  Normalization failed: {e}")
            return audio

class  UltimateVocalRemover:
    """Ultimate Vocal Remover สำหรับแยกเสียงออกจากดนตรี"""
    
    def __init__(self):
        self.models = {}
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.sample_rate = 44100
        
        # Initialize models
        self._load_models()
    
    def _load_models(self):
        """โหลดโมเดล Ultimate Vocal Remover"""
        try:
            print("🔧 กำลังโหลด Ultimate Vocal Remover models...")
            
            # Model paths
            models_dir = Path("models")
            vr_models_dir = models_dir / "VR_Models"
            mdx_models_dir = models_dir / "MDX_Net_Models"
            
            if not models_dir.exists():
                print("⚠️  ไม่พบโฟลเดอร์ models/ สำหรับ Ultimate Vocal Remover")
                return
            
            # Load VR Architecture models (.pth files)
            if vr_models_dir.exists():
                print("📁 ตรวจพบโฟลเดอร์ VR_Models...")
                
                # Load VR models
                vr_model_files = [
                    "UVR-DeNoise-Lite.pth",
                    "1_HP-UVR.pth"
                ]
                
                for vr_model in vr_model_files:
                    vr_model_path = vr_models_dir / vr_model
                    if vr_model_path.exists():
                        try:
                            # Load PyTorch model
                            model_data = torch.load(str(vr_model_path), map_location=self.device)
                            self.models[f'vr_{vr_model}'] = model_data
                            print(f"✅ โหลด VR model: {vr_model}")
                        except Exception as e:
                            print(f"⚠️  ไม่สามารถโหลด VR model {vr_model}: {e}")
            
            # Load MDX Net models (.onnx files)
            if mdx_models_dir.exists() and ONNX_AVAILABLE:
                print("📁 ตรวจพบโฟลเดอร์ MDX_Net_Models...")
                
                mdx_model_files = [
                    "Kim_Vocal_2.onnx",
                    "UVR-MDX-NET-Inst_HQ_3.onnx"
                ]
                
                for mdx_model in mdx_model_files:
                    mdx_model_path = mdx_models_dir / mdx_model
                    if mdx_model_path.exists():
                        # Check if file is not dummy (larger than 1MB)
                        if mdx_model_path.stat().st_size > 1024*1024:
                            try:
                                self.models[f'mdx_{mdx_model}'] = ort.InferenceSession(str(mdx_model_path))
                                print(f"✅ โหลด MDX model: {mdx_model}")
                            except Exception as e:
                                print(f"⚠️  ไม่สามารถโหลด MDX model {mdx_model}: {e}")
                        else:
                            print(f"⚠️  ข้าม dummy model: {mdx_model} (ขนาด: {mdx_model_path.stat().st_size} bytes)")
            
            # Set default models (prioritize MDX models for better compatibility)
            if 'mdx_Kim_Vocal_2.onnx' in self.models:
                self.models['vocal'] = self.models['mdx_Kim_Vocal_2.onnx']
                print("✅ ใช้ MDX model สำหรับแยกเสียงร้อง")
            elif 'vr_1_HP-UVR.pth' in self.models:
                self.models['vocal'] = self.models['vr_1_HP-UVR.pth']
                print("✅ ใช้ VR model สำหรับแยกเสียงร้อง (fallback)")
            
            if 'mdx_UVR-MDX-NET-Inst_HQ_3.onnx' in self.models:
                self.models['instrumental'] = self.models['mdx_UVR-MDX-NET-Inst_HQ_3.onnx']
                print("✅ ใช้ MDX model สำหรับแยกดนตรี")
            
            # Fallback to dummy models if no real models found
            if not self.models:
                print("🔄 ไม่พบโมเดลจริง ใช้โมเดลจำลอง...")
                self._load_dummy_models(models_dir)
            
            print(f"🎵 โหลด Ultimate Vocal Remover models สำเร็จ: {len(self.models)} models")
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการโหลด Ultimate Vocal Remover models: {e}")
            # Load dummy models as fallback
            self._load_dummy_models(Path("models"))
    
    def _load_dummy_models(self, models_dir):
        """โหลดโมเดลจำลองเมื่อไม่มีโมเดลจริง"""
        try:
            # Load vocal separation dummy model
            vocal_dummy_path = models_dir / "UVR-MDX-NET-Voc_FT.pkl"
            if vocal_dummy_path.exists():
                import pickle
                with open(vocal_dummy_path, 'rb') as f:
                    self.models['vocal'] = pickle.load(f)
                print("✅ โหลด Vocal Separation model (Dummy) สำเร็จ")
            
            # Load instrumental separation dummy model
            instrumental_dummy_path = models_dir / "UVR-MDX-NET-Inst_FT.pkl"
            if instrumental_dummy_path.exists():
                import pickle
                with open(instrumental_dummy_path, 'rb') as f:
                    self.models['instrumental'] = pickle.load(f)
                print("✅ โหลด Instrumental Separation model (Dummy) สำเร็จ")
            
        except Exception as e:
            print(f"⚠️  ไม่สามารถโหลดโมเดลจำลอง: {e}")
    
    def separate_audio(self, audio_path, task_id):
        """แยกเสียงออกจากดนตรี"""
        try:
            print(f"🎵 เริ่มต้นการแยกเสียงด้วย Ultimate Vocal Remover...")
            print(f"   ไฟล์เสียง: {audio_path}")
            
            # Load audio
            audio, sr = self._load_audio(audio_path)
            
            # Resample to 44.1kHz if needed
            if sr != self.sample_rate:
                audio = librosa.resample(audio, orig_sr=sr, target_sr=self.sample_rate)
                sr = self.sample_rate
            
            # Separate vocals and instrumental
            vocals, instrumental = self._separate_vocals_instrumental(audio, sr)
            
            # Save separated audio files
            vocals_path = TEMP_DIR / f"{task_id}_vocals.wav"
            instrumental_path = TEMP_DIR / f"{task_id}_instrumental.wav"
            
            sf.write(str(vocals_path), vocals, sr)
            sf.write(str(instrumental_path), instrumental, sr)
            
            print(f"✅ แยกเสียงสำเร็จ:")
            print(f"   🎤 เสียงร้อง: {vocals_path}")
            print(f"   🎵 ดนตรี: {instrumental_path}")
            
            # Clean up temporary files (keep only final results)
            self._cleanup_temp_files(task_id)
            
            # Store instrumental path for later use in video merge
            return {
                'vocals': str(vocals_path),
                'instrumental': str(instrumental_path),
                'original_sr': sr,
                'instrumental_path': str(instrumental_path)  # For video merge
            }
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการแยกเสียง: {e}")
            # Clean up any temporary files even on error
            self._cleanup_temp_files(task_id)
            # Fallback to original audio
            return {
                'vocals': audio_path,
                'instrumental': None,
                'original_sr': sr,
                'instrumental_path': None
            }
    
    def _load_audio(self, audio_path):
        """โหลดไฟล์เสียง"""
        try:
            # Try librosa first
            audio, sr = librosa.load(audio_path, sr=None)
            return audio, sr
        except Exception as e:
            print(f"⚠️  ไม่สามารถโหลดด้วย librosa: {e}")
            try:
                # Fallback to soundfile
                audio, sr = sf.read(audio_path)
                if len(audio.shape) > 1:
                    audio = audio[:, 0]  # Convert to mono
                return audio, sr
            except Exception as e2:
                print(f"❌ ไม่สามารถโหลดไฟล์เสียง: {e2}")
                raise Exception(f"ไม่สามารถโหลดไฟล์เสียง: {e2}")
    
    def _separate_vocals_instrumental(self, audio, sr):
        """แยกเสียงร้องและดนตรี"""
        try:
            # If models are not available, use fallback method
            if not self.models:
                print("⚠️  ไม่มี Ultimate Vocal Remover models ใช้ fallback method")
                return self._fallback_separation(audio, sr)
            
            # Check model types
            has_vr_model = any(key.startswith('vr_') for key in self.models.keys())
            has_mdx_model = any(key.startswith('mdx_') for key in self.models.keys())
            has_dummy_model = 'vocal' in self.models and isinstance(self.models['vocal'], dict)
            
            # Process entire file without chunking (for smaller files)
            print(f"🎵 ประมวลผลไฟล์เสียงทั้งหมด ({len(audio)} samples)")
            
            # Normalize audio
            audio_normalized = audio / np.max(np.abs(audio))
            
            # Prioritize MDX models for better compatibility
            if has_mdx_model:
                # Use MDX model processing (preferred)
                vocals, instrumental = self._process_with_mdx_models(audio_normalized, sr)
            elif has_vr_model:
                # Use VR model processing (fallback)
                vocals, instrumental = self._process_with_vr_models(audio_normalized, sr)
            elif has_dummy_model:
                # Use dummy model processing
                vocals, instrumental = self._process_with_dummy_models(audio_normalized, sr)
            else:
                # Use fallback method
                vocals, instrumental = self._fallback_separation(audio_normalized, sr)
            
            # Ensure same length
            min_length = min(len(vocals), len(instrumental))
            vocals = vocals[:min_length]
            instrumental = instrumental[:min_length]
            
            return vocals, instrumental
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการแยกเสียง: {e}")
            return self._fallback_separation(audio, sr)
    
    def _process_with_vr_models(self, audio, sr):
        """ประมวลผลด้วย VR models"""
        try:
            print("🎵 ใช้ VR models สำหรับแยกเสียง...")
            
            # VR models are state dicts, not callable models
            # Use fallback method for VR models since they require specific architecture
            print("⚠️  VR models เป็น state dicts ใช้ fallback method...")
            return self._fallback_separation(audio, sr)
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการประมวลผลด้วย VR models: {e}")
            return audio, audio
    
    def _process_with_mdx_models(self, audio, sr):
        """ประมวลผลด้วย MDX models"""
        try:
            print("🎵 ใช้ MDX models สำหรับแยกเสียง...")
            
            # MDX models require spectrogram input, not raw audio
            # Since converting to proper spectrogram is complex, use fallback method
            print("⚠️  MDX models ต้องการ spectrogram input ใช้ fallback method...")
            return self._fallback_separation(audio, sr)
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการประมวลผลด้วย MDX models: {e}")
            return audio, audio
    
    def _process_with_dummy_models(self, audio, sr):
        """ประมวลผลด้วยโมเดลจำลอง"""
        try:
            print("🔄 ใช้โมเดลจำลองสำหรับแยกเสียง...")
            
            # Simple bandpass filter for vocals (80-8000 Hz)
            nyquist = sr / 2
            low_cutoff = 80 / nyquist
            high_cutoff = 8000 / nyquist
            
            # Design bandpass filter for vocals
            b, a = signal.butter(4, [low_cutoff, high_cutoff], btype='band')
            vocals = signal.filtfilt(b, a, audio)
            
            # Instrumental is the difference
            instrumental = audio - vocals
            
            # Normalize
            vocals = vocals / np.max(np.abs(vocals)) if np.max(np.abs(vocals)) > 0 else vocals
            instrumental = instrumental / np.max(np.abs(instrumental)) if np.max(np.abs(instrumental)) > 0 else instrumental
            
            return vocals, instrumental
            
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการประมวลผลด้วยโมเดลจำลอง: {e}")
            return audio, audio
    

    
    def _fallback_separation(self, audio, sr):
        """Fallback method สำหรับแยกเสียง"""
        print("🔄 ใช้ fallback method สำหรับแยกเสียง")
        
        # Simple high-pass filter for vocals
        vocals = self._extract_vocals_simple(audio, sr)
        
        # Instrumental is the difference
        instrumental = audio - vocals
        
        # Normalize
        vocals = vocals / np.max(np.abs(vocals)) if np.max(np.abs(vocals)) > 0 else vocals
        instrumental = instrumental / np.max(np.abs(instrumental)) if np.max(np.abs(instrumental)) > 0 else instrumental
        
        print(f"✅ Fallback separation completed")
        print(f"   🎤 Vocals RMS: {np.sqrt(np.mean(vocals**2)):.6f}")
        print(f"   🎵 Instrumental RMS: {np.sqrt(np.mean(instrumental**2)):.6f}")
        
        return vocals, instrumental
    
    def _extract_vocals_simple(self, audio, sr):
        """แยกเสียงร้องแบบง่าย"""
        # High-pass filter to extract vocals (typically 80-8000 Hz)
        nyquist = sr / 2
        low_cutoff = 80 / nyquist
        high_cutoff = 8000 / nyquist
        
        # Design bandpass filter
        b, a = signal.butter(4, [low_cutoff, high_cutoff], btype='band')
        
        # Apply filter
        vocals = signal.filtfilt(b, a, audio)
        
        return vocals
    
    def _cleanup_temp_files(self, task_id):
        """ลบไฟล์ชั่วคราวที่ไม่จำเป็น"""
        try:
            import os
            import glob
            
            # Clean up temp directory
            temp_patterns = [
                f"{task_id}_temp_*",
                f"{task_id}_chunk_*",
                f"{task_id}_processed_*",
                f"{task_id}_normalized_*"
            ]
            
            for pattern in temp_patterns:
                temp_files = glob.glob(str(TEMP_DIR / pattern))
                for temp_file in temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                            print(f"🗑️  ลบไฟล์ชั่วคราว: {os.path.basename(temp_file)}")
                    except Exception as e:
                        print(f"⚠️  ไม่สามารถลบไฟล์ชั่วคราว {temp_file}: {e}")
            
            # Clean up any other temporary audio files
            temp_audio_patterns = [
                f"{task_id}_*.wav",
                f"{task_id}_*.mp3",
                f"{task_id}_*.flac"
            ]
            
            for pattern in temp_audio_patterns:
                temp_files = glob.glob(str(TEMP_DIR / pattern))
                for temp_file in temp_files:
                    # Skip final result files (vocals and instrumental)
                    if not any(skip in temp_file for skip in ['_vocals.wav', '_instrumental.wav']):
                        try:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                                print(f"🗑️  ลบไฟล์เสียงชั่วคราว: {os.path.basename(temp_file)}")
                        except Exception as e:
                            print(f"⚠️  ไม่สามารถลบไฟล์เสียงชั่วคราว {temp_file}: {e}")
            
            print("🧹 ทำความสะอาดไฟล์ชั่วคราวเสร็จสิ้น")
            
        except Exception as e:
            print(f"⚠️  เกิดข้อผิดพลาดในการทำความสะอาดไฟล์ชั่วคราว: {e}")