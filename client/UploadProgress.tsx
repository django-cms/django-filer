import React, {useContext, useEffect, useState} from 'react';
import {FinderSettings} from './FinderSettings';


export function ProgressOverlay(props) {
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


export function ProgressBar(props) {
	const settings = useContext(FinderSettings);
	const {file, targetId} = props;
	const [complete, setComplete] = useState(0);

	useEffect(() => {
		const uploadFilesURL = `${settings.base_url}${targetId}/upload`;
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
