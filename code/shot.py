import asyncio, http.server, threading, functools
from playwright.async_api import async_playwright
h=functools.partial(http.server.SimpleHTTPRequestHandler,directory='site')
s=http.server.ThreadingHTTPServer(('127.0.0.1',8765),h); threading.Thread(target=s.serve_forever,daemon=True).start()
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1280,'height':900}); errs=[]
        pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None); pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.goto('http://127.0.0.1:8765/index.html'); await pg.wait_for_timeout(2500)
        await pg.click('#tab-p'); await pg.wait_for_timeout(1500); await pg.click('#years button:nth-child(5)'); await pg.wait_for_timeout(600)
        await pg.screenshot(path='shot_desktop.png')
        m=await b.new_page(viewport={'width':390,'height':844}); await m.goto('http://127.0.0.1:8765/index.html'); await m.wait_for_timeout(2500)
        await m.screenshot(path='shot_mobile.png',full_page=True); print(errs); await b.close()
asyncio.run(main())
