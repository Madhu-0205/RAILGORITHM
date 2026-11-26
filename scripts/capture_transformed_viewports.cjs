const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

const VIEWPORTS = [
  { name: '1920px', width: 1920, height: 1080 },
  { name: '1440px', width: 1440, height: 900 },
  { name: '1280px', width: 1280, height: 800 },
  { name: 'tablet-1024px', width: 1024, height: 768 },
];

const REC_ID = 'a18cef4c-e807-4936-a3c1-c676aec04f0b';

async function capture() {
  const transformedDir = path.resolve(__dirname, '../docs/screenshots/transformed');
  if (!fs.existsSync(transformedDir)) {
    fs.mkdirSync(transformedDir, { recursive: true });
  }

  const browser = await puppeteer.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--user-data-dir=/tmp/chrome-transformed-profile'],
  });

  try {
    const page = await browser.newPage();

    // 1. Portals across all viewports
    for (const vp of VIEWPORTS) {
      await page.setViewport({ width: vp.width, height: vp.height });

      // Gateway
      await page.goto('http://127.0.0.1:8080/login', { waitUntil: 'networkidle0', timeout: 15000 });
      await page.evaluate(() => localStorage.clear());
      await page.goto('http://127.0.0.1:8080/login', { waitUntil: 'networkidle0', timeout: 15000 });
      await page.screenshot({ path: path.join(transformedDir, `transformed-gateway-${vp.name}.png`), fullPage: false });

      // Station Master Login
      await page.goto('http://127.0.0.1:8080/login/station-master', { waitUntil: 'networkidle0', timeout: 15000 });
      await page.screenshot({ path: path.join(transformedDir, `transformed-sm-login-${vp.name}.png`), fullPage: false });

      // Section Controller Login
      await page.goto('http://127.0.0.1:8080/login/section-controller', { waitUntil: 'networkidle0', timeout: 15000 });
      await page.screenshot({ path: path.join(transformedDir, `transformed-sc-login-${vp.name}.png`), fullPage: false });
    }

    // 2. Station Master Screens (SM_NDL_001)
    await page.setViewport({ width: 1440, height: 900 });
    await page.goto('http://127.0.0.1:8080/login/station-master', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.evaluate(() => localStorage.clear());
    await page.goto('http://127.0.0.1:8080/login/station-master', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.type('#sm-username', 'SM_NDL_001');
    await page.type('#sm-password', 'Station@123');
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(() => {});
    await new Promise((r) => setTimeout(r, 2000));

    for (const vp of VIEWPORTS) {
      await page.setViewport({ width: vp.width, height: vp.height });

      // Yard Workspace
      await page.goto('http://127.0.0.1:8080/station-master/dashboard', { waitUntil: 'networkidle0', timeout: 15000 });
      await new Promise((r) => setTimeout(r, 1200));
      await page.screenshot({ path: path.join(transformedDir, `transformed-sm-yard-${vp.name}.png`), fullPage: false });

      // Train Movement Board
      await page.goto('http://127.0.0.1:8080/station-master/trains', { waitUntil: 'networkidle0', timeout: 15000 });
      await new Promise((r) => setTimeout(r, 1200));
      await page.screenshot({ path: path.join(transformedDir, `transformed-sm-trains-${vp.name}.png`), fullPage: false });

      // Platform & Line Berth
      await page.goto('http://127.0.0.1:8080/station-master/platforms', { waitUntil: 'networkidle0', timeout: 15000 });
      await new Promise((r) => setTimeout(r, 1200));
      await page.screenshot({ path: path.join(transformedDir, `transformed-sm-platforms-${vp.name}.png`), fullPage: false });
    }

    // 3. Section Controller Screens (SC_CORRIDOR_001)
    await page.setViewport({ width: 1440, height: 900 });
    await page.goto('http://127.0.0.1:8080/login/section-controller', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.evaluate(() => localStorage.clear());
    await page.goto('http://127.0.0.1:8080/login/section-controller', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.type('#sc-username', 'SC_CORRIDOR_001');
    await page.type('#sc-password', 'Section@123');
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(() => {});
    await new Promise((r) => setTimeout(r, 2000));

    for (const vp of VIEWPORTS) {
      await page.setViewport({ width: vp.width, height: vp.height });

      // Territory Overview
      await page.goto('http://127.0.0.1:8080/section-controller/dashboard', { waitUntil: 'networkidle0', timeout: 15000 });
      await new Promise((r) => setTimeout(r, 1200));
      await page.screenshot({ path: path.join(transformedDir, `transformed-sc-dashboard-${vp.name}.png`), fullPage: false });

      // Master Control Graph
      await page.goto('http://127.0.0.1:8080/section-controller/graph', { waitUntil: 'networkidle0', timeout: 15000 });
      await new Promise((r) => setTimeout(r, 1500));
      await page.screenshot({ path: path.join(transformedDir, `transformed-sc-mcg-${vp.name}.png`), fullPage: false });

      // Block Section Board
      await page.goto('http://127.0.0.1:8080/section-controller/blocks', { waitUntil: 'networkidle0', timeout: 15000 });
      await new Promise((r) => setTimeout(r, 1200));
      await page.screenshot({ path: path.join(transformedDir, `transformed-sc-blocks-${vp.name}.png`), fullPage: false });

      // Crossings & Precedence
      await page.goto('http://127.0.0.1:8080/section-controller/crossings', { waitUntil: 'networkidle0', timeout: 15000 });
      await new Promise((r) => setTimeout(r, 1200));
      await page.screenshot({ path: path.join(transformedDir, `transformed-sc-crossings-${vp.name}.png`), fullPage: false });

      // Recommendation Detail Review
      await page.goto(`http://127.0.0.1:8080/section-controller/recommendations/${REC_ID}`, { waitUntil: 'networkidle0', timeout: 15000 });
      await new Promise((r) => setTimeout(r, 1500));
      await page.screenshot({ path: path.join(transformedDir, `transformed-sc-recommendation-${vp.name}.png`), fullPage: false });
    }

    console.log('TRANSFORMED SCREENSHOTS CAPTURED SUCCESSFULLY!');
  } finally {
    await browser.close();
  }
}

capture().catch((err) => {
  console.error('CAPTURE FAILED:', err);
  process.exit(1);
});
