"""验证冲突判定按"登记时刻"计算的行为。

模型：
- 笔试、面试登记的是开始时刻，往后推一个时段
- 作业、交付登记的是 DDL 时刻本身，只占那一刻

覆盖：
1. 作业截止 15:00 与面试 14:30 开始判为冲突（截止时刻落在面试时段里）
2. 两个时刻相同的笔试仍然判为冲突
3. 时段不重叠就不算冲突
4. 两个截止落在不同时刻不算冲突
5. 两个截止落在同一时刻算冲突
6. 缺时刻仍走"补时刻后判定"的软提示
7. 时长字段只在笔试/面试出现
8. 7 天视图给冲突事项打标记
"""

import asyncio, base64, json, os, subprocess, sys, time

sys.path.insert(0, "/tmp/zhouxu_qa")
from cdp import CDP, connect, http_json

ROOT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/mvp"
OUT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/work/qa"
BASE = "http://127.0.0.1:4173/?v=20261125-2"
os.makedirs(OUT, exist_ok=True)

results = []


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


SEED = """
(() => {
  const key = 'zhouxu-mvp-v2';
  const base = {
    dateState: 'explicit', urgency: 'medium', needsReview: false,
    sourceType: 'manual', sourceText: 'x', sourceUrl: '', sourceImage: '',
    context: '', selectedForConflict: false, category: 'recruiting'
  };
  const mk = (o) => Object.assign({ action: o.title, status: 'todo' }, base, o);
  localStorage.setItem(key, JSON.stringify([
    mk({ id: 'qa-hw',  title: '数据课程作业', category: 'school', status: 'coursework', deadline: '2026-11-26', time: '15:00' }),
    mk({ id: 'qa-itv', title: '产品经理面试', status: 'interview', deadline: '2026-11-26', time: '14:30' }),
    mk({ id: 'qa-e1',  title: '中国移动笔试', status: 'exam', deadline: '2026-11-27', time: '19:00' }),
    mk({ id: 'qa-e2',  title: '农业银行笔试', status: 'exam', deadline: '2026-11-27', time: '19:00' }),
    mk({ id: 'qa-far', title: '很远的事情', status: 'interview', deadline: '2026-11-27', time: '09:00' })
  ]));
  location.reload();
  return true;
})()
"""

READ_CONFLICTS = """
(() => {
  document.querySelector('[data-view="conflicts"]').click();
  const text = document.querySelector('#conflictContent').innerText;
  const groups = [...document.querySelectorAll('#conflictContent .conflict-group')].map(g => ({
    heading: g.querySelector('h3').innerText,
    reason: g.querySelector('.conflict-group-heading p').innerText,
    soft: g.classList.contains('soft')
  }));
  return {
    text,
    groups,
    count: document.querySelector('#conflictCount').textContent,
    hardCount: (text.match(/组时间冲突需要处理/) || [0]).length
  };
})()
"""


async def main():
    srv = subprocess.Popen(["python3", "-m", "http.server", "4173", "--directory", ROOT],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    chrome = subprocess.Popen([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
        "--user-data-dir=/tmp/zhouxu_qa/profile_conflict", "--remote-debugging-port=9341",
        "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                http_json("http://127.0.0.1:9341/json/version")
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("chrome 未就绪")
        page = [t for t in http_json("http://127.0.0.1:9341/json/list") if t["type"] == "page"][0]
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
                return {"__error": str(r["exceptionDetails"])[:400]}
            return r["result"].get("value")

        async def shot(name):
            s = await cdp.call("Page.captureScreenshot", format="png")
            with open(os.path.join(OUT, name), "wb") as f:
                f.write(base64.b64decode(s["data"]))

        await cdp.call("Page.navigate", url=BASE)
        await asyncio.sleep(2.2)
        await ev("localStorage.clear(); location.reload();")
        await asyncio.sleep(2.2)

        await run_checks(ev, shot)

        errors = []
        for e in cdp.events:
            m = e.get("method")
            if m == "Runtime.exceptionThrown":
                errors.append("exception")
            if m == "Log.entryAdded" and e["params"]["entry"].get("level") == "error":
                errors.append("log: " + str(e["params"]["entry"].get("text")))
            if m == "Runtime.consoleAPICalled" and e["params"].get("type") == "error":
                errors.append("console: " + json.dumps(e["params"]["args"], ensure_ascii=False)[:300])

        with open(os.path.join(OUT, "conflict_report.json"), "w", encoding="utf-8") as f:
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


async def run_checks(ev, shot):
    await ev(SEED)
    await asyncio.sleep(2.2)

    # ---------- 规则 1 与 2：截止时刻落在笔试/面试时段里 ----------
    r = await ev(READ_CONFLICTS)
    check("1a 冲突页有内容", len(r["groups"]) >= 1, True)
    check("1b 作业截止15:00与面试14:30判为冲突",
          ("数据课程作业" in r["text"]) and ("产品经理面试" in r["text"]), True)
    check("1c 不靠时刻完全一样才判冲突", r["hardCount"] >= 1, True)
    check("1d 时刻相同的两个笔试也算冲突",
          ("中国移动笔试" in r["text"]) and ("农业银行笔试" in r["text"]), True)
    check("1e 不重叠的面试不进冲突", "很远的事情" not in r["text"], True)
    check("1f 冲突计数正确", r["count"], "2")

    mixed = next((g for g in r["groups"]
                  if "截止时刻落在必须到场的时段里" in g["reason"]), None)
    check("1g 说明是截止时刻落在别人时段里",
          bool(mixed) and ("截止时刻落在必须到场的时段里" in mixed["reason"]), True)

    r = await ev("""
    (() => {
      const t = JSON.parse(localStorage.getItem('zhouxu-mvp-v2')).find(x => x.id === 'qa-hw');
      const win = taskOccupiedWindow(t);
      return {
        occupancy: describeOccupancy(t),
        from: win.from.getTime(),
        to: win.to.getTime()
      };
    })()
    """)
    check("1h 作业只显示截止时刻", r["occupancy"], "15:00 截止")
    check("1i 作业不铺准备窗口", r["from"] == r["to"], True)
    check("1j 作业时段基准不含需提前", ("需提前" not in r["occupancy"]), True)

    r = await ev("""
    (() => {
      const t = JSON.parse(localStorage.getItem('zhouxu-mvp-v2')).find(x => x.id === 'qa-itv');
      const win = taskOccupiedWindow(t);
      return {
        occupancy: describeOccupancy(t),
        from: win.from.getHours() + ':' + String(win.from.getMinutes()).padStart(2,'0'),
        to: win.to.getHours() + ':' + String(win.to.getMinutes()).padStart(2,'0')
      };
    })()
    """)
    check("1k 面试从开始时刻往后推",
          (r["from"] == "14:30" and r["to"] == "15:30"), True)
    check("1l 面试显示占用时长", "60 分钟" in r["occupancy"], True)

    # ---------- 规则 3：时段不重叠不算冲突 ----------
    await ev("""
    (() => {
      const key = 'zhouxu-mvp-v2';
      const tasks = JSON.parse(localStorage.getItem(key));
      const hw = tasks.find(t => t.id === 'qa-hw');
      hw.time = '20:00';
      localStorage.setItem(key, JSON.stringify(tasks));
      location.reload();
      return true;
    })()
    """)
    await asyncio.sleep(2.2)
    r = await ev(READ_CONFLICTS)
    check("3a 截止时刻在面试时段外就不算冲突",
          ("数据课程作业" in r["text"]) and ("产品经理面试" in r["text"]), False)
    check("3b 冲突数降为1", r["count"], "1")

    # ---------- 规则 4：两个截止落在不同时刻不算冲突 ----------
    await ev("""
    (() => {
      const key = 'zhouxu-mvp-v2';
      const tasks = JSON.parse(localStorage.getItem(key));
      const hw = tasks.find(t => t.id === 'qa-hw');
      hw.time = '11:00'; hw.deadline = '2026-11-26';
      const itv = tasks.find(t => t.id === 'qa-itv');
      itv.time = '14:30'; itv.deadline = '2026-11-26';
      const far = tasks.find(t => t.id === 'qa-far');
      far.deadline = '2026-11-27'; far.time = '09:00';
      localStorage.setItem(key, JSON.stringify(tasks));
      location.reload();
      return true;
    })()
    """)
    await asyncio.sleep(2.2)
    r = await ev(READ_CONFLICTS)
    check("4a 两个截止不同时刻不算冲突",
          ("数据课程作业" in r["text"]) and ("产品经理面试" in r["text"]), False)

    # ---------- 规则 5：两个截止落在同一时刻算冲突 ----------
    await ev("""
    (() => {
      const key = 'zhouxu-mvp-v2';
      const tasks = JSON.parse(localStorage.getItem(key));
      const hw = tasks.find(t => t.id === 'qa-hw');
      hw.time = '15:00'; hw.deadline = '2026-11-26';
      const itv = tasks.find(t => t.id === 'qa-itv');
      itv.time = '15:00'; itv.deadline = '2026-11-26'; itv.status = 'coursework';
      itv.category = 'school';
      localStorage.setItem(key, JSON.stringify(tasks));
      location.reload();
      return true;
    })()
    """)
    await asyncio.sleep(2.2)
    r = await ev(READ_CONFLICTS)
    check("5a 两个截止落在同一时刻算冲突",
          ("数据课程作业" in r["text"]) and ("产品经理面试" in r["text"]), True)
    same = next((g for g in r["groups"]
                 if "同一个截止时刻" in g["reason"]), None)
    check("5b 说明卡在同一个截止时刻",
          bool(same) and ("同一个截止时刻" in same["reason"]), True)

    # ---------- 规则 6：缺时刻走软提示 ----------
    await ev("""
    (() => {
      const key = 'zhouxu-mvp-v2';
      const tasks = JSON.parse(localStorage.getItem(key));
      tasks.find(t => t.id === 'qa-hw').time = '';
      const itv = tasks.find(t => t.id === 'qa-itv');
      itv.time = ''; itv.status = 'interview';
      const far = tasks.find(t => t.id === 'qa-far');
      far.deadline = '2026-11-26'; far.time = '';
      localStorage.setItem(key, JSON.stringify(tasks));
      location.reload();
      return true;
    })()
    """)
    await asyncio.sleep(2.2)
    r = await ev(READ_CONFLICTS)
    check("6a 缺时刻走软提示", "多件事排在一起" in r["text"], True)
    check("6b 软提示说明要补时刻",
          ("补上时刻" in r["text"]) or ("暂未判定为冲突" in r["text"]), True)

    # ---------- 时长字段只在笔试/面试出现 ----------
    await ev("""
    (() => {
      const key = 'zhouxu-mvp-v2';
      const tasks = JSON.parse(localStorage.getItem(key));
      const hw = tasks.find(t => t.id === 'qa-hw');
      hw.time = '15:00'; hw.deadline = '2026-11-26'; hw.needsReview = true;
      const itv = tasks.find(t => t.id === 'qa-itv');
      itv.time = '14:30'; itv.deadline = '2026-11-26'; itv.status = 'interview';
      itv.needsReview = true;
      const far = tasks.find(t => t.id === 'qa-far');
      far.deadline = '2026-11-27'; far.time = '09:00';
      localStorage.setItem(key, JSON.stringify(tasks));
      location.reload();
      return true;
    })()
    """)
    await asyncio.sleep(2.2)
    r = await ev("""
    (() => {
      document.querySelector('[data-view="inbox"]').click();
      const btn = document.querySelector('[data-review-id="qa-itv"]');
      if (btn) btn.click();
      const field = document.querySelector('#reviewDurationField');
      return {
        hiddenForInterview: field ? field.classList.contains('hidden') : null,
        label: document.querySelector('#reviewDurationLabel').textContent,
        occupancy: document.querySelector('#reviewOccupancy').textContent
      };
    })()
    """)
    check("7a 面试时显示时长字段", r["hiddenForInterview"], False)
    check("7b 面试时长字段有明确标签", r["label"], "面试时长")
    check("7c 面试回显占用时段",
          ("14:30" in r["occupancy"]) and ("15:30" in r["occupancy"]), True)

    r = await ev("""
    (() => {
      const t = document.querySelector('#reviewTime');
      t.value = '15:00';
      t.dispatchEvent(new Event('input', {bubbles:true}));
      const s = document.querySelector('#reviewStatus');
      s.value = 'coursework';
      s.dispatchEvent(new Event('change', {bubbles:true}));
      const field = document.querySelector('#reviewDurationField');
      return {
        hidden: field.classList.contains('hidden'),
        occupancy: document.querySelector('#reviewOccupancy').textContent
      };
    })()
    """)
    check("7d 作业时隐藏时长字段", r["hidden"], True)
    check("7e 作业只回显截止时刻",
          ("15:00" in r["occupancy"]) and ("截止" in r["occupancy"]), True)

    # ---------- 7 天视图冲突标记 ----------
    await ev("""
    (() => {
      const key = 'zhouxu-mvp-v2';
      const tasks = JSON.parse(localStorage.getItem(key));
      const hw = tasks.find(t => t.id === 'qa-hw');
      hw.time = '15:00'; hw.deadline = '2026-11-26'; hw.needsReview = false;
      hw.status = 'coursework'; hw.category = 'school';
      const itv = tasks.find(t => t.id === 'qa-itv');
      itv.time = '14:30'; itv.deadline = '2026-11-26'; itv.needsReview = false;
      itv.status = 'interview'; itv.category = 'recruiting';
      const far = tasks.find(t => t.id === 'qa-far');
      far.deadline = '2026-11-27'; far.time = '09:00';
      localStorage.setItem(key, JSON.stringify(tasks));
      location.reload();
      return true;
    })()
    """)
    await asyncio.sleep(2.2)
    r = await ev("""
    (() => {
      document.querySelector('[data-view="week"]').click();
      const cards = [...document.querySelectorAll('#dayList .event-card')].map(c => ({
        title: c.querySelector('.event-title').innerText,
        tags: [...c.querySelectorAll('.tag')].map(t => t.innerText),
        occupancy: c.querySelector('.event-occupancy')
          ? c.querySelector('.event-occupancy').innerText : ''
      }));
      return { cards };
    })()
    """)
    hw_card = next((c for c in r["cards"] if "数据课程作业" in c["title"]), None)
    itv_card = next((c for c in r["cards"] if "产品经理面试" in c["title"]), None)
    far_card = next((c for c in r["cards"] if "很远的事情" in c["title"]), None)
    check("8a 7天视图给冲突事项打标记",
          bool(hw_card) and ("时间冲突" in hw_card["tags"]), True)
    check("8b 面试卡也打时间冲突",
          bool(itv_card) and ("时间冲突" in itv_card["tags"]), True)
    check("8c 不冲突的事项没有冲突标记",
          bool(far_card) and ("时间冲突" not in far_card["tags"]), True)
    check("8d 作业卡显示截止时刻", bool(hw_card) and ("15:00" in hw_card["occupancy"]), True)
    check("8e 面试卡显示占用区间",
          bool(itv_card) and ("占用 14:30" in itv_card["occupancy"]), True)

    await ev("document.querySelector('[data-view=\"conflicts\"]').click();")
    await asyncio.sleep(0.4)
    await shot("conflict_view_desktop.png")
    await ev("document.querySelector('[data-view=\"week\"]').click();")
    await asyncio.sleep(0.4)
    await shot("conflict_desktop.png")


asyncio.run(main())
