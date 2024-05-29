import {createRoot} from 'react-dom/client';
import React from 'react';
import {FinderSettings} from 'finder/FinderSettings';


export default function loadFinderAdmin(children: React.ReactNode) {
	window.addEventListener('DOMContentLoaded', () => {
		const reactContent = document.getElementById('content-react');
		const mainContent = document.getElementById('content-main');
		const settings = JSON.parse(document.getElementById('finder-settings').textContent);
		settings.workAreaRect = reactContent.getBoundingClientRect();
		if (mainContent) {
			settings.mainContent = mainContent;
			mainContent.remove();
		}
		createRoot(reactContent).render(<FinderSettings.Provider value={settings}>{children}</FinderSettings.Provider>);

		// prevent browser from loading a drag-and-dropped file
		window.addEventListener('dragover', function (event) {
			event.preventDefault();
		}, false);
		window.addEventListener('drop', function (event) {
			event.preventDefault();
		}, false);
	});
}
