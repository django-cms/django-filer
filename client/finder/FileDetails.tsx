import React, {Fragment, useContext, useMemo, useRef, useState} from 'react';
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


export function ReplaceFileButton(props) {
	const {acceptMimeType} = props;
	const inputRef = useRef(null);

	function replaceFile() {
		inputRef.current.click();
	}

	function handleFileSelect(event) {
		const file = event.target.files[0];
		const promise = new Promise<Response>((resolve, reject) => {
			file.resolve = resolve;
			file.reject = reject;
		});
		props.setUploadFile(file);
		promise.then((response) => {
			window.location.reload();
		}).catch((error) => {
			alert(error);
		}).finally( () => {
			props.setUploadFile(null);
		});
	}

	return (<>
		<button onClick={replaceFile}><UploadIcon/>{gettext("Replace File")}</button>
		<input type="file" name="replaceFile" ref={inputRef} accept={acceptMimeType} onChange={handleFileSelect} />
	</>);
}


export function FileDetails(props) {
	const settings = useContext(FinderSettings);
	const controlButtons: Array<React.JSX.Element> = [...(props.controlButtons ?? [])];
	const [uploadFile, setUploadFile] = useState<Promise<Response>>(null);
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
	if (settings.download_url) {
		controlButtons.push(<DownloadFileButton />);
	}
	if (settings.original_url) {
		controlButtons.push(<ViewOriginalButton />);
	}
	if (settings.replacing_mime_type) {
		controlButtons.push(<ReplaceFileButton setUploadFile={setUploadFile} acceptMimeType={settings.replacing_mime_type} />);
	}

	return (<>
		<div className="file-details" style={props.style}>
			<h2>{subtitle}</h2>
			{props.children}
			<div className="button-group">{controlButtons.map((button, index) =>
				<Fragment key={index}>{button}</Fragment>
			)}</div>
		</div>
		{uploadFile &&
		<ProgressOverlay>
			<ProgressBar file={uploadFile} targetId={settings.file_id} />
		</ProgressOverlay>
		}
	</>);
}
