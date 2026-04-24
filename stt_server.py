"""
Monsoon Whisper STT Server
รัน: python stt_server.py
API: POST http://localhost:8000/transcribe
"""

import os
import io
import time
import tempfile
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import torch
import soundfile as sf
import librosa
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

load_dotenv()

# Global model storage
model_data = {}

def load_model():
    """โหลด model ครั้งเดียวตอน startup"""
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
    
    model_name = os.getenv("MODEL_NAME", "scb10x/monsoon-whisper-medium-gigaspeech2")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    
    print(f"Loading model: {model_name}")
    print(f"Using device: {device}")
    start_time = time.time()
    
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_name,
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
    )
    model.to(device)
    
    processor = AutoProcessor.from_pretrained(model_name)
    
    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype,
        device=device,
    )
    
    load_time = time.time() - start_time
    print(f"Model loaded in {load_time:.2f} seconds")
    
    return pipe

@asynccontextmanager
async def lifespan(app: FastAPI):
    """โหลด model ตอน startup"""
    model_data["pipe"] = load_model()
    print("=" * 50)
    print("STT Server Ready!")
    print("POST http://localhost:8000/transcribe")
    print("=" * 50)
    yield
    model_data.clear()

app = FastAPI(
    title="Monsoon Whisper STT API",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {"status": "ready", "model": os.getenv("MODEL_NAME", "monsoon-whisper")}

@app.get("/health")
async def health():
    return {"status": "healthy", "model_loaded": "pipe" in model_data}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    """
    รับไฟล์เสียง แล้วถอดเป็นข้อความ
    รองรับ: wav, mp3, m4a, ogg, flac
    """
    if "pipe" not in model_data:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    total_start = time.time()
    
    try:
        # 1. อ่านไฟล์เสียง
        read_start = time.time()
        content = await file.read()
        read_time = time.time() - read_start
        
        # 2. บันทึกเป็น temp file
        save_start = time.time()
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        save_time = time.time() - save_start
        
        try:
            # 3. โหลดและ resample เป็น 16kHz
            load_start = time.time()
            audio, sr = librosa.load(tmp_path, sr=16000)
            audio_duration = len(audio) / sr
            load_time = time.time() - load_start
            
            # 4. ถอดเสียง
            transcribe_start = time.time()
            result = model_data["pipe"](audio, return_timestamps=True)
            transcribe_time = time.time() - transcribe_start
            
            total_time = time.time() - total_start
            
            return JSONResponse({
                "success": True,
                "text": result["text"],
                "chunks": result.get("chunks", []),
                "timing": {
                    "read_file": round(read_time, 3),
                    "save_temp": round(save_time, 3),
                    "load_audio": round(load_time, 3),
                    "transcribe": round(transcribe_time, 3),
                    "total": round(total_time, 3)
                },
                "audio_duration": round(audio_duration, 2),
                "filename": file.filename
            })
            
        finally:
            # ลบ temp file
            os.unlink(tmp_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcribe/url")
async def transcribe_url(audio_url: str):
    """
    รับ URL ของไฟล์เสียง แล้วถอดเป็นข้อความ
    ใช้สำหรับ LINE Audio URL
    """
    import urllib.request
    
    if "pipe" not in model_data:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    total_start = time.time()
    
    try:
        # 1. ดาวน์โหลดไฟล์
        download_start = time.time()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp:
            urllib.request.urlretrieve(audio_url, tmp.name)
            tmp_path = tmp.name
        download_time = time.time() - download_start
        
        try:
            # 2. โหลดและ resample
            load_start = time.time()
            audio, sr = librosa.load(tmp_path, sr=16000)
            audio_duration = len(audio) / sr
            load_time = time.time() - load_start
            
            # 3. ถอดเสียง
            transcribe_start = time.time()
            result = model_data["pipe"](audio, return_timestamps=True)
            transcribe_time = time.time() - transcribe_start
            
            total_time = time.time() - total_start
            
            return JSONResponse({
                "success": True,
                "text": result["text"],
                "chunks": result.get("chunks", []),
                "timing": {
                    "download": round(download_time, 3),
                    "load_audio": round(load_time, 3),
                    "transcribe": round(transcribe_time, 3),
                    "total": round(total_time, 3)
                },
                "audio_duration": round(audio_duration, 2)
            })
            
        finally:
            os.unlink(tmp_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
