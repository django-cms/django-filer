import React, {useContext, useMemo, useRef, useState} from 'react';
import {ProgressBar, ProgressOverlay} from '../UploadProgress';
import {FinderSettings} from '../FinderSettings';
import DownloadIcon from '../icons/download.svg';
import FullSizeIcon from '../icons/full-size.svg';
import UploadIcon from '../icons/upload.svg';


export function FileDetails(props) {
	const settings = useContext(FinderSettings);
	const [uploadFile, setUploadFile] = useState<Promise<Response>>(null);
	const downloadLinkRef = useRef(null);
	const inputRef = useRef(null);
	const subtitle = useMemo(
		() => {
			const subtitle = document.getElementById('id_subtitle');
			subtitle.remove();
			return subtitle.innerHTML;
		},
		[]
	);

	function viewOriginal() {
		window.open(settings.download_url, '_blank').focus();
	}

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
		<div className="file-details">
			<h2>{subtitle}</h2>
			{props.children}
			<div className="button-group">
				<a download={settings.filename} href={settings.download_url}><DownloadIcon/>{gettext("Download")}</a>
				<button onClick={viewOriginal}><FullSizeIcon/>{gettext("View Original")}</button>
				<button onClick={replaceFile}><UploadIcon/>{gettext("Replace File")}</button>
			</div>
			<a ref={downloadLinkRef} download="download" hidden />
			<input type="file" name="replaceFile" ref={inputRef} accept={settings.file_mime_type} onChange={handleFileSelect} />
		</div>
		{uploadFile &&
		<ProgressOverlay>
			<ProgressBar file={uploadFile} targetId={settings.file_id} />
		</ProgressOverlay>
		}
	</>);
}


export default function Common(props) {
	const settings = useContext(FinderSettings);

	return props.editorRef ? (
		<FileDetails>
			<img src={settings.thumbnail_url} />
		</FileDetails>
	) : (
		<>{props.children}</>
	);
}
