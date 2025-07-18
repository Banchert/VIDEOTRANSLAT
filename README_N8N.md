# 🎬 Video Translator N8N Workflow

แปลงโปรเจกต์ Video Translator เป็นระบบอัตโนมัติด้วย N8N workflow ที่สามารถเรียกใช้ผ่าน API ได้

## 🚀 คุณสมบัติหลัก

### ✅ โหมดการทำงาน
- **โหมดอัตโนมัติ**: ประมวลผลทั้งหมดในครั้งเดียว
- **โหมดทีละขั้นตอน**: ควบคุมการประมวลผลแต่ละขั้นตอน
- **โหมด YouTube**: ประมวลผลวิดีโอจาก YouTube URL

### ✅ ฟีเจอร์ขั้นสูง
- **รองรับหลายภาษา**: 50+ ภาษา
- **เสียง TTS หลากหลาย**: ผู้หญิง, ผู้ชาย, เด็ก, คนแก่, หุ่นยนต์
- **ปรับความเร็ววิดีโอ**: 1x, 2x, 4x
- **ระบบจัดการหน่วยความจำ**: ป้องกันปัญหาแรมเต็ม
- **รองรับ GPU**: ประมวลผลเร็วขึ้น

## 📦 ไฟล์ที่รวมอยู่

```
📁 N8N Workflow Files/
├── 📄 n8n-video-translator-workflow.json    # N8N workflow หลัก
├── 📄 N8N_WORKFLOW_GUIDE.md                 # คู่มือการใช้งาน
├── 📄 n8n-example-requests.json             # ตัวอย่างการเรียกใช้
└── 📄 README_N8N.md                         # ไฟล์นี้
```

## 🛠️ การติดตั้ง

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

### 4. เริ่มต้น Video Translator Server
```bash
cd VIDEOTRANSLAT
python main_optimized.py
```

## 📊 โครงสร้าง Workflow

### 🔗 โหนดหลัก (Main Nodes)

| โหนด | หน้าที่ | URL Endpoint |
|------|--------|--------------|
| **Webhook Trigger** | รับคำขอจากภายนอก | `/video-translate` |
| **Mode Checker** | ตรวจสอบโหมดการทำงาน | - |
| **Auto Mode Processor** | ประมวลผลอัตโนมัติ | `/api/upload/auto` |
| **Step Mode Processor** | ประมวลผลทีละขั้นตอน | `/api/upload/step` |
| **YouTube Processor** | ประมวลผล YouTube | `/api/youtube/realtime` |
| **Status Checker** | ตรวจสอบสถานะ | `/api/status/{task_id}` |
| **Download Result** | ดาวน์โหลดผลลัพธ์ | `/api/download/{task_id}` |

### 🔄 ขั้นตอนการประมวลผล

#### โหมดอัตโนมัติ
1. **อัปโหลดไฟล์** → Auto Mode Processor
2. **ตรวจสอบสถานะ** → Status Checker
3. **รอผลลัพธ์** → Wait 5 Seconds
4. **ดาวน์โหลด** → Download Result

#### โหมดทีละขั้นตอน
1. **อัปโหลดไฟล์** → Step Mode Processor
2. **Step 2**: Vocal Removal
3. **Step 3**: Speech to Text (STT)
4. **Step 4**: Translation
5. **Step 5**: Text to Speech (TTS)
6. **Step 6**: Audio Mixing
7. **Step 7**: Video Merge
8. **ตรวจสอบสถานะ** → Status Checker

## 📝 ตัวอย่างการใช้งาน

### 1. โหมดอัตโนมัติ
```bash
curl -X POST http://localhost:5678/webhook/video-translate \
  -H 'Content-Type: application/json' \
  -d '{
    "mode": "auto",
    "video_file": "base64_encoded_video_data",
    "source_language": "th",
    "target_language": "en",
    "voice_mode": "female",
    "video_speed": "1.0"
  }'
```

### 2. โหมด YouTube
```bash
curl -X POST http://localhost:5678/webhook/video-translate \
  -H 'Content-Type: application/json' \
  -d '{
    "mode": "youtube",
    "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "source_language": "en",
    "target_language": "th",
    "voice_mode": "male",
    "video_speed": "2.0"
  }'
```

### 3. ใช้ Python
```python
import requests
import base64

# อ่านไฟล์วิดีโอ
with open('video.mp4', 'rb') as f:
    video_data = base64.b64encode(f.read()).decode('utf-8')

# ส่งคำขอ
url = 'http://localhost:5678/webhook/video-translate'
data = {
    'mode': 'auto',
    'video_file': video_data,
    'source_language': 'th',
    'target_language': 'en',
    'voice_mode': 'female',
    'video_speed': '1.0'
}

response = requests.post(url, json=data)
print(response.json())
```

## 🌍 ภาษาที่รองรับ

### ภาษาต้นฉบับ (Source Languages)
`auto`, `en`, `th`, `ja`, `ko`, `zh`, `vi`, `hi`, `es`, `fr`, `de`, `it`, `pt`, `ru`, `ar`, `tr`, `pl`, `nl`, `sv`, `da`, `no`, `fi`, `hu`, `cs`, `sk`, `ro`, `bg`, `hr`, `sl`, `et`, `lv`, `lt`, `id`, `ms`, `tl`, `bn`, `ur`, `fa`, `he`, `el`, `uk`, `be`, `mk`, `sr`, `bs`, `me`, `sq`, `lo`

### ภาษาปลายทาง (Target Languages)
`en`, `th`, `ja`, `ko`, `zh`, `vi`, `hi`, `es`, `fr`, `de`, `it`, `pt`, `ru`, `ar`, `tr`, `pl`, `nl`, `sv`, `da`, `no`, `fi`, `hu`, `cs`, `sk`, `ro`, `bg`, `hr`, `sl`, `et`, `lv`, `lt`, `id`, `ms`, `tl`, `bn`, `ur`, `fa`, `he`, `el`, `uk`, `be`, `mk`, `sr`, `bs`, `me`, `sq`, `lo`

## 🎵 โหมดเสียง (Voice Modes)
- `female`: ผู้หญิง
- `male`: ผู้ชาย
- `child`: เด็ก
- `elderly`: คนแก่
- `robot`: หุ่นยนต์
- `whisper`: กระซิบ
- `shout`: ตะโกน
- `sing`: ร้องเพลง

## ⚡ ความเร็ววิดีโอ (Video Speeds)
- `1.0`: ปกติ (1x)
- `2.0`: เร็ว 2 เท่า
- `4.0`: เร็ว 4 เท่า

## 📊 Response Format

### สำเร็จ (Success)
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "Video translation completed successfully",
  "download_url": "http://localhost:5556/api/download/550e8400-e29b-41d4-a716-446655440000",
  "original_text": "สวัสดีครับ นี่คือวิดีโอทดสอบ",
  "translated_text": "Hello, this is a test video",
  "processing_time": "120.5",
  "file_size": "15.2MB"
}
```

### กำลังประมวลผล (Processing)
```json
{
  "success": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Video is being processed",
  "progress": 45,
  "current_step": "Step 4: Translation",
  "estimated_time": "60 seconds remaining"
}
```

### ข้อผิดพลาด (Error)
```json
{
  "success": false,
  "error": "Invalid video file format",
  "message": "Please provide a valid video file (mp4, avi, mov, mkv, wmv, flv, webm)",
  "supported_formats": ["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"]
}
```

## 🔧 การปรับแต่ง

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

## 🔍 การแก้ไขปัญหา

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

## 📄 License

MIT License

## 🤝 การมีส่วนร่วม

หากต้องการปรับปรุง workflow:
1. Fork repository
2. สร้าง feature branch
3. Commit changes
4. Push to branch
5. สร้าง Pull Request

---

**หมายเหตุ**: Workflow นี้ต้องการ Video Translator server ที่กำลังทำงานอยู่เพื่อให้สามารถใช้งานได้

## 🎯 จุดเด่นของ N8N Workflow

### ✅ ข้อดี
- **อัตโนมัติ**: ไม่ต้องใช้ UI ในการประมวลผล
- **API Integration**: เชื่อมต่อกับระบบอื่นได้ง่าย
- **Scalable**: รองรับการใช้งานหลายคนพร้อมกัน
- **Monitoring**: ติดตามสถานะได้แบบ real-time
- **Error Handling**: จัดการข้อผิดพลาดได้ดี
- **Extensible**: เพิ่มฟีเจอร์ใหม่ได้ง่าย

### 🔄 การเปรียบเทียบกับ UI แบบเดิม

| ฟีเจอร์ | UI แบบเดิม | N8N Workflow |
|---------|------------|--------------|
| **การใช้งาน** | ต้องเปิดเว็บไซต์ | เรียกใช้ผ่าน API |
| **อัตโนมัติ** | ต้องกดปุ่มเอง | ทำงานอัตโนมัติ |
| **Integration** | จำกัด | เชื่อมต่อได้หลากหลาย |
| **Monitoring** | ต้องดูหน้าเว็บ | ติดตามผ่าน API |
| **Scalability** | จำกัดผู้ใช้ | รองรับหลายคน |
| **Error Handling** | แสดงในหน้าเว็บ | จัดการอัตโนมัติ |

---

**🎉 พร้อมใช้งานแล้ว!** N8N workflow นี้จะช่วยให้คุณใช้งาน Video Translator ได้อย่างมีประสิทธิภาพและอัตโนมัติมากขึ้น 