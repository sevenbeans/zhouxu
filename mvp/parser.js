const WEEKDAY_MAP = {
  一: 1,
  二: 2,
  三: 3,
  四: 4,
  五: 5,
  六: 6,
  日: 0,
  天: 0,
};

const WEEKDAY_NAMES = {
  1: "周一",
  2: "周二",
  3: "周三",
  4: "周四",
  5: "周五",
  6: "周六",
  0: "周日",
};

const ACTION_WORDS = [
  "提交",
  "交",
  "报名",
  "投递",
  "笔试",
  "面试",
  "宣讲",
  "截止",
  "答辩",
  "汇报",
  "交付",
  "确认",
  "参加",
  "参加",
  "预约",
  "面试",
  "开题",
  "考试",
  "review",
  "整理",
  "填写",
  "上传",
  "下载",
  "参加",
];

function toIso(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function startOfWeek(date) {
  const result = new Date(date);
  const weekday = result.getDay();
  const offset = weekday === 0 ? -6 : 1 - weekday;
  result.setDate(result.getDate() + offset);
  result.setHours(0, 0, 0, 0);
  return result;
}

/**
 * 从自然语言中解析日期表达。
 * 只解析有明确指向的表达，解析不到就返回 null，绝不猜测。
 * 返回 matched 让调用方展示"根据原文推算"，把判断权交还用户。
 */
function parseDateExpression(text, today) {
  if (!text) return null;
  const source = String(text);

  const absolute = source.match(
    /(\d{4})\s*[年\-/.]\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})\s*日?/,
  );
  if (absolute) {
    const [, year, month, day] = absolute;
    const parsed = new Date(Number(year), Number(month) - 1, Number(day));
    if (!Number.isNaN(parsed.getTime())) {
      return {
        date: toIso(parsed),
        matched: absolute[0],
        basis: "原文包含完整日期",
        needsConfirmation: true,
      };
    }
  }

  const monthDay = source.match(/(\d{1,2})\s*月\s*(\d{1,2})\s*日?/);
  if (monthDay) {
    const [, month, day] = monthDay;
    let parsed = new Date(today.getFullYear(), Number(month) - 1, Number(day));
    if (parsed < today) {
      parsed = new Date(today.getFullYear() + 1, Number(month) - 1, Number(day));
    }
    return {
      date: toIso(parsed),
      matched: monthDay[0],
      basis: `原文只有月日，按今年 ${month} 月处理`,
      needsConfirmation: true,
    };
  }

  const relativeDay = source.match(/(\d{1,3})\s*天(?:后|之[后内]|以内)/);
  if (relativeDay) {
    const days = Number(relativeDay[1]);
    const parsed = new Date(today);
    parsed.setDate(parsed.getDate() + days);
    return {
      date: toIso(parsed),
      matched: relativeDay[0],
      basis: `原文写的是 ${days} 天后`,
      needsConfirmation: true,
    };
  }

  const weekBase = startOfWeek(today);
  const weekdayMatch = source.match(
    /(下+个?周|下星期|这周|本周|这个星期|下个星期)([一二三四五六日天])/,
  );
  if (weekdayMatch) {
    const prefix = weekdayMatch[1];
    const target = WEEKDAY_MAP[weekdayMatch[2]];
    const nextWeek = prefix.startsWith("下");
    const offset = nextWeek ? 7 : 0;
    const parsed = new Date(weekBase);
    parsed.setDate(parsed.getDate() + offset + target - 1);
    if (!nextWeek && parsed < today) {
      parsed.setDate(parsed.getDate() + 7);
    }
    return {
      date: toIso(parsed),
      matched: weekdayMatch[0],
      basis: nextWeek
        ? `原文写的是下${WEEKDAY_NAMES[target]}，已按下周计算`
        : `原文写的是本${WEEKDAY_NAMES[target]}`,
      needsConfirmation: true,
    };
  }

  // 只写"周四"这类不带"本/下"的星期：按本周该星期几计算，已经过去则顺延到下周
  const bareWeekday = source.match(/(?:周|星期|礼拜)([一二三四五六日天])/);
  if (bareWeekday) {
    const target = WEEKDAY_MAP[bareWeekday[1]];
    const parsed = new Date(weekBase);
    parsed.setDate(parsed.getDate() + target - 1);
    if (parsed < today) {
      parsed.setDate(parsed.getDate() + 7);
    }
    return {
      date: toIso(parsed),
      matched: bareWeekday[0],
      basis: `原文只写了${WEEKDAY_NAMES[target]}，按本周${WEEKDAY_NAMES[target]}计算，若当天已过则顺延到下周`,
      needsConfirmation: true,
    };
  }

  const dayLater = source.match(/大后天|大後天/);
  if (dayLater) {
    const parsed = new Date(today);
    parsed.setDate(parsed.getDate() + 3);
    return {
      date: toIso(parsed),
      matched: dayLater[0],
      basis: "原文写的是大后天",
      needsConfirmation: true,
    };
  }

  if (/后天|後天/.test(source)) {
    const parsed = new Date(today);
    parsed.setDate(parsed.getDate() + 2);
    return {
      date: toIso(parsed),
      matched: "后天",
      basis: "原文写的是后天",
      needsConfirmation: true,
    };
  }

  if (/明天|明日|次日/.test(source)) {
    const parsed = new Date(today);
    parsed.setDate(parsed.getDate() + 1);
    return {
      date: toIso(parsed),
      matched: source.match(/明天|明日|次日/)[0],
      basis: "原文写的是明天",
      needsConfirmation: true,
    };
  }

  if (/今天|今日|当天|今晚/.test(source)) {
    return {
      date: toIso(today),
      matched: source.match(/今天|今日|当天|今晚/)[0],
      basis: "原文写的是今天",
      needsConfirmation: true,
    };
  }

  if (/本周内|这周内|本星期内/.test(source)) {
    const parsed = new Date(weekBase);
    parsed.setDate(parsed.getDate() + 6);
    return {
      date: toIso(parsed),
      matched: "本周内",
      basis: "原文写的是本周内，按本周日计算",
      needsConfirmation: true,
    };
  }

  if (/下周|下星期/.test(source)) {
    const parsed = new Date(weekBase);
    parsed.setDate(parsed.getDate() + 13);
    return {
      date: toIso(parsed),
      matched: source.match(/下周|下星期/)[0],
      basis: "原文写的是下周，按下周日计算",
      needsConfirmation: true,
    };
  }

  if (/月底|月末/.test(source)) {
    const parsed = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    return {
      date: toIso(parsed),
      matched: source.match(/月底|月末/)[0],
      basis: "原文写的是月底，按本月最后一天计算",
      needsConfirmation: true,
    };
  }

  return null;
}

const CATEGORY_WORDS = {
  school: ["作业", "论文", "实验报告", "课程", "考试", "期末", "期中", "答辩", "预习", "复习", "习题", "课堂", "选课"],
  // 不放"报告"这种泛词：它会把"实验报告"误判成实习任务。
  internship: ["实习", "组会", "周报", "日报", "月报", "交付", "上线", "需求", "转正", "甲方", "值班"],
  recruiting: ["投递", "网申", "简历", "报名", "宣讲会", "宣讲", "双选会", "招聘会", "测评", "笔试", "面试", "复试", "群面", "offer", "录用意向", "招聘", "校招", "提前批", "秋招", "春招"],
  civil: ["考公", "公务员", "国考", "省考", "选调", "选调生", "事业单位", "事业编", "教师招聘", "教师资格", "招警", "公安招警", "三支一扶", "西部计划", "军队文职", "遴选", "公选", "事业单位联考", "法考", "司法考试"],
};

const STATUS_WORDS = [
  { status: "exam", label: "笔试", words: ["笔试", "机考", "笔试通知"] },
  { status: "interview", label: "面试", words: ["面试", "复试", "群面", "一面", "二面", "三面"] },
  { status: "result", label: "结果", words: ["体检", "政审", "公示", "资格复审", "考察", "录取名单"] },
  { status: "submitted", label: "已投递", words: ["投递", "网申", "简历", "报名", "双选会"] },
];

const CAMPUS_HINTS = ["秋招", "校招", "提前批", "春招"];

function firstMatch(text, words) {
  for (const word of words) {
    if (text.includes(word)) return word;
  }
  return "";
}

/**
 * 从原文推断分类和进度。
 * 只做预填，用户可以在确认页改，返回命中的关键词便于说明依据。
 */
function inferTask(text) {
  const source = String(text || "");
  if (!source.trim()) return null;

  const schoolWord = firstMatch(source, CATEGORY_WORDS.school);
  const internshipWord = firstMatch(source, CATEGORY_WORDS.internship);
  const recruitingWord = firstMatch(source, CATEGORY_WORDS.recruiting);
  const civilWord = firstMatch(source, CATEGORY_WORDS.civil);
  const campusWord = firstMatch(source, CAMPUS_HINTS);

  let category = "recruiting";
  let categoryWord = recruitingWord;
  // 考公优先：原文出现"国考/省考/选调/事业单位"这类词时，
  // 即使同时出现"报名""笔试"，也应该归到考公而不是秋招。
  if (civilWord) {
    category = "civil";
    categoryWord = civilWord;
  } else if (internshipWord && !campusWord) {
    category = "internship";
    categoryWord = internshipWord;
  } else if (schoolWord && !recruitingWord) {
    category = "school";
    categoryWord = schoolWord;
  } else if (recruitingWord) {
    category = "recruiting";
    categoryWord = recruitingWord;
  } else if (internshipWord) {
    category = "internship";
    categoryWord = internshipWord;
  } else if (schoolWord) {
    category = "school";
    categoryWord = schoolWord;
  }

  let status = "todo";
  let statusWord = "";
  for (const rule of STATUS_WORDS) {
    const word = firstMatch(source, rule.words);
    if (word) {
      status = rule.status;
      statusWord = word;
      break;
    }
  }
  if (status === "todo") {
    if (category === "school") {
      status = "coursework";
      statusWord = schoolWord;
    } else if (category === "internship") {
      status = "todo";
      statusWord = internshipWord;
    }
  }
  // 考公的"报名/缴费"还没交，不能标成"已投递"，标成"待提交"更贴近用户心理。
  if (category === "civil" && status === "submitted") {
    status = "coursework";
    statusWord = statusWord || civilWord;
  }

  return { category, status, categoryWord, statusWord };
}

function parseTimeExpression(text) {
  if (!text) return null;
  const source = String(text);
  const match = source.match(/(\d{1,2})\s*[:：点]\s*(\d{1,2})?\s*分?/);
  if (!match) return null;
  const hour = Number(match[1]);
  const minute = match[2] ? Number(match[2]) : 0;
  if (hour > 23 || minute > 59) return null;
  const period = source.match(/上午|早上|凌晨|下午|晚上|傍晚|中午/);
  let adjusted = hour;
  if (period && /下午|晚上|傍晚/.test(period[0]) && hour < 12) adjusted = hour + 12;
  if (period && /上午|早上|凌晨/.test(period[0]) && hour === 12) adjusted = 0;
  return {
    time: `${String(adjusted).padStart(2, "0")}:${String(minute).padStart(2, "0")}`,
    matched: match[0],
    needsConfirmation: true,
  };
}

const NOISE_PREFIX = [
  /【[^】]*】/g,
  /\[[^\]]*\]/g,
  /^(招聘|实习|校园招聘|宣讲会|通知|急|重要|转发)[:：\s]*/g,
];

const DATE_NOISE = [
  /\d{4}\s*[年\-/.]\s*\d{1,2}\s*[月\-/.]\s*\d{1,2}\s*日?/g,
  /\d{1,2}\s*月\s*\d{1,2}\s*日?/g,
  /(下+个?周|下星期|这周|本周|这个星期|下个星期)[一二三四五六日天]/g,
  /(?:周|星期|礼拜)[一二三四五六日天]/g,
  /\d{1,3}\s*天(?:后|之[后内]|以内)/g,
  /(大后天|大後天|后天|後天|明天|明日|次日|今天|今日|当天|今晚|本周内|这周内|本星期内|下周|下星期|月底|月末)/g,
  /\d{1,2}\s*[:：点]\s*\d{0,2}\s*分?(上午|下午|晚上|早上|中午)?/g,
  /(上午|下午|晚上|早上|中午|凌晨|傍晚)/g,
];

/**
 * 从一句话里取出可读的事项名称。
 * 优先挑含有动作词的分句；没有动作词就取第一个分句并清理噪声。
 */
function extractTitle(text) {
  if (!text) return "";
  let source = String(text).trim();
  if (!source) return "";

  const segments = source
    .split(/[\n。；;！!？?]/)
    .map((item) => item.trim())
    .filter(Boolean);
  if (!segments.length) return "";

  let picked = segments.find((segment) =>
    ACTION_WORDS.some((word) => segment.includes(word)),
  );
  if (!picked) picked = segments[0];

  let cleaned = picked;
  NOISE_PREFIX.forEach((pattern) => {
    cleaned = cleaned.replace(pattern, "");
  });
  DATE_NOISE.forEach((pattern) => {
    cleaned = cleaned.replace(pattern, " ");
  });
  cleaned = cleaned
    .replace(/(要|需要|得|记得|请)\s*(?=[交提交报名投递面试笔试])/, "")
    .replace(/\s{2,}/g, " ")
    .trim();

  const EDGE_WORDS =
    /^(之前|以前|前|以内|之内|截止前|截止|到|了|的|是|要|得|记得|请|帮我|把|对|关于|在)+|^(截止|投递|报名)\s*(?:到|至|在)\s*/;
  const TAIL_WORDS =
    /(之前|以前|前|以内|之内|截止前|截止到|截止|deadline|到|号|了|的|是|要|得|记得|请)+$/;
  let changed = true;
  while (changed) {
    const before = cleaned;
    cleaned = cleaned.replace(EDGE_WORDS, "").replace(TAIL_WORDS, "");
    cleaned = cleaned.replace(/(截止到|截止在|截止)\s*$/, "");
    changed = cleaned !== before;
  }
  cleaned = cleaned
    .replace(/\s{2,}/g, " ")
    .replace(/^[\s，,。.、:：\-—]+|[\s，,。.、:：\-—]+$/g, "")
    .trim();

  if (!cleaned) {
    cleaned = picked.slice(0, 24);
  }
  if (cleaned.length > 28) {
    cleaned = `${cleaned.slice(0, 28)}…`;
  }
  return cleaned;
}

window.ZhouxuParser = {
  parseDateExpression,
  parseTimeExpression,
  extractTitle,
  inferTask,
};
