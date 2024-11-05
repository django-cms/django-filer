import React, {lazy, Suspense, useMemo} from 'react';
import SelectLabels from '../finder/SelectLabels';


export default function BrowserEditor(props) {
	const {uploadedFile, mainContent} = props;
	const DetailEditor = useMemo(() => {
		if (uploadedFile.file_info.browser_component) {
			const component = `./components/browser/${uploadedFile.file_info.browser_component}.js`;
			const LazyItem = lazy(() => import(component));
			return (props) => (
				<div className="detail-editor">
					<Suspense fallback={<span>{gettext("Loading...")}</span>}>
						<LazyItem fileInfo={props.file_info} />
					</Suspense>
					<form>
						<SelectLabels settings={{labels: uploadedFile.labels, mainContent: mainContent}} />
						<div dangerouslySetInnerHTML={{__html: props.form_html}} />
					</form>
				</div>
			);
		}
		return (props) => (
			<div className="detail-editor">
				<img src={props.file_info.thumbnail_url} />
				<form>
					<SelectLabels settings={{labels: uploadedFile.labels, mainContent: mainContent}} />
					<div dangerouslySetInnerHTML={{__html: props.form_html}} />
				</form>
			</div>
		);
	}, [uploadedFile.file_info.browser_component]);

	return <DetailEditor {...uploadedFile} />;
}
