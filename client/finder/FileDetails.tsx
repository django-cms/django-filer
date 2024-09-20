import React, {
	Fragment,
	useContext,
	useMemo,
	useRef,
	useState
} from 'react';
import Select from 'react-select';
import {ProgressBar, ProgressOverlay} from 'finder/UploadProgress';
import {FinderSettings} from 'finder/FinderSettings';
import DownloadIcon from 'icons/download.svg';
import FullSizeIcon from 'icons/full-size.svg';
import UploadIcon from 'icons/upload.svg';
import PauseIcon from "../icons/pause.svg";
import PlayIcon from "../icons/play.svg";


function DownloadFileButton(props) {
	const settings = useContext(FinderSettings);

	return (
		<a download={settings.filename} href={settings.download_url}><DownloadIcon/>{gettext("Download")}</a>
	);
}


function ViewOriginalButton() {
	const settings = useContext(FinderSettings);

	function viewOriginal() {
		window.open(settings.download_url, '_blank').focus();
	}

	return (
		<button type="button" onClick={viewOriginal}><FullSizeIcon/>{gettext("View Original")}</button>
	);
}


function ReplaceFileButton(props) {
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
		<button type="button" onClick={replaceFile}><UploadIcon/>{gettext("Replace File")}</button>
		<input type="file" name="replaceFile" ref={inputRef} accept={acceptMimeType} onChange={handleFileSelect} />
	</>);
}


export function ControlButtons(props) {
	const settings = useContext(FinderSettings);

	const controlButtons = useMemo(() => {
		const buttons: Array<React.JSX.Element> = [];
		if (settings.download_url) {
			buttons.push(<DownloadFileButton/>);
		}
		if (settings.original_url) {
			buttons.push(<ViewOriginalButton/>);
		}
		if (settings.replacing_mime_type) {
			buttons.push(
				<ReplaceFileButton
					setUploadFile={props.setUploadFile}
					acceptMimeType={settings.replacing_mime_type}
				/>
			);
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


function SelectLabels() {
	const settings = useContext(FinderSettings);
	const LabelOption = ({innerProps, data}) => (
		<div {...innerProps} className="select-labels-option">
			<span style={{backgroundColor: data.color}} className="select-labels-dot" />
			{data.label}
		</div>
	);
	const MultiValueLabel = ({data}) => (
		<div>
			<span style={{backgroundColor: data.color}} className="select-labels-dot" />
			{data.label}
		</div>
	);
	const MultiValueContainer = ({children}) => (
		<div className="select-labels-value">
			{children}
		</div>
	);
	const defaultValues = useMemo(() => {
		const defaultValues = [];
		if (settings.labels) {
			let labelsElement = document.getElementById('id_labels');
			if (labelsElement instanceof HTMLSelectElement) {
				// extract selected values from the original <select multiple name="labels"> element
				for (const option of labelsElement.selectedOptions) {
					const found = settings.labels.find(label => label.value == option.value);
					if (found) {
						defaultValues.push(found);
					}
				}
				// remove the original <select multiple name="labels"> element
				while (labelsElement) {
					if (labelsElement.classList.contains('field-labels')) {
						labelsElement.remove();
						break;
					}
					labelsElement = labelsElement.parentElement;
				}
			}
		}
		return defaultValues;
	}, []);

	if (settings.labels) return (
		<div className="aligned">
			<div className="form-row" style={{overflow: "visible"}}>
				<div className="flex-container">
					<label>{gettext("Labels")}:</label>
					<Select
						components={{Option: LabelOption, MultiValueLabel, MultiValueContainer}}
						defaultValue={defaultValues}
						options={settings.labels}
						name="labels"
						placeholder={gettext("Choose Labels")}
						className="select-labels"
						isMulti={true}
					/>
				</div>
			</div>
		</div>
	);
}


export function FileDetails(props) {
	const settings = useContext(FinderSettings);
	const [uploadFile, setUploadFile] = useState<Promise<Response>>(null);
	const subtitle = useMemo(() => {
		const subtitle = document.getElementById('id_subtitle');
		if (subtitle) {
			subtitle.remove();
			return subtitle.innerHTML;
		}
		return '';
	},[]);

	return (<>
		<div className="file-details" style={props.style}>
			<h2>{subtitle}</h2>
			{props.children}
			<ControlButtons setUploadFile={setUploadFile}>{props.controlButtons}</ControlButtons>
			<SelectLabels />
		</div>
		{uploadFile &&
		<ProgressOverlay>
			<ProgressBar file={uploadFile} targetId={settings.file_id} />
		</ProgressOverlay>
		}
	</>);
}
