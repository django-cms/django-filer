import {build} from 'esbuild';
import svgr from 'esbuild-plugin-svgr';
import license from 'esbuild-plugin-license';
import parser from 'yargs-parser';

const buildOptions = parser(process.argv.slice(2), {
  boolean: ['debug', 'minify'],
});

await build({
  entryPoints: [
    'client/finder-select.ts',
    'client/folder-admin.tsx',
    'client/file-admin.tsx',
    'client/components/browser/*.tsx',
    'client/components/editor/*.tsx',
    'client/components/folderitem/*.tsx',
    'client/components/menuextension/*.tsx',
  ],
  bundle: true,
  minify: buildOptions.minify,
  sourcemap: buildOptions.debug,
  outdir: 'finder/static/finder/js',
  splitting: true,
  format: 'esm',
  jsx: 'automatic',
  plugins: [
    svgr(),
    license({
      thirdParty: {
        output: {
          file: 'LICENSES.txt',
          template(dependencies) {
            return dependencies.map(dep =>
              `${dep.packageJson.name}@${dep.packageJson.version}\nLicense: ${dep.packageJson.license}\n${dep.licenseText || 'No license text available.'}`
            ).join('\n\n---\n\n');
          },
        },
      },
    }),
  ],
  loader: {'.svg': 'text', '.jsx': 'jsx' },
  target: ['es2022', 'chrome100', 'firefox100', 'safari15', 'edge100']
}).catch(() => process.exit(1));
