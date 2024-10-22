import React, {
	lazy,
	memo,
	Suspense,
	useCallback,
	useEffect,
	useMemo,
	useRef,
	useState,
} from 'react';
import FigureLabels from '../finder/FigureLabels';
import FileUploader	 from '../finder/FileUploader';
import ArrowDownIcon from '../icons/arrow-down.svg';
import ArrowRightIcon from '../icons/arrow-right.svg';
import EmptyIcon from '../icons/empty.svg';
import FolderIcon from '../icons/folder.svg';
import FolderOpenIcon from '../icons/folder-open.svg';
import RootIcon from '../icons/root.svg';


function StaticFigure(props) {
	return (<>{props.children}</>);
}


function Figure(props) {
	const FigBody = useMemo(() => {
		if (props.browser_component) {
			const component = `./components/folderitem/${props.browser_component}.js`;
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
	const {files, isLoading} = props;

	function selectFile(file) {
		console.log(file);
	}

	console.log('FolderList', files);
	return (
		<ul className="files-list">{
		files.length === 0 ?
			<li className="status">{gettext("Empty folder")}</li> :
		files.map(file => (
			<li key={file.id} onClick={() => selectFile(file)}><Figure {...file} /></li>
		))}
		</ul>
	);
});


function FolderEntry(props) {
	const {folder, toggleOpen, fetchFiles, isCurrent} = props;

	if (folder.is_root) {
		return (<span onClick={() => fetchFiles(folder.id)}><RootIcon/></span>);
	}

	return (<>
		<i onClick={toggleOpen}>{
			folder.has_subfolders ? folder.is_open ? <ArrowDownIcon/> : <ArrowRightIcon/> : <EmptyIcon/>
		}</i>
		{isCurrent ?
		<strong><FolderOpenIcon/>{folder.name}</strong> :
		<span onClick={() => fetchFiles(folder.id)} role="button">
			<FolderIcon/>{folder.name}
		</span>
		}
	</>);
}


function FolderStructure(props) {
	const {baseUrl, folder, lastFolderId, fetchFiles, refreshStructure} = props;

	async function fetchChildren() {
		const response = await fetch(`${baseUrl}fetch/${folder.id}`);
		if (response.ok) {
			const reply = await response.json();
			folder.name = reply.name;
			folder.has_subfolders = reply.has_subfolders;
			folder.children = reply.children;
		} else {
			console.error(response);
		}
	}

	async function toggleOpen() {
		folder.is_open = !folder.is_open;
		if (folder.is_open) {
			if (folder.children === null) {
				await fetchChildren();
			} else {
				await fetch(`${baseUrl}open/${folder.id}`);
			}
		} else {
			await fetch(`${baseUrl}close/${folder.id}`);
		}
		refreshStructure();
	}

	return folder ? (
		<li>
			<FolderEntry
				folder={folder}
				toggleOpen={toggleOpen}
				fetchFiles={fetchFiles}
				isCurrent={lastFolderId === folder.id}
			/>
			{folder.is_open && (
			<ul>
			{folder.children.map(child => (
				<FolderStructure
					key={child.id}
					baseUrl={baseUrl}
					folder={child}
					lastFolderId={lastFolderId}
					fetchFiles={fetchFiles}
					refreshStructure={refreshStructure}
				/>
			))}
			</ul>)}
		</li>
	) : null;
}


export default function FinderFileSelect(props) {
	const baseUrl = props['base-url'];
	const [structure, setStructure] = useState({root_folder: null, last_folder: null, files: []});
	const [isLoading, setLoading] = useState(false);
	const [searchQuery, setSearchQuery] = useState(() => {
		const params = new URLSearchParams(window.location.search);
		return params.get('q');
	});
	const folderListRef = useRef(null);

	useEffect(() => {
		getStructure();
	}, []);

	async function getStructure() {
		const response = await fetch(`${baseUrl}structure/${props.realm}`);
		if (response.ok) {
			setStructure(await response.json());
		} else {
			console.error(response);
		}
	}

	async function fetchFiles(folderId){
		const params = new URLSearchParams({q: searchQuery});
		const listFilesUrl = `${baseUrl}list/${folderId}${searchQuery ? `?${params.toString()}` : ''}`;
		setLoading(true);
		const newStructure = {root_folder: structure.root_folder, last_folder: folderId, files: []};
		const response = await fetch(listFilesUrl);
		if (response.ok) {
			const body = await response.json();
			newStructure.files = body.files;
		} else {
			console.error(response);
		}
		setLoading(false);
		setStructure(newStructure);
	}

	function refreshStructure() {
		console.log('refreshStructure');
		setStructure({...structure});
	}

	function handleUpload(folderId) {
		folderListRef.current.fetchFiles
	}

	return structure.root_folder && (<>
		<ul className="folder-structure">
			<FolderStructure
				baseUrl={baseUrl}
				folder={structure.root_folder}
				lastFolderId={structure.last_folder}
				fetchFiles={fetchFiles}
				// folderListRef={folderListRef}
				refreshStructure={refreshStructure}
			/>
		</ul>
		<FileUploader folderId={structure.root_folder} handleUpload={handleUpload}>{
			isLoading ?
			<div className="status">{gettext("Loading…")}</div> :
			<FilesList files={structure.files} />
		}</FileUploader>
	</>);
}
