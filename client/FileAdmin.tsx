import React, {useContext, useEffect, useRef, lazy, Suspense} from 'react';
import {FinderSettings} from './FinderSettings';
import {FolderTabs} from "./FolderTabs";


export default function FileAdmin(props) {
	const settings = useContext(FinderSettings);
	const editorRef = useRef(null);
	const component = `./components/${settings.editor_component}.js`;
	const FileEditor = settings.editor_component ? lazy(() => import(component)) : null;

	useEffect(() => {
		editorRef.current.insertAdjacentHTML('afterbegin', settings.mainContent.innerHTML);
	}, []);

	return (<>
		<FolderTabs />
		<div className="detail-editor">
			{FileEditor &&
			<Suspense fallback={<span>Loading...</span>}>
				<FileEditor editorRef={editorRef} />
			</Suspense>
			}
			<div ref={editorRef}></div>
		</div>
 	</>);
}
