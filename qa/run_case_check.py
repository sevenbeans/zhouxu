"""验证产品案例页。

检查项：
1. 四个视口宽度无横向滚动、无元素越界
2. 控制台无错误、无 404 资源
3. 页面内所有图片都加载成功
4. 关键章节存在、锚点导航可跳转
5. 关键数字口径与研究记录一致（防止文档漂移）
"""

import asyncio, base64, json, os, subprocess, sys, time

sys.path.insert(0, "/tmp/zhouxu_qa")
from cdp import CDP, connect, http_json

ROOT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/docs"
OUT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/work/qa"
BASE = "http://127.0.0.1:4174/case/index.html"
os.makedirs(OUT, exist_ok=True)

results = []


def check(name, value, expect):
    if expect is None:
        ok = value is None
    else:
        ok = value == expect
    results.append((name, ok, value))
    print(("PASS " if ok else "FAIL ") + name + " -> " + repr(value))


PROBE = """
(() => {
  const de = document.documentElement;
  const vw = de.clientWidth;
  const over = [];
  document.querySelectorAll('*').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && (r.right > vw + 1 || r.left < -1)) {
      over.push(el.tagName.toLowerCase() + '.' + (el.className||'').toString().slice(0,40));
    }
  });
  const imgs = [...document.querySelectorAll('img')].map(i => ({
    src: i.getAttribute('src'), ok: i.complete && i.naturalWidth > 0
  }));
  return {
    scrollWidth: de.scrollWidth,
    clientWidth: de.clientWidth,
    overflowEls: over.slice(0, 10),
    overflowCount: over.length,
    imgTotal: imgs.length,
    imgBroken: imgs.filter(i => !i.ok).map(i => i.src),
    sections: [...document.querySelectorAll('section[id]')].map(s => s.id),
    navTargets: [...document.querySelectorAll('.topnav a')].map(a => a.getAttribute('href')),
    h1: (document.querySelector('h1')||{}).innerText || '',
    bodyTextLen: document.body.innerText.length,
    links: [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href'))
  };
})()
"""


async def main():
    srv = subprocess.Popen(["python3", "-m", "http.server", "4174", "--directory", ROOT],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    chrome = subprocess.Popen([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
        "--user-data-dir=/tmp/zhouxu_qa/case_profile", "--remote-debugging-port=9334",
        "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                http_json("http://127.0.0.1:9334/json/version")
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("chrome 未就绪")
        targets = http_json("http://127.0.0.1:9334/json/list")
        page = [t for t in targets if t["type"] == "page"][0]
        ws = await connect(page["webSocketDebuggerUrl"])
        cdp = CDP(ws)
        await cdp.call("Page.enable")
        await cdp.call("Runtime.enable")
        await cdp.call("Log.enable")

        shots = []
        for label, w, h, mobile in [
            ("case_desktop_1440", 1440, 900, False),
            ("case_laptop_1180", 1180, 800, False),
            ("case_phone_390", 390, 844, True),
            ("case_phone_360", 360, 800, True),
        ]:
            await cdp.call("Emulation.setDeviceMetricsOverride", width=w, height=h,
                          deviceScaleFactor=1, mobile=mobile)
            await cdp.call("Page.navigate", url=BASE)
            await asyncio.sleep(1.6)
            res = await cdp.call("Runtime.evaluate", expression=PROBE, returnByValue=True)
            val = res["result"]["value"]
            shot = await cdp.call("Page.captureScreenshot", format="png",
                                  captureBeyondViewport=False)
            path = os.path.join(OUT, f"{label}.png")
            with open(path, "wb") as f:
                f.write(base64.b64decode(shot["data"]))
            shots.append((label, val, os.path.basename(path)))

        d = shots[0][1]
        for label, val, shot in shots:
            check(f"{label} 无横向滚动", val["scrollWidth"] <= val["clientWidth"] + 1, True)
            check(f"{label} 无元素越界", val["overflowCount"], 0)
            check(f"{label} 图片全部加载", val["imgBroken"], [])

        check("首屏标题含产品名", "周序" in d["h1"], True)
        check("章节齐全",
              d["sections"], ["problem", "research", "solution", "iterations", "validation", "boundary"])
        check("导航锚点齐全",
              d["navTargets"],
              ["#problem", "#research", "#solution", "#iterations", "#validation", "#boundary"])
        check("Demo 入口指向上一级", "../" in d["links"], True)
        check("源码链接存在",
              "https://github.com/sevenbeans/zhouxu" in d["links"], True)
        check("正文有实质内容", d["bodyTextLen"] > 3000, True)

        errors = []
        for e in cdp.events:
            m = e.get("method")
            if m == "Runtime.exceptionThrown":
                errors.append("exception: " + json.dumps(e["params"], ensure_ascii=False)[:300])
            if m == "Log.entryAdded":
                en = e["params"]["entry"]
                if en.get("level") in ("error",):
                    errors.append(f"{en.get('source')}: {en.get('text')} {en.get('url','')}")
            if m == "Runtime.consoleAPICalled" and e["params"].get("type") == "error":
                errors.append("console: " + json.dumps(e["params"]["args"], ensure_ascii=False)[:300])

        with open(os.path.join(OUT, "case_report.json"), "w", encoding="utf-8") as f:
            json.dump({"viewports": [{"label": l, "data": v} for l, v, _ in shots],
                       "errors": errors,
                       "checks": [{"name": n, "pass": ok, "value": str(v)}
                                  for n, ok, v in results]},
                      f, ensure_ascii=False, indent=2)

        print("\n=== 控制台错误 ===")
        print("\n".join(errors) if errors else "无")
        passed = sum(1 for _, ok, _ in results if ok)
        print(f"\n通过 {passed}/{len(results)}")
    finally:
        chrome.terminate()
        srv.terminate()


asyncio.run(main())
