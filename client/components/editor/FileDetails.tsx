import React, {forwardRef, useContext, useImperativeHandle, useMemo, useRef, useState} from 'react';
import {ProgressBar, ProgressOverlay} from 'finder/UploadProgress';
import {FinderSettings} from 'finder/FinderSettings';
import DownloadIcon from 'icons/download.svg';
import FullSizeIcon from 'icons/full-size.svg';
import UploadIcon from 'icons/upload.svg';


export function DownloadFileButton(props) {
	const settings = useContext(FinderSettings);

	return (
		<a download={settings.filename} href={settings.download_url}><DownloadIcon/>{gettext("Download")}</a>
	);
}


export function ViewOriginalButton() {
	const settings = useContext(FinderSettings);

	function viewOriginal() {
		window.open(settings.download_url, '_blank').focus();
	}

	return (
		<button onClick={viewOriginal}><FullSizeIcon/>{gettext("View Original")}</button>
	);
}


export const ReplaceFileButton = forwardRef((props, forwardedRef) => {
	const settings = useContext(FinderSettings);
	const inputRef = useRef(null);
	const [uploadFile, setUploadFile] = useState<Promise<Response>>(null);
	useImperativeHandle(forwardedRef, () => ({uploadFile}));

	function replaceFile() {
		inputRef.current.click();
	}

	function handleFileSelect(event) {
		const file = event.target.files[0];
		const promise = new Promise<Response>((resolve, reject) => {
			file.resolve = resolve;
			file.reject = reject;
		});
		setUploadFile(file);
		promise.then((response) => {
			window.location.reload();
		}).catch((error) => {
			alert(error);
		}).finally( () => {
			setUploadFile(null);
		});
	}

	return (<>
		<button onClick={replaceFile}><UploadIcon/>{gettext("Replace File")}</button>
		<input type="file" name="replaceFile" ref={inputRef} accept={settings.file_mime_type} onChange={handleFileSelect} />
	</>);
});


export default function FileDetails(props) {
	const settings = useContext(FinderSettings);
	const [uploadFile, setUploadFile] = useState<Promise<Response>>(null);
	const replaceRef = useRef(null);
	const subtitle = useMemo(
		() => {
			const subtitle = document.getElementById('id_subtitle');
			if (subtitle) {
				subtitle.remove();
				return subtitle.innerHTML;
			}
			return '';
		},
		[]
	);

	// function viewOriginal() {
	// 	window.open(settings.download_url, '_blank').focus();
	// }
	//
	// function replaceFile() {
	// 	inputRef.current.click();
	// }
	//
	function handleFileSelect(event) {
		const file = event.target.files[0];
		const promise = new Promise<Response>((resolve, reject) => {
			file.resolve = resolve;
			file.reject = reject;
		});
		setUploadFile(file);
		promise.then((response) => {
			window.location.reload();
		}).catch((error) => {
			alert(error);
		}).finally( () => {
			setUploadFile(null);
		});
	}

	return (<>
		<div className="file-details">
			<h2>{subtitle}</h2>
			{props.children}
			<div className="button-group">
				<DownloadFileButton />
				<ViewOriginalButton />
				<ReplaceFileButton ref={replaceRef} />
			</div>
		</div>
		{uploadFile &&
		<ProgressOverlay>
			<ProgressBar file={uploadFile} targetId={settings.file_id} />
		</ProgressOverlay>
		}
	</>);
}
