"""
Video Translator Application - Main Entry Point
แอปพลิเคชันแปลวิดีโอ - จุดเริ่มต้นหลัก
"""

import os
import json
import uuid
import re
import subprocess
import tempfile
import warnings
import threading
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

# Global variables
current_device = 'auto'

# Initialize job queue
job_queue = JobQueue(MAX_CONCURRENT_JOBS)

# Task storage for step-by-step processing
tasks_data = {}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Flask Routes
@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', video_speed_options=VIDEO_SPEED_OPTIONS)

@app.route('/test')
def test_form():
    """Test form page"""
    return render_template('test_form_submit.html')

@app.route('/debug')
def debug_form():
    """Debug form page"""
    return render_template('debug_form.html')

@app.route('/simple')
def simple_test():
    """Simple test page"""
    return render_template('simple_test.html')

# ===== YOUTUBE URL (REAL-TIME) MODE =====
@app.route('/api/youtube/realtime', methods=['POST'])
def youtube_realtime():
    """Process YouTube URL in real-time mode"""
    try:
        print("🎬 YouTube real-time processing request received")
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
            'translation_mode': data.get('translation_mode', 'separate_translation'),
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
        return jsonify({'error': str(e)}), 500

# ===== FILE UPLOAD MODE =====
@app.route('/api/upload/auto', methods=['POST'])
def file_upload_auto():
    """Process uploaded file in auto mode"""
    try:
        print("📁 File upload auto processing request received")
        
        if 'video' not in request.files:
            print("❌ No video file provided")
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
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
            'translation_mode': request.form.get('translation_mode', 'separate_translation'),
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
            'message': 'File auto processing added to queue',
            'queue_position': job_queue.queue.qsize()
        })
        
    except Exception as e:
        print(f"❌ Error in file upload auto processing: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload/step', methods=['POST'])
def file_upload_step():
    """Initialize step-by-step processing for uploaded file"""
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Save uploaded file
        filename = secure_filename(file.filename or 'video')
        file_path = UPLOADS_DIR / f"{task_id}_{filename}"
        file.save(str(file_path))
        
        # Initialize step-by-step data
        tasks_data[task_id] = {
            'mode': 'file_step',
            'video_input': str(file_path),
            'source_lang': request.form.get('source_lang', 'auto'),
            'target_lang': request.form.get('target_lang', 'th'),
            'stt_model': request.form.get('stt_model', 'base'),
            'translation_mode': request.form.get('translation_mode', 'separate_translation'),
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
            # Ultimate Vocal Remover options - บังคับให้เปิดใช้งาน
            'enable_vocal_removal': True,  # บังคับให้เปิดใช้งาน
            'enable_instrumental_mixing': True,  # บังคับให้เปิดใช้งาน
            'sync_original_audio': request.form.get('sync_original_audio', 'false').lower() == 'true',
            # Processing steps control
            'enable_step_2': request.form.get('enable_step_2', 'true').lower() == 'true',
            'enable_step_3': request.form.get('enable_step_3', 'true').lower() == 'true',
            'enable_step_4': request.form.get('enable_step_4', 'true').lower() == 'true',
            'enable_step_5': request.form.get('enable_step_5', 'true').lower() == 'true',
            'enable_step_6': request.form.get('enable_step_6', 'true').lower() == 'true',
            'enable_step_7': request.form.get('enable_step_7', 'true').lower() == 'true',
            'current_step': 2,
            'steps': {
                1: {'name': 'Upload', 'status': 'completed', 'text': ''},
                2: {'name': 'Vocal Removal', 'status': 'pending', 'text': ''},
                3: {'name': 'STT', 'status': 'pending', 'text': ''},
                4: {'name': 'Translation', 'status': 'pending', 'text': ''},
                5: {'name': 'TTS', 'status': 'pending', 'audio_path': ''},
                6: {'name': 'Merge', 'status': 'pending', 'output_path': ''}
            }
        }
        
        return jsonify({
            'task_id': task_id,
            'message': 'Step-by-step processing initialized',
            'current_step': 2,
            'total_steps': 6
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== STEP-BY-STEP PROCESSING =====
@app.route('/api/step/<task_id>/<int:step>', methods=['POST'])
def process_step(task_id, step):
    """Process a specific step"""
    try:
        if task_id not in tasks_data:
            return jsonify({'error': 'Task not found'}), 404
        
        task_data = tasks_data[task_id]
        
        if step < 2 or step > 6:
            return jsonify({'error': 'Invalid step number'}), 400
        
        # Process the step
        if step == 2:  # Vocal Removal
            result = process_vocal_removal_step(task_id, task_data)
        elif step == 3:  # STT
            result = process_stt_step(task_id, task_data)
        elif step == 4:  # Translation
            result = process_translation_step(task_id, task_data)
        elif step == 5:  # TTS
            result = process_tts_step(task_id, task_data)
        elif step == 6:  # Merge
            result = process_merge_step(task_id, task_data)
        else:
            return jsonify({'error': 'Invalid step number'}), 400
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error in process_step: {str(e)}")
        return jsonify({'error': str(e)}), 500

def process_vocal_removal_step(task_id, task_data):
    """Process Vocal Removal step"""
    try:
        # Initialize services
        video_processor = VideoProcessor()

        # Extract audio with vocal removal enabled
        print(f"🎵 เริ่มต้นการแยกเสียงด้วย Ultimate Vocal Remover...")
        audio_result = video_processor.extract_audio(task_data['video_input'], task_id, enable_vocal_removal=True)
        
        # Check if vocal removal was successful
        if isinstance(audio_result, dict) and 'vocals' in audio_result:
            print(f"✅ แยกเสียงสำเร็จ: เสียงพูดและดนตรีแยกออกจากกัน")
            # Store vocal separation result for later use
            tasks_data[task_id]['vocal_separation'] = audio_result
            vocal_removal_applied = True
        else:
            print(f"⚠️  การแยกเสียงไม่สำเร็จ ใช้เสียงรวม")
            vocal_removal_applied = False

        # Update task data
        tasks_data[task_id]['steps'][2]['status'] = 'completed'
        tasks_data[task_id]['current_step'] = 3

        return {
            'task_id': task_id,
            'step': 2,
            'status': 'completed',
            'next_step': 3,
            'vocal_removal_applied': vocal_removal_applied
        }

    except Exception as e:
        tasks_data[task_id]['steps'][2]['status'] = 'error'
        return {'error': str(e)}

def process_stt_step(task_id, task_data):
    """Process STT step"""
    try:
        # Initialize services
        video_processor = VideoProcessor()

        # Get audio path from vocal removal or extract audio
        if 'vocal_separation' in tasks_data[task_id]:
            audio_result = tasks_data[task_id]['vocal_separation']
            if 'vocals' in audio_result:
                audio_path = audio_result['vocals']
                print(f"✅ ใช้เสียงที่แยกแล้วสำหรับ STT: {audio_path}")
            else:
                audio_path = audio_result
        else:
            # Extract audio without vocal removal (fallback)
            print(f"⚠️  ไม่มีผลการแยกเสียง ใช้เสียงรวม")
            audio_path = video_processor.extract_audio(task_data['video_input'], task_id, enable_vocal_removal=False)
        
        # Check translation mode
        translation_mode = task_data.get('translation_mode', 'separate_translation')
        
        if translation_mode == 'whisper_translate':
            # Whisper translate mode - STT + translate in one step
            print(f"🔤 ใช้โหมด Whisper แปลโดยตรง")
            translated_text = video_processor.transcribe_audio(
                audio_path,
                task_data.get('stt_model', 'base'),
                task_data.get('source_lang', 'auto'),
                task_id,
                task='translate',  # Use translate task
                target_lang=task_data.get('target_lang', 'th')
            )
            
            # Store both original and translated text
            tasks_data[task_id]['steps'][3]['status'] = 'completed'
            tasks_data[task_id]['steps'][3]['text'] = translated_text  # This is the translated text
            tasks_data[task_id]['steps'][4]['status'] = 'completed'  # Skip translation step
            tasks_data[task_id]['steps'][4]['text'] = translated_text  # Same text for translation step
            tasks_data[task_id]['current_step'] = 5  # Skip to TTS step
            
            return {
                'task_id': task_id,
                'step': 3,
                'status': 'completed',
                'text': translated_text,
                'translation_mode': 'whisper_translate',
                'next_step': 5  # Skip translation step
            }
        else:
            # Separate translation mode - STT only
            print(f"🔤 ใช้โหมดแยกการแปล")
            stt_text = video_processor.transcribe_audio(
                audio_path,
                task_data.get('stt_model', 'base'),
                task_data.get('source_lang', 'auto'),
                task_id,
                task='transcribe'  # Use transcribe task only
            )
            if not stt_text:
                stt_text = ""

            # Update task data
            tasks_data[task_id]['steps'][3]['status'] = 'completed'
            tasks_data[task_id]['steps'][3]['text'] = stt_text
            tasks_data[task_id]['current_step'] = 4

            return {
                'task_id': task_id,
                'step': 3,
                'status': 'completed',
                'text': stt_text,
                'translation_mode': 'separate_translation',
                'next_step': 4
            }

    except Exception as e:
        tasks_data[task_id]['steps'][3]['status'] = 'error'
        return {'error': str(e)}

def process_translation_step(task_id, task_data):
    """Process Translation step"""
    try:
        # Check if we're in whisper translate mode
        translation_mode = task_data.get('translation_mode', 'separate_translation')
        
        if translation_mode == 'whisper_translate':
            # Translation already done in STT step, just mark as completed
            print(f"⏭️ ข้ามขั้นตอนการแปล (ใช้ Whisper translate)")
            return {
                'task_id': task_id,
                'step': 4,
                'status': 'completed',
                'text': tasks_data[task_id]['steps'][4]['text'],
                'next_step': 5,
                'message': 'Translation already completed in STT step'
            }
        
        # Get STT text from previous step
        stt_text = tasks_data[task_id]['steps'][3]['text']
        
        if not stt_text:
            return {'error': 'No STT text available. Please complete step 3 first.'}
        
        # Initialize translation service
        translation_service = TranslationService()
        
        # Perform translation
        translated_text = translation_service.translate(
            stt_text, 
            task_data['source_lang'], 
            task_data['target_lang'],
            task_data.get('translation_model', 'nllb-200')
        )
        
        # Update task data
        tasks_data[task_id]['steps'][4]['status'] = 'completed'
        tasks_data[task_id]['steps'][4]['text'] = translated_text
        tasks_data[task_id]['current_step'] = 5
        
        return {
            'task_id': task_id,
            'step': 4,
            'status': 'completed',
            'text': translated_text,
            'next_step': 5
        }
        
    except Exception as e:
        tasks_data[task_id]['steps'][4]['status'] = 'error'
        return {'error': str(e)}

def process_tts_step(task_id, task_data):
    """Process TTS step"""
    try:
        # Get translated text from previous step
        translated_text = tasks_data[task_id]['steps'][4]['text']
        
        if not translated_text:
            return {'error': 'No translated text available. Please complete step 4 first.'}
        
        # Get TTS settings from request (handle both JSON and form data)
        try:
            request_data = request.get_json() or {}
        except:
            request_data = {}
        tts_model = request_data.get('tts_model', task_data.get('tts_model', 'gtts'))
        voice_mode = request_data.get('voice_mode', task_data.get('voice_mode', 'female'))
        custom_coqui_model = request_data.get('custom_coqui_model', task_data.get('custom_coqui_model', ''))
        
        # Initialize TTS service
        tts_service = TTSService()
        
        # Generate audio
        audio_path = tts_service.synthesize_speech(
            translated_text,
            task_data['target_lang'],
            tts_model,
            task_id,
            voice_mode,
            custom_coqui_model
        )
        
        if not audio_path or not os.path.exists(audio_path):
            return {'error': 'Failed to generate TTS audio'}
        
        # Create audio URL for preview
        audio_url = f'/api/audio/{task_id}/tts'
        
        # Get audio file info
        audio_info = f"โมเดล: {tts_model}, เสียง: {voice_mode}"
        if custom_coqui_model:
            audio_info += f", Custom Model: {custom_coqui_model}"
        
        # Update task data
        tasks_data[task_id]['steps'][5]['status'] = 'completed'
        tasks_data[task_id]['steps'][5]['audio_path'] = audio_path
        tasks_data[task_id]['current_step'] = 6
        
        return {
            'task_id': task_id,
            'step': 5,
            'status': 'completed',
            'audio_path': audio_path,
            'audio_url': audio_url,
            'audio_info': audio_info,
            'next_step': 6
        }
        
    except Exception as e:
        tasks_data[task_id]['steps'][3]['status'] = 'error'
        return {'error': str(e)}

def process_merge_step(task_id, task_data):
    """Process Merge step with instrumental mixing"""
    try:
        # Get audio path from previous step
        audio_path = tasks_data[task_id]['steps'][5]['audio_path']
        
        if not audio_path:
            return {'error': 'No audio available. Please complete step 5 first.'}
        
        # Initialize video processor
        video_processor = VideoProcessor()
        
        # Check if we have vocal separation result
        instrumental_path = None
        if 'vocal_separation' in tasks_data[task_id]:
            vocal_sep = tasks_data[task_id]['vocal_separation']
            if 'instrumental' in vocal_sep:
                instrumental_path = vocal_sep['instrumental']
                print(f"🎵 ใช้ instrumental จาก vocal separation: {instrumental_path}")
        
        # Merge video with audio and instrumental
        output_path = video_processor.merge_audio_video(
            task_data['video_input'],
            audio_path,
            task_id,
            task_data['video_speed'],
            instrumental_path=instrumental_path,
            sync_original_audio=task_data.get('sync_original_audio', False)
        )
        
        # Update task data
        tasks_data[task_id]['steps'][6]['status'] = 'completed'
        tasks_data[task_id]['steps'][6]['output_path'] = output_path
        tasks_data[task_id]['current_step'] = 6
        
        return {
            'task_id': task_id,
            'step': 6,
            'status': 'completed',
            'output_path': output_path,
            'message': 'Video translation completed with instrumental mixing!',
            'instrumental_used': instrumental_path is not None
        }
        
    except Exception as e:
        tasks_data[task_id]['steps'][6]['status'] = 'error'
        return {'error': str(e)}

# ===== TEXT EDITING =====
@app.route('/api/text/<task_id>/<text_type>', methods=['GET'])
def get_text(task_id, text_type):
    """Get text for editing"""
    try:
        if task_id not in tasks_data:
            return jsonify({'error': 'Task not found'}), 404
        
        task_data = tasks_data[task_id]
        
        if text_type == 'stt':
            text = task_data['steps'][3]['text']
        elif text_type == 'translation':
            text = task_data['steps'][4]['text']
        elif text_type == 'original':
            text = task_data['steps'][3]['text']  # STT text as original
        else:
            return jsonify({'error': 'Invalid text type'}), 400
        
        return jsonify({
            'task_id': task_id,
            'text_type': text_type,
            'text': text
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/text/<task_id>/<text_type>', methods=['PUT'])
def update_text(task_id, text_type):
    """Update text after editing"""
    try:
        if task_id not in tasks_data:
            return jsonify({'error': 'Task not found'}), 404
        
        data = request.get_json()
        new_text = data.get('text', '')
        
        if text_type == 'stt':
            tasks_data[task_id]['steps'][3]['text'] = new_text
        elif text_type == 'translation':
            tasks_data[task_id]['steps'][4]['text'] = new_text
        elif text_type == 'original':
            tasks_data[task_id]['steps'][3]['text'] = new_text
        else:
            return jsonify({'error': 'Invalid text type'}), 400
        
        return jsonify({
            'task_id': task_id,
            'text_type': text_type,
            'message': 'Text updated successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== STATUS AND DOWNLOAD =====
@app.route('/api/status/<task_id>')
def get_status(task_id):
    """Get task status with enhanced real-time information"""
    try:
        print(f"📊 Status request for task ID: {task_id}")
        
        # Check if it's a step-by-step task
        if task_id in tasks_data:
            task_data = tasks_data[task_id]
            print(f"✅ Found step-by-step task: {task_data['mode']}")
            return jsonify({
                'task_id': task_id,
                'mode': task_data['mode'],
                'current_step': task_data['current_step'],
                'steps': task_data['steps']
            })
        
        # Check if it's a queue job
        job = job_queue.get_job_status(task_id)
        if job:
            print(f"✅ Found queue job: {job['status']} - {job['progress']}%")
            
            # Calculate elapsed time
            elapsed_time = 0
            if job.get('started_at'):
                elapsed_time = int((datetime.now() - job['started_at']).total_seconds())
            
            # Estimate remaining time based on progress
            estimated_time_remaining = None
            if job['progress'] > 0:
                total_estimated_time = (elapsed_time / job['progress']) * 100
                estimated_time_remaining = max(0, int(total_estimated_time - elapsed_time))
            
            return jsonify({
                'task_id': task_id,
                'status': job['status'],
                'progress': job['progress'],
                'message': job['message'],
                'output_path': job.get('output_path'),
                'elapsed_time': elapsed_time,
                'estimated_time_remaining': estimated_time_remaining,
                'current_step': job.get('current_step', 'ไม่ทราบ'),
                'total_steps': job.get('total_steps', 7),
                'step_progress': job.get('step_progress', 0)
            })
        
        print(f"❌ Task not found: {task_id}")
        return jsonify({'error': 'Task not found'}), 404
        
    except Exception as e:
        print(f"❌ Error getting status for task {task_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio/<task_id>/tts')
def serve_tts_audio(task_id):
    """Serve TTS audio file for preview"""
    try:
        if task_id not in tasks_data:
            return jsonify({'error': 'Task not found'}), 404
        
        task_data = tasks_data[task_id]
        audio_path = task_data['steps'][5].get('audio_path')
        
        if not audio_path or not os.path.exists(audio_path):
            return jsonify({'error': 'Audio file not found'}), 404
        
        return send_file(audio_path, mimetype='audio/wav')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<task_id>')
def download_video(task_id):
    """Download completed video"""
    try:
        # Check step-by-step tasks first
        if task_id in tasks_data:
            task_data = tasks_data[task_id]
            output_path = task_data['steps'][6]['output_path']
            
            if output_path and os.path.exists(output_path):
                return send_file(output_path, as_attachment=True)
            else:
                return jsonify({'error': 'Video not ready for download'}), 404
        
        # Check queue jobs
        job = job_queue.get_job_status(task_id)
        if job and job.get('output_path'):
            if os.path.exists(job['output_path']):
                return send_file(job['output_path'], as_attachment=True)
        
        return jsonify({'error': 'Video not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== SYSTEM ENDPOINTS =====
@app.route('/api/models/list')
def list_models():
    """List available models"""
    return jsonify({
        'stt_models': STT_MODELS,
        'translation_models': TRANSLATION_MODELS,
        'tts_models': TTS_MODELS,
        'model_categories': {
            'openai_whisper': {
                'name': 'OpenAI Whisper Models',
                'description': 'Standard OpenAI Whisper models for speech recognition',
                'models': ['base', 'small', 'medium', 'large']
            },
            'thonburian_whisper': {
                'name': 'Thonburian Whisper Models',
                'description': 'Thai-optimized Whisper models with better Thai language support',
                'models': ['thonburian-base', 'thonburian-small', 'thonburian-medium', 'thonburian-medium-timestamps', 'thonburian-large']
            }
        }
    })

@app.route('/api/tts/models/available')
def get_available_tts_models():
    """Get available TTS models from TTS-MODEL directory"""
    try:
        tts_models_dir = Path('TTS-MODEL')
        available_models = []
        
        if tts_models_dir.exists():
            for model_dir in tts_models_dir.iterdir():
                if model_dir.is_dir():
                    config_file = model_dir / 'config.json'
                    model_info_file = model_dir / 'model_info.json'
                    
                    model_info = {}
                    model_info['name'] = model_dir.name
                    model_info['path'] = f'TTS-MODEL/{model_dir.name}'
                    
                    # Read config.json if exists
                    if config_file.exists():
                        try:
                            with open(config_file, 'r', encoding='utf-8') as f:
                                config_data = json.load(f)
                                model_info.update({
                                    'model_name': config_data.get('model_name', model_dir.name),
                                    'language': config_data.get('language', 'unknown'),
                                    'voice_gender': config_data.get('voice_gender', 'unknown'),
                                    'model_version': config_data.get('model_version', '1.0'),
                                    'description': config_data.get('description', ''),
                                    'quality_score': config_data.get('performance', {}).get('quality_score', 0)
                                })
                        except Exception as e:
                            print(f"Error reading config for {model_dir.name}: {e}")
                    
                    # Check for .pth files
                    pth_files = list(model_dir.glob('*.pth'))
                    if pth_files:
                        model_info['pth_files'] = [str(pth) for pth in pth_files]
                        model_info['has_pth_model'] = True
                        print(f"Found .pth files in {model_dir.name}: {[pth.name for pth in pth_files]}")
                    else:
                        model_info['has_pth_model'] = False
                    
                    # Read model_info.json if exists
                    if model_info_file.exists():
                        try:
                            with open(model_info_file, 'r', encoding='utf-8') as f:
                                info_data = json.load(f)
                                model_info.update({
                                    'model_name': info_data.get('model_name', model_info.get('model_name', model_dir.name)),
                                    'language': info_data.get('language', model_info.get('language', 'unknown')),
                                    'voice_gender': info_data.get('voice_gender', model_info.get('voice_gender', 'unknown')),
                                    'model_version': info_data.get('model_version', model_info.get('model_version', '1.0')),
                                    'description': info_data.get('description', model_info.get('description', ''))
                                })
                        except Exception as e:
                            print(f"Error reading model_info for {model_dir.name}: {e}")
                    
                    available_models.append(model_info)
        
        return jsonify({
            'success': True,
            'models': available_models,
            'total_count': len(available_models)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'models': [],
            'total_count': 0
        }), 500

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
    """Get system status"""
    try:
        import psutil
        
        # CPU and Memory info
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Disk space
        disk = psutil.disk_usage('/')
        
        # Queue status
        queue_status = job_queue.get_queue_status()
        
        return jsonify({
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': (disk.used / disk.total) * 100
            },
            'queue': queue_status,
            'active_tasks': len(tasks_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/models/download/status')
def get_model_download_status():
    """Get status of all models (available/missing)"""
    try:
        from services import ModelDownloader
        downloader = ModelDownloader()
        
        available_models = downloader.get_available_models()
        missing_models = downloader.get_missing_models()
        
        return jsonify({
            'success': True,
            'available_models': available_models,
            'missing_models': missing_models,
            'total_available': len(available_models),
            'total_missing': len(missing_models)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/models/download/<model_name>', methods=['POST'])
def download_model(model_name):
    """Download a specific model"""
    try:
        from services import ModelDownloader
        downloader = ModelDownloader()
        
        if model_name not in downloader.download_paths:
            return jsonify({
                'success': False,
                'error': f'Model {model_name} not in download list'
            }), 400
        
        if downloader.is_model_available(model_name):
            return jsonify({
                'success': True,
                'message': f'Model {model_name} already available',
                'status': 'already_available'
            })
        
        # Start download
        success = downloader.download_model(model_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Model {model_name} downloaded successfully',
                'status': 'downloaded'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to download model {model_name}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/models/download/all', methods=['POST'])
def download_all_missing_models():
    """Download all missing models"""
    try:
        from services import ModelDownloader
        downloader = ModelDownloader()
        
        missing_models = downloader.get_missing_models()
        
        if not missing_models:
            return jsonify({
                'success': True,
                'message': 'All models already available',
                'downloaded_count': 0
            })
        
        downloaded_count = 0
        failed_models = []
        
        for model_name in missing_models:
            try:
                if downloader.download_model(model_name):
                    downloaded_count += 1
                else:
                    failed_models.append(model_name)
            except Exception as e:
                failed_models.append(f"{model_name} (error: {str(e)})")
        
        return jsonify({
            'success': True,
            'message': f'Downloaded {downloaded_count} models',
            'downloaded_count': downloaded_count,
            'failed_models': failed_models,
            'total_missing': len(missing_models)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/translate/test', methods=['POST'])
def translate_test():
    """API ทดสอบแปลข้อความทันทีด้วย NLLB-200-3.3B"""
    try:
        print("🔤 Translation test request received")
        
        data = request.get_json()
        if not data:
            print("❌ No data provided")
            return jsonify({'error': 'กรุณาส่งข้อมูล JSON'}), 400
        
        text = data.get('text', '').strip()
        source_lang = data.get('source_lang', 'en')
        target_lang = data.get('target_lang', 'th')
        
        if not text:
            print("❌ No text provided")
            return jsonify({'error': 'กรุณากรอกข้อความ'}), 400
        
        print(f"📝 Translating text: {text[:50]}...")
        print(f"🌐 From {source_lang} to {target_lang}")
        
        # Initialize translation service
        translation_service = TranslationService()
        
        # Perform translation
        result = translation_service.translate(text, source_lang, target_lang, 'nllb-200')
        
        if not result:
            print("❌ Translation failed - no result")
            return jsonify({'error': 'การแปลล้มเหลว'}), 500
        
        # Handle both string and dictionary results
        if isinstance(result, str):
            translated_text = result
        elif isinstance(result, dict) and 'translation' in result:
            translated_text = result.get('translation', '')
        else:
            print(f"❌ Unexpected result format: {type(result)}")
            return jsonify({'error': 'รูปแบบผลลัพธ์ไม่ถูกต้อง'}), 500
        
        if not translated_text.strip():
            print("❌ Translation result is empty")
            return jsonify({'error': 'ผลการแปลเป็นค่าว่าง'}), 500
        
        print(f"✅ Translation successful: {len(translated_text)} characters")
        
        return jsonify({
            'success': True,
            'original_text': text,
            'translated_text': translated_text,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'result': result
        })
        
    except Exception as e:
        print(f"❌ Error in translation test: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'เกิดข้อผิดพลาดในการแปล: {str(e)}'
        }), 500



if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5556) 