import React, {useContext, useEffect, useMemo, useRef, lazy, Suspense} from 'react';
import {FinderSettings} from './FinderSettings';
import {FolderTabs} from "./FolderTabs";


export function FileAdmin(props) {
	const settings = useContext(FinderSettings);
	const FileEditor = useMemo(() => {
		const component = `./components/editor/${settings.extension.component}.js`;
		const LazyItem = lazy(() => import(component));
		return (props) => (
			<Suspense fallback={<span>{gettext("Loading...")}</span>}>
				<LazyItem {...props} />
			</Suspense>
		);
	}, []);
	const editorRef = useRef(null);

	useEffect(() => {
		editorRef.current.insertAdjacentHTML('afterbegin', settings.mainContent.innerHTML);
	}, []);

	return (<>
		<FolderTabs />
		<div className="detail-editor">
			<FileEditor editorRef={editorRef} extension={settings.extension} />
			<div ref={editorRef}></div>
		</div>
 	</>);
}
