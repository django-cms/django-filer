import React, {forwardRef, useContext, useEffect, useImperativeHandle, useRef, useState} from 'react';
import {FinderSettings} from './FinderSettings';


function ProgressOverlay(props) {
	return (
		<div className="progress-overlay">
			<div className="progress-indicator">{
			props.dragging ? (
				<p>Drop files here</p>
			) : (<>
				<p>Uploading:</p>
				<ul className="progress-bar">
				{props.children}
				</ul>
			</>)
			}</div>
		</div>
	);
}


function ProgressBar(props) {
	const settings = useContext(FinderSettings);
	const {file, folderId} = props;
	const [complete, setComplete] = useState(0);

	useEffect(() => {
		const uploadFilesURL = `${settings.base_url}${folderId}/upload`;
		const request = new XMLHttpRequest();
		request.addEventListener('loadstart', transferStart);
		request.upload.addEventListener('progress', transferProgress, false);
		request.addEventListener('loadend', transferComplete);
		request.open('POST', uploadFilesURL, true);
		request.setRequestHeader('X-CSRFToken', settings.csrf_token);
		request.responseType = 'json';
		const body = new FormData();
		body.append('upload_file', file);
		request.send(body);

		return () => {
			request.removeEventListener('loadstart', transferStart);
			request.removeEventListener('progress', transferProgress);
			request.removeEventListener('loadend', transferComplete);
		};
	}, [file]);

	function transferStart() {
		setComplete(0);
	}

	function transferProgress(event: ProgressEvent) {
		if (event.lengthComputable) {
			setComplete(event.loaded / event.total * 0.98);
		}
	}

	function transferComplete(event: ProgressEvent) {
		if (event.lengthComputable) {
			setComplete(1);
		}
		const request = event.target as XMLHttpRequest;
		if (request.status === 200) {
			file.resolve(request.response);
		} else {
			file.reject(request.response);
		}
	}

	return (
		<li>
			<span>{file.name}:</span>
			<progress value={complete} max="1"></progress>
		</li>
	);
}


export const FileUploader = forwardRef((props: any, forwardedRef) => {
	const settings = useContext(FinderSettings);
	const {folderId, handleUpload} = props;
	const inputRef = useRef(null);
	const [dragging, setDragging] = useState(false);
	const [uploading, setUploading] = useState([]);

	useImperativeHandle(forwardedRef, () => ({
		openUploader() {
			inputRef.current.click()
		}
	}));

	function swallowEvent(event) {
		event.stopPropagation();
		event.preventDefault();
	}

	function handleDragEnter(event) {
		swallowEvent(event);
		setDragging(true);
	}

	function handleDragLeave(event) {
		swallowEvent(event);
		const {relatedTarget} = event;
		if (!relatedTarget || !event.currentTarget.contains(relatedTarget)) {
			setDragging(false);
		}
	}

	function handleDrop(event) {
		swallowEvent(event);
		setDragging(false);
		if (event.dataTransfer) {
			uploadFiles(event.dataTransfer.files);
		}
	}

	function handleFileSelect(event) {
		uploadFiles(event.target.files);
	}

	function uploadFiles(files: FileList) {
		const promises: Array<Promise<Response>> = [];
		for (let k = 0; k < files.length; k++) {
			promises.push(uploadFile(files.item(k)));
		}
		setUploading([...uploading, ...files]);
		Promise.all(promises).catch((error) => {
			alert(error);
		}).finally( () => {
			setUploading([]);
			handleUpload(folderId);
		});
	}

	function uploadFile(file) {
		return new Promise<Response>((resolve, reject) => {
			file.resolve = resolve;
			file.reject = reject;
		});
	}

	return (
		<div className="file-uploader" onDragEnter={handleDragEnter} onDragOver={swallowEvent} onDragLeave={handleDragLeave} onDrop={handleDrop}>
			{props.children}
			<input type="file" name={`file:${folderId}`} multiple ref={inputRef} onChange={handleFileSelect} />
			{dragging || uploading.length > 0 ? (
			<ProgressOverlay dragging={dragging}>{
			uploading.map((file, index) =>
				<ProgressBar key={index} file={file} folderId={folderId} />
			)
			}</ProgressOverlay>
			) : null}
		</div>
	)
});
