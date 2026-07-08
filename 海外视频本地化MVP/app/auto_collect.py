"""后台定时采集：服务进程活着就按周期抓取热点视频，不依赖网页是否打开。

默认关闭。开启方式（海外视频本地化MVP/.env）：
  AUTO_COLLECT_ENABLED=1
  AUTO_COLLECT_INTERVAL_HOURS=6        # 每轮间隔，默认 6 小时
  AUTO_COLLECT_PRODUCT_IDS=吸奶器,便携恒温杯   # 留空则抓全部已配置产品

注意：TikTok 采集仍然需要真实浏览器窗口完成登录/验证码（非 headless）。
后台定时任务只是替你按周期点「采集并整理」，第一次仍需人工在弹出的
Chrome 里完成一次 TikTok 登录，之后复用已保存的登录态。
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from fastapi.concurrency import run_in_threadpool

from .hotspot_refresh import PRODUCT_COLLECTOR_KEYWORDS
from .material_maintenance import run_one_click_collect

_STAGGER_SECONDS = 30


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except ValueError:
        return default


def auto_collect_enabled() -> bool:
    return _env_bool("AUTO_COLLECT_ENABLED", False)


def auto_collect_interval_seconds() -> int:
    hours = max(1, _env_int("AUTO_COLLECT_INTERVAL_HOURS", 6))
    return hours * 3600


def auto_collect_product_ids() -> list[str]:
    raw = os.getenv("AUTO_COLLECT_PRODUCT_IDS", "").strip()
    if raw:
        return [p.strip() for p in raw.split(",") if p.strip()]
    return list(PRODUCT_COLLECTOR_KEYWORDS.keys())


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


async def _run_one_product(product_id: str) -> None:
    try:
        from tiktok_collector.browser_launch import collector_launch_blocked_reason

        blocked = collector_launch_blocked_reason()
        if blocked:
            print(f"[auto-collect] {_utc_now()} 跳过「{product_id}」：{blocked}")
            return
    except Exception as exc:
        print(f"[auto-collect] {_utc_now()} 跳过「{product_id}」：采集环境检查失败 {exc}")
        return

    try:
        report = await run_in_threadpool(run_one_click_collect, product_id=product_id, limit_per_keyword=20)
        print(f"[auto-collect] {_utc_now()} 「{product_id}」: {report.get('message', '')}")
    except Exception as exc:
        print(f"[auto-collect] {_utc_now()} 「{product_id}」采集异常: {exc}")


async def auto_collect_loop() -> None:
    interval = auto_collect_interval_seconds()
    print(
        f"[auto-collect] 后台定时采集已启动：每 {interval // 3600} 小时一轮，"
        f"产品：{', '.join(auto_collect_product_ids()) or '（未配置）'}"
    )
    while True:
        for product_id in auto_collect_product_ids():
            await _run_one_product(product_id)
            await asyncio.sleep(_STAGGER_SECONDS)
        await asyncio.sleep(interval)


def start_auto_collect_if_enabled() -> "asyncio.Task | None":
    if not auto_collect_enabled():
        return None
    return asyncio.create_task(auto_collect_loop())
