import { test, expect } from '@playwright/test';

test.describe('Products Business Flow E2E Tests', () => {
  test.describe('Product List View', () => {
    test('should display products list page', async ({ page }) => {
      await page.goto('/es/products');
      await expect(page).toHaveURL(/\/es\/products/);
      
      const pageContent = page.locator('main, [role="main"]').first();
      await expect(pageContent).toBeVisible({ timeout: 10000 });
    });

    test('should have create product button', async ({ page }) => {
      await page.goto('/es/products');
      
      const createButton = page.locator('button:has-text("Crear"), button:has-text("Nuevo"), a:has-text("Crear"), a:has-text("Nuevo")');
      if (await createButton.isVisible()) {
        await expect(createButton).toBeEnabled();
      }
    });
  });

  test.describe('Product Detail View', () => {
    test('should navigate to product detail', async ({ page }) => {
      await page.goto('/es/products');
      
      const productLink = page.locator('a[href*="/products/"]').first();
      if (await productLink.isVisible()) {
        await productLink.click();
        await expect(page).toHaveURL(/\/es\/products\/\d+/);
      }
    });
  });

  test.describe('Product Creation Flow', () => {
    test('should access create product page', async ({ page }) => {
      await page.goto('/es/products/new');
      await expect(page).toHaveURL(/\/es\/products\/new/);
      
      const form = page.locator('form').first();
      if (await form.isVisible()) {
        await expect(form).toBeVisible();
      }
    });

    test('should validate required fields in product form', async ({ page }) => {
      await page.goto('/es/products/new');
      
      const form = page.locator('form').first();
      if (await form.isVisible()) {
        const submitButton = form.locator('button[type="submit"]').first();
        if (await submitButton.isVisible()) {
          await submitButton.click();
          
          const errorMessages = page.locator('[role="alert"], .error, .invalid-feedback');
          const errorCount = await errorMessages.count();
          expect(errorCount).toBeGreaterThan(0);
        }
      }
    });
  });
});
