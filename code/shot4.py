import asyncio, http.server, threading, functools
from playwright.async_api import async_playwright
h=functools.partial(http.server.SimpleHTTPRequestHandler,directory='site')
s=http.server.ThreadingHTTPServer(('127.0.0.1',8767),h); threading.Thread(target=s.serve_forever,daemon=True).start()
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1400,'height':950}); errs=[]
        pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.goto('http://127.0.0.1:8767/index.html'); await pg.wait_for_timeout(2000)
        await pg.click('#tab-d'); await pg.wait_for_timeout(2500); await pg.check('#ov-fire'); await pg.check('#ov-parcel'); await pg.click('#years button:nth-child(4)'); await pg.wait_for_timeout(700)
        await pg.screenshot(path='shot_3d.png'); print(errs); await b.close()
asyncio.run(main())
