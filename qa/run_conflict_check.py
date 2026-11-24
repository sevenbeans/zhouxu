"""验证冲突判定改成"占用时段重叠"之后的行为。

覆盖：
1. 面试 14:30 与作业截止 15:00 判为冲突（不要求时刻完全一样）
2. 时刻完全相同的两个笔试仍然判为冲突
3. 时段不重叠的两件事不判为冲突
4. 截止那一刻正好撞上必须到场的时段，也算冲突
5. 缺时刻的事项仍走"补时刻后判定"的软提示
6. 冲突页能显示具体重叠时段
7. 确认页与手动录入都能设置预计占用时长
"""

import asyncio, base64, json, os, subprocess, sys, time

sys.path.insert(0, "/tmp/zhouxu_qa")
from cdp import CDP, connect, http_json

ROOT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/mvp"
OUT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/work/qa"
BASE = "http://127.0.0.1:4173/?v=20261125-1"
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

SET_TIMES = """
(hwTime, hwDur, itvTime, itvDur) => {
  const key = 'zhouxu-mvp-v2';
  const tasks = JSON.parse(localStorage.getItem(key));
  const hw = tasks.find(t => t.id === 'qa-hw');
  const itv = tasks.find(t => t.id === 'qa-itv');
  if (hwTime !== null) { hw.time = hwTime; hw.deadline = '2026-11-26'; }
  if (hwDur !== null) hw.durationMin = hwDur;
  if (itvTime !== null) { itv.time = itvTime; itv.deadline = '2026-11-26'; }
  if (itvDur !== null) itv.durationMin = itvDur;
  localStorage.setItem(key, JSON.stringify(tasks));
  location.reload();
  return true;
}
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

    r = await ev(READ_CONFLICTS)
    check("1a 冲突页有内容", len(r["groups"]) >= 1, True)
    check("1b 作业截止15:00与面试14:30判为冲突",
          ("数据课程作业" in r["text"]) and ("产品经理面试" in r["text"]), True)
    check("1c 不靠时刻完全一样才判冲突", r["hardCount"] >= 1, True)
    check("1d 冲突组显示重叠时段", ("14:30" in r["text"]) and ("15:00" in r["text"]), True)
    check("1e 时刻相同的两个笔试也算冲突",
          ("中国移动笔试" in r["text"]) and ("农业银行笔试" in r["text"]), True)
    check("1f 冲突页显示占用时段说明", "占用时段" in r["text"], True)
    check("1g 不重叠的面试不进冲突", "很远的事情" not in r["text"], True)
    check("1h 冲突计数正确", r["count"], "2")

    # 截止那一刻正好落在必须到场的时段里
    await ev(SET_TIMES + "")
    await ev("""
    (() => {
      const key = 'zhouxu-mvp-v2';
      const tasks = JSON.parse(localStorage.getItem(key));
      const itv = tasks.find(t => t.id === 'qa-itv');
      const hw = tasks.find(t => t.id === 'qa-hw');
      itv.time = '14:00'; itv.durationMin = 30;
      hw.time = '14:30'; hw.durationMin = 15;
      localStorage.setItem(key, JSON.stringify(tasks));
      location.reload();
      return true;
    })()
    """)
    await asyncio.sleep(2.2)
    r = await ev(READ_CONFLICTS)
    check("2a 截止时刻紧接面试也判为冲突",
          ("数据课程作业" in r["text"]) and ("产品经理面试" in r["text"]), True)

    # 完全不重叠
    await ev("""
    (() => {
      const key = 'zhouxu-mvp-v2';
      const tasks = JSON.parse(localStorage.getItem(key));
      const hw = tasks.find(t => t.id === 'qa-hw');
      hw.time = '20:00'; hw.durationMin = 60;
      localStorage.setItem(key, JSON.stringify(tasks));
      location.reload();
      return true;
    })()
    """)
    await asyncio.sleep(2.2)
    r = await ev(READ_CONFLICTS)
    check("3a 时段不重叠就不算冲突",
          ("数据课程作业" in r["text"]) and ("产品经理面试" in r["text"]), False)
    check("3b 冲突数降为1", r["count"], "1")

    # 缺时刻 → 软提示
    await ev("""
    (() => {
      const key = 'zhouxu-mvp-v2';
      const tasks = JSON.parse(localStorage.getItem(key));
      tasks.find(t => t.id === 'qa-hw').time = '';
      const far = tasks.find(t => t.id === 'qa-far');
      far.time = '09:00'; far.deadline = '2026-11-26';
      localStorage.setItem(key, JSON.stringify(tasks));
      location.reload();
      return true;
    })()
    """)
    await asyncio.sleep(2.2)
    r = await ev(READ_CONFLICTS)
    check("4a 缺时刻走软提示", "多件事排在一起" in r["text"], True)
    check("4b 软提示说明要补时刻",
          ("补上时刻" in r["text"]) or ("暂未判定为冲突" in r["text"]), True)

    # 确认页的占用时长
    await ev("""
    (() => {
      const key = 'zhouxu-mvp-v2';
      const tasks = JSON.parse(localStorage.getItem(key));
      const hw = tasks.find(t => t.id === 'qa-hw');
      hw.time = '15:00'; hw.deadline = '2026-11-26';
      const itv = tasks.find(t => t.id === 'qa-itv');
      itv.time = '14:30'; itv.deadline = '2026-11-26'; itv.durationMin = undefined;
      const far = tasks.find(t => t.id === 'qa-far');
      far.deadline = '2026-11-27'; far.time = '09:00';
      itv.needsReview = true;
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
      const occ = document.querySelector('#reviewOccupancy');
      return {
        hasDuration: !!document.querySelector('#reviewDuration'),
        hasOccupancy: !!occ,
        occupancy: occ ? occ.textContent : ''
      };
    })()
    """)
    check("5a 确认页有占用时长字段", r["hasDuration"], True)
    check("5b 确认页回显占用时段", r["hasOccupancy"], True)
    check("5c 占用时段按面试时长算",
          ("14:30" in r["occupancy"]) and ("60 分钟" in r["occupancy"]), True)

    r = await ev("""
    (() => {
      const d = document.querySelector('#reviewDuration');
      d.value = '120';
      d.dispatchEvent(new Event('change', {bubbles:true}));
      return document.querySelector('#reviewOccupancy').textContent;
    })()
    """)
    check("5d 改时长后占用时段跟着变", "120 分钟" in r, True)

    r = await ev("""
    (() => {
      const form = document.querySelector('#reviewForm');
      form.dispatchEvent(new Event('submit', {bubbles:true, cancelable:true}));
      const tasks = JSON.parse(localStorage.getItem('zhouxu-mvp-v2'));
      const t = tasks.find(x => x.id === 'qa-itv');
      return {durationMin: t.durationMin, needsReview: t.needsReview};
    })()
    """)
    await asyncio.sleep(0.8)
    check("5e 时长被保存", r["durationMin"], 120)
    check("5f 保存后进入已确认", r["needsReview"], False)

    # 手动录入也有时长字段
    r = await ev("""
    (() => {
      document.querySelector('#openCapture').click();
      document.querySelector('[data-capture-mode="manual"]').click();
      const hasDuration = !!document.querySelector('#manualDuration');
      document.querySelector('#manualTitle').value = '产品作业2';
      document.querySelector('#manualAction').value = '交作业';
      document.querySelector('#manualDeadline').value = '2026-11-28';
      document.querySelector('#manualTime').value = '16:00';
      document.querySelector('#manualDuration').value = '45';
      document.querySelector('#manualDuration').dispatchEvent(new Event('change', {bubbles:true}));
      const occupancy = document.querySelector('#manualOccupancy').textContent;
      document.querySelector('#saveCapture').click();
      const tasks = JSON.parse(localStorage.getItem('zhouxu-mvp-v2'));
      const t = tasks[0];
      return {hasDuration, occupancy, durationMin: t.durationMin, title: t.title};
    })()
    """)
    check("6a 手动录入有时长字段", r["hasDuration"], True)
    check("6b 手动录入回显占用时段", "45 分钟" in r["occupancy"], True)
    check("6c 手动录入时长被保存", r["durationMin"], 45)

    # 7 天视图：冲突卡片要打上标记，用户不用去冲突页才知道撞车了
    await ev("""
    (() => {
      const key = 'zhouxu-mvp-v2';
      const tasks = JSON.parse(localStorage.getItem(key));
      const hw = tasks.find(t => t.id === 'qa-hw');
      hw.time = '15:00'; hw.deadline = '2026-11-26'; hw.needsReview = false;
      const itv = tasks.find(t => t.id === 'qa-itv');
      itv.time = '14:30'; itv.deadline = '2026-11-26'; itv.needsReview = false;
      itv.durationMin = undefined;
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
      return {
        cards,
        text: document.querySelector('#dayList').innerText
      };
    })()
    """)
    hw_card = next((c for c in r["cards"] if "数据课程作业" in c["title"]), None)
    itv_card = next((c for c in r["cards"] if "产品经理面试" in c["title"]), None)
    check("7a 7天视图给冲突事项打标记",
          bool(hw_card) and ("时间冲突" in hw_card["tags"]), True)
    check("7b 面试卡也打时间冲突",
          bool(itv_card) and ("时间冲突" in itv_card["tags"]), True)
    far_card = next((c for c in r["cards"] if "很远的事情" in c["title"]), None)
    check("7c 不冲突的事项没有冲突标记",
          bool(far_card) and ("时间冲突" not in far_card["tags"]), True)
    check("7d 卡片显示占用时段",
          bool(hw_card) and ("15:00" in hw_card["occupancy"]), True)
    check("7e 占用时段标出开始时间",
          bool(itv_card) and ("14:30" in itv_card["occupancy"]), True)

    await ev("document.querySelector('[data-view=\"conflicts\"]').click();")
    await asyncio.sleep(0.4)
    await shot("conflict_view_desktop.png")

    await shot("conflict_desktop.png")


asyncio.run(main())
