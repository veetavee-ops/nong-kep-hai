#!/usr/bin/env python3
"""
rich_menu.py — จัดการ Rich Menu สำหรับน้องเก็บให้

ใช้:
  python rich_menu.py image                    สร้างไฟล์รูปอย่างเดียว  → rich_menu.jpg
  python rich_menu.py deploy                   สร้างรูป + deploy ไป LINE (set as default)
  python rich_menu.py upload [path]            ใช้รูปที่มีอยู่แล้ว deploy โดยไม่ generate ใหม่
  python rich_menu.py list                     แสดง Rich Menu ที่มีอยู่ทั้งหมด
  python rich_menu.py delete <menuId>          ลบ Rich Menu ตาม ID
  python rich_menu.py delete-all              ลบทั้งหมด + unset default
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Dimensions ────────────────────────────────────────────────
WIDTH, HEIGHT = 2500, 1686
COLS, ROWS = 3, 2

COL_X  = [0, 833, 1666, 2500]
ROW_Y  = [0, 843, 1686]
CELL_W = [833, 833, 834]
CELL_H = [843, 843]

OUTPUT_PATH = "rich_menu.jpg"

# ── LINE API ──────────────────────────────────────────────────
LINE_API      = "https://api.line.me/v2/bot"
LINE_DATA_API = "https://api-data.line.me/v2/bot"

# ── Cell Definitions (3×2, left→right, top→bottom) ───────────
# สีพาสเทล: พื้นหลังเซลล์เป็น pastel แต่ละช่อง
CELLS = [
    # Row 0
    {
        "icon": "MIC",
        "label": "บันทึกเสียง",
        "bg": (200, 240, 225),   # mint pastel
        "action_type": "liff",
    },
    {
        "icon": "ID",
        "label": "บัตรประชาชน",
        "bg": (190, 220, 255),   # blue pastel
        "action_type": "postback",
        "data": "action=id_card",
        "displayText": "บัตรประชาชน",
    },
    {
        "icon": "บ้าน",
        "label": "ทะเบียนบ้าน",
        "bg": (255, 245, 180),   # yellow pastel
        "action_type": "postback",
        "data": "action=house_reg",
        "displayText": "ทะเบียนบ้าน",
    },
    # Row 1
    {
        "icon": "รถ",
        "label": "ใบขับขี่",
        "bg": (255, 215, 185),   # peach pastel
        "action_type": "postback",
        "data": "action=driving_license",
        "displayText": "ใบขับขี่",
    },
    {
        "icon": "DOC",
        "label": "เอกสารสำคัญ",
        "bg": (225, 200, 255),   # lavender pastel
        "action_type": "postback",
        "data": "action=important_doc_1",
        "displayText": "เอกสารสำคัญ",
    },
    {
        "icon": "DOC",
        "label": "เอกสารสำคัญ",
        "bg": (255, 200, 215),   # pink pastel
        "action_type": "postback",
        "data": "action=important_doc_2",
        "displayText": "เอกสารสำคัญ",
    },
]


# ─────────────────────────────────────────────────────────────
# Image Generation
# ─────────────────────────────────────────────────────────────

def _get_font(size: int, bold: bool = False):
    from PIL import ImageFont

    bold_candidates = [
        r"C:\Windows\Fonts\LeelaUIb.ttf",
        r"C:\Windows\Fonts\leelawuib.ttf",
        r"C:\Windows\Fonts\THSarabunNew Bold.ttf",
        r"C:\Windows\Fonts\tahomabd.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
    ]
    regular_candidates = [
        r"C:\Windows\Fonts\LeelawUI.ttf",
        r"C:\Windows\Fonts\leelawui.ttf",
        r"C:\Windows\Fonts\Leelawad.ttf",
        r"C:\Windows\Fonts\THSarabunNew.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/thai/Garuda.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    candidates = bold_candidates if bold else regular_candidates
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_text_center(draw, text, cx, cy, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text((cx - w // 2, cy - h // 2), text, font=font, fill=fill)


def _darken(color: tuple, factor: float = 0.6) -> tuple:
    return tuple(int(c * factor) for c in color)


def _draw_shadow_rect(img, x0, y0, x1, y1, radius=30, shadow_offset=18, shadow_blur=28, shadow_alpha=80):
    """วาด drop shadow ใต้ rectangle"""
    from PIL import Image, ImageFilter
    shadow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_layer)
    sx0, sy0 = x0 + shadow_offset, y0 + shadow_offset
    sx1, sy1 = x1 + shadow_offset, y1 + shadow_offset
    sd.rounded_rectangle([sx0, sy0, sx1, sy1], radius=radius, fill=(0, 0, 0, shadow_alpha))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(shadow_blur))
    img.paste(Image.new("RGB", img.size, (240, 240, 248)),
              mask=shadow_layer.split()[3])


def _draw_gradient_rect(draw, x0, y0, x1, y1, color_top, color_bot):
    """วาด vertical gradient rectangle"""
    h = y1 - y0
    for dy in range(h):
        t = dy / h
        r = int(color_top[0] + (color_bot[0] - color_top[0]) * t)
        g = int(color_top[1] + (color_bot[1] - color_top[1]) * t)
        b = int(color_top[2] + (color_bot[2] - color_top[2]) * t)
        draw.line([(x0, y0 + dy), (x1, y0 + dy)], fill=(r, g, b))


def generate_image(output_path: str = OUTPUT_PATH) -> str:
    from PIL import Image, ImageDraw, ImageFilter

    BG_COLOR   = (235, 236, 242)
    GRID_W     = 8
    GRID_COLOR = (255, 255, 255)
    CIRCLE_R   = 205
    PAD        = 40          # inset padding per cell (raised card effect)
    RADIUS     = 36
    TEXT_COLOR = (45, 45, 58)

    img  = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_icon  = _get_font(120, bold=True)
    font_label = _get_font(88)

    for i, cell in enumerate(CELLS):
        row = i // COLS
        col = i % COLS

        x0 = COL_X[col];  x1 = COL_X[col + 1]
        y0 = ROW_Y[row];  y1 = ROW_Y[row + 1]
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2

        bg  = cell["bg"]
        # top is slightly lighter, bottom slightly darker → raised look
        bg_top = tuple(min(255, int(c * 1.08)) for c in bg)
        bg_bot = tuple(int(c * 0.88) for c in bg)

        # card inset
        cx0, cy0 = x0 + PAD, y0 + PAD
        cx1, cy1 = x1 - PAD, y1 - PAD
        card_cx   = (cx0 + cx1) // 2
        card_cy   = (cy0 + cy1) // 2

        # ── Drop shadow (painted on base layer) ──
        shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle([cx0 + 14, cy0 + 18, cx1 + 14, cy1 + 18],
                              radius=RADIUS, fill=(0, 0, 0, 90))
        shadow = shadow.filter(ImageFilter.GaussianBlur(22))
        img.paste(Image.new("RGB", img.size, BG_COLOR), mask=shadow.split()[3])

        # ── Gradient card background ──
        _draw_gradient_rect(draw, cx0, cy0, cx1, cy1, bg_top, bg_bot)
        draw.rounded_rectangle([cx0, cy0, cx1, cy1], radius=RADIUS,
                                outline=_darken(bg, 0.78), width=5)

        # ── Top highlight line (makes card look raised) ──
        draw.rounded_rectangle([cx0 + 5, cy0 + 5, cx1 - 5, cy0 + 22],
                                radius=RADIUS,
                                fill=tuple(min(255, int(c * 1.25)) for c in bg))

        # ── Circle shadow ──
        cir_cy = card_cy - 55
        cshadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        csd = ImageDraw.Draw(cshadow)
        csd.ellipse([card_cx - CIRCLE_R + 10, cir_cy - CIRCLE_R + 14,
                     card_cx + CIRCLE_R + 10, cir_cy + CIRCLE_R + 14],
                    fill=(0, 0, 0, 70))
        cshadow = cshadow.filter(ImageFilter.GaussianBlur(16))
        img.paste(Image.new("RGB", img.size, bg_bot), mask=cshadow.split()[3])

        # ── Circle (white, raised) ──
        draw.ellipse([card_cx - CIRCLE_R, cir_cy - CIRCLE_R,
                      card_cx + CIRCLE_R, cir_cy + CIRCLE_R],
                     fill=(255, 255, 255),
                     outline=_darken(bg, 0.72), width=6)

        # ── Glossy highlight on circle ──
        hr = int(CIRCLE_R * 0.55)
        draw.ellipse([card_cx - hr, cir_cy - CIRCLE_R + 18,
                      card_cx + hr, cir_cy - CIRCLE_R + 18 + hr],
                     fill=(255, 255, 255, 160) if hasattr(draw, 'ellipse') else (255, 255, 255))

        # ── Icon text ──
        icon_color = _darken(bg, 0.52)
        _draw_text_center(draw, cell["icon"], card_cx, cir_cy, font_icon, fill=icon_color)

        # ── Thai label ──
        label_y = cir_cy + CIRCLE_R + 72
        _draw_text_center(draw, cell["label"], card_cx, label_y, font_label, fill=TEXT_COLOR)

    # ── Grid lines ──
    for c in range(1, COLS):
        draw.line([(COL_X[c], 0), (COL_X[c], HEIGHT)], fill=GRID_COLOR, width=GRID_W)
    for r in range(1, ROWS):
        draw.line([(0, ROW_Y[r]), (WIDTH, ROW_Y[r])], fill=GRID_COLOR, width=GRID_W)

    img.save(output_path, "JPEG", quality=92, optimize=True)
    size_kb = os.path.getsize(output_path) // 1024
    print(f"[OK] save: {output_path} ({WIDTH}x{HEIGHT}px, {size_kb} KB)")
    return output_path


# ─────────────────────────────────────────────────────────────
# LINE Messaging API helpers
# ─────────────────────────────────────────────────────────────

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _require_token() -> str:
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        print("[ERR] LINE_CHANNEL_ACCESS_TOKEN not set in .env")
        sys.exit(1)
    return token


def _build_action(cell: dict) -> dict:
    if cell["action_type"] == "liff":
        liff_url = os.getenv("LIFF_URL", "")
        if liff_url:
            return {"type": "uri", "uri": liff_url}
        return {"type": "postback", "data": "action=open_liff", "displayText": "บันทึกเสียง"}
    return {
        "type": "postback",
        "data": cell["data"],
        "displayText": cell["displayText"],
    }


def create_rich_menu(token: str) -> str:
    areas = []
    for i, cell in enumerate(CELLS):
        row = i // COLS
        col = i % COLS
        areas.append({
            "bounds": {
                "x": COL_X[col],
                "y": ROW_Y[row],
                "width": CELL_W[col],
                "height": CELL_H[row],
            },
            "action": _build_action(cell),
        })

    menu = {
        "size": {"width": WIDTH, "height": HEIGHT},
        "selected": True,
        "name": "nong-kep-hai-menu",
        "chatBarText": "เมนูน้องเก็บให้",
        "areas": areas,
    }

    r = requests.post(
        f"{LINE_API}/richmenu",
        headers={**_headers(token), "Content-Type": "application/json"},
        json=menu,
        timeout=15,
    )
    r.raise_for_status()
    menu_id = r.json()["richMenuId"]
    print(f"[OK] create richMenuId: {menu_id}")
    return menu_id


def upload_image(token: str, menu_id: str, image_path: str):
    with open(image_path, "rb") as f:
        data = f.read()
    r = requests.post(
        f"{LINE_DATA_API}/richmenu/{menu_id}/content",
        headers={**_headers(token), "Content-Type": "image/jpeg"},
        data=data,
        timeout=30,
    )
    r.raise_for_status()
    print(f"[OK] upload image -> {menu_id}")


def set_default_menu(token: str, menu_id: str):
    r = requests.post(
        f"{LINE_API}/user/all/richmenu/{menu_id}",
        headers=_headers(token),
        timeout=15,
    )
    r.raise_for_status()
    print(f"[OK] set default menu: {menu_id}")


def list_menus(token: str):
    r = requests.get(f"{LINE_API}/richmenu/list", headers=_headers(token), timeout=15)
    r.raise_for_status()
    menus = r.json().get("richmenus", [])
    if not menus:
        print("ไม่มี Rich Menu")
        return
    for m in menus:
        print(f"  {m['richMenuId']}  name={m.get('name')}  selected={m.get('selected')}")


def delete_menu(token: str, menu_id: str):
    r = requests.delete(
        f"{LINE_API}/richmenu/{menu_id}", headers=_headers(token), timeout=15
    )
    r.raise_for_status()
    print(f"[OK] deleted: {menu_id}")


def delete_all_menus(token: str):
    requests.delete(f"{LINE_API}/user/all/richmenu", headers=_headers(token), timeout=15)
    r = requests.get(f"{LINE_API}/richmenu/list", headers=_headers(token), timeout=15)
    r.raise_for_status()
    for m in r.json().get("richmenus", []):
        delete_menu(token, m["richMenuId"])


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def cmd_image():
    generate_image()


def cmd_deploy():
    token = _require_token()
    image_path = generate_image()
    menu_id = create_rich_menu(token)
    upload_image(token, menu_id, image_path)
    set_default_menu(token, menu_id)
    print(f"\n[DONE] Deploy OK! richMenuId = {menu_id}")
    print(f"       save to .env: RICH_MENU_ID={menu_id}")


def cmd_upload(image_path: str = OUTPUT_PATH):
    if not os.path.exists(image_path):
        print(f"[ERR] ไม่พบไฟล์: {image_path}")
        sys.exit(1)
    token = _require_token()
    size_kb = os.path.getsize(image_path) // 1024
    print(f"[OK] ใช้รูป: {image_path} ({size_kb} KB)")
    menu_id = create_rich_menu(token)
    upload_image(token, menu_id, image_path)
    set_default_menu(token, menu_id)
    print(f"\n[DONE] Deploy OK! richMenuId = {menu_id}")
    print(f"       save to .env: RICH_MENU_ID={menu_id}")


def cmd_list():
    list_menus(_require_token())


def cmd_delete(menu_id: str):
    delete_menu(_require_token(), menu_id)


def cmd_delete_all():
    confirm = input("⚠️  ลบ Rich Menu ทั้งหมด? (y/N): ").strip().lower()
    if confirm == "y":
        delete_all_menus(_require_token())
    else:
        print("ยกเลิก")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0].lower()
    if cmd == "image":
        cmd_image()
    elif cmd == "deploy":
        cmd_deploy()
    elif cmd == "upload":
        cmd_upload(args[1] if len(args) >= 2 else OUTPUT_PATH)
    elif cmd == "list":
        cmd_list()
    elif cmd == "delete" and len(args) >= 2:
        cmd_delete(args[1])
    elif cmd == "delete-all":
        cmd_delete_all()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
