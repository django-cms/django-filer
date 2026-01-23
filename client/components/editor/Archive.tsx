import React, {Fragment, useState} from 'react';
import FileDetails from '../../admin/FileDetails';
import UnarchiveIcon from '../../icons/unarchive.svg';


export default function Archive(props) {
	const {settings, children} = props;
	const [extracting, setExtracting] = useState(false);

	async function extractArchive() {
		setExtracting(true);
		const fetchUrl = `${settings.base_url}${settings.file_id}/unarchive`;
		const response = await fetch(fetchUrl, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': settings.csrf_token,
			},
		});
		if (response.ok || [409, 415].includes(response.status)) {
			window.alert(await response.text());
		} else {
			console.error(response);
		}
		// setUnarchiving(false); // why would someone extract an archive twice?
	}

	const controlButtons = [
		<Fragment key="extract-archive">
			<button type="button" disabled={extracting} onClick={extractArchive}><UnarchiveIcon/>{gettext("Extract archive")}</button>
		</Fragment>
	];

	return (<>
		{children}
		<FileDetails {...props} controlButtons={controlButtons}>
			<img src={props.settings.thumbnail_url} />
		</FileDetails>
	</>);
}
