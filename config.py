"""
Configuration file for Video Translator Application
ไฟล์การตั้งค่าสำหรับแอปพลิเคชันแปลวิดีโอ
"""

import os
from pathlib import Path
from datetime import datetime

# Flask Configuration
FLASK_SECRET_KEY = 'your-secret-key-here'
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB

# File Extensions
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm'}

# Directories
UPLOADS_DIR = Path("uploads")
OUTPUTS_DIR = Path("outputs")
TEMP_DIR = Path("temp")
LOGS_DIR = Path("logs")
TEXTS_DIR = Path("texts")
PREVIEWS_DIR = Path("previews")
AUDIOS_DIR = Path("audios")

# Create directories if they don't exist
for directory in [UPLOADS_DIR, OUTPUTS_DIR, TEMP_DIR, LOGS_DIR, TEXTS_DIR, PREVIEWS_DIR, AUDIOS_DIR]:
    directory.mkdir(exist_ok=True)

# Queue Configuration
MAX_CONCURRENT_JOBS = 3

# Progress Bar Configuration
PROGRESS_UPDATE_INTERVAL = 1
PROGRESS_BAR_COLOR = "#28a745"
PROGRESS_BAR_HEIGHT = "20px"

# Language Configuration
SUPPORTED_LANGUAGES = {
    'auto': 'อัตโนมัติ',
    'en': 'English',
    'th': 'ไทย',
    'ja': '日本語',
    'ko': '한국어',
    'zh': '中文',
    'vi': 'Tiếng Việt',
    'hi': 'हिन्दी',
    'es': 'Español',
    'fr': 'Français',
    'de': 'Deutsch',
    'it': 'Italiano',
    'pt': 'Português',
    'ru': 'Русский',
    'ar': 'العربية',
    'tr': 'Türkçe',
    'pl': 'Polski',
    'nl': 'Nederlands',
    'sv': 'Svenska',
    'da': 'Dansk',
    'no': 'Norsk',
    'fi': 'Suomi',
    'hu': 'Magyar',
    'cs': 'Čeština',
    'sk': 'Slovenčina',
    'ro': 'Română',
    'bg': 'Български',
    'hr': 'Hrvatski',
    'sl': 'Slovenščina',
    'et': 'Eesti',
    'lv': 'Latviešu',
    'lt': 'Lietuvių',
    'id': 'Bahasa Indonesia',
    'ms': 'Bahasa Melayu',
    'tl': 'Tagalog',
    'bn': 'বাংলা',
    'ur': 'اردو',
    'fa': 'فارسی',
    'he': 'עברית',
    'el': 'Ελληνικά',
    'uk': 'Українська',
    'be': 'Беларуская',
    'mk': 'Македонски',
    'sr': 'Српски',
    'bs': 'Bosanski',
    'me': 'Crnogorski',
    'sq': 'Shqip',
    'lo': 'ລາວ'
}

# Voice Modes
VOICE_MODES = {
    'female': 'ผู้หญิง',
    'male': 'ผู้ชาย',
    'child': 'เด็ก',
    'elderly': 'คนแก่',
    'robot': 'หุ่นยนต์',
    'whisper': 'กระซิบ',
    'shout': 'ตะโกน',
    'sing': 'ร้องเพลง'
}

# Model Configuration
STT_MODELS = {
    # OpenAI Whisper Models (แนะนำ)
    'base': 'openai/whisper-base',
    'small': 'openai/whisper-small',
    'medium': 'openai/whisper-medium',
    'large': 'openai/whisper-large',
    # Biodatlab Thai Whisper Models (สำรอง)
    'biodatlab-large-v3': 'biodatlab/whisper-th-large-v3-combined',
    'biodatlab-medium-timestamp': 'biodatlab/whisper-th-medium-timestamp',
    'biodatlab-medium': 'biodatlab/whisper-th-medium-combined'
}

TRANSLATION_MODELS = {
    'nllb-200': 'models/nllb-200-3.3B',
    'nllb-200-distilled': 'facebook/nllb-200-distilled-1.3B',  # fallback distilled model
}

TTS_MODELS = {
    'gtts': 'Google TTS',
    'edge': 'Microsoft Edge TTS'
}

# Video Speed options
VIDEO_SPEED_OPTIONS = {
    '1.0': 'ปกติ (1x)',
    '2.0': 'เร็ว 2 เท่า',
    '4.0': 'เร็ว 4 เท่า'
}

# YouTube Configuration
YOUTUBE_PATTERNS = [
    r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=',
    r'(?:https?://)?(?:www\.)?youtu\.be/',
    r'(?:https?://)?(?:www\.)?youtube\.com/embed/',
    r'(?:https?://)?(?:www\.)?youtube\.com/v/'
]

# Processing Configuration
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
OVERLAP_DURATION = 30
CHUNK_DURATION = 60
# Remove text length limitations for unlimited processing
MAX_TEXT_LENGTH = None  # No limit for unlimited processing
AUTO_GENERATE_PREVIEW = True

# Unlimited Processing Configuration - All modes enabled
UNLIMITED_AUDIO_PROCESSING = True
UNLIMITED_TRANSLATION = True
UNLIMITED_TTS = True
MAX_AUDIO_DURATION = None  # No limit
MAX_TRANSLATION_LENGTH = None  # No limit
MAX_TTS_LENGTH = None  # No limit

# Enhanced Chunking for Unlimited Processing
UNLIMITED_CHUNK_SIZE = 10 * 60  # 10 minutes per chunk for unlimited processing
UNLIMITED_OVERLAP_SIZE = 60  # 1 minute overlap for better continuity
UNLIMITED_MAX_CHUNKS = None  # No limit on number of chunks

# Memory Management for Unlimited Processing
ENABLE_MEMORY_OPTIMIZATION = True
STREAMING_PROCESSING = True
BATCH_SIZE_UNLIMITED = 1  # Process one chunk at a time for memory efficiency

# Force all processing modes to unlimited
FORCE_UNLIMITED_MODE = True
DISABLE_ALL_LIMITS = True

# Enhanced Audio Preprocessing Configuration
ENABLE_AUDIO_PREPROCESSING = True
ENABLE_NOISE_REDUCTION = True
ENABLE_VAD = True
ENABLE_NORMALIZATION = True
ENABLE_BANDPASS_FILTER = True

# Ultimate Vocal Remover Configuration
ENABLE_VOCAL_REMOVAL = True
VOCAL_REMOVAL_QUALITY = 'high'  # 'low', 'medium', 'high'
VOCAL_REMOVAL_MODELS_PATH = 'models/'
ENABLE_INSTRUMENTAL_MIXING = True
INSTRUMENTAL_VOLUME = 0.3  # Volume level for instrumental (0.0-1.0)
TTS_VOLUME = 1.0  # Volume level for TTS audio (0.0-1.0)
SYNC_ORIGINAL_AUDIO = False  # Sync with original audio timing

# Force enable vocal removal for step 2
FORCE_VOCAL_REMOVAL_STEP_2 = True

# Processing Mode Configuration - เปิดใช้งานเฉพาะขั้นตอนที่ 2 และ 6
ENABLE_STEP_2_VOCAL_REMOVAL = True    # ขั้นตอนที่ 2: Vocal Removal (เปิดใช้งาน)
ENABLE_STEP_6_AUDIO_MIXING = True     # ขั้นตอนที่ 6: Audio Mixing (เปิดใช้งาน)
ENABLE_STEP_3_STT = True             # ขั้นตอนที่ 3: STT (เปิดใช้งาน)
ENABLE_STEP_4_TRANSLATION = True     # ขั้นตอนที่ 4: Translation (เปิดใช้งาน)
ENABLE_STEP_5_TTS = True             # ขั้นตอนที่ 5: TTS (เปิดใช้งาน)
ENABLE_STEP_7_VIDEO_MERGE = True      # ขั้นตอนที่ 7: Video Merge (เปิดใช้งาน - จำเป็น)

# Unlimited Processing Configuration - ไร้ขีดจำกัดทุกขั้นตอน
ENABLE_UNLIMITED_PROCESSING = True
ENABLE_UNLIMITED_AUDIO_LENGTH = True
ENABLE_UNLIMITED_VIDEO_SIZE = True
ENABLE_UNLIMITED_CONCURRENT_JOBS = True
ENABLE_UNLIMITED_MEMORY_USAGE = True
ENABLE_UNLIMITED_CPU_USAGE = True
ENABLE_UNLIMITED_GPU_USAGE = True
ENABLE_UNLIMITED_STORAGE = True
ENABLE_UNLIMITED_NETWORK = True
ENABLE_UNLIMITED_API_CALLS = True

# Remove all limits for unlimited processing
MAX_CONTENT_LENGTH = None  # No file size limit
MAX_CONCURRENT_JOBS = 3  # Keep job limit for stability
MAX_AUDIO_DURATION = None  # No audio duration limit
MAX_TRANSLATION_LENGTH = None  # No translation length limit
MAX_TTS_LENGTH = None  # No TTS length limit
MAX_TEXT_LENGTH = None  # No text length limit
MAX_CHUNK_SIZE = None  # No chunk size limit
MAX_OVERLAP_SIZE = None  # No overlap size limit
MAX_CHUNKS = None  # No chunk count limit

# Enhanced Noise Reduction Configuration
ENABLE_AGGRESSIVE_NOISE_REDUCTION = True
ENABLE_MUSIC_REMOVAL = True
ENABLE_SPEECH_ENHANCEMENT = True
ENABLE_ADAPTIVE_FILTERING = True
ENABLE_FINAL_NORMALIZATION = True

# Multiple Noise Reduction Passes
NOISE_REDUCTION_PASSES = 3
STATIONARY_NOISE_REDUCTION_STRENGTH = 0.8
NON_STATIONARY_NOISE_REDUCTION_STRENGTH = 0.6

# Music and Background Noise Removal
MUSIC_REMOVAL_HIGH_PASS_CUTOFF = 80  # Hz
MUSIC_REMOVAL_NOTCH_FREQUENCIES = [50, 60, 100, 120]  # Hz

# Speech Enhancement Configuration
SPEECH_ENHANCEMENT_LOW_FREQ = 80  # Hz
SPEECH_ENHANCEMENT_HIGH_FREQ = 8000  # Hz
SPEECH_ENHANCEMENT_FILTER_ORDER = 8

# Adaptive Filtering Configuration
ADAPTIVE_GAIN_CONTROL_ENABLED = True
ADAPTIVE_GAIN_LOUD_THRESHOLD = 0.1
ADAPTIVE_GAIN_QUIET_THRESHOLD = 0.01
ADAPTIVE_GAIN_LOUD_MULTIPLIER = 0.5
ADAPTIVE_GAIN_QUIET_MULTIPLIER = 2.0

# Dynamic Range Compression
DYNAMIC_RANGE_COMPRESSION_ENABLED = True
DYNAMIC_RANGE_THRESHOLD = 0.3
DYNAMIC_RANGE_RATIO = 4.0

# Final Normalization Configuration
FINAL_NORMALIZATION_PEAK_TARGET = 0.95
FINAL_NORMALIZATION_RMS_TARGET = 0.1

# VAD Configuration
VAD_MODE = 3  # 0-3, higher = more aggressive
VAD_FRAME_DURATION = 30  # ms
VAD_PADDING_DURATION = 300  # ms

# Audio Filter Configuration
BANDPASS_LOW = 200  # Hz
BANDPASS_HIGH = 3000  # Hz
NOISE_REDUCTION_STRENGTH = 0.5  # 0.0-1.0
NORMALIZATION_TARGET = -20  # dB

# Enhanced Whisper Configuration for Noisy Audio
WHISPER_NO_SPEECH_THRESHOLD_NOISY = 0.3  # Lower threshold for noisy audio
WHISPER_LOGPROB_THRESHOLD_NOISY = -1.0   # Lower threshold for noisy audio
WHISPER_COMPRESSION_RATIO_THRESHOLD_NOISY = 2.4  # Higher threshold for noisy audio

# Whisper Configuration
WHISPER_RETURN_TIMESTAMPS = True
WHISPER_NO_SPEECH_THRESHOLD = 0.2
WHISPER_LOGPROB_THRESHOLD = -1.0
WHISPER_COMPRESSION_RATIO_THRESHOLD = 2.4

# Enhanced Whisper Configuration for Long Audio
WHISPER_MAX_LENGTH = 2048
WHISPER_NUM_BEAMS = 5
WHISPER_EARLY_STOPPING = True
WHISPER_TEMPERATURE = 0.0
WHISPER_DO_SAMPLE = False
WHISPER_CONDITION_ON_PREVIOUS_TEXT = False
WHISPER_PROMPT_RESET_ON_TIMESTAMP = False

# Whisper Chunking for Long Audio
WHISPER_CHUNK_DURATION = 30  # seconds per chunk
WHISPER_CHUNK_OVERLAP = 5    # seconds overlap between chunks
WHISPER_MAX_CHUNKS = None     # No limit on chunks

# TTS Sync Configuration
ENABLE_TTS_SYNC = True
TTS_SILENCE_PADDING = 0.1  # seconds
TTS_MIN_SEGMENT_DURATION = 0.5  # seconds

# Logging Configuration
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def generate_output_filename(original_filename, task_id=None):
    """สร้างชื่อไฟล์ผลลัพธ์"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if task_id:
        return f"{timestamp}_{task_id}_translated.mp4"
    else:
        name_without_ext = Path(original_filename).stem
        return f"{timestamp}_{name_without_ext}_translated.mp4"

def cleanup_temp_files(file_paths):
    """ลบไฟล์ชั่วคราว"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️  ลบไฟล์ชั่วคราว: {file_path}")
        except Exception as e:
            print(f"⚠️  ไม่สามารถลบไฟล์ {file_path}: {e}")

def cleanup_upload_file(file_path):
    """ลบไฟล์ upload หลังประมวลผล"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️  ลบไฟล์ upload: {file_path}")
    except Exception as e:
        print(f"⚠️  ไม่สามารถลบไฟล์ upload {file_path}: {e}") 