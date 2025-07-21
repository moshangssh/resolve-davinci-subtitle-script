from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .core.dependencies import get_subtitle_manager
from .services.subtitle_manager import SubtitleManager

app = FastAPI(
    title="Subvigator Next Backend",
    description="为 Subvigator Next 提供核心业务逻辑的 FastAPI 服务。",
    version="0.1.0",
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/test")
def test_endpoint():
    """
    一个简单的测试端点，用于验证前后端通信。
    """
    return {"message": "🎉 Hello from FastAPI backend! The connection is successful! 🎉"}

@app.get("/api/subtitles")
def get_subtitles(subtitle_manager: SubtitleManager = Depends(get_subtitle_manager)):
    """
    获取当前轨道的所有字幕（使用模拟数据）。
    """
    return subtitle_manager.get_all_subtitles()