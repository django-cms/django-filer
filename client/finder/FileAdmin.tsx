import React, {useContext, useMemo, useRef, lazy, Suspense, useEffect} from 'react';
import {createRoot} from 'react-dom/client';
import FinderSettings from './FinderSettings';
import FolderTabs from './FolderTabs';
import FileDetails from './FileDetails';
import SelectLabels from "./SelectLabels";


export function FileAdmin() {
	const settings = useContext(FinderSettings);
	const FileEditor = useMemo(() => {
		if (settings.editor_component) {
			const component = `./components/editor/${settings.editor_component}.js`;
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
				console.log('initialValues', initial);

				// replace the original <select multiple name="labels"> element with the "downshift" component
				const divElement = document.createElement('div');
				divElement.classList.add('select-labels-container');
				labelsElement.insertAdjacentElement('afterend', divElement);
				labelsElement.style.display = 'none';
				const root = createRoot(divElement);
				root.render(<SelectLabels labels={settings.labels} initial={initial} original={labelsElement} />);
			}
		}
	}, []);

	return (<>
		<FolderTabs settings={settings} />
		<div className="detail-editor">
			<FileEditor editorRef={editorRef} settings={settings} />
			<div dangerouslySetInnerHTML={{__html: settings.mainContent.innerHTML}} ref={editorRef}></div>
		</div>
	</>);
}
