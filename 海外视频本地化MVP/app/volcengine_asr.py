"""火山语音 ASR（可选）。未配置时返回空转写，由豆包视频理解补全。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .doubao_config import doubao_config


def transcribe_media(path: Path | None) -> dict[str, Any]:
    cfg = doubao_config()
    if not path or not path.is_file():
        return {
            "provider": "none",
            "full_transcript": "",
            "segments": [],
            "message": "无本地音视频文件",
        }
    if not cfg["asr_enabled"] or not cfg["asr_configured"]:
        return {
            "provider": "none",
            "full_transcript": "",
            "segments": [],
            "message": "未配置 VOLCENGINE_ASR_*，跳过 ASR",
        }
    # 预留：接入火山录音文件识别后在此实现
    return {
        "provider": "volcengine_asr",
        "full_transcript": "",
        "segments": [],
        "message": "ASR 接口待配置集群 ID（见 docs/豆包详细视频分解接入指南.md）",
    }
