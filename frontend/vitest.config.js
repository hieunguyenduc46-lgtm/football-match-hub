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
      // Logic that is unit tested: helpers, translations, Pinia stores.
      // Vue page components are checked end-to-end by the pipeline's smoke tests instead.
      include: ['src/utils/**/*.js', 'src/i18n.js', 'src/stores/**/*.js'],
      reporter: ['text', 'lcov'],
      reportsDirectory: 'coverage',
    },
  },
})
