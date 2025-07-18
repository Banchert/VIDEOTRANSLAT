"""
Video Translator Application - Optimized Main Entry Point
แอปพลิเคชันแปลวิดีโอ - จุดเริ่มต้นหลักที่ปรับปรุงแล้ว
"""

import os
import json
import uuid
import re
import subprocess
import tempfile
import warnings
import threading
import gc
import psutil
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Import configuration and services
from config import *
from services import VideoProcessor, TranslationService, TTSService, JobQueue, AdvancedSubtitleService

# Initialize Flask app
app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = FLASK_SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Initialize CORS
CORS(app)

# Global variables with thread safety
current_device = 'auto'
memory_monitor = None

# Thread safety for global variables
tasks_data_lock = threading.Lock()
memory_lock = threading.Lock()

# Initialize job queue with memory monitoring
job_queue = JobQueue(MAX_CONCURRENT_JOBS)

# Task storage for step-by-step processing with cleanup
tasks_data = {}

def allowed_file(filename):
    """Check if file extension is allowed"""
    if not filename:
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_memory():
    """Clean up memory and force garbage collection with cooldown"""
    try:
        current_time = time.time()
        
        # Check if enough time has passed since last cleanup
        if hasattr(cleanup_memory, 'last_cleanup_time'):
            if current_time - cleanup_memory.last_cleanup_time < 30:  # 30 second cooldown
                return
        else:
            cleanup_memory.last_cleanup_time = 0
        
        with memory_lock:
            gc.collect()
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            cleanup_memory.last_cleanup_time = current_time
            print("🧹 Memory cleanup completed")
    except Exception as e:
        print(f"⚠️ Memory cleanup error: {e}")

def monitor_memory_usage():
    """Monitor memory usage and cleanup if needed with cooldown"""
    try:
        # Add cooldown for memory monitoring
        current_time = time.time()
        if hasattr(monitor_memory_usage, 'last_check_time'):
            if current_time - monitor_memory_usage.last_check_time < 30:  # 30 second cooldown
                return
        else:
            monitor_memory_usage.last_check_time = 0
        
        memory = psutil.virtual_memory()
        
        # เพิ่ม memory monitoring ที่ละเอียดขึ้น
        if memory.percent > 95:  # Critical memory usage
            print(f"🚨 Critical memory usage: {memory.percent}% - Forcing cleanup")
            cleanup_memory()
        elif memory.percent > 90:  # High memory usage
            print(f"⚠️ High memory usage: {memory.percent}% - Recommended cleanup")
            cleanup_memory()
        elif memory.percent > 80:  # Moderate memory usage
            print(f"📊 Memory usage: {memory.percent}% - Monitoring")
        
        # Log memory stats every 10 minutes
        if not hasattr(monitor_memory_usage, 'last_log_time'):
            monitor_memory_usage.last_log_time = 0
        
        if current_time - monitor_memory_usage.last_log_time > 600:  # 10 minutes
            print(f"💾 Memory Stats - Used: {memory.percent}%, Available: {memory.available / (1024**3):.1f}GB")
            monitor_memory_usage.last_log_time = current_time
        
        monitor_memory_usage.last_check_time = current_time
    except Exception as e:
        print(f"⚠️ Memory monitoring error: {e}")

def cleanup_task_data(task_id):
    """Clean up task data and associated files"""
    try:
        with tasks_data_lock:
            if task_id in tasks_data:
                task_data = tasks_data[task_id]
                
                # Clean up temporary files
                temp_files = []
                for key in ['video_path', 'audio_path', 'vocals_path', 'instrumental_path', 'tts_audio_path']:
                    if key in task_data and task_data[key]:
                        file_path = task_data[key]
                        if os.path.exists(file_path) and os.path.isfile(file_path):
                            temp_files.append(file_path)
                
                # Clean up temp files
                cleanup_temp_files(temp_files)
                
                # Remove from tasks_data
                del tasks_data[task_id]
                print(f"🧹 Cleaned up task data for {task_id}")
                
    except Exception as e:
        print(f"⚠️ Error cleaning up task data for {task_id}: {e}")

def safe_get_task_data(task_id):
    """Safely get task data with thread safety"""
    with tasks_data_lock:
        return tasks_data.get(task_id, {}).copy()

def safe_update_task_data(task_id, updates):
    """Safely update task data with thread safety"""
    with tasks_data_lock:
        if task_id in tasks_data:
            tasks_data[task_id].update(updates)

def safe_remove_task_data(task_id):
    """Safely remove task data with thread safety"""
    with tasks_data_lock:
        if task_id in tasks_data:
            del tasks_data[task_id]

# Flask Routes with memory optimization
@app.route('/')
def index():
    """Main page"""
    # Only monitor memory every 60 seconds for page requests
    current_time = time.time()
    if not hasattr(index, 'last_memory_check'):
        index.last_memory_check = 0
    
    if current_time - index.last_memory_check > 60:
        monitor_memory_usage()
        index.last_memory_check = current_time
    
    return render_template('index.html', video_speed_options=VIDEO_SPEED_OPTIONS)

@app.route('/test')
def test_form():
    """Test form page"""
    # Only monitor memory every 60 seconds for page requests
    current_time = time.time()
    if not hasattr(test_form, 'last_memory_check'):
        test_form.last_memory_check = 0
    
    if current_time - test_form.last_memory_check > 60:
        monitor_memory_usage()
        test_form.last_memory_check = current_time
    
    return render_template('test_form_submit.html')

@app.route('/debug')
def debug_form():
    """Debug form page"""
    # Only monitor memory every 60 seconds for page requests
    current_time = time.time()
    if not hasattr(debug_form, 'last_memory_check'):
        debug_form.last_memory_check = 0
    
    if current_time - debug_form.last_memory_check > 60:
        monitor_memory_usage()
        debug_form.last_memory_check = current_time
    
    return render_template('debug_form.html')

@app.route('/simple')
def simple_test():
    """Simple test page"""
    # Only monitor memory every 60 seconds for page requests
    current_time = time.time()
    if not hasattr(simple_test, 'last_memory_check'):
        simple_test.last_memory_check = 0
    
    if current_time - simple_test.last_memory_check > 60:
        monitor_memory_usage()
        simple_test.last_memory_check = current_time
    
    return render_template('simple_test.html')

# ===== YOUTUBE URL (REAL-TIME) MODE =====
@app.route('/api/youtube/realtime', methods=['POST'])
def youtube_realtime():
    """Process YouTube URL in real-time mode with memory optimization"""
    try:
        print("🎬 YouTube real-time processing request received")
        # Only monitor memory every 60 seconds for processing requests
        current_time = time.time()
        if not hasattr(youtube_realtime, 'last_memory_check'):
            youtube_realtime.last_memory_check = 0
        
        if current_time - youtube_realtime.last_memory_check > 60:
            monitor_memory_usage()
            youtube_realtime.last_memory_check = current_time
        
        data = request.get_json()
        
        if not data:
            print("❌ No data provided")
            return jsonify({'error': 'No data provided'}), 400
        
        video_url = data.get('video_url')
        if not video_url:
            print("❌ No YouTube URL provided")
            return jsonify({'error': 'No YouTube URL provided'}), 400
        
        print(f"📺 Processing YouTube URL: {video_url}")
        
        # Validate YouTube URL
        if not any(re.match(pattern, video_url) for pattern in YOUTUBE_PATTERNS):
            print("❌ Invalid YouTube URL")
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        print(f"🆔 Generated task ID: {task_id}")
        
        task_data = {
            'mode': 'youtube_realtime',
            'video_url': video_url,
            'source_lang': data.get('source_lang', 'auto'),
            'target_lang': data.get('target_lang', 'th'),
            'stt_model': data.get('stt_model', 'base'),
            'translation_model': data.get('translation_model', 'nllb-200'),
            'tts_model': data.get('tts_model', 'gtts'),
            'voice_mode': data.get('voice_mode', 'female'),
            'video_speed': data.get('video_speed', '1.0'),
            'custom_coqui_model': data.get('custom_coqui_model', None),
            # Advanced audio processing options
            'enable_preprocessing': data.get('enable_preprocessing', True),
            'enable_noise_reduction': data.get('enable_noise_reduction', True),
            'enable_vad': data.get('enable_vad', True),
            'enable_tts_sync': data.get('enable_tts_sync', True),
            # Ultimate Vocal Remover options
            'enable_vocal_removal': data.get('enable_vocal_removal', False),
            'enable_instrumental_mixing': data.get('enable_instrumental_mixing', False),
            'sync_original_audio': data.get('sync_original_audio', False),
            # Processing steps control - ทุกขั้นตอน
            'enable_step1_video_processing': data.get('enable_step1_video_processing', True),
            'enable_step2_vocal_removal': data.get('enable_step2_vocal_removal', True),
            'enable_step3_stt': data.get('enable_step3_stt', True),
            'enable_step4_translation': data.get('enable_step4_translation', True),
            'enable_step5_tts': data.get('enable_step5_tts', True),
            'enable_step6_audio_mixing': data.get('enable_step6_audio_mixing', True),
            'enable_step7_video_merge': data.get('enable_step7_video_merge', True),
            # Unlimited processing flags
            'unlimited_mode': True,
            'unlimited_audio_length': True,
            'unlimited_file_size': True,
            'unlimited_processing_time': True
        }
        
        # Add job to queue
        print(f"📋 Adding job to queue with task ID: {task_id}")
        job = job_queue.add_job(task_id, task_data)
        
        print(f"✅ Job added successfully. Queue position: {job_queue.queue.qsize()}")
        
        return jsonify({
            'task_id': task_id,
            'message': 'YouTube real-time processing added to queue',
            'queue_position': job_queue.queue.qsize()
        })
        
    except Exception as e:
        print(f"❌ Error in YouTube real-time processing: {str(e)}")
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

# ===== FILE UPLOAD MODE =====
@app.route('/api/upload/auto', methods=['POST'])
def file_upload_auto():
    """Process uploaded file in auto mode with memory optimization"""
    task_id = None
    try:
        print("📁 File upload auto processing request received")
        # Only monitor memory every 60 seconds for processing requests
        current_time = time.time()
        if not hasattr(file_upload_auto, 'last_memory_check'):
            file_upload_auto.last_memory_check = 0
        
        if current_time - file_upload_auto.last_memory_check > 60:
            monitor_memory_usage()
            file_upload_auto.last_memory_check = current_time
        
        if 'video' not in request.files:
            print("❌ No video file provided")
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if not file or file.filename == '':
            print("❌ No file selected")
            return jsonify({'error': 'No file selected'}), 400
        
        print(f"📄 Processing file: {file.filename}")
        
        if not allowed_file(file.filename):
            print(f"❌ File type not allowed: {file.filename}")
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        print(f"🆔 Generated task ID: {task_id}")
        
        # Save uploaded file
        filename = secure_filename(file.filename or 'video')
        file_path = UPLOADS_DIR / f"{task_id}_{filename}"
        file.save(str(file_path))
        
        task_data = {
            'mode': 'file_auto',
            'video_input': str(file_path),
            'source_lang': request.form.get('source_lang', 'auto'),
            'target_lang': request.form.get('target_lang', 'th'),
            'stt_model': request.form.get('stt_model', 'base'),
            'translation_model': request.form.get('translation_model', 'nllb-200'),
            'tts_model': request.form.get('tts_model', 'gtts'),
            'voice_mode': request.form.get('voice_mode', 'female'),
            'video_speed': request.form.get('video_speed', '1.0'),
            'custom_coqui_model': request.form.get('custom_coqui_model', None),
            # Advanced audio processing options
            'enable_preprocessing': request.form.get('enable_preprocessing', 'true').lower() == 'true',
            'enable_noise_reduction': request.form.get('enable_noise_reduction', 'true').lower() == 'true',
            'enable_vad': request.form.get('enable_vad', 'true').lower() == 'true',
            'enable_tts_sync': request.form.get('enable_tts_sync', 'true').lower() == 'true',
            # Ultimate Vocal Remover options
            'enable_vocal_removal': request.form.get('enable_vocal_removal', 'false').lower() == 'true',
            'enable_instrumental_mixing': request.form.get('enable_instrumental_mixing', 'false').lower() == 'true',
            'sync_original_audio': request.form.get('sync_original_audio', 'false').lower() == 'true',
            # Processing steps control - ทุกขั้นตอน
            'enable_step1_video_processing': request.form.get('enable_step1_video_processing', 'true').lower() == 'true',
            'enable_step2_vocal_removal': request.form.get('enable_step2_vocal_removal', 'true').lower() == 'true',
            'enable_step3_stt': request.form.get('enable_step3_stt', 'true').lower() == 'true',
            'enable_step4_translation': request.form.get('enable_step4_translation', 'true').lower() == 'true',
            'enable_step5_tts': request.form.get('enable_step5_tts', 'true').lower() == 'true',
            'enable_step6_audio_mixing': request.form.get('enable_step6_audio_mixing', 'true').lower() == 'true',
            'enable_step7_video_merge': request.form.get('enable_step7_video_merge', 'true').lower() == 'true',
            # Unlimited processing flags
            'unlimited_mode': True,
            'unlimited_audio_length': True,
            'unlimited_file_size': True,
            'unlimited_processing_time': True
        }
        
        # Add job to queue
        print(f"📋 Adding job to queue with task ID: {task_id}")
        job = job_queue.add_job(task_id, task_data)
        
        print(f"✅ Job added successfully. Queue position: {job_queue.queue.qsize()}")
        
        return jsonify({
            'task_id': task_id,
            'message': 'File upload processing added to queue',
            'queue_position': job_queue.queue.qsize()
        })
        
    except Exception as e:
        print(f"❌ Error in file upload processing: {str(e)}")
        if task_id:
            cleanup_task_data(task_id)
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

# ===== STEP-BY-STEP PROCESSING =====
@app.route('/api/upload/step', methods=['POST'])
def file_upload_step():
    """Process uploaded file in step-by-step mode with memory optimization"""
    task_id = None
    try:
        print("📁 File upload step-by-step processing request received")
        # Only monitor memory every 60 seconds for processing requests
        current_time = time.time()
        if not hasattr(file_upload_step, 'last_memory_check'):
            file_upload_step.last_memory_check = 0
        
        if current_time - file_upload_step.last_memory_check > 60:
            monitor_memory_usage()
            file_upload_step.last_memory_check = current_time
        
        if 'video' not in request.files:
            print("❌ No video file provided")
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if not file or file.filename == '':
            print("❌ No file selected")
            return jsonify({'error': 'No file selected'}), 400
        
        print(f"📄 Processing file: {file.filename}")
        
        if not allowed_file(file.filename):
            print(f"❌ File type not allowed: {file.filename}")
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        print(f"🆔 Generated task ID: {task_id}")
        
        # Save uploaded file
        filename = secure_filename(file.filename or 'video')
        file_path = UPLOADS_DIR / f"{task_id}_{filename}"
        file.save(str(file_path))
        
        task_data = {
            'mode': 'file_step',
            'video_input': str(file_path),
            'source_lang': request.form.get('source_lang', 'auto'),
            'target_lang': request.form.get('target_lang', 'th'),
            'stt_model': request.form.get('stt_model', 'base'),
            'translation_model': request.form.get('translation_model', 'nllb-200'),
            'tts_model': request.form.get('tts_model', 'gtts'),
            'voice_mode': request.form.get('voice_mode', 'female'),
            'video_speed': request.form.get('video_speed', '1.0'),
            'custom_coqui_model': request.form.get('custom_coqui_model', None),
            # Advanced audio processing options
            'enable_preprocessing': request.form.get('enable_preprocessing', 'true').lower() == 'true',
            'enable_noise_reduction': request.form.get('enable_noise_reduction', 'true').lower() == 'true',
            'enable_vad': request.form.get('enable_vad', 'true').lower() == 'true',
            'enable_tts_sync': request.form.get('enable_tts_sync', 'true').lower() == 'true',
            # Ultimate Vocal Remover options
            'enable_vocal_removal': request.form.get('enable_vocal_removal', 'false').lower() == 'true',
            'enable_instrumental_mixing': request.form.get('enable_instrumental_mixing', 'false').lower() == 'true',
            'sync_original_audio': request.form.get('sync_original_audio', 'false').lower() == 'true',
            # Processing steps control - ทุกขั้นตอน
            'enable_step1_video_processing': request.form.get('enable_step1_video_processing', 'true').lower() == 'true',
            'enable_step2_vocal_removal': request.form.get('enable_step2_vocal_removal', 'true').lower() == 'true',
            'enable_step3_stt': request.form.get('enable_step3_stt', 'true').lower() == 'true',
            'enable_step4_translation': request.form.get('enable_step4_translation', 'true').lower() == 'true',
            'enable_step5_tts': request.form.get('enable_step5_tts', 'true').lower() == 'true',
            'enable_step6_audio_mixing': request.form.get('enable_step6_audio_mixing', 'true').lower() == 'true',
            'enable_step7_video_merge': request.form.get('enable_step7_video_merge', 'true').lower() == 'true',
            # Unlimited processing flags
            'unlimited_mode': True,
            'unlimited_audio_length': True,
            'unlimited_file_size': True,
            'unlimited_processing_time': True
        }
        
        # Store task data for step-by-step processing
        with tasks_data_lock:
            tasks_data[task_id] = task_data
        
        print(f"✅ Task data stored for step-by-step processing. Task ID: {task_id}")
        
        return jsonify({
            'task_id': task_id,
            'message': 'File uploaded for step-by-step processing',
            'next_step': 1
        })
        
    except Exception as e:
        print(f"❌ Error in file upload step processing: {str(e)}")
        if task_id:
            cleanup_task_data(task_id)
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

@app.route('/api/step/<task_id>/<int:step>', methods=['POST'])
def process_step(task_id, step):
    """Process specific step with memory optimization"""
    try:
        print(f"🔄 Processing step {step} for task {task_id}")
        monitor_memory_usage()
        
        task_data = safe_get_task_data(task_id)
        if not task_data:
            return jsonify({'error': 'Task not found'}), 404
        
        request_data = request.get_json() or {}
        
        # Update task data with request data
        safe_update_task_data(task_id, request_data)
        
        try:
            if step == 1:
                result = process_video_step(task_id, task_data)
            elif step == 2:
                result = process_vocal_removal_step(task_id, task_data)
            elif step == 3:
                result = process_stt_step(task_id, task_data)
            elif step == 4:
                result = process_translation_step(task_id, task_data)
            elif step == 5:
                result = process_tts_step(task_id, task_data)
            elif step == 6:
                result = process_audio_mixing_step(task_id, task_data)
            elif step == 7:
                result = process_merge_step(task_id, task_data)
            else:
                return jsonify({'error': 'Invalid step number'}), 400
            
            # Cleanup memory after each step
            cleanup_memory()
            
            return jsonify(result)
            
        except Exception as e:
            print(f"❌ Error in step {step}: {str(e)}")
            cleanup_memory()
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        print(f"❌ Error in process_step: {str(e)}")
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

def process_video_step(task_id, task_data):
    """Process video step with memory optimization"""
    try:
        print(f"🎬 Processing video step for task {task_id}")
        
        video_processor = VideoProcessor()
        video_path = video_processor.process_video_input(
            task_data['video_input'], 
            task_id, 
            realtime=False
        )
        
        # Update task data with dictionary
        result = {
            'video_path': video_path
        }
        safe_update_task_data(task_id, result)
        
        return {
            'status': 'success',
            'message': 'Video processing completed',
            'next_step': 2,
            'data': result
        }
        
    except Exception as e:
        raise Exception(f"Video processing error: {str(e)}")

def process_vocal_removal_step(task_id, task_data):
    """Process vocal removal step with memory optimization"""
    try:
        print(f"🎤 Processing vocal removal step for task {task_id}")
        
        video_processor = VideoProcessor()
        audio_path = video_processor.extract_audio(
            task_data.get('video_path', task_data['video_input']), 
            task_id, 
            enable_vocal_removal=True
        )
        
        # Update task data with dictionary
        result = {
            'audio_path': audio_path,
            'vocals_path': audio_path  # For compatibility
        }
        safe_update_task_data(task_id, result)
        
        return {
            'status': 'success',
            'message': 'Vocal removal completed',
            'next_step': 3,
            'data': result
        }
        
    except Exception as e:
        raise Exception(f"Vocal removal error: {str(e)}")

def process_stt_step(task_id, task_data):
    """Process STT step with memory optimization"""
    try:
        print(f"🎧 Processing STT step for task {task_id}")
        
        video_processor = VideoProcessor()
        transcription = video_processor.transcribe_audio(
            task_data.get('audio_path', task_data.get('vocals_path')), 
            task_data['stt_model'], 
            task_data['source_lang'], 
            task_id
        )
        
        # Update task data with dictionary
        result = {
            'transcription': transcription
        }
        safe_update_task_data(task_id, result)
        
        return {
            'status': 'success',
            'message': 'Speech-to-text completed',
            'next_step': 4,
            'data': result
        }
        
    except Exception as e:
        raise Exception(f"STT error: {str(e)}")

def process_translation_step(task_id, task_data):
    """Process translation step with memory optimization"""
    try:
        print(f"🌐 Processing translation step for task {task_id}")
        
        translation_service = TranslationService()
        translation = translation_service.translate(
            task_data.get('transcription', ''), 
            task_data['source_lang'], 
            task_data['target_lang'], 
            task_data['translation_model']
        )
        
        # Update task data with dictionary
        result = {
            'translation': translation
        }
        safe_update_task_data(task_id, result)
        
        return {
            'status': 'success',
            'message': 'Translation completed',
            'next_step': 5,
            'data': result
        }
        
    except Exception as e:
        raise Exception(f"Translation error: {str(e)}")

def process_tts_step(task_id, task_data):
    """Process TTS step with memory optimization"""
    try:
        print(f"🔊 Processing TTS step for task {task_id}")
        
        tts_service = TTSService()
        tts_audio_path = tts_service.synthesize_speech(
            task_data.get('translation', ''), 
            task_data['target_lang'], 
            task_data['tts_model'], 
            task_id, 
            task_data['voice_mode'], 
            task_data.get('custom_coqui_model')
        )
        
        # Update task data with dictionary
        result = {
            'tts_audio_path': tts_audio_path
        }
        safe_update_task_data(task_id, result)
        
        return {
            'status': 'success',
            'message': 'Text-to-speech completed',
            'next_step': 6,
            'data': result
        }
        
    except Exception as e:
        raise Exception(f"TTS error: {str(e)}")

def process_audio_mixing_step(task_id, task_data):
    """Process audio mixing step with memory optimization"""
    try:
        print(f"🎵 Processing audio mixing step for task {task_id}")
        
        video_processor = VideoProcessor()
        final_audio_path = video_processor.merge_audio_video(
            task_data.get('video_path', task_data['video_input']), 
            task_data.get('tts_audio_path'), 
            task_id, 
            task_data['video_speed'],
            task_data.get('instrumental_path'),
            task_data.get('sync_original_audio', False)
        )
        
        # Update task data with dictionary
        result = {
            'final_audio_path': final_audio_path
        }
        safe_update_task_data(task_id, result)
        
        return {
            'status': 'success',
            'message': 'Audio mixing completed',
            'next_step': 7,
            'data': result
        }
        
    except Exception as e:
        raise Exception(f"Audio mixing error: {str(e)}")

def process_merge_step(task_id, task_data):
    """Process final merge step with memory optimization"""
    try:
        print(f"🎬 Processing final merge step for task {task_id}")
        
        # Final video processing
        video_processor = VideoProcessor()
        final_video_path = video_processor.merge_audio_video(
            task_data.get('video_path', task_data['video_input']), 
            task_data.get('final_audio_path', task_data.get('tts_audio_path')), 
            task_id, 
            task_data['video_speed']
        )
        
        # Update task data with dictionary
        result = {
            'final_video_path': final_video_path
        }
        safe_update_task_data(task_id, result)
        
        # Cleanup task data after completion
        cleanup_task_data(task_id)
        
        return {
            'status': 'success',
            'message': 'Video processing completed',
            'next_step': None,
            'data': result
        }
        
    except Exception as e:
        raise Exception(f"Final merge error: {str(e)}")

# ===== API ENDPOINTS =====
@app.route('/api/text/<task_id>/<text_type>', methods=['GET'])
def get_text(task_id, text_type):
    """Get text content with memory optimization"""
    try:
        monitor_memory_usage()
        
        task_data = safe_get_task_data(task_id)
        if not task_data:
            return jsonify({'error': 'Task not found'}), 404
        
        if text_type == 'transcription':
            text = task_data.get('transcription', '')
        elif text_type == 'translation':
            text = task_data.get('translation', '')
        else:
            return jsonify({'error': 'Invalid text type'}), 400
        
        return jsonify({'text': text})
        
    except Exception as e:
        print(f"❌ Error getting text: {str(e)}")
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

@app.route('/api/text/<task_id>/<text_type>', methods=['PUT'])
def update_text(task_id, text_type):
    """Update text content with memory optimization"""
    try:
        monitor_memory_usage()
        
        task_data = safe_get_task_data(task_id)
        if not task_data:
            return jsonify({'error': 'Task not found'}), 404
        
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        updates = {}
        if text_type == 'transcription':
            updates['transcription'] = data['text']
        elif text_type == 'translation':
            updates['translation'] = data['text']
        else:
            return jsonify({'error': 'Invalid text type'}), 400
        
        safe_update_task_data(task_id, updates)
        
        return jsonify({'message': 'Text updated successfully'})
        
    except Exception as e:
        print(f"❌ Error updating text: {str(e)}")
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/<task_id>')
def get_status(task_id):
    """Get job status with memory optimization"""
    try:
        # Only monitor memory every 30 seconds for status requests
        current_time = time.time()
        if not hasattr(get_status, 'last_memory_check'):
            get_status.last_memory_check = 0
        
        if current_time - get_status.last_memory_check > 30:
            monitor_memory_usage()
            get_status.last_memory_check = current_time
        
        # Check job queue status
        job_status = job_queue.get_job_status(task_id)
        if job_status:
            return jsonify(job_status)
        
        # Check step-by-step processing status
        task_data = safe_get_task_data(task_id)
        if task_data:
            return jsonify({
                'task_id': task_id,
                'status': 'processing',
                'mode': 'step_by_step',
                'data': {
                    'source_lang': task_data.get('source_lang'),
                    'target_lang': task_data.get('target_lang'),
                    'stt_model': task_data.get('stt_model'),
                    'translation_model': task_data.get('translation_model'),
                    'tts_model': task_data.get('tts_model'),
                    'voice_mode': task_data.get('voice_mode'),
                    'video_speed': task_data.get('video_speed')
                }
            })
        
        return jsonify({'error': 'Task not found'}), 404
        
    except Exception as e:
        print(f"❌ Error getting status: {str(e)}")
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio/<task_id>/tts')
def serve_tts_audio(task_id):
    """Serve TTS audio with memory optimization"""
    try:
        monitor_memory_usage()
        
        task_data = safe_get_task_data(task_id)
        if not task_data:
            return jsonify({'error': 'Task not found'}), 404
        
        tts_audio_path = task_data.get('tts_audio_path')
        
        if not tts_audio_path or not os.path.exists(tts_audio_path):
            return jsonify({'error': 'TTS audio not found'}), 404
        
        return send_file(tts_audio_path, mimetype='audio/wav')
        
    except Exception as e:
        print(f"❌ Error serving TTS audio: {str(e)}")
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<task_id>')
def download_video(task_id):
    """Download processed video with memory optimization"""
    try:
        monitor_memory_usage()
        
        # Check job queue for completed video
        job_status = job_queue.get_job_status(task_id)
        if job_status and job_status.get('status') == 'completed':
            output_path = job_status.get('output_path')
            if output_path and os.path.exists(output_path):
                return send_file(output_path, as_attachment=True)
        
        # Check step-by-step processing
        task_data = safe_get_task_data(task_id)
        if task_data:
            output_path = task_data.get('output_path')
            if output_path and os.path.exists(output_path):
                return send_file(output_path, as_attachment=True)
        
        return jsonify({'error': 'Video not found or not completed'}), 404
        
    except Exception as e:
        print(f"❌ Error downloading video: {str(e)}")
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

# ===== SYSTEM ENDPOINTS =====
@app.route('/api/models/list')
def list_models():
    """List available models with memory optimization"""
    try:
        monitor_memory_usage()
        
        from services import ModelDownloader
        downloader = ModelDownloader()
        
        return jsonify({
            'available': downloader.get_available_models(),
            'missing': downloader.get_missing_models()
        })
        
    except Exception as e:
        print(f"❌ Error listing models: {str(e)}")
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

@app.route('/api/tts/models/available')
def get_available_tts_models():
    """Get available TTS models with memory optimization"""
    try:
        monitor_memory_usage()
        
        tts_models = []
        tts_model_dir = Path("TTS-MODEL")
        
        if tts_model_dir.exists():
            for model_dir in tts_model_dir.iterdir():
                if model_dir.is_dir():
                    config_file = model_dir / "config.json"
                    model_info_file = model_dir / "model_info.json"
                    
                    model_info = {
                        'name': model_dir.name,
                        'path': str(model_dir),
                        'has_config': config_file.exists(),
                        'has_model_info': model_info_file.exists(),
                        'has_pth_model': False,
                        'pth_files': []
                    }
                    
                    # Check for .pth files
                    pth_files = list(model_dir.glob("*.pth"))
                    if pth_files:
                        model_info['has_pth_model'] = True
                        model_info['pth_files'] = [f.name for f in pth_files]
                    
                    # Load model info if available
                    if model_info_file.exists():
                        try:
                            with open(model_info_file, 'r', encoding='utf-8') as f:
                                info_data = json.load(f)
                                model_info.update(info_data)
                        except Exception as e:
                            print(f"⚠️ Error loading model info for {model_dir.name}: {e}")
                    
                    tts_models.append(model_info)
        
        return jsonify(tts_models)
        
    except Exception as e:
        print(f"❌ Error getting TTS models: {str(e)}")
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

@app.route('/api/languages/supported')
def get_supported_languages():
    """Get supported languages"""
    return jsonify(SUPPORTED_LANGUAGES)

@app.route('/api/voice_modes/supported')
def get_supported_voice_modes():
    """Get supported voice modes"""
    return jsonify(VOICE_MODES)

@app.route('/api/video_speed_options/supported')
def get_supported_video_speed_options():
    """Get supported video speed options"""
    return jsonify(VIDEO_SPEED_OPTIONS)

@app.route('/api/system/status')
def system_status():
    """Get system status with memory monitoring"""
    try:
        monitor_memory_usage()
        
        # CPU and Memory info
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Queue status
        queue_status = job_queue.get_queue_status()
        
        # Task count
        with tasks_data_lock:
            active_tasks = len(tasks_data)
        
        # เพิ่ม system health indicators
        import torch
        gpu_available = torch.cuda.is_available()
        gpu_memory = None
        if gpu_available:
            gpu_memory = torch.cuda.get_device_properties(0).total_memory
        
        # System health score (0-100)
        health_score = 100
        if memory.percent > 90:
            health_score -= 30
        elif memory.percent > 85:
            health_score -= 20
        elif memory.percent > 75:
            health_score -= 10
            
        if cpu_percent > 90:
            health_score -= 20
        elif cpu_percent > 80:
            health_score -= 10
            
        if disk.percent > 90:
            health_score -= 20
        elif disk.percent > 85:
            health_score -= 10
        
        return jsonify({
            'cpu_percent': cpu_percent,
            'memory_total': memory.total,
            'memory_available': memory.available,
            'memory_percent': memory.percent,
            'disk_total': disk.total,
            'disk_free': disk.free,
            'disk_percent': disk.percent,
            'queue_status': queue_status,
            'active_tasks': active_tasks,
            'gpu_available': gpu_available,
            'gpu_memory': gpu_memory,
            'health_score': max(0, health_score),
            'system_status': 'healthy' if health_score > 70 else 'warning' if health_score > 50 else 'critical'
        })
        
    except Exception as e:
        print(f"❌ Error getting system status: {str(e)}")
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/active')
def get_active_jobs():
    """Get detailed information about active jobs"""
    try:
        queue_status = job_queue.get_queue_status()
        return jsonify({
            'active_jobs': queue_status.get('active_jobs_info', []),
            'total_active': queue_status.get('active_jobs', 0),
            'queue_size': queue_status.get('queue_size', 0)
        })
        
    except Exception as e:
        print(f"❌ Error getting active jobs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop/<task_id>', methods=['POST'])
def stop_processing(task_id):
    """Stop processing for a specific task"""
    try:
        # Check if task exists in job queue
        if job_queue.stop_job(task_id):
            # Clean up task data
            cleanup_task_data(task_id)
            
            return jsonify({
                'success': True,
                'message': f'หยุดการทำงานสำหรับ task {task_id} สำเร็จ'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'ไม่พบ task {task_id} หรือไม่สามารถหยุดได้'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'เกิดข้อผิดพลาดในการหยุดการทำงาน: {str(e)}'
        })

@app.route('/api/stop/all', methods=['POST'])
def stop_all_processing():
    """Stop all active processing tasks"""
    try:
        # Stop all jobs in queue
        stopped_count = job_queue.stop_all_jobs()
        
        # Clean up all task data
        with tasks_data_lock:
            task_ids = list(tasks_data.keys())
        
        for task_id in task_ids:
            cleanup_task_data(task_id)
        
        return jsonify({
            'success': True,
            'message': f'หยุดการทำงานทั้งหมด {stopped_count} jobs สำเร็จ',
            'stopped_count': stopped_count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'เกิดข้อผิดพลาดในการหยุดการทำงานทั้งหมด: {str(e)}'
        })

@app.route('/api/models/download/status')
def get_model_download_status():
    """Get model download status with memory optimization"""
    try:
        monitor_memory_usage()
        
        from services import ModelDownloader
        downloader = ModelDownloader()
        
        return jsonify({
            'available': downloader.get_available_models(),
            'missing': downloader.get_missing_models()
        })
        
    except Exception as e:
        print(f"❌ Error getting model download status: {str(e)}")
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

@app.route('/api/models/download/<model_name>', methods=['POST'])
def download_model(model_name):
    """Download specific model with memory optimization"""
    try:
        monitor_memory_usage()
        
        from services import ModelDownloader
        downloader = ModelDownloader()
        
        if model_name not in downloader.download_paths:
            return jsonify({
                'error': f'Model {model_name} not in download list'
            }), 400
        
        if downloader.is_model_available(model_name):
            return jsonify({
                'message': f'Model {model_name} already available'
            })
        
        success = downloader.download_model(model_name)
        
        if success:
            return jsonify({
                'message': f'Model {model_name} downloaded successfully'
            })
        else:
            return jsonify({
                'error': f'Failed to download model {model_name}'
            }), 500
        
    except Exception as e:
        print(f"❌ Error downloading model: {str(e)}")
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

@app.route('/api/models/download/all', methods=['POST'])
def download_all_missing_models():
    """Download all missing models with memory optimization"""
    try:
        monitor_memory_usage()
        
        from services import ModelDownloader
        downloader = ModelDownloader()
        
        missing_models = downloader.get_missing_models()
        results = {}
        
        for model_name in missing_models:
            try:
                success = downloader.download_model(model_name)
                results[model_name] = 'success' if success else 'failed'
            except Exception as e:
                results[model_name] = f'error: {str(e)}'
        
        return jsonify({
            'message': 'Model download completed',
            'results': results
        })
        
    except Exception as e:
        print(f"❌ Error downloading all models: {str(e)}")
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

@app.route('/api/translate/test', methods=['POST'])
def translate_test():
    """Test translation with memory optimization"""
    try:
        monitor_memory_usage()
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        text = data.get('text', '')
        source_lang = data.get('source_lang', 'auto')
        target_lang = data.get('target_lang', 'th')
        model_name = data.get('model', 'nllb-200')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        translation_service = TranslationService()
        result = translation_service.translate(text, source_lang, target_lang, model_name)
        
        return jsonify({
            'original_text': text,
            'translated_text': result.get('translation', ''),
            'source_lang': source_lang,
            'target_lang': target_lang,
            'model': model_name
        })
        
    except Exception as e:
        print(f"❌ Error in translation test: {str(e)}")
        cleanup_memory()
        return jsonify({'error': str(e)}), 500

# ===== CLEANUP AND SHUTDOWN =====
@app.teardown_appcontext
def cleanup_context(exception=None):
    """Cleanup after each request"""
    cleanup_memory()

def cleanup_on_shutdown():
    """Cleanup on application shutdown"""
    try:
        print("🧹 Cleaning up on shutdown...")
        cleanup_memory()
        
        # Stop job queue
        if job_queue:
            job_queue.stop()
        
        # Clear task data
        with tasks_data_lock:
            tasks_data.clear()
        
        print("✅ Cleanup completed")
    except Exception as e:
        print(f"⚠️ Error during shutdown cleanup: {e}")

# Register shutdown handler
import atexit
atexit.register(cleanup_on_shutdown)

if __name__ == '__main__':
    print("🚀 Starting Video Translator Application (Optimized)")
    print("🧹 Memory optimization enabled")
    print("📊 Memory monitoring enabled")
    print("🔒 Thread safety enabled")
    
    # Initial memory cleanup
    cleanup_memory()
    
    # Start Flask app
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=False,  # Disable debug mode for production
        threaded=True,
        use_reloader=False  # Disable reloader to prevent memory issues
    ) 