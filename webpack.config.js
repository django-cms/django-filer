const path = require('path');
const fs = require('fs');

module.exports = (env, argv) => {
    const isDebug = argv.debug || false;
    const mode = isDebug ? 'development' : 'production';

    return {
        mode: mode,
        entry: {
            // Admin file widget bundle - for Django admin file fields
            'admin-file-widget': [
                './filer/static/filer/js/addons/dropzone.init.js',
                './filer/static/filer/js/addons/popup_handling.js',
                './filer/static/filer/js/addons/widget.js',
                './filer/static/filer/js/widgets/admin-file-widget.js',
                './filer/static/filer/js/widgets/admin-folder-widget.js'
            ],
            // Base site bundle - for filer directory listing pages
            'filer-base': [
                './filer/static/filer/js/addons/dropdown-menu.js',
                './filer/static/filer/js/addons/popup_handling.js',
                './filer/static/filer/js/addons/table-dropzone.js',
                './filer/static/filer/js/addons/upload-button.js',
                './filer/static/filer/js/addons/tooltip.js',
                './filer/static/filer/js/base.js',
            ],
        },
        output: {
            filename: '[name].bundle.js',
            path: path.resolve(__dirname, 'filer/static/filer/js/dist'),
            clean: true, // Clean the output directory before emit
        },
        devtool: isDebug ? 'source-map' : false,
        optimization: {
            minimize: !isDebug,
            minimizer: !isDebug ? [
                new (require('terser-webpack-plugin'))({
                    extractComments: false, // Disable automatic LICENSE.txt extraction
                })
            ] : [],
        },
        resolve: {
            fallback: {
                "process": false,
                "util": false
            }
        },
        plugins: [
            new (require('webpack')).DefinePlugin({
                'process.env.NODE_ENV': JSON.stringify(mode)
            }),
            // Custom plugin to extract third-party licenses
            {
                apply: (compiler) => {
                    compiler.hooks.afterEmit.tap('LicenseExtractor', () => {
                        const licenses = [];

                        // Read Dropzone license
                        try {
                            const dropzoneLicense = fs.readFileSync(
                                path.resolve(__dirname, 'node_modules/dropzone/LICENSE'),
                                'utf8'
                            );
                            licenses.push('/*!\n * Dropzone.js\n * https://www.dropzonejs.com/\n */\n' + dropzoneLicense);
                        } catch (e) {
                            console.warn('Could not read Dropzone license');
                        }

                        // Read Mediator.js license (already in bundle, but include for completeness)
                        try {
                            const mediatorLicense = fs.readFileSync(
                                path.resolve(__dirname, 'node_modules/mediator-js/LICENSE.md'),
                                'utf8'
                            );
                            licenses.push('\n\n/*!\n * Mediator.js\n * https://github.com/ajacksified/Mediator.js\n */\n' + mediatorLicense);
                        } catch (e) {
                            console.warn('Could not read Mediator.js license');
                        }

                        // Write combined license file
                        if (licenses.length > 0) {
                            const outputPath = path.resolve(__dirname, 'filer/static/filer/js/dist/LICENSES.txt');
                            fs.writeFileSync(outputPath, licenses.join('\n\n'));
                        }
                    });
                }
            }
        ],
        module: {
            rules: [
                {
                    test: /\.js$/,
                    exclude: /node_modules/,
                    use: {
                        loader: 'babel-loader',
                        options: {
                            presets: [
                                ['@babel/preset-env', {
                                    targets: '> 0.5%, last 2 versions, not dead'
                                }]
                            ]
                        }
                    }
                }
            ]
        },
        stats: {
            colors: true,
            modules: false,
            children: false,
            chunks: false,
            chunkModules: false
        }
    };
};
