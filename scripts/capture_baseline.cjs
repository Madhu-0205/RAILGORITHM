const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

async function run() {
  const screenshotDir = path.resolve(__dirname, '../docs/screenshots');
  if (!fs.existsSync(screenshotDir)) {
    fs.mkdirSync(screenshotDir, { recursive: true });
  }

  const browser = await puppeteer.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--user-data-dir=/tmp/chrome-baseline-profile'],
  });

  try {
    const page = await browser.newPage();
    
    console.log('Navigating to http://127.0.0.1:8080/ ...');
    await page.goto('http://127.0.0.1:8080/', { waitUntil: 'networkidle0', timeout: 15000 });

    const loginInput = await page.$('input[name="username"]');
    if (loginInput) {
      console.log('Logging in as section.master...');
      await page.type('input[name="username"]', 'section.master');
      await page.type('input[name="password"]', 'Section@123');
      await page.click('button[type="submit"]');
      await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 });
    }
    console.log('Navigated to:', page.url());

    // Wait for dashboard content to load
    await page.waitForSelector('.page-heading', { timeout: 10000 });
    // Let any async data settle
    await new Promise((r) => setTimeout(r, 2000));

    // 1440px Viewport
    console.log('Capturing 1440px viewport...');
    await page.setViewport({ width: 1440, height: 900 });
    await new Promise((r) => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(screenshotDir, 'baseline-1440px.png'), fullPage: false });

    // 1920px Viewport
    console.log('Capturing 1920px viewport...');
    await page.setViewport({ width: 1920, height: 1080 });
    await new Promise((r) => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(screenshotDir, 'baseline-1920px.png'), fullPage: false });

    console.log('Screenshots saved successfully!');
  } finally {
    await browser.close();
  }
}

run().catch((err) => {
  console.error('Capture failed:', err);
  process.exit(1);
});
