"""验证 2026-11-24 真实使用反馈的修复是否生效。

覆盖 6 条反馈：
1. 分类与进度下拉不跟随输入
2. 手改日期后"具体下一步"仍留着旧日期
3. 裸星期"周四产品经理面试"推算不出日期
4. 没写时刻、没写具体截止日期时没有提示
5. 同一天多件事因缺时刻而没被判为冲突
6. 没有删除键，且重复提交未去重
"""

import asyncio, base64, json, os, subprocess, sys, time

sys.path.insert(0, "/tmp/zhouxu_qa")
from cdp import CDP, connect, http_json

BASE = "http://127.0.0.1:4173/?v=20261125-2"
OUT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/work/qa"
ROOT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/mvp"
os.makedirs(OUT, exist_ok=True)

results = []

CONTEXT_SCHOOL = "课程上下文（冲突比较时使用）"

STEP_CAPTURE_TEXT = """
(() => {
  window.__confirmMsg = null;
  window.confirm = (m) => { window.__confirmMsg = m; return false; };
  document.querySelector('#openCapture').click();
  document.querySelector('[data-capture-mode="text"]').click();
  document.querySelector('#rawTextInput').value = '%s';
  document.querySelector('#saveCapture').click();
  return true;
})()
"""

READ_REVIEW = """
(() => {
  const q = (s) => document.querySelector(s);
  return {
    title: q('#reviewTitle').value,
    category: q('#reviewCategory').value,
    status: q('#reviewStatus').value,
    deadline: q('#reviewDeadline').value,
    action: q('#reviewAction').value,
    contextLabel: q('#reviewContextLabel').textContent,
    prefill: q('#reviewPrefillNote').textContent,
    prefillHidden: q('#reviewPrefillNote').classList.contains('hidden'),
    timeHint: q('#reviewTimeHint').textContent,
    hintTone: q('#reviewTimeHint').className,
    basis: q('#reviewInferenceText').textContent,
    confirmMsg: window.__confirmMsg,
    toast: q('#toast').textContent,
    count: JSON.parse(localStorage.getItem('zhouxu-mvp-v2') || '[]')
      .filter(t => t.title === '产品经理面试').length
  };
})()
"""

SUBMIT_REVIEW = """
(() => {
  const form = document.querySelector('#reviewForm');
  form.dispatchEvent(new Event('submit', {bubbles:true, cancelable:true}));
  return true;
})()
"""

CHANGE_DEADLINE = """
(() => {
  const d = document.querySelector('#reviewDeadline');
  d.value = '%s';
  d.dispatchEvent(new Event('change', {bubbles:true}));
  return {
    action: document.querySelector('#reviewAction').value,
    basis: document.querySelector('#reviewInferenceText').textContent
  };
})()
"""

CHANGE_CATEGORY = """
(() => {
  const c = document.querySelector('#reviewCategory');
  c.value = '%s';
  c.dispatchEvent(new Event('change', {bubbles:true}));
  return {
    action: document.querySelector('#reviewAction').value,
    contextLabel: document.querySelector('#reviewContextLabel').textContent
  };
})()
"""

SET_CATEGORY_RECruiting = """
(() => {
  const c = document.querySelector('#reviewCategory');
  c.value = 'recruiting';
  c.dispatchEvent(new Event('change', {bubbles:true}));
  return true;
})()
"""

DELETE_SELECTED = """
(() => {
  const before = JSON.parse(localStorage.getItem('zhouxu-mvp-v2') || '[]').length;
  window.confirm = () => true;
  const btn = document.querySelector('#deleteTask');
  const visible = !!btn && !btn.classList.contains('hidden');
  btn.click();
  const after = JSON.parse(localStorage.getItem('zhouxu-mvp-v2') || '[]').length;
  return { before, after, visible, toast: document.querySelector('#toast').textContent };
})()
"""

SEED_SAME_DAY = """
(() => {
  const key = 'zhouxu-mvp-v2';
  const tasks = JSON.parse(localStorage.getItem(key) || '[]');
  tasks.push({
    id: 'qa-a', title: '数据课程作业', category: 'school', dateState: 'explicit',
    deadline: '2026-11-26', time: '', action: '提交实验报告', urgency: 'high',
    status: 'coursework', needsReview: false, sourceType: 'text',
    sourceText: '交作业', sourceUrl: '', sourceImage: '', context: '',
    selectedForConflict: false
  });
  tasks.push({
    id: 'qa-b', title: '产品经理面试', category: 'recruiting', dateState: 'explicit',
    deadline: '2026-11-26', time: '', action: '准备面试', urgency: 'high',
    status: 'interview', needsReview: false, sourceType: 'text',
    sourceText: '周四产品经理面试', sourceUrl: '', sourceImage: '', context: '',
    selectedForConflict: false
  });
  localStorage.setItem(key, JSON.stringify(tasks));
  location.reload();
  return true;
})()
"""

SEED_SAME_DAY_WITH_TIME = """
(() => {
  const key = 'zhouxu-mvp-v2';
  const tasks = JSON.parse(localStorage.getItem(key) || '[]');
  tasks.forEach(t => { if (t.id === 'qa-a' || t.id === 'qa-b') t.time = '19:00'; });
  localStorage.setItem(key, JSON.stringify(tasks));
  location.reload();
  return true;
})()
"""

READ_CONFLICT_VIEW = """
(() => {
  document.querySelector('[data-view="conflicts"]').click();
  const text = document.querySelector('#conflictContent').innerText;
  return {
    hasSameDay: text.includes('多件事排在一起'),
    hasHint: text.includes('暂未判定为冲突') || text.includes('补上时刻'),
    hardConflict: text.includes('组时间冲突需要处理'),
    softGone: !text.includes('多件事排在一起'),
    cards: document.querySelectorAll('#conflictContent .compare-card').length,
    conflictCount: document.querySelector('#conflictCount').textContent
  };
})()
"""

READ_EXPORT_HINT = """
(() => {
  const key = 'zhouxu-mvp-v2';
  const tasks = JSON.parse(localStorage.getItem(key) || '[]');
  const noTime = tasks.filter(t => !t.needsReview && t.dateState === 'explicit' && !t.time);
  const noDate = tasks.filter(t => !t.needsReview && t.dateState !== 'explicit');
  return { noTimeCount: noTime.length, noDateCount: noDate.length };
})()
"""


def check(name, value, expect):
    if isinstance(expect, tuple):
        mode, target = expect
        ok = (target in value) if mode == "contains" else (target not in value)
    elif isinstance(expect, bool):
        ok = bool(value) is expect
    elif isinstance(expect, (str, int)):
        ok = value == expect
    else:
        ok = expect in value
    results.append({"check": name, "ok": bool(ok), "value": value, "expect": expect})
    print(("PASS " if ok else "FAIL ") + name, "->", json.dumps(value, ensure_ascii=False))


async def main():
    srv = subprocess.Popen(["python3", "-m", "http.server", "4173", "--directory", ROOT],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    chrome = subprocess.Popen([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
        "--user-data-dir=/tmp/zhouxu_qa/profile_feedback", "--remote-debugging-port=9336",
        "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                http_json("http://127.0.0.1:9336/json/version")
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("chrome 未就绪")
        targets = http_json("http://127.0.0.1:9336/json/list")
        page = [t for t in targets if t["type"] == "page"][0]
        ws = await connect(page["webSocketDebuggerUrl"])
        cdp = CDP(ws)
        await cdp.call("Page.enable")
        await cdp.call("Runtime.enable")
        await cdp.call("Log.enable")
        await cdp.call("Emulation.setDeviceMetricsOverride", width=1440, height=900,
                       deviceScaleFactor=1, mobile=False)

        async def ev(expr):
            r = await cdp.call("Runtime.evaluate", expression=expr,
                                returnByValue=True, awaitPromise=True)
            if r.get("exceptionDetails"):
                return {"__error": json.dumps(r["exceptionDetails"], ensure_ascii=False)[:500]}
            return r["result"].get("value")

        async def shot(name):
            s = await cdp.call("Page.captureScreenshot", format="png")
            with open(os.path.join(OUT, name), "wb") as f:
                f.write(base64.b64decode(s["data"]))

        await cdp.call("Page.navigate", url=BASE)
        await asyncio.sleep(2.0)
        await ev("localStorage.clear(); location.reload();")
        await asyncio.sleep(2.0)

        await run_checks(cdp, ev)

        errors = []
        for e in cdp.events:
            m = e.get("method")
            if m == "Runtime.exceptionThrown":
                errors.append("exception: " + json.dumps(e["params"], ensure_ascii=False)[:400])
            if m == "Log.entryAdded" and e["params"]["entry"].get("level") == "error":
                errors.append("log: " + str(e["params"]["entry"].get("text")))
            if m == "Runtime.consoleAPICalled" and e["params"].get("type") == "error":
                errors.append("console: " + json.dumps(e["params"]["args"], ensure_ascii=False)[:400])

        with open(os.path.join(OUT, "feedback_report.json"), "w", encoding="utf-8") as f:
            json.dump({"checks": results, "errors": errors}, f, ensure_ascii=False, indent=2)
        print("\n=== 控制台错误 ===")
        print("\n".join(errors) if errors else "无")
        failed = [r for r in results if not r["ok"]]
        print("\n通过 %d/%d" % (len(results) - len(failed), len(results)))
        for r in failed:
            print("未通过:", r["check"], "->", json.dumps(r["value"], ensure_ascii=False))
    finally:
        chrome.terminate()
        srv.terminate()


async def run_checks(cdp, ev):
    # ---------- 反馈 1：输入"交作业"后分类/进度应自动预填 ----------
    await ev(STEP_CAPTURE_TEXT % "交作业")
    await asyncio.sleep(1.0)
    r = await ev(READ_REVIEW)
    check("1a 分类自动跟随原文", r["category"], "school")
    check("1b 进度自动跟随原文", r["status"], "coursework")
    check("1c 上下文文案跟着分类变", r["contextLabel"], CONTEXT_SCHOOL)
    check("1d 预填说明可见", r["prefillHidden"], False)
    check("1e 预填说明含依据", "作业" in r["prefill"], True)
    check("1f 下一步用课程口径", "课程" in r["action"], True)
    check("1g 无日期时给出课程口径提示", ("截止日期" in r["timeHint"]) and ("DDL" in r["timeHint"]), True)
    await ev(SUBMIT_REVIEW)
    await asyncio.sleep(0.8)

    # ---------- 反馈 3：裸星期"周四产品经理面试"应能推算日期 ----------
    await ev(STEP_CAPTURE_TEXT % "周四产品经理面试")
    await asyncio.sleep(1.0)
    r = await ev(READ_REVIEW)
    check("3a 裸星期推算出日期", r["deadline"], "2026-11-26")
    check("3b 标题剥离星期", r["title"], "产品经理面试")
    check("3c 分类为秋招", r["category"], "recruiting")
    check("3d 进度为面试", r["status"], "interview")
    check("3e 面试没写时刻有提示", "全天事件" in r["timeHint"], True)
    check("3f 提示用危险色", "urgent" in r["hintTone"], True)

    # ---------- 反馈 6：重复提交同一条文字应被拦住 ----------
    await ev(SUBMIT_REVIEW)
    await asyncio.sleep(0.8)
    await ev(STEP_CAPTURE_TEXT % "周四产品经理面试")
    await asyncio.sleep(1.0)
    r = await ev(READ_REVIEW)
    check("6a 重复提交被拦截", r["count"], 1)
    check("6b 提示说明是重复", "已经有一条" in (r["toast"] or ""), True)

    # ---------- 反馈 2：手改日期后，下一步描述要跟着变 ----------
    # 真实场景：输入"下周四"推算出 12/3，用户手动改成 11/26
    await ev(STEP_CAPTURE_TEXT % "下周四产品经理终面")
    await asyncio.sleep(1.0)
    r = await ev(READ_REVIEW)
    check("2a0 下周四推算到 12/3", r["deadline"], "2026-12-03")
    check("2a0b 标题是终面不是面试", r["title"], "产品经理终面")
    r = await ev(CHANGE_DEADLINE % "2026-11-26")
    check("2a 手改日期后下一步同步", ("11/26" in r["action"]) or ("11月26" in r["action"]), True)
    check("2b 描述里不再出现旧日期", ("12/3" not in r["action"]) and ("12月3" not in r["action"]), True)
    check("2c 推算依据标出手动修改", "手动改为" in r["basis"], True)

    r = await ev(CHANGE_CATEGORY % "school")
    check("2d 改分类后下一步换口径", "课程" in r["action"], True)
    check("2e 改分类后上下文文案跟着变", r["contextLabel"], CONTEXT_SCHOOL)

    await ev(SET_CATEGORY_RECruiting)
    await ev(SUBMIT_REVIEW)
    await asyncio.sleep(0.8)

    # ---------- 反馈 6：删除键 ----------
    r = await ev(DELETE_SELECTED)
    check("6c 确认页有删除按钮", r["visible"], True)
    check("6d 删除后少一条", r["after"], r["before"] - 1)

    r = await ev("document.querySelector('[data-view=\"week\"]').click(); "
                 "document.querySelectorAll('[data-delete-id]').length")
    check("6e 一周视图有删除入口", r >= 1, True)

    # ---------- 反馈 5：同一天多件事但缺时刻，应单独提示 ----------
    await ev(SEED_SAME_DAY)
    await asyncio.sleep(2.0)
    r = await ev(READ_CONFLICT_VIEW)
    check("5a 同日多件事被提示", r["hasSameDay"], True)
    check("5b 说明为什么没判冲突", r["hasHint"], True)
    check("5c 同日事项并排展示", r["cards"] >= 2, True)

    await ev(SEED_SAME_DAY_WITH_TIME)
    await asyncio.sleep(2.0)
    r = await ev(READ_CONFLICT_VIEW)
    check("5d 补时刻后升级为冲突", r["hardConflict"], True)
    check("5e 软提示随之消失", r["softGone"], True)


asyncio.run(main())
