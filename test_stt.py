"""
ทดสอบ STT Server
รัน: python test_stt.py audio\voice2.wav
"""

import sys
import requests
import time

SERVER_URL = "http://localhost:8000"

def test_health():
    """เช็คว่า server พร้อมหรือยัง"""
    try:
        r = requests.get(f"{SERVER_URL}/health")
        return r.json()
    except:
        return None

def test_transcribe(audio_path: str):
    """ทดสอบถอดเสียง"""
    print(f"Sending: {audio_path}")
    
    start = time.time()
    with open(audio_path, "rb") as f:
        r = requests.post(
            f"{SERVER_URL}/transcribe",
            files={"file": f}
        )
    
    total_time = time.time() - start
    
    if r.status_code == 200:
        data = r.json()
        print(f"\n✅ Success!")
        print(f"Text: {data['text']}")
        print(f"Audio duration: {data.get('audio_duration', '?')}s")
        print(f"\n⏱️ Timing breakdown:")
        timing = data.get('timing', {})
        print(f"   read_file:  {timing.get('read_file', '?')}s")
        print(f"   save_temp:  {timing.get('save_temp', '?')}s")
        print(f"   load_audio: {timing.get('load_audio', '?')}s")
        print(f"   transcribe: {timing.get('transcribe', '?')}s")
        print(f"   total:      {timing.get('total', '?')}s")
        print(f"\n   request:    {total_time:.3f}s")
    else:
        print(f"\n❌ Error: {r.text}")

if __name__ == "__main__":
    # เช็ค server
    health = test_health()
    if not health:
        print("❌ Server not running!")
        print("รัน start-stt-server.bat ก่อน")
        sys.exit(1)
    
    print(f"✅ Server ready: {health}")
    
    # ถ้ามี argument เป็นไฟล์เสียง
    if len(sys.argv) > 1:
        test_transcribe(sys.argv[1])
    else:
        print("\nใช้งาน: python test_stt.py [ไฟล์เสียง]")
        print("ตัวอย่าง: python test_stt.py audio\\voice2.wav")
