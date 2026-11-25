"""验证"会议是开始时刻型"这一轮修复。

用户原话：输入"明天晚上8点腾讯会议汇报5002"，
系统把 20:00 填进了"截止时间"，而且粘贴流程里没有估算时长的字段。

根因：只有笔试、面试被当成"要人到场"的事件，会议被当成截止型。
修法：把会议、宣讲、答辩、组会等纳入开始时刻型，
识别、时间解析、字段显隐、冲突判定、导出全部跟着走同一套逻辑。
"""

import asyncio, base64, json, os, subprocess, sys, time

sys.path.insert(0, "/tmp/zhouxu_qa")
from cdp import CDP, connect, http_json

OUT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/work/qa"
BASE = "http://127.0.0.1:4173/?v=20261125-8"
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


CAPTURE = """
(() => {
  document.querySelector('#openCapture').click();
  document.querySelector('[data-capture-mode="text"]').click();
  document.querySelector('#rawTextInput').value = %s;
  document.querySelector('#saveCapture').click();
  return true;
})()
"""


async def main():
    chrome = subprocess.Popen([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
        "--user-data-dir=/tmp/zhouxu_qa/profile_meeting", "--remote-debugging-port=9352",
        "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                http_json("http://127.0.0.1:9352/json/version")
                break
            except Exception:
                time.sleep(0.5)
        page = [t for t in http_json("http://127.0.0.1:9352/json/list") if t["type"] == "page"][0]
        ws = await connect(page["webSocketDebuggerUrl"])
        cdp = CDP(ws)
        await cdp.call("Page.enable")
        await cdp.call("Runtime.enable")
        await cdp.call("Log.enable")
        await cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=844,
                       deviceScaleFactor=2, mobile=True)

        async def ev(expr):
            r = await cdp.call("Runtime.evaluate", expression=expr,
                                returnByValue=True, awaitPromise=True)
            if r.get("exceptionDetails"):
                return {"__error": str(r["exceptionDetails"])[:300]}
            return r["result"].get("value")

        async def shot(name):
            s = await cdp.call("Page.captureScreenshot", format="png")
            with open(os.path.join(OUT, name), "wb") as f:
                f.write(base64.b64decode(s["data"]))

        await cdp.call("Page.navigate", url=BASE)
        await asyncio.sleep(2.5)
        await ev("localStorage.clear(); location.reload();")
        await asyncio.sleep(2.5)

        # ---------- 1. 用户原句走一遍粘贴流程 ----------
        await ev(CAPTURE % json.dumps("明天晚上8点腾讯会议汇报5002"))
        await asyncio.sleep(2)
        r = await ev("""
        (() => {
          const f = document.querySelector('#reviewForm');
          const task = state.tasks[0];
          return {
            status: task.status,
            time: task.time,
            title: task.title,
            context: task.context,
            dateLabel: document.querySelector('#reviewDeadlineLabel').innerText,
            timeLabel: document.querySelector('#reviewTimeLabel').innerText,
            durationHidden: f.querySelector('#reviewDurationField').classList.contains('hidden'),
            durationLabel: document.querySelector('#reviewDurationLabel').innerText,
            endHidden: f.querySelector('#reviewEndTimeField').classList.contains('hidden'),
            occupancy: document.querySelector('#reviewOccupancy').innerText,
            extraOpen: f.querySelector('.review-extra').open
          };
        })()
        """)
        check("1a 识别成会议", r["status"], "meeting")
        check("1b 时刻是 20:00", r["time"], "20:00")
        check("1c 标题去掉房间号", r["title"], "腾讯会议汇报")
        check("1d 房间号进补充说明", ("5002" in r["context"]), True)
        check("1e 日期字段变成开始日期", r["dateLabel"], "开始日期")
        check("1f 时间字段变成开始时间", r["timeLabel"], "开始时间")
        check("1g 估算时长字段出现", r["durationHidden"], False)
        check("1h 时长字段写明是会议", ("会议" in r["durationLabel"]), True)
        check("1i 结束时间字段出现", r["endHidden"], False)
        check("1j 有推算依据时展开折叠区", r["extraOpen"], True)
        check("1k 冲突怎么算给出时段", ("20:00–21:00" in r["occupancy"]), True)
        await shot("meeting_review_phone.png")

        # ---------- 2. 会议照样参与冲突判定 ----------
        r = await ev("""
        (() => {
          const base = {dateState:'explicit', urgency:'medium', needsReview:false,
            sourceType:'manual', sourceText:'x', sourceUrl:'', sourceImage:'',
            context:'', selectedForConflict:false, action:'做点事'};
          const mk = (o) => Object.assign({status:'todo'}, base, o);
          const rows = [];
          rows.push(mk({id:'m-meet', title:'腾讯会议汇报', category:'internship', status:'meeting',
            deadline:'2026-11-26', time:'20:00'}));
          rows.push(mk({id:'m-ddl', title:'交实验报告', category:'school', status:'coursework',
            deadline:'2026-11-26', time:'20:30'}));
          localStorage.setItem('zhouxu-mvp-v2', JSON.stringify(rows));
          location.reload();
          return true;
        })()
        """)
        await asyncio.sleep(2.5)
        r = await ev("""
        (() => {
          document.querySelector('[data-view="conflicts"]').click();
          return {text: document.querySelector('#conflictContent').innerText,
                  count: document.querySelector('#conflictCount').textContent};
        })()
        """)
        check("2a 会议时段内的截止算冲突", ("腾讯会议汇报" in r["text"]) and ("交实验报告" in r["text"]), True)
        check("2b 冲突计数为 1", r["count"], "1")

        # ---------- 3. 时间解析的老问题一并修掉 ----------
        cases = [
            ("周四下午2点半产品经理面试", "14:30", "产品经理面试"),
            ("下周一交数据结构实验报告，截止3点", "15:00", "交数据结构实验报告"),
            ("明天晚上8点腾讯会议汇报5002", "20:00", "腾讯会议汇报5002"),
            ("12月3日晚上8点组会", "20:00", "组会"),
        ]
        for raw_text, want_time, want_title in cases:
            r = await ev("""
            (() => {
              const raw = %s;
              const t = window.ZhouxuParser.parseTimeExpression(raw);
              return {time: t ? t.time : null, title: window.ZhouxuParser.extractTitle(raw)};
            })()
            """ % json.dumps(raw_text))
            check("3 解析 " + raw_text, [r["time"], r["title"]], [want_time, want_title])

        r = await ev("window.ZhouxuParser.parseTimeExpression('明天上午9点半面试')")
        check("3x 上午9点半", r["time"], "09:30")
        r = await ev("window.ZhouxuParser.parseTimeExpression('截止3点')")
        check("3y 无上下午按下午并说明", [r["time"], r["assumed"]], ["15:00", "按下午理解"])
        r = await ev("window.ZhouxuParser.parseTimeExpression('明天14:30面试')")
        check("3z 冒号写法保留分钟", r["time"], "14:30")

        errors = []
        for e in cdp.events:
            if e.get("method") == "Runtime.exceptionThrown":
                errors.append("exception")
            if e.get("method") == "Log.entryAdded" and e["params"]["entry"].get("level") == "error":
                errors.append("log: " + str(e["params"]["entry"].get("text")))

        with open(os.path.join(OUT, "meeting_report.json"), "w", encoding="utf-8") as f:
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
