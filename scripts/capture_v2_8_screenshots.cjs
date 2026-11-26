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
    args: ['--no-sandbox', '--disable-gpu', '--user-data-dir=/tmp/chrome-v28-profile'],
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
    await new Promise((r) => setTimeout(r, 1500));

    // 1. Recommendations queue /recommendations at 1440px
    console.log('Capturing v2_8-recommendations-queue-1440px.png...');
    await page.goto('http://127.0.0.1:8080/recommendations', { waitUntil: 'networkidle0', timeout: 15000 });
    await page.setViewport({ width: 1440, height: 900 });
    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_8-recommendations-queue-1440px.png'), fullPage: false });

    // 2. Recommendations queue at 1920px
    console.log('Capturing v2_8-recommendations-queue-1920px.png...');
    await page.setViewport({ width: 1920, height: 1080 });
    await new Promise((r) => setTimeout(r, 1000));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_8-recommendations-queue-1920px.png'), fullPage: false });

    // Check if there is a review button to navigate to detail, or generate one
    const reviewBtn = await page.$('a.button.button-small');
    if (reviewBtn) {
      console.log('Navigating to recommendation detail...');
      await reviewBtn.click();
      await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(() => {});
      await new Promise((r) => setTimeout(r, 2000));
    } else {
      const genBtn = await page.$('button.button.button-primary');
      if (genBtn) {
        console.log('Generating recommendation...');
        await genBtn.click();
        await new Promise((r) => setTimeout(r, 4000));
      }
    }

    // 3. Recommendation detail at 1440px
    console.log('Capturing v2_8-predictive-regulation-detail-1440px.png...');
    await page.setViewport({ width: 1440, height: 1200 });
    await new Promise((r) => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_8-predictive-regulation-detail-1440px.png'), fullPage: false });

    // 4. Recommendation detail at 1920px
    console.log('Capturing v2_8-predictive-regulation-detail-1920px.png...');
    await page.setViewport({ width: 1920, height: 1200 });
    await new Promise((r) => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(screenshotDir, 'v2_8-predictive-regulation-detail-1920px.png'), fullPage: false });

    console.log('Successfully captured all v2.8 visual verification screenshots!');
  } catch (err) {
    console.error('Error capturing screenshots:', err);
  } finally {
    await browser.close();
  }
}

run();
