import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from quart import Quart, render_template, request, jsonify, send_file, websocket, url_for, redirect
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
import aiofiles
from PIL import Image

from models import Base, Photo

APP_DIR = Path(__file__).resolve().parent
MEDIA_DIR = APP_DIR / "media"
ORIG_DIR = MEDIA_DIR / "originals"
THUMB_DIR = MEDIA_DIR / "thumbs"
DB_URL = "sqlite+aiosqlite:///" + str(APP_DIR / "app.db")

for d in (MEDIA_DIR, ORIG_DIR, THUMB_DIR):
    d.mkdir(parents=True, exist_ok=True)

app = Quart(__name__, static_folder="static", static_url_path="/static")
engine = create_async_engine(DB_URL, echo=False, future=True)
Session = async_sessionmaker(engine, expire_on_commit=False)

# --- WebSocket: 接続中クライアント管理 ---
clients = set()

@app.websocket("/ws")
async def ws():
    clients.add(websocket._get_current_object())
    try:
        while True:
            # クライアントからのメッセージは特に使わない（ping用途）
            await websocket.receive()
    except Exception:
        pass
    finally:
        clients.discard(websocket._get_current_object())

async def broadcast(event: dict):
    if not clients:
        return
    dead = []
    for ws in list(clients):
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)

# --- ユーティリティ ---
ALLOWED = {"image/jpeg", "image/png", "image/webp"}

def secure_name(name: str) -> str:
    # 超シンプル版
    name = os.path.basename(name).replace(" ", "_")
    return "".join(c for c in name if c.isalnum() or c in ("_", "-", "."))

async def save_thumbnail(src_path: Path, dst_path: Path, size=(480, 480)):
    loop = asyncio.get_running_loop()
    def _make_thumb():
        with Image.open(src_path) as im:
            im.thumbnail(size)
            im.save(dst_path)
    await loop.run_in_executor(None, _make_thumb)

# --- ルーティング ---
@app.before_serving
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
async def index():
    async with Session() as s:
        res = await s.execute(select(Photo).order_by(Photo.id.desc()))
        photos = res.scalars().all()
    return await render_template("index.html", photos=photos)

@app.get("/upload")
async def upload_form():
    return await render_template("upload.html")

@app.post("/upload")
async def upload_post():
    form = await request.form
    title = form.get("title", "")
    file = (await request.files).get("file")
    if not file:
        return jsonify({"error": "no file"}), 400
    if file.mimetype not in ALLOWED:
        return jsonify({"error": "unsupported type"}), 415

    safe = secure_name(file.filename) or f"photo_{int(datetime.utcnow().timestamp())}.jpg"
    orig_path = ORIG_DIR / safe
    thumb_path = THUMB_DIR / safe

    # 保存
    async with aiofiles.open(orig_path, "wb") as f:
        await f.write(file.read())

    # サムネ生成
    await save_thumbnail(orig_path, thumb_path)

    # DB
    async with Session() as s:
        p = Photo(filename=safe, title=title, mime=file.mimetype)
        s.add(p)
        await s.commit()
        await s.refresh(p)

    # ブロードキャスト
    await broadcast({
        "type": "new_photo",
        "id": p.id,
        "thumb_url": url_for("thumb", filename=p.filename),
        "title": p.title,
    })

    # フォームからは一覧へ
    if request.headers.get("HX-Request"):
        return jsonify({"ok": True, "id": p.id})
    return redirect(url_for("index"))

@app.get("/media/thumbs/<path:filename>")
async def thumb(filename):
    path = THUMB_DIR / filename
    if not path.exists():
        return {"error": "not found"}, 404
    return await send_file(path)

@app.get("/media/originals/<path:filename>")
async def original(filename):
    path = ORIG_DIR / filename
    if not path.exists():
        return {"error": "not found"}, 404
    return await send_file(path)

if __name__ == "__main__":
    app.run(debug=True, port=8000)