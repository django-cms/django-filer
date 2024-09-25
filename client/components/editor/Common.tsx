import React from 'react';
import {FileDetails} from 'finder/FileDetails';


export default function Common(props) {
	return (
		<FileDetails {...props}>
			<img src={props.settings.thumbnail_url} />
		</FileDetails>
	);
}
