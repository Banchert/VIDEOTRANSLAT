# Ultimate Vocal Remover (UVR) Models Setup Guide
# คู่มือการตั้งค่าโมเดล Ultimate Vocal Remover

## 📁 โครงสร้างโฟลเดอร์ Models

```
models/
├── VR_Models/                    # VR Architecture models (.pth files)
│   ├── UVR-DeNoise-Lite.pth     # 17MB - Lightweight denoising model
│   ├── 1_HP-UVR.pth            # 121MB - High-performance vocal separation
│   └── model_data/              # Additional model data
├── MDX_Net_Models/              # MDX Network models (.onnx files)
│   ├── Kim_Vocal_2.onnx        # 64MB - Vocal separation model
│   ├── UVR-MDX-NET-Inst_HQ_3.onnx  # 64MB - High-quality instrumental separation
│   └── model_data/              # Additional model data
├── uvr_config.json              # Configuration file
├── uvr_config.py                # Python configuration
└── [dummy files]                # Fallback dummy models
```

## 🎵 ประเภทโมเดล UVR

### 1. VR Architecture Models (.pth files)
- **UVR-DeNoise-Lite.pth** (17MB): โมเดลเบา สำหรับลดเสียงรบกวน
- **1_HP-UVR.pth** (121MB): โมเดลประสิทธิภาพสูง สำหรับแยกเสียงร้อง

### 2. MDX Network Models (.onnx files)
- **Kim_Vocal_2.onnx** (64MB): โมเดลแยกเสียงร้อง
- **UVR-MDX-NET-Inst_HQ_3.onnx** (64MB): โมเดลแยกดนตรีคุณภาพสูง

## ⚙️ การทำงานของระบบ

### การโหลดโมเดล (Model Loading)
```python
# ระบบจะตรวจสอบและโหลดโมเดลตามลำดับความสำคัญ:
1. VR Models (.pth files) - ประสิทธิภาพสูง
2. MDX Models (.onnx files) - เสถียร
3. Dummy Models (.pkl files) - สำรอง
4. Fallback Method - กรณีไม่มีโมเดล
```

### การประมวลผล (Processing)
```python
# ระบบจะเลือกวิธีการประมวลผลตามโมเดลที่มี:
- VR Models: ใช้ PyTorch processing
- MDX Models: ใช้ ONNX Runtime processing  
- Dummy Models: ใช้ Bandpass filter
- Fallback: ใช้ Simple separation
```

## 🔧 การตั้งค่าในโปรแกรม

### 1. การเปิดใช้งาน Vocal Removal
```python
# ใน config.py
VOCAL_REMOVAL_ENABLED = True
VOCAL_REMOVAL_MODELS = {
    'vr_models': ['UVR-DeNoise-Lite.pth', '1_HP-UVR.pth'],
    'mdx_models': ['Kim_Vocal_2.onnx', 'UVR-MDX-NET-Inst_HQ_3.onnx']
}
```

### 2. การเรียกใช้ใน VideoProcessor
```python
# ใน services.py - VideoProcessor.extract_audio()
if enable_vocal_removal:
    uvr = UltimateVocalRemover()
    separation_result = uvr.separate_audio(audio_path, task_id)
    # เก็บ instrumental_path สำหรับใช้ใน video merge
```

### 3. การใช้ใน Video Merge
```python
# ใน services.py - VideoProcessor.merge_audio_video()
if instrumental_path:
    # ผสม TTS audio กับ instrumental track
    mixed_audio = self._create_advanced_audio_mix(
        tts_audio_path, instrumental_path, task_id
    )
```

## 📊 ผลลัพธ์ที่ได้

### ไฟล์ที่สร้างขึ้น
```
temp/
├── {task_id}_vocals.wav      # เสียงร้องที่แยกออกมา
├── {task_id}_instrumental.wav # ดนตรีที่แยกออกมา
└── {task_id}_mixed_audio.wav  # เสียงผสม (TTS + instrumental)
```

### คุณภาพการแยกเสียง
- **VR Models**: คุณภาพสูงสุด (แนะนำ)
- **MDX Models**: คุณภาพดี (เสถียร)
- **Dummy Models**: คุณภาพปานกลาง (สำรอง)
- **Fallback**: คุณภาพพื้นฐาน

## 🚀 การใช้งาน

### 1. เปิดใช้งานใน UI
```javascript
// ใน frontend - เปิดใช้งาน Vocal Removal
vocalRemovalEnabled: true
```

### 2. การประมวลผลอัตโนมัติ
```python
# ระบบจะประมวลผลตามลำดับ:
1. แยกเสียงร้องและดนตรี
2. แปลงเสียงร้องเป็นข้อความ (STT)
3. แปลข้อความ
4. สังเคราะห์เสียง (TTS)
5. ผสมเสียง TTS กับดนตรีเดิม
```

### 3. การประมวลผลแบบ Manual
```python
# สามารถเลือกขั้นตอนได้:
- Step 2: Vocal Separation
- Step 3: Speech-to-Text
- Step 4: Translation
- Step 5: Text-to-Speech
- Step 6: Audio-Video Merge
```

## 🔍 การตรวจสอบสถานะ

### 1. ตรวจสอบโมเดลที่โหลด
```python
# ใน logs จะแสดง:
✅ โหลด VR model: 1_HP-UVR.pth
✅ โหลด MDX model: Kim_Vocal_2.onnx
✅ ใช้ VR model สำหรับแยกเสียงร้อง
✅ ใช้ MDX model สำหรับแยกดนตรี
```

### 2. ตรวจสอบการประมวลผล
```python
# ใน logs จะแสดง:
🎵 ใช้ VR models สำหรับแยกเสียง...
✅ แยกเสียงสำเร็จ:
   🎤 เสียงร้อง: temp/task_123_vocals.wav
   🎵 ดนตรี: temp/task_123_instrumental.wav
```

## ⚠️ การแก้ไขปัญหา

### 1. ไม่พบโมเดล
```python
# ตรวจสอบ:
- โฟลเดอร์ models/VR_Models/ และ models/MDX_Net_Models/
- ขนาดไฟล์โมเดล (ต้อง > 1MB)
- สิทธิ์การเข้าถึงไฟล์
```

### 2. ข้อผิดพลาดการโหลด
```python
# แก้ไข:
- ตรวจสอบ CUDA/GPU support
- ตรวจสอบ PyTorch และ ONNX Runtime
- ลองใช้ CPU mode
```

### 3. ข้อผิดพลาดการประมวลผล
```python
# แก้ไข:
- ตรวจสอบ RAM (ต้องการ > 8GB)
- ลดขนาดไฟล์เสียง
- ใช้ fallback method
```

## 📈 ประสิทธิภาพ

### ข้อกำหนดระบบ
- **RAM**: 8GB+ (16GB+ สำหรับไฟล์ใหญ่)
- **GPU**: RTX 4090D (แนะนำ)
- **Storage**: 10GB+ สำหรับโมเดล
- **CPU**: 4 cores+ (8 cores+ แนะนำ)

### เวลาประมวลผล (ประมาณ)
- **VR Models**: 2-5 นาที/นาทีเสียง
- **MDX Models**: 3-7 นาที/นาทีเสียง
- **Dummy Models**: 1-2 นาที/นาทีเสียง
- **Fallback**: 30 วินาที-1 นาที/นาทีเสียง

## 🎯 ข้อแนะนำ

### 1. สำหรับการใช้งานทั่วไป
- ใช้ VR Models (1_HP-UVR.pth) สำหรับเสียงร้อง
- ใช้ MDX Models (UVR-MDX-NET-Inst_HQ_3.onnx) สำหรับดนตรี

### 2. สำหรับไฟล์เสียงคุณภาพต่ำ
- ใช้ UVR-DeNoise-Lite.pth สำหรับลดเสียงรบกวน
- ใช้ Dummy Models สำหรับการประมวลผลเร็ว

### 3. สำหรับการประมวลผลแบบ Real-time
- ใช้ Fallback Method
- ลดขนาดไฟล์เสียง
- ใช้ GPU acceleration

## 🔄 การอัปเดต

### การเพิ่มโมเดลใหม่
1. เพิ่มไฟล์โมเดลในโฟลเดอร์ที่เหมาะสม
2. อัปเดต `uvr_config.json`
3. อัปเดต `uvr_config.py`
4. ทดสอบการโหลดโมเดล

### การปรับแต่งการประมวลผล
1. แก้ไข `services.py` - `UltimateVocalRemover` class
2. ปรับแต่ง parameters ใน `_process_with_*_models` methods
3. ทดสอบประสิทธิภาพและคุณภาพ

---

**หมายเหตุ**: ระบบนี้ได้รับการออกแบบให้รองรับโมเดล UVR หลายประเภท และมี fallback mechanisms เพื่อให้แน่ใจว่าสามารถทำงานได้เสมอ แม้ในกรณีที่ไม่มีโมเดลจริง 