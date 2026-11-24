import asyncio, base64, json, os, subprocess, sys, time
sys.path.insert(0, "/tmp/zhouxu_qa")
from cdp import CDP, connect, http_json

BASE = "http://127.0.0.1:4173/?v=20261124-2"
OUT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu/work/qa"
os.makedirs(OUT, exist_ok=True)

PROBE = """
(() => {
  const de = document.documentElement;
  const vw = de.clientWidth;
  const over = [];
  document.querySelectorAll('*').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && (r.right > vw + 1 || r.left < -1)) {
      over.push({
        tag: el.tagName.toLowerCase(),
        cls: (el.className && el.className.toString().slice(0,60)) || '',
        id: el.id || '',
        left: Math.round(r.left), right: Math.round(r.right), w: Math.round(r.width)
      });
    }
  });
  return {
    scrollWidth: de.scrollWidth,
    clientWidth: vw,
    hasHorizontalScroll: de.scrollWidth > vw + 1,
    title: document.title,
    views: [...document.querySelectorAll('[data-view]')].map(v=>v.dataset.view),
    sampleButtons: [...document.querySelectorAll('[data-sample]')].map(b=>b.dataset.sample),
    overflowing: over.slice(0, 12),
    overflowCount: over.length,
    bodyTextLen: document.body.innerText.length
  };
})()
"""

async def main():
    chrome = subprocess.Popen([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
        "--user-data-dir=/tmp/zhouxu_qa/profile", "--remote-debugging-port=9333",
        "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                http_json("http://127.0.0.1:9333/json/version"); break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("chrome 未就绪")
        targets = http_json("http://127.0.0.1:9333/json/list")
        page = [t for t in targets if t["type"] == "page"][0]
        ws = await connect(page["webSocketDebuggerUrl"])
        cdp = CDP(ws)
        await cdp.call("Page.enable"); await cdp.call("Runtime.enable"); await cdp.call("Log.enable")

        report = []
        for label, w, h, mobile in [
            ("desktop_1440", 1440, 900, False),
            ("laptop_1180", 1180, 800, False),
            ("tablet_900", 900, 1200, False),
            ("tablet_768", 768, 1024, True),
            ("phone_390", 390, 844, True),
            ("phone_360", 360, 800, True),
        ]:
            await cdp.call("Emulation.setDeviceMetricsOverride", width=w, height=h,
                          deviceScaleFactor=1, mobile=mobile)
            await cdp.call("Page.navigate", url=BASE)
            await asyncio.sleep(2.2)
            res = await cdp.call("Runtime.evaluate", expression=PROBE, returnByValue=True)
            val = res["result"]["value"]
            shot = await cdp.call("Page.captureScreenshot", format="png",
                                  captureBeyondViewport=False)
            path = os.path.join(OUT, f"{label}.png")
            with open(path, "wb") as f:
                f.write(base64.b64decode(shot["data"]))
            val["shot"] = os.path.basename(path)
            report.append(val)
            print(label, "scrollW", val["scrollWidth"], "clientW", val["clientWidth"],
                  "hscroll", val["hasHorizontalScroll"], "overflowEls", val["overflowCount"],
                  "samples", val["sampleButtons"])

        errors = []
        for e in cdp.events:
            m = e.get("method")
            if m == "Runtime.exceptionThrown":
                errors.append("exception: " + json.dumps(e["params"], ensure_ascii=False)[:400])
            if m == "Log.entryAdded":
                en = e["params"]["entry"]
                if en.get("level") in ("error",):
                    errors.append(f"{en.get('source')}: {en.get('text')} {en.get('url','')}")
            if m == "Runtime.consoleAPICalled" and e["params"].get("type") == "error":
                errors.append("console: " + json.dumps(e["params"]["args"], ensure_ascii=False)[:400])

        with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
            json.dump({"viewports": report, "errors": errors}, f, ensure_ascii=False, indent=2)
        print("\n=== 控制台错误 ===")
        print("\n".join(errors) if errors else "无")
    finally:
        chrome.terminate()

asyncio.run(main())
