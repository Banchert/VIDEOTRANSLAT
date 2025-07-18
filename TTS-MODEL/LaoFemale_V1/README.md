# LaoFemale_V1 - Lao Female Voice Model

## ข้อมูลโมเดล

- **ชื่อโมเดล**: LaoFemale_V1
- **ประเภท**: Coqui TTS
- **ภาษา**: ລາວ (Lao)
- **เพศเสียง**: หญิง
- **เวอร์ชัน**: 1.0

## คุณสมบัติ

- เสียงผู้หญิงลาวที่ชัดเจนและเป็นธรรมชาติ
- คุณภาพเสียงสูง (High Quality)
- ความเร็วในการประมวลผลเร็ว
- ใช้หน่วยความจำน้อย
- รองรับการอ่านเครื่องหมายวรรคตอน

## การใช้งาน

### ใน Video Translator

1. เลือก "Coqui TTS" ในโมเดล TTS
2. ใส่ path: `TTS-MODEL/LaoFemale_V1`
3. เลือกเสียง "ผู้หญิง"

### ตัวอย่างการใช้งาน

```python
from services import TTSService

tts = TTSService()
audio = tts.generate_speech(
    text="ສະບາຍດີ ຍິນດີຕ້ອນຮັບສູ່ Video Translator",
    model_path="TTS-MODEL/LaoFemale_V1",
    voice_mode="female"
)
```

## ข้อกำหนดระบบ

- Python 3.8+
- Coqui TTS
- PyTorch
- Librosa

## การติดตั้ง

1. คัดลอกโฟลเดอร์ `LaoFemale_V1` ไปยัง `TTS-MODEL/`
2. ตรวจสอบว่าไฟล์ config.json และ model_info.json อยู่ในโฟลเดอร์
3. ทดสอบการใช้งานผ่าน Video Translator

## การปรับแต่ง

- **Sample Rate**: 22050 Hz
- **Bit Rate**: 32000 bps
- **Channels**: Mono (1)
- **Vocoder**: HiFiGAN
- **Encoder**: Tacotron2

## ประสิทธิภาพ

- **ความเร็ว**: เร็ว
- **หน่วยความจำ**: ต่ำ
- **คุณภาพ**: 4.0/5.0

## ข้อมูลการฝึกฝน

- **จำนวนตัวอย่าง**: 3,000 ตัวอย่าง
- **ระยะเวลารวม**: 6 ชั่วโมง
- **คุณภาพเสียง**: สูง
- **การลดเสียงรบกวน**: ใช่
- **การปรับมาตรฐาน**: ใช่

## การสนับสนุน

หากมีปัญหาหรือต้องการความช่วยเหลือ กรุณาติดต่อทีมพัฒนา Video Translator

## หมายเหตุ

โมเดลนี้ได้รับการออกแบบมาเพื่อรองรับภาษาลาวโดยเฉพาะ เหมาะสำหรับการแปลวิดีโอที่มีเนื้อหาภาษาลาว 