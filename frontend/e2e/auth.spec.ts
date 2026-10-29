import { test, expect } from '@playwright/test';

test.describe('Authentication E2E Tests', () => {
  test.describe('Login Page UI', () => {
    test('should display login page with title', async ({ page }) => {
      await page.goto('/login');
      await expect(page.locator('h1')).toBeVisible();
    });

    test('should have email and password fields', async ({ page }) => {
      await page.goto('/login');
      await expect(page.locator('input[type="email"]')).toBeVisible();
      await expect(page.locator('input[type="password"]')).toBeVisible();
    });

    test('should have login button', async ({ page }) => {
      await page.goto('/login');
      await expect(page.locator('button[type="submit"]')).toBeVisible();
    });
  });

  test.describe('Form Validation', () => {
    test('should show validation errors for empty fields', async ({ page }) => {
      await page.goto('/login');
      
      // Try to submit empty form
      await page.locator('button[type="submit"]').click();
      
      // Should show validation errors
      await expect(page.locator('text=Email is required')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('text=Password is required')).toBeVisible({ timeout: 5000 });
    });

    test('should show error for invalid email format', async ({ page }) => {
      await page.goto('/login');
      
      // Fill invalid email
      await page.locator('input[type="email"]').fill('invalid-email');
      await page.locator('input[type="password"]').fill('password123');
      
      // Submit form
      await page.locator('button[type="submit"]').click();
      
      // Should show email validation error
      await expect(page.locator('text=Invalid email')).toBeVisible({ timeout: 5000 });
    });

    test('should show error for short password', async ({ page }) => {
      await page.goto('/login');
      
      // Fill valid email but short password
      await page.locator('input[type="email"]').fill('test@example.com');
      await page.locator('input[type="password"]').fill('123');
      
      // Submit form
      await page.locator('button[type="submit"]').click();
      
      // Should show password validation error
      await expect(page.locator('text=Password must be at least')).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Authentication Flow', () => {
    test('should redirect unauthenticated user to login', async ({ page }) => {
      // Try to access protected route
      await page.goto('/dashboard');
      
      // Should be redirected to login
      await expect(page).toHaveURL(/\/login/);
    });

    test('should show loading state during login', async ({ page }) => {
      await page.goto('/login');
      
      // Fill valid credentials
      await page.locator('input[type="email"]').fill('test@example.com');
      await page.locator('input[type="password"]').fill('password123');
      
      // Submit form
      await page.locator('button[type="submit"]').click();
      
      // Should show loading state
      await expect(page.locator('button[type="submit"]').locator('text=Loading')).toBeVisible({ timeout: 5000 });
    });
  });
});
