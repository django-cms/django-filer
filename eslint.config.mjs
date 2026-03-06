import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';

export default [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['client/**/*.{ts,tsx}'],
    plugins: {
      react,
      'react-hooks': reactHooks,
    },
    languageOptions: {
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        document: 'readonly',
        window: 'readonly',
        console: 'readonly',
        fetch: 'readonly',
        gettext: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        FormData: 'readonly',
        XMLHttpRequest: 'readonly',
        HTMLInputElement: 'readonly',
        HTMLSelectElement: 'readonly',
        HTMLElement: 'readonly',
        HTMLDialogElement: 'readonly',
        URLSearchParams: 'readonly',
        AudioContext: 'readonly',
        URL: 'readonly',
        alert: 'readonly',
        ProgressEvent: 'readonly',
      },
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
    rules: {
      // React rules
      'react/jsx-uses-react': 'off',       // Not needed with React 17+ JSX transform
      'react/react-in-jsx-scope': 'off',    // Not needed with React 17+ JSX transform
      'react/prop-types': 'off',            // Using TypeScript for prop types
      'react/display-name': 'off',
      'react/no-unescaped-entities': 'warn',
      'react/jsx-key': 'error',
      'react/no-direct-mutation-state': 'error',

      // React Hooks rules
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',

      // TypeScript rules
      '@typescript-eslint/no-unused-vars': ['warn', {argsIgnorePattern: '^_'}],
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-empty-function': 'off',

      // General rules
      'no-console': ['warn', {allow: ['warn', 'error']}],
      'no-debugger': 'warn',
      'no-duplicate-case': 'error',
      'no-empty': 'warn',
      'prefer-const': 'warn',
    },
  },
  {
    ignores: [
      'finder/static/**',
      'node_modules/**',
      'filer/**',
      'docs/**',
      'tests/**',
    ],
  },
];

