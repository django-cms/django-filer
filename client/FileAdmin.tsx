import React, {useContext, useEffect, useRef, lazy, Suspense} from 'react';
import {FinderSettings} from './FinderSettings';
import {FolderTabs} from "./FolderTabs";


export default function FileAdmin(props) {
	const settings = useContext(FinderSettings);
	const editorRef = useRef(null);
	const FileEditor = lazy(() => import(settings.react_component));

	useEffect(() => {
		editorRef.current.insertAdjacentHTML('afterbegin', settings.mainContent.innerHTML);
	}, []);

	return (<>
		<FolderTabs />
		<div className="detail-editor">
			{settings.react_component &&
			<Suspense fallback={<span>Loading...</span>}>
				<FileEditor editorRef={editorRef} />
			</Suspense>
			}
			<div ref={editorRef}></div>
		</div>
 	</>);
}
