import React, {useEffect, useRef, useState} from 'react';
import FileSelectDialog from './FileSelectDialog';


interface SelectedFile {
	id: string;
	name: string;
	file_name: string;
	file_size: number;
	sha1: string;
	mime_type: string;
	last_modified_at: string;
	summary: string;
	download_url: string;
	thumbnail_url: string;
	labels: string[];
}

function parseDataset(dataset: string|object) : SelectedFile {
	const data = typeof dataset === 'string' ? JSON.parse(dataset) : dataset;
	const {id, name, file_name, file_size, sha1, mime_type, last_modified_at, summary, download_url, thumbnail_url, labels} = data;
	return {id, name, file_name, file_size, sha1, mime_type, last_modified_at, summary, download_url, thumbnail_url, labels};
}


export default function FinderFileSelect(props) {
	const shadowRoot = props.container;
	const baseUrl = props['base-url'];
	const styleUrl = props['style-url'];
	const mimeTypes = props['mime-types'] ? props['mime-types'].split(',') : [];
	const selectRef = useRef(null);
	const slotRef = useRef(null);
	const dialogRef = useRef(null);
	const [selectedFile, setSelectedFile] = useState<SelectedFile>(null);
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
			setSelectedFile(parseDataset(inputElement.dataset.selected_file));
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
		const fileId = event.target.value;
		if (!uuid5Regex.test(fileId)) {
			setSelectedFile(null);
			return;
		}
		const response = await fetch(`${baseUrl}${fileId}/fetch`);
		if (response.ok) {
			const dataset = parseDataset(await response.json());
			const inputElement = slotRef.current.assignedElements()[0];
			if (inputElement instanceof HTMLInputElement) {
				inputElement.dataset.selected_file = JSON.stringify(dataset);
			}
			setSelectedFile(dataset);
		} else {
			console.error(`Failed to fetch file info for ID ${fileId}:`, response.statusText);
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

	function removeFile() {
		setSelectedFile(null);
		const inputElement = slotRef.current.assignedElements()[0];
		if (inputElement instanceof HTMLInputElement) {
			inputElement.value = '';
		}
	}

	function selectFile(file) {
		if (file) {
			setSelectedFile(file);
			const inputElement = slotRef.current.assignedElements()[0];
			if (inputElement instanceof HTMLInputElement) {
				inputElement.value = file.id;
				inputElement.dataset.selected_file = JSON.stringify(parseDataset(file));
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
			<figure>{selectedFile ? <>
				<img src={selectedFile.thumbnail_url} onClick={openDialog} onDragEnter={openDialog} />
				<figcaption>
					<dl>
						<dt>{gettext("Name")}:</dt>
						<dd>{selectedFile.name}</dd>
					</dl>
					<dl>
						<dt>{gettext("Details")}:</dt>
						<dd>{selectedFile.summary}</dd>
					</dl>
					<dl>
						<dt>{gettext("Modified at")}:</dt>
						<dd>{renderTimestamp(selectedFile.last_modified_at)}</dd>
					</dl>
					<dl>
						<dt>{gettext("Content-Type")}:</dt>
						<dd>{selectedFile.mime_type}</dd>
					</dl>
					<button className="remove-file-button" type="button" onClick={removeFile}>{gettext("Remove")}</button>
				</figcaption>
			</> :
				<span onClick={openDialog} onDragEnter={openDialog}>
					<p>{gettext("Select File")}</p>
				</span>
			}</figure>
		</div>
		<dialog ref={dialogRef}>
			<FileSelectDialog
				ref={selectRef}
				realm={props.realm}
				baseUrl={baseUrl}
				mimeTypes={mimeTypes}
				csrfToken={csrfToken}
				selectFile={selectFile}
				dialogRef={dialogRef}
			/>
		</dialog>
	</>);
}
