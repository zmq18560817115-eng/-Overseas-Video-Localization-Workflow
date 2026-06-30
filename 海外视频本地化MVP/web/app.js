const state = {
  view: "generate",
  draftFeedbackSub: "finished",
  feedbackEditorTab: "review",
  items: [],
  products: [],
  templates: [],
  selectedMaterialId: null,
  selectedProductId: null,
  selectedFeedbackSlug: null,
  feedbackTagDefs: null,
  scriptSlug: null,
  showAllMaterials: false,
  selectedAudience: [],
  selectedScenarios: [],
  lastPreview: null,
  tagPoolExtra: { audience: [], scenarios: [], selling: [], pains: [] },
  tagSelection: { audience: [], scenarios: [], selling: [], pains: [] },
  filters: { category: "", q: "", analyzedOnly: true },
  jobPoll: null,
  healthCache: null,
  scriptStep: "product",
  generateStudioTab: "featured",
  selectedScenarioFeature: null,
  generateWorkspaceOpen: false,
  pendingScenarioTag: null,
  createPipelineActive: false,
  seedanceProgressPersist: false,
  scriptTagSnapshot: null,
  lastScriptProductId: null,
  videoSettings: {
    resolution: "720P",
    aspectRatio: "9:16",
    durationSec: 5,
    generateCount: 1,
    editMode: "multi_shot",
  },
  promptEnhanceOn: false,
  promptEnhanceUsed: false,
};

const VIDEO_RESOLUTIONS = ["720P", "1080P"];
const VIDEO_ASPECT_RATIOS = ["9:16", "16:9", "1:1", "3:4", "4:3"];
const VIDEO_DURATIONS = [5, 10, 20];
const GENERATE_COUNTS = [1, 2, 3, 4];

const JOB_LABELS = {
  discover: "发现候选",
  promote: "筛选入库",
  fetch: "同步 TikTok",
  decompose: "结构拆解",
  templates: "更新模板",
  products: "同步产品资料",
  links: "生成链接表",
  "cache-thumbnails": "缓存封面图",
};

function jobLabel(name) {
  return JOB_LABELS[name] || name || "";
}

const SCENARIO_GROUPS = [
  { id: "bedroom", keys: ["卧室", "夜间", "夜奶"] },
  { id: "car", keys: ["车内", "杯架"] },
  { id: "travel", keys: ["机场", "旅途", "长途"] },
  { id: "outdoor", keys: ["公园", "遛娃"] },
  { id: "office", keys: ["办公室", "背奶"] },
  { id: "public", keys: ["餐厅", "商场", "临时冲奶"] },
];

const GENERATE_FEATURES = [
  { id: "bedroom", label: "夜间场景", sub: "卧室 · 夜奶", grad: "g-bedroom", scenarioTag: "卧室" },
  { id: "car", label: "车载场景", sub: "杯架 · 通勤", grad: "g-car", scenarioTag: "车内" },
  { id: "travel", label: "旅途场景", sub: "机场 · 长途", grad: "g-travel", scenarioTag: "机场" },
  { id: "office", label: "办公场景", sub: "背奶 · 工位", grad: "g-office", scenarioTag: "办公室" },
  { id: "outdoor", label: "户外遛娃", sub: "公园 · 出行", grad: "g-outdoor", scenarioTag: "公园" },
  { id: "public", label: "商场餐厅", sub: "临时冲奶", grad: "g-public", scenarioTag: "商场" },
];

const IMITATE_FEATURES = [
  { id: "extract", label: "原视频提取", sub: "拉取对标结构", grad: "g-extract", planned: true },
  { id: "template", label: "套结构模板", sub: "镜头语言复用", grad: "g-template", planned: true },
  { id: "brand", label: "品牌脚本套用", sub: "一键出模仿稿", grad: "g-brand", planned: true },
];

const REVERSE_FEATURES = [
  { id: "video-rev", label: "视频反推", sub: "拆镜头 → Prompt", grad: "g-video-rev", planned: true },
  { id: "script-rev", label: "脚本反推", sub: "拆解脚本结构", grad: "g-script-rev", planned: true },
];

const DRAFT_FEEDBACK_FEATURES = [
  { id: "finished", label: "成稿库", sub: "已交付成片", grad: "g-finished", action: "finished" },
  { id: "feedback", label: "反馈库", sub: "投放数据记录", grad: "g-feedback", action: "feedback" },
  { id: "iterate", label: "迭代优化", sub: "反哺下一轮", grad: "g-iterate", action: "audit", planned: true },
];

function scenarioConflictNote(tags) {
  const groups = [];
  for (const tag of tags || []) {
    const g = SCENARIO_GROUPS.find((x) => x.keys.some((k) => tag.includes(k)));
    if (g && !groups.includes(g.id)) groups.push(g.id);
  }
  if (groups.length <= 1) return "";
  return `已选多个互斥场景，成片将统一按「${tags[0]}」生成，避免卧室/车载等画面冲突。`;
}

const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[c]));

const ANALYSIS_LABELS = {
  hook_3s: "钩子 0-3秒",
  pain_points: "痛点",
  selling_points: "卖点",
  video_structure: "视频结构",
  reusable_template: "可复用模板",
};

const CATEGORY_ZH = {
  bottle_warmer: "便携暖奶/恒温杯",
  breast_pump: "吸奶器",
};

/** 产品资料展示：优先中文段落，口播/英文字段另列 */
function chineseText(text) {
  return parseTagList(text).join("；") || String(text || "");
}

function parseTagList(text) {
  return String(text || "")
    .split(/[；;、\n，,]/)
    .map((s) => s.trim())
    .filter((s) => s.length >= 2 && /[\u4e00-\u9fff]/.test(s));
}

const TAG_GROUPS = {
  audience: {
    field: "target_audience",
    poolKey: "audience",
    savedKey: "audience",
    label: "目标人群",
    placeholder: "输入人群标签，如：夜奶家庭",
  },
  scenario: {
    field: "usage_scenarios",
    poolKey: "scenarios",
    savedKey: "scenarios",
    label: "投放场景",
    placeholder: "输入场景标签，如：车内杯架",
    single: true,
  },
  selling: {
    field: "core_selling_points",
    poolKey: "selling",
    savedKey: "selling",
    label: "核心卖点",
    placeholder: "输入卖点，如：USB-C 充电",
  },
  pain: {
    field: "pain_points",
    poolKey: "pains",
    savedKey: "pains",
    label: "用户痛点",
    placeholder: "输入痛点，如：外出没热水",
  },
};

function buildTagPool(p, apiTags) {
  const pool = {
    audience: (apiTags?.audience?.length ? apiTags.audience : parseTagList(p.target_audience)),
    scenarios: (apiTags?.scenarios?.length ? apiTags.scenarios : parseTagList(p.usage_scenarios)),
    selling: (apiTags?.selling?.length ? apiTags.selling : parseTagList(p.core_selling_points)),
    pains: (apiTags?.pains?.length ? apiTags.pains : parseTagList(p.pain_points)),
  };
  for (const key of ["audience", "scenarios", "selling", "pains"]) {
    for (const t of state.tagPoolExtra[key] || []) {
      if (!pool[key].includes(t)) pool[key].push(t);
    }
  }
  return pool;
}

function defaultSelectedTags(pool, saved) {
  const pick = (poolKey, savedKey, single = false) => {
    if (saved && Object.prototype.hasOwnProperty.call(saved, savedKey)) {
      const list = (saved[savedKey] || []).filter((t) => pool[poolKey].includes(t));
      return single ? list.slice(0, 1) : list;
    }
    const list = (saved?.[savedKey] || []).filter((t) => pool[poolKey].includes(t));
    if (list.length) return single ? list.slice(0, 1) : list;
    return pool[poolKey][0] ? [pool[poolKey][0]] : [];
  };
  return {
    audience: pick("audience", "audience"),
    scenarios: pick("scenarios", "scenarios", true),
    selling: pick("selling", "selling"),
    pains: pick("pains", "pains"),
  };
}

function readAllSelectedTags() {
  return {
    audience: [...(state.tagSelection?.audience || [])],
    scenarios: [...(state.tagSelection?.scenarios || [])],
    selling: [...(state.tagSelection?.selling || [])],
    pains: [...(state.tagSelection?.pains || [])],
  };
}

const TAG_GROUP_DOM = {
  audience: { row: "audienceTagRow", library: "audienceLibraryRow", poolKey: "audience", savedKey: "audience" },
  scenario: { row: "scenarioTagRow", library: "scenarioLibraryRow", poolKey: "scenarios", savedKey: "scenarios" },
  selling: { row: "sellingTagRow", library: "sellingLibraryRow", poolKey: "selling", savedKey: "selling" },
  pain: { row: "painTagRow", library: "painLibraryRow", poolKey: "pains", savedKey: "pains" },
};

function readSelectedTags(group) {
  const key = TAG_GROUP_DOM[group]?.savedKey;
  return key ? [...(state.tagSelection?.[key] || [])] : [];
}

function syncDockPromptFromScenarioTags() {
  const ta = document.getElementById("generateDockPrompt");
  if (!ta) return;
  const scenarios = readSelectedTags("scenario");
  ta.value = scenarios.length
    ? `${scenarios[0]}场景：展示产品在真实使用环境中的卖点与痛点，口播自然、镜头节奏对标爆款结构。`
    : "";
}

function toggleTagChip(group, value) {
  const cfg = TAG_GROUPS[group];
  const dom = TAG_GROUP_DOM[group];
  if (!cfg || !dom || !value) return;
  const key = dom.savedKey;
  let sel = [...(state.tagSelection[key] || [])];
  if (cfg.single) {
    state.tagSelection[key] = sel.includes(value) ? [] : [value];
    if (group === "scenario") syncDockPromptFromScenarioTags();
    return;
  }
  state.tagSelection[key] = sel.includes(value) ? sel.filter((t) => t !== value) : [...sel, value];
}

function refreshTagGroupsUI() {
  const pool = state.currentTagPool || { audience: [], scenarios: [], selling: [], pains: [] };
  const sel = state.tagSelection || readAllSelectedTags();
  for (const [group, dom] of Object.entries(TAG_GROUP_DOM)) {
    const picked = sel[dom.savedKey] || [];
    renderTagRow(dom.row, pool[dom.poolKey] || [], picked, group);
    renderLibraryTagRow(dom.library, pool[dom.poolKey] || [], picked, group);
  }
  const warn = document.getElementById("scenarioConflictWarn");
  if (warn) {
    const conflict = scenarioConflictNote(sel.scenarios);
    if (conflict) {
      warn.classList.remove("hidden");
      warn.textContent = conflict;
    } else {
      warn.classList.add("hidden");
      warn.textContent = "";
    }
  }
}

function formatStoryboardHtml(storyboard) {
  const shots = storyboard || [];
  if (!shots.length) return '<p class="muted">暂无分镜</p>';
  return `<div class="shot-list-compact">${shots.map((s, idx) => {
    const vo = String(s.voiceover_en || "").trim();
    const voPreview = vo.length > 72 ? `${vo.slice(0, 72)}…` : vo;
    return `
    <details class="shot-compact"${idx === 0 ? " open" : ""}>
      <summary>第 ${s.number} 镜 · ${esc(s.role || "")}（${esc(s.timing || "")}）${voPreview ? ` — ${esc(voPreview)}` : ""}</summary>
      <div class="shot-compact-body">
        <p><span class="pack-label">画面</span>${esc(s.visual || "")}</p>
        <p><span class="pack-label">口播</span>${esc(s.voiceover_en || "")}</p>
        <p><span class="pack-label">字幕</span>${esc(s.subtitle_en || "")}</p>
        ${s.visual_prompt ? `<p><span class="pack-label">构图</span>${esc(s.visual_prompt)}</p>` : ""}
        ${s.seedance_prompt ? `<p><span class="pack-label">空镜</span>${esc(s.seedance_prompt)}</p>` : ""}
      </div>
    </details>`;
  }).join("")}</div>`;
}

function formatPackResult(pack, meta) {
  const broll = (pack.seedance_prompts || []).filter(Boolean);
  const m = pack.inputs?.market || {};
  const provider = meta?.provider || pack.provider || "";
  const model = meta?.model || pack.model || "";
  const providerLine = provider === "anthropic"
    ? `脚本引擎：Claude（${esc(model || "claude")}）`
    : provider === "rule_template"
      ? "脚本引擎：规则模板（未配置 ANTHROPIC_API_KEY 或 API 失败时自动使用）"
      : "";
  const tagSummary = [
    m.audience_tags?.length ? `人群：${m.audience_tags.join("、")}` : "",
    m.scenario_tags?.length ? `场景：${m.scenario_tags.join("、")}` : "",
    m.selling_tags?.length ? `卖点：${m.selling_tags.join("、")}` : "",
    m.pain_tags?.length ? `痛点：${m.pain_tags.join("、")}` : "",
  ].filter(Boolean).join(" · ");
  const sceneNote = pack.inputs?.scenario_primary
    ? `全片统一场景：${pack.inputs.scenario_primary}`
    : "";
  const sceneWarn = pack.inputs?.scenario_conflict_note;
  const title = String(pack.title || "").trim();
  const subtitle = String(pack.subtitle || "").trim();
  const voiceover = String(pack.voiceover_20s || "").trim();
  return `
    <h3>脚本已生成</h3>
    ${providerLine ? `<p class="pack-summary-line">${providerLine}</p>` : ""}
    ${tagSummary ? `<p class="pack-summary-line">${esc(tagSummary)}</p>` : ""}
    ${sceneNote ? `<p class="pack-summary-line">${esc(sceneNote)}</p>` : ""}
    ${sceneWarn ? `<p class="workflow-warn">${esc(sceneWarn)}</p>` : ""}
    <div class="script-pack">
      ${title || subtitle || voiceover ? `
      <details class="pack-meta-details">
        <summary>标题与口播全文</summary>
        ${title ? `<div class="pack-row"><span>英文标题</span><p>${esc(title)}</p></div>` : ""}
        ${subtitle ? `<div class="pack-row"><span>英文副标题</span><p>${esc(subtitle)}</p></div>` : ""}
        ${voiceover ? `<div class="pack-row"><span>完整口播</span><p>${esc(voiceover)}</p></div>` : ""}
      </details>` : ""}
      <div class="pack-row"><span>分镜脚本（${(pack.storyboard || []).length} 镜，点击展开）</span><div class="shot-list">${formatStoryboardHtml(pack.storyboard)}</div></div>
      ${broll.length ? `<details class="pack-meta-details"><summary>空镜提示词（${broll.length} 条）</summary><pre>${esc(broll.join("\n\n"))}</pre></details>` : ""}
    </div>`;
}

function currentScriptSlug() {
  return state.scriptSlug || state.lastPreview?.slug || "";
}

function captureTagSnapshot() {
  return JSON.stringify(readAllSelectedTags());
}

function tagsChangedSinceScript() {
  if (!state.scriptTagSnapshot) return false;
  return captureTagSnapshot() !== state.scriptTagSnapshot;
}

function openFloatPanel(panelId, backdropId) {
  const panel = document.getElementById(panelId);
  const backdrop = document.getElementById(backdropId);
  if (!panel || !backdrop) return;
  panel.hidden = false;
  panel.style.display = "";
  backdrop.hidden = false;
  panel.setAttribute("aria-hidden", "false");
  requestAnimationFrame(() => {
    panel.classList.add("open");
    backdrop.classList.add("open");
  });
}

function closeFloatPanel(panelId, backdropId, afterClose) {
  const panel = document.getElementById(panelId);
  const backdrop = document.getElementById(backdropId);
  if (!panel || !backdrop) return;
  panel.classList.remove("open");
  backdrop.classList.remove("open");
  panel.setAttribute("aria-hidden", "true");
  const delay = panelId === "refFloatPanel" ? 250 : 200;
  window.setTimeout(() => {
    if (!panel.classList.contains("open")) {
      panel.hidden = true;
      panel.style.display = "none";
      backdrop.hidden = true;
      afterClose?.();
    }
  }, delay);
}

function ensureScriptResultVisible() {
  openScriptFloatPanel();
}

function syncScriptOutputSection() {
  syncDockScrollPadding();
}

function scrollScriptOutputIntoView() {
  openScriptFloatPanel();
}

let dockPadRaf = 0;
function syncDockScrollPadding() {
  if (dockPadRaf) cancelAnimationFrame(dockPadRaf);
  dockPadRaf = requestAnimationFrame(() => {
    dockPadRaf = 0;
    const dock = document.getElementById("generateDock");
    const scroll = document.querySelector('.module-studio[data-module="generate"] .module-studio-scroll');
    const studio = document.querySelector('.module-studio[data-module="generate"]');
    if (!dock || !scroll || state.view !== "generate") return;
    const h = Math.ceil(dock.getBoundingClientRect().height) + 24;
    scroll.style.paddingBottom = `${h}px`;
    studio?.style.setProperty("--dock-pad", `${h}px`);
  });
}

function syncFinishButton(canFinish, delivered) {
  const canProduce = Boolean(canFinish && currentScriptSlug());
  const runBtn = document.getElementById("generateDockRun");
  if (runBtn && !runBtn.dataset.busy) {
    runBtn.disabled = !canProduce && Boolean(state.lastPreview?.has_script) === false
      ? !tagsSelectionOk() || !state.selectedMaterialId
      : false;
    runBtn.title = canProduce || tagsSelectionOk()
      ? "生成脚本并产出 AI 分镜视频"
      : "请先配置产品与对标";
  }
}

function showSeedanceProgress(show, { status, percent, indeterminate, pipeline, persist } = {}) {
  const bar = document.getElementById("seedanceProgress");
  const statusEl = document.getElementById("seedanceProgressStatus");
  const fill = document.getElementById("seedanceProgressFill");
  const meta = document.getElementById("seedancePipelineCompact");
  const track = bar?.querySelector(".seedance-progress-track");
  if (!bar) return;

  if (persist != null) state.seedanceProgressPersist = Boolean(persist);
  if (!show && persist !== true) state.seedanceProgressPersist = false;

  const visible = Boolean(show && (state.createPipelineActive || state.seedanceProgressPersist));
  const wasVisible = !bar.classList.contains("hidden");
  bar.classList.toggle("hidden", !visible);

  if (!visible) {
    fill?.classList.remove("indeterminate");
    if (wasVisible) syncDockScrollPadding();
    return;
  }

  if (status && statusEl) statusEl.textContent = status;
  if (pipeline != null && meta) meta.textContent = pipeline;
  if (fill) {
    fill.classList.toggle("indeterminate", Boolean(indeterminate));
    if (percent != null) fill.style.width = `${Math.min(100, Math.max(0, percent))}%`;
  }
  if (track && percent != null) track.setAttribute("aria-valuenow", String(Math.round(percent)));
  if (!wasVisible) syncDockScrollPadding();
}

function renderSeedanceFinalPreview(slug, seedance) {
  const box = document.getElementById("seedanceFinalPreview");
  if (!box) return;
  const final = seedance?.final_video || {};
  if (final.ready && final.file && slug) {
    box.classList.remove("hidden");
    box.innerHTML = `<a class="seedance-final-link" href="/api/delivery/${encodeURIComponent(slug)}/files/${encodeURI(final.file)}" target="_blank">预览成片 final-video.mp4</a>`;
  } else {
    box.classList.add("hidden");
    box.innerHTML = "";
  }
}

async function runStartCreate() {
  const runBtn = document.getElementById("generateDockRun");
  const ps = document.getElementById("scriptProductSelect");
  if (ps?.value) {
    state.selectedProductId = ps.value;
    await refreshScriptPreview();
  }
  if (!tagsSelectionOk()) {
    await openProductFloatPanel();
    return;
  }
  const linkId = Number(document.getElementById("scriptMaterialSelect")?.value || state.selectedMaterialId);
  if (!linkId) {
    openRefFloatPanel();
    return;
  }

  if (runBtn) {
    runBtn.disabled = true;
    runBtn.dataset.busy = "1";
    runBtn.innerHTML = '<span class="dock-run-icon">✦</span> 创作中…';
  }

  try {
    const prev = state.lastPreview || {};
    if (!prev.has_script) {
      await runScriptGenerate();
      if (!currentScriptSlug() && !state.lastPreview?.has_script) return;
      openScriptFloatPanel();
      return;
    }
    refreshScriptFloatFromPreview(prev);
    openScriptFloatPanel();
  } finally {
    if (runBtn) {
      delete runBtn.dataset.busy;
      runBtn.disabled = false;
      runBtn.innerHTML = '<span class="dock-run-icon">✦</span> 开始创作';
    }
    syncFinishButton(Boolean(state.lastPreview?.can_finish), Boolean(state.lastPreview?.delivery_ready));
  }
}

function renderDockProduceComplete(slug, message) {
  showSeedanceProgress(true, {
    status: message || "成片已就绪",
    percent: 100,
    persist: true,
  });
  const meta = document.getElementById("seedancePipelineCompact");
  if (meta && slug) {
    meta.innerHTML = `<a class="seedance-final-link" href="/api/delivery/${encodeURIComponent(slug)}/zip" download>下载成片 zip</a>`;
  }
}

async function runConfirmProduceVideo() {
  const slug = currentScriptSlug();
  if (!slug) {
    setScriptActionStatus("请先生成并确认脚本");
    openScriptFloatPanel();
    return;
  }
  const produceBtn = document.getElementById("scriptFloatProduceBtn");
  const runBtn = document.getElementById("generateDockRun");
  closeScriptFloatPanel();
  state.seedanceProgressPersist = false;
  if (produceBtn) {
    produceBtn.disabled = true;
    produceBtn.textContent = "生成中…";
  }
  if (runBtn) {
    runBtn.disabled = true;
    runBtn.dataset.busy = "1";
    runBtn.innerHTML = '<span class="dock-run-icon">✦</span> 生成中…';
  }
  state.createPipelineActive = true;
  document.getElementById("generateDock")?.scrollIntoView({ behavior: "smooth", block: "end" });
  try {
    const ok = await runProduceVideo({ background: true });
    await refreshScriptPreview();
    updateLoopBarFromForm(state.lastPreview || {});
    const finalSlug = currentScriptSlug();
    if (ok !== false && finalSlug) {
      syncDownloadLinks(`/api/delivery/${finalSlug}/zip`, true);
      renderDockProduceComplete(finalSlug, "视频生成完成，可下载 zip 或预览成片");
    }
  } finally {
    state.createPipelineActive = false;
    if (!state.seedanceProgressPersist) showSeedanceProgress(false);
    if (produceBtn) {
      produceBtn.disabled = false;
      produceBtn.textContent = "确认生成视频";
    }
    if (runBtn) {
      delete runBtn.dataset.busy;
      runBtn.disabled = false;
      runBtn.innerHTML = '<span class="dock-run-icon">✦</span> 开始创作';
    }
    syncFinishButton(Boolean(state.lastPreview?.can_finish), Boolean(state.lastPreview?.delivery_ready));
  }
}

function refreshScriptFloatFromPreview(prev = {}) {
  const body = scriptResultBody();
  if (!body) return;
  if (prev.has_script && prev.script_pack) {
    body.innerHTML = formatPackResult(prev.script_pack, prev.script_meta);
  }
  updateLoopBarFromForm(prev);
}

function setScriptActionStatus(msg) {
  const el = document.getElementById("scriptActionStatus");
  if (el) el.textContent = msg || "";
  if ((state.createPipelineActive || state.seedanceProgressPersist) && msg) {
    const dockSt = document.getElementById("seedanceProgressStatus");
    if (dockSt) dockSt.textContent = msg;
  }
}

function syncDownloadLinks(href, visible) {
  document.querySelectorAll("#scriptDownloadBtnBottom, .js-script-download").forEach((dl) => {
    if (href) dl.href = href;
    dl.classList.toggle("hidden", !visible);
  });
}

function slugFor(linkId) {
  return `ref-${String(linkId).padStart(3, "0")}`;
}

function renderTagRow(containerId, options, selected, group) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const picked = [...new Set(selected)];
  if (!picked.length) {
    el.innerHTML = '<span class="muted tag-selected-empty">暂未选用</span>';
  } else {
    el.innerHTML = picked.map((t) =>
      `<button type="button" class="tag-chip active" data-group="${group}" data-value="${esc(t)}">${esc(t)}</button>`
    ).join("");
  }
}

function renderLibraryTagRow(containerId, options, selected, group) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const picked = [...new Set(selected)];
  if (!options.length) {
    el.innerHTML = '<span class="muted">素材库暂无该类别，请手动添加或到「设置」同步产品资料</span>';
    return;
  }
  el.innerHTML = options.map((t) =>
    `<button type="button" class="tag-chip ${picked.includes(t) ? "active" : ""}" data-group="${group}" data-value="${esc(t)}">${esc(t)}</button>`
  ).join("");
}

function renderProductPanel(p, apiTags, savedTags) {
  const pool = buildTagPool(p, apiTags);
  const selected = defaultSelectedTags(pool, savedTags);
  state.tagSelection = {
    audience: [...selected.audience],
    scenarios: [...selected.scenarios].slice(0, 1),
    selling: [...selected.selling],
    pains: [...selected.pains],
  };
  state.selectedAudience = state.tagSelection.audience;
  state.selectedScenarios = state.tagSelection.scenarios;
  state.currentTagPool = pool;
  const panel = document.getElementById("scriptProduct");
  panel.className = "script-tag-grid script-tag-grid-float";
  const groupsHtml = Object.entries(TAG_GROUPS).map(([group, cfg]) => `
    <div class="tag-panel tag-panel-compact">
      <div class="tag-panel-head">
        <span class="tag-group-label">${cfg.label}</span>
        ${cfg.single ? '<span class="tag-panel-hint muted">单选</span>' : ""}
      </div>
      <div class="tag-section tag-section-selected">
        <span class="tag-section-label">已选</span>
        <div id="${group}TagRow" class="tag-row tag-row-selected"></div>
      </div>
      <div class="tag-add-row">
        <input type="text" class="tag-input" data-group="${group}" placeholder="${cfg.placeholder}">
        <button type="button" class="tag-add-btn" data-group="${group}">添加</button>
      </div>
      <details class="tag-library-fold">
        <summary>素材库推荐</summary>
        <div class="tag-library-block">
          <div id="${group}LibraryRow" class="tag-row tag-library-row"></div>
        </div>
      </details>
    </div>`).join("");
  panel.innerHTML = groupsHtml;
  refreshTagGroupsUI();
}

async function persistProductTags(productId, field, tags) {
  const body = {};
  body[field] = tags.join("；");
  await api(`/api/products/${encodeURIComponent(productId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const p = state.products.find((x) => x.product_id === productId);
  if (p) p[field] = body[field];
}

async function addTagInline(group, rawText) {
  const text = String(rawText || "").trim();
  if (!text || text.length < 2) return;
  const cfg = TAG_GROUPS[group];
  if (!cfg) return;
  const productId = document.getElementById("scriptProductSelect").value;
  const pool = state.currentTagPool || { audience: [], scenarios: [], selling: [], pains: [] };
  const list = [...(pool[cfg.poolKey] || [])];
  if (!list.includes(text)) list.push(text);
  if (!state.tagPoolExtra[cfg.poolKey]) state.tagPoolExtra[cfg.poolKey] = [];
  state.tagPoolExtra[cfg.poolKey] = [...new Set([...state.tagPoolExtra[cfg.poolKey], text])];
  try {
    await persistProductTags(productId, cfg.field, list);
  } catch (err) {
    console.warn("标签保存失败", err);
  }
  const p = state.products.find((x) => x.product_id === productId) || state.lastPreview?.product || {};
  const key = cfg.savedKey;
  if (cfg.single) {
    state.tagSelection[key] = [text];
  } else if (!(state.tagSelection[key] || []).includes(text)) {
    state.tagSelection[key] = [...(state.tagSelection[key] || []), text];
  }
  renderProductPanel(p, buildTagPool(p, state.lastPreview?.delivery_tags), readAllSelectedTags());
  updateLoopBarFromForm(state.lastPreview || {});
  if (group === "scenario") syncDockPromptFromScenarioTags();
}

function tagsSelectionOk() {
  const sel = readAllSelectedTags();
  return sel.audience.length > 0 && sel.scenarios.length > 0
    && sel.selling.length > 0 && sel.pains.length > 0;
}

function selectGenerateScenario(featureId) {
  state.selectedScenarioFeature = featureId;
  document.querySelectorAll("#generateFeatureGrid .feature-card").forEach((c) => {
    c.classList.toggle("selected", c.dataset.featureId === featureId);
  });
}

function viralVideoCardHtml(item) {
  const active = item.link_id === state.selectedMaterialId ? " selected" : "";
  const thumb = item.thumbnail_url
    ? `<img class="viral-video-thumb" src="${esc(item.thumbnail_url)}" alt="">`
    : `<span class="feature-card-bg g-video-rev"></span>`;
  const title = (item.title || "").trim().slice(0, 32) || `爆款 #${item.link_id}`;
  const stats = [item.author, fmtNum(item.view_count) && `${fmtNum(item.view_count)}播放`, item.duration_sec && `${item.duration_sec}s`].filter(Boolean).join(" · ");
  return `<button type="button" class="feature-card viral-video-card${active}" data-link-id="${item.link_id}">
    ${thumb}
    <span class="viral-video-badge">${materialBadgeHtml(item)}</span>
    <span class="feature-card-label"><strong>${esc(title)}</strong><span>${esc(stats || `#${item.link_id}`)}</span></span>
  </button>`;
}

function syncGenerateViralGridDesc(count) {
  const el = document.getElementById("generateViralGridDesc");
  if (!el) return;
  const productId = currentProductId();
  if (!productId) {
    el.textContent = "请先在底部配置「产品」与场景标签，此处将展示同品类已抓取爆款";
    return;
  }
  if (!count) {
    el.textContent = `当前产品「${currentProductLabel()}」暂无已拆解对标，占位预留 · 可在设置中同步 TikTok 或打开「对标」浏览`;
    return;
  }
  el.textContent = `已抓取 ${count} 条同品类爆款（按播放量排序），点击卡片设为对标参考`;
}

function renderGenerateViralGrid() {
  const root = document.getElementById("generateFeatureGrid");
  if (!root) return;
  const pool = getMaterialPreviewPool();
  const sorted = [...pool].sort((a, b) => (Number(b.view_count) || 0) - (Number(a.view_count) || 0));
  const display = sorted.slice(0, 12);
  syncGenerateViralGridDesc(display.length);

  if (display.length) {
    root.classList.add("has-viral-videos");
    root.innerHTML = display.map((item) => viralVideoCardHtml(item)).join("");
    root.querySelectorAll(".viral-video-card[data-link-id]").forEach((card) => {
      card.addEventListener("click", async () => {
        const linkId = Number(card.dataset.linkId);
        if (!productWorkflowReady()) {
          await openProductFloatPanel();
          return;
        }
        await selectGenerateViralVideo(linkId);
      });
    });
    return;
  }

  root.classList.remove("has-viral-videos");
  renderFeatureGrid("generateFeatureGrid", GENERATE_FEATURES);
}

async function selectGenerateViralVideo(linkId) {
  if (state.selectedMaterialId !== linkId) resetPromptEnhanceUsed();
  state.selectedMaterialId = linkId;
  repopulateScriptMaterials();
  syncMaterialSelectFromState();
  syncWorkspaceRefChip();
  renderGenerateViralGrid();
  renderRefFloatMaterialList();
  if (currentProductId()) await refreshScriptPreview();
}

function handleDraftFeedbackFeature(action) {
  if (action === "audit") {
    switchDraftFeedbackStudioTab("audit");
    return;
  }
  switchDraftFeedbackSub(action);
  document.getElementById("draftFeedbackBody")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderFeatureGrid(containerId, items, { onClick } = {}) {
  const root = document.getElementById(containerId);
  if (!root) return;
  root.innerHTML = items.map((item) => `
    <button type="button" class="feature-card${item.planned ? " planned" : ""}${state.selectedScenarioFeature === item.id ? " selected" : ""}"
      data-feature-id="${esc(item.id)}" data-scenario-tag="${esc(item.scenarioTag || "")}"
      data-action="${esc(item.action || "")}" ${item.planned ? "disabled" : ""}>
      <span class="feature-card-bg ${esc(item.grad || "")}"></span>
      ${item.planned ? '<span class="feature-card-badge">规划中</span>' : ""}
      <span class="feature-card-label"><strong>${esc(item.label)}</strong><span>${esc(item.sub || "")}</span></span>
    </button>`).join("");
  root.querySelectorAll(".feature-card:not(.planned)").forEach((card) => {
    card.addEventListener("click", () => {
      if (onClick) onClick(card.dataset.featureId, card);
      else if (card.dataset.scenarioTag) selectGenerateScenario(card.dataset.featureId);
      else if (card.dataset.action) handleDraftFeedbackFeature(card.dataset.action);
    });
  });
}

function switchModuleStudioTab(moduleRoot, tab) {
  if (!moduleRoot) return;
  moduleRoot.querySelectorAll(".module-studio-tabs button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.studioTab === tab);
  });
  moduleRoot.querySelectorAll("[data-studio-panel]").forEach((panel) => {
    panel.classList.toggle("hidden", panel.dataset.studioPanel !== tab);
  });
  const featureSection = moduleRoot.querySelector(".module-feature-section");
  if (featureSection) featureSection.classList.toggle("hidden", tab !== "featured");
}

function switchGenerateStudioTab(tab) {
  state.generateStudioTab = tab;
  const root = document.querySelector('.module-studio[data-module="generate"]');
  switchModuleStudioTab(root, tab);
  if (tab === "featured") renderGenerateViralGrid();
  if (tab === "examples") renderGenerateExamples();
}

function switchDraftFeedbackStudioTab(tab) {
  const root = document.querySelector('.module-studio[data-module="draft-feedback"]');
  switchModuleStudioTab(root, tab);
}

function expandGenerateWorkspace() {
  state.generateWorkspaceOpen = true;
}

function collapseGenerateWorkspace() {
  state.generateWorkspaceOpen = false;
  document.getElementById("generateBackHomeBtn")?.classList.add("hidden");
  switchGenerateStudioTab(state.generateStudioTab || "featured");
}

async function renderDraftFeedbackHistory() {
  const root = document.getElementById("draftFeedbackHistoryList");
  if (!root) return;
  try {
    const data = await api("/api/library/finished");
    const items = (data.items || []).slice(0, 12);
    if (!items.length) {
      root.innerHTML = '<div class="detail-empty">暂无成稿。完成交付后在此查看历史。</div>';
      return;
    }
    root.innerHTML = items.map((r) => `
      <div class="feature-history-item">
        <span><strong>${esc(r.slug)}</strong> · ${esc(r.title || r.product_id || "")}</span>
        <span class="feature-history-actions">
          <span class="muted">${esc(r.saved_at || "")}</span>
          <button type="button" class="secondary pill-btn pill-btn-sm js-history-open-workspace" data-slug="${esc(r.slug)}">进入工作台</button>
        </span>
      </div>`).join("");
    root.querySelectorAll(".js-history-open-workspace").forEach((btn) => {
      btn.addEventListener("click", () => openHistoryInWorkspace(btn.dataset.slug));
    });
  } catch (err) {
    root.innerHTML = `<div class="detail-empty">加载失败：${esc(err.message)}</div>`;
  }
}

async function openHistoryInWorkspace(slug) {
  if (!slug) return;
  const item = state.items.find((m) => m.slug === slug || `ref-${String(m.link_id).padStart(3, "0")}` === slug);
  if (item) await selectMaterial(item.link_id);
  switchView("generate");
  refreshScriptFloatFromPreview(state.lastPreview || {});
  openScriptFloatPanel();
}

function renderGenerateExamples() {
  const root = document.getElementById("generateExamplesGrid");
  if (!root) return;
  const items = (state.items || []).filter((m) => m.analyzed).slice(0, 6);
  if (!items.length) {
    root.innerHTML = '<div class="detail-empty">暂无已拆解对标，请先在设置中同步并拆解素材。</div>';
    return;
  }
  root.innerHTML = items.map((m) => `
    <button type="button" class="feature-card" data-link-id="${m.link_id}">
      <span class="feature-card-bg g-video-rev"></span>
      <span class="feature-card-label"><strong>${esc((m.title || "").slice(0, 18) || `素材 #${m.link_id}`)}</strong><span>${esc(m.author || "")}</span></span>
    </button>`).join("");
  root.querySelectorAll("[data-link-id]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await selectMaterial(Number(btn.dataset.linkId));
      openRefFloatPanel();
      updateLoopBarFromForm(state.lastPreview || {});
    });
  });
}

async function renderDraftFeedbackStats() {
  const root = document.getElementById("draftFeedbackFeatureGrid");
  if (!root) return;
  try {
    const [fin, fb] = await Promise.all([
      api("/api/library/finished"),
      api("/api/library/feedback"),
    ]);
    const finN = (fin.items || []).length;
    const fbN = (fb.items || []).length;
    root.innerHTML = `
      <button type="button" class="feature-stat-card" data-action="finished">
        <strong>${finN}</strong><span>成稿库 · 已交付</span>
      </button>
      <button type="button" class="feature-stat-card" data-action="feedback">
        <strong>${fbN}</strong><span>反馈库 · 投放记录</span>
      </button>
      <button type="button" class="feature-stat-card" data-action="audit">
        <strong>—</strong><span>迭代优化 · 规划中</span>
      </button>`;
    root.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", () => handleDraftFeedbackFeature(btn.dataset.action));
    });
  } catch {
    renderFeatureGrid("draftFeedbackFeatureGrid", DRAFT_FEEDBACK_FEATURES);
  }
}

function initModuleStudios() {
  initDockGenSettings();
  renderGenerateViralGrid();
  renderFeatureGrid("imitateFeatureGrid", IMITATE_FEATURES);
  renderFeatureGrid("reverseFeatureGrid", REVERSE_FEATURES);
  renderDraftFeedbackStats();

  document.querySelectorAll('.module-studio[data-module="generate"] .module-studio-tabs button').forEach((btn) => {
    btn.addEventListener("click", () => switchGenerateStudioTab(btn.dataset.studioTab));
  });
  document.querySelectorAll('.module-studio[data-module="imitate"] .module-studio-tabs button').forEach((btn) => {
    btn.addEventListener("click", () => {
      const root = document.querySelector('.module-studio[data-module="imitate"]');
      switchModuleStudioTab(root, btn.dataset.studioTab);
    });
  });
  document.querySelectorAll('.module-studio[data-module="reverse"] .module-studio-tabs button').forEach((btn) => {
    btn.addEventListener("click", () => {
      const root = document.querySelector('.module-studio[data-module="reverse"]');
      switchModuleStudioTab(root, btn.dataset.studioTab);
    });
  });
  document.querySelectorAll('.module-studio[data-module="draft-feedback"] .module-studio-tabs button').forEach((btn) => {
    btn.addEventListener("click", () => switchDraftFeedbackStudioTab(btn.dataset.studioTab));
  });

  document.getElementById("generateBackHomeBtn")?.addEventListener("click", collapseGenerateWorkspace);
  document.getElementById("generateDockRun")?.addEventListener("click", () => runStartCreate());
  document.getElementById("dockOpenMaterialsBtn")?.addEventListener("click", () => openRefFloatPanel());
  document.getElementById("dockOpenProductBtn")?.addEventListener("click", () => openProductFloatPanel());
  document.getElementById("productFloatCloseBtn")?.addEventListener("click", closeProductFloatPanel);
  document.getElementById("productFloatBackdrop")?.addEventListener("click", closeProductFloatPanel);
  document.getElementById("productFloatConfirmBtn")?.addEventListener("click", async () => {
    syncProductFloatStatus();
    if (!document.getElementById("scriptProductSelect")?.value) return;
    if (!tagsSelectionOk()) return;
    const hadScript = Boolean(state.lastPreview?.has_script);
    const tagsChanged = tagsChangedSinceScript();
    const productId = document.getElementById("scriptProductSelect")?.value;
    const productChanged = Boolean(state.lastScriptProductId && productId !== state.lastScriptProductId);
    if (productChanged || tagsChanged) resetPromptEnhanceUsed();
    closeProductFloatPanel();
    await refreshScriptPreview();
    if (hadScript && (tagsChanged || productChanged)) {
      await runScriptGenerate();
      openScriptFloatPanel();
    } else {
      updateLoopBarFromForm(state.lastPreview || {});
      syncDockProductSlot();
      syncDockRefSlot();
      repopulateScriptMaterials();
      renderGenerateViralGrid();
      if (!state.selectedMaterialId) openRefFloatPanel();
    }
  });
  document.getElementById("refFloatCloseBtn")?.addEventListener("click", closeRefFloatPanel);
  document.getElementById("refFloatBackdrop")?.addEventListener("click", closeRefFloatPanel);
  document.getElementById("refFloatConfirmBtn")?.addEventListener("click", async () => {
    if (!state.selectedMaterialId) return;
    closeRefFloatPanel();
    syncDockRefSlot();
    if (document.getElementById("scriptProductSelect")?.value) {
      await refreshScriptPreview();
    }
    updateLoopBarFromForm(state.lastPreview || {});
  });
  document.getElementById("scriptFloatCloseBtn")?.addEventListener("click", closeScriptFloatPanel);
  document.getElementById("scriptFloatBackdrop")?.addEventListener("click", closeScriptFloatPanel);
  document.getElementById("scriptFloatProduceBtn")?.addEventListener("click", () => runConfirmProduceVideo());
  document.getElementById("scriptFloatRegenBtn")?.addEventListener("click", async () => {
    if (!tagsSelectionOk()) {
      await openProductFloatPanel();
      return;
    }
    await runScriptGenerate();
    openScriptFloatPanel();
  });
  document.getElementById("imitateDockRefBtn")?.addEventListener("click", () => openMaterialLibraryDrawer());
  document.getElementById("reverseDockMaterialBtn")?.addEventListener("click", () => openMaterialLibraryDrawer());
}

function syncDockChipsFromHealth() {
  const h = state.healthCache;
  const model = document.getElementById("dockModelChip");
  if (model && h?.seedance) {
    const prov = h.seedance.provider === "volcengine-ark" ? "SeedDance" : "AI 视频";
    const mode = h.seedance.mode === "script" ? "脚本分镜" : "空镜";
    model.textContent = `${prov} · ${mode}`;
  }
  syncDockVideoSettingsLabel();
  syncDockProductSlot();
}

function currentVideoSettings() {
  return state.videoSettings;
}

function persistVideoSettings() {
  try {
    localStorage.setItem("vl_video_settings", JSON.stringify(state.videoSettings));
  } catch { /* ignore */ }
}

function loadVideoSettings() {
  try {
    const raw = localStorage.getItem("vl_video_settings");
    if (!raw) return;
    const saved = JSON.parse(raw);
    if (VIDEO_RESOLUTIONS.includes(saved.resolution)) state.videoSettings.resolution = saved.resolution;
    if (VIDEO_ASPECT_RATIOS.includes(saved.aspectRatio)) state.videoSettings.aspectRatio = saved.aspectRatio;
    if (VIDEO_DURATIONS.includes(Number(saved.durationSec))) state.videoSettings.durationSec = Number(saved.durationSec);
    if (GENERATE_COUNTS.includes(Number(saved.generateCount))) state.videoSettings.generateCount = Number(saved.generateCount);
  } catch { /* ignore */ }
}

function syncDockVideoSettingsLabel() {
  const vs = currentVideoSettings();
  const label = document.getElementById("dockVideoSettingsLabel");
  const countLabel = document.getElementById("dockGenerateCountLabel");
  if (label) label.textContent = `${vs.resolution} · ${vs.aspectRatio}`;
  if (countLabel) countLabel.textContent = `生成 ${vs.generateCount} 条`;
}

function renderDockVideoSettingsPanel() {
  const vs = currentVideoSettings();
  const resRow = document.getElementById("dockResolutionRow");
  const ratioRow = document.getElementById("dockAspectRatioRow");
  if (resRow) {
    resRow.innerHTML = VIDEO_RESOLUTIONS.map((r) =>
      `<button type="button" class="dock-settings-pill${r === vs.resolution ? " active" : ""}" data-resolution="${r}">${r}</button>`
    ).join("");
    resRow.querySelectorAll("[data-resolution]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.videoSettings.resolution = btn.dataset.resolution;
        persistVideoSettings();
        renderDockVideoSettingsPanel();
        syncDockVideoSettingsLabel();
      });
    });
  }
  if (ratioRow) {
    ratioRow.innerHTML = VIDEO_ASPECT_RATIOS.map((ratio) => {
      const cls = ratio.replace(":", "x");
      return `<button type="button" class="dock-ratio-btn${ratio === vs.aspectRatio ? " active" : ""}" data-aspect-ratio="${ratio}" title="${ratio}">
        <span class="dock-ratio-icon ratio-${cls}" aria-hidden="true"></span>
        <span>${ratio}</span>
      </button>`;
    }).join("");
    ratioRow.querySelectorAll("[data-aspect-ratio]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.videoSettings.aspectRatio = btn.dataset.aspectRatio;
        persistVideoSettings();
        renderDockVideoSettingsPanel();
        syncDockVideoSettingsLabel();
      });
    });
  }
}

function renderDockGenerateCountMenu() {
  const menu = document.getElementById("dockGenerateCountMenu");
  if (!menu) return;
  const vs = currentVideoSettings();
  menu.innerHTML = GENERATE_COUNTS.map((n) =>
    `<button type="button" class="dock-gen-count-option${n === vs.generateCount ? " active" : ""}" role="menuitem" data-count="${n}">生成 ${n} 条</button>`
  ).join("");
  menu.querySelectorAll("[data-count]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.videoSettings.generateCount = Number(btn.dataset.count);
      persistVideoSettings();
      syncDockVideoSettingsLabel();
      renderDockGenerateCountMenu();
      closeDockGenerateCountMenu();
    });
  });
}

function closeDockVideoSettingsPanel() {
  const wrap = document.getElementById("dockVideoSettingsWrap");
  const btn = document.getElementById("dockVideoSettingsBtn");
  const panel = document.getElementById("dockVideoSettingsPanel");
  wrap?.classList.remove("open");
  btn?.setAttribute("aria-expanded", "false");
  panel?.classList.add("hidden");
  if (panel) panel.hidden = true;
}

function openDockVideoSettingsPanel() {
  const wrap = document.getElementById("dockVideoSettingsWrap");
  const btn = document.getElementById("dockVideoSettingsBtn");
  const panel = document.getElementById("dockVideoSettingsPanel");
  if (!wrap || !btn || !panel) return;
  closeDockGenerateCountMenu();
  renderDockVideoSettingsPanel();
  panel.classList.remove("hidden");
  panel.hidden = false;
  wrap.classList.add("open");
  btn.setAttribute("aria-expanded", "true");
}

function closeDockGenerateCountMenu() {
  const wrap = document.getElementById("dockGenerateCountWrap");
  const btn = document.getElementById("dockGenerateCountBtn");
  const menu = document.getElementById("dockGenerateCountMenu");
  wrap?.classList.remove("open");
  btn?.setAttribute("aria-expanded", "false");
  menu?.classList.add("hidden");
  if (menu) menu.hidden = true;
}

function openDockGenerateCountMenu() {
  const wrap = document.getElementById("dockGenerateCountWrap");
  const btn = document.getElementById("dockGenerateCountBtn");
  const menu = document.getElementById("dockGenerateCountMenu");
  if (!wrap || !btn || !menu) return;
  closeDockVideoSettingsPanel();
  renderDockGenerateCountMenu();
  menu.classList.remove("hidden");
  menu.hidden = false;
  wrap.classList.add("open");
  btn.setAttribute("aria-expanded", "true");
}

function syncPromptEnhanceButton() {
  const btn = document.getElementById("dockPromptEnhanceBtn");
  if (!btn) return;
  const used = state.promptEnhanceUsed;
  btn.disabled = used;
  btn.classList.toggle("active", Boolean(state.promptEnhanceOn) && !used);
  btn.title = used
    ? "本轮已使用提示词增强（切换产品/对标或完成生成后可再次使用）"
    : "结合标签与对标结构强化创作指令（每轮仅可点击一次）";
}

function resetPromptEnhanceUsed() {
  state.promptEnhanceUsed = false;
  state.promptEnhanceOn = false;
  syncPromptEnhanceButton();
}

function enhanceDockPrompt() {
  if (state.promptEnhanceUsed) return;
  const ta = document.getElementById("generateDockPrompt");
  if (!ta) return;
  const tags = readAllSelectedTags();
  const vs = currentVideoSettings();
  const material = state.items.find((i) => i.link_id === state.selectedMaterialId);
  const analysis = material?.analysis || state.lastPreview?.material?.analysis || {};
  const base = ta.value.trim();
  const sceneLine = tags.scenarios[0]
    ? `${tags.scenarios[0]}场景：展示产品在真实使用环境中的卖点与痛点，口播自然、镜头节奏对标爆款结构。`
    : "";
  const lead = base || sceneLine;
  const boosts = [
    "【增强】结构：钩子3秒痛点 → 产品入画 → 使用演示 → 效果验证 → 软性CTA",
    tags.audience.length ? `人群：${tags.audience.join("、")}` : "",
    tags.scenarios.length ? `场景：${tags.scenarios.join("、")}` : "",
    tags.selling.length ? `卖点：${tags.selling.join("、")}` : "",
    tags.pains.length ? `痛点：${tags.pains.join("、")}` : "",
    `画幅 ${vs.aspectRatio} · ${vs.resolution} · 生成 ${vs.generateCount} 条`,
    analysis.video_structure ? `对标结构：${String(analysis.video_structure).slice(0, 100)}` : "",
    analysis.hook_3s ? `钩子参考：${String(analysis.hook_3s).slice(0, 80)}` : "",
    "口播口语化、镜头节奏紧凑；禁止医疗承诺、竞品品牌与夸大表述",
  ].filter(Boolean);
  ta.value = lead ? `${lead}\n\n${boosts.join("；")}` : boosts.join("；");
  state.promptEnhanceOn = true;
  state.promptEnhanceUsed = true;
  syncPromptEnhanceButton();
}

function initDockGenSettings() {
  loadVideoSettings();
  syncDockVideoSettingsLabel();
  renderDockVideoSettingsPanel();
  renderDockGenerateCountMenu();

  syncPromptEnhanceButton();

  document.getElementById("dockVideoSettingsBtn")?.addEventListener("click", (e) => {
    e.stopPropagation();
    const wrap = document.getElementById("dockVideoSettingsWrap");
    if (wrap?.classList.contains("open")) closeDockVideoSettingsPanel();
    else openDockVideoSettingsPanel();
  });
  document.getElementById("dockGenerateCountBtn")?.addEventListener("click", (e) => {
    e.stopPropagation();
    const wrap = document.getElementById("dockGenerateCountWrap");
    if (wrap?.classList.contains("open")) closeDockGenerateCountMenu();
    else openDockGenerateCountMenu();
  });
  document.getElementById("dockPromptEnhanceBtn")?.addEventListener("click", () => {
    enhanceDockPrompt();
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest("#dockVideoSettingsWrap")) closeDockVideoSettingsPanel();
    if (!e.target.closest("#dockGenerateCountWrap")) closeDockGenerateCountMenu();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeDockVideoSettingsPanel();
      closeDockGenerateCountMenu();
    }
  });
}

function normalizeView(name) {
  if (name === "materials" || name === "script" || name === "workspace") return "generate";
  if (name === "finished" || name === "feedback") return "draft-feedback";
  return name;
}

function viewElementId(name) {
  const n = normalizeView(name);
  const map = {
    generate: "viewWorkspace",
    imitate: "viewImitate",
    reverse: "viewReverse",
    "draft-feedback": "viewDraftFeedback",
    products: "viewProducts",
  };
  if (map[n]) return map[n];
  const camel = n.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
  return `view${camel.charAt(0).toUpperCase()}${camel.slice(1)}`;
}

function activateView(name, options = {}) {
  name = normalizeView(name);
  const viewId = viewElementId(name);
  const el = document.getElementById(viewId);
  if (!el) {
    console.warn(`Unknown view: ${name} (${viewId})`);
    document.getElementById("viewWorkspace")?.classList.add("active");
    state.view = "generate";
    loadWorkspaceView();
    return "generate";
  }
  state.view = name;
  document.querySelectorAll(".view").forEach((node) => node.classList.remove("active"));
  el.classList.add("active");
  document.querySelectorAll("#mainNav button").forEach((btn) => {
    btn.classList.toggle("active", normalizeView(btn.dataset.view) === name);
  });
  if (name === "generate") {
    loadWorkspaceView();
    if (!state.generateWorkspaceOpen) collapseGenerateWorkspace();
  }
  if (name === "products") loadProductsView();
  if (name === "draft-feedback") {
    const sub = options.sub || state.draftFeedbackSub || "finished";
    switchDraftFeedbackSub(sub);
    renderDraftFeedbackStats();
    renderDraftFeedbackHistory();
  }
  return name;
}

function syncDraftFeedbackSubNav(sub) {
  state.draftFeedbackSub = sub;
  document.querySelectorAll("#draftFeedbackSubNav button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.sub === sub);
  });
  document.getElementById("draftFeedbackPanelFinished")?.classList.toggle("hidden", sub !== "finished");
  document.getElementById("draftFeedbackPanelFeedback")?.classList.toggle("hidden", sub !== "feedback");
  const finishedPanel = document.getElementById("draftFeedbackPanelFinished");
  finishedPanel?.classList.toggle("active", sub === "finished");
  const feedbackPanel = document.getElementById("draftFeedbackPanelFeedback");
  feedbackPanel?.classList.toggle("active", sub === "feedback");
}

function switchDraftFeedbackSub(sub) {
  if (!["finished", "feedback"].includes(sub)) return;
  syncDraftFeedbackSubNav(sub);
  if (sub === "finished") loadFinishedView();
  if (sub === "feedback") loadFeedbackView();
  renderDraftFeedbackHistory();
}

function syncWorkspaceActionBar(step) {
  document.querySelectorAll(".workspace-action-step").forEach((el) => {
    el.classList.toggle("hidden", el.dataset.forStep !== step);
  });
}

function syncMaterialSelectFromState() {
  const ms = document.getElementById("scriptMaterialSelect");
  if (!ms || !state.selectedMaterialId) return;
  const val = String(state.selectedMaterialId);
  if (ms.querySelector(`option[value="${val}"]`)) ms.value = val;
}

function syncScriptProduceEmpty() {
  syncDockScrollPadding();
}

function setScriptStep(step, { scroll = true } = {}) {
  const order = ["product", "ref", "produce"];
  if (!order.includes(step)) return;
  state.scriptStep = step;
  syncWorkspaceActionBar(step);
  if (!scroll) return;
  if (step === "product") openProductFloatPanel();
  else if (step === "ref") openRefFloatPanel();
  else if (step === "produce") openScriptFloatPanel();
}

function updateLoopBarFromForm(prev = {}) {
  const hint = document.getElementById("loopHint");
  const hasMaterial = Boolean(document.getElementById("scriptMaterialSelect")?.value);
  const tagsOk = tagsSelectionOk();
  const hasScript = Boolean(prev.has_script) || Boolean(prev.delivery_ready);
  syncScriptProduceEmpty(hasScript);
  if (hint) {
    if (state.scriptStep === "produce" && prev.delivery_ready) {
      hint.textContent = "成片已完成：可下载 zip 或预览视频。";
    } else if (state.scriptStep === "produce" && hasScript) {
      hint.textContent = "请检查脚本与分镜，确认无误后点击「确认生成视频」。";
    } else if (state.scriptStep === "product") {
      hint.textContent = tagsOk
        ? "标签已齐 → 点击底部「对标」选择爆款。"
        : "点击底部「产品」配置人群、场景、卖点与痛点。";
    } else if (state.scriptStep === "ref" && !hasMaterial) {
      hint.textContent = "点击底部「对标」选择爆款视频。";
    } else if (state.scriptStep === "ref" && hasMaterial) {
      hint.textContent = "对标已选 → 点击「开始创作」生成脚本。";
    } else if (!tagsOk) {
      hint.textContent = "请先点击底部「产品」完成场景标签配置。";
    } else if (!hasMaterial) {
      hint.textContent = "产品已就绪 → 点击「对标」选择同品类爆款。";
    } else {
      hint.textContent = "产品与对标已就绪 → 点击「开始创作」生成脚本预览。";
    }
  }
  syncDockProductSlot();
  syncDockRefSlot();
}

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function debounce(fn, ms = 280) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

function fmtNum(n) {
  const v = Number(n);
  if (!Number.isFinite(v) || v <= 0) return "";
  if (v >= 10000) return `${(v / 10000).toFixed(1)}万`;
  return String(v);
}

function scriptResultEl() {
  return document.getElementById("scriptFloatPanel");
}

function scriptResultBody() {
  return document.getElementById("scriptFloatBody");
}

// ── Navigation ─────────────────────────────────────────────────────────────

function switchView(name, options = {}) {
  activateView(name, options);
}

async function loadWorkspaceView() {
  if (!state.items.length) await loadMaterials();
  await loadScriptView();
  syncWorkspaceActionBar(state.scriptStep);
  renderGenerateViralGrid();
  syncDockChipsFromHealth();
}

function openSettingsDrawer() {
  const drawer = document.getElementById("settingsDrawer");
  const backdrop = document.getElementById("settingsBackdrop");
  const trigger = document.getElementById("settingsOpenBtn");
  if (!drawer || !backdrop) return;
  drawer.hidden = false;
  backdrop.hidden = false;
  requestAnimationFrame(() => {
    drawer.classList.add("open");
    backdrop.classList.add("open");
  });
  drawer.setAttribute("aria-hidden", "false");
  trigger?.setAttribute("aria-expanded", "true");
  loadSettingsView();
}

function closeSettingsDrawer() {
  const drawer = document.getElementById("settingsDrawer");
  const backdrop = document.getElementById("settingsBackdrop");
  const trigger = document.getElementById("settingsOpenBtn");
  if (!drawer || !backdrop) return;
  drawer.classList.remove("open");
  backdrop.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
  trigger?.setAttribute("aria-expanded", "false");
  window.setTimeout(() => {
    if (!drawer.classList.contains("open")) {
      drawer.hidden = true;
      backdrop.hidden = true;
    }
  }, 220);
}

function ensureCollectorPanel() {
  if (document.getElementById("btnCollectorRun")) return;
  const body = document.querySelector(".settings-drawer-body");
  const productsBlock = document.getElementById("openProductsBtn")?.closest(".settings-block");
  if (!body || !productsBlock) return;
  const wrap = document.createElement("details");
  wrap.className = "settings-block";
  wrap.open = true;
  wrap.innerHTML = `
    <summary>TikTok 采集</summary>
    <p class="hint">按关键词抓取 TikTok 公开视频元数据，并自动同步入当前素材库。</p>
    <div class="collector-form">
      <label>关键词
        <textarea id="collectorKeywords" rows="3" placeholder="每行一个关键词，例如：&#10;breast pump&#10;baby bottle&#10;baby products"></textarea>
      </label>
      <label>每词条数
        <input id="collectorLimit" type="number" min="1" max="100" value="20">
      </label>
      <div class="collector-actions">
        <button type="button" class="primary pill-btn" id="btnCollectorRun">开始采集</button>
      </div>
      <div id="collectorStatus" class="seedance-status">待执行</div>
      <div id="collectorResult" class="collector-result muted"></div>
      <div class="collector-actions">
        <button type="button" class="pill-btn" id="btnCollectorQuery">MySQL</button>
      </div>
      <label>TikTok 库内查询
        <input id="collectorQueryText" type="text" placeholder="关键词 / 作者 / video_id / hashtag">
      </label>
      <div id="collectorQueryStatus" class="seedance-status muted">待查询</div>
      <div id="collectorQueryResult" class="collector-query-result muted tiktok-db-preview-list"></div>
    </div>`;
  body.insertBefore(wrap, productsBlock);
  document.getElementById("btnCollectorRun")?.addEventListener("click", runCollectorImport);
  document.getElementById("btnCollectorQuery")?.addEventListener("click", runCollectorQuery);
}

const TIKTOK_DB_PREVIEW_LIMIT = 5;
const TIKTOK_DB_CAPTION_LEN = 48;

function renderTikTokDbPreviewCards(items, total = items.length) {
  if (!items.length) return '<div class="muted">暂无匹配记录。</div>';
  const shown = items.slice(0, TIKTOK_DB_PREVIEW_LIMIT);
  const rest = Math.max(0, (total || items.length) - shown.length);
  const cards = shown.map((item) => {
    const caption = String(item.caption || "").trim();
    const short = caption.slice(0, TIKTOK_DB_CAPTION_LEN);
    return `<article class="tiktok-db-preview-card">
      <a href="${esc(item.video_url)}" target="_blank" rel="noreferrer">${esc(item.author_name || item.video_id || "视频")}</a>
      <span class="tiktok-db-preview-meta">${esc(item.source_keyword || "-")} · ${esc(item.like_count || 0)} 赞 · ${esc(item.comment_count || 0)} 评</span>
      ${caption ? `<p class="tiktok-db-preview-caption">${esc(short)}${caption.length > TIKTOK_DB_CAPTION_LEN ? "…" : ""}</p>` : ""}
    </article>`;
  }).join("");
  const more = rest > 0
    ? `<p class="tiktok-db-preview-more muted">还有 ${rest} 条未展示，请缩小关键词或在下方素材库查看</p>`
    : "";
  return cards + more;
}

async function runCollectorImport() {
  const keywordsRaw = document.getElementById("collectorKeywords")?.value || "";
  const keywords = keywordsRaw.split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
  const limit = Number(document.getElementById("collectorLimit")?.value || 20);
  const statusEl = document.getElementById("collectorStatus");
  const resultEl = document.getElementById("collectorResult");
  if (!keywords.length) {
    if (statusEl) statusEl.textContent = "请至少输入一个关键词";
    return;
  }
  if (statusEl) statusEl.textContent = "正在采集 TikTok 公开数据，请稍候…";
  if (resultEl) resultEl.textContent = "";
  try {
    const data = await api("/api/tiktok-collector/collect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        keywords,
        limit_per_keyword: Number.isFinite(limit) ? limit : 20,
      }),
    });
    if (statusEl) {
      statusEl.textContent = `采集完成：${data.total_collected} 条，新增 ${data.imported_new_links} 条，更新 ${data.updated_existing_links} 条`;
    }
    if (resultEl) {
      const parts = [
        data.json_path ? `JSON: ${data.json_path}` : "",
        data.csv_path ? `CSV: ${data.csv_path}` : "",
        data.output_dir ? `输出目录: ${data.output_dir}` : "",
      ].filter(Boolean);
      resultEl.textContent = parts.join(" | ");
    }
    await refreshHealth();
    await loadMaterials();
  } catch (err) {
    if (statusEl) statusEl.textContent = `采集失败：${err.message}`;
  }
}

function renderCollectorQueryItems(items, total) {
  return renderTikTokDbPreviewCards(items, total);
}

async function runCollectorQuery() {
  const q = document.getElementById("collectorQueryText")?.value?.trim() || "";
  const statusEl = document.getElementById("collectorQueryStatus");
  const resultEl = document.getElementById("collectorQueryResult");
  if (statusEl) statusEl.textContent = "正在查询 MySQL…";
  if (resultEl) resultEl.innerHTML = "";
  try {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    params.set("limit", String(TIKTOK_DB_PREVIEW_LIMIT));
    const data = await api(`/api/tiktok-collector/db/videos?${params.toString()}`);
    if (statusEl) {
      statusEl.textContent = data.db_enabled
        ? `MySQL 查询完成，命中 ${data.total} 条，预览 ${Math.min(data.items.length, TIKTOK_DB_PREVIEW_LIMIT)} 条`
        : "未配置 MySQL，无法查询。";
    }
    if (resultEl) resultEl.innerHTML = renderCollectorQueryItems(data.items || [], data.total);
  } catch (err) {
    if (statusEl) statusEl.textContent = `MySQL 查询失败：${err.message}`;
  }
}

function openMaterialLibraryDrawer() {
  const drawer = document.getElementById("materialLibraryDrawer");
  const backdrop = document.getElementById("materialLibraryBackdrop");
  if (!drawer || !backdrop) return;
  syncDrawerFiltersFromState();
  drawer.hidden = false;
  backdrop.hidden = false;
  requestAnimationFrame(() => {
    drawer.classList.add("open");
    backdrop.classList.add("open");
  });
  drawer.setAttribute("aria-hidden", "false");
  void loadMaterials();
}

function closeMaterialLibraryDrawer() {
  const drawer = document.getElementById("materialLibraryDrawer");
  const backdrop = document.getElementById("materialLibraryBackdrop");
  if (!drawer || !backdrop) return;
  drawer.classList.remove("open");
  backdrop.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
  window.setTimeout(() => {
    if (!drawer.classList.contains("open")) {
      drawer.hidden = true;
      backdrop.hidden = true;
    }
  }, 220);
}

function syncProductFloatStatus() {
  const el = document.getElementById("productFloatStatus");
  if (!el) return;
  const ps = document.getElementById("scriptProductSelect");
  const productName = ps?.selectedOptions?.[0]?.textContent?.trim() || "";
  if (!ps?.value) {
    el.textContent = "请先选择产品";
    return;
  }
  if (!tagsSelectionOk()) {
    el.textContent = "请为人群、场景、卖点、痛点各至少选择一项";
    return;
  }
  el.textContent = productName ? `已配置：${productName}` : "标签已就绪";
}

function syncDockProductSlot() {
  const btn = document.getElementById("dockOpenProductBtn");
  if (!btn) return;
  const ready = Boolean(document.getElementById("scriptProductSelect")?.value) && tagsSelectionOk();
  btn.classList.toggle("has-value", ready);
}

function syncDockRefSlot() {
  const btn = document.getElementById("dockOpenMaterialsBtn");
  if (!btn) return;
  const ready = productWorkflowReady();
  btn.disabled = !ready;
  btn.classList.toggle("dock-upload-slot-locked", !ready);
  btn.classList.toggle("has-value", ready && Boolean(state.selectedMaterialId));
  btn.title = ready ? "选择同品类对标视频" : "请先点击「产品」完成配置";
}

function syncRefFloatStatus() {
  const el = document.getElementById("refFloatStatus");
  if (!el) return;
  const item = state.items.find((i) => i.link_id === state.selectedMaterialId);
  if (item) {
    const title = (item.title || "").slice(0, 24);
    el.textContent = `已选 #${item.link_id}${title ? ` · ${title}` : ""}`;
  } else {
    el.textContent = "未选择对标";
  }
}

function syncRefFloatFiltersFromState() {
  const cat = document.getElementById("refFloatCategorySelect");
  const kw = document.getElementById("refFloatKeywordInput");
  const analyzed = document.getElementById("refFloatAnalyzedOnly");
  const showAll = document.getElementById("refFloatShowAllMaterials");
  if (cat) cat.value = state.filters.category || "";
  if (kw) kw.value = state.filters.q || "";
  if (analyzed) analyzed.checked = Boolean(state.filters.analyzedOnly);
  if (showAll) showAll.checked = Boolean(state.showAllMaterials);
}

function syncDrawerFiltersFromState() {
  const cat = document.getElementById("categorySelect");
  const kw = document.getElementById("keywordInput");
  const analyzed = document.getElementById("analyzedOnly");
  const showAll = document.getElementById("showAllMaterials");
  if (cat) cat.value = state.filters.category || "";
  if (kw) kw.value = state.filters.q || "";
  if (analyzed) analyzed.checked = Boolean(state.filters.analyzedOnly);
  if (showAll) showAll.checked = Boolean(state.showAllMaterials);
}

async function openRefFloatPanel() {
  if (!productWorkflowReady()) {
    await openProductFloatPanel();
    return;
  }
  if (!state.items.length) await loadMaterials();
  syncRefFloatFiltersFromState();
  if (!state.showAllMaterials) {
    const pool = getMaterialPreviewPool();
    if (state.selectedMaterialId && !pool.some((i) => i.link_id === state.selectedMaterialId)) {
      state.selectedMaterialId = null;
      syncMaterialSelectFromState();
      const pane = document.getElementById("materialDetail");
      if (pane) {
        pane.className = "detail-empty ref-float-detail";
        pane.innerHTML = "选择左侧对标视频查看拆解";
      }
    }
  }
  renderRefFloatMaterialList();
  syncRefFloatProductLine();
  renderGenerateViralGrid();
  openFloatPanel("refFloatPanel", "refFloatBackdrop");
  syncRefFloatStatus();
  if (state.selectedMaterialId) {
    const pane = document.getElementById("materialDetail");
    if (pane && pane.classList.contains("detail-empty")) {
      await selectMaterial(state.selectedMaterialId, { keepDetail: true });
    }
  }
}

function closeRefFloatPanel() {
  closeFloatPanel("refFloatPanel", "refFloatBackdrop", () => {
    syncDockRefSlot();
    updateLoopBarFromForm(state.lastPreview || {});
  });
}

function openScriptFloatPanel() {
  refreshScriptFloatFromPreview(state.lastPreview || {});
  openFloatPanel("scriptFloatPanel", "scriptFloatBackdrop");
}

function closeScriptFloatPanel() {
  closeFloatPanel("scriptFloatPanel", "scriptFloatBackdrop");
}

async function openProductFloatPanel() {
  const panel = document.getElementById("productFloatPanel");
  const backdrop = document.getElementById("productFloatBackdrop");
  if (!panel || !backdrop) return;
  await populateScriptProductSelect();
  if (document.getElementById("scriptProductSelect")?.value) {
    await refreshScriptPreview();
  }
  openFloatPanel("productFloatPanel", "productFloatBackdrop");
  syncProductFloatStatus();
}

function closeProductFloatPanel() {
  closeFloatPanel("productFloatPanel", "productFloatBackdrop", () => {
    syncDockProductSlot();
    updateLoopBarFromForm(state.lastPreview || {});
  });
}

["openMaterialLibraryBtn", "openMaterialLibraryAnalyzedBtn"].forEach((id) => {
  document.getElementById(id)?.addEventListener("click", () => openMaterialLibraryDrawer());
});
document.getElementById("materialLibraryCloseBtn")?.addEventListener("click", closeMaterialLibraryDrawer);
document.getElementById("materialLibraryBackdrop")?.addEventListener("click", closeMaterialLibraryDrawer);
document.getElementById("materialLibraryTikTokSearchBtn")?.addEventListener("click", () => loadMaterialLibraryTikTokDb());
document.getElementById("materialLibraryTikTokQuery")?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    loadMaterialLibraryTikTokDb();
  }
});

document.getElementById("mainNav")?.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-view]");
  if (btn) switchView(btn.dataset.view);
});

document.getElementById("draftFeedbackSubNav")?.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-sub]");
  if (btn) switchDraftFeedbackSub(btn.dataset.sub);
});

// ── Health / stats ───────────────────────────────────────────────────────

async function refreshHealth() {
  try {
    const h = await api("/api/health");
    state.healthCache = h;
    const matEl = document.getElementById("statMaterials");
    const anaEl = document.getElementById("statAnalyzed");
    if (matEl) matEl.textContent = h.materials ?? 0;
    if (anaEl) anaEl.textContent = h.analyzed ?? 0;
    syncDockChipsFromHealth();
    return h;
  } catch (err) {
    console.warn("refreshHealth failed", err);
    const matEl = document.getElementById("statMaterials");
    const anaEl = document.getElementById("statAnalyzed");
    if (matEl && matEl.textContent === "-") matEl.textContent = "?";
    if (anaEl && anaEl.textContent === "-") anaEl.textContent = "?";
    throw err;
  }
}

function renderSeedanceSettings(health) {
  const el = document.getElementById("seedanceSettingsStatus");
  if (!el) return;
  const sd = health?.seedance || {};
  const mode = sd.mode === "script" ? "脚本分镜模式（各镜生成短视频）" : "空镜模式（仅痛点镜）";
  if (!sd.configured) {
    el.innerHTML = `未配置 · 在 <code>overseas-loc-mvp/.env</code> 填写 <code>ARK_API_KEY</code><br><span class="muted">${esc(sd.setup || "")}</span>`;
    return;
  }
  const prov = sd.provider === "volcengine-ark" ? "火山方舟 Ark" : (sd.provider || "fal.ai");
  el.innerHTML = `已配置 ${esc(prov)} · ${esc(mode)}<br>模型 <code>${esc(sd.text_model || "")}</code>`;
}

function renderSeedance(slug, seedance, health) {
  const statusEl = document.getElementById("seedanceStatus");
  const pipelineEl = document.getElementById("seedancePipeline");
  const hintEl = document.getElementById("seedanceHint");
  if (!statusEl) return;

  const pipeline = seedance?.pipeline || health?.seedance?.label || "";
  if (pipelineEl) pipelineEl.textContent = pipeline;

  if (!slug || !seedance) {
    showSeedanceProgress(false);
    renderSeedanceFinalPreview(null, null);
    return;
  }

  const finalReady = Boolean(seedance.final_video?.ready);
  renderSeedanceFinalPreview(slug, seedance);

  if (!state.createPipelineActive) {
    showSeedanceProgress(false);
    return;
  }

  const configured = health?.seedance?.configured;
  if (!configured) {
    statusEl.textContent = "未连接 SeedDance";
    showSeedanceProgress(true, {
      status: "未配置 ARK_API_KEY",
      pipeline: health?.seedance?.setup || "",
      percent: 0,
    });
    if (hintEl) hintEl.textContent = health?.seedance?.setup || "";
    return;
  }

  const prov = health.seedance.provider === "volcengine-ark" ? "火山方舟 Ark" : (health.seedance.provider || "fal.ai");
  const modeHint = health.seedance.mode === "script" ? "脚本分镜模式" : "空镜模式";
  const statusText = `已连接 ${prov} · ${modeHint} · ${health.seedance.text_model || ""}`;
  statusEl.textContent = statusText;

  const shots = seedance.shots || [];
  const readyCount = shots.filter((s) => s.ready).length;
  const total = shots.length || 5;
  const pct = finalReady ? 100 : (total ? Math.round((readyCount / total) * 90) : 10);

  showSeedanceProgress(true, {
    status: finalReady ? "成片已就绪" : (readyCount ? `已生成 ${readyCount}/${total} 镜` : statusText),
    pipeline,
    percent: pct,
    indeterminate: !finalReady && readyCount === 0,
  });

  if (hintEl) {
    hintEl.textContent = finalReady
      ? "视频生成完成"
      : "每镜约 5 秒；全部生成后自动拼接为 final-video.mp4";
  }

  document.getElementById("seedanceShots").innerHTML = shots.map((s) => `<span data-n="${s.number}"></span>`).join("");
}

async function loadSeedanceForSlug(slug) {
  if (!slug) return;
  const health = state.healthCache || await refreshHealth();
  try {
    const seedance = await api(`/api/delivery/${encodeURIComponent(slug)}/seedance`);
    renderSeedance(slug, seedance, health);
  } catch (err) {
    renderSeedance(slug, { available: false, shots: [] }, health);
    const hint = document.getElementById("seedanceHint");
    if (hint) hint.textContent = err.message;
  }
}

// ── Materials ────────────────────────────────────────────────────────────

async function loadFilters() {
  const data = await api("/api/filters");
  state.products = data.products || [];
  for (const id of ["categorySelect", "refFloatCategorySelect"]) {
    const cs = document.getElementById(id);
    if (!cs) continue;
    cs.innerHTML = '<option value="">全部</option>';
    (data.categories || []).forEach((c) => {
      const o = document.createElement("option");
      o.value = c;
      o.textContent = CATEGORY_ZH[c] || c;
      cs.appendChild(o);
    });
  }
}

async function loadMaterials() {
  const p = new URLSearchParams();
  if (state.filters.category) p.set("category", state.filters.category);
  if (state.filters.q) p.set("q", state.filters.q);
  if (state.filters.analyzedOnly) p.set("analyzed_only", "true");
  state.items = (await api(`/api/materials?${p}`)).items || [];
  renderMaterialList();
  renderRefFloatMaterialList();
  renderGenerateViralGrid();
}

function renderMaterialLibraryTikTokCards(items, total) {
  return renderTikTokDbPreviewCards(items, total);
}

async function loadMaterialLibraryTikTokDb() {
  const q = document.getElementById("materialLibraryTikTokQuery")?.value?.trim() || state.filters.q || "";
  const statusEl = document.getElementById("materialLibraryTikTokStatus");
  const listEl = document.getElementById("materialLibraryTikTokList");
  const summaryEl = document.getElementById("materialLibraryTikTokSummary");
  if (statusEl) statusEl.textContent = "正在查询…";
  if (listEl) listEl.innerHTML = "";
  try {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    params.set("limit", String(TIKTOK_DB_PREVIEW_LIMIT));
    const data = await api(`/api/tiktok-collector/db/videos?${params.toString()}`);
    if (statusEl) {
      statusEl.textContent = data.db_enabled
        ? `命中 ${data.total} 条，预览 ${Math.min((data.items || []).length, TIKTOK_DB_PREVIEW_LIMIT)} 条`
        : "未启用 TikTok 数据库";
    }
    if (summaryEl && data.db_enabled) {
      summaryEl.textContent = data.total ? `（${data.total} 条）` : "（无结果）";
    }
    if (listEl) listEl.innerHTML = renderMaterialLibraryTikTokCards(data.items || [], data.total);
  } catch (err) {
    if (statusEl) statusEl.textContent = `查询失败：${err.message}`;
  }
}

function materialBadgeHtml(item) {
  if (!item.has_analysis) {
    return '<span class="badge badge-pending">待拆解</span>';
  }
  return '<span class="badge badge-done">已拆解</span>';
}

function materialCardHtml(item, { compact = false } = {}) {
  const active = item.link_id === state.selectedMaterialId ? "active" : "";
  const thumb = item.thumbnail_url
    ? `<img class="thumb" src="${esc(item.thumbnail_url)}" alt="">`
    : '<div class="thumb placeholder">无图</div>';
  const stats = [fmtNum(item.view_count) && `${fmtNum(item.view_count)}播放`, item.duration_sec && `${item.duration_sec}s`].filter(Boolean).join(" · ");
  const badge = materialBadgeHtml(item);
  const title = item.title || "";
  const titleText = `#${item.link_id} ${title}`;
  const titleSlice = compact ? 56 : 80;
  return `<button type="button" class="card ${active}" data-id="${item.link_id}">
    ${thumb}
    <div><h3 title="${esc(titleText)}">${esc(`#${item.link_id} ${title.slice(0, titleSlice)}`)}</h3>
    <div class="meta">${esc(item.author)}${stats ? ` · ${stats}` : ""}</div>${badge}</div>
  </button>`;
}

function productWorkflowReady() {
  return Boolean(document.getElementById("scriptProductSelect")?.value) && tagsSelectionOk();
}

function currentProductId() {
  return document.getElementById("scriptProductSelect")?.value || state.selectedProductId || "";
}

function currentProductLabel() {
  const productId = currentProductId();
  const p = state.products.find((x) => x.product_id === productId);
  return p?.product_name || productId;
}

function getMaterialPreviewPool() {
  const productId = currentProductId();
  let pool = state.items.filter((i) => i.has_analysis);
  if (productId && !state.showAllMaterials) {
    pool = pool.filter((i) => materialMatchesProduct(i, productId));
  }
  return pool;
}

function materialInProductPool(linkId, productId = currentProductId()) {
  if (!linkId || !productId) return false;
  return getMaterialPreviewPool().some((i) => i.link_id === Number(linkId));
}

function syncRefFloatProductLine() {
  const line = document.getElementById("refFloatProductLine");
  const hint = document.getElementById("refFloatPoolHint");
  const productId = currentProductId();
  const pool = getMaterialPreviewPool();
  if (line) {
    line.textContent = productId
      ? `当前产品：${currentProductLabel()} · 脚本将严格按此产品标签 + 所选对标结构生成`
      : "";
  }
  if (hint) {
    hint.textContent = productId
      ? (state.showAllMaterials ? `共 ${pool.length} 条（含其他品类）` : `同品类 ${pool.length} 条`)
      : "";
  }
}

function syncWorkspaceRefChip() {
  syncRefFloatStatus();
  syncDockRefSlot();
}

function renderMaterialListPreview() {
  const root = document.getElementById("materialListPreview");
  if (!root) return;
  const pool = getMaterialPreviewPool();
  if (!pool.length) {
    root.innerHTML = '<div class="detail-empty">暂无素材。点击「浏览全部素材」打开素材库。</div>';
    return;
  }
  const sorted = [...pool].sort((a, b) => a.link_id - b.link_id);
  const selected = sorted.find((i) => i.link_id === state.selectedMaterialId) || sorted[0];
  const others = sorted.filter((i) => i.link_id !== selected.link_id).slice(0, 3);
  const previewItems = [selected, ...others];
  root.innerHTML = previewItems.map((item) => materialCardHtml(item, { compact: true })).join("");
  root.querySelectorAll(".card").forEach((c) =>
    c.addEventListener("click", () => selectMaterial(Number(c.dataset.id), { fromDrawer: false }))
  );
}

function renderRefFloatMaterialList() {
  const root = document.getElementById("refFloatMaterialList");
  if (!root) return;
  const productId = currentProductId();
  if (!productId) {
    root.innerHTML = '<div class="detail-empty">请先在底部点击「产品」并完成场景标签配置。</div>';
    syncRefFloatProductLine();
    return;
  }
  const pool = getMaterialPreviewPool();
  syncRefFloatProductLine();
  if (!pool.length) {
    root.innerHTML = state.showAllMaterials
      ? '<div class="detail-empty">暂无已拆解素材。请在设置中同步并拆解，或调整筛选条件。</div>'
      : `<div class="detail-empty">暂无与「${esc(currentProductLabel())}」同品类的已拆解对标。可勾选「显示其他品类」浏览全部，或更换产品。</div>`;
    return;
  }
  const sorted = [...pool].sort((a, b) => a.link_id - b.link_id);
  root.innerHTML = sorted.map((item) => materialCardHtml(item)).join("");
  root.querySelectorAll(".card").forEach((c) =>
    c.addEventListener("click", () => selectMaterial(Number(c.dataset.id), { fromRefFloat: true }))
  );
}

function renderMaterialList() {
  const root = document.getElementById("materialList");
  if (!root) return;
  if (!state.items.length) {
    root.innerHTML = '<div class="detail-empty">无匹配素材。请先在「设置」同步 TikTok。</div>';
    renderMaterialListPreview();
    return;
  }
  root.innerHTML = state.items.map((item) => materialCardHtml(item)).join("");
  root.querySelectorAll(".card").forEach((c) =>
    c.addEventListener("click", () => selectMaterial(Number(c.dataset.id), { fromDrawer: true }))
  );
  renderMaterialListPreview();
}

function fmtShotRange(start, end) {
  const pad = (v) => {
    const n = parseInt(String(v).replace(/\D/g, ""), 10);
    if (Number.isNaN(n)) return String(v || "0");
    const m = Math.floor(n / 60);
    const s = n % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };
  return `${pad(start)} - ${pad(end)}`;
}

function copyText(text, btn) {
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    if (btn) {
      const orig = btn.textContent;
      btn.textContent = "已复制";
      setTimeout(() => { btn.textContent = orig; }, 1500);
    }
  }).catch(() => alert("复制失败"));
}

function renderDissectorMedia(d) {
  const thumb = d.thumbnail_url
    ? `<img class="dissector-poster-img" src="${esc(d.thumbnail_url)}" alt="">`
    : `<div class="dissector-poster-placeholder">无封面</div>`;
  const stats = [
    fmtNum(d.view_count) && `${fmtNum(d.view_count)} 播放`,
    d.duration_sec && `${d.duration_sec}s`,
    fmtNum(d.like_count) && `${fmtNum(d.like_count)} 赞`,
  ].filter(Boolean).join(" · ");
  return `
    <div class="dissector-media">
      <div class="dissector-poster">${thumb}</div>
      <div class="dissector-meta">
        <div class="dissector-author">@${esc(d.author || "unknown")}</div>
        <h2 class="dissector-title">#${d.link_id} ${esc(d.title || "")}</h2>
        <div class="dissector-stats">${esc(stats || "—")}</div>
        <a class="dissector-link" href="${esc(d.url)}" target="_blank" rel="noopener">打开 TikTok ↗</a>
      </div>
    </div>`;
}

function renderDissectorShots(shots) {
  if (!shots.length) {
    return `<p class="dissector-empty">暂无分镜，豆包拆解完成后将显示在此</p>`;
  }
  return `<table class="dissector-table">
    <thead><tr>
      <th class="col-idx">#</th>
      <th class="col-time">时间</th>
      <th class="col-visual">画面描述</th>
      <th class="col-dialogue">台词</th>
      <th class="col-sub">字幕/标签</th>
    </tr></thead>
    <tbody>${shots.map((s) => `<tr>
      <td class="col-idx">${esc(s.index)}</td>
      <td class="col-time">${esc(fmtShotRange(s.start, s.end))}</td>
      <td class="col-visual">${esc(s.visual_description || "")}</td>
      <td class="col-dialogue">${esc(s.dialogue || "")}</td>
      <td class="col-sub">${esc(s.subtitle_or_title || "")}</td>
    </tr>`).join("")}</tbody>
  </table>`;
}

function friendlyAnalyzeError(msg, detail) {
  const text = String(msg || "").trim();
  if (text.includes("video_analysis.csv") || text.includes("豆包失败，已回退规则") || text.includes("rule shots=")) {
    return "豆包拆解超时或失败。若下方已有分镜表可继续使用，也可点击「重试拆解」。";
  }
  return text || "豆包拆解失败";
}

function renderMaterialDetail(d, detail) {
  const a = (detail?.analysis || d.analysis || {});
  let shots = detail?.shots || [];
  let status = detail?.status || (shots.length ? "ready" : "unknown");
  const summary = detail?.summary || a.summary || "";
  const transcript = detail?.full_transcript || a.full_transcript || "";
  let warning = detail?.warning || "";

  if (status === "error" && shots.length) {
    status = "ready";
    warning = warning || friendlyAnalyzeError(detail?.message, detail);
  }

  if (status === "running") {
    return `
      <div class="dissector">
        <div class="dissector-top">
          ${renderDissectorMedia(d)}
          <div class="dissector-script-panel dissector-loading-panel">
            <div class="dissector-panel-head"><span>完整文案（逐字稿）</span></div>
            <div class="analyze-loading">
              <p><strong>豆包视频拆解中…</strong></p>
              <p class="muted">正在生成逐字稿与分镜表（约 1–3 分钟），完成后自动刷新</p>
            </div>
          </div>
        </div>
        <div class="dissector-bottom">
          <div class="dissector-panel-head"><span>分镜脚本</span></div>
          <p class="dissector-empty muted">等待拆解结果…</p>
        </div>
      </div>`;
  }

  if (status === "error") {
    return `
      <div class="dissector">
        <div class="dissector-top">${renderDissectorMedia(d)}</div>
        <div class="result error">${esc(friendlyAnalyzeError(detail?.message, detail))}</div>
        <div class="dissector-foot dissector-foot-row">
          ${detail?.retryable ? '<button type="button" class="secondary" id="retryAnalyzeBtn">重试拆解</button>' : ""}
          <button type="button" class="primary primary-dark" id="goScriptBtn">生成脚本</button>
        </div>
      </div>`;
  }

  return `
    <div class="dissector">
      ${warning ? `<div class="dissector-warn">${esc(warning)}</div>` : ""}
      <div class="dissector-top">
        ${renderDissectorMedia(d)}
        <div class="dissector-script-panel">
          <div class="dissector-panel-head">
            <span>完整文案（逐字稿）</span>
            <button type="button" class="btn-text" id="copyTranscriptBtn" ${transcript ? "" : "disabled"}>复制</button>
          </div>
          <div class="dissector-transcript" id="transcriptBody">${transcript ? esc(transcript) : '<span class="muted">（无逐字稿）</span>'}</div>
          ${summary ? `<div class="dissector-summary"><strong>概要：</strong>${esc(summary)}</div>` : ""}
        </div>
      </div>
      <div class="dissector-bottom">
        <div class="dissector-panel-head">
          <span>分镜脚本（共 ${shots.length} 镜）</span>
          <span class="dissector-tag">已拆解</span>
        </div>
        ${renderDissectorShots(shots)}
      </div>
      <details class="dissector-fold">
        <summary>结构参考（供脚本生成）</summary>
        <div class="dissector-fold-grid">
          ${["hook_3s", "pain_points", "selling_points", "video_structure", "reusable_template"].map((k) => `
            <div><dt>${ANALYSIS_LABELS[k] || k}</dt><dd>${esc(a[k] || "—")}</dd></div>`).join("")}
        </div>
      </details>
      <div class="dissector-foot">
        <button type="button" class="primary primary-dark" id="goScriptBtn">生成脚本</button>
      </div>
    </div>`;
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function fetchMaterialAnalysis(linkId, pane) {
  for (let i = 0; i < 80; i++) {
    const detail = await api(`/api/materials/${linkId}/analysis/detail`);
    if (detail.status === "running") {
      if (pane) {
        const d = state.items.find((x) => x.link_id === linkId) || { link_id: linkId, title: "", author: "", url: "#" };
        pane.innerHTML = renderMaterialDetail(d, detail);
      }
      await sleep(3000);
      continue;
    }
    return detail;
  }
  throw new Error("豆包拆解超时，请稍后重试");
}

async function selectMaterial(linkId, { fromDrawer = false, fromRefFloat = false, keepDetail = false } = {}) {
  if (state.selectedMaterialId !== linkId) resetPromptEnhanceUsed();
  state.selectedMaterialId = linkId;
  renderMaterialList();
  renderRefFloatMaterialList();
  renderGenerateViralGrid();
  if (fromDrawer) closeMaterialLibraryDrawer();
  repopulateScriptMaterials();
  syncMaterialSelectFromState();
  syncWorkspaceRefChip();
  const pane = document.getElementById("materialDetail");
  if (!pane) return;
  if (!keepDetail) {
    pane.className = "detail dissector-detail ref-float-detail";
    pane.innerHTML = "加载中…";
  }
  try {
    const d = await api(`/api/materials/${linkId}`);
    let detail = await fetchMaterialAnalysis(linkId, pane);
    const item = state.items.find((i) => i.link_id === linkId);
    if (item) {
      item.analyze_provider = detail.analyze_provider || "doubao_video";
      item.has_analysis = true;
    }
    pane.className = "detail dissector-detail";
    pane.innerHTML = renderMaterialDetail(d, detail);
    if (document.getElementById("scriptProductSelect")?.value) {
      await refreshScriptPreview();
    } else {
      updateLoopBarFromForm(state.lastPreview || {});
    }
    document.getElementById("retryAnalyzeBtn")?.addEventListener("click", async () => {
      const btn = document.getElementById("retryAnalyzeBtn");
      if (btn) { btn.disabled = true; btn.textContent = "拆解中…"; }
      try {
        await api(`/api/materials/${linkId}/analyze`, { method: "POST" });
        await selectMaterial(linkId);
      } catch (err) {
        alert(err.message);
        if (btn) { btn.disabled = false; btn.textContent = "重试拆解"; }
      }
    });
    document.getElementById("copyTranscriptBtn")?.addEventListener("click", (e) => {
      const text = detail?.full_transcript || d.analysis?.full_transcript || "";
      copyText(text, e.currentTarget);
    });
    document.getElementById("goScriptBtn")?.addEventListener("click", async () => {
      state.selectedMaterialId = linkId;
      const row = state.items.find((i) => i.link_id === linkId);
      if (row?.content_line) state.selectedProductId = row.content_line;
      syncMaterialSelectFromState();
      repopulateScriptMaterials();
      if (document.getElementById("scriptProductSelect")?.value) {
        await refreshScriptPreview();
      }
      setScriptStep("ref");
      if (tagsSelectionOk()) {
      await runStartCreate();
    } else {
        setScriptStep("product");
        const hint = document.getElementById("loopHint");
        if (hint) hint.textContent = "请先点击底部「产品」完成场景标签。";
      }
      updateLoopBarFromForm(state.lastPreview || {});
    });
    setScriptStep("ref", { scroll: false });
    await refreshHealth();
  } catch (err) {
    pane.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
  }
}

// ── Products ─────────────────────────────────────────────────────────────

async function loadProductsView() {
  const data = await api("/api/products");
  state.products = data.items || [];
  const root = document.getElementById("productList");
  if (!state.products.length) {
    root.innerHTML = '<div class="detail-empty">暂无产品，请在设置同步产品资料</div>';
    return;
  }
  if (!state.selectedProductId) {
    const def = state.products.find((p) => p.product_id === "便携恒温杯") || state.products[0];
    state.selectedProductId = def.product_id;
  }
  root.innerHTML = state.products.map((p) => `
    <button type="button" class="card compact ${p.product_id === state.selectedProductId ? "active" : ""}" data-pid="${esc(p.product_id)}">
      <div><h3>${esc(p.product_name || p.product_id)}</h3>
      <div class="meta">${esc(p.product_id)}</div></div>
    </button>`).join("");
  root.querySelectorAll(".card").forEach((c) =>
    c.addEventListener("click", () => { state.selectedProductId = c.dataset.pid; loadProductsView(); })
  );
  renderProductEditor();
}

function renderProductEditor() {
  const pane = document.getElementById("productEditor");
  const p = state.products.find((x) => x.product_id === state.selectedProductId);
  if (!p) { pane.innerHTML = "选择左侧产品"; return; }
  const fields = [
    ["product_name", "产品名称"],
    ["target_audience", "目标人群"],
    ["core_selling_points", "核心卖点"],
    ["pain_points", "痛点"],
    ["usage_scenarios", "使用场景"],
    ["forbidden_terms", "禁用词"],
    ["price_range", "价格带"],
    ["competitor_ref", "竞品参考"],
  ];
  pane.className = "detail";
  pane.innerHTML = `
    <form id="productForm" class="form-grid">
      ${fields.map(([k, label]) => `
        <label>${label}<textarea name="${k}" rows="${k.includes("points") || k.includes("terms") ? 4 : 2}">${esc(p[k] || "")}</textarea></label>`).join("")}
      <button type="submit" class="primary">保存</button>
      <p id="productSaveHint" class="muted"></p>
    </form>`;
  document.getElementById("productForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    const hint = document.getElementById("productSaveHint");
    try {
      await api(`/api/products/${encodeURIComponent(p.product_id)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      hint.textContent = "已保存";
      await loadProductsView();
    } catch (err) {
      hint.textContent = err.message;
    }
  });
}

// ── Script generation ────────────────────────────────────────────────────

function materialMatchesProduct(item, productId) {
  return !item.content_line || item.content_line === productId;
}

function materialOptionsHtml(productId) {
  const analyzed = state.items.filter((i) => i.has_analysis);
  const pool = state.showAllMaterials
    ? analyzed
    : analyzed.filter((i) => materialMatchesProduct(i, productId));
  const sorted = [...pool].sort((a, b) => a.link_id - b.link_id);
  return sorted.map((i) =>
    `<option value="${i.link_id}" ${i.link_id === state.selectedMaterialId ? "selected" : ""}>#${i.link_id} ${esc((i.title || "").slice(0, 42))}</option>`
  ).join("");
}

function pickDefaultMaterialId(pool) {
  const prefer = (pred) => pool.find(pred);
  const hit = prefer((i) => i.link_id === state.selectedMaterialId)
    || prefer((i) => i.has_script && !i.delivery_ready)
    || prefer((i) => !i.delivery_ready)
    || pool[0];
  return hit?.link_id;
}

function repopulateScriptMaterials() {
  const ms = document.getElementById("scriptMaterialSelect");
  const productId = currentProductId();
  const prev = Number(ms.value);
  const pool = getMaterialPreviewPool();
  const hint = document.getElementById("materialFilterHint");
  if (hint) {
    hint.textContent = productId
      ? (state.showAllMaterials ? `共 ${pool.length} 条可选` : `同品类 ${pool.length} 条`)
      : "";
  }
  if (!productId) {
    ms.innerHTML = "";
    return;
  }
  ms.innerHTML = pool.map((i) =>
    `<option value="${i.link_id}" ${i.link_id === state.selectedMaterialId ? "selected" : ""}>#${i.link_id} ${esc((i.title || "").slice(0, 42))}</option>`
  ).join("");
  const still = [...ms.options].some((o) => Number(o.value) === prev);
  if (still) ms.value = String(prev);
  else {
    const next = pickDefaultMaterialId(pool);
    if (next) {
      ms.value = String(next);
      state.selectedMaterialId = next;
    } else {
      ms.value = "";
      state.selectedMaterialId = null;
    }
  }
  syncDockRefSlot();
  renderMaterialListPreview();
}

async function populateScriptProductSelect() {
  const ps = document.getElementById("scriptProductSelect");
  if (!ps) return;
  try {
    const pr = await api("/api/products");
    state.products = pr.items || [];
  } catch {
    if (!state.products.length) {
      const filters = await api("/api/filters").catch(() => ({}));
      state.products = filters.products || [];
    }
  }
  if (!state.products.length) {
    ps.innerHTML = '<option value="">请先在「设置」同步产品资料</option>';
    return;
  }
  ps.innerHTML = state.products.map((p) =>
    `<option value="${esc(p.product_id)}">${esc(p.product_name || p.product_id)}</option>`
  ).join("");
  if (state.selectedProductId && [...ps.options].some((o) => o.value === state.selectedProductId)) {
    ps.value = state.selectedProductId;
  } else {
    const thermos = state.products.find((p) => p.product_id === "便携恒温杯");
    ps.value = thermos ? thermos.product_id : state.products[0].product_id;
    state.selectedProductId = ps.value;
  }
  syncDockProductSlot();
  syncDockRefSlot();
}

async function loadScriptView() {
  if (!state.items.length) await loadMaterials();
  const showAll = document.getElementById("showAllMaterials");
  const refShowAll = document.getElementById("refFloatShowAllMaterials");
  if (showAll) showAll.checked = state.showAllMaterials;
  if (refShowAll) refShowAll.checked = state.showAllMaterials;
  const analyzed = document.getElementById("analyzedOnly");
  const refAnalyzed = document.getElementById("refFloatAnalyzedOnly");
  if (analyzed) analyzed.checked = state.filters.analyzedOnly;
  if (refAnalyzed) refAnalyzed.checked = state.filters.analyzedOnly;
  const ms = document.getElementById("scriptMaterialSelect");
  await populateScriptProductSelect();
  repopulateScriptMaterials();
  if (state.selectedMaterialId && ms?.querySelector(`option[value="${state.selectedMaterialId}"]`)) {
    ms.value = String(state.selectedMaterialId);
  }
  if (state.selectedMaterialId && state.selectedProductId) {
    await refreshScriptPreview();
  }
  syncWorkspaceRefChip();
  syncDockProductSlot();
  syncDockRefSlot();
  renderGenerateViralGrid();
}

async function refreshScriptPreview() {
  const linkId = Number(document.getElementById("scriptMaterialSelect").value);
  const productId = document.getElementById("scriptProductSelect").value;
  state.selectedMaterialId = linkId;
  const analysisEl = document.getElementById("scriptAnalysis");
  const productEl = document.getElementById("scriptProduct");
  if (!productId || !linkId) {
    if (productEl) {
      productEl.className = "script-tag-grid script-tag-grid-float detail-empty";
      productEl.innerHTML = productId ? "选择对标后查看结构摘要" : "选择产品后配置场景标签";
    }
    if (analysisEl) {
      analysisEl.innerHTML = linkId
        ? '<div class="detail-empty">选择产品后显示结构迁移摘要</div>'
        : '<div class="detail-empty">选择对标后显示</div>';
    }
    return;
  }
  try {
    const prev = await api(`/api/materials/${linkId}/preview?product_id=${encodeURIComponent(productId)}`);
    state.lastPreview = prev;
    state.scriptSlug = prev.slug;

    const warnEl = document.getElementById("scriptMismatchWarn");
    const mismatch = prev.product_match === false;
    if (mismatch) {
      warnEl.classList.remove("hidden");
      warnEl.textContent =
        `品类不一致：参考偏「${prev.content_line || "其他"}」，产品为「${productId}」。建议换同品类参考，或勾选「显示其他品类」后确认再生成。`;
    } else {
      warnEl.classList.add("hidden");
      warnEl.textContent = "";
    }
    const a = prev.material?.analysis || {};
    const brandHint = prev.brand_product && mismatch
      ? `<p class="brand-hint muted">成片品牌：${esc(prev.brand_product)}</p>`
      : "";
    analysisEl.innerHTML = `${brandHint}<div class="field-grid-compact">
      <div class="field-compact"><label>钩子 0-3s</label><p>${esc(a.hook_3s)}</p></div>
      <div class="field-compact"><label>痛点</label><p>${esc(a.pain_points)}</p></div>
      <div class="field-compact"><label>卖点</label><p>${esc(a.selling_points)}</p></div>
      <div class="field-compact"><label>结构</label><p>${esc(a.video_structure)}</p></div>
      <div class="field-compact"><label>字幕布局</label><p>${esc(a.subtitle_layout)}</p></div>
    </div>`;
    const p = prev.product || {};
    renderProductPanel(p, prev.delivery_tags || {}, prev.selected_tags || {});
    updateLoopBarFromForm(prev);
    if (prev.delivery_ready) {
      syncDownloadLinks(`/api/delivery/${prev.slug}/zip`, true);
    } else {
      syncDownloadLinks("", false);
    }
    if (prev.has_script && prev.script_pack) {
      syncScriptProduceEmpty(true);
      scriptResultBody().innerHTML = formatPackResult(prev.script_pack, prev.script_meta);
    }
    syncFinishButton(Boolean(prev.can_finish), Boolean(prev.delivery_ready));
    showSeedanceProgress(false);
    renderSeedanceFinalPreview(null, null);
  } catch (err) {
    analysisEl.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
    productEl.className = "script-tag-grid script-tag-grid-float detail-empty";
    productEl.innerHTML = "";
    const lp = state.lastPreview || {};
    syncFinishButton(Boolean(lp.can_finish), Boolean(lp.delivery_ready));
  }
}

function onScriptSelectionChange() {
  state.selectedProductId = document.getElementById("scriptProductSelect").value;
  state.tagPoolExtra = { audience: [], scenarios: [], selling: [], pains: [] };
  state.tagSelection = { audience: [], scenarios: [], selling: [], pains: [] };
  state.createPipelineActive = false;
  state.scriptTagSnapshot = null;
  state.lastScriptProductId = null;
  if (scriptResultBody()) scriptResultBody().innerHTML = "";
  showSeedanceProgress(false);
  renderSeedanceFinalPreview(null, null);
  syncScriptProduceEmpty();
}

document.getElementById("scriptMaterialSelect")?.addEventListener("change", async () => {
  const next = Number(document.getElementById("scriptMaterialSelect").value);
  if (state.selectedMaterialId !== next) resetPromptEnhanceUsed();
  state.selectedMaterialId = next;
  onScriptSelectionChange();
  await refreshScriptPreview();
});
document.getElementById("scriptProductSelect")?.addEventListener("change", async () => {
  resetPromptEnhanceUsed();
  state.selectedProductId = document.getElementById("scriptProductSelect").value;
  state.selectedMaterialId = null;
  const dockPrompt = document.getElementById("generateDockPrompt");
  if (dockPrompt) dockPrompt.value = "";
  const pane = document.getElementById("materialDetail");
  if (pane) {
    pane.className = "detail-empty ref-float-detail";
    pane.innerHTML = "选择左侧对标视频查看拆解";
  }
  onScriptSelectionChange();
  repopulateScriptMaterials();
  renderRefFloatMaterialList();
  syncRefFloatProductLine();
  renderGenerateViralGrid();
  await refreshScriptPreview();
  syncProductFloatStatus();
  syncDockProductSlot();
  syncDockRefSlot();
});

async function runScriptGenerate() {
  const linkId = Number(document.getElementById("scriptMaterialSelect").value);
  const productId = document.getElementById("scriptProductSelect").value;
  const audienceTags = readSelectedTags("audience");
  const scenarioTags = readSelectedTags("scenario");
  const sellingTags = readSelectedTags("selling");
  const painTags = readSelectedTags("pain");
  const genBtns = document.querySelectorAll(".js-script-generate");
  const resultEl = scriptResultBody();
  if (!audienceTags.length || !scenarioTags.length || !sellingTags.length || !painTags.length) {
    await openProductFloatPanel();
    return;
  }
  if (!document.getElementById("scriptMaterialSelect")?.value) {
    openRefFloatPanel();
    return;
  }
  if (!materialInProductPool(linkId, productId)) {
    setScriptActionStatus("所选对标与当前产品不匹配，请重新选择同品类对标。");
    openRefFloatPanel();
    return;
  }
  await refreshScriptPreview();
  if (state.lastPreview?.product_match === false) {
    const warn = document.getElementById("scriptMismatchWarn");
    const msg = warn?.textContent || "对标与产品品类不一致，请更换对标或勾选「显示其他品类」后确认。";
    if (resultEl) resultEl.innerHTML = `<div class="result error">${esc(msg)}</div>`;
    setScriptActionStatus(msg);
    openScriptFloatPanel();
    return;
  }
  setScriptStep("produce");
  genBtns.forEach((b) => { b.disabled = true; });
  if (resultEl) resultEl.innerHTML = "正在生成脚本…";
  setScriptActionStatus("");
  try {
    const vs = currentVideoSettings();
    const creativeBrief = document.getElementById("generateDockPrompt")?.value?.trim() || "";
    const res = await api(`/api/materials/${linkId}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_id: productId,
        bridge: true,
        target_country: "US",
        language: "en",
        style: "us_tiktok_spoken",
        audience_tags: audienceTags,
        scenario_tags: scenarioTags,
        selling_tags: sellingTags,
        pain_tags: painTags,
        aspect_ratio: vs.aspectRatio,
        edit_mode: vs.editMode,
        resolution: vs.resolution,
        duration_sec: vs.durationSec,
        generate_count: vs.generateCount,
        creative_brief: creativeBrief,
        prompt_enhanced: state.promptEnhanceOn,
      }),
    });
    const pack = res.script_pack || res.pack || {};
    state.scriptSlug = res.slug || slugFor(linkId);
    state.scriptTagSnapshot = captureTagSnapshot();
    state.lastScriptProductId = productId;
    if (resultEl) resultEl.innerHTML = formatPackResult(pack, res.meta);
    syncFinishButton(true, Boolean(state.lastPreview?.delivery_ready));
    syncScriptProduceEmpty(true);
    setScriptStep("produce");
    await refreshScriptPreview();
    resetPromptEnhanceUsed();
  } catch (err) {
    if (resultEl) resultEl.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
  } finally {
    genBtns.forEach((b) => { b.disabled = false; });
  }
}

async function runScriptFinish(options = {}) {
  const { keepScript = false, background = false } = options;
  const slug = currentScriptSlug();
  if (!slug) {
    setScriptActionStatus("请先生成脚本");
    if (!background) ensureScriptResultVisible();
    return false;
  }
  state.scriptSlug = slug;
  const finishBtns = document.querySelectorAll("#scriptFinishBtn, .js-script-finish");
  const resultEl = scriptResultBody();
  const savedHtml = resultEl?.innerHTML || "";
  finishBtns.forEach((b) => { b.disabled = true; });
  if (!background) openScriptFloatPanel();
  if (!keepScript) {
    resultEl.textContent = "正在生成交付包（英文字幕 + 脚本包）…";
  } else {
    setScriptActionStatus("正在生成交付包（英文字幕 + 脚本包）…");
  }
  try {
    const res = await api(`/api/delivery/${slug}/finish`, { method: "POST" });
    if (!keepScript) {
      resultEl.innerHTML = `<div class="result">交付完成：${esc(res.message || "字幕与交付包已生成")}
        <p class="muted">正在继续生成 AI 分镜视频…</p>
        <p class="loop-next">
          <button type="button" class="text-link" id="goFinishedBtn">打开成稿库</button>
          ·
          <button type="button" class="text-link" id="goFeedbackBtn">填写投放反馈</button>
        </p></div>`;
      document.getElementById("goFinishedBtn")?.addEventListener("click", () => switchView("draft-feedback", { sub: "finished" }));
      document.getElementById("goFeedbackBtn")?.addEventListener("click", () => {
        state.selectedFeedbackSlug = slug;
        switchView("draft-feedback", { sub: "feedback" });
      });
    } else {
      resultEl.innerHTML = savedHtml;
      setScriptActionStatus(`交付完成：${res.message || "字幕与交付包已生成"}`);
    }
    syncDownloadLinks(`/api/delivery/${slug}/zip`, true);
    await refreshScriptPreview();
    await refreshHealth();
    return true;
  } catch (err) {
    if (!keepScript) {
      resultEl.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
    } else {
      setScriptActionStatus(`交付失败：${err.message}`);
    }
    await refreshScriptPreview();
    return false;
  } finally {
    const lp = state.lastPreview || {};
    syncFinishButton(Boolean(lp.can_finish), Boolean(lp.delivery_ready));
  }
}

async function runSeedanceGenerate(options = {}) {
  const force = options.force ?? document.getElementById("seedanceForceRegen")?.checked;
  const background = Boolean(options.background);
  const slug = currentScriptSlug();
  if (!slug) {
    setScriptActionStatus("请先生成脚本");
    if (!background) ensureScriptResultVisible();
    return false;
  }
  state.scriptSlug = slug;
  if (!background) ensureScriptResultVisible();
  showSeedanceProgress(true, {
    status: force ? "正在强制重生成…" : "正在生成分镜视频…",
    indeterminate: true,
    pipeline: state.healthCache?.seedance?.label || "",
  });
  setScriptActionStatus(force ? "强制重生成中…" : "正在生成分镜视频，请耐心等待…");
  const hintEl = document.getElementById("seedanceHint");
  try {
    const qs = force ? "?force=1" : "";
    const data = await api(`/api/delivery/${encodeURIComponent(slug)}/seedance/run${qs}`, { method: "POST" });
    renderSeedance(slug, data.seedance, state.healthCache);
    const failed = (data.results || []).filter((r) => r.status === "error");
    const skipped = (data.results || []).filter((r) => r.status === "skipped");
    const okCount = (data.results || []).filter((r) => r.status === "ok").length;
    const finalReady = Boolean(data.seedance?.final_video?.ready || data.assemble?.ok);
    let msg;
    if (failed.length) {
      msg = failed.every((r) => (r.message || "").includes("ARK_API_KEY"))
        ? `火山方舟密钥失效：${failed[0].message}。请到「设置」→ 测试连接，或更新 overseas-loc-mvp/.env 中的 ARK_API_KEY 后重启工作台。`
        : `部分失败：${failed.map((r) => `镜${r.number} ${r.message}`).join("；")}`;
    } else if (finalReady || okCount > 0) {
      msg = force
        ? `已强制重生成 ${okCount || "5"} 镜并拼接成片，可预览 mp4 或下载 zip`
        : "视频生成完成，可预览 mp4 或下载 zip";
    } else if (skipped.length) {
      msg = force
        ? "本次未覆盖旧视频：请重启工作台（启动页面.cmd）后再勾选强制重生成，或运行 本地生成视频.cmd <编号> --force"
        : "未生成新视频：镜头已有 mp4。请勾选「强制重生成」后重试，或先重新生成脚本以更新 Prompt。";
    } else {
      msg = "视频生成完成，可预览 mp4 或下载 zip";
    }
    if (hintEl) hintEl.textContent = msg;
    showSeedanceProgress(true, {
      status: finalReady ? "成片已就绪" : msg,
      pipeline: data.seedance?.pipeline || "",
      percent: finalReady ? 100 : undefined,
      indeterminate: !finalReady && !failed.length,
    });
    setScriptActionStatus(msg);
    if (!document.getElementById("scriptDownloadBtnBottom")?.classList.contains("hidden")) {
      syncDownloadLinks(`/api/delivery/${slug}/zip?ts=${Date.now()}`, true);
    }
    if (!background) openScriptFloatPanel();
    return !failed.length;
  } catch (err) {
    showSeedanceProgress(true, { status: `失败：${err.message}`, percent: 0 });
    setScriptActionStatus(`视频生成失败：${err.message}`);
    return false;
  }
}

async function runProduceVideo(options = {}) {
  const background = Boolean(options.background);
  const slug = currentScriptSlug();
  if (!slug) {
    setScriptActionStatus("请先生成脚本后再产出视频");
    if (!background) ensureScriptResultVisible();
    return false;
  }
  state.scriptSlug = slug;
  if (!background) {
    setScriptStep("produce", { scroll: false });
    ensureScriptResultVisible();
  }
  showSeedanceProgress(true, {
    status: "正在准备交付与分镜生成…",
    indeterminate: true,
    pipeline: state.healthCache?.seedance?.label || "",
  });
  setScriptActionStatus("正在启动：交付包 → AI 分镜视频 → 拼接成片（约 15–30 分钟）…");
  if (!background) openScriptFloatPanel();
  try {
    const lp = state.lastPreview || {};
    if (!lp.delivery_ready) {
      const ok = await runScriptFinish({ keepScript: true, background });
      if (!ok) {
        setScriptActionStatus("交付未完成，无法产出视频。");
        return false;
      }
      await refreshScriptPreview();
    }
    return await runSeedanceGenerate({
      force: document.getElementById("seedanceForceRegen")?.checked,
      background,
    });
  } catch (err) {
    setScriptActionStatus(`产出视频失败：${err.message}`);
    showSeedanceProgress(true, { status: `失败：${err.message}`, persist: true });
    return false;
  } finally {
    syncFinishButton(Boolean(state.lastPreview?.can_finish), Boolean(state.lastPreview?.delivery_ready));
  }
}

document.getElementById("scriptStepProductNext")?.addEventListener("click", () => {
  if (!tagsSelectionOk()) {
    openProductFloatPanel();
    return;
  }
  setScriptStep("ref");
  updateLoopBarFromForm(state.lastPreview || {});
});

document.getElementById("scriptStepRefPrev")?.addEventListener("click", () => {
  setScriptStep("product");
  updateLoopBarFromForm(state.lastPreview || {});
});

document.getElementById("scriptStepProducePrev")?.addEventListener("click", () => {
  setScriptStep("ref");
  updateLoopBarFromForm(state.lastPreview || {});
});

document.getElementById("scriptStepProduceBack")?.addEventListener("click", () => {
  setScriptStep("ref");
  updateLoopBarFromForm(state.lastPreview || {});
});

document.addEventListener("click", (e) => {
  const gen = e.target.closest(".js-script-generate");
  if (gen) {
    e.preventDefault();
    runStartCreate();
  }
});

// ── Finished library ───────────────────────────────────────────────────────

async function loadFinishedView() {
  const data = await api("/api/library/finished");
  const items = data.items || [];
  const root = document.getElementById("finishedList");
  if (!items.length) {
    root.innerHTML = '<div class="detail-empty">暂无成稿。在脚本生成页完成交付后会自动入库。</div>';
    return;
  }
  root.innerHTML = `<table class="data-table"><thead><tr>
    <th>项目</th><th>标题</th><th>产品</th><th>保存时间</th><th>操作</th>
  </tr></thead><tbody>${items.map((r) => `
    <tr>
      <td>${esc(r.slug)}</td>
      <td>${esc((r.title || "").slice(0, 48))}</td>
      <td>${esc(r.product_name || r.product_id)}</td>
      <td>${esc((r.saved_at || "").slice(0, 19))}</td>
      <td><a href="/api/delivery/${esc(r.slug)}/zip">下载 zip</a></td>
    </tr>`).join("")}</tbody></table>`;
}

// ── Feedback ─────────────────────────────────────────────────────────────

async function ensureFeedbackTagDefs() {
  if (state.feedbackTagDefs) return state.feedbackTagDefs;
  try {
    const data = await api("/api/library/feedback-tags");
    state.feedbackTagDefs = data.items || [];
  } catch {
    state.feedbackTagDefs = [];
  }
  return state.feedbackTagDefs;
}

function collectFeedbackIssueTags(form) {
  return [...form.querySelectorAll('input[name="issue_tags"]:checked')].map((el) => el.value);
}

function syncFeedbackEditorTab(tab) {
  state.feedbackEditorTab = tab;
  document.querySelectorAll("#feedbackEditorTabs button[data-fb-tab]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.fbTab === tab);
  });
  document.querySelectorAll("#feedbackForm .feedback-form-section").forEach((sec) => {
    sec.classList.toggle("hidden", sec.dataset.fbPanel !== tab);
  });
}

async function loadFeedbackView() {
  const data = await api("/api/library/feedback");
  const items = data.items || [];
  const root = document.getElementById("feedbackList");
  if (!items.length) {
    root.innerHTML = '<div class="detail-empty">暂无反馈记录</div>';
    return;
  }
  if (!state.selectedFeedbackSlug) state.selectedFeedbackSlug = items[0].slug;
  root.innerHTML = items.map((r) => {
    const tags = (r.issue_tags || []).length ? ` · ${(r.issue_tags || []).length}项问题` : "";
    return `
    <button type="button" class="card compact ${r.slug === state.selectedFeedbackSlug ? "active" : ""}" data-slug="${esc(r.slug)}">
      <div><h3>${esc((r.title || r.slug).slice(0, 42))}</h3>
      <div class="meta">${esc(r.adopted || "待定")}${tags} · ${esc((r.updated_at || "").slice(0, 10))}</div></div>
    </button>`;
  }).join("");
  root.querySelectorAll(".card").forEach((c) =>
    c.addEventListener("click", () => { state.selectedFeedbackSlug = c.dataset.slug; loadFeedbackView(); })
  );
  renderFeedbackEditor();
}

async function renderFeedbackEditor() {
  const pane = document.getElementById("feedbackEditor");
  const slug = state.selectedFeedbackSlug;
  if (!slug) return;
  const tab = state.feedbackEditorTab || "review";
  try {
    const r = await api(`/api/library/feedback/${encodeURIComponent(slug)}`);
    const pub = r.publish || {};
    const tagDefs = await ensureFeedbackTagDefs();
    const selectedTags = new Set(r.issue_tags || []);
    const tagHtml = tagDefs.map((t) => `
      <label class="feedback-issue-chip">
        <input type="checkbox" name="issue_tags" value="${esc(t.id)}" ${selectedTags.has(t.id) ? "checked" : ""}>
        <span>${esc(t.label)}</span>
      </label>`).join("");
    const scLine = (r.scenario_tags || []).join("、") || "—";
    let loopPreview = "";
    if (r.product_id) {
      try {
        const prev = await api(
          `/api/library/feedback-constraints?product_id=${encodeURIComponent(r.product_id)}&scenario_tags=${encodeURIComponent((r.scenario_tags || []).join(","))}`,
        );
        if (prev.matched_count > 0) {
          loopPreview = `<p class="feedback-loop-banner">闭环已启用：下次生成「${esc(r.product_id)}」且场景匹配时，将自动带入 <strong>${prev.matched_count}</strong> 条已采纳约束。</p>`;
        } else if (r.adopted === "已采纳" || r.adopted === "修改后采纳") {
          loopPreview = `<p class="feedback-loop-banner muted">本条已采纳，将在同产品同场景下次生成时生效。</p>`;
        }
      } catch { /* ignore */ }
    }
    pane.className = "detail feedback-editor";
    pane.innerHTML = `
      <h3>${esc(r.title || slug)}</h3>
      <p class="muted feedback-editor-meta">产品 ${esc(r.product_id || "—")} · 场景 ${esc(scLine)}</p>
      ${loopPreview}
      <p class="muted feedback-editor-hint">请将采纳状态设为「已采纳」或「修改后采纳」，并勾选问题类型；保存后会在下次同产品、同场景生成时自动注入脚本与分镜约束。</p>
      <nav class="feedback-editor-tabs" id="feedbackEditorTabs" aria-label="反馈类型">
        <button type="button" class="${tab === "review" ? "active" : ""}" data-fb-tab="review">成片审核</button>
        <button type="button" class="${tab === "metrics" ? "active" : ""}" data-fb-tab="metrics">投放数据</button>
        <button type="button" data-fb-tab="iterate" disabled title="规划中">迭代优化</button>
      </nav>
      <form id="feedbackForm" class="form-grid">
        <div class="feedback-form-section${tab === "review" ? "" : " hidden"}" data-fb-panel="review">
          <fieldset class="feedback-issue-fieldset">
            <legend>问题类型（结构化）</legend>
            <div class="feedback-issue-grid">${tagHtml || '<span class="muted">加载标签…</span>'}</div>
          </fieldset>
          <label>具体问题描述
            <textarea name="manual_edits" rows="4" placeholder="补充细节，如：倒出口画成宽口直倒、奶瓶放入杯内等">${esc(r.manual_edits)}</textarea>
          </label>
          <label>采纳状态
            <select name="adopted">
              ${["待定", "已采纳", "未采纳", "修改后采纳"].map((o) =>
                `<option ${r.adopted === o ? "selected" : ""}>${o}</option>`).join("")}
            </select>
          </label>
          <label>备注<textarea name="notes" rows="2" placeholder="补充说明">${esc(r.notes)}</textarea></label>
        </div>
        <div class="feedback-form-section${tab === "metrics" ? "" : " hidden"}" data-fb-panel="metrics">
          <label>播放量<input name="publish_views" value="${esc(pub.views)}"></label>
          <label>互动率<input name="publish_engagement" placeholder="如 3.2%" value="${esc(pub.engagement)}"></label>
          <label>投放备注<textarea name="publish_notes" rows="3" placeholder="投放渠道、表现与复盘">${esc(pub.notes)}</textarea></label>
          <p class="muted">高互动率已采纳反馈会作为同产品模板的结构/场景参考（权重次于本次竞品拆解）。</p>
        </div>
        <div class="feedback-form-section${tab === "iterate" ? "" : " hidden"}" data-fb-panel="iterate">
          <p class="muted module-placeholder-inner compact">基础闭环已接入：已采纳反馈 → 下次同产品同场景生成自动注入约束。完整自动迭代（一键重生成）规划中。</p>
        </div>
        <div class="feedback-form-actions">
          <button type="submit" class="primary">保存反馈</button>
          <p id="fbHint" class="muted"></p>
        </div>
      </form>`;
    document.getElementById("feedbackEditorTabs")?.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-fb-tab]:not(:disabled)");
      if (btn) syncFeedbackEditorTab(btn.dataset.fbTab);
    });
    document.getElementById("feedbackForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        await api(`/api/library/feedback/${encodeURIComponent(slug)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            manual_edits: fd.get("manual_edits"),
            adopted: fd.get("adopted"),
            notes: fd.get("notes"),
            issue_tags: collectFeedbackIssueTags(e.target),
            publish_views: fd.get("publish_views"),
            publish_engagement: fd.get("publish_engagement"),
            publish_notes: fd.get("publish_notes"),
          }),
        });
        document.getElementById("fbHint").textContent = "已保存";
        await loadFeedbackView();
      } catch (err) {
        document.getElementById("fbHint").textContent = err.message;
      }
    });
  } catch (err) {
    pane.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
  }
}

// ── Settings / jobs ──────────────────────────────────────────────────────

function renderDoubaoSettings(health) {
  const el = document.getElementById("doubaoSettingsStatus");
  if (!el) return;
  const db = health?.decompose?.doubao || {};
  const policy = health?.decompose?.policy || {};
  if (policy.paused) {
    el.innerHTML = `<span class="warn-inline">拆解已暂停</span> · ${esc(policy.message || "不重复分析已有素材，新素材也不自动分析")}`;
    return;
  }
  if (!db.configured) {
    el.innerHTML = `未配置 · 在 <code>overseas-loc-mvp/.env</code> 填写 <code>ARK_API_KEY</code><br><span class="muted">${esc(db.setup || "")}</span>`;
    return;
  }
  el.innerHTML = `已配置 · 默认模型 <code>${esc(db.turbo_model || "")}</code><br>高精度 <code>${esc(db.pro_model || "")}</code> · ASR ${db.asr_configured ? "已配" : "未配（可选）"}`;
}

async function loadSettingsView() {
  ensureCollectorPanel();
  const h = await api("/api/health");
  state.healthCache = h;
  renderDoubaoSettings(h);
  renderSeedanceSettings(h);
  const policyNote = h.decompose?.policy?.paused
    ? `<br><span class="warn-inline">拆解已暂停</span>（已有结果不重复调豆包，新素材不分析）`
    : "";
  document.getElementById("envInfo").innerHTML = `
    UI v${h.ui_version} · 素材 ${h.materials}（已拆解 ${h.analyzed}）· 产品 ${h.products} · 成稿 ${h.finished}<br>
    结构拆解：${h.decompose?.label || "规则模板"}${policyNote}<br>
    脚本生成：${h.llm.available ? h.llm.model : h.llm.fallback}<br>
    交付引擎：${h.delivery_engine?.label || "overseas-loc-mvp"}<br>
    SeedDance：${h.seedance?.configured ? `已配置 ${h.seedance.provider}` : "未配置"}`;
  await pollJobStatus();
}

async function pollJobStatus() {
  const st = await api("/api/jobs/status");
  const el = document.getElementById("jobStatus");
  const log = document.getElementById("jobLog");
  if (st.status === "running") {
    el.textContent = `运行中：${jobLabel(st.job)}（${st.started_at || ""}）`;
    log.textContent = st.output || "";
    if (!state.jobPoll) {
      state.jobPoll = setInterval(async () => {
        const s = await api("/api/jobs/status");
        document.getElementById("jobStatus").textContent = s.status === "running"
          ? `运行中：${jobLabel(s.job)}` : (s.exit_code === 0 ? `✅ ${jobLabel(s.job)} 完成` : `❌ ${jobLabel(s.job)} 失败 (code ${s.exit_code})`);
        document.getElementById("jobLog").textContent = s.output || "";
        if (s.status !== "running") {
          clearInterval(state.jobPoll);
          state.jobPoll = null;
          await refreshHealth();
          await loadMaterials();
        }
      }, 2000);
    }
  } else {
    el.textContent = st.job ? `${st.status}: ${jobLabel(st.job)}` : "就绪";
    log.textContent = st.output || "";
  }
}

document.querySelectorAll(".job-btn").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const job = btn.dataset.job;
    try {
      await api(`/api/jobs/${job}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ engine: "auto" }),
      });
      document.getElementById("jobStatus").textContent = `已启动：${job}`;
      await pollJobStatus();
    } catch (err) {
      document.getElementById("jobStatus").textContent = err.message;
    }
  });
});

// ── Init ─────────────────────────────────────────────────────────────────

document.getElementById("openProductsBtn")?.addEventListener("click", () => {
  closeSettingsDrawer();
  switchView("products");
});
document.getElementById("openMaterialLibraryFromSettings")?.addEventListener("click", () => {
  closeSettingsDrawer();
  openMaterialLibraryDrawer();
});
document.getElementById("openProductsFromSettings")?.addEventListener("click", () => {
  closeSettingsDrawer();
  switchView("products");
});

document.getElementById("settingsOpenBtn")?.addEventListener("click", () => openSettingsDrawer());
document.getElementById("settingsCloseBtn")?.addEventListener("click", () => closeSettingsDrawer());
document.getElementById("settingsBackdrop")?.addEventListener("click", () => closeSettingsDrawer());
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  closeSettingsDrawer();
  closeProductFloatPanel();
  closeRefFloatPanel();
  closeScriptFloatPanel();
  closeMaterialLibraryDrawer();
});

document.getElementById("categorySelect")?.addEventListener("change", (e) => {
  state.filters.category = e.target.value;
  const refCat = document.getElementById("refFloatCategorySelect");
  if (refCat) refCat.value = e.target.value;
  loadMaterials();
});
document.getElementById("refFloatCategorySelect")?.addEventListener("change", (e) => {
  state.filters.category = e.target.value;
  const cat = document.getElementById("categorySelect");
  if (cat) cat.value = e.target.value;
  loadMaterials();
});
document.getElementById("keywordInput")?.addEventListener("input", debounce((e) => {
  state.filters.q = e.target.value.trim();
  const refKw = document.getElementById("refFloatKeywordInput");
  if (refKw) refKw.value = state.filters.q;
  loadMaterials();
}));
document.getElementById("refFloatKeywordInput")?.addEventListener("input", debounce((e) => {
  state.filters.q = e.target.value.trim();
  const kw = document.getElementById("keywordInput");
  if (kw) kw.value = state.filters.q;
  loadMaterials();
}));
document.getElementById("analyzedOnly")?.addEventListener("change", (e) => {
  state.filters.analyzedOnly = e.target.checked;
  const ref = document.getElementById("refFloatAnalyzedOnly");
  if (ref) ref.checked = e.target.checked;
  loadMaterials();
});
document.getElementById("refFloatAnalyzedOnly")?.addEventListener("change", (e) => {
  state.filters.analyzedOnly = e.target.checked;
  const analyzed = document.getElementById("analyzedOnly");
  if (analyzed) analyzed.checked = e.target.checked;
  loadMaterials();
});
document.getElementById("showAllMaterials")?.addEventListener("change", async (e) => {
  state.showAllMaterials = e.target.checked;
  const ref = document.getElementById("refFloatShowAllMaterials");
  if (ref) ref.checked = e.target.checked;
  repopulateScriptMaterials();
  renderRefFloatMaterialList();
  syncRefFloatProductLine();
  renderGenerateViralGrid();
  if (state.selectedMaterialId && document.getElementById("scriptProductSelect")?.value) {
    await refreshScriptPreview();
  }
});
document.getElementById("refFloatShowAllMaterials")?.addEventListener("change", async (e) => {
  state.showAllMaterials = e.target.checked;
  const showAll = document.getElementById("showAllMaterials");
  if (showAll) showAll.checked = e.target.checked;
  repopulateScriptMaterials();
  renderRefFloatMaterialList();
  if (state.selectedMaterialId && document.getElementById("scriptProductSelect")?.value) {
    await refreshScriptPreview();
  }
});

document.getElementById("scriptProduct")?.addEventListener("click", (e) => {
  const chip = e.target.closest(".tag-chip");
  if (chip) {
    toggleTagChip(chip.dataset.group, chip.dataset.value);
    updateLoopBarFromForm(state.lastPreview || {});
    refreshTagGroupsUI();
    syncProductFloatStatus();
    syncDockProductSlot();
    return;
  }
  const addBtn = e.target.closest(".tag-add-btn");
  if (addBtn) {
    const group = addBtn.dataset.group;
    const input = document.querySelector(`.tag-input[data-group="${group}"]`);
    addTagInline(group, input?.value);
    if (input) input.value = "";
  }
});

document.getElementById("scriptProduct")?.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || !e.target.classList.contains("tag-input")) return;
  e.preventDefault();
  const group = e.target.dataset.group;
  addTagInline(group, e.target.value);
  e.target.value = "";
});

async function runSeedanceTest(hintEl) {
  const target = hintEl || document.getElementById("seedanceHint");
  const prov = state.healthCache?.seedance?.provider === "volcengine-ark" ? "火山方舟 Ark" : "SeedDance";
  if (target) target.textContent = `正在测试 ${prov} 连接（约 30–120 秒）…`;
  try {
    const data = await api("/api/seedance/test");
    const msg = data.ok
      ? `✅ ${data.message || "连接成功"}`
      : `❌ ${data.message || "连接失败"}`;
    if (target) target.textContent = msg;
    await refreshHealth();
    renderSeedanceSettings(state.healthCache);
    if (state.scriptSlug) await loadSeedanceForSlug(state.scriptSlug);
    return data;
  } catch (err) {
    if (target) target.textContent = `❌ ${err.message}`;
    throw err;
  }
}

document.getElementById("btnDoubaoTestSettings")?.addEventListener("click", async () => {
  const el = document.getElementById("doubaoSettingsStatus");
  if (el) el.textContent = "正在测试豆包连接…";
  try {
    const data = await api("/api/doubao/test");
    if (el) el.textContent = data.ok ? `✅ ${data.message}` : `❌ ${data.message}`;
    await refreshHealth();
    renderDoubaoSettings(state.healthCache);
  } catch (err) {
    if (el) el.textContent = `❌ ${err.message}`;
  }
});

document.getElementById("btnSeedanceTestSettings")?.addEventListener("click", () => {
  runSeedanceTest(document.getElementById("seedanceSettingsStatus"));
});

async function bootstrapApp() {
  try {
    initModuleStudios();
  } catch (err) {
    console.error("initModuleStudios failed", err);
  }
  try {
    await refreshHealth();
  } catch {
    /* stats show ? — still load materials below */
  }
  try {
    await loadFilters();
    await loadMaterials();
  } catch (err) {
    console.error("bootstrap load failed", err);
    const root = document.getElementById("materialList");
    if (root) {
      root.innerHTML = `<div class="detail-empty">素材加载失败：${esc(err.message)}。请确认服务已启动（8788）后刷新页面。</div>`;
    }
  }
  syncDockScrollPadding();
  window.addEventListener("resize", syncDockScrollPadding);
  activateView("generate");
}

bootstrapApp();
