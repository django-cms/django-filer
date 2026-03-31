import * as sass from 'sass';
import * as fs from 'fs';
import * as path from 'path';
import {fileURLToPath} from 'url';
import parser from 'yargs-parser';

const baseDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const scssInputDir = path.join(baseDir, 'client/scss');
const cssOutputDir = path.join(baseDir, 'finder/static/finder/css');

export function compileSass(debug = false) {
	fs.mkdirSync(cssOutputDir, {recursive: true});
	for (const file of fs.readdirSync(scssInputDir).filter(f => f.endsWith('.scss') && !f.startsWith('_'))) {
		const result = sass.compile(path.join(scssInputDir, file), {
			loadPaths: [baseDir],
			style: debug ? 'expanded' : 'compressed',
			sourceMap: debug,
			sourceMapIncludeSources: debug,
		});
		const outFile = path.join(cssOutputDir, file.replace('.scss', '.css'));
		fs.writeFileSync(outFile, result.css);
		if (debug && result.sourceMap) {
			const mapFile = outFile + '.map';
			fs.writeFileSync(mapFile, JSON.stringify(result.sourceMap));
			fs.appendFileSync(outFile, `\n/*# sourceMappingURL=${path.basename(mapFile)} */\n`);
		}
		console.log(`sass: ${file} → ${outFile}`);
	}
}

// Allow running standalone: node assets/sass.config.mjs [--debug]
if (process.argv[1] === fileURLToPath(import.meta.url)) {
	const buildOptions = parser(process.argv.slice(2), {boolean: ['debug']});
	compileSass(buildOptions.debug);
}
