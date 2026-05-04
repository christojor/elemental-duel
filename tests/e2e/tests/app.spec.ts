import { test, expect } from '@playwright/test';

test('homepage loads', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Elemental Duel' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Duel' })).toBeVisible();
});

test('user can play one round', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Choose your element').selectOption('Fire');
  await page.getByRole('button', { name: 'Duel' }).click();
  await expect(page.getByText('Result:')).toBeVisible();
});

test.describe('mobile layout', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('duel flow remains usable on small screens', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('button', { name: 'Duel' })).toBeVisible();
    await page.getByLabel('Choose your element').selectOption('Fire');
    await page.getByRole('button', { name: 'Duel' }).click();
    await expect(page.getByText('Result:')).toBeVisible();
    await expect(page.locator('span[title="Player"]')).toBeVisible();
    await expect(page.locator('span[title="AI"]')).toBeVisible();
    await expect(page.locator('span[title="Fire"]').first()).toBeVisible();
  });
});
