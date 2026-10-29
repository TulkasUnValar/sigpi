# E2E Testing Guide - SIGPI

This guide explains how to work with end-to-end (E2E) tests in the SIGPI project using Playwright.

## Overview

E2E tests verify that the application works correctly from the user's perspective, testing complete workflows across the frontend and backend integration.

**Test Location:** `frontend/e2e/`

**Framework:** Playwright (v1.64.1+)

**Browsers:** Chromium, Firefox, WebKit

## Running E2E Tests

### Basic Commands

```bash
# Run all E2E tests
npm run test:e2e

# Run tests with UI mode (interactive)
npm run test:e2e:ui

# Run tests with visible browser
npm run test:e2e:headed

# Run tests in debug mode
npm run test:e2e:debug

# View test report
npm run test:e2e:report
```

### Running Specific Tests

```bash
# Run a specific test file
npx playwright test e2e/auth.spec.ts

# Run tests matching a pattern
npx playwright test -g "login"

# Run tests for a specific browser
npx playwright test --project=chromium
```

### Prerequisites

Before running E2E tests:

1. **Backend must be running** on `http://localhost:8000`
2. **Frontend must be running** on `http://localhost:3000`
3. **Test data must be set up** (see Test Data section)

```bash
# Terminal 1: Start backend
cd backend
python manage.py runserver

# Terminal 2: Start frontend
cd frontend
npm run dev

# Terminal 3: Run tests
cd frontend
npm run test:e2e
```

## Test Structure

### File Organization

```
frontend/e2e/
├── auth.spec.ts              # Authentication tests
├── i18n.spec.ts              # Internationalization tests
├── navigation.spec.ts        # Navigation and routing tests
├── budgets.spec.ts           # Budget module E2E tests
├── projects.spec.ts          # Projects module E2E tests
├── products.spec.ts          # Products module E2E tests
└── fixtures/
    └── test-data.ts          # Shared test data and helpers
```

### Test Categories

1. **Authentication Tests** (`auth.spec.ts`)
   - Login flow
   - Session persistence
   - Logout
   - Protected routes

2. **Internationalization Tests** (`i18n.spec.ts`)
   - Language switching
   - URL localization
   - Content translation

3. **Navigation Tests** (`navigation.spec.ts`)
   - Menu navigation
   - Breadcrumbs
   - Deep linking
   - Route guards

4. **Module Tests** (`budgets.spec.ts`, `projects.spec.ts`, `products.spec.ts`)
   - List views
   - Detail views
   - Create/Edit forms
   - Business workflows

## Writing New Tests

### Basic Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test('should do something', async ({ page }) => {
    // Navigate to page
    await page.goto('/es/page');
    
    // Interact with elements
    await page.click('button:has-text("Submit")');
    
    // Assert expectations
    await expect(page).toHaveURL(/\/success/);
  });
});
```

### Best Practices

1. **Use Page Objects for complex interactions**
   ```typescript
   class LoginPage {
     constructor(page) {
       this.page = page;
       this.emailInput = page.locator('[name="email"]');
       this.passwordInput = page.locator('[name="password"]');
       this.submitButton = page.locator('button[type="submit"]');
     }
     
     async login(email, password) {
       await this.emailInput.fill(email);
       await this.passwordInput.fill(password);
       await this.submitButton.click();
     }
   }
   ```

2. **Use meaningful test descriptions**
   ```typescript
   // Good
   test('should show validation error when email is empty', async ({ page }) => {
   
   // Bad
   test('test1', async ({ page }) => {
   ```

3. **Wait for network requests when needed**
   ```typescript
   // Wait for API response
   const responsePromise = page.waitForResponse('**/api/projects');
   await page.click('button:has-text("Load Projects")');
   await responsePromise;
   ```

4. **Use test.fixme() for known issues**
   ```typescript
   test.fixme('should handle edge case', async ({ page }) => {
     // Known issue, will be fixed later
   });
   ```

5. **Clean up after tests**
   ```typescript
   test.afterEach(async ({ page }) => {
     // Clear cookies, localStorage, etc.
     await page.context().clearCookies();
   });
   ```

## Test Data

### Using Fixtures

Create test data in `frontend/e2e/fixtures/test-data.ts`:

```typescript
export const testUser = {
  email: 'test@example.com',
  password: 'testpass123',
  firstName: 'Test',
  lastName: 'User'
};

export const testProject = {
  title: 'Test Project',
  description: 'Test description',
  budget: 10000
};
```

Use fixtures in tests:

```typescript
import { test, expect } from '@playwright/test';
import { testUser, testProject } from './fixtures/test-data';

test('should create project', async ({ page }) => {
  // Login with test user
  await page.goto('/login');
  await page.fill('[name="email"]', testUser.email);
  await page.fill('[name="password"]', testUser.password);
  await page.click('button[type="submit"]');
  
  // Create project
  await page.goto('/projects/new');
  await page.fill('[name="title"]', testProject.title);
  // ...
});
```

### Database Setup

For tests that require specific database state:

1. **Use Django management commands** to create test data:
   ```bash
   python manage.py create_test_data
   ```

2. **Reset database between test runs**:
   ```bash
   python manage.py flush --no-input
   python manage.py loaddata test_fixtures.json
   ```

## Debugging Tests

### View Test Execution

```bash
# Run with visible browser
npm run test:e2e:headed

# Run in debug mode (with debugger)
npm run test:e2e:debug
```

### View Screenshots and Videos

Playwright automatically captures screenshots and videos on failure:

- **Screenshots:** `frontend/test-results/`
- **Videos:** `frontend/test-results/`
- **HTML Report:** `frontend/playwright-report/`

### Common Issues

1. **Element not found**
   - Check if element is visible: `await expect(page.locator('.element')).toBeVisible()`
   - Add explicit wait: `await page.waitForSelector('.element')`

2. **Timeout errors**
   - Increase timeout: `test.setTimeout(60000)`
   - Check if backend/frontend is running

3. **Network errors**
   - Verify API endpoints are correct
   - Check backend logs for errors

## CI/CD Integration

E2E tests run automatically in GitHub Actions:

- **Trigger:** On push to main/develop, and on PRs
- **Job:** `e2e-tests` (see `.github/workflows/ci.yml`)
- **Artifacts:** Test reports uploaded for 30 days

### Local CI Simulation

```bash
# Run tests as CI would
CI=true npm run test:e2e
```

## Configuration

Playwright configuration is in `frontend/playwright.config.ts`:

```typescript
export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: 'http://localhost:3000',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
    { name: 'firefox', use: { browserName: 'firefox' } },
    { name: 'webkit', use: { browserName: 'webkit' } },
  ],
});
```

## Resources

- [Playwright Documentation](https://playwright.dev/docs/intro)
- [Playwright API](https://playwright.dev/docs/api/class-playwright)
- [Testing Library](https://testing-library.com/docs/)
- SIGPI Frontend Documentation: `docs/frontend/architecture.md`

## Troubleshooting

### Tests fail locally but pass in CI

- Check if backend is running on correct port (8000)
- Verify frontend is running on correct port (3000)
- Clear browser cache: `npx playwright clear-cache`

### Tests are slow

- Use `page.route()` to mock slow API responses
- Run tests in parallel: `npx playwright test --workers=4`
- Disable video recording for faster execution

### Flaky tests

- Add explicit waits for dynamic content
- Avoid relying on exact timings
- Use `await expect().toBeVisible()` instead of arbitrary timeouts

---

**Last Updated:** 2026-01-XX
**Maintained by:** SIGPI Development Team
