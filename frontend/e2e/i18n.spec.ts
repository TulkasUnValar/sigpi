import { test, expect } from '@playwright/test';

test.describe('Internationalization E2E Tests', () => {
  test('should display language switcher', async ({ page }) => {
    await page.goto('/login');
    // Language switcher should be visible
    await expect(page.locator('[data-testid="language-switcher"]')).toBeVisible();
  });

  test('should switch from Spanish to English', async ({ page }) => {
    await page.goto('/es/login');
    // Click language switcher to English
    await page.locator('[data-testid="language-switcher"]').click();
    await page.locator('text=English').click();

    // URL should change to /en
    await expect(page).toHaveURL(/\/en\//);
  });

  test('should switch from English to Spanish', async ({ page }) => {
    await page.goto('/en/login');
    // Click language switcher to Spanish
    await page.locator('[data-testid="language-switcher"]').click();
    await page.locator('text=Español').click();

    // URL should change to /es
    await expect(page).toHaveURL(/\/es\//);
  });
});
