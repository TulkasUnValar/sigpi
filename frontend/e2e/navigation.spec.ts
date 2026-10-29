import { test, expect } from '@playwright/test';

test.describe('Navigation E2E Tests', () => {
  test.describe('Main Navigation', () => {
    test('should navigate to dashboard from login', async ({ page }) => {
      // This test assumes user is authenticated
      // In a real scenario, you'd need to authenticate first
      await page.goto('/es/dashboard');
      await expect(page).toHaveURL(/\/es\/dashboard/);
    });

    test('should navigate to budgets section', async ({ page }) => {
      await page.goto('/es/budgets');
      await expect(page).toHaveURL(/\/es\/budgets/);
    });

    test('should navigate to projects section', async ({ page }) => {
      await page.goto('/es/projects');
      await expect(page).toHaveURL(/\/es\/projects/);
    });

    test('should navigate to products section', async ({ page }) => {
      await page.goto('/es/products');
      await expect(page).toHaveURL(/\/es\/products/);
    });

    test('should navigate to reports section', async ({ page }) => {
      await page.goto('/es/reports');
      await expect(page).toHaveURL(/\/es\/reports/);
    });
  });

  test.describe('Navigation Links', () => {
    test('should have working navigation menu', async ({ page }) => {
      await page.goto('/es/dashboard');
      
      // Check if navigation menu exists
      const nav = page.locator('nav').first();
      if (await nav.isVisible()) {
        // Try to find navigation links
        const links = nav.locator('a');
        const count = await links.count();
        expect(count).toBeGreaterThan(0);
      }
    });

    test('should maintain locale in navigation', async ({ page }) => {
      await page.goto('/es/dashboard');
      await expect(page).toHaveURL(/\/es\//);
      
      // If there's a nav with links, clicking should maintain locale
      const nav = page.locator('nav').first();
      if (await nav.isVisible()) {
        const firstLink = nav.locator('a').first();
        if (await firstLink.isVisible()) {
          await firstLink.click();
          await expect(page).toHaveURL(/\/es\//);
        }
      }
    });
  });

  test.describe('Route Protection', () => {
    test('should redirect unauthenticated users to login', async ({ page }) => {
      // Try to access protected route without authentication
      await page.goto('/es/dashboard');
      
      // Should redirect to login
      await expect(page).toHaveURL(/\/login/);
    });

    test('should allow access to public routes', async ({ page }) => {
      // Login page should be accessible
      await page.goto('/es/login');
      await expect(page).toHaveURL(/\/es\/login/);
    });
  });
});
