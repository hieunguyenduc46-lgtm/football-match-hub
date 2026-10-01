import { defineConfig } from 'vitest/config'

// Unit tests for pure helper functions (src/utils). They run in Node, no browser needed.
// Coverage is written as lcov so SonarQube can read it in the Code Quality stage.
export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.js'],
    reporters: ['default', 'junit'],
    outputFile: { junit: 'reports/junit.xml' },
    coverage: {
      provider: 'v8',
      include: ['src/utils/**/*.js'],
      reporter: ['text', 'lcov'],
      reportsDirectory: 'coverage',
    },
  },
})
