"""验证手动录入路径：提交必须有反馈，错误提示必须看得见。"""

import asyncio, json, os, subprocess, sys, time

sys.path.insert(0, "/tmp/zhouxu_qa")
from cdp import CDP, connect, http_json

ROOT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/mvp"
OUT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/work/qa"
BASE = "http://127.0.0.1:4173/?v=20261125-2"

results = []


def check(name, value, expect):
    if isinstance(expect, tuple):
        mode, target = expect
        ok = (target in value) if mode == "contains" else (target not in value)
    elif isinstance(expect, bool):
        ok = bool(value) is expect
    elif isinstance(expect, (str, int)):
        ok = value == expect
    elif isinstance(expect, list):
        ok = list(value) == expect
    else:
        ok = expect in value
    results.append({"check": name, "ok": bool(ok), "value": value, "expect": expect})
    print(("PASS " if ok else "FAIL ") + name, "->", json.dumps(value, ensure_ascii=False))


OPEN_MANUAL = """
(() => {
  document.querySelector('#openCapture').click();
  document.querySelector('[data-capture-mode="manual"]').click();
  return {
    panelVisible: document.querySelector('[data-mode-panel="manual"]').classList.contains('active'),
    dateState: document.querySelector('#manualDateState').value,
    hint: document.querySelector('#manualHint').textContent
  };
})()
"""

FILL = """
(() => {
  document.querySelector('#manualTitle').value = '%s';
  document.querySelector('#manualAction').value = '%s';
  if ('%s') document.querySelector('#manualDeadline').value = '%s';
  return true;
})()
"""

CLICK_SAVE = """
(() => {
  document.querySelector('#saveCapture').click();
  const dlg = document.querySelector('#captureDialog');
  const tasks = JSON.parse(localStorage.getItem('zhouxu-mvp-v2') || '[]');
  const dlgToast = document.querySelector('#captureToast');
  const mainToast = document.querySelector('#toast');
  const tr = dlgToast.getBoundingClientRect();
  const elAt = tr.height > 0
    ? document.elementFromPoint(tr.left + tr.width / 2, tr.top + tr.height / 2)
    : null;
  return {
    dlgOpen: dlg.open,
    taskCount: tasks.length,
    newest: tasks[0] ? {
      title: tasks[0].title,
      deadline: tasks[0].deadline,
      time: tasks[0].time,
      status: tasks[0].status,
      category: tasks[0].category,
      urgency: tasks[0].urgency,
      needsReview: tasks[0].needsReview
    } : null,
    dialogToastText: dlgToast.textContent,
    dialogToastVisible: dlgToast.classList.contains('show'),
    dialogToastInFront: elAt ? (elAt.id === 'captureToast') : false,
    mainToastText: mainToast.textContent,
    fieldErrors: [...document.querySelectorAll('.field-error')].map(n => n.textContent),
    errorFields: [...document.querySelectorAll('.field.has-error')].map(n => n.id)
  };
})()
"""


async def main():
    srv = subprocess.Popen(["python3", "-m", "http.server", "4173", "--directory", ROOT],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    chrome = subprocess.Popen([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
        "--user-data-dir=/tmp/zhouxu_qa/profile_manual", "--remote-debugging-port=9360",
        "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                http_json("http://127.0.0.1:9360/json/version")
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("chrome 未就绪")
        page = [t for t in http_json("http://127.0.0.1:9360/json/list") if t["type"] == "page"][0]
        ws = await connect(page["webSocketDebuggerUrl"])
        cdp = CDP(ws)
        await cdp.call("Page.enable")
        await cdp.call("Runtime.enable")
        await cdp.call("Log.enable")

        async def ev(expr):
            r = await cdp.call("Runtime.evaluate", expression=expr,
                                returnByValue=True, awaitPromise=True)
            if r.get("exceptionDetails"):
                return {"__error": json.dumps(r["exceptionDetails"].get("exception", {}), ensure_ascii=False)[:400]}
            return r["result"].get("value")

        await cdp.call("Page.navigate", url=BASE)
        await asyncio.sleep(2.2)
        await ev("localStorage.clear(); location.reload()")
        await asyncio.sleep(2.2)

        await run_checks(ev)

        errors = []
        for e in cdp.events:
            m = e.get("method")
            if m == "Runtime.exceptionThrown":
                errors.append("exception")
            if m == "Log.entryAdded" and e["params"]["entry"].get("level") == "error":
                errors.append("log: " + str(e["params"]["entry"].get("text")))
        with open(os.path.join(OUT, "manual_report.json"), "w", encoding="utf-8") as f:
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


async def run_checks(ev):
    # 1. 打开手动录入
    r = await ev(OPEN_MANUAL)
    check("m1 手动录入面板能打开", r["panelVisible"], True)
    check("m2 默认日期状态是明确日期", r["dateState"], "explicit")
    check("m3 面板有日期状态说明", "截止日期" in r["hint"], True)

    # 2. 只填标题，不填下一步
    before = await ev("JSON.parse(localStorage.getItem('zhouxu-mvp-v2')||'[]').length")
    await ev(FILL % ("只填标题事项", "", "", ""))
    r = await ev(CLICK_SAVE)
    if "__error" in r:
        print("EVAL ERROR:", r["__error"])
        return
    check("m4 缺下一步时提示可见", r["dialogToastVisible"], True)
    check("m5 提示条没有被弹窗挡住", r["dialogToastInFront"], True)
    check("m6 提示内容指明缺什么",
          ("要做什么" in r["dialogToastText"]) or ("下一步" in r["dialogToastText"]), True)
    check("m7 出错字段被标红", r["errorFields"], ["manualActionField"])
    check("m8 没有偷偷新增记录", r["taskCount"], before)

    # 3. 标题与下一步都填了，但没填日期
    await ev(FILL % ("数据课程作业", "提交实验报告", "", ""))
    r = await ev(CLICK_SAVE)
    check("m9 缺日期时提示可见", r["dialogToastVisible"], True)
    check("m10 提示内容指明缺日期", "截止日期" in r["dialogToastText"], True)
    check("m11 日期字段被标红", r["errorFields"], ["manualDeadlineField"])
    check("m12 仍然没有新增记录", r["taskCount"], before)

    # 4. 补上日期
    await ev(FILL % ("数据课程作业", "提交实验报告", "2026-11-28", "2026-11-28"))
    r = await ev(CLICK_SAVE)
    check("m13 补齐后能提交", r["newest"]["title"], "数据课程作业")
    check("m14 日期写入正确", r["newest"]["deadline"], "2026-11-28")
    check("m15 进入待确认状态", r["newest"]["needsReview"], True)
    check("m16 弹窗已关闭", r["dlgOpen"], False)
    check("m17 记录数增加", r["taskCount"], before + 1)

    # 5. 收件箱里能看到
    r = await ev("""(() => {
      document.querySelector('[data-view="inbox"]').click();
      return {
        text: document.querySelector('#inboxList').innerText.replace(/\\s+/g,' '),
        reviewTitle: document.querySelector('#reviewTitle').value
      };
    })()""")
    check("m18 收件箱里能看到", "数据课程作业" in r["text"], True)
    check("m19 确认页选中这条", r["reviewTitle"], "数据课程作业")

    # 6. 进度与紧急程度能带过来
    r = await ev("""(() => {
      document.querySelector('#openCapture').click();
      document.querySelector('[data-capture-mode="manual"]').click();
      document.querySelector('#manualTitle').value = '产品规格作业';
      document.querySelector('#manualAction').value = '写完文档';
      document.querySelector('#manualDeadline').value = '2026-11-29';
      document.querySelector('#manualCategory').value = 'school';
      document.querySelector('#manualStatus').value = 'coursework';
      document.querySelector('#manualUrgency').value = 'high';
      document.querySelector('#saveCapture').click();
      const tasks = JSON.parse(localStorage.getItem('zhouxu-mvp-v2')||'[]');
      return tasks[0];
    })()""")
    check("m20 分类写入正确", r["category"], "school")
    check("m21 进度写入正确", r["status"], "coursework")
    check("m22 紧急程度写入正确", r["urgency"], "high")

    # 7. 改成"未找到日期"，日期框应禁用且能保存
    r = await ev("""(() => {
      document.querySelector('#openCapture').click();
      document.querySelector('[data-capture-mode="manual"]').click();
      document.querySelector('#manualDateState').value = 'missing';
      document.querySelector('#manualDateState').dispatchEvent(new Event('change', {bubbles:true}));
      const disabled = document.querySelector('#manualDeadline').disabled;
      document.querySelector('#manualTitle').value = '还没有截止日期的宣讲会';
      document.querySelector('#manualAction').value = '回原渠道确认';
      document.querySelector('#saveCapture').click();
      const tasks = JSON.parse(localStorage.getItem('zhouxu-mvp-v2')||'[]');
      return {disabled, newest: tasks[0]};
    })()""")
    check("m23 未找到日期时禁用日期框", r["disabled"], True)
    check("m24 无日期也能保存", r["newest"]["dateState"], "missing")
    check("m25 无日期时截止日期为空", r["newest"]["deadline"], "")

    # 8. 手动录入重复项应被拦下
    before = await ev("JSON.parse(localStorage.getItem('zhouxu-mvp-v2')||'[]').length")
    r = await ev("""(() => {
      document.querySelector('#openCapture').click();
      document.querySelector('[data-capture-mode="manual"]').click();
      document.querySelector('#manualTitle').value = '数据课程作业';
      document.querySelector('#manualAction').value = '再写一次';
      document.querySelector('#manualDeadline').value = '2026-11-28';
      document.querySelector('#saveCapture').click();
      const tasks = JSON.parse(localStorage.getItem('zhouxu-mvp-v2')||'[]');
      return {count: tasks.length, toast: document.querySelector('#toast').textContent};
    })()""")
    check("m26 手动重复被拦下", r["count"], before)
    check("m27 提示是重复", "已经有一条" in r["toast"], True)

    # 9. 同一弹窗里，图片与文本方式的报错也必须看得见
    r = await ev("""(() => {
      document.querySelector('#openCapture').click();
      document.querySelector('[data-capture-mode="image"]').click();
      document.querySelector('#saveCapture').click();
      const t = document.querySelector('#captureToast');
      const rect = t.getBoundingClientRect();
      const at = rect.height > 0
        ? document.elementFromPoint(rect.left + rect.width/2, rect.top + rect.height/2)
        : null;
      return {
        visible: t.classList.contains('show'),
        text: t.textContent,
        inFront: at ? (at.id === 'captureToast') : false,
        dlgOpen: document.querySelector('#captureDialog').open
      };
    })()""")
    check("m28 图片方式报错看得见", r["visible"], True)
    check("m29 图片方式提示没被挡住", r["inFront"], True)
    check("m30 图片方式提示内容正确", "截图" in r["text"], True)
    check("m31 图片方式不误关弹窗", r["dlgOpen"], True)

    r = await ev("""(() => {
      document.querySelector('[data-capture-mode="text"]').click();
      document.querySelector('#saveCapture').click();
      const t = document.querySelector('#captureToast');
      const rect = t.getBoundingClientRect();
      const at = rect.height > 0
        ? document.elementFromPoint(rect.left + rect.width/2, rect.top + rect.height/2)
        : null;
      return {
        visible: t.classList.contains('show'),
        text: t.textContent,
        inFront: at ? (at.id === 'captureToast') : false
      };
    })()""")
    check("m32 文本方式报错看得见", r["visible"], True)
    check("m33 文本方式提示没被挡住", r["inFront"], True)
    check("m34 文本方式提示内容正确", "原文" in r["text"], True)


asyncio.run(main())
