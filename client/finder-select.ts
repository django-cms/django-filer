import r2wc from '@r2wc/react-to-web-component';
import FinderFileSelect from 'browser/FinderFileSelect';


window.addEventListener('DOMContentLoaded', (event) => {
	window.customElements.define(
		'finder-file-select',
		r2wc(FinderFileSelect, {
			props: {'base-url': 'string', 'selected-file': 'json', 'style-url': 'string', realm: 'string'},
			shadow: 'closed',
		}),
	);
});
