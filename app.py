import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse

# pip install "realtimetts[kokoro]" fastapi uvicorn
from RealtimeTTS import TextToAudioStream, KokoroEngine

app = FastAPI(title="RealtimeTTS + Kokoro (Preload, Multi-language)")

# ====== CACHE NHIỀU ENGINE THEO LANG ======
ENGINES: Dict[str, KokoroEngine] = {}
ENGINE_LOCK = asyncio.Lock()

# Tùy bạn định nghĩa các lang hot để preload (ví dụ: 'a'=American, 'b'=British, ...).
PRELOAD_LANGS = ["a", "b"]

async def get_engine(lang_code: str) -> KokoroEngine:
    # Lấy engine theo lang; nếu chưa có thì tạo (lazy) và cache.
    if lang_code in ENGINES:
        return ENGINES[lang_code]
    async with ENGINE_LOCK:
        # Double-check trong lock
        if lang_code not in ENGINES:
            ENGINES[lang_code] = KokoroEngine(lang_code=lang_code)
            print(f"[LazyLoad] KokoroEngine loaded for lang_code='{lang_code}'")
        return ENGINES[lang_code]
    
@asynccontextmanager
async def lifespan():
    async with ENGINE_LOCK:
        for lang in PRELOAD_LANGS:
            if lang not in ENGINES:
                ENGINES[lang] = KokoroEngine(lang_code=lang)
                print(f"[Startup] Preloaded KokoroEngine for lang_code='{lang}'")
    print("[Startup] All preloads done.")
    yield
    async with ENGINE_LOCK:
        ENGINES.clear()
    print("[Shutdown] Engines cache cleared.")

    

# ====== STREAMING HANDLER ======
async def stream_tts_bytes(text: str, voice: str, speed: float, lang: str) -> AsyncGenerator[bytes, None]:
    """
    Stream audio bytes PCM s16le 24kHz từ RealtimeTTS (engine Kokoro).
    """
    engine = await get_engine(lang)

    q: asyncio.Queue[bytes] = asyncio.Queue()
    done = asyncio.Event()

    def on_chunk(b: bytes):
        q.put_nowait(b)

    def on_stop():
        done.set()

    # Tạo stream per-request, tái sử dụng engine theo lang
    stream = TextToAudioStream(
        engine=engine,
        muted=True,
        on_audio_stream_stop=on_stop,
    )

    # Lưu ý: truyền voice/speed per-utterance (engine đã cố định lang)
    stream.play_async(
        buffer_threshold_seconds=0.0,
        on_audio_chunk=on_chunk,
        voice=voice,
        speed=speed,
    )
    stream.feed(text)

    while True:
        if done.is_set() and q.empty():
            break
        try:
            chunk = await asyncio.wait_for(q.get(), timeout=0.1)
            yield chunk
        except asyncio.TimeoutError:
            continue

# ====== API ======
@app.get("/tts")
async def tts(
    text: str = Query(..., min_length=1, description="Nội dung cần đọc"),
    voice: str = Query("af_heart", description="Mã giọng Kokoro (phải khớp lang)"),
    lang: str = Query("a", description="Mã ngôn ngữ/model của Kokoro, ví dụ: 'a' (American), 'b' (British)"),
    speed: float = Query(1.0, ge=0.5, le=2.0, description="Tốc độ đọc 0.5–2.0"),
):
    generator = stream_tts_bytes(text=text, voice=voice, speed=speed, lang=lang)
    return StreamingResponse(
        generator,
        media_type="audio/pcm",
        headers={
            "X-Audio-Sample-Rate": "24000",
            "X-Audio-Codec": "s16le",
            "X-Audio-Channels": "1",
        },
    )


if "__name__" == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=1006,
        # ssl_keyfile="ssl/key.pem",
        # ssl_certfile="ssl/cert.pem",
    )
