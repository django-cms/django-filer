import React, {useContext, useRef, useState} from 'react';
import {FinderSettings} from './FinderSettings';


export default function FileAdmin(props) {
	const settings = useContext(FinderSettings);

	return (
		<div className="finder">Edit File</div>
	);
}
