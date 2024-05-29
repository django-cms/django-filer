import React, {useContext, useEffect, useRef, useState} from 'react';
import {FinderSettings} from 'finder/FinderSettings';
import FileDetails from './FileDetails';


export default function Video(props) {
	const settings = useContext(FinderSettings);

	return (
		<FileDetails>
			<video src={settings.download_url}></video>
		</FileDetails>
	);
}
