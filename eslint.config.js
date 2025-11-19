export default [
    {
        files: ['**/*.js'],
        languageOptions: {
            ecmaVersion: 2015,
            sourceType: 'script',
            globals: {
                // Browser globals
                window: 'readonly',
                document: 'readonly',
                console: 'readonly',
                alert: 'readonly',
                // Node.js globals
                require: 'readonly',
                module: 'readonly',
                __dirname: 'readonly',
                process: 'readonly',
                // Django globals
                django: 'readonly',
                // Third-party library globals
                Dropzone: 'readonly',
                Mediator: 'readonly',
                Class: 'readonly',
                opener: 'readonly',
                // Test globals
                jasmine: 'readonly',
                describe: 'readonly',
                it: 'readonly',
                expect: 'readonly',
                beforeEach: 'readonly',
                afterEach: 'readonly'
            }
        },
        rules: {
            // Code quality
            'eqeqeq': ['error', 'always'],
            'curly': ['error', 'all'],
            'no-unused-vars': ['error', { 'vars': 'all', 'args': 'after-used' }],
            'no-undef': 'error',
            'no-bitwise': 'error',
            'no-caller': 'error',

            // Style
            'quotes': ['error', 'single', { 'avoidEscape': true }],
            'indent': ['error', 4, { 'SwitchCase': 1 }],
            'semi': ['error', 'always'],
            'no-trailing-spaces': 'error',
            'no-multiple-empty-lines': ['error', { 'max': 2 }],
            'max-len': ['error', { 'code': 120, 'ignoreUrls': true, 'ignoreRegExpLiterals': true }],

            // Best practices
            'strict': ['error', 'global'],
            'no-implied-eval': 'error',
            'no-new-func': 'error'
        }
    }
];
