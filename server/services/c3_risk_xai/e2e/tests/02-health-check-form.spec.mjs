// The health check form: valid and invalid values, required and optional answers.
import { expect, test } from '@playwright/test';
import { button, openApp, savedCount, scrollTo, text, typeInto, see, notSee, atHome } from '../support/app.mjs';

async function openForm(page) {
  const deviceId = await openApp(page);
  await button(page, 'Start a health check').click();
  await see(page, 'Your health details');
  return deviceId;
}

async function choose(page, name, index = 0) {
  const chip = await scrollTo(page, page.getByRole('checkbox', { name, exact: true }).nth(index));
  await chip.click();
}

async function submit(page) {
  const go = await scrollTo(page, button(page, 'Save & recalculate'));
  await go.click();
}

const invalidCases = [
  ['Age (years)', '10', 'Enter a value from 18 to 100'],
  ['Age (years)', '120', 'Enter a value from 18 to 100'],
  ['Age (years)', 'abc', 'Enter a number'],
  ['Height (cm)', '50', 'Enter a value from 100 to 250'],
  ['Weight (kg)', '500', 'Enter a value from 20 to 300'],
  ['Systolic (mmHg)', '300', 'Enter a value from 70 to 260'],
  ['Diastolic (mmHg)', '20', 'Enter a value from 40 to 150'],
  ['Resting pulse (beats per minute)', '10', 'Enter a value from 35 to 200'],
];

for (const [label, value, message] of invalidCases) {
  test(`form rejects ${label} = ${value} before sending`, async ({ page }) => {
    const deviceId = await openForm(page);
    await typeInto(page, label, value);
    await submit(page);
    await expect(text(page, message)).toBeVisible();
    await notSee(page, 'Estimated risk:');
    expect(await savedCount(deviceId)).toBe(0);
  });
}

test('form rejects an out-of-range blood glucose once the glucose switch is on', async ({ page }) => {
  await openForm(page);
  const toggle = await scrollTo(page, page.getByRole('switch', { name: 'I have a recent blood glucose result' }));
  await toggle.click();
  await typeInto(page, 'Blood glucose (mmol/L)', '50');
  await submit(page);
  await see(page, 'Enter a value from 1.5 to 40');
});

test('a fully valid form, typed with the keyboard, gives a result and is saved once', async ({ page }) => {
  const deviceId = await openForm(page);
  await typeInto(page, 'Age (years)', '45');
  await choose(page, 'Female');
  await typeInto(page, 'Height (cm)', '160');
  await typeInto(page, 'Weight (kg)', '60');
  await see(page, 'Your BMI: 23.4');
  await typeInto(page, 'Systolic (mmHg)', '118');
  await typeInto(page, 'Diastolic (mmHg)', '76');
  await choose(page, 'High');
  await typeInto(page, 'Resting pulse (beats per minute)', '72');
  const toggle = await scrollTo(page, page.getByRole('switch', { name: 'I have a recent blood glucose result' }));
  await toggle.click();
  await typeInto(page, 'Blood glucose (mmol/L)', '5.2');
  await submit(page);
  await expect(button(page, 'Update health information')).toBeVisible({ timeout: 30_000 });
  await see(page, 'estimated risk');
  await expect.poll(() => savedCount(deviceId)).toBe(1);
});

test('required answers: leaving age empty asks for it instead of guessing', async ({ page }) => {
  await openForm(page);
  await choose(page, 'Male');
  await typeInto(page, 'Height (cm)', '170');
  await typeInto(page, 'Weight (kg)', '70');
  await typeInto(page, 'Systolic (mmHg)', '120');
  await typeInto(page, 'Diastolic (mmHg)', '80');
  await submit(page);
  await see(page, 'We need a few more answers', { timeout: 30_000 });
  await see(page, 'age');
});

test('optional answers: pulse and glucose may stay empty', async ({ page }) => {
  await openForm(page);
  await typeInto(page, 'Age (years)', '50');
  await choose(page, 'Male');
  await typeInto(page, 'Height (cm)', '170');
  await typeInto(page, 'Weight (kg)', '70');
  await typeInto(page, 'Systolic (mmHg)', '120');
  await typeInto(page, 'Diastolic (mmHg)', '80');
  await submit(page);
  await expect(button(page, 'Update health information')).toBeVisible({ timeout: 30_000 });
});

test('Back on the form returns home without sending anything', async ({ page }) => {
  const deviceId = await openForm(page);
  await typeInto(page, 'Age (years)', '50');
  await button(page, 'Back').click();
  await expect(button(page, 'Start a health check')).toBeVisible();
  expect(await savedCount(deviceId)).toBe(0);
});
