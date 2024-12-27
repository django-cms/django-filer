import React, {useEffect, useRef, useState} from 'react';
import FileSelectDialog from './FileSelectDialog';
import {Tooltip} from 'react-tooltip';


export default function FinderFileSelect(props) {
	const shadowRoot = props.container;
	const baseUrl = props['base-url'];
	const styleUrl = props['style-url'];
	const [selectedFile, setSelectedFile] = useState(props['selected-file']);
	const selectRef = useRef(null);
	const slotRef = useRef(null);
	const dialogRef = useRef(null);
	const csrfToken = shadowRoot.host.closest('form')?.querySelector('input[name="csrfmiddlewaretoken"]')?.value;

	useEffect(() => {
		// Create a styles element for the shadow DOM
		const link = document.createElement('link');
		link.href = styleUrl;
		link.media = 'all';
		link.rel = 'stylesheet';
		shadowRoot.insertBefore(link, shadowRoot.firstChild);
	}, []);

	useEffect(() => {
		const handleEscape = (event) => {
			if (event.key === 'Escape') {
				selectRef.current.dismissAndClose();
			}
		};
		const preventDefault = (event) => {
			event.preventDefault();
		}
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
			}
		}
	}

	function renderTimestamp(timestamp) {
		const date = new Date(timestamp);
		return date.toLocaleString();
	}

	console.log('FinderFileSelect', selectedFile);

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
				csrfToken={csrfToken}
				selectFile={selectFile}
				closeDialog={() => dialogRef.current.close()}
			/>
		</dialog>
		<Tooltip id="django-finder-tooltip" place="bottom-start" />
	</>);
}
