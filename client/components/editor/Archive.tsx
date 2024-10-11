import React, {Fragment} from 'react';
import FileDetails from 'finder/FileDetails';
import UnarchiveIcon from '../../icons/unarchive.svg';


export default function Archive(props) {
	const {settings} = props;

	async function extractArchive() {
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
	}

	const controlButtons = [
		<Fragment key="extract-archive">
			<button type="button" onClick={extractArchive}><UnarchiveIcon/>{gettext("Extract archive")}</button>
		</Fragment>
	];

	return (
		<FileDetails {...props} controlButtons={controlButtons}>
			<img src={props.settings.thumbnail_url} />
		</FileDetails>
	);
}
