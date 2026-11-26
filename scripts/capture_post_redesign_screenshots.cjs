const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

async function run() {
  const screenshotDir = path.resolve(__dirname, '../docs/screenshots');
  if (!fs.existsSync(screenshotDir)) {
    fs.mkdirSync(screenshotDir, { recursive: true });
  }

  const browser = await puppeteer.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--user-data-dir=/tmp/chrome-post-redesign-profile'],
  });

  try {
    const page = await browser.newPage();

    // 1. Station Master at 1440px
    console.log('Capturing Station Master at 1440px (post-redesign-sm-1440px.png)...');
    await page.setViewport({ width: 1440, height: 900 });
    await page.goto('http://127.0.0.1:8080/login', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.evaluate(() => localStorage.clear());
    await page.goto('http://127.0.0.1:8080/login', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.type('input[name="username"]', 'SM_NDL_001');
    await page.type('input[name="password"]', 'Station@123');
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(() => {});
    await new Promise((r) => setTimeout(r, 3000));
    await page.screenshot({ path: path.join(screenshotDir, 'post-redesign-sm-1440px.png'), fullPage: false });

    // 2. Station Master at 1920px
    console.log('Capturing Station Master at 1920px (post-redesign-sm-1920px.png)...');
    await page.setViewport({ width: 1920, height: 1080 });
    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(screenshotDir, 'post-redesign-sm-1920px.png'), fullPage: false });

    // 3. Section Controller at 1440px
    console.log('Capturing Section Controller at 1440px (post-redesign-sc-1440px.png)...');
    await page.setViewport({ width: 1440, height: 900 });
    await page.evaluate(() => localStorage.clear());
    await page.goto('http://127.0.0.1:8080/login', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.type('input[name="username"]', 'SC_CORRIDOR_001');
    await page.type('input[name="password"]', 'Section@123');
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(() => {});
    await new Promise((r) => setTimeout(r, 3000));
    await page.screenshot({ path: path.join(screenshotDir, 'post-redesign-sc-1440px.png'), fullPage: false });

    // 4. Section Controller at 1920px
    console.log('Capturing Section Controller at 1920px (post-redesign-sc-1920px.png)...');
    await page.setViewport({ width: 1920, height: 1080 });
    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(screenshotDir, 'post-redesign-sc-1920px.png'), fullPage: false });

    console.log('Post-redesign screenshots captured successfully!');
  } catch (err) {
    console.error('Error capturing post-redesign screenshots:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

run();
