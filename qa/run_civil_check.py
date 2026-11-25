"""验证"考公"作为第四个分类接入后，识别与冲突判定都照常工作。

设计前提：考公不做独立板块，只加一个分类。
报名缴费是 DDL 时点，笔试面试是开始时刻+时长，体检政审是日期型——
全部落进现有的"登记时刻 + 占用形态"模型，不新增任何数据结构。
"""

import asyncio, json, os, subprocess, sys, time

sys.path.insert(0, "/tmp/zhouxu_qa")
from cdp import CDP, connect, http_json

OUT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/work/qa"
BASE = "http://127.0.0.1:4173/?v=20261125-6"
os.makedirs(OUT, exist_ok=True)

results = []


def check(name, value, expect):
    if isinstance(expect, bool):
        ok = bool(value) is expect
    elif isinstance(expect, list):
        ok = value == expect
    elif isinstance(expect, (str, int)):
        ok = value == expect
    else:
        ok = expect in value
    results.append({"check": name, "ok": bool(ok), "value": value, "expect": expect})
    print(("PASS " if ok else "FAIL ") + name, "->", json.dumps(value, ensure_ascii=False))


INFER = """
(() => {
  const text = %s;
  const inferred = window.ZhouxuParser.inferTask(text);
  return {category: inferred.category, status: inferred.status, word: inferred.categoryWord};
})()
"""

SEED = """
(() => {
  const base = {dateState:'explicit', urgency:'medium', needsReview:false, sourceType:'manual', sourceText:'x', sourceUrl:'', sourceImage:'', context:'', selectedForConflict:false, action:'做点事'};
  const mk = (o) => Object.assign({status:'todo'}, base, o);
  const rows = [];
  rows.push(mk({id:'c-itv', title:'省考面试', category:'civil', status:'interview', deadline:'2026-11-26', time:'14:30'}));
  rows.push(mk({id:'c-hw', title:'课程作业', category:'school', status:'coursework', deadline:'2026-11-26', time:'15:00'}));
  localStorage.setItem('zhouxu-mvp-v2', JSON.stringify(rows));
  location.reload();
  return true;
})()
"""


async def main():
    chrome = subprocess.Popen([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
        "--user-data-dir=/tmp/zhouxu_qa/profile_civil", "--remote-debugging-port=9347",
        "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                http_json("http://127.0.0.1:9347/json/version")
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("chrome 未就绪")
        page = [t for t in http_json("http://127.0.0.1:9347/json/list") if t["type"] == "page"][0]
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
                return {"__error": str(r["exceptionDetails"])[:300]}
            return r["result"].get("value")

        await cdp.call("Page.navigate", url=BASE)
        await asyncio.sleep(2.5)
        await ev("localStorage.clear(); location.reload();")
        await asyncio.sleep(2.5)

        cases = [
            ("国考报名截止11月30日", "civil", "coursework"),
            ("省考笔试 3月14日 09:30 开考", "civil", "exam"),
            ("公务员面试 3月20日 14:00", "civil", "interview"),
            ("事业单位体检 3月25日 上午", "civil", "result"),
            ("选调生公示 4月2日", "civil", "result"),
            ("中国移动笔试 11月27日 19:00", "recruiting", "exam"),
            ("交数据结构实验报告 12月1日", "school", "coursework"),
            ("实习周报 12月3日", "internship", "todo"),
        ]
        for text, category, status in cases:
            r = await ev(INFER % json.dumps(text))
            check("识别 " + text, [r["category"], r["status"]], [category, status])

        r = await ev("""
        (() => ({
          chips: [...document.querySelectorAll('#categoryFilters .filter-button')].map(x => x.innerText),
          reviewOptions: [...document.querySelectorAll('#reviewCategory option')].map(x => x.value),
          manualOptions: [...document.querySelectorAll('#manualCategory option')].map(x => x.value)
        }))()
        """)
        check("2a 筛选有考公", ("考公" in r["chips"]), True)
        check("2b 确认页有考公选项", ("civil" in r["reviewOptions"]), True)
        check("2c 手动录入有考公选项", ("civil" in r["manualOptions"]), True)

        await ev(SEED)
        await asyncio.sleep(2.5)
        r = await ev("""
        (() => {
          document.querySelector('[data-view="conflicts"]').click();
          return {
            text: document.querySelector('#conflictContent').innerText,
            count: document.querySelector('#conflictCount').textContent
          };
        })()
        """)
        check("3a 考公面试与作业撞车被判冲突", ("省考面试" in r["text"]) and ("课程作业" in r["text"]), True)
        check("3b 冲突计数为 1", r["count"], "1")

        ics = await ev("buildICSText()")
        check("4a 导出的分类是考公", ("分类：考公" in ics), True)

        errors = []
        for e in cdp.events:
            if e.get("method") == "Runtime.exceptionThrown":
                errors.append("exception")
            if e.get("method") == "Log.entryAdded" and e["params"]["entry"].get("level") == "error":
                errors.append("log: " + str(e["params"]["entry"].get("text")))

        with open(os.path.join(OUT, "civil_report.json"), "w", encoding="utf-8") as f:
            json.dump({"checks": results, "errors": errors}, f, ensure_ascii=False, indent=2)
        print("\n=== 控制台错误 ===")
        print("\n".join(errors) if errors else "无")
        failed = [r for r in results if not r["ok"]]
        print("\n通过 %d/%d" % (len(results) - len(failed), len(results)))
        for r in failed:
            print("未通过:", r["check"], "->", json.dumps(r["value"], ensure_ascii=False))
    finally:
        chrome.terminate()


asyncio.run(main())
