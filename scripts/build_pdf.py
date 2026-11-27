#!/usr/bin/env python3
"""生成 PDF Case Pack。

用无头 Chrome 把 A4 打印样式的 HTML 渲染成 PDF，再用 Poppler 渲染成 PNG 供人工核对。
中文字形由系统字体直接绘制，不做子集化，避免缺字。
"""

import asyncio, base64, os, subprocess, sys, time

sys.path.insert(0, "/tmp/zhouxu_qa")
from cdp import CDP, connect, http_json

ROOT = "/Users/macbookpro/Documents/Codex/2026-11-11/ru-gu"
HTML = ROOT + "/mvp/case/print/case-pack.html"
PDF = ROOT + "/mvp/case/print/zhouxu_case_pack.pdf"
OUT = ROOT + "/work/pdf"
PORT = 4175

os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.dirname(PDF), exist_ok=True)


async def main():
    srv = subprocess.Popen(["python3", "-m", "http.server", str(PORT), "--directory", ROOT],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    chrome = subprocess.Popen([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars",
        "--user-data-dir=/tmp/zhouxu_qa/pdf_profile", "--remote-debugging-port=9337",
        "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                http_json("http://127.0.0.1:9337/json/version")
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("chrome 未就绪")

        targets = http_json("http://127.0.0.1:9337/json/list")
        page = [t for t in targets if t["type"] == "page"][0]
        ws = await connect(page["webSocketDebuggerUrl"])
        cdp = CDP(ws)
        await cdp.call("Page.enable")
        await cdp.call("Runtime.enable")

        url = f"http://127.0.0.1:{PORT}/mvp/case/print/case-pack.html"
        await cdp.call("Page.navigate", url=url)
        await asyncio.sleep(2.5)

        # 页面自检：每页高度是否超出 A4
        probe = """
        (() => {
          const pages = [...document.querySelectorAll('.page')];
          const limit = 297 * 96 / 25.4;
          return {
            count: pages.length,
            overflow: pages.map((p, i) => ({
              i: i + 1,
              h: Math.round(p.scrollHeight),
              over: Math.round(p.scrollHeight - limit)
            })).filter(x => x.over > 1),
            imgs: [...document.images].map(i => ({src: i.getAttribute('src'), ok: i.complete && i.naturalWidth > 0}))
          };
        })()
        """
        res = await cdp.call("Runtime.evaluate", expression=probe, returnByValue=True)
        val = res["result"]["value"]
        print("页数:", val["count"])
        print("超出 A4 的页:", val["overflow"] if val["overflow"] else "无")
        broken = [i["src"] for i in val["imgs"] if not i["ok"]]
        print("未加载图片:", broken if broken else "无")

        result = await cdp.call("Page.printToPDF", printBackground=True,
                                preferCSSPageSize=True, marginTop=0, marginBottom=0,
                                marginLeft=0, marginRight=0)
        with open(PDF, "wb") as f:
            f.write(base64.b64decode(result["data"]))
        print("已生成:", PDF, os.path.getsize(PDF) // 1024, "KB")

        for f in os.listdir(OUT):
            if f.endswith(".png"):
                os.remove(os.path.join(OUT, f))
        subprocess.run(["pdftoppm", "-png", "-r", "90", PDF, os.path.join(OUT, "page")],
                       check=True)
        pages = sorted(f for f in os.listdir(OUT) if f.endswith(".png"))
        print("已渲染", len(pages), "页 PNG 到 work/pdf/")
    finally:
        chrome.terminate()
        srv.terminate()


asyncio.run(main())
