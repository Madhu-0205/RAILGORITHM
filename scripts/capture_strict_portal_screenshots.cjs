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
    args: ['--no-sandbox', '--disable-gpu', '--user-data-dir=/tmp/chrome-strict-portals-profile'],
  });

  try {
    const page = await browser.newPage();

    // 0. Portal Gateway Hub
    console.log('Capturing Portal Gateway Hub...');
    await page.setViewport({ width: 1440, height: 900 });
    await page.goto('http://127.0.0.1:8080/login', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.evaluate(() => localStorage.clear());
    await page.goto('http://127.0.0.1:8080/login', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise((r) => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(screenshotDir, 'portal-gateway-1440px.png'), fullPage: false });

    // 1. Station Master Login (1440px)
    console.log('Capturing Station Master Login at 1440px...');
    await page.setViewport({ width: 1440, height: 900 });
    await page.goto('http://127.0.0.1:8080/login/station-master', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.evaluate(() => localStorage.clear());
    await new Promise((r) => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(screenshotDir, 'sm-login-1440px.png'), fullPage: false });

    // 2. Station Master Login (1920px)
    console.log('Capturing Station Master Login at 1920px...');
    await page.setViewport({ width: 1920, height: 1080 });
    await new Promise((r) => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(screenshotDir, 'sm-login-1920px.png'), fullPage: false });

    // 3. Station Master Dashboard (1440px)
    console.log('Logging into Station Master Dashboard as SM_NDL_001...');
    await page.setViewport({ width: 1440, height: 900 });
    await page.type('#sm-username', 'SM_NDL_001');
    await page.type('#sm-password', 'Station@123');
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(() => {});
    await new Promise((r) => setTimeout(r, 3000));
    console.log('Current URL:', page.url());
    await page.screenshot({ path: path.join(screenshotDir, 'sm-dashboard-1440px.png'), fullPage: false });

    // 4. Station Master Dashboard (1920px)
    console.log('Capturing Station Master Dashboard at 1920px...');
    await page.setViewport({ width: 1920, height: 1080 });
    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(screenshotDir, 'sm-dashboard-1920px.png'), fullPage: false });

    // 5. Section Controller Login (1440px)
    console.log('Capturing Section Controller Login at 1440px...');
    await page.setViewport({ width: 1440, height: 900 });
    await page.goto('http://127.0.0.1:8080/login/section-controller', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.evaluate(() => localStorage.clear());
    await page.goto('http://127.0.0.1:8080/login/section-controller', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise((r) => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(screenshotDir, 'sc-login-1440px.png'), fullPage: false });

    // 6. Section Controller Login (1920px)
    console.log('Capturing Section Controller Login at 1920px...');
    await page.setViewport({ width: 1920, height: 1080 });
    await new Promise((r) => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(screenshotDir, 'sc-login-1920px.png'), fullPage: false });

    // 7. Section Controller Dashboard (1440px)
    console.log('Logging into Section Controller Dashboard as SC_CORRIDOR_001...');
    await page.setViewport({ width: 1440, height: 900 });
    await page.type('#sc-username', 'SC_CORRIDOR_001');
    await page.type('#sc-password', 'Section@123');
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(() => {});
    await new Promise((r) => setTimeout(r, 3000));
    console.log('Current URL:', page.url());
    await page.screenshot({ path: path.join(screenshotDir, 'sc-dashboard-1440px.png'), fullPage: false });

    // 8. Section Controller Dashboard (1920px)
    console.log('Capturing Section Controller Dashboard at 1920px...');
    await page.setViewport({ width: 1920, height: 1080 });
    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(screenshotDir, 'sc-dashboard-1920px.png'), fullPage: false });

    // 9. Cross-Login Rejection: Section Controller trying Station Master Portal
    console.log('Testing cross-login rejection: SC on SM Portal...');
    await page.setViewport({ width: 1440, height: 900 });
    await page.goto('http://127.0.0.1:8080/login/station-master', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.evaluate(() => localStorage.clear());
    await page.goto('http://127.0.0.1:8080/login/station-master', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.type('#sm-username', 'SC_CORRIDOR_001');
    await page.type('#sm-password', 'Section@123');
    await page.click('button[type="submit"]');
    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(screenshotDir, 'cross-rejection-sc-on-sm-portal.png'), fullPage: false });

    // 10. Cross-Login Rejection: Station Master trying Section Controller Portal
    console.log('Testing cross-login rejection: SM on SC Portal...');
    await page.goto('http://127.0.0.1:8080/login/section-controller', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.evaluate(() => localStorage.clear());
    await page.goto('http://127.0.0.1:8080/login/section-controller', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.type('#sc-username', 'SM_NDL_001');
    await page.type('#sc-password', 'Station@123');
    await page.click('button[type="submit"]');
    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(screenshotDir, 'cross-rejection-sm-on-sc-portal.png'), fullPage: false });

    console.log('All strict portal screenshots captured successfully!');
  } catch (err) {
    console.error('Error during screenshot capture:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

run();
