import React, {useEffect, useRef, useState} from 'react';
import FileSelectDialog from './FileSelectDialog';


interface SelectedFolder {
	id: string;
	name: string;
	last_modified_at: string;
	summary: string;
	meta_data: object;
}

function parseDataset(dataset: string|object) : SelectedFolder|null {
	const data = typeof dataset === 'string' ? JSON.parse(dataset) : dataset;
	if (data) {
		const {
			id,
			name,
			last_modified_at,
			summary,
			meta_data,
		} = data;
		return {
			id,
			name,
			last_modified_at,
			summary,
			meta_data,
		} as SelectedFolder;
	}
	return null;
}


export default function FinderFolderSelect(props) {
	const shadowRoot = props.container;
	const baseUrl = props['base-url'];
	const styleUrl = props['style-url'];
	const folderIconUrl = props['folder-icon-url'];
	const selectRef = useRef(null);
	const slotRef = useRef(null);
	const dialogRef = useRef(null);
	const [selectedFolder, setSelectedFolder] = useState<SelectedFolder>(null);
	const csrfToken = getCSRFToken();
	const uuid5Regex = new RegExp(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);

	useEffect(() => {
		// Create a styles element for the shadow DOM
		const link = document.createElement('link');
		link.href = styleUrl;
		link.media = 'all';
		link.rel = 'stylesheet';
		shadowRoot.insertBefore(link, shadowRoot.firstChild);
		const inputElement = slotRef.current.assignedElements()[0];
		if (inputElement instanceof HTMLInputElement) {
			setSelectedFolder(parseDataset(inputElement.dataset.selected_folder));
			inputElement.addEventListener('change', valueChanged);
		}
		return () => {
			inputElement.removeEventListener('change', valueChanged);
		};
	}, []);

	useEffect(() => {
		const handleEscape = (event) => {
			if (event.key === 'Escape') {
				selectRef.current.dismissAndClose();
			}
		};
		const preventDefault = (event) => {
			event.preventDefault();
		};
		window.addEventListener('keydown', handleEscape);

		// prevent browser from loading a drag-and-dropped file
		window.addEventListener('dragover', preventDefault, false);
		window.addEventListener('drop', preventDefault, false);

		return () => {
			window.removeEventListener('keydown', handleEscape);
			window.removeEventListener('dragover', preventDefault);
			window.removeEventListener('drop', preventDefault);
		}
	}, []);

	async function valueChanged(event) {
		const folderId = event.target.value;
		if (!uuid5Regex.test(folderId)) {
			setSelectedFolder(null);
			return;
		}
		const response = await fetch(`${baseUrl}${folderId}/fetch`);
		if (response.ok) {
			const dataset = parseDataset(await response.json());
			const inputElement = slotRef.current.assignedElements()[0];
			if (inputElement instanceof HTMLInputElement) {
				inputElement.dataset.selected_file = JSON.stringify(dataset);
			}
			setSelectedFolder(dataset);
		} else {
			console.error(`Failed to fetch folder info for ID ${folderId}:`, response.statusText);
		}
	}

	function getCSRFToken() {
		const csrfToken = shadowRoot.host.closest('form')?.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
		if (csrfToken)
			return csrfToken;
		const parts = `; ${document.cookie}`.split('; csrftoken=');
		if (parts.length === 2)
			return parts.pop().split(';').shift();
	}

	function openDialog() {
		dialogRef.current.showModal();
		selectRef.current.scrollToCurrentFolder();
	}

	function removeFolder() {
		setSelectedFolder(null);
		const inputElement = slotRef.current.assignedElements()[0];
		if (inputElement instanceof HTMLInputElement) {
			inputElement.value = '';
			inputElement.dataset.selected_file = null;
			inputElement.checkValidity();
		}
	}

	function selectFolder(folder) {
		if (folder) {
			setSelectedFolder(folder);
			const inputElement = slotRef.current.assignedElements()[0];
			if (inputElement instanceof HTMLInputElement) {
				inputElement.value = folder.id;
				inputElement.dataset.selected_folder = JSON.stringify(parseDataset(folder));
				inputElement.checkValidity();
			}
		}
	}

	function renderTimestamp(timestamp) {
		const date = new Date(timestamp);
		return date.toLocaleString();
	}

	return (<>
		<slot ref={slotRef} />
		<div className="finder-file-select">
			<figure>{selectedFolder ? <>
				<img src={folderIconUrl} onClick={openDialog} onDragEnter={openDialog} />
				<figcaption>
					<dl>
						<dt>{gettext("Name")}:</dt>
						<dd>{selectedFolder.name}</dd>
					</dl>
					<dl>
						<dt>{gettext("Details")}:</dt>
						<dd>{selectedFolder.summary}</dd>
					</dl>
					<dl>
						<dt>{gettext("Modified at")}:</dt>
						<dd>{renderTimestamp(selectedFolder.last_modified_at)}</dd>
					</dl>
					<button className="remove-file-button" type="button" onClick={removeFolder}>{gettext("Remove")}</button>
				</figcaption>
			</> :
				<span onClick={openDialog} onDragEnter={openDialog}>
					<p>{gettext("Select Folder")}</p>
				</span>
			}</figure>
		</div>
		<dialog ref={dialogRef}>
			<FileSelectDialog
				ref={selectRef}
				realm={props.realm}
				baseUrl={baseUrl}
				csrfToken={csrfToken}
				selectFolder={selectFolder}
				dialogRef={dialogRef}
			/>
		</dialog>
	</>);
}
