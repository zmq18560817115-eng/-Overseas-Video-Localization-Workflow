const state = {
  view: "workspace",
  items: [],
  products: [],
  templates: [],
  selectedMaterialId: null,
  selectedProductId: null,
  selectedFeedbackSlug: null,
  scriptSlug: null,
  showAllMaterials: false,
  selectedAudience: [],
  selectedScenarios: [],
  lastPreview: null,
  tagPoolExtra: { audience: [], scenarios: [], selling: [], pains: [] },
  tagSelection: { audience: [], scenarios: [], selling: [], pains: [] },
  filters: { category: "", q: "", analyzedOnly: false },
  jobPoll: null,
  healthCache: null,
  scriptStep: "ref",
};

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

function toggleTagChip(group, value) {
  const cfg = TAG_GROUPS[group];
  const dom = TAG_GROUP_DOM[group];
  if (!cfg || !dom || !value) return;
  const key = dom.savedKey;
  let sel = [...(state.tagSelection[key] || [])];
  if (cfg.single) {
    state.tagSelection[key] = sel.includes(value) ? [] : [value];
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

function ensureScriptResultVisible() {
  const wrap = scriptResultEl();
  if (wrap) wrap.classList.remove("hidden");
}

function syncFinishButton(canFinish, delivered) {
  const btns = document.querySelectorAll("#scriptFinishBtn, .js-script-finish");
  btns.forEach((btn) => {
    btn.disabled = !canFinish;
    if (!canFinish) {
      btn.textContent = "完成交付";
      btn.title = "请先生成脚本";
    } else if (delivered) {
      btn.textContent = "更新交付";
      btn.title = "脚本已更新时可重新生成交付包";
    } else {
      btn.textContent = "完成交付";
      btn.title = "生成英文字幕与交付 zip";
    }
  });
  const canProduce = Boolean(canFinish && currentScriptSlug());
  document.querySelectorAll(".js-script-produce").forEach((btn) => {
    btn.disabled = !canProduce;
    btn.title = canProduce
      ? "自动完成交付并生成分镜视频（约 15–30 分钟）"
      : "请先生成脚本";
  });
}

function setScriptActionStatus(msg) {
  const el = document.getElementById("scriptActionStatus");
  if (el) el.textContent = msg || "";
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
  panel.className = "script-tag-grid script-tag-grid-spacious";
  const groupsHtml = Object.entries(TAG_GROUPS).map(([group, cfg]) => `
    <div class="tag-panel tag-panel-spacious">
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
      <div class="tag-library-block">
        <span class="tag-library-label">素材库推荐 · 点击选用</span>
        <div id="${group}LibraryRow" class="tag-row tag-library-row"></div>
      </div>
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
}

function tagsSelectionOk() {
  const sel = readAllSelectedTags();
  return sel.audience.length > 0 && sel.scenarios.length > 0
    && sel.selling.length > 0 && sel.pains.length > 0;
}

function normalizeView(name) {
  if (name === "materials" || name === "script") return "workspace";
  return name;
}

function viewElementId(name) {
  const n = normalizeView(name);
  const map = {
    workspace: "viewWorkspace",
    products: "viewProducts",
    finished: "viewFinished",
    feedback: "viewFeedback",
  };
  return map[n] || `view${n.charAt(0).toUpperCase()}${n.slice(1)}`;
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

function syncScriptProduceEmpty(hasScript) {
  const empty = document.getElementById("scriptProduceEmpty");
  if (empty) empty.classList.toggle("hidden", Boolean(hasScript));
}

function setScriptStep(step, { scroll = true } = {}) {
  const order = ["ref", "product", "produce"];
  if (!order.includes(step)) return;
  state.scriptStep = step;
  document.querySelectorAll(".script-step-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.step === step);
  });
  document.querySelectorAll("#scriptLoopBar li").forEach((li) => {
    li.classList.toggle("current", li.dataset.step === step);
  });
  syncWorkspaceActionBar(step);
  if (scroll) {
    document.querySelector(".workspace-card")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

function updateLoopBarFromForm(prev = {}) {
  const bar = document.getElementById("scriptLoopBar");
  const hint = document.getElementById("loopHint");
  if (!bar) return;
  const sel = readAllSelectedTags();
  const hasMaterial = Boolean(document.getElementById("scriptMaterialSelect")?.value);
  const hasProduct = Boolean(document.getElementById("scriptProductSelect")?.value);
  const tagsOk = tagsSelectionOk();
  const hasScript = Boolean(prev.has_script) || Boolean(prev.delivery_ready);
  const steps = {
    ref: hasMaterial,
    product: hasProduct && tagsOk,
    produce: hasScript,
  };
  bar.querySelectorAll("li").forEach((li) => {
    const key = li.dataset.step;
    li.classList.remove("done", "current");
    if (steps[key]) li.classList.add("done");
    else if (key === state.scriptStep) li.classList.add("current");
  });
  syncScriptProduceEmpty(hasScript);
  if (hint) {
    if (state.scriptStep === "produce" && prev.delivery_ready) {
      hint.textContent = "③ 交付完成：可下载 zip、预览 AI 分镜成片，或重新生成后更新。";
    } else if (state.scriptStep === "produce" && hasScript) {
      hint.textContent = "③ 脚本已就绪 → 完成交付或直接产出视频。";
    } else if (state.scriptStep === "product") {
      hint.textContent = tagsOk
        ? "② 标签已齐，可生成脚本并进入交付页。"
        : "② 为人群、场景、卖点、痛点各至少选择一项标签。";
    } else if (!hasMaterial) {
      hint.textContent = "① 先选择对标爆款，查看右侧结构拆解。";
    } else {
      hint.textContent = "① 结构参考已选 → 点击「下一步」配置产品场景标签。";
    }
  }
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
  return document.getElementById("scriptResult");
}

function scriptResultBody() {
  return document.querySelector("#scriptResult .output-body");
}

// ── Navigation ─────────────────────────────────────────────────────────────

function switchView(name) {
  name = normalizeView(name);
  state.view = name;
  document.querySelectorAll(".view").forEach((el) => el.classList.remove("active"));
  document.getElementById(viewElementId(name))?.classList.add("active");
  document.querySelectorAll("#mainNav button").forEach((btn) => {
    btn.classList.toggle("active", normalizeView(btn.dataset.view) === name);
  });
  if (name === "workspace") loadWorkspaceView();
  if (name === "products") loadProductsView();
  if (name === "finished") loadFinishedView();
  if (name === "feedback") loadFeedbackView();
}

async function loadWorkspaceView() {
  if (!state.items.length) await loadMaterials();
  await loadScriptView();
  syncWorkspaceActionBar(state.scriptStep);
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

document.getElementById("mainNav").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-view]");
  if (btn) switchView(btn.dataset.view);
});

// ── Health / stats ───────────────────────────────────────────────────────

async function refreshHealth() {
  const h = await api("/api/health");
  state.healthCache = h;
  document.getElementById("statMaterials").textContent = h.materials;
  document.getElementById("statAnalyzed").textContent = h.analyzed;
  return h;
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
  const panel = document.getElementById("seedancePanel");
  const statusEl = document.getElementById("seedanceStatus");
  const runBtn = document.getElementById("btnSeedanceRun");
  if (!panel || !statusEl) return;

  const configured = health?.seedance?.configured;
  const pipeline = seedance?.pipeline || health?.seedance?.label || "";
  document.getElementById("seedancePipeline").textContent = pipeline;

  if (!slug || !seedance) {
    panel.classList.add("hidden");
    return;
  }

  panel.classList.remove("hidden");

  if (!configured) {
    statusEl.innerHTML = `未连接 · 请在 <code>overseas-loc-mvp/.env</code> 配置 <code>ARK_API_KEY</code> 后重启工作台`;
    document.getElementById("seedanceShots").innerHTML = "";
    if (runBtn) runBtn.disabled = true;
    document.getElementById("seedanceHint").textContent = health?.seedance?.setup || "";
    return;
  }

  const prov = health.seedance.provider === "volcengine-ark" ? "火山方舟 Ark" : (health.seedance.provider || "fal.ai");
  const modeHint = health.seedance.mode === "script" ? "脚本分镜模式" : "空镜模式";
  statusEl.innerHTML = `已连接 ${esc(prov)} · ${esc(modeHint)} · <code>${esc(health.seedance.text_model || "")}</code>`;
  if (runBtn) runBtn.disabled = false;

  if (!seedance.available) {
    document.getElementById("seedanceShots").innerHTML =
      '<p class="muted">当前项目无可生成的 AI 分镜。请在「品牌化出稿」重新生成脚本（script 模式下 5 镜均可生成视频）。</p>';
    document.getElementById("seedanceHint").textContent = "可先点「测试连接」验证密钥";
    if (runBtn) runBtn.disabled = true;
    return;
  }

  document.getElementById("seedanceHint").textContent =
    "每镜约 5 秒；全部生成后自动拼接为 broll/final-video.mp4";
  const final = seedance.final_video || {};
  let finalBlock = "";
  if (final.ready && final.file) {
    finalBlock = `<div class="seedance-shot seedance-final">
      <strong>拼接成片 · final-video.mp4</strong>
      <p class="muted">${Math.round((final.bytes || 0) / 1024)} KB</p>
      <a href="/api/delivery/${encodeURIComponent(slug)}/files/${encodeURI(final.file)}" target="_blank">预览 / 下载长视频</a>
    </div>`;
  }
  document.getElementById("seedanceShots").innerHTML = finalBlock + (seedance.shots || []).map((s) => {
    const status = s.ready
      ? `<a href="/api/delivery/${encodeURIComponent(slug)}/files/${encodeURI(s.file)}" target="_blank">预览 / 下载 mp4</a>`
      : '<span class="muted">待生成</span>';
    const label = s.footage_label || (s.footage_type === "AI_VIDEO" ? "AI 分镜" : "AI 空镜");
    const prompt = String(s.prompt || "（无 Prompt）");
    const promptShort = prompt.length > 80 ? `${prompt.slice(0, 80)}…` : prompt;
    const promptBlock = prompt.length > 80
      ? `<details class="seedance-prompt-fold"><summary>${esc(promptShort)}</summary><p class="seedance-prompt-full">${esc(prompt)}</p></details>`
      : `<p class="muted">${esc(prompt)}</p>`;
    return `<div class="seedance-shot">
      <strong>镜 ${esc(s.number)} · ${esc(s.role || s.timing)} · ${esc(label)}</strong>
      ${promptBlock}
      ${status}
    </div>`;
  }).join("");
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
  const cs = document.getElementById("categorySelect");
  cs.innerHTML = '<option value="">全部</option>';
  (data.categories || []).forEach((c) => {
    const o = document.createElement("option");
    o.value = c;
    o.textContent = CATEGORY_ZH[c] || c;
    cs.appendChild(o);
  });
}

async function loadMaterials() {
  const p = new URLSearchParams();
  if (state.filters.category) p.set("category", state.filters.category);
  if (state.filters.q) p.set("q", state.filters.q);
  if (state.filters.analyzedOnly) p.set("analyzed_only", "true");
  state.items = (await api(`/api/materials?${p}`)).items || [];
  renderMaterialList();
}

function materialBadgeHtml(item) {
  if (!item.has_analysis) {
    return '<span class="badge badge-pending">待拆解</span>';
  }
  return '<span class="badge badge-done">已拆解</span>';
}

function renderMaterialList() {
  const root = document.getElementById("materialList");
  if (!state.items.length) {
    root.innerHTML = '<div class="detail-empty">无匹配素材。请先在「设置」同步 TikTok。</div>';
    return;
  }
  root.innerHTML = state.items.map((item) => {
    const active = item.link_id === state.selectedMaterialId ? "active" : "";
    const thumb = item.thumbnail_url
      ? `<img class="thumb" src="${esc(item.thumbnail_url)}" alt="">`
      : '<div class="thumb placeholder">无图</div>';
    const stats = [fmtNum(item.view_count) && `${fmtNum(item.view_count)}播放`, item.duration_sec && `${item.duration_sec}s`].filter(Boolean).join(" · ");
    const badge = materialBadgeHtml(item);
    const title = item.title || "";
    const titleText = `#${item.link_id} ${title}`;
    return `<button type="button" class="card ${active}" data-id="${item.link_id}">
      ${thumb}
      <div><h3 title="${esc(titleText)}">${esc(titleText)}</h3>
      <div class="meta">${esc(item.author)}${stats ? ` · ${stats}` : ""}</div>${badge}</div>
    </button>`;
  }).join("");
  root.querySelectorAll(".card").forEach((c) =>
    c.addEventListener("click", () => selectMaterial(Number(c.dataset.id)))
  );
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
          <button type="button" class="primary primary-dark" id="goScriptBtn">下一步：配场景</button>
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
        <button type="button" class="primary primary-dark" id="goScriptBtn">下一步：配场景</button>
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

async function selectMaterial(linkId) {
  state.selectedMaterialId = linkId;
  renderMaterialList();
  repopulateScriptMaterials();
  syncMaterialSelectFromState();
  const pane = document.getElementById("materialDetail");
  pane.className = "detail dissector-detail";
  pane.innerHTML = "加载中…";
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
      setScriptStep("product");
      updateLoopBarFromForm(state.lastPreview || {});
    });
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
  const productId = document.getElementById("scriptProductSelect").value;
  const prev = Number(ms.value);
  const analyzed = state.items.filter((i) => i.has_analysis);
  const pool = state.showAllMaterials
    ? analyzed
    : analyzed.filter((i) => materialMatchesProduct(i, productId));
  const hint = document.getElementById("materialFilterHint");
  if (hint) {
    hint.textContent = state.showAllMaterials
      ? `共 ${analyzed.length} 条可选`
      : `已筛 ${pool.length} 条同品类`;
  }
  ms.innerHTML = materialOptionsHtml(productId);
  const still = [...ms.options].some((o) => Number(o.value) === prev);
  if (still) ms.value = String(prev);
  else {
    const pick = pickDefaultMaterialId(pool);
    if (pick) ms.value = String(pick);
    else if (ms.options.length) ms.selectedIndex = 0;
  }
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
}

async function loadScriptView() {
  if (!state.items.length) await loadMaterials();
  const showAll = document.getElementById("showAllMaterials");
  if (showAll) showAll.checked = state.showAllMaterials;
  const ms = document.getElementById("scriptMaterialSelect");
  await populateScriptProductSelect();
  repopulateScriptMaterials();
  if (state.selectedMaterialId && ms.querySelector(`option[value="${state.selectedMaterialId}"]`)) {
    ms.value = String(state.selectedMaterialId);
  }
  await refreshScriptPreview();
  const prev = state.lastPreview || {};
  if (prev.has_script || prev.delivery_ready) setScriptStep("produce", { scroll: false });
  else if (document.getElementById("scriptMaterialSelect")?.value && tagsSelectionOk()) setScriptStep("product", { scroll: false });
  else setScriptStep("ref", { scroll: false });
  syncWorkspaceActionBar(state.scriptStep);
}

async function refreshScriptPreview() {
  const linkId = Number(document.getElementById("scriptMaterialSelect").value);
  const productId = document.getElementById("scriptProductSelect").value;
  state.selectedMaterialId = linkId;
  const analysisEl = document.getElementById("scriptAnalysis");
  const productEl = document.getElementById("scriptProduct");
  const resultWrap = scriptResultEl();
  if (!productId) {
    productEl.className = "script-tag-grid script-tag-grid-spacious detail-empty";
    productEl.innerHTML = "选择产品后配置场景标签";
    analysisEl.innerHTML = '<div class="detail-empty">选择结构参考后显示</div>';
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
      resultWrap.classList.remove("hidden");
      syncScriptProduceEmpty(true);
      scriptResultBody().innerHTML = formatPackResult(prev.script_pack, prev.script_meta);
    }
    syncFinishButton(Boolean(prev.can_finish), Boolean(prev.delivery_ready));
    if (prev.has_script || prev.project_ready) {
      await loadSeedanceForSlug(prev.slug);
    } else {
      renderSeedance(null, null, state.healthCache);
    }
  } catch (err) {
    analysisEl.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
    productEl.className = "script-tag-grid script-tag-grid-spacious detail-empty";
    productEl.innerHTML = "";
    const lp = state.lastPreview || {};
    syncFinishButton(Boolean(lp.can_finish), Boolean(lp.delivery_ready));
  }
}

function onScriptSelectionChange() {
  state.selectedProductId = document.getElementById("scriptProductSelect").value;
  state.tagPoolExtra = { audience: [], scenarios: [], selling: [], pains: [] };
  state.tagSelection = { audience: [], scenarios: [], selling: [], pains: [] };
  scriptResultEl().classList.add("hidden");
  document.getElementById("seedancePanel")?.classList.add("hidden");
  syncScriptProduceEmpty(false);
}

document.getElementById("scriptMaterialSelect").addEventListener("change", async () => {
  state.selectedMaterialId = Number(document.getElementById("scriptMaterialSelect").value);
  onScriptSelectionChange();
  await refreshScriptPreview();
});
document.getElementById("scriptProductSelect").addEventListener("change", async () => {
  state.selectedProductId = document.getElementById("scriptProductSelect").value;
  onScriptSelectionChange();
  repopulateScriptMaterials();
  await refreshScriptPreview();
});
document.getElementById("showAllMaterials").addEventListener("change", async (e) => {
  state.showAllMaterials = e.target.checked;
  repopulateScriptMaterials();
  await refreshScriptPreview();
});

async function runScriptGenerate() {
  const linkId = Number(document.getElementById("scriptMaterialSelect").value);
  const productId = document.getElementById("scriptProductSelect").value;
  const audienceTags = readSelectedTags("audience");
  const scenarioTags = readSelectedTags("scenario");
  const sellingTags = readSelectedTags("selling");
  const painTags = readSelectedTags("pain");
  const genBtns = document.querySelectorAll("#scriptGenerateBtn, .js-script-generate");
  const resultWrap = scriptResultEl();
  const resultEl = scriptResultBody();
  if (!audienceTags.length || !scenarioTags.length || !sellingTags.length || !painTags.length) {
    setScriptStep("product");
    const hint = document.getElementById("loopHint");
    if (hint) hint.textContent = "请为人群、场景、核心卖点、用户痛点各至少选择一个标签后再生成。";
    return;
  }
  setScriptStep("produce");
  genBtns.forEach((b) => { b.disabled = true; });
  resultWrap.classList.remove("hidden");
  resultEl.innerHTML = "正在生成脚本…";
  setScriptActionStatus("");
  try {
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
      }),
    });
    const pack = res.script_pack || res.pack || {};
    state.scriptSlug = res.slug || slugFor(linkId);
    resultEl.innerHTML = formatPackResult(pack, res.meta);
    syncFinishButton(true, Boolean(state.lastPreview?.delivery_ready));
    syncScriptProduceEmpty(true);
    setScriptStep("produce");
    await refreshScriptPreview();
  } catch (err) {
    resultEl.innerHTML = `<div class="result error">${esc(err.message)}</div>`;
  } finally {
    genBtns.forEach((b) => { b.disabled = false; });
  }
}

async function runScriptFinish(options = {}) {
  const { keepScript = false } = options;
  const slug = currentScriptSlug();
  if (!slug) {
    setScriptActionStatus("请先生成脚本");
    ensureScriptResultVisible();
    return false;
  }
  state.scriptSlug = slug;
  const finishBtns = document.querySelectorAll("#scriptFinishBtn, .js-script-finish");
  const resultWrap = scriptResultEl();
  const resultEl = scriptResultBody();
  const savedHtml = resultEl?.innerHTML || "";
  finishBtns.forEach((b) => { b.disabled = true; });
  resultWrap.classList.remove("hidden");
  if (!keepScript) {
    resultEl.textContent = "正在生成交付包（英文字幕 + 脚本包）…";
  } else {
    setScriptActionStatus("正在生成交付包（英文字幕 + 脚本包）…");
  }
  try {
    const res = await api(`/api/delivery/${slug}/finish`, { method: "POST" });
    if (!keepScript) {
      resultEl.innerHTML = `<div class="result">交付完成：${esc(res.message || "字幕与交付包已生成")}
        <p class="muted">可在下方 SeedDance 面板生成 AI 分镜（需配置 ARK_API_KEY）。</p>
        <p class="loop-next">
          <button type="button" class="text-link" id="goFinishedBtn">打开成稿库</button>
          ·
          <button type="button" class="text-link" id="goFeedbackBtn">填写投放反馈</button>
        </p></div>`;
      document.getElementById("goFinishedBtn")?.addEventListener("click", () => switchView("finished"));
      document.getElementById("goFeedbackBtn")?.addEventListener("click", () => {
        state.selectedFeedbackSlug = slug;
        switchView("feedback");
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
  const slug = currentScriptSlug();
  if (!slug) {
    setScriptActionStatus("请先生成脚本");
    ensureScriptResultVisible();
    return false;
  }
  state.scriptSlug = slug;
  ensureScriptResultVisible();
  document.getElementById("seedancePanel")?.classList.remove("hidden");
  const btn = document.getElementById("btnSeedanceRun");
  const hint = document.getElementById("seedanceHint");
  if (btn) btn.disabled = true;
  if (hint) {
    hint.textContent = force
      ? "正在清除旧分镜并按最新规范重生成，约 15–30 分钟…"
      : "正在调用 SeedDance 生成分镜视频，请耐心等待…";
  }
  setScriptActionStatus(force ? "强制重生成中（已清除旧 mp4）…" : "正在生成分镜视频，请耐心等待…");
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
    if (hint) hint.textContent = msg;
    setScriptActionStatus(msg);
    if (!document.getElementById("scriptDownloadBtnBottom")?.classList.contains("hidden")) {
      syncDownloadLinks(`/api/delivery/${slug}/zip?ts=${Date.now()}`, true);
    }
    document.getElementById("seedancePanel")?.scrollIntoView({ behavior: "smooth", block: "start" });
    return !failed.length;
  } catch (err) {
    if (hint) hint.textContent = err.message;
    setScriptActionStatus(`视频生成失败：${err.message}`);
    return false;
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function runProduceVideo() {
  const slug = currentScriptSlug();
  if (!slug) {
    setScriptActionStatus("请先生成脚本后再产出视频");
    ensureScriptResultVisible();
    return;
  }
  state.scriptSlug = slug;
  setScriptStep("produce");
  ensureScriptResultVisible();
  document.getElementById("seedancePanel")?.classList.remove("hidden");
  const produceBtns = document.querySelectorAll(".js-script-produce");
  produceBtns.forEach((b) => { b.disabled = true; });
  setScriptActionStatus("正在启动：交付包 → AI 分镜视频 → 拼接成片（约 15–30 分钟）…");
  scriptResultEl()?.scrollIntoView({ behavior: "smooth", block: "start" });
  try {
    const lp = state.lastPreview || {};
    if (!lp.delivery_ready) {
      const ok = await runScriptFinish({ keepScript: true });
      if (!ok) {
        setScriptActionStatus("交付未完成，无法产出视频。请查看上方错误信息或先点「完成交付」。");
        return;
      }
      await refreshScriptPreview();
    }
    await runSeedanceGenerate({ force: document.getElementById("seedanceForceRegen")?.checked });
  } catch (err) {
    setScriptActionStatus(`产出视频失败：${err.message}`);
  } finally {
    const lp = state.lastPreview || {};
    syncFinishButton(Boolean(lp.can_finish), Boolean(lp.delivery_ready));
  }
}

document.getElementById("scriptGenerateBtn")?.addEventListener("click", () => runScriptGenerate());
document.getElementById("scriptFinishBtn")?.addEventListener("click", () => runScriptFinish());

document.getElementById("scriptStepRefNext")?.addEventListener("click", () => {
  if (!document.getElementById("scriptMaterialSelect")?.value) {
    const hint = document.getElementById("loopHint");
    if (hint) hint.textContent = "请先选择对标爆款。";
    return;
  }
  setScriptStep("product");
  updateLoopBarFromForm(state.lastPreview || {});
});

document.getElementById("scriptStepProductPrev")?.addEventListener("click", () => {
  setScriptStep("ref");
  updateLoopBarFromForm(state.lastPreview || {});
});

document.getElementById("scriptStepProductNext")?.addEventListener("click", () => {
  setScriptStep("produce");
  updateLoopBarFromForm(state.lastPreview || {});
});

document.getElementById("scriptStepProducePrev")?.addEventListener("click", () => {
  setScriptStep("product");
  updateLoopBarFromForm(state.lastPreview || {});
});

document.getElementById("scriptStepProduceBack")?.addEventListener("click", () => {
  setScriptStep("product");
  updateLoopBarFromForm(state.lastPreview || {});
});

document.getElementById("scriptLoopBar")?.addEventListener("click", (e) => {
  const li = e.target.closest("li[data-step]");
  if (!li) return;
  setScriptStep(li.dataset.step);
  updateLoopBarFromForm(state.lastPreview || {});
});

document.addEventListener("click", (e) => {
  const gen = e.target.closest(".js-script-generate");
  if (gen && gen.id !== "scriptGenerateBtn") {
    e.preventDefault();
    runScriptGenerate();
    return;
  }
  if (e.target.closest(".js-script-finish")) {
    e.preventDefault();
    runScriptFinish();
    return;
  }
  if (e.target.closest(".js-script-produce")) {
    e.preventDefault();
    runProduceVideo();
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

async function loadFeedbackView() {
  const data = await api("/api/library/feedback");
  const items = data.items || [];
  const root = document.getElementById("feedbackList");
  if (!items.length) {
    root.innerHTML = '<div class="detail-empty">暂无反馈记录</div>';
    return;
  }
  if (!state.selectedFeedbackSlug) state.selectedFeedbackSlug = items[0].slug;
  root.innerHTML = items.map((r) => `
    <button type="button" class="card compact ${r.slug === state.selectedFeedbackSlug ? "active" : ""}" data-slug="${esc(r.slug)}">
      <div><h3>${esc(r.title || r.slug)}</h3>
      <div class="meta">${esc(r.adopted || "待定")} · ${esc((r.updated_at || "").slice(0, 10))}</div></div>
    </button>`).join("");
  root.querySelectorAll(".card").forEach((c) =>
    c.addEventListener("click", () => { state.selectedFeedbackSlug = c.dataset.slug; loadFeedbackView(); })
  );
  renderFeedbackEditor();
}

async function renderFeedbackEditor() {
  const pane = document.getElementById("feedbackEditor");
  const slug = state.selectedFeedbackSlug;
  if (!slug) return;
  try {
    const r = await api(`/api/library/feedback/${encodeURIComponent(slug)}`);
    const pub = r.publish || {};
    pane.className = "detail";
    pane.innerHTML = `
      <h3>${esc(r.title || slug)}</h3>
      <form id="feedbackForm" class="form-grid">
        <label>人工修改<textarea name="manual_edits" rows="4">${esc(r.manual_edits)}</textarea></label>
        <label>采纳状态
          <select name="adopted">
            ${["待定", "已采纳", "未采纳", "修改后采纳"].map((o) =>
              `<option ${r.adopted === o ? "selected" : ""}>${o}</option>`).join("")}
          </select>
        </label>
        <label>播放量<input name="publish_views" value="${esc(pub.views)}"></label>
        <label>互动率<input name="publish_engagement" value="${esc(pub.engagement)}"></label>
        <label>投放备注<textarea name="publish_notes" rows="2">${esc(pub.notes)}</textarea></label>
        <label>备注<textarea name="notes" rows="2">${esc(r.notes)}</textarea></label>
        <button type="submit" class="primary">保存反馈</button>
        <p id="fbHint" class="muted"></p>
      </form>`;
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

document.getElementById("settingsOpenBtn")?.addEventListener("click", () => openSettingsDrawer());
document.getElementById("settingsCloseBtn")?.addEventListener("click", () => closeSettingsDrawer());
document.getElementById("settingsBackdrop")?.addEventListener("click", () => closeSettingsDrawer());
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeSettingsDrawer();
});

document.getElementById("categorySelect").addEventListener("change", (e) => {
  state.filters.category = e.target.value;
  loadMaterials();
});
document.getElementById("keywordInput").addEventListener("input", debounce((e) => {
  state.filters.q = e.target.value.trim();
  loadMaterials();
}));
document.getElementById("analyzedOnly").addEventListener("change", (e) => {
  state.filters.analyzedOnly = e.target.checked;
  loadMaterials();
});

document.getElementById("scriptProduct").addEventListener("click", (e) => {
  const chip = e.target.closest(".tag-chip");
  if (chip) {
    toggleTagChip(chip.dataset.group, chip.dataset.value);
    updateLoopBarFromForm(state.lastPreview || {});
    refreshTagGroupsUI();
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

document.getElementById("scriptProduct").addEventListener("keydown", (e) => {
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

document.getElementById("btnSeedanceTest")?.addEventListener("click", () => {
  runSeedanceTest(document.getElementById("seedanceHint"));
});

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

document.getElementById("btnSeedanceRun")?.addEventListener("click", () => runSeedanceGenerate());

(async () => {
  await refreshHealth();
  await loadFilters();
  await loadWorkspaceView();
  if (state.items.length) await selectMaterial(state.items[0].link_id);
})();
