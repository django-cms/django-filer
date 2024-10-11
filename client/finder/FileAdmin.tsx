import React, {useContext, useEffect, useMemo, useRef, lazy, Suspense} from 'react';
import FinderSettings from './FinderSettings';
import FolderTabs from './FolderTabs';
import FileDetails from './FileDetails';


export function FileAdmin() {
	const settings = useContext(FinderSettings);
	const FileEditor = useMemo(() => {
		if (settings.react_component) {
			const component = `./components/editor/${settings.react_component}.js`;
			const LazyItem = lazy(() => import(component));
			return (props) => (
				<Suspense fallback={<span>{gettext("Loading...")}</span>}>
					<LazyItem {...props} />
				</Suspense>
			);
		}
		return (props) => (
			<FileDetails {...props}>
				<img src={props.settings.thumbnail_url} />
			</FileDetails>
		);
	}, []);
	const editorRef = useRef(null);

	useEffect(() => {
		editorRef.current.insertAdjacentHTML('afterbegin', settings.mainContent.innerHTML);
	}, []);

	return (<>
		<FolderTabs settings={settings} />
		<div className="detail-editor">
			<FileEditor editorRef={editorRef} settings={settings} />
			<div ref={editorRef}></div>
		</div>
 	</>);
}
