// eslint.config.js — final version for Vite + React + Vitest
import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import vitest from 'eslint-plugin-vitest-globals'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist', 'node_modules']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
        ...vitest.environments.env.globals, // ✅ fixes 'test' and 'expect' undefined
      },
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    rules: {
      // --- General ---
      'no-unused-vars': ['warn', { varsIgnorePattern: '^[A-Z_]' }],
      'no-empty': 'off',
      'no-useless-escape': 'off',

      // --- React specific ---
      'react/react-in-jsx-scope': 'off', // ✅ for React 17+ (Vite)
      'react-refresh/only-export-components': 'off', // avoid Fast Refresh warnings
      'react-hooks/exhaustive-deps': 'warn', // keep warning only
      'react/prop-types': 'off', // disable prop-types requirement
    },
  },
])
