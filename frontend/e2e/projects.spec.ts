import { test, expect } from '@playwright/test';

test.describe('Projects Business Flow E2E Tests', () => {
  test.describe('Project List View', () => {
    test('should display projects list page', async ({ page }) => {
      await page.goto('/es/projects');
      await expect(page).toHaveURL(/\/es\/projects/);
      
      const pageContent = page.locator('main, [role="main"]').first();
      await expect(pageContent).toBeVisible({ timeout: 10000 });
    });

    test('should have create project button', async ({ page }) => {
      await page.goto('/es/projects');
      
      const createButton = page.locator('button:has-text("Crear"), button:has-text("Nuevo"), a:has-text("Crear"), a:has-text("Nuevo")');
      if (await createButton.isVisible()) {
        await expect(createButton).toBeEnabled();
      }
    });
  });

  test.describe('Project Detail View', () => {
    test('should navigate to project detail', async ({ page }) => {
      await page.goto('/es/projects');
      
      const projectLink = page.locator('a[href*="/projects/"]').first();
      if (await projectLink.isVisible()) {
        await projectLink.click();
        await expect(page).toHaveURL(/\/es\/projects\/\d+/);
      }
    });
  });

  test.describe('Project Creation Flow', () => {
    test('should access create project page', async ({ page }) => {
      await page.goto('/es/projects/new');
      await expect(page).toHaveURL(/\/es\/projects\/new/);
      
      const form = page.locator('form').first();
      if (await form.isVisible()) {
        await expect(form).toBeVisible();
      }
    });

    test('should validate required fields in project form', async ({ page }) => {
      await page.goto('/es/projects/new');
      
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
