import React, {forwardRef, useImperativeHandle, useRef, useState} from 'react';
import {ProgressOverlay, ProgressBar} from './UploadProgress';


const FileUploader = forwardRef(function FileUploader(props: any, forwardedRef) {
	const {folderId, disabled, handleUpload} = props;
	const mimeTypes = props.mimeTypes ?? [];
	const multiple = 'multiple' in props;
	const fileUploadRef = useRef(null);
	const folderUploadRef = useRef(null);
	const [dragging, setDragging] = useState(false);
	const [uploading, setUploading] = useState([]);

	useImperativeHandle(forwardedRef, () => ({
		openUploader(isFolder?: boolean) {
			(isFolder === true ? folderUploadRef : fileUploadRef).current.click();
		},
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
		if (disabled)
			return;
		const matchesMimeType = (fileType: string) => mimeTypes.some(
			allowed => allowed === fileType || (allowed.endsWith('/*') && fileType.startsWith(allowed.slice(0, -1)))
		);
		const filteredFiles = Array.from(files).filter(
			file => mimeTypes.length === 0 || matchesMimeType(file.type)
		);
		if (filteredFiles.length === 0)
			return;
		const uploadFile = file => new Promise<Response>((resolve, reject) => {
			file.resolve = resolve;
			file.reject = reject;
		});
		const promises: Array<Promise<Response>> = [];
		for (const file of filteredFiles) {
			promises.push(uploadFile(file));
		}
		setUploading([...uploading, ...filteredFiles]);
		Promise.all(promises).then(responses => {
			handleUpload(folderId, responses);
		}).catch((error) => {
			alert(gettext("An error occurred during file upload."));
			console.error(error);
		}).finally(() => {
			setUploading([]);
		});
	}

	const directory = {directory: '', webkitdirectory: '', mozdirectory: ''};
	const accept = mimeTypes.length > 0 ? mimeTypes.join(',') : undefined;

	return (
		<div
			className="file-uploader"
			onDragEnter={handleDragEnter}
			onDragOver={swallowEvent}
			onDragLeave={handleDragLeave}
			onDrop={handleDrop}
		>
			{props.children}
			<input type="file" name={`file:${folderId}`} multiple={multiple} accept={accept} ref={fileUploadRef} onChange={handleFileSelect} />
			{multiple && <input type="file" name={`folder:${folderId}`} accept={accept} {...directory} ref={folderUploadRef} onChange={handleFileSelect}/>}
			{(dragging || uploading.length > 0) && (
			disabled ?
			<div className="progress-overlay">
				<div className="progress-indicator">
					<p>{gettext("You don't have permission to upload files to this folder.")}</p>
				</div>
			</div>
			:
			<ProgressOverlay dragging={dragging}>{
				uploading.map((file, index) =>
					<ProgressBar key={index} file={file} targetId={folderId} settings={props.settings} />
				)
			}</ProgressOverlay>
			)
		}</div>
	)
});


export default FileUploader;
