"""验证 11/25 苹果用户反馈这一轮的修复。

覆盖：
1. 图片选择：input 不能是 display:none，改由 label 原生触发（iOS 才唤得起相册）
2. 图片事项的标题不再用文件名
3. 导出的 .ics 符合 iOS 导入要求：DTSTAMP 是 UTC、长行折行、ASCII 文件名
4. 同一天内按紧急程度排序，高紧急在前
5. 确认页字段用白话，次要信息默认折叠
6. "冲突怎么算"给人话解释
"""

import asyncio, base64, json, os, subprocess, sys, time

sys.path.insert(0, "/tmp/zhouxu_qa")
from cdp import CDP, connect, http_json

ROOT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/mvp"
OUT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/work/qa"
BASE = "http://127.0.0.1:4173/?v=20261125-5"
os.makedirs(OUT, exist_ok=True)

results = []


def check(name, value, expect):
    if isinstance(expect, bool):
        ok = bool(value) is expect
    elif isinstance(expect, (str, int)):
        ok = value == expect
    elif isinstance(expect, list):
        ok = value == expect
    else:
        ok = expect in value
    results.append({"check": name, "ok": bool(ok), "value": value, "expect": expect})
    print(("PASS " if ok else "FAIL ") + name, "->", json.dumps(value, ensure_ascii=False))


SEED = """
(() => {
  const base = {dateState:'explicit', urgency:'medium', needsReview:false, sourceType:'manual',
    sourceText:'x', sourceUrl:'', sourceImage:'', context:'', selectedForConflict:false,
    category:'recruiting'};
  const mk = (o) => Object.assign({status:'todo', action:'做点事'}, base, o);
  localStorage.setItem('zhouxu-mvp-v2', JSON.stringify([
    mk({id:'x-hw', title:'课程作业', category:'school', status:'coursework',
        deadline:'2026-11-26', time:'15:00', urgency:'low'}),
    mk({id:'x-itv', title:'产品经理面试', status:'interview',
        deadline:'2026-11-26', time:'14:30', urgency:'high'})
  ]));
  location.reload();
  return true;
})()
"""


async def main():
    chrome = subprocess.Popen([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
        "--user-data-dir=/tmp/zhouxu_qa/profile_ios", "--remote-debugging-port=9346",
        "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                http_json("http://127.0.0.1:9346/json/version")
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("chrome 未就绪")
        page = [t for t in http_json("http://127.0.0.1:9346/json/list") if t["type"] == "page"][0]
        ws = await connect(page["webSocketDebuggerUrl"])
        cdp = CDP(ws)
        await cdp.call("Page.enable")
        await cdp.call("Runtime.enable")
        await cdp.call("Log.enable")
        await cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=844,
                       deviceScaleFactor=2, mobile=True)
        await cdp.call("Emulation.setUserAgentOverride", userAgent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"))

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
        await ev(SEED)
        await asyncio.sleep(2.5)

        # ---------- 1. 图片选择框不能用 display:none ----------
        await ev("document.querySelector('#openCapture').click()")
        await asyncio.sleep(1)
        r = await ev("""
        (() => {
          const input = document.querySelector('#imageInput');
          const zone = document.querySelector('label[for="imageInput"]');
          return {
            display: getComputedStyle(input).display,
            hasLabel: Boolean(zone),
            accept: input.getAttribute('accept')
          };
        })()
        """)
        check("1a 图片输入框不是 display:none", r["display"] != "none", True)
        check("1b 图片输入框由 label 原生触发", r["hasLabel"], True)
        check("1c 只接受图片", r["accept"], "image/*")
        await shot("capture_ios_phone.png")

        # ---------- 2. 图片事项不再用文件名当标题 ----------
        r = await ev("""
        (() => {
          state.captureDraft = {name:'地信工程课程汇报.jpg', imageData:'data:image/jpeg;base64,AA'};
          saveCapture();
          const task = state.tasks[0];
          return {title: task.title, sourceType: task.sourceType, sourceText: task.sourceText};
        })()
        """)
        check("2a 标题不是文件名", (".jpg" not in r["title"]), True)
        check("2b 标题留空待用户填写", r["title"], "待确认事项")
        check("2c 明确告知本版本不识别图片文字", ("不识别图片文字" in r["sourceText"]), True)

        # ---------- 3. 导出的 .ics 要能被 iOS 导入 ----------
        ics = await ev("buildICSText()")
        lines = ics.split("\r\n")
        long_lines = 0
        for line in lines:
            if len(line.encode()) > 75:
                long_lines += 1
        stamps = [line for line in lines if line.startswith("DTSTAMP:")]
        check("3a ICS 以 VCALENDAR 开头", lines[0], "BEGIN:VCALENDAR")
        check("3b 有 VERSION 与 PRODID", ("VERSION:2.0" in lines) and any(line.startswith("PRODID:") for line in lines), True)
        check("3c DTSTAMP 用 UTC", all(line.endswith("Z") for line in stamps), True)
        check("3d 没有超过 75 字节的行", long_lines, 0)
        check("3e 有 VALARM 提醒", any(line.startswith("BEGIN:VALARM") for line in lines), True)

        await ev("document.querySelector('#exportButton').click()")
        await asyncio.sleep(0.8)
        r = await ev("""
        (() => ({
          title: document.querySelector('#exportGuideTitle').innerText,
          steps: document.querySelector('#exportGuideSteps').innerText
        }))()
        """)
        check("3f iPhone 指引给两种办法", ("办法一" in r["steps"]) and ("办法二" in r["steps"]), True)
        check("3g 说明日历 App 没有导入按钮", ("没有「导入」按钮" in r["steps"]), True)
        await shot("export_guide_ios.png")

        # ---------- 4. 同一天按紧急程度排序 ----------
        r = await ev("""
        (() => [...document.querySelectorAll('#weekView .day-row')].map(d => ({
          titles: [...d.querySelectorAll('.event-title')].map(x => x.innerText)
        })))()
        """)
        first_day = r[0]["titles"] if r else []
        check("4a 同一天高紧急排前面", first_day[:2], ["产品经理面试", "课程作业"])

        # ---------- 5/6. 确认页白话 + 折叠 ----------
        await ev("openReview('x-hw')")
        await asyncio.sleep(1)
        r = await ev("""
        (() => {
          const f = document.querySelector('#reviewForm');
          return {
            labels: [...f.querySelectorAll('.field > span')].map(x => x.innerText.split('\\n')[0]),
            extraOpen: f.querySelector('.review-extra').open,
            occupancy: document.querySelector('#reviewOccupancy').innerText
          };
        })()
        """)
        labels = r["labels"]
        check("5a 没有'具体下一步'这种说法", ("具体下一步" in " ".join(labels)), False)
        check("5b 有'要做什么'", ("要做什么" in labels), True)
        check("5c 有'冲突怎么算'", ("冲突怎么算" in labels), True)
        check("5d 次要信息默认折叠", r["extraOpen"], False)
        check("6a 冲突怎么算是人话", ("才算冲突" in r["occupancy"]), True)

        errors = []
        for e in cdp.events:
            if e.get("method") == "Runtime.exceptionThrown":
                errors.append("exception")
            if e.get("method") == "Log.entryAdded" and e["params"]["entry"].get("level") == "error":
                errors.append("log: " + str(e["params"]["entry"].get("text")))

        with open(os.path.join(OUT, "ios_fix_report.json"), "w", encoding="utf-8") as f:
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
