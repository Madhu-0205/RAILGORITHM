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
    args: ['--no-sandbox', '--disable-gpu', '--user-data-dir=/tmp/chrome-v281-profile'],
  });

  try {
    const page = await browser.newPage();

    // 1. Login Page at 1440px
    console.log('1. Capturing v2_8_1-login-1440px.png...');
    await page.setViewport({ width: 1440, height: 950 });
    await page.goto('http://127.0.0.1:8080/', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.evaluate(() => localStorage.clear());
    await page.goto('http://127.0.0.1:8080/login', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.waitForSelector('form input[name="username"]', { timeout: 10000 });
    await new Promise((r) => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_8_1-login-1440px.png'), fullPage: false });

    // 2. Station Master Nandpur (SM_NDL_001)
    console.log('2. Logging in as SM_NDL_001 and capturing v2_8_1-sm-ndl-1440px.png...');
    await page.evaluate(() => localStorage.clear());
    await page.goto('http://127.0.0.1:8080/login', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.type('input[name="username"]', 'SM_NDL_001');
    await page.type('input[name="password"]', 'Station@123');
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(() => {});
    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_8_1-sm-ndl-1440px.png'), fullPage: false });

    // 3. Section Controller Corridor (SC_CORRIDOR_001)
    console.log('3. Logging in as SC_CORRIDOR_001 and capturing v2_8_1-sc-corridor-1440px.png...');
    await page.evaluate(() => localStorage.clear());
    await page.goto('http://127.0.0.1:8080/login', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.type('input[name="username"]', 'SC_CORRIDOR_001');
    await page.type('input[name="password"]', 'Section@123');
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(() => {});
    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_8_1-sc-corridor-1440px.png'), fullPage: false });

    // 4. Master Control Graph Default View at 1440px
    console.log('4. Navigating to Master Control Graph (/graph) and capturing v2_8_1-mcg-default-1440px.png...');
    await page.goto('http://127.0.0.1:8080/graph', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.waitForSelector('.graph-toolbar', { timeout: 10000 }).catch(() => {});
    await new Promise((r) => setTimeout(r, 2500));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_8_1-mcg-default-1440px.png'), fullPage: false });

    // 5. Master Control Graph with Overlays Expanded
    console.log('5. Expanding Overlays panel and capturing v2_8_1-mcg-overlays-1440px.png...');
    const overlaysBtn = await page.$('button[title*="Toggle operational overlays"]');
    if (overlaysBtn) {
      await overlaysBtn.click();
      await new Promise((r) => setTimeout(r, 1000));
    }
    await page.screenshot({ path: path.join(screenshotDir, 'v2_8_1-mcg-overlays-1440px.png'), fullPage: false });

    // 6. Master Control Graph Filtered to UP Movements
    console.log('6. Filtering to UP movements and capturing v2_8_1-mcg-up-1440px.png...');
    await page.evaluate(() => {
      const btns = Array.from(document.querySelectorAll('button'));
      const up = btns.find((b) => b.innerText.includes('UP (NDL'));
      if (up) up.click();
    });
    await new Promise((r) => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_8_1-mcg-up-1440px.png'), fullPage: false });

    // 7. Master Control Graph Station Filter
    console.log('7. Selecting Station MLG and capturing v2_8_1-mcg-station-filter-1440px.png...');
    const stationSelect = await page.$('select[aria-label="Filter by station corridor highlight"]');
    if (stationSelect) {
      await page.select('select[aria-label="Filter by station corridor highlight"]', 'MLG');
      await new Promise((r) => setTimeout(r, 1000));
    }
    await page.screenshot({ path: path.join(screenshotDir, 'v2_8_1-mcg-station-filter-1440px.png'), fullPage: false });

    // 8. Master Control Graph at 1920px
    console.log('8. Capturing v2_8_1-mcg-1920px.png at 1920x1080...');
    await page.setViewport({ width: 1920, height: 1080 });
    await new Promise((r) => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_8_1-mcg-1920px.png'), fullPage: false });

    console.log('All v2.8.1 visual verification screenshots captured successfully!');
  } catch (err) {
    console.error('Error during screenshot capture:', err);
  } finally {
    await browser.close();
  }
}

run();
