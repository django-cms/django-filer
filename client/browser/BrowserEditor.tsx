import React, {lazy, Suspense, useEffect, useMemo, useState} from 'react';
import {createRoot} from 'react-dom/client';
import SelectLabels from '../finder/SelectLabels';


function EditorForm(props) {
	const {mainContent, file_info, settings} = props;
	const [formHtml, setFormHtml] = useState(props.form_html);

	useEffect(() => {
		const shadowRoot = mainContent.getRootNode();
		if (!(shadowRoot instanceof ShadowRoot))
			return;
		const labelsElement = shadowRoot.getElementById('id_labels');
		if (!(labelsElement instanceof HTMLSelectElement))
			return;
		if (settings.labels) {
			// replace the original <select multiple name="labels"> element with the "downshift" component
			if (labelsElement.nextElementSibling?.classList.contains('select-labels-container')) {
				labelsElement.nextElementSibling.remove();
			}
			const divElement = document.createElement('div');
			divElement.classList.add('select-labels-container');
			labelsElement.insertAdjacentElement('afterend', divElement);
			const root = createRoot(divElement);
			root.render(<SelectLabels labels={settings.labels} initial={[]} original={labelsElement}/>);
		}
		labelsElement.style.display = 'none';
	}, [formHtml]);

	function handleSave() {
		const changeUrl = `${settings.baseUrl}${file_info.id}/change`;
		const form = mainContent.querySelector('form');
		if (!(form instanceof HTMLFormElement))
			throw new Error('Form not found');
		const formData = new FormData(form);
		fetch(changeUrl, {
			method: 'POST',
			body: formData,
			headers: {
				'X-CSRFToken': settings.csrfToken,
			},
		}).then(async response => {
			if (response.ok) {
				const content = await response.json();
				if ('file_info' in content) {
					settings.selectFile(file_info);
				} else if ('form_html' in content) {
					setFormHtml(content.form_html);
				} else {
					alert('Unexpected response');
				}
			} else {
				alert(response.statusText);
			}
		});
	}

	function handleDismiss() {
		window.location.reload();
	}

	return (
		<form>
			<div dangerouslySetInnerHTML={{__html: formHtml}}/>
			<div className="button-row">
				<button type="button" className="default" onClick={handleSave}>{gettext("Save")}</button>
				<button type="button" className="dismiss" onClick={handleDismiss}>{gettext("Dismiss")}</button>
			</div>
		</form>
	);
}


export default function BrowserEditor(props) {
	const {uploadedFile, mainContent, settings} = props as {uploadedFile: any, mainContent: HTMLElement, settings: any};
	const DetailEditor = useMemo(() => {
		if (uploadedFile.file_info.browser_component) {
			const component = `./components/browser/${uploadedFile.file_info.browser_component}.js`;
			const LazyItem = lazy(() => import(component));
			return (props) => (
				<div className="browser-editor">
					<Suspense fallback={<span>{gettext("Loading...")}</span>}>
						<LazyItem fileInfo={props.file_info} />
					</Suspense>
					<EditorForm {...props} />
				</div>
			);
		}
		return (props) => (
			<div className="browser-editor">
				<img className="thumbnail" src={props.file_info.thumbnail_url} />
				<EditorForm {...props} />
			</div>
		);
	}, [uploadedFile.file_info.browser_component]);

	return <DetailEditor mainContent={mainContent} {...uploadedFile} settings={settings} />;
}
