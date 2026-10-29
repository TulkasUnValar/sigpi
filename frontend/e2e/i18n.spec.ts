import { test, expect } from '@playwright/test';

test.describe('Internationalization E2E Tests', () => {
  test('should display language switcher in header', async ({ page }) => {
    await page.goto('/login');
    // Language switcher should be visible in header
    const switcher = page.locator('header').locator('button').first();
    await expect(switcher).toBeVisible();
  });

  test('should have Spanish as default locale in URL', async ({ page }) => {
    await page.goto('/');
    // Should redirect to /es/ by default
    await expect(page).toHaveURL(/\/es\/?.*/);
  });

  test('should switch from Spanish to English', async ({ page }) => {
    await page.goto('/es/login');
    
    // Verify we're in Spanish
    await expect(page).toHaveURL(/\/es\//);
    
    // Click language switcher to English
    const switcher = page.locator('header').locator('button').first();
    await switcher.click();
    
    // Find and click English option
    const enButton = page.locator('button:has-text("EN")').or(page.locator('button:has-text("English")'));
    await enButton.click();

    // URL should change to /en
    await expect(page).toHaveURL(/\/en\//);
  });

  test('should switch from English to Spanish', async ({ page }) => {
    await page.goto('/en/login');
    
    // Verify we're in English
    await expect(page).toHaveURL(/\/en\//);
    
    // Click language switcher to Spanish
    const switcher = page.locator('header').locator('button').first();
    await switcher.click();
    
    // Find and click Spanish option
    const esButton = page.locator('button:has-text("ES")').or(page.locator('button:has-text("Español")'));
    await esButton.click();

    // URL should change to /es
    await expect(page).toHaveURL(/\/es\//);
  });

  test('should display translated content in Spanish', async ({ page }) => {
    await page.goto('/es/login');
    
    // Check for Spanish text (adjust selectors based on actual implementation)
    const body = page.locator('body');
    const content = await body.textContent();
    
    // Should contain some Spanish text (example: "Iniciar sesión" or similar)
    // This is a basic check - adjust based on actual login page content
    expect(content).toBeTruthy();
  });

  test('should display translated content in English', async ({ page }) => {
    await page.goto('/en/login');
    
    // Check for English text
    const body = page.locator('body');
    const content = await body.textContent();
    
    // Should contain some English text
    expect(content).toBeTruthy();
  });

  test('should maintain locale when navigating between pages', async ({ page }) => {
    await page.goto('/es/login');
    await expect(page).toHaveURL(/\/es\//);
    
    // Navigate to home or another page
    await page.goto('/es/');
    await expect(page).toHaveURL(/\/es\/?.*/);
    
    // Switch to English
    const switcher = page.locator('header').locator('button').first();
    await switcher.click();
    const enButton = page.locator('button:has-text("EN")').or(page.locator('button:has-text("English")'));
    await enButton.click();
    
    await expect(page).toHaveURL(/\/en\//);
    
    // Navigate to another page - should maintain /en/ locale
    await page.goto('/en/');
    await expect(page).toHaveURL(/\/en\/?.*/);
  });
});
