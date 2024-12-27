import React, {createRef, useEffect, useState} from 'react';


export function ProgressOverlay(props) {
	return (
		<div className="progress-overlay">
			<div className="progress-indicator">{
			props.dragging ? (
				<p>{gettext("Drop files here")}</p>
			) : (<>
				<p>{gettext("Uploading")}:</p>
				<ul className="progress-bar">{props.children}</ul>
			</>)
			}</div>
		</div>
	);
}


export function ProgressBar(props) {
	const {file, settings, targetId} = props;
	const [complete, setComplete] = useState(0);

	useEffect(() => {
		(async () => {
			let uploadFilesURL = `${settings.base_url}${targetId}/upload`;
			let relativePath = file.webkitRelativePath ?? file.mozRelativePath ?? file.relativePath;
			if (typeof relativePath === 'string') {
				relativePath = relativePath.slice(0, relativePath.lastIndexOf('/'));
				if (relativePath.length > 0) {
					const folder = await getOrCreateFolder(relativePath);
					uploadFilesURL = `${settings.base_url}${folder.id}/upload`;
				}
			}
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
		})();
	}, [file]);

	async function getOrCreateFolder(relativePath: string) {
		const fetchUrl = `${settings.base_url}${settings.folder_id}/get_or_create_folder`;
		const response = await fetch(fetchUrl, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': settings.csrf_token,
			},
			body: JSON.stringify({
				relative_path: relativePath,
			}),
		});
		if (response.ok) {
			const body = await response.json();
			return body.folder;
		} else {
			console.error(response);
		}
	}

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
