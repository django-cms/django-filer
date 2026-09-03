import {defineConfig} from 'vitest/config';

export default defineConfig({
	test: {
		include: ['client/**/*.test.{ts,tsx}'],
		environment: 'node',
		coverage: {
			provider: 'v8',
			include: ['client/**/*.{ts,tsx}'],
			exclude: ['client/**/*.test.{ts,tsx}'],
			reporter: ['text', 'lcov'],
			reportsDirectory: 'workdir/coverage/client',
		},
	},
});
