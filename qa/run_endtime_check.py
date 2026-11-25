"""验证"考试有起止两个时刻"这一轮改动。

背景：用户指出考试是有时间的，不能只有一个开始时刻加一个估算时长。
处理：笔试、面试增加"结束时间"字段。
- 填了结束时间 → 用真实时段，冲突判定与导出都按真实时段
- 没填 → 回退到按类型估算的时长，并且界面明说这是估算
"""

import asyncio, json, os, subprocess, sys, time

sys.path.insert(0, "/tmp/zhouxu_qa")
from cdp import CDP, connect, http_json

OUT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/work/qa"
BASE = "http://127.0.0.1:4173/?v=20261125-7"
os.makedirs(OUT, exist_ok=True)

results = []


def check(name, value, expect):
    if expect is None:
        ok = value is None
    elif isinstance(expect, bool):
        ok = bool(value) is expect
    elif isinstance(expect, list):
        ok = value == expect
    elif isinstance(expect, (str, int)):
        ok = value == expect
    else:
        ok = expect in value
    results.append({"check": name, "ok": bool(ok), "value": value, "expect": expect})
    print(("PASS " if ok else "FAIL ") + name, "->", json.dumps(value, ensure_ascii=False))


SEED = """
(() => {
  const base = {dateState:'explicit', urgency:'medium', needsReview:false, sourceType:'manual',
    sourceText:'x', sourceUrl:'', sourceImage:'', context:'', selectedForConflict:false,
    category:'civil', action:'做点事'};
  const mk = (o) => Object.assign({status:'todo'}, base, o);
  const rows = [];
  rows.push(mk({id:'e-exam', title:'省考笔试', status:'exam', deadline:'2026-11-26', time:'09:30', endTime:'11:00'}));
  rows.push(mk({id:'e-ddl', title:'课程作业', category:'school', status:'coursework', deadline:'2026-11-26', time:'10:30'}));
  rows.push(mk({id:'e-guess', title:'产品经理面试', status:'interview', deadline:'2026-11-27', time:'14:30'}));
  localStorage.setItem('zhouxu-mvp-v2', JSON.stringify(rows));
  location.reload();
  return true;
})()
"""


async def main():
    chrome = subprocess.Popen([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
        "--user-data-dir=/tmp/zhouxu_qa/profile_endtime", "--remote-debugging-port=9349",
        "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                http_json("http://127.0.0.1:9349/json/version")
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("chrome 未就绪")
        page = [t for t in http_json("http://127.0.0.1:9349/json/list") if t["type"] == "page"][0]
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
        await ev(SEED)
        await asyncio.sleep(2.5)

        # ---------- 1. 占用时段用真实结束时间 ----------
        r = await ev("""
        (() => {
          const t = JSON.parse(localStorage.getItem('zhouxu-mvp-v2')).find(x => x.id === 'e-exam');
          const w = taskOccupiedWindow(t);
          return {
            from: formatClock(w.from),
            to: formatClock(w.to),
            minutes: w.minutes,
            estimated: w.estimated,
            occupancy: describeOccupancy(t)
          };
        })()
        """)
        check("1a 笔试用登记的结束时间", [r["from"], r["to"]], ["09:30", "11:00"])
        check("1b 时长按真实起止算", r["minutes"], 90)
        check("1c 不是估算", r["estimated"], False)
        check("1d 展示不写估算", ("估算" not in r["occupancy"]), True)

        # ---------- 2. 没填结束时间才估算，并且说清楚 ----------
        r = await ev("""
        (() => {
          const t = JSON.parse(localStorage.getItem('zhouxu-mvp-v2')).find(x => x.id === 'e-guess');
          const w = taskOccupiedWindow(t);
          return {minutes: w.minutes, estimated: w.estimated, hint: plainOccupancyHint(t)};
        })()
        """)
        check("2a 面试缺结束时间时按 60 分钟估算", r["minutes"], 60)
        check("2b 标明是估算", r["estimated"], True)
        check("2c 提示里说明是估算", ("估算" in r["hint"]), True)

        # ---------- 3. 冲突判定用真实时段 ----------
        r = await ev("""
        (() => {
          document.querySelector('[data-view="conflicts"]').click();
          const text = document.querySelector('#conflictContent').innerText;
          return {text: text, count: document.querySelector('#conflictCount').textContent};
        })()
        """)
        check("3a 落在真实时段里判为冲突", ("省考笔试" in r["text"]) and ("课程作业" in r["text"]), True)
        check("3b 冲突标题写出真实区间", ("09:30–11:00" in r["text"]), True)
        check("3c 冲突计数为 1", r["count"], "1")

        # ---------- 4. 界面：填了结束时间就不问时长 ----------
        r = await ev("""
        (() => {
          openReview('e-exam');
          const f = document.querySelector('#reviewForm');
          return {
            endValue: document.querySelector('#reviewEndTime').value,
            endHidden: f.querySelector('#reviewEndTimeField').classList.contains('hidden'),
            durationHidden: f.querySelector('#reviewDurationField').classList.contains('hidden')
          };
        })()
        """)
        check("4a 结束时间回显", r["endValue"], "11:00")
        check("4b 结束时间字段显示", r["endHidden"], False)
        check("4c 填了结束时间就不再问时长", r["durationHidden"], True)

        r = await ev("""
        (() => {
          openReview('e-guess');
          const f = document.querySelector('#reviewForm');
          return {
            durationHidden: f.querySelector('#reviewDurationField').classList.contains('hidden'),
            endHidden: f.querySelector('#reviewEndTimeField').classList.contains('hidden')
          };
        })()
        """)
        check("4d 没填结束时间才显示时长", r["durationHidden"], False)
        check("4e 结束时间字段仍然可见", r["endHidden"], False)

        # ---------- 5. 作业这类截止型不出现结束时间 ----------
        r = await ev("""
        (() => {
          openReview('e-ddl');
          const f = document.querySelector('#reviewForm');
          return {
            endHidden: f.querySelector('#reviewEndTimeField').classList.contains('hidden'),
            durationHidden: f.querySelector('#reviewDurationField').classList.contains('hidden')
          };
        })()
        """)
        check("5a 作业不显示结束时间", r["endHidden"], True)
        check("5b 作业不显示时长", r["durationHidden"], True)

        # ---------- 6. 文本里的区间能一次认出结束时刻 ----------
        r = await ev("window.ZhouxuParser.parseEndTimeExpression('省考笔试 3月14日 09:30-11:00 开考')")
        check("6a 区间文本认出结束时刻", r["endTime"], "11:00")
        r = await ev("window.ZhouxuParser.parseEndTimeExpression('明天下午3点到5点面试')")
        check("6b 下午区间换算成 24 小时制", r["endTime"], "17:00")
        r = await ev("window.ZhouxuParser.parseEndTimeExpression('明天9点半面试')")
        check("6c 没有区间就不猜结束时刻", r, None)

        # ---------- 7. 导出的 ICS 用真实结束时刻 ----------
        ics = await ev("buildICSText()")
        check("7a 导出写的是真实 DTEND", ("DTSTART:20261126T093000" in ics) and ("DTEND:20261126T110000" in ics), True)
        check("7b 截止型导出成 30 分钟短区间",
              ("DTSTART:20261126T103000" in ics) and ("DTEND:20261126T110000" in ics), True)

        errors = []
        for e in cdp.events:
            if e.get("method") == "Runtime.exceptionThrown":
                errors.append("exception")
            if e.get("method") == "Log.entryAdded" and e["params"]["entry"].get("level") == "error":
                errors.append("log: " + str(e["params"]["entry"].get("text")))

        with open(os.path.join(OUT, "endtime_report.json"), "w", encoding="utf-8") as f:
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
