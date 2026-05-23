# น้องเก็บให้ (Nong Kep Hai)

Thai Voice Assistant for Business

## Setup

### 1. Clone & Install
```bash
git clone https://github.com/YOUR_USERNAME/nong-kep-hai.git
cd nong-kep-hai
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Config
```bash
copy .env.example .env
# แก้ไข .env ใส่ค่าจริง
```

### 3. Run STT Server
```bash
python stt_server.py
# หรือ
start-stt-server.bat
```

### 4. Test
```bash
python test_stt.py audio\test.wav
python db.py  # test database connection
```

## Architecture

```
LIFF (Frontend)
     │
     ▼
Backend Server ──→ STT Server (Local Monsoon)
     │
     ├──→ Database (Neon PostgreSQL)
     │
     └──→ LLM API (Kimi/Google → Local)
```

## Files

| File | Description |
|------|-------------|
| stt_server.py | STT API Server |
| db.py | Database connection |
| test_stt.py | Test STT |
| schema.sql | Database schema |








สรุปเรื่องราว วัตถุประสงค์ และข้อแนะนำที่เกิดขึ้นในรอบนี้:

1. วัตถุประสงค์ของคุณ
ต้องการสร้าง LINE OA bot (“น้องเก็บให้”) สำหรับเก็บเอกสารและบันทึกเสียง
ต้องการ Rich Menu 6 ช่อง สีพาสเทล (layout เดิม)
ช่อง 1: ปุ่มไมโครโฟน (mic) สำหรับเรียก LIFF menu ส่งเสียงไป STT
ช่อง 2: บัตรประชาชน
ช่อง 3: ทะเบียนบ้าน
ช่อง 4: ใบขับขี่
ช่อง 5: เอกสารสำคัญ
ช่อง 6: เอกสารสำคัญ (หรือเปลี่ยนเป็นอย่างอื่นได้)
ต้องการให้ปุ่ม/ข้อความตรงวัตถุประสงค์ และตำแหน่ง mapping ตรงช่องพอดี
ต้องการดีไซน์ที่ “สวย ทันสมัย” (modern pastel, icon ชัดเจน)
2. ปัญหาที่พบ
Rich Menu ที่ deploy ผ่าน Claude/AI mapping ตรงช่อง แต่ไม่สวยและข้อความไม่ตรงวัตถุประสงค์
Rich Menu ที่ deploy ผ่าน OA Manager สวยแต่ mapping ปุ่มไม่ตรงช่อง
Rich Menu ที่แสดงในมือถือกับ OA Manager ไม่ตรงกัน (deploy ผ่าน API กับ OA Manager คนละอัน)
ต้องการให้ OA Manager กับมือถือแสดง Rich Menu เดียวกัน
3. ข้อแนะนำที่ผมให้
สร้าง Rich Menu ใหม่โดยใช้ “ภาพพื้นหลังสีพาสเทลเดิม”
mapping ปุ่ม/ข้อความ/Action ให้ตรงวัตถุประสงค์ (ตามที่คุณแจ้ง)
ช่อง 1 เป็น LIFF (mic), ช่อง 2-6 เป็นข้อความเอกสาร
วิธี deploy ที่ถูกต้อง:
เตรียมภาพพื้นหลัง (2500x843 px, 6 ช่อง, สีพาสเทล, icon mic ช่อง 1)
สร้าง Rich Menu ใหม่ใน OA Manager
Mapping ปุ่ม/Action ตามที่ต้องการ
Save & Deploy
ปิด-เปิดแอป LINE เพื่อ refresh
ถ้าต้องการให้ OA Manager กับมือถือแสดงเหมือนกัน ต้อง deploy ผ่าน OA Manager และลบ Rich Menu ที่ deploy ผ่าน API ออก
ถ้าต้องการไฟล์ template, mapping, หรือสคริปต์ rich_menu.py แจ้งได้
4. สิ่งที่คุณควรทำต่อ (ถ้าจะทำเองหรือให้ AI อื่นช่วย)
เตรียมภาพพื้นหลัง Rich Menu ตามขนาดและ layout ที่แนะนำ
ใส่ icon mic ช่อง 1, ข้อความ/ไอคอนแต่ละช่องให้ตรงวัตถุประสงค์
สร้าง Rich Menu ใหม่ใน OA Manager และ mapping ปุ่มให้ตรง
Deploy แล้วทดสอบในมือถือ
5. หมายเหตุ
ถ้าต้องการให้ผมช่วย mapping, template, หรือออกแบบภาพ แจ้งได้ทุกเมื่อ
ถ้าต้องการ deploy ผ่านสคริปต์ rich_menu.py สามารถขอ code ตัวอย่างได้