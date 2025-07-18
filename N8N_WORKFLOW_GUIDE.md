# N8N Workflow Guide - Video Translator

## 📋 ภาพรวม

N8N workflow นี้แปลงโปรเจกต์ Video Translator เป็นระบบอัตโนมัติที่สามารถเรียกใช้ผ่าน API ได้

## 🚀 การติดตั้ง

### 1. ติดตั้ง N8N
```bash
npm install -g n8n
```

### 2. เริ่มต้น N8N
```bash
n8n start
```

### 3. นำเข้า Workflow
1. เปิด N8N ที่ `http://localhost:5678`
2. คลิก "Import from file"
3. เลือกไฟล์ `n8n-video-translator-workflow.json`
4. คลิก "Import"

## 🔧 การตั้งค่า

### 1. เริ่มต้น Video Translator Server
```bash
cd VIDEOTRANSLAT
python main_optimized.py
```

### 2. ตรวจสอบ URL ใน Workflow
- เปลี่ยน `http://localhost:5556` เป็น URL ของ server ของคุณ
- หรือใช้ IP address เช่น `http://192.168.1.100:5556`

## 📊 โครงสร้าง Workflow

### โหนดหลัก (Main Nodes)

#### 1. **Webhook Trigger**
- **Path**: `/video-translate`
- **Method**: POST
- **Input**: JSON payload

#### 2. **Mode Checker**
- ตรวจสอบโหมดการทำงาน
- **auto**: ประมวลผลอัตโนมัติ
- **step**: ประมวลผลทีละขั้นตอน
- **youtube**: ประมวลผลจาก YouTube URL

#### 3. **Processors**
- **Auto Mode Processor**: `/api/upload/auto`
- **Step Mode Processor**: `/api/upload/step`
- **YouTube Processor**: `/api/youtube/realtime`

#### 4. **Status Management**
- **Status Checker**: ตรวจสอบสถานะงาน
- **Completion Checker**: ตรวจสอบการเสร็จสิ้น
- **Wait 5 Seconds**: รอ 5 วินาที

#### 5. **Step-by-Step Processing**
- **Step 2**: Vocal Removal
- **Step 3**: Speech to Text (STT)
- **Step 4**: Translation
- **Step 5**: Text to Speech (TTS)
- **Step 6**: Audio Mixing
- **Step 7**: Video Merge

#### 6. **Output Handlers**
- **Download Result**: ดาวน์โหลดไฟล์ผลลัพธ์
- **Get Original Text**: ดึงข้อความต้นฉบับ
- **Get Translated Text**: ดึงข้อความที่แปลแล้ว

## 📝 ตัวอย่างการใช้งาน

### 1. โหมดอัตโนมัติ (Auto Mode)

```json
{
  "mode": "auto",
  "video_file": "base64_encoded_video_or_file_path",
  "source_language": "th",
  "target_language": "en",
  "voice_mode": "female",
  "video_speed": "1.0"
}
```

### 2. โหมดทีละขั้นตอน (Step Mode)

```json
{
  "mode": "step",
  "video_file": "base64_encoded_video_or_file_path",
  "source_language": "th",
  "target_language": "en",
  "voice_mode": "female",
  "video_speed": "1.0"
}
```

### 3. โหมด YouTube

```json
{
  "mode": "youtube",
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "source_language": "th",
  "target_language": "en",
  "voice_mode": "female",
  "video_speed": "1.0"
}
```

## 🔄 การทำงานของ Workflow

### ขั้นตอนการทำงาน

1. **รับข้อมูล** → Webhook Trigger
2. **ตรวจสอบโหมด** → Mode Checker
3. **ประมวลผล** → Auto/Step/YouTube Processor
4. **ตรวจสอบสถานะ** → Status Checker
5. **รอผลลัพธ์** → Wait 5 Seconds (ถ้ายังไม่เสร็จ)
6. **ดาวน์โหลดผลลัพธ์** → Download Result
7. **ดึงข้อความ** → Get Original/Translated Text

### สำหรับโหมด Step-by-Step

1. **อัปโหลดไฟล์** → Step Mode Processor
2. **Step 2**: Vocal Removal
3. **Step 3**: Speech to Text
4. **Step 4**: Translation
5. **Step 5**: Text to Speech
6. **Step 6**: Audio Mixing
7. **Step 7**: Video Merge
8. **ตรวจสอบสถานะ** → Status Checker

## 🛠️ การปรับแต่ง

### 1. เปลี่ยน URL Server
แก้ไข URL ในทุกโหนด HTTP Request:
```
http://localhost:5556 → http://your-server-ip:5556
```

### 2. เพิ่ม Authentication
เพิ่ม Headers ในโหนด HTTP Request:
```json
{
  "Authorization": "Bearer YOUR_API_KEY"
}
```

### 3. เพิ่ม Error Handling
เพิ่มโหนด Error Handler:
- **HTTP Request Error**: จัดการข้อผิดพลาด HTTP
- **Timeout Error**: จัดการ timeout
- **Validation Error**: ตรวจสอบข้อมูล input

### 4. เพิ่ม Logging
เพิ่มโหนด Set เพื่อบันทึก log:
```json
{
  "timestamp": "={{ $now }}",
  "task_id": "={{ $json.task_id }}",
  "status": "={{ $json.status }}"
}
```

## 📊 การติดตามผลลัพธ์

### 1. Status Codes
- **200**: สำเร็จ
- **400**: ข้อมูลไม่ถูกต้อง
- **500**: ข้อผิดพลาดเซิร์ฟเวอร์

### 2. Response Format
```json
{
  "success": true,
  "task_id": "uuid-string",
  "status": "completed",
  "download_url": "http://localhost:5556/api/download/task_id",
  "original_text": "ข้อความต้นฉบับ",
  "translated_text": "Translated text"
}
```

## 🔧 การแก้ไขปัญหา

### 1. Server ไม่ตอบสนอง
- ตรวจสอบว่า Video Translator server กำลังทำงาน
- ตรวจสอบ URL และ port
- ตรวจสอบ firewall

### 2. ไฟล์ใหญ่เกินไป
- เพิ่ม timeout ในโหนด HTTP Request
- ใช้ streaming upload
- แบ่งไฟล์เป็น chunks

### 3. Memory Issues
- ลด concurrent jobs
- เพิ่ม memory monitoring
- ใช้ external storage

## 🚀 การใช้งานขั้นสูง

### 1. Webhook Security
```bash
# สร้าง webhook secret
n8n webhook:generate-secret
```

### 2. Rate Limiting
เพิ่มโหนด Rate Limiter:
```json
{
  "max_requests": 10,
  "time_window": 60000
}
```

### 3. Database Integration
เพิ่มโหนด Database เพื่อบันทึก:
- Task history
- User preferences
- Processing statistics

### 4. Notification System
เพิ่มโหนด Notification:
- Email notification
- Slack notification
- Telegram notification

## 📈 การติดตามประสิทธิภาพ

### 1. Metrics
- Processing time
- Success rate
- Error rate
- Memory usage

### 2. Monitoring
- CPU usage
- Memory usage
- Disk usage
- Network usage

## 🔐 ความปลอดภัย

### 1. Authentication
- API Key authentication
- JWT token
- OAuth 2.0

### 2. Authorization
- Role-based access
- Permission-based access
- IP whitelist

### 3. Data Protection
- Encrypt sensitive data
- Secure file storage
- Audit logging

## 📞 การสนับสนุน

หากพบปัญหา:
1. ตรวจสอบ logs ใน N8N
2. ตรวจสอบ logs ใน Video Translator server
3. ตรวจสอบ network connectivity
4. ติดต่อผู้ดูแลระบบ

---

**หมายเหตุ**: Workflow นี้ต้องการ Video Translator server ที่กำลังทำงานอยู่เพื่อให้สามารถใช้งานได้ 