import React, {useContext, useMemo, useRef, lazy, Suspense, useEffect} from 'react';
import {createRoot} from 'react-dom/client';
import {DndContext} from '@dnd-kit/core';
import FinderSettings from './FinderSettings';
import FolderTabs from './FolderTabs';
import FileDetails from './FileDetails';
import PermissionEditor from './PermissionEditor';
import SelectLabelTags from '../common/SelectTags';
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
				<img src={props.settings.thumbnail_url} draggable={false} />
			</FileDetails>
		</>);
	}, []);
	const editorRef = useRef(null);

	useEffect(() => {
		if (settings.label_tags) {
			const tagsElement = document.getElementById('id_label_tags');
			if (tagsElement instanceof HTMLSelectElement) {
				// extract selected values from the original <select multiple name="label_tags"> element
				const initial = [];
				for (const option of tagsElement.selectedOptions) {
					const found = settings.label_tags.find(label => label.id == option.value);
					if (found) {
						initial.push(found);
					}
				}

				// replace the original <select multiple name="labels"> element with the "downshift" component
				const divElement = document.createElement('div');
				divElement.classList.add('select-container');
				tagsElement.insertAdjacentElement('afterend', divElement);
				tagsElement.style.display = 'none';
				const root = createRoot(divElement);
				root.render(<SelectLabelTags tags={settings.label_tags} initial={initial} original={tagsElement} />);
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
