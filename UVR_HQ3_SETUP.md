# การติดตั้งโมเดล UVR-MDX-NET-Inst_HQ3

## 📋 ภาพรวม

โมเดล **UVR-MDX-NET-Inst_HQ3** เป็นโมเดลคุณภาพสูงสำหรับการแยกดนตรีออกจากเสียงร้องในระบบ Ultimate Vocal Remover

## 🎯 ความแตกต่างระหว่างโมเดล

### UVR-MDX-NET-Inst_FT (ปัจจุบัน)
- ✅ มีอยู่ในระบบ
- ⚡ ประมวลผลเร็ว
- 📊 คุณภาพปานกลาง

### UVR-MDX-NET-Inst_HQ3 (แนะนำ)
- 🎵 คุณภาพสูงกว่า
- 🎼 แยกดนตรีได้แม่นยำกว่า
- 📈 เหมาะสำหรับการประมวลผลขั้นสุดท้าย

## 📥 วิธีการดาวน์โหลด

### วิธีที่ 1: จาก Ultimate Vocal Remover GUI
1. ดาวน์โหลด [Ultimate Vocal Remover GUI](https://github.com/Anjok07/ultimatevocalremovergui)
2. รันโปรแกรมและไปที่ Settings > Download Models
3. เลือก "UVR-MDX-NET-Inst_HQ3.onnx"
4. คัดลอกไฟล์จากโฟลเดอร์ `models` ของ UVR GUI ไปยัง `models/` ของโปรเจค

### วิธีที่ 2: จาก GitHub Repository
1. ไปที่ [TRvlvr/model_repo](https://github.com/TRvlvr/model_repo)
2. ดาวน์โหลดไฟล์ `UVR-MDX-NET-Inst_HQ3.onnx`
3. วางไฟล์ในโฟลเดอร์ `models/`

### วิธีที่ 3: จาก HuggingFace (ต้อง Login)
```bash
# ติดตั้ง huggingface_hub
pip install huggingface_hub

# Login to HuggingFace
huggingface-cli login

# ดาวน์โหลดโมเดล
python -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='TRvlvr/model_repo',
    filename='UVR-MDX-NET-Inst_HQ3.onnx',
    local_dir='models'
)
"
```

## 🔧 การติดตั้ง

1. วางไฟล์ `UVR-MDX-NET-Inst_HQ3.onnx` ในโฟลเดอร์ `models/`
2. รีสตาร์ทแอปพลิเคชัน
3. ระบบจะเลือกใช้โมเดล HQ3 โดยอัตโนมัติ

## ✅ การตรวจสอบ

หลังจากติดตั้งแล้ว ระบบจะแสดงข้อความ:
```
✅ ใช้โมเดล UVR-MDX-NET-Inst_HQ3 สำหรับแยกดนตรี
```

## 🎵 การใช้งาน

### ในขั้นตอนที่ 2: แยกเสียงร้อง/ดนตรี
- ระบบจะใช้โมเดล HQ3 สำหรับแยกดนตรี
- ได้ไฟล์เสียงร้องและดนตรีแยกกัน
- ดนตรีจะถูกใช้ในการรวมเสียงกับวิดีโอขั้นสุดท้าย

### ในขั้นตอนที่ 6: รวมเสียงกับวิดีโอ
- เสียง TTS จะถูกผสมกับดนตรีเดิม
- ได้วิดีโอที่มีเสียงแปลแต่ดนตรีเดิม

## 🔍 การแก้ไขปัญหา

### ปัญหา: ไม่พบโมเดล HQ3
**วิธีแก้:**
1. ตรวจสอบว่าไฟล์อยู่ใน `models/UVR-MDX-NET-Inst_HQ3.onnx`
2. ตรวจสอบขนาดไฟล์ (ควรมากกว่า 100MB)
3. รีสตาร์ทแอปพลิเคชัน

### ปัญหา: ระบบใช้โมเดล FT แทน
**วิธีแก้:**
1. ตรวจสอบว่าไฟล์ HQ3 มีอยู่จริง
2. ลบไฟล์ placeholder ถ้ามี
3. รีสตาร์ทแอปพลิเคชัน

## 📊 เปรียบเทียบคุณภาพ

| คุณสมบัติ | FT Model | HQ3 Model |
|-----------|----------|-----------|
| ความเร็ว | ⚡⚡⚡ | ⚡⚡ |
| คุณภาพ | 📊📊 | 📊📊📊 |
| ความแม่นยำ | 🎯🎯 | 🎯🎯🎯 |
| ขนาดไฟล์ | ~50MB | ~100MB |

## 💡 เคล็ดลับ

- ใช้โมเดล FT สำหรับการทดสอบ
- ใช้โมเดล HQ3 สำหรับผลงานขั้นสุดท้าย
- ระบบจะ fallback ไปใช้โมเดล FT ถ้า HQ3 ไม่มี
- สามารถสลับระหว่างโมเดลได้โดยการเปลี่ยนชื่อไฟล์ 