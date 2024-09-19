import React, {useContext} from 'react';
import {FinderSettings} from 'finder/FinderSettings';
import {FileDetails} from 'finder/FileDetails';


export default function Common(props) {
	const settings = useContext(FinderSettings);

	return (
		<FileDetails>
			<img src={settings.thumbnail_url} />
		</FileDetails>
	);
}
