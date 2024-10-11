import {build} from 'esbuild';
import svgr from 'esbuild-plugin-svgr';
import parser from 'yargs-parser';
const buildOptions = parser(process.argv.slice(2), {
  boolean: ['debug', 'minify'],
});

await build({
  entryPoints: [
    'client/finder-browser.ts',
  ],
  bundle: true,
  minify: buildOptions.minify,
  sourcemap: buildOptions.debug,
  outfile: 'finder/static/finder/js/browser.js',
  format: 'esm',
  jsx: 'automatic',
  plugins: [svgr()],
  loader: {'.svg': 'text', '.jsx': 'jsx' },
  target: ['es2020', 'chrome84', 'firefox84', 'safari14', 'edge84']
}).catch(() => process.exit(1));
