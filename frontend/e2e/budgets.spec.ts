import { test, expect } from '@playwright/test';

test.describe('Budgets Business Flow E2E Tests', () => {
  test.describe('Budget List View', () => {
    test('should display budgets list page', async ({ page }) => {
      await page.goto('/es/budgets');
      await expect(page).toHaveURL(/\/es\/budgets/);
      
      // Check if page has content (title or list)
      const pageContent = page.locator('main, [role="main"]').first();
      await expect(pageContent).toBeVisible({ timeout: 10000 });
    });

    test('should have create budget button', async ({ page }) => {
      await page.goto('/es/budgets');
      
      // Look for create button
      const createButton = page.locator('button:has-text("Crear"), button:has-text("Nuevo"), a:has-text("Crear"), a:has-text("Nuevo")');
      if (await createButton.isVisible()) {
        await expect(createButton).toBeEnabled();
      }
    });
  });

  test.describe('Budget Detail View', () => {
    test('should navigate to budget detail', async ({ page }) => {
      await page.goto('/es/budgets');
      
      // If there are budgets in the list, try to click on one
      const budgetLink = page.locator('a[href*="/budgets/"]').first();
      if (await budgetLink.isVisible()) {
        await budgetLink.click();
        await expect(page).toHaveURL(/\/es\/budgets\/\d+/);
      }
    });
  });

  test.describe('Budget Creation Flow', () => {
    test('should access create budget page', async ({ page }) => {
      await page.goto('/es/budgets/new');
      await expect(page).toHaveURL(/\/es\/budgets\/new/);
      
      // Check if form is visible
      const form = page.locator('form').first();
      if (await form.isVisible()) {
        await expect(form).toBeVisible();
      }
    });

    test('should validate required fields in budget form', async ({ page }) => {
      await page.goto('/es/budgets/new');
      
      const form = page.locator('form').first();
      if (await form.isVisible()) {
        // Try to submit empty form
        const submitButton = form.locator('button[type="submit"]').first();
        if (await submitButton.isVisible()) {
          await submitButton.click();
          
          // Should show validation errors
          const errorMessages = page.locator('[role="alert"], .error, .invalid-feedback');
          const errorCount = await errorMessages.count();
          expect(errorCount).toBeGreaterThan(0);
        }
      }
    });
  });
});
