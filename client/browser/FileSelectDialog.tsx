import React, {
	lazy,
	memo,
	Suspense,
	useEffect,
	useMemo,
	useRef,
	useState,
} from 'react';
import {Tooltip} from 'react-tooltip';
import FigureLabels from '../finder/FigureLabels';
import FileUploader	 from '../finder/FileUploader';
import FolderStructure from './FolderStructure';
import Menu from './Menu';


function StaticFigure(props) {
	return (<>{props.children}</>);
}


function Figure(props) {
	const FigBody = useMemo(() => {
		if (props.folderitem_component) {
			const component = `./components/folderitem/${props.folderitem_component}.js`;
			const LazyItem = lazy(() => import(component));
			return (props) => (
				<Suspense>
					<LazyItem {...props}>{props.children}</LazyItem>
				</Suspense>
			);
		}
		return StaticFigure;
	},[]);

	return (
		<figure className="figure">
			<FigBody {...props}>
				<FigureLabels labels={props.labels}>
					<img src={props.thumbnail_url} {...props.listeners} {...props.attributes} />
				</FigureLabels>
			</FigBody>
			<figcaption>
				{props.name}
			</figcaption>
		</figure>
	);
}


const FilesList = memo((props: any) => {
	const {files, selectFile} = props;

	console.log('FolderList', files);

	return (
		<ul className="files-browser">{
		files.length === 0 ?
			<li className="status">{gettext("Empty folder")}</li> :
		files.map(file => (
			<li key={file.id} onClick={() => selectFile(file)}><Figure {...file} /></li>
		))}
		</ul>
	);
});


export default function FileSelectDialog(props) {
	const {baseUrl, csrfToken, realm, selectFile} = props;
	const [structure, setStructure] = useState({root_folder: null, last_folder: null, files: null});
	const uploaderRef = useRef(null);

	useEffect(() => {
		getStructure();
	}, []);

	async function getStructure() {
		const response = await fetch(`${baseUrl}structure/${realm}`);
		if (response.ok) {
			setStructure(await response.json());
		} else {
			console.error(response);
		}
	}

	async function fetchFiles(folderId: string, searchQuery='') {
		const fetchUrl = (() => {
			if (searchQuery) {
				const params = new URLSearchParams({q: searchQuery});
				return `${baseUrl}${folderId}/search?${params.toString()}`;
			}
			return `${baseUrl}${folderId}/list`;
		})();
		const newStructure = {root_folder: structure.root_folder, last_folder: folderId, files: null};
		const response = await fetch(fetchUrl);
		if (response.ok) {
			const body = await response.json();
			newStructure.files = body.files;
		} else {
			console.error(response);
		}
		setStructure(newStructure);
	}

	function refreshStructure() {
		console.log('refreshStructure');
		setStructure({...structure});
	}

	function handleUpload(folderId, files) {
		fetchFiles(folderId);
		selectFile(files[0]);
	}

	return structure.root_folder && (<>
		<div className="wrapper">
			<Menu
				lastFolderId={structure.last_folder}
				fetchFiles={fetchFiles}
				openUploader={() => uploaderRef.current.openUploader()}
			/>
			<div className="browser-body">
				<nav className="folder-structure">
					<ul>
						<FolderStructure
							baseUrl={baseUrl}
							folder={structure.root_folder}
							lastFolderId={structure.last_folder}
							fetchFiles={fetchFiles}
							refreshStructure={refreshStructure}
						/>
					</ul>
				</nav>
				<FileUploader
					folderId={structure.last_folder}
					handleUpload={handleUpload}
					ref={uploaderRef}
					settings={{csrf_token: csrfToken, base_url: baseUrl}}
				>{
					structure.files === null ?
					<div className="status">{gettext("Loading files…")}</div> :
					<FilesList files={structure.files} selectFile={selectFile} />
				}</FileUploader>
			</div>
		</div>
		<Tooltip id="django-finder-tooltip" place="bottom-start" />
	</>);
}