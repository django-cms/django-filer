import React, {Fragment, ReactElement, useMemo, useRef} from 'react';
import DownloadIcon from '../icons/download.svg';
import FullSizeIcon from '../icons/full-size.svg';
import UploadIcon from '../icons/upload.svg';


function DownloadFileButton(props) {
	const {settings} = props;

	return (
		<a download={settings.filename} href={settings.download_url}>
			<DownloadIcon/>{gettext("Download")}
		</a>
	);
}


function ViewOriginalButton(props) {
	const {settings} = props;

	function viewOriginal() {
		window.open(settings.download_url, '_blank').focus();
	}

	return (
		<button type="button" onClick={viewOriginal}>
			<FullSizeIcon/>{gettext("View Original")}
		</button>
	);
}


function ReplaceFileButton(props) {
	const {settings} = props;
	const disabled = !settings.can_change;
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
		<button type="button" disabled={disabled} onClick={replaceFile}><UploadIcon/>{gettext("Replace File")}</button>
		<input type="file" name="replaceFile" ref={inputRef} accept={settings.file_mime_type} onChange={handleFileSelect} />
	</>);
}


export function ControlButtons(props) {
	const {settings} = props;

	const controlButtons = useMemo(() => {
		const buttons: Array<ReactElement> = [];
		if (settings.download_file) {
			buttons.push(<DownloadFileButton {...props} />);
		}
		if (settings.view_original) {
			buttons.push(<ViewOriginalButton {...props} />);
		}
		if (settings.replace_file) {
			buttons.push(<ReplaceFileButton {...props} />);
		}
		return buttons;
	}, []);

	return (
		<div className="button-group">
			{props.children}
		{controlButtons.map((button, index) =>
			<Fragment key={index}>{button}</Fragment>
		)}
		</div>
	);
}
