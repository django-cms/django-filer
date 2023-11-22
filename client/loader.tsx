import {createRoot} from 'react-dom/client';
import React from 'react';
import {FinderSettings} from './FinderSettings';


export default function loadFinderAdmin(children: React.ReactNode) {
	window.addEventListener('DOMContentLoaded', () => {
		const content = document.getElementById('content');
		const settings = JSON.parse(document.getElementById('finder-settings').textContent);
		settings.workAreaRect = content.getBoundingClientRect();
		createRoot(content).render(<FinderSettings.Provider value={settings}>{children}</FinderSettings.Provider>);

		// prevent browser from loading a drag-and-dropped file
		window.addEventListener('dragover', function (event) {
			event.preventDefault();
		}, false);
		window.addEventListener('drop', function (event) {
			event.preventDefault();
		}, false);
	});
}
