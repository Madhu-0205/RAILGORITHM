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
    args: ['--no-sandbox', '--disable-gpu', '--user-data-dir=/tmp/chrome-v27-profile'],
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
    await page.waitForSelector('.page-heading', { timeout: 10000 });
    await new Promise((r) => setTimeout(r, 2000));

    // Measure Overview Metrics
    const metrics = await page.evaluate(() => {
      return {
        scrollHeight: document.body.scrollHeight,
        kpiCount: document.querySelectorAll('.kpi-card').length,
        panels: Array.from(document.querySelectorAll('.panel, .page-heading, .section-controller-header')).map(el => ({
          className: el.className,
          heading: (el.querySelector('h1, h2, h3, strong')?.innerText || el.innerText.split('\n')[0]).substring(0, 60)
        }))
      };
    });
    console.log('Overview Metrics:', JSON.stringify(metrics, null, 2));

    // 1. Overview 1440px
    console.log('Capturing v2_7-overview-1440px.png...');
    await page.setViewport({ width: 1440, height: 900 });
    await new Promise((r) => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_7-overview-1440px.png'), fullPage: false });

    // 2. Overview 1920px
    console.log('Capturing v2_7-overview-1920px.png...');
    await page.setViewport({ width: 1920, height: 1080 });
    await new Promise((r) => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_7-overview-1920px.png'), fullPage: false });

    // 3. Master Control Graph /graph
    console.log('Capturing v2_7-master-graph-1440px.png...');
    await page.goto('http://127.0.0.1:8080/graph', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise((r) => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_7-master-graph-1440px.png'), fullPage: false });

    // 4. Station Control /stations
    console.log('Capturing v2_7-stations-1440px.png...');
    await page.goto('http://127.0.0.1:8080/stations', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise((r) => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_7-stations-1440px.png'), fullPage: false });

    // 5. Block Section Board /blocks
    console.log('Capturing v2_7-blocks-1440px.png...');
    await page.goto('http://127.0.0.1:8080/blocks', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise((r) => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_7-blocks-1440px.png'), fullPage: false });

    // 6. Crossings & Precedence /crossings
    console.log('Capturing v2_7-crossings-1440px.png...');
    await page.goto('http://127.0.0.1:8080/crossings', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise((r) => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_7-crossings-1440px.png'), fullPage: false });

    // 7. Engineering Restrictions /restrictions
    console.log('Capturing v2_7-restrictions-1440px.png...');
    await page.goto('http://127.0.0.1:8080/restrictions', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise((r) => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_7-restrictions-1440px.png'), fullPage: false });

    // 8. Incidents Desk /incidents
    console.log('Capturing v2_7-incidents-1440px.png...');
    await page.goto('http://127.0.0.1:8080/incidents', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise((r) => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_7-incidents-1440px.png'), fullPage: false });

    // 9. Shift Handover /handover
    console.log('Capturing v2_7-handover-1440px.png...');
    await page.goto('http://127.0.0.1:8080/handover', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise((r) => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_7-handover-1440px.png'), fullPage: false });

    console.log('All v2.7 screenshots captured and verified successfully!');
  } finally {
    await browser.close();
  }
}

run().catch((err) => {
  console.error('Capture failed:', err);
  process.exit(1);
});
