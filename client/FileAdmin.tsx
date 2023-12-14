import React, {useContext, useEffect, useRef, useState} from 'react';
import {FinderSettings} from './FinderSettings';
import {FolderTabs} from "./FolderTabs";


export default function FileAdmin(props) {
	const settings = useContext(FinderSettings);
	const formRef = useRef(null);

	useEffect(() => {
		formRef.current.insertAdjacentHTML('afterbegin', settings.mainContent.innerHTML);
	}, []);

	const handleSubmit = (event) => {
		event.preventDefault();
		const formData = new FormData(event.target);
		console.log(formData);
	};

	return (<>
		<FolderTabs />
		<div className="detail-editor" ref={formRef}></div>
	</>);
}
