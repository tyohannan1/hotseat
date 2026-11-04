// End-to-end smoke test, local test mode: presenter tab + one phone tab in the same browser context
// (the MockStore syncs them through localStorage + BroadcastChannel, same as two real tabs).
import { test, expect } from "@playwright/test";

test("lecture runs end to end: slides, pretest, hot seat, quick check reveal, zoom, present mode, notes, posttest, pre/post reveal, summary", async ({ page, context }) => {
  // the smoke test always runs in local test mode: block config.js even when a real one exists
  await context.route("**/config.js", r => r.abort());
  // presenter: start a session
  await page.goto("/present.html");
  await expect(page.locator("#h-mode")).toHaveText("local test mode");
  await page.click("#btn-start");
  await expect(page.locator("#v-lobby")).toBeVisible();
  const sid = (await page.locator("#h-sid").textContent()).trim();
  expect(sid).toMatch(/^[A-Z0-9]{6}$/);

  // phone: join and pick a year
  const phone = await context.newPage();
  await phone.goto(`/vote.html?s=${sid}`);
  await expect(phone.locator("#s-class")).toBeVisible();
  await phone.click('#s-class button[data-c="R2"]');
  await expect(phone.locator("#s-wait")).toBeVisible();
  await expect(page.locator("#h-joined")).toHaveText("1");

  // Begin -> first item is a teaching slide; phone keeps waiting; no question controls
  await page.click("#btn-begin");
  await expect(page.locator("#slideview")).toBeVisible();
  await expect(page.locator("#runner")).toBeHidden();
  await expect(page.locator("#q-controls")).toBeHidden();
  await expect(page.locator("#s-title")).toHaveText("Disease-Specific Reporting");
  await expect(page.locator("#s-body .t-by")).toHaveText("Thomas Yohannan, MD");
  await expect(phone.locator("#s-wait")).toBeVisible();
  // pretest comes right after the title card
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("#runner")).toBeVisible();
  await expect(page.locator("#q-kind")).toContainText("Pretest");
  // L toggles circles: letters-only image by default, circled image when on
  await expect(page.locator("#imgbox img")).toHaveAttribute("src", /pre1-pelvis-fdg\.png/);
  await page.keyboard.press("l");
  await expect(page.locator("#imgbox img")).toHaveAttribute("src", /pre1-pelvis-fdg-(clean|bare)\.png/);
  await page.keyboard.press("l");
  await expect(page.locator("#imgbox img")).toHaveAttribute("src", /pre1-pelvis-fdg\.png/);
  // pretest: Reveal is hidden and R does nothing
  await expect(page.locator("#btn-reveal")).toBeHidden();
  await page.keyboard.press("r");
  await expect(page.locator("#st-state")).toHaveText("voting closed");

  // open voting, phone votes B, presenter counts 1 answered, phone remembers after reload
  await page.keyboard.press("o");
  await expect(page.locator("#st-state")).toHaveText("voting open");
  await expect(phone.locator("#s-q")).toBeVisible();
  await expect(phone.locator('.v-opt[data-i="1"]')).toBeEnabled();
  await phone.click('.v-opt[data-i="1"]');
  await expect(phone.locator('.v-opt[data-i="1"]')).toHaveClass(/chosen/);
  await expect(page.locator("#st-n")).toHaveText("1");
  await phone.reload();
  await expect(phone.locator('.v-opt[data-i="1"]')).toHaveClass(/chosen/);

  // hot seat: pick (R3/R4 pool), record answer C
  await page.keyboard.press("x");
  await expect(page.locator("#st-state")).toHaveText("voting closed");
  await page.click("#btn-pick");
  await expect(page.locator("#hot-name")).not.toHaveText("—", { timeout: 10000 });
  await expect(page.locator("#hot-cls")).toHaveText(/R[34]/);
  await expect(page.locator("#hot-name")).not.toHaveClass(/spin/);
  await expect(page.locator("#btn-pick")).toBeEnabled(); // re-enabled only once the pick is written to the session
  await expect(page.locator("#pool")).toContainText("29 of 30 not yet called");
  await page.keyboard.press("c");
  await expect(page.locator('#hot-answer button[data-a="2"]')).toHaveClass(/chosen/);


  // pre2..pre4, then the opening slides
  for (let k = 0; k < 2; k++) await page.keyboard.press("ArrowRight");
  await expect(page.locator("#q-kind")).toContainText("Pretest");
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("#s-title")).toContainText("ask what disease");
  // build slide: each ArrowRight reveals one line; the 8 body lines, then the next item
  await expect(page.locator("#s-body .frag")).toHaveCount(8);
  await expect(page.locator("#s-body .frag.shown")).toHaveCount(0);
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("#s-body .frag.shown")).toHaveCount(1);
  for (let k = 0; k < 7; k++) await page.keyboard.press("ArrowRight");
  await expect(page.locator("#s-body .frag.shown")).toHaveCount(8);
  await page.keyboard.press("ArrowLeft");
  await expect(page.locator("#s-body .frag.shown")).toHaveCount(7);
  await page.keyboard.press("ArrowRight");

  // arrow keys move through items in order; second slide, then pre1
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("#s-title")).toHaveText("Lymphoma counts regions");
  await expect(page.locator("#s-media img")).toHaveAttribute("src", /regions-lymphoma\.svg(\?v=\w+)?$/);
  // title builds in too: 1 title + 2 lines, then the next item
  await expect(page.locator("#s-title")).not.toHaveClass(/shown/);
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("#s-title")).toHaveClass(/shown/);
  await page.keyboard.press("ArrowRight"); await page.keyboard.press("ArrowRight");
  await expect(page.locator("#s-body .frag.shown")).toHaveCount(2);
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("#s-title")).toHaveText("Three landmarks");

  // jump straight to the first quick check and reveal there
  await page.click('#jump button:text-is("qc1")');
  await expect(page.locator("#q-kind")).toContainText("Quick check");
  await expect(page.locator("#btn-reveal")).toBeVisible();
  await page.keyboard.press("o");
  await expect(phone.locator('.v-opt[data-i="0"]')).toBeEnabled();
  await phone.click('.v-opt[data-i="0"]');
  await expect(page.locator("#st-n")).toHaveText("1");
  await page.keyboard.press("r");
  await expect(page.locator("#st-state")).toHaveText("revealed");
  await expect(page.locator('#opts .opt[data-i="0"]')).toHaveClass(/correct/);
  await expect(page.locator("#explain")).toBeVisible();
  await expect(phone.locator('.v-opt[data-i="0"]')).toBeDisabled();

  // slide with NCCN crops renders images (or labeled placeholders), table slide renders rows
  await page.click('#jump button[title="Same node, different page"]');
  await expect(page.locator("#s-media .nccn")).toHaveCount(2);
  await page.click('#jump button[title="One node, seven labels"]');
  await expect(page.locator("#s-body .s-table tr")).toHaveCount(8);

  // presenter refresh + resume lands on the same item
  await page.reload();
  await page.fill("#resume", sid);
  await page.click("#btn-resume");
  await expect(page.locator("#s-title")).toHaveText("One node, seven labels");

  // image zoom: Z opens the full-bleed overlay on a slide with an image, Esc closes it
  await page.click('#jump button[title="External iliac vs common iliac"]');
  await page.keyboard.press("z");
  await expect(page.locator("#zoom")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator("#zoom")).toBeHidden();

  // presentation mode: F hides the header and jump bar
  await page.keyboard.press("f");
  await expect(page.locator("body")).toHaveClass(/present/);
  await expect(page.locator(".p-header")).toBeHidden();
  await expect(page.locator("#jump")).toBeHidden();
  await page.keyboard.press("f");
  await expect(page.locator("body")).not.toHaveClass(/present/);

  // notes window follows the session: current slide title, notes text, next item
  const notes = await context.newPage();
  await notes.goto(`/notes.html?s=${sid}`);
  await expect(notes.locator("#n-title")).toHaveText("External iliac vs common iliac");
  await expect(notes.locator("#n-notes")).toContainText(/draw the bifurcation/i);
  await expect(notes.locator("#n-notes .n-src")).toContainText("AutoPET PETCT_791ec15924");
  await expect(notes.locator("#n-next")).toContainText("describe node A");
  await expect(notes.locator("#n-clock")).toHaveText(/^\d+:\d\d$/);

  // posttest: no Reveal button, vote on post1; notes shows the live count and the correct letter
  await page.click('#jump button:text-is("post1")');
  await expect(page.locator("#hotbox")).toBeHidden();
  await expect(page.locator("#btn-reveal")).toBeHidden();
  await page.keyboard.press("o");
  await expect(phone.locator('.v-opt[data-i="2"]')).toBeEnabled();
  await phone.click('.v-opt[data-i="2"]');
  await expect(page.locator("#st-n")).toHaveText("1");
  await expect(notes.locator("#n-answered")).toHaveText("1");
  await expect(notes.locator("#n-correct")).toHaveText("C");

  // pre/post reveal: Next after the last item lands here; pair 1 shows both bar sets and the correct row
  await page.click('#jump button[title="Ask what disease is being staged. That decides which words matter."]:last-child');
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("#v-reveal")).toBeVisible();
  await expect(page.locator(".rv-row")).toHaveCount(4);
  await expect(page.locator('.rv-row.correct .rv-letter')).toHaveText("C");
  await expect(page.locator("#rv-status")).toContainText("0% → 100%");
  await page.keyboard.press("ArrowRight");
  await expect(page.locator(".eyebrow", { hasText: "2 of 3" })).toBeVisible();
  await page.click("#btn-rv-summary");
  await expect(page.locator("#v-summary")).toBeVisible();
  await expect(page.locator("#sum-table tr")).toHaveCount(28); // header + 12 question items, no slides
  await expect(page.locator("#sum-pairs")).toContainText("pre1 → post1");
  await expect(page.locator("#sum-pairs")).toContainText("Paired devices: 1 · improved 1");
});
