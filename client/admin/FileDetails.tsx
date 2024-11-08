import React, {useMemo, useState} from 'react';
import {ControlButtons} from './ControlButtons';
import {ProgressBar, ProgressOverlay} from '../common/UploadProgress';


export default function FileDetails(props) {
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
		</div>
		{uploadFile &&
		<ProgressOverlay>
			<ProgressBar file={uploadFile} targetId={settings.file_id} settings={settings} />
		</ProgressOverlay>
		}
	</>);
}
