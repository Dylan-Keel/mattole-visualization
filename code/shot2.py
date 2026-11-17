import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1280,'height':900}); errs=[]
        pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None); pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.goto('file:///home/claude/work/Cooskie_Ridge_Aerial_Flipbook.html'); await pg.wait_for_timeout(4000)
        await pg.click('#tab-d'); await pg.wait_for_timeout(1500); await pg.click('#years button:nth-child(1)'); await pg.wait_for_timeout(500)
        async with pg.expect_download() as dl: await pg.click('#save')
        d=await dl.value; await d.save_as('still_test.jpg'); print('download',d.suggested_filename, await pg.inner_text('#msg'))
        await pg.screenshot(path='shot_export.png'); print(errs); await b.close()
asyncio.run(main())
