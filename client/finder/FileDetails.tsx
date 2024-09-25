import React, {useMemo, useState} from 'react';
import Select from 'react-select';
import {ControlButtons} from 'finder/ControlButtons';
import {ProgressBar, ProgressOverlay} from 'finder/UploadProgress';


function SelectLabels(props) {
	const {settings} = props;
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
	const {settings} = props;
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
			<ControlButtons setUploadFile={setUploadFile} settings={settings}>{props.controlButtons}</ControlButtons>
			<SelectLabels settings={settings} />
		</div>
		{uploadFile &&
		<ProgressOverlay>
			<ProgressBar file={uploadFile} targetId={settings.file_id} settings={settings} />
		</ProgressOverlay>
		}
	</>);
}
