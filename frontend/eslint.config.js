import js from '@eslint/js'
import prettier from 'eslint-plugin-prettier/recommended'
import vue from 'eslint-plugin-vue'
import globals from 'globals'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist/', 'node_modules/', 'playwright-report/', 'test-results/'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...vue.configs['flat/recommended'],
  {
    files: ['**/*.vue'],
    languageOptions: { parserOptions: { parser: tseslint.parser } },
  },
  // The app runs in the browser; config files and Playwright specs run in Node.
  {
    files: ['src/**'],
    languageOptions: { globals: globals.browser },
  },
  {
    files: ['*.{js,ts}', 'e2e/**'],
    languageOptions: { globals: globals.node },
  },
  prettier,
)
