#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Ultimate Vocal Remover models
ทดสอบโมเดล Ultimate Vocal Remover
"""

import os
import sys
from pathlib import Path
import numpy as np
import soundfile as sf

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services import UltimateVocalRemover

def create_test_audio():
    """สร้างไฟล์เสียงทดสอบ"""
    print("🎵 สร้างไฟล์เสียงทดสอบ...")
    
    # สร้างเสียงทดสอบ (เสียงร้อง + ดนตรี)
    sample_rate = 44100
    duration = 5  # 5 วินาที
    
    # สร้างเสียงร้อง (sine wave 440Hz)
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    vocals = 0.3 * np.sin(2 * np.pi * 440 * t)  # เสียงร้อง
    
    # สร้างดนตรี (chord progression)
    music = 0.2 * np.sin(2 * np.pi * 220 * t) + 0.1 * np.sin(2 * np.pi * 330 * t)
    
    # ผสมเสียง
    mixed_audio = vocals + music
    
    # บันทึกไฟล์
    test_audio_path = Path("temp/test_audio.wav")
    test_audio_path.parent.mkdir(exist_ok=True)
    sf.write(str(test_audio_path), mixed_audio, sample_rate)
    
    print(f"✅ สร้างไฟล์เสียงทดสอบ: {test_audio_path}")
    return str(test_audio_path)

def test_uvr_models():
    """ทดสอบโมเดล UVR"""
    print("🧪 เริ่มทดสอบ Ultimate Vocal Remover models...")
    
    # สร้างไฟล์เสียงทดสอบ
    test_audio_path = create_test_audio()
    
    # สร้าง UVR instance
    uvr = UltimateVocalRemover()
    
    print(f"📊 โมเดลที่โหลด: {len(uvr.models)}")
    print(f"📋 รายการโมเดล: {list(uvr.models.keys())}")
    
    # ทดสอบการแยกเสียง
    print("\n🎵 ทดสอบการแยกเสียง...")
    try:
        result = uvr.separate_audio(test_audio_path, "test_task")
        
        print("✅ การแยกเสียงสำเร็จ!")
        print(f"🎤 เสียงร้อง: {result['vocals']}")
        print(f"🎵 ดนตรี: {result['instrumental']}")
        print(f"📊 Sample Rate: {result['original_sr']}")
        
        # ตรวจสอบไฟล์ที่สร้างขึ้น
        vocals_path = Path(result['vocals'])
        instrumental_path = Path(result['instrumental'])
        
        if vocals_path.exists():
            print(f"✅ ไฟล์เสียงร้องมีอยู่: {vocals_path.stat().st_size} bytes")
        else:
            print("❌ ไม่พบไฟล์เสียงร้อง")
            
        if instrumental_path.exists():
            print(f"✅ ไฟล์ดนตรีมีอยู่: {instrumental_path.stat().st_size} bytes")
        else:
            print("❌ ไม่พบไฟล์ดนตรี")
        
        return True
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการทดสอบ: {e}")
        return False

def test_model_types():
    """ทดสอบประเภทโมเดลต่างๆ"""
    print("\n🔍 ทดสอบประเภทโมเดล...")
    
    uvr = UltimateVocalRemover()
    
    # ตรวจสอบ VR models
    vr_models = [key for key in uvr.models.keys() if key.startswith('vr_')]
    print(f"🎵 VR Models: {vr_models}")
    
    # ตรวจสอบ MDX models
    mdx_models = [key for key in uvr.models.keys() if key.startswith('mdx_')]
    print(f"🎵 MDX Models: {mdx_models}")
    
    # ตรวจสอบ default models
    if 'vocal' in uvr.models:
        print("✅ มีโมเดลเสียงร้องเริ่มต้น")
    else:
        print("❌ ไม่มีโมเดลเสียงร้องเริ่มต้น")
        
    if 'instrumental' in uvr.models:
        print("✅ มีโมเดลดนตรีเริ่มต้น")
    else:
        print("❌ ไม่มีโมเดลดนตรีเริ่มต้น")

def main():
    """ฟังก์ชันหลัก"""
    print("🚀 เริ่มทดสอบ Ultimate Vocal Remover Models")
    print("=" * 50)
    
    # ทดสอบประเภทโมเดล
    test_model_types()
    
    # ทดสอบการแยกเสียง
    success = test_uvr_models()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 การทดสอบสำเร็จ! โมเดล UVR พร้อมใช้งาน")
    else:
        print("❌ การทดสอบล้มเหลว กรุณาตรวจสอบการตั้งค่า")
    
    # ลบไฟล์ทดสอบ
    test_files = ["temp/test_audio.wav", "temp/test_task_vocals.wav", "temp/test_task_instrumental.wav"]
    for file_path in test_files:
        if Path(file_path).exists():
            Path(file_path).unlink()
            print(f"🗑️ ลบไฟล์: {file_path}")

if __name__ == "__main__":
    main() 