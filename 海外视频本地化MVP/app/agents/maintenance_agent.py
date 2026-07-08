"""维护 Agent：只读安全检查包装。不改任何文件，只跑已有的只读校验脚本
（出稿规则验证、部署包校验、清理预检）并把结果套进 Agent 状态格式。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .contracts import AgentName, AgentState, TaskStatus

MVP_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = MVP_ROOT / "scripts"


def _run_readonly_script(script_name: str, *, timeout: int = 60) -> tuple[bool, str]:
    """跑一个只读校验脚本，返回 (ok, 输出尾部)。任何异常都当作 ok=False，不抛出。"""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.is_file():
        return False, f"脚本不存在: {script_path}"
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(MVP_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()
        return proc.returncode == 0, "\n".join(tail[-6:])
    except subprocess.TimeoutExpired:
        return False, f"{script_name} 运行超时（{timeout}s）"
    except Exception as exc:
        return False, f"{script_name} 运行异常: {exc}"


def evaluate() -> AgentState:
    warnings: list[str] = []
    refs: list[str] = []

    ok_skill, tail_skill = _run_readonly_script("validate_output_standards_skill.py")
    refs.append(f"validate_output_standards_skill: {'PASS' if ok_skill else 'FAIL'}")
    if not ok_skill:
        warnings.append(f"出稿规则验证未全过：{tail_skill or '详见 validate_output_standards_skill.py 输出'}")

    ok_deploy, tail_deploy = _run_readonly_script("verify_deploy_repo.py")
    refs.append(f"verify_deploy_repo: {'PASS' if ok_deploy else 'FAIL'}")
    if not ok_deploy:
        warnings.append(f"部署包校验未全过：{tail_deploy or '详见 verify_deploy_repo.py 输出'}")

    ok_preflight, tail_preflight = _run_readonly_script("preflight_cleanup.py")
    refs.append(f"preflight_cleanup: {'PASS' if ok_preflight else 'FAIL'}")
    if not ok_preflight:
        warnings.append(f"清理预检发现需要人工确认的差异：{tail_preflight or '详见 preflight_cleanup.py 输出'}")

    status = TaskStatus.SUCCEEDED if not warnings else TaskStatus.NEEDS_REVIEW
    summary = "只读检查全部通过" if not warnings else f"只读检查发现 {len(warnings)} 项需要关注（均不阻断，仅提示）"

    return AgentState(
        agent=AgentName.MAINTENANCE,
        status=status,
        ready=True,
        warnings=warnings,
        next_suggestion="" if not warnings else "有空时看一眼上面几项提示，不影响日常使用",
        detail={"summary": summary, "refs": refs},
    )
