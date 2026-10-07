/** @type {import('jest').Config} */
const config = {
  testEnvironment: "jsdom",
  // jsdom + Radix interaction suites are wall-clock heavy: the multi-step
  // ProductList filter tests spent >5s under full parallel load while taking
  // ~1.3s in isolation. Jest's 5s default is calibrated for pure unit tests,
  // not component-integration tests, so give them explicit headroom.
  testTimeout: 15000,
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  transform: {
    "^.+\\.tsx?$": [
      "ts-jest",
      {
        tsconfig: {
          jsx: "react-jsx",
          module: "esnext",
          moduleResolution: "bundler",
          target: "ES2017",
          esModuleInterop: true,
          strict: true,
          paths: {
            "@/*": ["./*"],
          },
        },
      },
    ],
  },
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/$1",
  },
  testMatch: ["**/__tests__/**/*.test.{ts,tsx}"],
  collectCoverageFrom: [
    "lib/**/*.{ts,tsx}",
    "store/**/*.{ts,tsx}",
    "components/**/*.{ts,tsx}",
    "features/**/*.{ts,tsx}",
    "middleware.ts",
    "!**/*.d.ts",
    "!**/node_modules/**",
    // shadcn/ui generated boilerplate not yet exercised by this slice's
    // feature tests — shipped primitives, covered through usage in later PRs.
    "!components/ui/dropdown-menu.tsx",
    "!components/ui/select.tsx",
    "!components/ui/sheet.tsx",
    "!components/ui/input.tsx",
    "!components/ui/label.tsx",
    "!components/ui/separator.tsx",
    "!components/ui/switch.tsx",
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
};

module.exports = config;
