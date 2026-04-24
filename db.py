"""
Neon Database Connection
สำหรับ น้องเก็บให้
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Connection string จาก Neon
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_Gnm1MNuZ8IyO@ep-spring-wind-a1m1l43z-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require")

def get_connection():
    """สร้าง connection ไป Neon"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# =============================================
# Users
# =============================================

def get_or_create_user(line_user_id: str, display_name: str = None, picture_url: str = None):
    """หา user หรือสร้างใหม่ถ้าไม่มี"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # หาก่อน
            cur.execute("SELECT * FROM users WHERE line_user_id = %s", (line_user_id,))
            user = cur.fetchone()
            
            if user:
                return dict(user)
            
            # สร้างใหม่
            cur.execute("""
                INSERT INTO users (line_user_id, display_name, picture_url)
                VALUES (%s, %s, %s)
                RETURNING *
            """, (line_user_id, display_name, picture_url))
            conn.commit()
            return dict(cur.fetchone())

# =============================================
# Intents
# =============================================

def create_intent(line_user_id: str, user_id: int = None):
    """สร้าง intent ใหม่"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO intents (line_user_id, user_id)
                VALUES (%s, %s)
                RETURNING *
            """, (line_user_id, user_id))
            conn.commit()
            return dict(cur.fetchone())

def update_intent(intent_id: int, final_text: str = None, status: str = None):
    """อัพเดท intent"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            updates = []
            values = []
            
            if final_text is not None:
                updates.append("final_text = %s")
                values.append(final_text)
            if status is not None:
                updates.append("status = %s")
                values.append(status)
            
            if not updates:
                return None
            
            values.append(intent_id)
            cur.execute(f"""
                UPDATE intents SET {', '.join(updates)}
                WHERE id = %s
                RETURNING *
            """, values)
            conn.commit()
            return dict(cur.fetchone())

def get_recent_intents(line_user_id: str, limit: int = 5):
    """ดึง intents ล่าสุดของ user"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM intents 
                WHERE line_user_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (line_user_id, limit))
            return [dict(row) for row in cur.fetchall()]

# =============================================
# Messages
# =============================================

def create_message(
    line_user_id: str,
    role: str,
    content: str = None,
    user_id: int = None,
    intent_id: int = None,
    audio_url: str = None,
    audio_duration: float = None,
    transcribed_text: str = None,
    message_type: str = 'new',
    stt_process_time: float = None,
    llm_process_time: float = None
):
    """บันทึก message"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO messages (
                    line_user_id, user_id, intent_id, role, 
                    audio_url, audio_duration, transcribed_text, content,
                    message_type, stt_process_time, llm_process_time
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                line_user_id, user_id, intent_id, role,
                audio_url, audio_duration, transcribed_text, content,
                message_type, stt_process_time, llm_process_time
            ))
            conn.commit()
            return dict(cur.fetchone())

def get_conversation_history(line_user_id: str, limit: int = 20):
    """ดึงประวัติสนทนาล่าสุด"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM messages 
                WHERE line_user_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (line_user_id, limit))
            rows = [dict(row) for row in cur.fetchall()]
            return list(reversed(rows))  # เรียงจากเก่าไปใหม่

def get_messages_by_intent(intent_id: int):
    """ดึง messages ของ intent"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM messages 
                WHERE intent_id = %s 
                ORDER BY created_at ASC
            """, (intent_id,))
            return [dict(row) for row in cur.fetchall()]

# =============================================
# Correction Pairs (สำหรับ Fine-tune)
# =============================================

def create_correction_pair(
    intent_id: int,
    original_message_id: int,
    original_audio_url: str,
    original_text: str,
    corrected_message_id: int,
    corrected_audio_url: str,
    corrected_text: str
):
    """บันทึกคู่แก้ไขสำหรับ fine-tune"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO correction_pairs (
                    intent_id, original_message_id, original_audio_url, original_text,
                    corrected_message_id, corrected_audio_url, corrected_text
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                intent_id, original_message_id, original_audio_url, original_text,
                corrected_message_id, corrected_audio_url, corrected_text
            ))
            conn.commit()
            return dict(cur.fetchone())

def get_unverified_corrections(limit: int = 100):
    """ดึงคู่แก้ไขที่ยังไม่ verify"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM correction_pairs 
                WHERE verified = FALSE 
                ORDER BY created_at ASC 
                LIMIT %s
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]

def verify_correction(correction_id: int):
    """ยืนยันคู่แก้ไข"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE correction_pairs 
                SET verified = TRUE, verified_at = %s
                WHERE id = %s
                RETURNING *
            """, (datetime.now(), correction_id))
            conn.commit()
            return dict(cur.fetchone())

# =============================================
# Test Connection
# =============================================

def test_connection():
    """ทดสอบ connection"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT NOW()")
                result = cur.fetchone()
                print(f"✅ Connected to Neon!")
                print(f"   Server time: {result['now']}")
                
                # นับ tables
                cur.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = [row['table_name'] for row in cur.fetchall()]
                print(f"   Tables: {', '.join(tables)}")
                
                return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
