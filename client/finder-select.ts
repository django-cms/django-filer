import r2wc from '@r2wc/react-to-web-component';
import FinderFileSelect from './browser/FinderFileSelect';
import FinderFolderSelect from './browser/FinderFolderSelect';


window.addEventListener('DOMContentLoaded', (event) => {
	window.customElements.define(
		'finder-file-select',
		r2wc(FinderFileSelect, {
			props: {'base-url': 'string', 'style-url': 'string', ambit: 'string', 'mime-types': 'string'},
			shadow: 'open',
		}),
	);
	window.customElements.define(
		'finder-folder-select',
		r2wc(FinderFolderSelect, {
			props: {'base-url': 'string', 'style-url': 'string', ambit: 'string', 'folder-icon-url': 'string'},
			shadow: 'open',
		}),
	);
});
