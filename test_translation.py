#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append('.')

try:
    from services import TranslationService
    print("✅ Import TranslationService สำเร็จ")
    
    # สร้าง instance
    service = TranslationService()
    print("✅ สร้าง TranslationService instance สำเร็จ")
    
    # ทดสอบการแปล
    test_text = "Hello, how are you today?"
    print(f"📝 ทดสอบการแปล: {test_text}")
    
    result = service.translate(test_text, "en", "th", "nllb-200")
    print(f"✅ ผลการแปล (type: {type(result)}): {result}")
    
    # ตรวจสอบ structure ของ result
    if isinstance(result, dict):
        print("📊 ผลการแปลเป็น dict:")
        for key, value in result.items():
            print(f"  - {key}: {value}")
    elif isinstance(result, str):
        print("📊 ผลการแปลเป็น string")
        print(f"  Content: {result}")
    else:
        print(f"📊 ผลการแปลเป็น {type(result)}")
    
except Exception as e:
    print(f"❌ เกิดข้อผิดพลาด: {str(e)}")
    import traceback
    traceback.print_exc()