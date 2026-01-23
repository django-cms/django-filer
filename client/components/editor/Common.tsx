import React from 'react';
import FileDetails from '../../admin/FileDetails';


export default function Common(props) {
	return (<>
		{props.children}
		<FileDetails {...props}>
			<img src={props.settings.thumbnail_url} />
		</FileDetails>
	</>);
}
