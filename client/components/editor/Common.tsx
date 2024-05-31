import React, {useContext} from 'react';
import {FileDetails} from 'finder/FileDetails';
import {FinderSettings} from "../../finder/FinderSettings";


export default function Common(props) {
	const settings = useContext(FinderSettings);
	console.log(settings);

	return (
		<FileDetails>
			<img src={settings.thumbnail_url} />
		</FileDetails>
	);
}
