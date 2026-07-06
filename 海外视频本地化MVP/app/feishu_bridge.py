"""飞书 CLI 状态探测（可选集成；未安装时返回明确说明而非 404）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

WORKFLOW_ROOT = Path(__file__).resolve().parents[2]
FEISHU_CLI_DIR = WORKFLOW_ROOT / "tools" / "feishu-cli"


def feishu_status_payload() -> dict[str, Any]:
    if not FEISHU_CLI_DIR.is_dir():
        return {
            "integrated": False,
            "installed": False,
            "configured": False,
            "authenticated": False,
            "message": "工作台未集成飞书 CLI。如需使用请运行根目录「配置飞书CLI.cmd」。",
        }
    version = "@larksuite/cli"
    pkg = FEISHU_CLI_DIR / "package.json"
    if pkg.is_file():
        try:
            version = json.loads(pkg.read_text(encoding="utf-8")).get("name", version)
        except (json.JSONDecodeError, OSError):
            pass
    configured = any(
        (FEISHU_CLI_DIR / name).is_file() for name in (".env", "config.json", "lark-cli.config.json")
    )
    return {
        "integrated": True,
        "installed": True,
        "configured": configured,
        "authenticated": False,
        "version": version,
        "package_version": version,
        "message": "已检测到 tools/feishu-cli。请在终端运行「配置飞书CLI.cmd」完成授权。",
    }


def feishu_auth_url_payload() -> dict[str, Any]:
    st = feishu_status_payload()
    if not st.get("integrated"):
        return {
            "ok": False,
            "message": st.get("message", "飞书 CLI 未安装"),
            "stdout": "",
            "stderr": "",
            "json": None,
        }
    return {
        "ok": False,
        "message": "请在项目根目录运行「配置飞书CLI.cmd」生成授权链接（浏览器内暂不支持 CLI 交互）。",
        "stdout": "",
        "stderr": "",
        "json": None,
    }


def feishu_doctor_payload(*, offline: bool = True) -> dict[str, Any]:
    st = feishu_status_payload()
    if not st.get("integrated"):
        return {
            "ok": False,
            "message": st.get("message", "飞书 CLI 未安装"),
            "stdout": "",
            "stderr": "",
            "json": st,
        }
    return {
        "ok": configured_ok(st),
        "message": st.get("message", ""),
        "stdout": json.dumps(st, ensure_ascii=False, indent=2),
        "stderr": "",
        "json": st,
    }


def configured_ok(st: dict[str, Any]) -> bool:
    return bool(st.get("configured"))
