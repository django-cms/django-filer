const { build } = require('esbuild');
const svgr = require('esbuild-plugin-svgr');
const buildOptions = require('yargs-parser')(process.argv.slice(2), {
  boolean: ['debug'],
});

build({
  entryPoints: ['client/folder-admin.tsx', 'client/file-admin.tsx'],
  bundle: true,
  minify: !buildOptions.debug,
  sourcemap: buildOptions.debug,
  outdir: 'finder/static/admin/finder/js',
  splitting: false,
  format: 'esm',
  jsx: 'automatic',
  plugins: [svgr()],
  loader: {'.svg': 'text', '.jsx': 'jsx' },
  target: ['es2020', 'chrome84', 'firefox84', 'safari14', 'edge84']
}).catch(() => process.exit(1));
