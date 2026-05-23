-- =============================================
-- น้องเก็บให้ Database Schema
-- Neon PostgreSQL
-- =============================================

-- 1. ตาราง users (ข้อมูล LINE users)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    line_user_id VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    picture_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. ตาราง intents (ความประสงค์ของผู้ใช้)
CREATE TABLE IF NOT EXISTS intents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    line_user_id VARCHAR(50) NOT NULL,
    
    final_text TEXT,                          -- ข้อความสุดท้ายที่ถูกต้อง
    status VARCHAR(20) DEFAULT 'pending',     -- pending / completed / cancelled
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. ตาราง messages (ทุกข้อความ ทั้ง user และ assistant)
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    line_user_id VARCHAR(50) NOT NULL,
    intent_id INTEGER REFERENCES intents(id), -- ชี้ว่าเป็นของ intent ไหน (LLM กำหนด)
    
    role VARCHAR(20) NOT NULL,                -- 'user' / 'assistant'
    
    -- Audio (ถ้าเป็น voice message)
    audio_url TEXT,
    audio_duration DECIMAL(10,2),
    
    -- Text
    transcribed_text TEXT,                    -- ผลจาก STT (ถ้าเป็น voice)
    content TEXT,                             -- ข้อความจริง (text หรือ LLM response)
    
    -- Type
    message_type VARCHAR(20) DEFAULT 'new',   -- 'new' / 'correction'
    
    -- Processing time
    stt_process_time DECIMAL(10,3),
    llm_process_time DECIMAL(10,3),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. ตาราง correction_pairs (สำหรับ fine-tune)
CREATE TABLE IF NOT EXISTS correction_pairs (
    id SERIAL PRIMARY KEY,
    intent_id INTEGER REFERENCES intents(id),
    
    -- Original (ถอดผิด)
    original_message_id INTEGER REFERENCES messages(id),
    original_audio_url TEXT,
    original_text TEXT,                       -- STT ถอดได้ผิด
    
    -- Corrected (ถอดถูก / user แก้)
    corrected_message_id INTEGER REFERENCES messages(id),
    corrected_audio_url TEXT,
    corrected_text TEXT,                      -- ข้อความที่ถูกต้อง
    
    -- Status
    verified BOOLEAN DEFAULT FALSE,           -- ยืนยันแล้วหรือยัง
    verified_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- Indexes
-- =============================================
CREATE INDEX IF NOT EXISTS idx_users_line_user_id ON users(line_user_id);
CREATE INDEX IF NOT EXISTS idx_intents_line_user_id ON intents(line_user_id);
CREATE INDEX IF NOT EXISTS idx_intents_status ON intents(status);
CREATE INDEX IF NOT EXISTS idx_messages_line_user_id ON messages(line_user_id);
CREATE INDEX IF NOT EXISTS idx_messages_intent_id ON messages(intent_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_correction_pairs_intent_id ON correction_pairs(intent_id);
CREATE INDEX IF NOT EXISTS idx_correction_pairs_verified ON correction_pairs(verified);

-- =============================================
-- Auto update updated_at
-- =============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_intents_updated_at ON intents;
CREATE TRIGGER update_intents_updated_at
    BEFORE UPDATE ON intents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
