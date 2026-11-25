const STORAGE_KEY = "zhouxu-mvp-v2";

const today = new Date();
today.setHours(0, 0, 0, 0);

const addDays = (date, days) => {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
};

const isoDate = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const dateAt = (offset) => isoDate(addDays(today, offset));

const demoTasks = [
  {
    id: "demo-mobile-exam",
    title: "中国移动笔试",
    category: "recruiting",
    dateState: "explicit",
    deadline: dateAt(1),
    time: "19:00",
    action: "确认考试设备，完成模拟登录",
    urgency: "high",
    status: "exam",
    needsReview: false,
    sourceType: "manual",
    sourceText: "中国移动笔试通知：次日 19:00 开始",
    sourceUrl: "",
    sourceImage: "",
    context: "运营商 · 产品岗 · 线上笔试 · 已收到通知",
    selectedForConflict: false,
  },
  {
    id: "demo-bank-exam",
    title: "农业银行笔试",
    category: "recruiting",
    dateState: "explicit",
    deadline: dateAt(1),
    time: "19:00",
    action: "比较岗位信息，决定是否保留",
    urgency: "high",
    status: "exam",
    needsReview: false,
    sourceType: "manual",
    sourceText: "农业银行笔试通知：次日 19:00 开始",
    sourceUrl: "",
    sourceImage: "",
    context: "国有银行 · 综合岗 · 线上笔试 · 已收到通知",
    selectedForConflict: false,
  },
  {
    id: "demo-course",
    title: "数据科学课程作业",
    category: "school",
    dateState: "explicit",
    deadline: dateAt(2),
    time: "23:59",
    action: "补充模型评估章节并提交",
    urgency: "medium",
    status: "todo",
    needsReview: false,
    sourceType: "manual",
    sourceText: "课程作业通知：本周内提交",
    sourceUrl: "",
    sourceImage: "",
    context: "课程作业 · 个人提交",
    selectedForConflict: false,
  },
  {
    id: "demo-internship",
    title: "实习项目周交付",
    category: "internship",
    dateState: "explicit",
    deadline: dateAt(3),
    time: "18:00",
    action: "整理测试结论并发给导师",
    urgency: "medium",
    status: "todo",
    needsReview: false,
    sourceType: "manual",
    sourceText: "实习项目周会：每周五提交进展",
    sourceUrl: "",
    sourceImage: "",
    context: "实习 · 产品助理 · 周交付",
    selectedForConflict: false,
  },
  {
    id: "demo-nowcoder",
    title: "原力灵机 · 产品经理",
    category: "recruiting",
    dateState: "explicit",
    deadline: "2026-12-31",
    time: "23:59",
    action: "确认是否投递并准备针对性材料",
    urgency: "low",
    status: "todo",
    needsReview: false,
    sourceType: "image",
    sourceText: "投递时间: 2026年8月17日-2026年12月31日",
    sourceUrl: "https://www.nowcoder.com/jobs/detail/460860",
    sampleId: "IMG-01",
    sourceImage: "./assets/samples/s01-nowcoder.jpg",
    context: "具身智能 · 产品策划 · 校招",
    selectedForConflict: false,
  },
  {
    id: "demo-huolala",
    title: "货拉拉 · 产品实习生",
    category: "internship",
    dateState: "published",
    deadline: "",
    time: "",
    action: "确认是否仍在招聘，再决定投入",
    urgency: "medium",
    status: "todo",
    needsReview: true,
    sourceType: "image",
    sourceText: "发布于2026-09-11",
    sourceUrl:
      "https://app.mokahr.com/campus-recruitment/huolalahr/98660#/job/366495a0-8786-4d48-a2fc-f59c1fd864b1",
    sampleId: "IMG-02",
    sourceImage: "./assets/samples/s02-huolala.jpg",
    context: "产品部 · 深圳 · 2027 届产品实习生",
    confirmedAt: dateAt(-5),
    selectedForConflict: false,
  },
  {
    id: "demo-ecoflow",
    title: "EcoFlow · 软件产品经理",
    category: "recruiting",
    dateState: "missing",
    deadline: "",
    time: "",
    action: "核对官网是否还有截止时间",
    urgency: "low",
    status: "todo",
    needsReview: true,
    sourceType: "image",
    sourceText: "当前可见区域没有截止日期",
    sourceUrl: "https://jobs.ecoflow.com/602892/position/7680177861047077170/detail",
    sampleId: "IMG-03",
    sourceImage: "./assets/samples/s03-ecoflow.jpg",
    context: "软件产品经理 · 深圳 · 当前可见页面无日期",
    confirmedAt: dateAt(-2),
    selectedForConflict: false,
  },
];

const state = {
  tasks: [],
  activeView: "week",
  category: "all",
  selectedTaskId: null,
  captureMode: "image",
  captureDraft: null,
};

const el = (selector) => document.querySelector(selector);
const els = (selector) => Array.from(document.querySelectorAll(selector));

const categoryLabels = {
  recruiting: "秋招",
  internship: "实习",
  school: "学校",
};

const urgencyLabels = {
  high: "高紧急",
  medium: "中紧急",
  low: "低紧急",
};

const statusLabels = {
  todo: "待准备",
  coursework: "待提交",
  submitted: "已投递",
  exam: "笔试",
  interview: "面试",
  result: "结果",
  done: "已完成",
};

// 冲突判定不再比"时刻是否完全一样"，而是比"占用时段是否重叠"。
// 面试、笔试登记的是开始时间，往后推一个时段；作业、交付登记的是 DDL 时刻本身。
const FIXED_START_STATUSES = ["exam", "interview"];

const DURATION_OPTIONS = [15, 30, 45, 60, 90, 120, 180, 240];

/**
 * 每类事项的默认占用时长（分钟）。
 * 只有笔试和面试用得上：它们登记的是开始时间，要往后推才知道占多久。
 */
function defaultDurationMin(task) {
  if (task.status === "exam") return 90;
  if (task.status === "interview") return 60;
  return 60;
}

function taskDurationMin(task) {
  const value = Number(task.durationMin);
  if (Number.isFinite(value) && value > 0) return Math.min(Math.round(value), 480);
  return defaultDurationMin(task);
}

function isFixedStart(task) {
  return FIXED_START_STATUSES.includes(task.status);
}

/**
 * "23:59" 在招聘信息里通常表示"当天结束前交"，不是一个真的要卡点的时刻。
 * 这种截止不往前铺准备窗口，否则一堆同一天的截止会互相误报。
 */
function isEndOfDay(time) {
  return time === "23:59";
}

const contextLabels = {
  recruiting: "岗位上下文（冲突比较时使用）",
  internship: "实习任务上下文（冲突比较时使用）",
  school: "课程上下文（冲突比较时使用）",
};

const contextPlaceholders = {
  recruiting: "岗位职责、地点、考试形式或你自己的选择理由",
  internship: "任务内容、交付对象、时间要求或你自己的选择理由",
  school: "课程名、提交要求、评分方式或你自己的选择理由",
};

const dateStateLabels = {
  explicit: "明确日期",
  missing: "未找到日期",
  published: "只有发布日期",
  no_schedule: "无需排期",
};

function save() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.tasks));
}

function load() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    state.tasks = Array.isArray(parsed) ? parsed : structuredClone(demoTasks);
  } catch {
    state.tasks = structuredClone(demoTasks);
  }
  state.tasks.forEach((task) => {
    if (task.actionAuto === undefined) {
      task.actionAuto = looksAutoGenerated(task.action);
    }
    if (task.actionAuto && task.dateState === "explicit") {
      task.action = buildAutoAction(task.category, task.deadline);
    }
  });
  if (state.tasks.length) save();
}

function toast(message) {
  // 弹窗打开时，主提示条在 top layer 之下会被完全挡住，
  // 所以要改用弹窗内部的提示条。
  const openDialog = document.querySelector("dialog[open]");
  const dialogToast = openDialog ? openDialog.querySelector(".dialog-toast") : null;
  const node = dialogToast || el("#toast");
  if (!node) return;
  node.textContent = message;
  node.classList.add("show");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => {
    node.classList.remove("show");
    el("#toast").classList.remove("show");
    document.querySelectorAll(".dialog-toast").forEach((item) => {
      item.classList.remove("show");
    });
  }, 2400);
}

/**
 * 表单级错误提示：直接标在出错的输入框下面，不依赖浮层。
 */
function setFieldError(fieldId, message) {
  ["manualTitleField", "manualActionField", "manualDeadlineField"].forEach((id) => {
    const field = el(`#${id}`);
    if (!field) return;
    field.classList.remove("has-error");
    const hint = field.querySelector(".field-error");
    if (hint) hint.remove();
  });
  if (!fieldId || !message) return;
  const field = el(`#${fieldId}`);
  if (!field) return;
  field.classList.add("has-error");
  const hint = document.createElement("p");
  hint.className = "field-error";
  hint.textContent = message;
  field.appendChild(hint);
}

function clearFieldErrors() {
  setFieldError(null, "");
}


function formatFullDate(iso) {
  if (!iso) return "没有确定日期";
  const date = new Date(`${iso}T00:00:00`);
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    weekday: "short",
  }).format(date);
}

function formatDateMonth(iso) {
  if (!iso) return "待确认";
  const date = new Date(`${iso}T00:00:00`);
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
  }).format(date);
}

function formatWeek(iso) {
  if (!iso) return "无日期";
  return new Intl.DateTimeFormat("zh-CN", { weekday: "short" }).format(
    new Date(`${iso}T00:00:00`),
  );
}

function formatClock(date) {
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

/**
 * 把若干重叠区间合并成连续的几段，方便在界面上说清楚"到底撞在哪"。
 */
function mergeIntervals(intervals) {
  const sorted = [...intervals].sort((one, two) => one.from - two.from);
  const merged = [];
  sorted.forEach((item) => {
    const last = merged[merged.length - 1];
    if (last && item.from <= last.to) {
      if (item.to > last.to) last.to = item.to;
      return;
    }
    merged.push({ from: item.from, to: item.to });
  });
  return merged;
}

/**
 * 一条事项会被占用的时间，用一句人话讲清楚。
 */
function describeOccupancy(task) {
  const window = taskOccupiedWindow(task);
  if (!window) return "没有具体时刻";
  if (window.fixed) {
    return `${formatClock(window.from)}–${formatClock(window.to)} · ${window.minutes} 分钟`;
  }
  if (window.flexible) {
    return `${formatClock(window.to)} 截止 · 当天结束前`;
  }
  return `${formatClock(window.to)} 截止`;
}

/**
 * 截止型事项只是"那一刻要交"，并不占用一段时间，
 * 所以字段名不能和笔试、面试共用"占用时段"。
 */
function occupancyLabel(task) {
  return isFixedStart(task) ? "占用时段" : "截止时刻";
}

/**
 * 卡片里只放得下一行，所以给个更短的占用时段描述。
 */
function describeOccupancyBrief(task) {
  const window = taskOccupiedWindow(task);
  if (!window) return "未定时刻";
  if (window.fixed) {
    return `占用 ${formatClock(window.from)}–${formatClock(window.to)}`;
  }
  if (window.flexible) {
    return "当天结束前交";
  }
  return `${formatClock(window.to)} 截止`;
}

function normalizedDateTime(task) {
  if (!task.deadline || !task.time) return null;
  return new Date(`${task.deadline}T${task.time}:00`);
}

/**
 * 占用时段：一条带时刻的事项真正"占住"的时间段。
 * - 笔试、面试登记的是开始时间，往后推预计时长：[开始, 开始 + 时长]
 * - 作业、投递、交付登记的是 DDL 时刻本身，就占那一个时刻：[DDL, DDL]
 * 冲突判定比的是两段时段是否相交，而不是时刻是否完全相同。
 */
function taskOccupiedWindow(task) {
  const anchor = normalizedDateTime(task);
  if (!anchor || Number.isNaN(anchor.getTime())) return null;
  if (isFixedStart(task)) {
    const minutes = taskDurationMin(task);
    return {
      from: anchor,
      to: new Date(anchor.getTime() + minutes * 60000),
      minutes,
      fixed: true,
      criticalAt: null,
    };
  }
  if (isEndOfDay(task.time)) {
    // 当天结束前交：只是"这天之内"的一个软边界，不参与冲突判定。
    return {
      from: anchor,
      to: anchor,
      minutes: 0,
      fixed: false,
      criticalAt: null,
      flexible: true,
    };
  }
  // 截止型：只登记最后时刻，前面不铺准备窗口。
  return {
    from: anchor,
    to: anchor,
    minutes: 0,
    fixed: false,
    criticalAt: anchor,
    flexible: false,
  };
}

/**
 * 判断两个占用时段是否撞车。
 *
 * 两种形态：
 * - 区间（笔试、面试）：从开始时刻往后推的一段时间。
 * - 时点（作业、交付的 DDL）：只有最后那一刻，本身不占时间。
 *
 * 判定规则：
 * 1. 两个区间有交集 → 冲突（面试和面试撞在一起）。
 * 2. 时点落在另一个区间里 → 冲突（作业 15:00 截止，面试 14:30 开始，
 *    面试时段盖住了 15:00 那一刻，来不及交）。
 * 3. 两个时点 → 只有时刻完全一样才算撞（同一分钟要交两件事）。
 */
function overlapBetween(one, two) {
  const oneIsPoint = !one.fixed && !one.flexible;
  const twoIsPoint = !two.fixed && !two.flexible;
  const oneIsRange = one.fixed;
  const twoIsRange = two.fixed;

  // 规则 1：两个区间有交集。
  if (oneIsRange && twoIsRange) {
    const from = Math.max(one.from.getTime(), two.from.getTime());
    const to = Math.min(one.to.getTime(), two.to.getTime());
    if (to <= from) return null;
    return {
      from: new Date(from),
      to: new Date(to),
      minutes: Math.round((to - from) / 60000),
      tight: false,
    };
  }

  // 规则 2：时点落在另一个区间里（含端点）。
  if (oneIsPoint && twoIsRange) {
    const at = one.from.getTime();
    if (at >= two.from.getTime() && at <= two.to.getTime()) {
      return {
        from: one.from,
        to: one.from,
        minutes: 0,
        tight: true,
        hitSpan: { from: two.from, to: two.to },
      };
    }
    return null;
  }
  if (twoIsPoint && oneIsRange) {
    const at = two.from.getTime();
    if (at >= one.from.getTime() && at <= one.to.getTime()) {
      return {
        from: two.from,
        to: two.from,
        minutes: 0,
        tight: true,
        hitSpan: { from: one.from, to: one.to },
      };
    }
    return null;
  }

  // 规则 3：两个时点，只有时刻完全一样才算撞。
  if (oneIsPoint && twoIsPoint) {
    if (one.from.getTime() === two.from.getTime()) {
      return { from: one.from, to: one.from, minutes: 0, tight: true };
    }
    return null;
  }

  // 有一方是 23:59 的软边界（当天结束前交），不参与判定。
  return null;
}

/**
 * 找出所有时段相交的事项对。
 * decisive 表示这组相交里至少有一方是必须本人到场的笔试/面试，属于"要取舍"的冲突。
 */
function overlapPairs() {
  const items = confirmedTasks()
    .map((task) => ({ task, win: taskOccupiedWindow(task) }))
    .filter((item) => item.win);
  const pairs = [];
  for (let i = 0; i < items.length; i += 1) {
    for (let j = i + 1; j < items.length; j += 1) {
      const overlap = overlapBetween(items[i].win, items[j].win);
      if (!overlap) continue;
      pairs.push({
        a: items[i].task,
        b: items[j].task,
        overlap,
        decisive: isFixedStart(items[i].task) || isFixedStart(items[j].task),
      });
    }
  }
  return pairs;
}

/**
 * 把相交的事项串成组：一组里任意两件事都占用同一段时间。
 */
function buildOverlapGroups(pairs) {
  const parent = new Map();
  const find = (id) => {
    if (!parent.has(id)) parent.set(id, id);
    let root = id;
    while (parent.get(root) !== root) root = parent.get(root);
    let cursor = id;
    while (parent.get(cursor) !== root) {
      const next = parent.get(cursor);
      parent.set(cursor, root);
      cursor = next;
    }
    return root;
  };
  const union = (x, y) => {
    const rx = find(x);
    const ry = find(y);
    if (rx !== ry) parent.set(rx, ry);
  };
  pairs.forEach((pair) => {
    find(pair.a.id);
    find(pair.b.id);
  });
  pairs.forEach((pair) => union(pair.a.id, pair.b.id));

  const buckets = new Map();
  pairs.forEach((pair) => {
    const root = find(pair.a.id);
    if (!buckets.has(root)) buckets.set(root, { tasks: [], overlaps: [] });
    const bucket = buckets.get(root);
    [pair.a, pair.b].forEach((task) => {
      if (!bucket.tasks.find((item) => item.id === task.id)) bucket.tasks.push(task);
    });
    bucket.overlaps.push(pair.overlap);
  });

  return [...buckets.values()]
    .map((bucket) => {
      const from = new Date(Math.min(...bucket.overlaps.map((item) => item.from.getTime())));
      const to = new Date(Math.max(...bucket.overlaps.map((item) => item.to.getTime())));
      return {
        key: bucket.tasks.map((task) => task.id).sort().join("-"),
        tasks: bucket.tasks,
        overlaps: bucket.overlaps,
        from,
        to,
        minutes: Math.max(...bucket.overlaps.map((item) => item.minutes)),
      };
    })
    .sort((one, two) => one.from - two.from);
}

/**
 * 硬冲突：至少有一方是必须本人到场的笔试/面试，且两段时段相交。
 * 这类冲突需要用户取舍，所以进"时间冲突"页做并排比较。
 */
function conflictingGroups() {
  return buildOverlapGroups(overlapPairs().filter((pair) => pair.decisive));
}

/**
 * 软冲突：时段相交，但双方都是可以各自完成的截止型事项。
 * 不需要二选一，只需要知道"这段时间你排得太满"。
 */
function crowdedGroups() {
  return buildOverlapGroups(overlapPairs().filter((pair) => !pair.decisive));
}

/**
 * 按分类生成"具体下一步"的默认文案。
 * 日期或分类被改动后，这条文案需要跟着变，否则会留着旧日期误导用户。
 */
function buildAutoAction(category, deadline) {
  if (category === "school") {
    return deadline
      ? `核对课程截止时间 ${formatFullDate(deadline)} 并补充下一步`
      : "回课程群或通知确认截止时间，并补充下一步";
  }
  if (category === "internship") {
    return deadline
      ? `核对实习任务时间 ${formatFullDate(deadline)} 并补充下一步`
      : "确认实习任务时间，并补充下一步";
  }
  return deadline
    ? `核对推算日期 ${formatFullDate(deadline)} 并补充下一步`
    : "从原文确认日期和下一步";
}

function normalizeForDedupe(value) {
  return String(value || "")
    .replace(/[\s　]+/g, "")
    .replace(/[，,。.；;：:！!？?、"'（）()【】\[\]<>《》—\-_]/g, "")
    .toLowerCase();
}

/**
 * 判断一段"具体下一步"是不是系统自动生成的旧文案。
 * 老数据里这类文案带着过期的日期，需要跟着分类和日期刷新。
 */
function looksAutoGenerated(action) {
  return /^(核对推算日期|核对实习任务时间|核对课程截止时间|从原文确认日期和下一步|确认实习任务时间)/.test(
    String(action || "").trim(),
  );
}

/**
 * 找同一件事的重复记录：标题归一化后相同，且落在同一天。
 */
function findDuplicateTask(title, deadline, excludeId) {
  const key = normalizeForDedupe(title);
  if (!key) return null;
  return (
    state.tasks.find(
      (task) =>
        task.id !== excludeId &&
        normalizeForDedupe(task.title) === key &&
        (deadline ? task.deadline === deadline : !task.deadline),
    ) || null
  );
}

/**
 * 同名但日期不同：只有当老那条还没确认时，才多半是用户重复敲了一遍。
 * 已确认的同名不同日期算两件不同的事，不拦。
 */
function findUnconfirmedSameTitle(title, excludeId) {
  const key = normalizeForDedupe(title);
  if (!key) return null;
  return (
    state.tasks.find(
      (task) =>
        task.id !== excludeId &&
        task.needsReview &&
        normalizeForDedupe(task.title) === key,
    ) || null
  );
}

function daysFromToday(task) {
  if (!task.deadline) return null;
  const target = new Date(`${task.deadline}T00:00:00`);
  return Math.round((target - today) / 86400000);
}

function isWithinSevenDays(task) {
  const days = daysFromToday(task);
  return days !== null && days >= 0 && days <= 6;
}

function laterTasks() {
  return confirmedTasks().filter((task) => {
    const days = daysFromToday(task);
    return days !== null && days > 6;
  });
}

function urgencyScore(task) {
  const urgency = { high: 3, medium: 2, low: 1 }[task.urgency] || 1;
  const days = daysFromToday(task);
  if (days === null) return urgency;
  const distance = Math.max(0, 7 - days);
  return urgency * 4 + distance;
}

function pendingTasks() {
  return state.tasks.filter((task) => task.needsReview);
}

function confirmedTasks() {
  return state.tasks.filter((task) => !task.needsReview);
}

function unscheduledTasks() {
  return confirmedTasks().filter((task) => task.dateState !== "explicit");
}

function daysSinceConfirmed(task) {
  if (!task.confirmedAt) return 0;
  const confirmed = new Date(`${task.confirmedAt}T00:00:00`);
  return Math.round((today - confirmed) / 86400000);
}

function needsFollowUp(task) {
  if (task.dateState === "explicit") return false;
  return daysSinceConfirmed(task) >= 3;
}

/**
 * 同一天有多件事，但至少有一件没写时刻。
 * 这种还判不出真冲突，只能并排放着并提示用户补时刻。
 */
function sameDayGroups() {
  const busyTaskIds = new Set();
  conflictingGroups().forEach((group) => {
    group.tasks.forEach((task) => busyTaskIds.add(task.id));
  });
  const byDay = new Map();
  confirmedTasks()
    .filter((task) => task.dateState === "explicit" && task.deadline)
    .forEach((task) => {
      if (!byDay.has(task.deadline)) byDay.set(task.deadline, []);
      // 已经判出硬冲突的那几条不进来，它们会在冲突页单独出现。
      // 但同一天其他缺时刻的事项要留着——它们恰恰是最需要提醒的。
      if (!busyTaskIds.has(task.id)) byDay.get(task.deadline).push(task);
    });
  return [...byDay.entries()]
    .filter(([date, tasks]) => tasks.length >= 2 && tasks.some((task) => !task.time))
    .map(([date, tasks]) => ({ date, tasks }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

/**
 * 未来七天视图的卡片要显示"这条撞车了没有"，所以先把冲突索引算好。
 * 一次算完给所有卡片复用，避免每张卡都重算一遍冲突。
 */
function buildCardContext() {
  const hard = new Map();
  const soft = new Map();
  const index = (group, target) => {
    const window = mergeIntervals(group.overlaps);
    group.tasks.forEach((task) => {
      if (target.has(task.id)) return;
      target.set(task.id, {
        group,
        window,
        rivals: group.tasks.filter((item) => item.id !== task.id),
      });
    });
  };
  conflictingGroups().forEach((group) => index(group, hard));
  crowdedGroups().forEach((group) => index(group, soft));
  return { hard, soft };
}

function setView(view) {
  state.activeView = view;
  els(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.view === view);
  });
  els(".view").forEach((item) => item.classList.remove("active"));
  el(`#${view}View`).classList.add("active");
  const viewMeta = {
    week: ["WEEKLY COMMAND CENTER", "未来七天", "先看截止时间，再看下一步要做什么。"],
    inbox: [
      "REVIEW QUEUE",
      "待确认收件箱",
      "原始信息与确认结果并列，日期不会被静默猜测。",
    ],
    conflicts: [
      "DECISION ROOM",
      "时间冲突",
      "把两份岗位上下文放在一起，再决定怎么处理。",
    ],
  }[view];
  el("#viewEyebrow").textContent = viewMeta[0];
  el("#viewTitle").textContent = viewMeta[1];
  el("#viewSubtitle").textContent = viewMeta[2];
  renderAll();
}

function renderAll() {
  els("#weekCount").forEach((node) => {
    node.textContent = confirmedTasks().filter(isWithinSevenDays).length;
  });
  els("#inboxCount").forEach((node) => {
    node.textContent = pendingTasks().length;
  });
  els("#conflictCount").forEach((node) => {
    node.textContent = conflictingGroups().length;
  });
  renderWeek();
  renderInbox();
  renderConflicts();
}

function renderWeek() {
  const weekTasks = confirmedTasks()
    .filter(isWithinSevenDays)
    .filter((task) => state.category === "all" || task.category === state.category)
    .sort((a, b) => {
      const dateCompare = a.deadline.localeCompare(b.deadline);
      if (dateCompare !== 0) return dateCompare;
      const timeCompare = (a.time || "23:59").localeCompare(b.time || "23:59");
      if (timeCompare !== 0) return timeCompare;
      return urgencyScore(b) - urgencyScore(a);
    });

  const allWeekTasks = confirmedTasks().filter(isWithinSevenDays);
  const pending = pendingTasks();
  const conflicts = conflictingGroups();
  el("#metricUpcoming").textContent = allWeekTasks.length;
  el("#metricPending").textContent = pending.length;
  el("#metricConflicts").textContent = conflicts.length;

  const priority = [...allWeekTasks].sort((a, b) => urgencyScore(b) - urgencyScore(a))[0];
  if (priority) {
    el("#priorityHeadline").textContent = priority.title;
    el("#prioritySummary").textContent = `${priority.action} · ${formatFullDate(priority.deadline)} ${priority.time || ""}`;
  } else if (!state.tasks.length) {
    el("#priorityHeadline").textContent = "先添加一条真实信息";
    el("#prioritySummary").textContent = "这里会汇总未来七天的截止时间、具体任务、紧急程度和当前进度。";
  } else {
    el("#priorityHeadline").textContent = "本周还没有已确认事项";
    el("#prioritySummary").textContent = "从待确认收件箱开始整理，或添加一条新的截止信息。";
  }

  renderCategoryFilters();
  renderDayList(weekTasks);
  renderNextAction(allWeekTasks);
  renderPipeline();
  renderUnscheduled();
  renderLater();
}

function renderCategoryFilters() {
  const categoryOptions = [
    ["all", "全部"],
    ["recruiting", "秋招"],
    ["internship", "实习"],
    ["school", "学校"],
  ];
  el("#categoryFilters").innerHTML = categoryOptions
    .map(
      ([value, label]) =>
        `<button class="filter-button ${state.category === value ? "active" : ""}" data-category="${value}" type="button">${label}</button>`,
    )
    .join("");
}

function renderDayList(tasks) {
  if (!tasks.length) {
    const isCompletelyEmpty = !state.tasks.length;
    el("#dayList").innerHTML = `
      <div class="empty-state">
        <div class="empty-mark">七</div>
        <h3>${isCompletelyEmpty ? "还没有安排" : "这个分类在未来七天没有安排"}</h3>
        <p>${isCompletelyEmpty ? "点击“添加事项”，从截图、文本、手动录入或示例开始。" : "可以切换分类，或点击“添加事项”。"}</p>
      </div>
    `;
    return;
  }
  const groups = new Map();
  tasks.forEach((task) => {
    if (!groups.has(task.deadline)) groups.set(task.deadline, []);
    groups.get(task.deadline).push(task);
  });
  const cardContext = buildCardContext();
  el("#dayList").innerHTML = [...groups.entries()]
    .map(([date, items]) => {
      const dayNumber = new Date(`${date}T00:00:00`).getDate();
      const month = new Date(`${date}T00:00:00`).getMonth() + 1;
      return `
        <div class="day-row">
          <div class="day-stamp">
            <span class="day-week">${formatWeek(date)}</span>
            <span class="day-number">${String(dayNumber).padStart(2, "0")}</span>
            <span class="day-month">${month} 月</span>
          </div>
          <div class="event-list">
            ${items.map((item) => renderEventCard(item, cardContext)).join("")}
          </div>
        </div>
      `;
    })
    .join("");
  wireEventButtons();
}

function renderEventCard(task, cardContext = {}) {
  const pending = task.needsReview ? '<span class="tag pending">待确认</span>' : "";
  const missingTime =
    !task.time && task.dateState === "explicit"
      ? '<span class="tag need-time">缺时刻</span>'
      : "";
  const hard = cardContext.hard?.get(task.id);
  const soft = cardContext.soft?.get(task.id);
  const conflictTag = hard
    ? `<span class="tag conflict" title="与 ${hard.rivals
        .map((item) => escapeHtml(item.title))
        .join("、")} 的占用时段重叠">时间冲突</span>`
    : soft
      ? `<span class="tag crowded" title="与 ${soft.rivals
          .map((item) => escapeHtml(item.title))
          .join("、")} 的准备时段压在一起">时段排满</span>`
      : "";
  const days = daysFromToday(task);
  const relative =
    days === 0 ? "今天" : days === 1 ? "明天" : days !== null ? `${days} 天后` : "无日期";
  return `
    <article class="event-card" data-task-id="${task.id}">
      <span class="event-category ${task.category}"></span>
      <div class="event-main">
        <div class="event-title-row">
          <h3 class="event-title">${escapeHtml(task.title)}</h3>
          ${pending}
          ${missingTime}
          ${conflictTag}
          ${task.inferredBasis ? '<span class="tag inferred">推算日期</span>' : ""}
          <span class="tag category-${task.category}">${categoryLabels[task.category] || task.category}</span>
          <span class="tag priority-${task.urgency}">${urgencyLabels[task.urgency] || task.urgency}</span>
        </div>
        <p class="event-action">${escapeHtml(task.action || "下一步尚未填写")}</p>
        <div class="event-deadline">${relative} · ${formatFullDate(task.deadline)}</div>
        ${
          task.time
            ? `<div class="event-occupancy">${escapeHtml(describeOccupancyBrief(task))}</div>`
            : ""
        }
      </div>
      <div class="event-time">
        ${task.time || "未定时刻"}
        <span class="event-status">${statusLabels[task.status] || task.status}</span>
      </div>
      <div class="event-actions">
        <button class="event-edit" data-edit-id="${task.id}" type="button">编辑</button>
        <button class="event-edit danger" data-delete-id="${task.id}" type="button">删除</button>
      </div>
    </article>
  `;
}

function wireEventButtons() {
  els("[data-edit-id]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      openReview(button.dataset.editId);
    });
  });
  els("[data-delete-id]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      state.selectedTaskId = button.dataset.deleteId;
      deleteTask();
    });
  });
}

function renderNextAction(tasks) {
  const next = [...tasks].sort((a, b) => urgencyScore(b) - urgencyScore(a))[0];
  if (!next) {
    el("#nextActionCard").innerHTML = `
      <div class="empty-state compact" style="padding: 30px 4px 24px">
        <h3>暂无行动</h3>
        <p>添加未来七天的截止信息后，这里会出现最优先的下一步。</p>
      </div>
    `;
    return;
  }
  el("#nextActionCard").innerHTML = `
    <div class="next-action-card">
      <span class="next-action-label">${urgencyLabels[next.urgency]} · ${categoryLabels[next.category]}</span>
      <h3>${escapeHtml(next.action)}</h3>
      <p>${escapeHtml(next.title)}</p>
      <div class="next-action-meta">
        <span>${formatFullDate(next.deadline)} ${next.time || ""}</span>
        <span>${statusLabels[next.status]}</span>
      </div>
    </div>
  `;
}

function renderPipeline() {
  const statuses = ["todo", "coursework", "submitted", "exam", "interview", "result"];
  el("#pipelineSummary").innerHTML = statuses
    .map((status) => {
      const count = state.tasks.filter((task) => task.status === status).length;
      return `<div class="pipeline-row"><span>${statusLabels[status]}</span><strong>${count}</strong></div>`;
    })
    .join("");
}

function renderUnscheduled() {
  const tasks = unscheduledTasks();
  el("#unscheduledCount").textContent = `${tasks.length} 项`;
  if (!tasks.length) {
    el("#unscheduledList").innerHTML = `
      <div class="unscheduled-empty">
        <p>没有无日期事项。</p>
        <span>确认后的招聘或现场投递会保留在这里。</span>
      </div>
    `;
    return;
  }
  el("#unscheduledList").innerHTML = tasks
    .map(
      (task) => `
        <button class="unscheduled-item" data-edit-id="${task.id}" type="button">
          <span class="unscheduled-state ${needsFollowUp(task) ? "follow" : ""}">${dateStateLabels[task.dateState]}</span>
          <strong>${escapeHtml(task.title)}</strong>
          <span>${escapeHtml(task.action)}${needsFollowUp(task) ? ` · 已等待 ${daysSinceConfirmed(task)} 天，建议核对是否已出现截止日期` : ""}</span>
        </button>
      `,
    )
    .join("");
  wireEventButtons();
}

function renderLater() {
  const tasks = laterTasks();
  el("#laterCount").textContent = `${tasks.length} 项`;
  if (!tasks.length) {
    el("#laterList").innerHTML = `
      <div class="unscheduled-empty">
        <p>七天内和更晚的事项都在这里收着。</p>
        <span>推算出的日期如果超过七天，会保留在这里而不是消失。</span>
      </div>
    `;
    return;
  }
  el("#laterList").innerHTML = tasks
    .sort((a, b) => a.deadline.localeCompare(b.deadline))
    .map(
      (task) => `
        <button class="unscheduled-item later" data-edit-id="${task.id}" type="button">
          <span class="unscheduled-state later">${formatDateMonth(task.deadline)}</span>
          <strong>${escapeHtml(task.title)}</strong>
          <span>${escapeHtml(task.action)}</span>
        </button>
      `,
    )
    .join("");
  wireEventButtons();
}

function renderInbox() {
  const pending = pendingTasks();
  if (!pending.length) {
    el("#inboxList").innerHTML = `
      <div class="empty-state">
        <div class="empty-mark">完</div>
        <h3>待确认信息已经清空</h3>
        <p>新截图、文本或示例会先进入这里。</p>
      </div>
    `;
    el("#reviewForm").classList.add("hidden");
    el("#reviewEmpty").classList.remove("hidden");
    return;
  }

  el("#inboxList").innerHTML = pending
    .map(
      (task) => `
      <button class="inbox-item ${state.selectedTaskId === task.id ? "selected" : ""}" data-review-id="${task.id}" type="button">
        <span class="status-dot draft"></span>
        <span>
          <span class="inbox-item-title">${escapeHtml(task.title)}</span>
          <span class="inbox-item-meta">${dateStateLabels[task.dateState]} · ${formatDateMonth(task.deadline)} · ${categoryLabels[task.category]}</span>
        </span>
        <span class="inbox-arrow">›</span>
      </button>
    `,
    )
    .join("");

  els("[data-review-id]").forEach((button) => {
    button.addEventListener("click", () => openReview(button.dataset.reviewId));
  });

  const selectedTask = state.tasks.find((task) => task.id === state.selectedTaskId);
  if (!selectedTask) {
    state.selectedTaskId = pending[0].id;
  }
  fillReviewForm(state.tasks.find((task) => task.id === state.selectedTaskId));
}

function openReview(id) {
  const task = state.tasks.find((item) => item.id === id);
  if (!task) return;
  state.selectedTaskId = id;
  setView("inbox");
  fillReviewForm(task);
}

function existingTaskForSample(task) {
  return state.tasks.find((item) => {
    if (task.sampleId && item.sampleId === task.sampleId) return true;
    return !task.sampleId
      && item.sourceType === task.sourceType
      && item.title === task.title
      && item.dateState === task.dateState;
  });
}

function fillReviewForm(task) {
  if (!task) return;
  el("#reviewEmpty").classList.add("hidden");
  el("#reviewForm").classList.remove("hidden");
  el("#reviewSourceText").textContent = task.sourceText || "没有保留原文依据";
  const imageWrap = el("#reviewImageWrap");
  const image = el("#reviewImage");
  if (task.sourceImage) {
    image.src = task.sourceImage;
    imageWrap.classList.remove("hidden");
  } else {
    image.removeAttribute("src");
    imageWrap.classList.add("hidden");
  }
  const link = el("#reviewSourceLink");
  if (task.sourceUrl) {
    link.href = task.sourceUrl;
    link.classList.remove("hidden");
  } else {
    link.classList.add("hidden");
  }
  el("#reviewTitle").value = task.title || "";
  el("#reviewCategory").value = task.category || "recruiting";
  el("#reviewDateState").value = task.dateState || "explicit";
  el("#reviewDeadline").value = task.deadline || "";
  el("#reviewTime").value = task.time || "";
  el("#reviewAction").value = task.action || "";
  el("#reviewUrgency").value = task.urgency || "medium";
  el("#reviewStatus").value = task.status || "todo";
  el("#reviewContext").value = task.context || "";
  el("#reviewDuration").value = task.durationMin ? String(task.durationMin) : "";
  syncReviewDateState();
  renderInferenceNote(task);
  refreshReviewHints(task);
}

function renderInferenceNote(task) {
  const inference = el("#reviewInference");
  if (!task.inferredBasis) {
    inference.classList.add("hidden");
    return;
  }
  const original = task.inferredDate;
  const current = el("#reviewDeadline").value;
  if (original && current && current !== original) {
    el("#reviewInferenceText").textContent = `你已手动改为 ${formatFullDate(current)}，原文推算的是 ${formatFullDate(original)}（依据：${task.inferredBasis}）`;
  } else {
    el("#reviewInferenceText").textContent = `${task.inferredBasis}（原文匹配「${task.inferredFrom || "日期表达"}」）`;
  }
  inference.classList.remove("hidden");
}

/**
 * 确认页的实时提示：上下文文案跟着分类走，时刻缺失时明确说出后果。
 */
function refreshReviewHints(task) {
  const category = el("#reviewCategory").value || task?.category || "recruiting";
  el("#reviewContextLabel").textContent = contextLabels[category];
  el("#reviewContext").placeholder = contextPlaceholders[category];

  const hint = el("#reviewTimeHint");
  const status = el("#reviewStatus").value;
  const hasTime = Boolean(el("#reviewTime").value);
  const hasDate = el("#reviewDateState").value === "explicit";

  let text = "";
  let tone = "";
  if (!hasDate) {
    text = {
      school: "这条还没有确定截止日期。回课程群或通知确认具体 DDL 再填，否则它不会进入未来七天视图，也不会写进日历。",
      internship: "这条还没有确定交付时间。确认具体交付时间再填，否则它不会进入未来七天视图，也不会写进日历。",
      recruiting: "这条还没有确定截止日期。回原渠道确认是否还有投递截止时间，否则它不会进入未来七天视图，也不会写进日历。",
    }[category];
  } else if (!hasTime && (status === "exam" || status === "interview")) {
    text = "笔试和面试建议补上具体时刻：不写时刻会导出成全天事件，也不会参与冲突判断，同一天的安排就看不出撞车。";
    tone = "urgent";
  } else if (!hasTime) {
    text = "没写时刻的事件会导出成全天事件，并且不参与冲突判断。如果这件事需要卡点，建议补上时间。";
    tone = "warn";
  } else if (status === "exam" || status === "interview") {
    text =
      "已填开始时间。笔试和面试从开始时刻往后占一段时长，这段时间里撞上别的事就算冲突。";
    tone = "ok";
  } else {
    text =
      "已填截止时刻。这一刻落在别人的笔试或面试时段里，就算冲突——不是要比时刻完全一样。";
    tone = "ok";
  }
  hint.textContent = text;
  hint.className = `field-help time-hint ${tone}`.trim();
  refreshOccupancyPreview();

  const note = el("#reviewPrefillNote");
  if (task?.prefillNote) {
    note.textContent = task.prefillNote;
    note.classList.remove("hidden");
  } else {
    note.classList.add("hidden");
  }
}

/**
 * 实时算出"这条会占住哪一段时间"，让用户看得见冲突判定的依据。
 */
function refreshOccupancyPreview() {
  const node = el("#reviewOccupancy");
  if (!node) return;
  const deadline = el("#reviewDeadline").value;
  const time = el("#reviewTime").value;
  const status = el("#reviewStatus").value;
  syncDurationField(el("#reviewDurationField"), el("#reviewDurationLabel"), status);
  syncTimeLabels(status);
  if (!deadline || !time) {
    node.textContent = "填上日期和时刻后显示";
    return;
  }
  const preview = {
    deadline,
    time,
    status,
    category: el("#reviewCategory").value,
    durationMin: el("#reviewDuration").value || undefined,
  };
  node.textContent = describeOccupancy(preview);
}

/**
 * 只有笔试和面试是"从开始时刻往后推"，其他类型只登记最后时刻。
 * 所以时长字段只在笔试、面试时出现，其余类型不占用用户的注意力。
 */
function syncDurationField(fieldNode, labelNode, status) {
  if (!fieldNode || !labelNode) return;
  const isSpan = FIXED_START_STATUSES.includes(status);
  fieldNode.classList.toggle("hidden", !isSpan);
  labelNode.textContent = status === "exam" ? "笔试时长" : "面试时长";
}

/**
 * 笔试、面试登记的是开始时刻，其余类型登记的是截止时刻，
 * 所以字段名要跟着类型走，不能一律叫"截止时间"。
 */
function syncTimeLabels(status) {
  const isSpan = FIXED_START_STATUSES.includes(status);
  const dateLabel = isSpan ? "开始日期" : "截止日期";
  const timeLabel = isSpan ? "开始时间" : "截止时间";
  [
    ["#reviewDeadlineLabel", dateLabel],
    ["#reviewTimeLabel", timeLabel],
    ["#manualDeadlineLabel", dateLabel],
    ["#manualTimeLabel", timeLabel],
  ].forEach(([selector, text]) => {
    const node = el(selector);
    if (node) node.textContent = text;
  });
}

function syncReviewDateState() {
  const dateState = el("#reviewDateState").value;
  const hasDate = dateState === "explicit";
  el("#reviewDeadline").disabled = !hasDate;
  el("#reviewTime").disabled = !hasDate;
  const task = state.tasks.find((item) => item.id === state.selectedTaskId);
  refreshReviewHints(task);
}

/**
 * 用户改了日期或分类后，"具体下一步"里的旧日期就过期了。
 * 只重写系统自动生成的那句；用户自己写的内容保持不动。
 */
function refreshAutoAction() {
  const task = state.tasks.find((item) => item.id === state.selectedTaskId);
  if (!task || !task.actionAuto) return;
  const category = el("#reviewCategory").value;
  const deadline = el("#reviewDateState").value === "explicit"
    ? el("#reviewDeadline").value
    : "";
  el("#reviewAction").value = buildAutoAction(category, deadline);
}

function saveReview(confirmed) {
  const task = state.tasks.find((item) => item.id === state.selectedTaskId);
  if (!task) return;
  task.title = el("#reviewTitle").value.trim();
  task.category = el("#reviewCategory").value;
  task.dateState = el("#reviewDateState").value;
  task.deadline = task.dateState === "explicit" ? el("#reviewDeadline").value : "";
  task.time = task.dateState === "explicit" ? el("#reviewTime").value : "";
  task.action = el("#reviewAction").value.trim();
  task.urgency = el("#reviewUrgency").value;
  task.status = el("#reviewStatus").value;
  task.context = el("#reviewContext").value.trim();
  task.durationMin = el("#reviewDuration").value
    ? Number(el("#reviewDuration").value)
    : undefined;
  if (!task.title || !task.action) {
    toast("事项名称和具体下一步不能为空");
    return;
  }
  if (task.dateState === "explicit" && !task.deadline) {
    toast("明确日期状态需要填写截止日期");
    return;
  }
  if (confirmed) {
    const duplicate = findDuplicateTask(task.title, task.deadline, task.id);
    if (duplicate) {
      const keep = window.confirm(
        `已经有一条「${duplicate.title}」（${formatFullDate(duplicate.deadline)}）了。\n如果这是同一件事，可以删掉旧的那条；继续保存会留下两条重复记录。\n\n点击"确定"继续保存两条，点击"取消"先不保存。`,
      );
      if (!keep) {
        toast("已取消保存，可以先删除重复的那条");
        return;
      }
    }
  }
  task.needsReview = !confirmed;
  if (confirmed && !task.confirmedAt) {
    task.confirmedAt = isoDate(today);
  }
  save();
  renderAll();
  if (confirmed && !pendingTasks().length) {
    setView("week");
  }
  toast(confirmed ? "已确认并加入七天计划" : "草稿已保存");
}

function deleteTask() {
  const task = state.tasks.find((item) => item.id === state.selectedTaskId);
  if (!task) return;
  const ok = window.confirm(`删除「${task.title}」？删除后本机这条记录就不见了。`);
  if (!ok) return;
  state.tasks = state.tasks.filter((item) => item.id !== task.id);
  state.selectedTaskId = pendingTasks()[0]?.id || null;
  save();
  renderAll();
  if (state.selectedTaskId) {
    fillReviewForm(state.tasks.find((item) => item.id === state.selectedTaskId));
  }
  toast("已删除这条事项");
}

function renderConflicts() {
  const groups = conflictingGroups();
  const crowded = crowdedGroups();
  const sameDay = sameDayGroups();
  const container = el("#conflictContent");
  if (!groups.length && !crowded.length && !sameDay.length) {
    container.innerHTML = `
      <div class="panel">
        <div class="empty-state">
          <div class="empty-mark">冲</div>
          <h3>当前没有时段重叠的冲突</h3>
          <p>只要两个事项的占用时段有交集，就会出现在这里；同一天多件事但缺时刻，也会单独列出来。</p>
        </div>
      </div>
    `;
    return;
  }
  container.innerHTML = `
    ${groups.length ? `
    <div class="conflict-banner">
      <div>
        <h2>${groups.length} 组时间冲突需要处理</h2>
        <p>先比较岗位、阶段和考试形式。系统不会替你判断哪个更适合。</p>
      </div>
      <button class="button secondary small" data-view-jump="week" type="button">查看一周时间线</button>
    </div>
    <div class="conflict-groups">
      ${groups.map(renderConflictGroup).join("")}
    </div>
    ` : ""}
    ${crowded.length ? `
    <div class="same-day-section">
      <div class="conflict-banner soft">
        <div>
          <h2>${crowded.length} 处截止时刻撞在一起</h2>
          <p>这些安排都卡在同一个时刻，但不需要你放弃哪一个——看看能不能把其中一件提前做完。</p>
        </div>
        <button class="button secondary small" data-view-jump="week" type="button">查看一周时间线</button>
      </div>
      <div class="conflict-groups">
        ${crowded.map(renderCrowdedGroup).join("")}
      </div>
    </div>
    ` : ""}
    ${sameDay.length ? `
    <div class="same-day-section">
      <div class="conflict-banner soft">
        <div>
          <h2>${sameDay.length} 天有多件事排在一起</h2>
          <p>这些安排在同一天，但至少有一件没写具体时刻，所以系统暂时判不出是不是撞车。先补上时刻，结论才会准确。</p>
        </div>
        <button class="button secondary small" data-view-jump="week" type="button">查看一周时间线</button>
      </div>
      <div class="conflict-groups">
        ${sameDay.map(renderSameDayGroup).join("")}
      </div>
    </div>
    ` : ""}
  `;
  wireConflictActions();
}

function renderCrowdedGroup(group) {
  const windows = mergeIntervals(group.overlaps);
  const overlapText = windows
    .map((item) => `${formatClock(item.from)}–${formatClock(item.to)}`)
    .join("、");
  return `
    <article class="conflict-group soft" data-conflict-key="crowd-${group.key}">
      <div class="conflict-group-heading">
        <div>
          <h3>${formatFullDate(isoDate(group.from))} · ${overlapText} 截止</h3>
          <p>${group.tasks.length} 项安排卡在同一个截止时刻</p>
        </div>
        <span class="tag pending">建议错开</span>
      </div>
      <div class="compare-grid">
        ${group.tasks.map(renderCompareCard).join("")}
      </div>
    </article>
  `;
}

function renderSameDayGroup(group) {
  return `
    <article class="conflict-group soft" data-conflict-key="same-${group.date}">
      <div class="conflict-group-heading">
        <div>
          <h3>${formatFullDate(group.date)} · ${group.tasks.length} 项安排</h3>
          <p>${group.tasks.filter((task) => !task.time).length} 项缺时刻，暂未判定为冲突</p>
        </div>
        <span class="tag pending">补时刻后判定</span>
      </div>
      <div class="compare-grid">
        ${group.tasks.map(renderCompareCard).join("")}
      </div>
    </article>
  `;
}

function renderConflictGroup(group) {
  const windows = mergeIntervals(group.overlaps);
  const overlapText = windows
    .map((item) => {
      const sameMoment = item.from.getTime() === item.to.getTime();
      if (!sameMoment) {
        return `${formatClock(item.from)}–${formatClock(item.to)}`;
      }
      // 只是一个时点撞上了区间：把被占用的那一段显示出来，
      // 用户才知道"我到底被哪段时间占住了"。
      const hit = group.overlaps.find(
        (overlap) =>
          overlap.hitSpan &&
          overlap.from.getTime() === item.from.getTime(),
      );
      return hit
        ? `${formatClock(item.from)} 落在 ${formatClock(hit.hitSpan.from)}–${formatClock(hit.hitSpan.to)} 里`
        : `${formatClock(item.from)} 这一刻撞上了`;
    })
    .join("、");
  return `
    <article class="conflict-group" data-conflict-key="${group.key}">
      <div class="conflict-group-heading">
        <div>
          <h3>${formatFullDate(isoDate(group.from))} · ${overlapText}</h3>
          <p>${describeConflictReason(group)}</p>
        </div>
        <span class="tag pending">需要决定</span>
      </div>
      <div class="compare-grid">
        ${group.tasks.map(renderCompareCard).join("")}
      </div>
    </article>
  `;
}

/**
 * 说清楚这组为什么算冲突：是两个必须到场的时段撞在一起，
 * 还是某个截止时刻正好落在别人的时段里。
 */
function describeConflictReason(group) {
  const spans = group.tasks.filter((task) => isFixedStart(task));
  const points = group.tasks.filter((task) => !isFixedStart(task));
  if (spans.length >= 2 && points.length === 0) {
    return `${group.tasks.length} 项都必须本人到场，时段撞上了，需要你取舍`;
  }
  if (spans.length >= 1 && points.length >= 1) {
    return `截止时刻落在必须到场的时段里，来不及做完，需要你决定`;
  }
  if (points.length >= 2) {
    return `${group.tasks.length} 项安排卡在同一个截止时刻，需要你决定先做哪个`;
  }
  return `${group.tasks.length} 项安排的时段有重叠，需要你取舍`;
}

function renderCompareCard(task) {
  return `
    <section class="compare-card ${task.selectedForConflict ? "selected" : ""}" data-compare-id="${task.id}">
      <div class="compare-card-top">
        <div>
          <h4>${escapeHtml(task.title)}</h4>
          <div class="compare-meta">${categoryLabels[task.category]} · ${statusLabels[task.status]} · ${urgencyLabels[task.urgency]}</div>
        </div>
        <span class="tag category-${task.category}">${task.time || "未定时刻"}</span>
      </div>
      <dl class="compare-facts">
        <div class="compare-fact"><dt>${occupancyLabel(task)}</dt><dd>${describeOccupancy(task)}</dd></div>
        <div class="compare-fact"><dt>具体任务</dt><dd>${escapeHtml(task.action)}</dd></div>
        <div class="compare-fact"><dt>${contextLabels[task.category]?.split("（")[0] || "上下文"}</dt><dd>${escapeHtml(task.context || "尚未填写")}</dd></div>
        <div class="compare-fact"><dt>原文依据</dt><dd>${escapeHtml(task.sourceText || "无")}</dd></div>
      </dl>
      <div class="compare-actions">
        <button class="button small ${task.selectedForConflict ? "primary" : "secondary"}" data-prefer-id="${task.id}" type="button">
          ${task.selectedForConflict ? "已选为优先" : "标记优先"}
        </button>
        <button class="button small ghost" data-reschedule-id="${task.id}" type="button">要我重排</button>
      </div>
    </section>
  `;
}

function wireConflictActions() {
  const jump = el("[data-view-jump]");
  if (jump) jump.addEventListener("click", () => setView("week"));
  els("[data-prefer-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const task = state.tasks.find((item) => item.id === button.dataset.preferId);
      if (!task) return;
      // 只有真正撞在一起的那几条才需要二选一，同一天但不冲突的不受影响。
      const rivals = conflictingGroups()
        .filter((group) => group.tasks.some((item) => item.id === task.id))
        .flatMap((group) => group.tasks)
        .filter((item) => item.id !== task.id);
      rivals.forEach((item) => (item.selectedForConflict = false));
      task.selectedForConflict = true;
      save();
      renderConflicts();
      toast(`已把“${task.title}”标记为优先，另一项需要你决定是否放弃或重排`);
    });
  });
  els("[data-reschedule-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const task = state.tasks.find((item) => item.id === button.dataset.rescheduleId);
      if (!task) return;
      openReview(task.id);
      toast("可以在当前页修改日期或时间");
    });
  });
}

function openCapture() {
  state.captureMode = "image";
  state.captureDraft = null;
  els("[data-capture-mode]").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.captureMode === "image");
  });
  els("[data-mode-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.modePanel === "image");
  });
  el("#rawTextInput").value = "";
  el("#manualTitle").value = "";
  el("#manualAction").value = "";
  el("#manualDeadline").value = "";
  el("#manualTime").value = "";
  el("#manualCategory").value = "recruiting";
  el("#manualDateState").value = "explicit";
  el("#manualStatus").value = "todo";
  el("#manualUrgency").value = "medium";
  el("#manualDuration").value = "";
  clearFieldErrors();
  const dialogToast = el("#captureToast");
  if (dialogToast) dialogToast.classList.remove("show");
  el("#imagePreview").classList.add("hidden");
  el("#imagePreview").innerHTML = "";
  syncManualDateState();
  el("#captureDialog").showModal();
}

/**
 * 手动录入时，按当前进度和分类给出建议时长，并实时显示占用时段。
 */
function refreshManualOccupancy() {
  const node = el("#manualOccupancy");
  if (!node) return;
  const deadline = el("#manualDeadline").value;
  const time = el("#manualTime").value;
  const status = el("#manualStatus").value;
  syncDurationField(el("#manualDurationField"), el("#manualDurationLabel"), status);
  syncTimeLabels(status);
  if (!deadline || !time) {
    node.textContent = "填上日期和时刻后显示";
    return;
  }
  node.textContent = describeOccupancy({
    deadline,
    time,
    status,
    category: el("#manualCategory").value,
    durationMin: el("#manualDuration").value || undefined,
  });
}

/**
 * 手动录入的日期状态决定截止日期/时间是否可用，并给一句明确说明。
 */
function syncManualDateState() {
  const dateState = el("#manualDateState").value;
  const hasDate = dateState === "explicit";
  el("#manualDeadline").disabled = !hasDate;
  el("#manualTime").disabled = !hasDate;
  const hint = el("#manualHint");
  if (!hint) return;
  hint.textContent = {
    explicit: "既然日期状态是明确日期，就一定要填截止日期；没填会留在收件箱等你补。",
    missing: "原文里没有找到截止日期。这条会留在收件箱里提醒你回原渠道确认。",
    published: "只有发布日期，还没有截止日期。这条会留在收件箱里等你确认。",
    no_schedule: "不需要排期（比如现场投递）。这条只保留进度，不进日历。",
  }[dateState];
}

function setCaptureMode(mode) {
  state.captureMode = mode;
  els("[data-capture-mode]").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.captureMode === mode);
  });
  els("[data-mode-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.modePanel === mode);
  });
}

function createPendingTask(overrides) {
  const task = {
    id: `task-${Date.now()}`,
    title: "待确认事项",
    category: "recruiting",
    dateState: "missing",
    deadline: "",
    time: "",
    action: "核对信息并补充下一步",
    urgency: "medium",
    status: "todo",
    needsReview: true,
    sourceType: "manual",
    sourceText: "",
    sourceUrl: "",
    sourceImage: "",
    context: "",
    selectedForConflict: false,
    ...overrides,
  };
  state.tasks.unshift(task);
  state.selectedTaskId = task.id;
  save();
  renderAll();
  el("#captureDialog").close();
  setView("inbox");
  toast("已放入待确认收件箱，日期与任务需要你确认");
}

function saveCapture() {
  if (state.captureMode === "image") {
    if (!state.captureDraft?.imageData) {
      toast("请先选择一张截图");
      return;
    }
    createPendingTask({
      title: state.captureDraft.name || "待确认招聘截图",
      sourceType: "image",
      sourceText: "图片已选择。首版尚未接入视觉模型，请手动补充公司、岗位和日期原文。",
      sourceImage: state.captureDraft.imageData,
      action: "查看截图并确认公司、岗位、日期和下一步",
      dateState: "missing",
    });
    return;
  }
  if (state.captureMode === "text") {
    const raw = el("#rawTextInput").value.trim();
    if (!raw) {
      toast("请先粘贴招聘或通知原文");
      return;
    }
    const parsedDate = window.ZhouxuParser.parseDateExpression(raw, today);
    const parsedTime = window.ZhouxuParser.parseTimeExpression(raw);
    const extractedTitle = window.ZhouxuParser.extractTitle(raw);
    const inferred = window.ZhouxuParser.inferTask(raw);
    const category = inferred?.category || "recruiting";
    const status = inferred?.status || "todo";
    const deadline = parsedDate ? parsedDate.date : "";

    const duplicate = findDuplicateTask(extractedTitle, deadline, null);
    const pendingDuplicate = duplicate
      ? null
      : findUnconfirmedSameTitle(extractedTitle, null);
    if (duplicate || pendingDuplicate) {
      const existing = duplicate || pendingDuplicate;
      el("#captureDialog").close();
      openReview(existing.id);
      toast("已经有一条同名同一天的事项了，已为你打开原来那条，没有重复添加");
      return;
    }

    createPendingTask({
      title: extractedTitle || "待确认文本信息",
      category,
      status,
      sourceType: "text",
      sourceText: raw,
      action: buildAutoAction(category, deadline),
      actionAuto: true,
      autoFilled: true,
      prefillNote: inferred
        ? `已根据原文预填：${categoryLabels[category]} · ${statusLabels[status]}${
            inferred.categoryWord ? `（依据「${inferred.categoryWord}」）` : ""
          }`
        : "",
      dateState: parsedDate ? "explicit" : "missing",
      deadline,
      time: parsedTime ? parsedTime.time : "",
      inferredBasis: parsedDate ? parsedDate.basis : "",
      inferredFrom: parsedDate ? parsedDate.matched : "",
      inferredDate: parsedDate ? parsedDate.date : "",
    });
    return;
  }
  if (state.captureMode === "manual") {
    const title = el("#manualTitle").value.trim();
    const action = el("#manualAction").value.trim();
    const dateState = el("#manualDateState").value;
    const deadline = el("#manualDeadline").value;
    clearFieldErrors();
    if (!title) {
      setFieldError("manualTitleField", "请填写事项名称");
      toast("请填写事项名称");
      el("#manualTitle").focus();
      return;
    }
    if (!action) {
      setFieldError("manualActionField", "请填写具体下一步");
      toast("请填写具体下一步");
      el("#manualAction").focus();
      return;
    }
    if (dateState === "explicit" && !deadline) {
      setFieldError("manualDeadlineField", "日期状态选了明确日期，就需要填截止日期");
      toast("日期状态选了明确日期，就需要填截止日期");
      el("#manualDeadline").focus();
      return;
    }
    const duplicate = findDuplicateTask(title, deadline, null);
    if (duplicate) {
      el("#captureDialog").close();
      openReview(duplicate.id);
      toast("已经有一条同名同一天的事项了，已为你打开原来那条，没有重复添加");
      return;
    }
    createPendingTask({
      title,
      category: el("#manualCategory").value,
      status: el("#manualStatus").value,
      urgency: el("#manualUrgency").value,
      dateState,
      deadline: dateState === "explicit" ? deadline : "",
      time: dateState === "explicit" ? el("#manualTime").value : "",
      durationMin: el("#manualDuration").value
        ? Number(el("#manualDuration").value)
        : undefined,
      action,
      sourceText: "手动录入",
      sourceType: "manual",
    });
    return;
  }
  toast("请从示例中选择一条信息");
}

function addSample(sample) {
  const sampleMap = {
    explicit: {
      title: "原力灵机 · 产品经理",
      category: "recruiting",
      dateState: "explicit",
      deadline: "2026-12-31",
      time: "23:59",
      action: "确认岗位适配并准备投递材料",
      sourceText: "投递时间: 2026年8月17日-2026年12月31日",
      sourceUrl: "https://www.nowcoder.com/jobs/detail/460860",
      sourceType: "image",
      sampleId: "IMG-01",
      sourceImage: "./assets/samples/s01-nowcoder.jpg",
      context: "具身智能 · 产品策划 · 校招",
    },
    published: {
      title: "货拉拉 · 产品实习生",
      category: "internship",
      dateState: "published",
      action: "确认岗位是否仍在招聘，并核对截止时间",
      sourceText: "发布于2026-09-11",
      sourceUrl:
        "https://app.mokahr.com/campus-recruitment/huolalahr/98660#/job/366495a0-8786-4d48-a2fc-f59c1fd864b1",
      sourceType: "image",
      sampleId: "IMG-02",
      sourceImage: "./assets/samples/s02-huolala.jpg",
      context: "产品部 · 深圳 · 2027 届产品实习生",
    },
    missing: {
      title: "EcoFlow · 软件产品经理",
      category: "recruiting",
      dateState: "missing",
      action: "再次核对官网是否出现截止日期",
      sourceText: "当前可见区域没有截止日期",
      sourceUrl: "https://jobs.ecoflow.com/602892/position/7680177861047077170/detail",
      sourceType: "image",
      sampleId: "IMG-03",
      sourceImage: "./assets/samples/s03-ecoflow.jpg",
      context: "软件产品经理 · 深圳 · 当前可见页面无日期",
    },
    graduationYear: {
      title: "浩鲸云计算 · 产品经理",
      category: "recruiting",
      dateState: "explicit",
      deadline: "2026-12-31",
      action: "确认岗位方向并准备投递材料",
      sourceText: "毕业时间：2027年 招聘截止日期：2026.12.31",
      sourceUrl:
        "https://ctww.ncss.cn/student/m/jobs/NLwiLxC77eozRcP8No9cic/detail.html",
      sourceType: "image",
      sampleId: "IMG-06",
      sourceImage: "./assets/samples/s06-ncss.jpg",
      context: "产品 · 福州 · 2027 届秋招 · 移动端页面",
    },
    noSchedule: {
      title: "双选会现场投递",
      category: "recruiting",
      dateState: "no_schedule",
      deadline: "",
      time: "",
      action: "继续跟进邮箱，记录是否收到后续通知",
      status: "submitted",
      urgency: "low",
      sourceText: "校招双选会现场与 HR 沟通并递交简历，没有截止时间",
      sourceType: "manual",
      context: "线下双选会 · 现场投递 · 等待后续",
    },
    conflict: {
      title: "中国移动笔试",
      category: "recruiting",
      dateState: "explicit",
      deadline: dateAt(1),
      time: "19:00",
      action: "确认考试设备，比较岗位后决定是否参加",
      status: "exam",
      urgency: "high",
      sourceText: "中国移动与农业银行笔试通知时间相同",
      sourceType: "manual",
      context: "运营商 · 产品岗 · 线上笔试 · 已收到通知",
    },
  };
  const selected = sampleMap[sample];
  if (!selected) return;
  if (sample === "conflict") {
    const first = {
      ...selected,
      id: `task-${Date.now()}-mobile`,
      needsReview: false,
    };
    const second = {
      ...selected,
      id: `task-${Date.now()}-bank`,
      title: "农业银行笔试",
      action: "比较岗位信息，决定是否保留",
      context: "国有银行 · 综合岗 · 线上笔试 · 已收到通知",
      sourceText: "中国移动与农业银行笔试通知时间相同",
      needsReview: false,
    };
    state.tasks.unshift(first, second);
    save();
    renderAll();
    el("#captureDialog").close();
    setView("conflicts");
    toast("已加入两个同时间笔试，请比较岗位信息");
    return;
  }
  const existing = existingTaskForSample(selected);
  if (existing) {
    state.selectedTaskId = existing.id;
    el("#captureDialog").close();
    openReview(existing.id);
    toast("这条示例已经存在，已为你打开确认页");
    return;
  }
  createPendingTask(selected);
}

function exportICS() {
  const exportable = state.tasks.filter(
    (task) => task.dateState === "explicit" && task.deadline && !task.needsReview,
  );
  const followUps = state.tasks.filter(
    (task) => !task.needsReview && task.dateState !== "explicit" && needsFollowUp(task),
  );
  const missingTime = exportable.filter((task) => !task.time);
  if (!exportable.length && !followUps.length) {
    toast("没有已确认且带日期的事项可导出");
    return;
  }
  const escapeICS = (value = "") =>
    String(value)
      .replace(/\\/g, "\\\\")
      .replace(/\n/g, "\\n")
      .replace(/,/g, "\\,")
      .replace(/;/g, "\\;");
  const formatICSDate = (date, time) => {
    const [year, month, day] = date.split("-");
    const [hour, minute] = time.split(":");
    return `${year}${month}${day}T${hour}${minute}00`;
  };
  const addOneHour = (date, time) => {
    const value = new Date(`${date}T${time}:00`);
    value.setHours(value.getHours() + 1);
    return {
      date: isoDate(value),
      time: `${String(value.getHours()).padStart(2, "0")}:${String(value.getMinutes()).padStart(2, "0")}`,
    };
  };
  const formatAllDayEnd = (date) => {
    const value = addDays(new Date(`${date}T00:00:00`), 1);
    return `${value.getFullYear()}${String(value.getMonth() + 1).padStart(2, "0")}${String(value.getDate()).padStart(2, "0")}`;
  };
  const followUpDate = dateAt(3);
  const followUpEnd = formatAllDayEnd(followUpDate);
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Zhouxu MVP//CN",
    "CALSCALE:GREGORIAN",
    ...exportable.flatMap((task) => {
      const timed = Boolean(task.time);
      const end = timed ? addOneHour(task.deadline, task.time) : null;
      const timingLines = timed
        ? [
            `DTSTART:${formatICSDate(task.deadline, task.time)}`,
            `DTEND:${formatICSDate(end.date, end.time)}`,
          ]
        : [
            `DTSTART;VALUE=DATE:${task.deadline.replaceAll("-", "")}`,
            `DTEND;VALUE=DATE:${formatAllDayEnd(task.deadline)}`,
          ];
      return [
        "BEGIN:VEVENT",
        `UID:${task.id}@zhouxu.local`,
        `DTSTAMP:${formatICSDate(isoDate(new Date()), "12:00")}`,
        ...timingLines,
        `SUMMARY:${escapeICS(task.title)}`,
        `DESCRIPTION:${escapeICS(`${task.action}\n分类：${categoryLabels[task.category]}\n状态：${statusLabels[task.status]}\n${task.context}`)}`,
        "BEGIN:VALARM",
        "TRIGGER:-P3D",
        "ACTION:DISPLAY",
        `DESCRIPTION:${escapeICS(`${task.title} 将在 3 天后到期`)}`,
        "END:VALARM",
        "BEGIN:VALARM",
        "TRIGGER:-P1D",
        "ACTION:DISPLAY",
        `DESCRIPTION:${escapeICS(`${task.title} 将在明天到期`)}`,
        "END:VALARM",
        "END:VEVENT",
      ];
    }),
    ...followUps.map((task) => [
      "BEGIN:VEVENT",
      `UID:followup-${task.id}@zhouxu.local`,
      `DTSTAMP:${formatICSDate(isoDate(new Date()), "12:00")}`,
      `DTSTART;VALUE=DATE:${followUpDate.replaceAll("-", "")}`,
      `DTEND;VALUE=DATE:${followUpEnd}`,
      `SUMMARY:${escapeICS(`核对截止日期：${task.title}`)}`,
      `DESCRIPTION:${escapeICS(`${task.action}\n这条事项还没有截止日期。已等待 ${daysSinceConfirmed(task)} 天，建议回原渠道确认是否已出现新的截止时间。`)}`,
      "BEGIN:VALARM",
      "TRIGGER:-P1D",
      "ACTION:DISPLAY",
      `DESCRIPTION:${escapeICS(`${task.title} 明天需要核对截止日期`)}`,
      "END:VALARM",
      "END:VEVENT",
    ]),
    "END:VCALENDAR",
  ];
  const blob = new Blob([lines.join("\r\n")], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "周序_未来七天.ics";
  anchor.click();
  URL.revokeObjectURL(url);
  toast(
    [
      `已导出 ${exportable.length} 条已确认事项`,
      followUps.length ? `含 ${followUps.length} 条核对截止日期提醒` : "",
      missingTime.length ? `其中 ${missingTime.length} 条没写时刻，导出为全天事件` : "",
      "导出为当前快照",
    ]
      .filter(Boolean)
      .join("，"),
  );
}

function resetDemo() {
  state.tasks = structuredClone(demoTasks);
  state.selectedTaskId = null;
  state.category = "all";
  save();
  renderAll();
  toast("示例数据已恢复");
}

function clearLocalData() {
  localStorage.removeItem(STORAGE_KEY);
  state.tasks = [];
  state.activeView = "week";
  state.selectedTaskId = null;
  state.category = "all";
  renderAll();
  setView("week");
  toast("本机数据已清空，可以从一条新信息开始");
}

function openClearDataDialog() {
  const dialog = el("#clearDataDialog");
  if (typeof dialog.showModal === "function") {
    dialog.showModal();
    return;
  }
  if (window.confirm("这会删除本机浏览器中保存的全部事项。继续吗？")) {
    clearLocalData();
  }
}

function escapeHtml(value = "") {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function wireGlobalEvents() {
  els("[data-view]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });
  el("#categoryFilters").addEventListener("click", (event) => {
    const button = event.target.closest("[data-category]");
    if (!button) return;
    state.category = button.dataset.category;
    renderWeek();
  });
  el("#openCapture").addEventListener("click", openCapture);
  el("#exportButton").addEventListener("click", exportICS);
  el("#resetDemo").addEventListener("click", resetDemo);
  el("#clearLocalData").addEventListener("click", openClearDataDialog);
  el("#clearDataDialog").addEventListener("close", () => {
    if (el("#clearDataDialog").returnValue === "confirm") clearLocalData();
  });
  el("#saveDraft").addEventListener("click", () => saveReview(false));
  el("#reviewForm").addEventListener("submit", (event) => {
    event.preventDefault();
    saveReview(true);
  });
  el("#deleteTask").addEventListener("click", deleteTask);
  el("#reviewDateState").addEventListener("change", syncReviewDateState);
  el("#reviewCategory").addEventListener("change", () => {
    refreshAutoAction();
    const task = state.tasks.find((item) => item.id === state.selectedTaskId);
    refreshReviewHints(task);
  });
  el("#reviewDeadline").addEventListener("change", () => {
    refreshAutoAction();
    const task = state.tasks.find((item) => item.id === state.selectedTaskId);
    if (task) renderInferenceNote(task);
    refreshReviewHints(task);
  });
  el("#reviewTime").addEventListener("input", () => {
    const task = state.tasks.find((item) => item.id === state.selectedTaskId);
    refreshReviewHints(task);
  });
  el("#reviewDuration").addEventListener("change", refreshOccupancyPreview);
  el("#reviewAction").addEventListener("input", () => {
    const task = state.tasks.find((item) => item.id === state.selectedTaskId);
    // 用户自己改写了"具体下一步"，之后日期变化就不再自动覆盖它
    if (task) task.actionAuto = false;
  });
  el("#reviewStatus").addEventListener("change", () => {
    const task = state.tasks.find((item) => item.id === state.selectedTaskId);
    refreshReviewHints(task);
  });
  els("[data-capture-mode]").forEach((tab) => {
    tab.addEventListener("click", () => setCaptureMode(tab.dataset.captureMode));
  });
  el("#manualDateState").addEventListener("change", () => {
    syncManualDateState();
    clearFieldErrors();
  });
  ["manualDeadline", "manualTime", "manualDuration", "manualStatus", "manualCategory"].forEach(
    (id) => {
      el(`#${id}`).addEventListener("input", refreshManualOccupancy);
      el(`#${id}`).addEventListener("change", refreshManualOccupancy);
    },
  );
  ["manualTitle", "manualAction", "manualDeadline"].forEach((id) => {
    el(`#${id}`).addEventListener("input", () => clearFieldErrors());
  });
  el("#dropzone").addEventListener("click", () => el("#imageInput").click());
  el("#imageInput").addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      toast("请选择图片文件");
      return;
    }
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      const preview = document.createElement("img");
      preview.alt = "已选择的截图预览";
      preview.src = reader.result;
      preview.addEventListener("load", () => {
        const maxSide = 1400;
        const scale = Math.min(1, maxSide / Math.max(preview.naturalWidth, preview.naturalHeight));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(preview.naturalWidth * scale);
        canvas.height = Math.round(preview.naturalHeight * scale);
        canvas.getContext("2d").drawImage(preview, 0, 0, canvas.width, canvas.height);
        const imageData = canvas.toDataURL("image/jpeg", 0.82);
        state.captureDraft = { name: file.name, imageData };
        el("#imagePreview").innerHTML = '<img alt="已选择的截图预览" />';
        el("#imagePreview").querySelector("img").src = imageData;
        el("#imagePreview").classList.remove("hidden");
      });
    });
    reader.readAsDataURL(file);
  });
  els("[data-sample]").forEach((button) => {
    button.addEventListener("click", () => addSample(button.dataset.sample));
  });
  el("#saveCapture").addEventListener("click", saveCapture);
  el("#todayChip").textContent = new Intl.DateTimeFormat("zh-CN", {
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(today);
}

load();
wireGlobalEvents();
renderAll();
