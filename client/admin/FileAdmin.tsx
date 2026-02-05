import React, {useContext, useMemo, useRef, lazy, Suspense, useEffect} from 'react';
import {createRoot} from 'react-dom/client';
import {DndContext} from '@dnd-kit/core';
import FinderSettings from './FinderSettings';
import FolderTabs from './FolderTabs';
import FileDetails from './FileDetails';
import PermissionEditor from './PermissionEditor';
import SelectLabels from '../common/SelectLabels';
import ShieldFileIcon from '../icons/shield-file.svg';


export default function FileAdmin() {
	const settings = useContext(FinderSettings);
	const permissionDialogRef = useRef(null);
	const FileEditor = useMemo(() => {
		const PermissionDialogButton = () => (
			<div className="button-group">{settings.is_admin &&
				<button type="button" onClick={() => permissionDialogRef.current.show()}>
					<ShieldFileIcon/><span>{gettext("Edit file permissions")}</span>
				</button>
			}</div>
		);
		if (settings.editor_component) {
			const component = `./components/editor/${settings.editor_component}.js`;
			const LazyItem = lazy(() => import(component));
			return (props) => (
				<Suspense fallback={<span>{gettext("Loading...")}</span>}>
					<LazyItem {...props}><PermissionDialogButton /></LazyItem>
				</Suspense>
			);
		}
		return (props) => (<>
			<PermissionDialogButton />
			<FileDetails {...props}>
				<img src={props.settings.thumbnail_url} />
			</FileDetails>
		</>);
	}, []);
	const editorRef = useRef(null);

	useEffect(() => {
		if (settings.labels) {
			const labelsElement = document.getElementById('id_labels');
			if (labelsElement instanceof HTMLSelectElement) {
				// extract selected values from the original <select multiple name="labels"> element
				const initial = [];
				for (const option of labelsElement.selectedOptions) {
					const found = settings.labels.find(label => label.value == option.value);
					if (found) {
						initial.push(found);
					}
				}

				// replace the original <select multiple name="labels"> element with the "downshift" component
				const divElement = document.createElement('div');
				divElement.classList.add('select-container');
				labelsElement.insertAdjacentElement('afterend', divElement);
				labelsElement.style.display = 'none';
				const root = createRoot(divElement);
				root.render(<SelectLabels labels={settings.labels} initial={initial} original={labelsElement} />);
			}
		}
	}, []);

	return (
		<DndContext
			onDragStart={event => permissionDialogRef.current.handleDragStart(event)}
			onDragEnd={event => permissionDialogRef.current.handleDragEnd(event)}
			autoScroll={false}
		>
			<FolderTabs settings={settings} />
			<PermissionEditor ref={permissionDialogRef} settings={settings} />
			<div className="detail-editor">
				<FileEditor editorRef={editorRef} settings={settings} />
				<div dangerouslySetInnerHTML={{__html: settings.mainContent.innerHTML}} ref={editorRef}></div>
			</div>
		</DndContext>
	);
}
