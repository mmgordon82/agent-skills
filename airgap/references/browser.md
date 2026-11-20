# Browser checks for air-gapped sites

Serve the site from the build you will ship (local server or container), not a dev server that
pulls from a CDN. `TARGET` is its URL.

## 1. Request audit: does the page contact anything outside? (chrome-devtools MCP)

1. `new_page` with `isolatedContext: "airgap"` and the site URL. Use a fresh context, so no cached
   asset hides a request.
2. Exercise the page: navigate the main routes, open menus, submit a form, wait for lazy loads.
3. `list_network_requests` with `includePreservedRequests: true`. Every request's host must be the
   site's own origin (or an approved internal host). Any other host (fonts, CDN, analytics, maps,
   telemetry) is a failure, even if it returned an error.
4. Optional: `emulate` with `networkConditions: "Offline"` after the load, then interact: see how
   the already-loaded page behaves when the network drops. `emulate` without it restores the network.

Playwright equivalent: collect `page.on("request")` URLs and fail on any foreign host:

```ts
const foreign: string[] = [];
page.on("request", r => { if (new URL(r.url()).origin !== new URL(TARGET).origin) foreign.push(r.url()); });
await page.goto(TARGET); /* exercise the page */
expect(foreign).toEqual([]);
```

## 2. Hard no-egress: the whole browser with no network (Docker)

Run the site and Playwright's Chromium in one container with `--network none`. The page must still
load completely: no failed requests, no missing fonts or images.

```bash
docker run --rm --network none -v "$PWD:/work" -w /work <internal-registry>/playwright:<version> \
  sh -c 'python3 -m http.server 8080 -d dist & sleep 1; npx --no-install playwright test airgap.spec.ts'
```

```ts
test("loads fully with no network", async ({ page }, info) => {
  const failed: string[] = [];
  page.on("requestfailed", r => failed.push(`${r.url()} ${r.failure()?.errorText}`));
  await page.goto("http://127.0.0.1:8080/");
  await page.waitForLoadState("networkidle");
  expect(failed).toEqual([]);
  await page.screenshot({ path: info.outputPath("offline-full.png"), fullPage: true });
});
```

Install Playwright and its browser into the image while online. This also covers channels browser
emulation can't (WebRTC, workers).

## 3. Offline behavior (Playwright)

| Goal | Approach |
|---|---|
| Chrome's native "No internet" page | `context.setOffline(true)`, then `page.goto` |
| Catalogue of native network-error pages | `page.route("**/*", r => r.abort(code))` per error code |
| The app's own offline experience (PWA) | Load online, wait for the service worker, then `setOffline(true)` and reload |
| A loaded page losing the network | Load online, then `setOffline(true)` and interact |
| Selected origins down, others up | `page.route("https://cdn.example.com/**", r => r.abort("internetdisconnected"))`, or CDP `Network.setBlockedURLs` |
| Guarantee no egress, WebRTC included | Section 2 (container or network namespace), not emulation |
| Other browsers | WebDriver BiDi, after checking the browser supports the commands you need |

### Native error catalogue

No real DNS failures or broken routes needed: abort every request with a Chromium network error
and screenshot the error page Chrome renders.

```ts
const errorCodes = [
  "internetdisconnected", "namenotresolved", "addressunreachable", "connectionrefused",
  "connectionreset", "connectionclosed", "connectionaborted", "connectionfailed",
  "timedout", "accessdenied", "blockedbyclient", "blockedbyresponse", "aborted", "failed",
];

for (const errorCode of errorCodes) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, serviceWorkers: "block" });
  const page = await context.newPage();
  await page.route("**/*", route => route.abort(errorCode));
  try {
    await page.goto(TARGET, { timeout: 10_000 });
  } catch {
    // Expected: navigation fails, Chromium commits its own error page (chrome-error://chromewebdata/).
  }
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${errorCode}.png` });
  await context.close();
}
```

`route.abort` returns the error at once; it doesn't reproduce real timing (a real timeout waits).
All 14 codes render Chrome's own error page at `chrome-error://chromewebdata/`, except `aborted`,
which leaves `about:blank`.

### A loaded page losing the network

```ts
await page.goto(TARGET);                       // online
await context.setOffline(true);                // drop the network
await page.getByRole("button", { name: "Save" }).click();
await expect(page.getByText(/offline|try again/i)).toBeVisible();   // adapt to the app
await page.screenshot({ path: "after-disconnect.png" });
```

### PWA offline fallback

```ts
test.use({ serviceWorkers: "allow" });
test("service worker serves the offline fallback", async ({ page, context }) => {
  await page.goto(TARGET);
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();               // become controlled if the app doesn't call clients.claim()
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByTestId("offline-fallback")).toBeVisible();   // adapt to the app
});
```

Keep cold (fresh context, service workers blocked) and warm (PWA) tests separate: they test
different things.
