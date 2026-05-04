import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: process.env.FRONTEND_URL || 'http://localhost:5050',
    headless: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
    {
      name: 'mobile-chromium',
      use: {
        ...devices['Pixel 7'],
        baseURL: process.env.FRONTEND_URL || 'http://localhost:5050',
      },
    },
  ],
});
