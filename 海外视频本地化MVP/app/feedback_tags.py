"""反馈结构化问题标签（无依赖，供 library / loop / UI 共用）。"""
from __future__ import annotations

ISSUE_TAG_DEFS: dict[str, dict[str, str]] = {
    "product_structure": {
        "label": "产品结构",
        "hint_zh": "产品外观与结构须严格对照白底主图与细节图，禁止改造型、改盖型、改倒出口/按键布局",
        "hint_en": "Match white-background hero and detail refs exactly; no redesign, wrong lid type, or wrong spout layout",
    },
    "scene_mismatch": {
        "label": "场景偏差",
        "hint_zh": "环境、道具与产品摆放须严格对照所选场景图，禁止跨场景混用或未选场景元素",
        "hint_en": "Environment and props must match the selected scenario reference; no cross-scene mixing",
    },
    "physics_logic": {
        "label": "物理逻辑",
        "hint_zh": "倒液方向、倾斜角度、重力与容器分离关系须符合真实物理与批准用法",
        "hint_en": "Pour direction, tilt, gravity, and container separation must be physics-safe and usage-correct",
    },
    "usage_flow": {
        "label": "用法流程",
        "hint_zh": "开盖、进液、加热、倒出等步骤须按场景图与用法参考顺序演示",
        "hint_en": "Open, fill, warm, pour steps must follow approved usage-step and scenario references",
    },
    "person_inconsistent": {
        "label": "人物不一致",
        "hint_zh": "同一视频内人物年龄、服饰、发型、肤色、手部须前后一致",
        "hint_en": "Same person identity across all shots: age, wardrobe, hair, skin tone, hands",
    },
    "product_appearance": {
        "label": "外观偏差",
        "hint_zh": "产品颜色、比例、Logo 区、数显须与白底主图一致，禁止私自改色或简化",
        "hint_en": "Color, proportions, logo zone, display must match white-background hero; no recolor or simplification",
    },
    "lighting_unreal": {
        "label": "光影失真",
        "hint_zh": "光影须有动机且真实，但不得借光影掩盖产品变形或错误结构",
        "hint_en": "Motivated realistic lighting without hiding product shape errors",
    },
}

ISSUE_TAG_IDS = tuple(ISSUE_TAG_DEFS.keys())

ADOPTED_FOR_LOOP = frozenset({"已采纳", "修改后采纳"})
