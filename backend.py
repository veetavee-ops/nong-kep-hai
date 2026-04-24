"""
น้องเก็บให้ - Backend Server
รับเสียงจาก LIFF → ส่ง STT → บันทึก DB → ส่ง LLM → ตอบกลับ
"""

import os
import io
import time
import json
import httpx
from datetime import datetime
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import db

load_dotenv()

# Config
STT_SERVER_URL = os.getenv("STT_SERVER_URL", "http://localhost:8000")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup"""
    print("=" * 50)
    print("น้องเก็บให้ Backend Server")
    print("=" * 50)
    yield

app = FastAPI(title="น้องเก็บให้ Backend", lifespan=lifespan)

# CORS - อนุญาต LIFF เรียกได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production ควรระบุ domain จริง
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================
# Health Check
# =============================================

@app.get("/")
async def root():
    return {"status": "ready", "service": "nong-kep-hai"}

@app.get("/health")
async def health():
    """เช็คสถานะ Backend + STT Server"""
    stt_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{STT_SERVER_URL}/health")
            if r.status_code == 200:
                stt_status = "healthy"
            else:
                stt_status = "unhealthy"
    except:
        stt_status = "offline"
    
    return {
        "backend": "healthy",
        "stt_server": stt_status,
        "database": "healthy" if db.test_connection() else "offline"
    }

# =============================================
# User Management
# =============================================

@app.post("/users/register")
async def register_user(
    line_user_id: str = Form(...),
    display_name: str = Form(None),
    picture_url: str = Form(None)
):
    """ลงทะเบียน/ดึงข้อมูล user"""
    user = db.get_or_create_user(line_user_id, display_name, picture_url)
    return {"success": True, "user": user}

# =============================================
# Voice Processing (Main Flow)
# =============================================

@app.post("/voice/transcribe")
async def transcribe_voice(
    file: UploadFile = File(...),
    line_user_id: str = Form(...)
):
    """
    รับไฟล์เสียง → ส่ง STT → บันทึก DB → return text
    ยังไม่ส่ง LLM (แยก endpoint)
    """
    total_start = time.time()
    
    # 1. ดึง/สร้าง user
    user = db.get_or_create_user(line_user_id)
    
    # 2. ส่งไป STT Server
    stt_start = time.time()
    try:
        content = await file.read()
        async with httpx.AsyncClient(timeout=120) as client:
            files = {"file": (file.filename, content, file.content_type)}
            r = await client.post(f"{STT_SERVER_URL}/transcribe", files=files)
            
            if r.status_code != 200:
                raise HTTPException(status_code=500, detail="STT Server error")
            
            stt_result = r.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="STT Server timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT error: {str(e)}")
    
    stt_time = time.time() - stt_start
    transcribed_text = stt_result.get("text", "")
    audio_duration = stt_result.get("audio_duration", 0)
    
    # 3. บันทึกลง DB (ยังไม่มี intent_id)
    message = db.create_message(
        line_user_id=line_user_id,
        user_id=user["id"],
        role="user",
        content=transcribed_text,
        transcribed_text=transcribed_text,
        audio_duration=audio_duration,
        stt_process_time=stt_time,
        message_type="new"
    )
    
    total_time = time.time() - total_start
    
    return JSONResponse({
        "success": True,
        "text": transcribed_text,
        "message_id": message["id"],
        "timing": {
            "stt": round(stt_time, 3),
            "total": round(total_time, 3)
        },
        "audio_duration": audio_duration
    })

@app.post("/voice/process")
async def process_voice(
    file: UploadFile = File(...),
    line_user_id: str = Form(...)
):
    """
    Full Flow: รับเสียง → STT → LLM → ตอบกลับ
    """
    total_start = time.time()
    
    # 1. ดึง/สร้าง user
    user = db.get_or_create_user(line_user_id)
    
    # 2. ส่งไป STT Server
    stt_start = time.time()
    try:
        content = await file.read()
        async with httpx.AsyncClient(timeout=120) as client:
            files = {"file": (file.filename, content, file.content_type)}
            r = await client.post(f"{STT_SERVER_URL}/transcribe", files=files)
            
            if r.status_code != 200:
                raise HTTPException(status_code=500, detail="STT Server error")
            
            stt_result = r.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="STT Server timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT error: {str(e)}")
    
    stt_time = time.time() - stt_start
    transcribed_text = stt_result.get("text", "")
    audio_duration = stt_result.get("audio_duration", 0)
    
    # 3. ดึง conversation history
    history = db.get_conversation_history(line_user_id, limit=10)
    
    # 4. ส่งไป LLM
    llm_start = time.time()
    llm_response = await call_llm(transcribed_text, history)
    llm_time = time.time() - llm_start
    
    # 5. วิเคราะห์ผล LLM (intent, correction)
    intent_id = llm_response.get("intent_id")
    is_correction = llm_response.get("is_correction", False)
    final_text = llm_response.get("final_text", transcribed_text)
    assistant_reply = llm_response.get("response", "")
    
    # 6. สร้าง/อัพเดท intent
    if is_correction and intent_id:
        # แก้ไข intent เดิม
        db.update_intent(intent_id, final_text=final_text)
        message_type = "correction"
    else:
        # สร้าง intent ใหม่
        intent = db.create_intent(line_user_id, user["id"])
        intent_id = intent["id"]
        db.update_intent(intent_id, final_text=final_text)
        message_type = "new"
    
    # 7. บันทึก user message
    user_message = db.create_message(
        line_user_id=line_user_id,
        user_id=user["id"],
        intent_id=intent_id,
        role="user",
        content=transcribed_text,
        transcribed_text=transcribed_text,
        audio_duration=audio_duration,
        stt_process_time=stt_time,
        message_type=message_type
    )
    
    # 8. บันทึก assistant message
    assistant_message = db.create_message(
        line_user_id=line_user_id,
        user_id=user["id"],
        intent_id=intent_id,
        role="assistant",
        content=assistant_reply,
        llm_process_time=llm_time
    )
    
    total_time = time.time() - total_start
    
    return JSONResponse({
        "success": True,
        "transcribed_text": transcribed_text,
        "response": assistant_reply,
        "intent_id": intent_id,
        "is_correction": is_correction,
        "final_text": final_text,
        "timing": {
            "stt": round(stt_time, 3),
            "llm": round(llm_time, 3),
            "total": round(total_time, 3)
        }
    })

# =============================================
# LLM Integration
# =============================================

async def call_llm(user_text: str, history: list) -> dict:
    """
    ส่งข้อความไป LLM แล้ว return ผลลัพธ์
    TODO: เปลี่ยนเป็น Kimi/Google API จริง
    """
    
    # ถ้ายังไม่มี API key → ใช้ mock response
    if not LLM_API_KEY or not LLM_API_URL:
        return mock_llm_response(user_text, history)
    
    # TODO: Implement real LLM API call
    # async with httpx.AsyncClient() as client:
    #     r = await client.post(LLM_API_URL, ...)
    
    return mock_llm_response(user_text, history)

def mock_llm_response(user_text: str, history: list) -> dict:
    """
    Mock LLM response สำหรับทดสอบ
    จะถูกแทนที่ด้วย API จริงทีหลัง
    """
    
    # ตรวจจับคำแก้ไข
    correction_keywords = ["ไม่ใช่", "ผิด", "หมายถึง", "แก้", "ที่ถูกคือ", "ไม่ใช่นะ"]
    is_correction = any(kw in user_text for kw in correction_keywords)
    
    # หา intent ล่าสุดถ้าเป็นการแก้ไข
    intent_id = None
    if is_correction and history:
        # หา intent_id จาก message ก่อนหน้า
        for msg in reversed(history):
            if msg.get("intent_id"):
                intent_id = msg["intent_id"]
                break
    
    # สร้าง response
    if is_correction:
        response = f"รับทราบค่ะ แก้ไขเป็น: {user_text}"
        final_text = user_text.replace("ไม่ใช่", "").replace("ผิด", "").strip()
    else:
        response = f"รับทราบค่ะ: {user_text}"
        final_text = user_text
    
    return {
        "intent_id": intent_id,
        "is_correction": is_correction,
        "final_text": final_text,
        "response": response
    }

# =============================================
# Conversation History
# =============================================

@app.get("/conversations/{line_user_id}")
async def get_conversations(line_user_id: str, limit: int = 20):
    """ดึงประวัติสนทนา"""
    history = db.get_conversation_history(line_user_id, limit)
    return {"success": True, "messages": history}

@app.get("/intents/{line_user_id}")
async def get_intents(line_user_id: str, limit: int = 10):
    """ดึง intents ล่าสุด"""
    intents = db.get_recent_intents(line_user_id, limit)
    return {"success": True, "intents": intents}





# =============================================
# LINE Webhook
# =============================================

@app.post("/webhook")
async def line_webhook(request: Request):
    """รับ event จาก LINE"""
    
    body = await request.body()
    
    try:
        data = json.loads(body)
        events = data.get("events", [])
        
        for event in events:
            await handle_line_event(event)
        
        return {"status": "ok"}
    
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}


async def handle_line_event(event: dict):
    """จัดการ event แต่ละประเภท"""
    
    event_type = event.get("type")
    
    if event_type == "message":
        message = event.get("message", {})
        message_type = message.get("type")
        reply_token = event.get("replyToken")
        user_id = event["source"].get("userId")
        
        print(f"📩 Message from {user_id}: type={message_type}")
        
        if message_type == "audio":
            message_id = message.get("id")
            audio_content = await download_line_content(message_id)
            
            if audio_content:
                transcribed = await transcribe_audio_bytes(audio_content, user_id)
                await reply_to_line(reply_token, f"ได้ยินว่า: {transcribed}")
            else:
                await reply_to_line(reply_token, "ไม่สามารถดึงไฟล์เสียงได้")
        
        elif message_type == "text":
            text = message.get("text", "")
            print(f"📝 Text: {text}")
            await reply_to_line(reply_token, f"รับข้อความ: {text}")


async def download_line_content(message_id: str) -> bytes:
    """ดาวน์โหลดไฟล์จาก LINE"""
    
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                print(f"✅ Downloaded audio: {len(r.content)} bytes")
                return r.content
            else:
                print(f"❌ Download failed: {r.status_code}")
                return None
    except Exception as e:
        print(f"❌ Download error: {e}")
        return None


async def transcribe_audio_bytes(audio_bytes: bytes, user_id: str) -> str:
    """ส่ง audio bytes ไป STT"""
    
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            files = {"file": ("audio.m4a", audio_bytes, "audio/m4a")}
            r = await client.post(f"{STT_SERVER_URL}/transcribe", files=files)
            
            if r.status_code == 200:
                result = r.json()
                return result.get("text", "")
            else:
                return "[STT error]"
    except Exception as e:
        print(f"STT error: {e}")
        return "[STT timeout]"


async def reply_to_line(reply_token: str, text: str):
    """ตอบกลับไป LINE"""
    
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, headers=headers, json=payload)
            print(f"📤 Reply sent: {r.status_code}")
    except Exception as e:
        print(f"❌ Reply error: {e}")
# =============================================
# Run Server\\wsl$\Ubuntu\home\paul\nong-kep-hai\.env
# =============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
