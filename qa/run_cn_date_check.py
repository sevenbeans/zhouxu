"""验证中文日期表达的识别。

用户反馈："下个月3号""两天后""三天后"这类中文写法识别不了，
必须先写成阿拉伯数字才能用。

覆盖：
1. 中文数字的相对天数（两天后、三天后、十天后、一周后）
2. 带前缀的月日（下个月3号、这个月15号、本月3号、下个月底）
3. 日期表达不残留到标题里
4. 已经过去的日期会顺延并说明依据
5. 原来的表达不受影响（绝对日期、星期、明天后天）
"""

import asyncio, base64, json, os, subprocess, sys, time

sys.path.insert(0, "/tmp/zhouxu_qa")
from cdp import CDP, connect, http_json

OUT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/work/qa"
BASE = "http://127.0.0.1:4173/?v=20261125-9"
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


READ = """
(() => {
  const raw = %s;
  const d = window.ZhouxuParser.parseDateExpression(raw, new Date());
  const t = window.ZhouxuParser.parseTimeExpression(raw);
  return {
    date: d ? d.date : null,
    basis: d ? d.basis : null,
    time: t ? t.time : null,
    title: window.ZhouxuParser.extractTitle(raw)
  };
})()
"""


async def main():
    chrome = subprocess.Popen([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
        "--user-data-dir=/tmp/zhouxu_qa/profile_cndate", "--remote-debugging-port=9354",
        "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                http_json("http://127.0.0.1:9354/json/version")
                break
            except Exception:
                time.sleep(0.5)
        page = [t for t in http_json("http://127.0.0.1:9354/json/list") if t["type"] == "page"][0]
        ws = await connect(page["webSocketDebuggerUrl"])
        cdp = CDP(ws)
        await cdp.call("Page.enable")
        await cdp.call("Runtime.enable")
        await cdp.call("Log.enable")

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

        # 相对天数：中文数字
        cases = [
            ("两天后", "2026-11-27"),
            ("三天后", "2026-11-28"),
            ("两天之后", "2026-11-27"),
            ("十天后", "2026-12-05"),
            ("一周后", "2026-12-02"),
            ("三天内", "2026-11-28"),
        ]
        for text, want in cases:
            r = await ev(READ % json.dumps(text))
            check("1 识别 " + text, r["date"], want)

        # 带前缀的月日
        cases = [
            ("下个月3号", "2026-12-03"),
            ("下个月三号交材料", "2026-12-03"),
            ("下个月底", "2026-12-31"),
            ("本月3号", "2026-12-03"),
            ("这个月15号", "2026-12-15"),
        ]
        for text, want in cases:
            r = await ev(READ % json.dumps(text))
            check("2 识别 " + text, r["date"], want)

        # 日期表达不残留到标题
        r = await ev(READ % json.dumps("3号交实验报告"))
        check("3a 标题去掉日期前缀", r["title"], "交实验报告")
        r = await ev(READ % json.dumps("下个月三号交材料"))
        check("3b 标题去掉下个月三号", r["title"], "交材料")
        r = await ev(READ % json.dumps("两天后"))
        check("3c 整句是日期时标题留空", r["title"], "")

        # 顺延要说明依据
        r = await ev(READ % json.dumps("本月3号"))
        check("4 已过去的日期说明依据", ("已经过去" in r["basis"]) and ("下个月" in r["basis"]), True)

        # 原有表达不受影响
        cases = [
            ("2026年12月20日截止", "2026-12-20"),
            ("12月3日晚上8点组会", "2026-12-03"),
            ("下周五下午2点产品经理面试", "2026-12-04"),
            ("后天交报告", "2026-11-27"),
            ("大后天面试", "2026-11-28"),
            ("明天下午3点面试", "2026-11-26"),
        ]
        for text, want in cases:
            r = await ev(READ % json.dumps(text))
            check("5 仍能识别 " + text, r["date"], want)

        r = await ev(READ % json.dumps("明天下午3点面试"))
        check("5x 时刻不受影响", r["time"], "15:00")

        # 端到端：粘贴"两天后交实验报告"
        await ev("""
        (() => {
          localStorage.clear();
          document.querySelector('#openCapture').click();
          document.querySelector('[data-capture-mode="text"]').click();
          document.querySelector('#rawTextInput').value = '两天后交实验报告';
          document.querySelector('#saveCapture').click();
          return true;
        })()
        """)
        await asyncio.sleep(2)
        r = await ev("""
        (() => {
          const task = state.tasks[0];
          return {
            deadline: task.deadline,
            title: task.title,
            dateValue: document.querySelector('#reviewDeadline').value,
            basis: document.querySelector('#reviewInferenceText').innerText
          };
        })()
        """)
        check("6a 粘贴后日期回填", r["dateValue"], "2026-11-27")
        check("6b 标题是交实验报告", r["title"], "交实验报告")
        check("6c 推算依据写明 2 天后", ("2 天后" in r["basis"]), True)

        errors = []
        for e in cdp.events:
            if e.get("method") == "Runtime.exceptionThrown":
                errors.append("exception")
            if e.get("method") == "Log.entryAdded" and e["params"]["entry"].get("level") == "error":
                errors.append("log: " + str(e["params"]["entry"].get("text")))

        with open(os.path.join(OUT, "cn_date_report.json"), "w", encoding="utf-8") as f:
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
