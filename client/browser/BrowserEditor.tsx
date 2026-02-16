import React, {lazy, Suspense, useEffect, useMemo, useState} from 'react';
import {createRoot} from 'react-dom/client';
import SelectTags from '../common/SelectTags';


function EditorForm(props) {
	const {mainContent, file_info, settings} = props;
	const [formHtml, setFormHtml] = useState(props.form_html);

	useEffect(() => {
		const shadowRoot = mainContent.getRootNode();
		if (!(shadowRoot instanceof ShadowRoot))
			return;
		const tagsElement = shadowRoot.getElementById('id_tags');
		if (!(tagsElement instanceof HTMLSelectElement))
			return;
		if (settings.tags) {
			// extract selected values from the original <select multiple name="labels"> element
			// this only happens if a user sets a label but the form is rejected by the server
			const initial = [];
			for (const option of tagsElement.selectedOptions) {
				const found = settings.tags.find(tag => tag.value == option.value);
				if (found) {
					initial.push(found);
				}
			}

			// replace the original <select multiple name="labels"> element with the "downshift" component
			if (tagsElement.nextElementSibling?.classList.contains('select-container')) {
				tagsElement.nextElementSibling.remove();
			}
			const divElement = document.createElement('div');
			divElement.classList.add('select-container');
			tagsElement.insertAdjacentElement('afterend', divElement);
			const root = createRoot(divElement);
			root.render(<SelectTags tags={settings.tags} initial={initial} original={tagsElement}/>);
		}
		tagsElement.style.display = 'none';
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
					settings.selectFile(content.file_info);
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

	return (
		<form>
			<div dangerouslySetInnerHTML={{__html: formHtml}}/>
			<div className="button-row">
				<button type="button" className="default" onClick={handleSave}>{gettext("Save")}</button>
				<button type="button" className="dismiss" onClick={settings.dismissAndClose}>{gettext("Dismiss Upload")}</button>
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
