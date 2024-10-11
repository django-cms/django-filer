import {build} from 'esbuild';
import svgr from 'esbuild-plugin-svgr';
import parser from 'yargs-parser';
const buildOptions = parser(process.argv.slice(2), {
  boolean: ['debug', 'minify'],
});

await build({
  entryPoints: [
    'client/folder-admin.tsx',
    'client/file-admin.tsx',
    'client/components/editor/*.tsx',
    'client/components/folderitem/*.tsx',
    'client/components/menuextension/*.tsx',
  ],
  bundle: true,
  minify: buildOptions.minify,
  sourcemap: buildOptions.debug,
  outdir: 'finder/static/finder/js/admin',
  splitting: true,
  format: 'esm',
  jsx: 'automatic',
  plugins: [svgr()],
  loader: {'.svg': 'text', '.jsx': 'jsx' },
  target: ['es2020', 'chrome84', 'firefox84', 'safari14', 'edge84']
}).catch(() => process.exit(1));
