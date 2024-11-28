import React, {
	forwardRef,
	lazy,
	memo,
	Suspense,
	useCallback,
	useEffect,
	useImperativeHandle,
	useMemo,
	useRef,
	useState,
} from 'react';
import {useInView} from 'react-intersection-observer';
import {Tooltip} from 'react-tooltip';
import FigureLabels from '../common/FigureLabels';
import FileUploader	 from '../common/FileUploader';
import BrowserEditor from './BrowserEditor';
import FolderStructure from './FolderStructure';
import MenuBar from './MenuBar';
import CloseIcon from '../icons/close.svg';


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


const ScrollSpy = (props) => {
	const {fetchFiles} = props;
	const {ref, inView} = useInView({
		triggerOnce: true,
		onChange: async (loadMore) => {
			if (loadMore && !inView) {
				await fetchFiles();
			}
		},
	});
	console.log('ScrollSpy', inView);
	if (inView) {
		console.log('already visible');
		fetchFiles();
	}

	return (
		<div className="scroll-spy" ref={ref}></div>
	);
};


const FilesList = memo((props: any) => {
	const {structure, fetchFiles, selectFile} = props;

	console.log('FolderList', structure);

	return (
		<ul className="files-browser">{
		structure.files.length === 0 ?
			<li className="status">{gettext("Empty folder")}</li> : (
			<>{structure.files.map(file => (
			<li key={file.id} onClick={() => selectFile(file)}><Figure {...file} /></li>
			))}
			{structure.offset !== null && <ScrollSpy key={structure.offset} fetchFiles={fetchFiles} />}
			</>
		)}</ul>
	);
});


const FileSelectDialog = forwardRef(function FileSelectDialog(props: any, forwardedRef) {
	const {realm, baseUrl, csrfToken} = props;
	const [structure, setStructure] = useState({
		root_folder: null,
		last_folder: null,
		files: null,
		offset: null,
		recursive: false,
		search_query: '',
		labels: [],
	});
	const ref = useRef(null);
	const uploaderRef = useRef(null);
	const [uploadedFile, setUploadedFile] = useState(null);
	const [currentFolderId, setCurrentFolderId] = useState(null);
	const [currentFolderElement, setCurrentFolderElement] = useState(null);

	useImperativeHandle(forwardedRef, () => ({scrollToCurrentFolder, dismissAndClose}));

	useEffect(() => {
		if (structure.root_folder === null) {
			getStructure();
		}
	}, [structure.root_folder]);

	useEffect(() => {
		if (currentFolderId && uploadedFile === null) {
			fetchFiles();
		}
	}, [currentFolderId, uploadedFile]);

	useEffect(() => {
		if (structure.root_folder) {
			fetchFiles();
		}
	}, [structure.recursive, structure.search_query]);

	function setCurrentFolder(folderId){
		setCurrentFolderId(folderId);
		setStructure({
			...structure,
			last_folder: folderId,
			files: [],
			offset: null,
			recursive: false,
			search_query: '',
		});
	}

	 function toggleRecursive(folderId: string) {
		setStructure({
			...structure,
			last_folder: folderId,
			files: [],
			offset: null,
			recursive: structure.recursive ? false : true,
			search_query: '',
		});
	}

	function setSearchQuery(query) {
		setStructure({
			...structure,
			files: [],
			offset: null,
			recursive: false,
			search_query: query,
		});
	}

	function refreshFilesList(){
		setStructure({
			...structure,
			root_folder: structure.root_folder,
			files: [],
			last_folder: structure.last_folder,
			offset: null,
			search_query: structure.search_query,
			labels: structure.labels,
		});
	}

	async function getStructure() {
		const response = await fetch(`${baseUrl}structure/${realm}`);
		if (response.ok) {
			setStructure(await response.json());
		} else {
			console.error(response);
		}
	}

	const fetchFiles = useCallback(async () => {
		const fetchUrl = (() => {
			const params = new URLSearchParams();
			if (structure.recursive) {
				params.set('recursive', '');
			}
			if (structure.offset !== null) {
				params.set('offset', String(structure.offset));
			}
			if (structure.search_query) {
				params.set('q', structure.search_query);
				return `${baseUrl}${structure.last_folder}/search?${params.toString()}`;
			}
			return `${baseUrl}${structure.last_folder}/list${params.size === 0 ? '' : `?${params.toString()}`}`;
		})();
		const response = await fetch(fetchUrl);
		if (response.ok) {
			const body = await response.json();
			setStructure({
				...structure,
				files: structure.files.concat(body.files),
				offset: body.offset,
			});
		} else {
			console.error(response);
		}
	}, [structure.last_folder, structure.recursive, structure.search_query, structure.offset]);

	const refreshStructure = () => setStructure({...structure});

	const handleUpload = (folderId, uploadedFiles) => {
		setCurrentFolderId(folderId);
		setUploadedFile(uploadedFiles[0]);
	};

	const selectFile = useCallback(fileInfo => {
		props.selectFile(fileInfo);
		setUploadedFile(null);
		refreshFilesList();
		props.closeDialog();
	}, []);

	function scrollToCurrentFolder() {
		if (currentFolderElement) {
			currentFolderElement.scrollIntoView({behavior: 'smooth', block: 'center'});
		}
	}

	function dismissAndClose() {
		if (uploadedFile?.file_info) {
			const changeUrl = `${baseUrl}${uploadedFile.file_info.id}/change`;
			fetch(changeUrl, {
				method: 'DELETE',
				headers: {
					'X-CSRFToken': csrfToken,
				},
			}).then(async response => {
				if (response.ok) {
					props.selectFile(null);
				} else {
					alert(response.statusText);
				}
			});
		}
		setUploadedFile(null);
		refreshFilesList();
		props.closeDialog();
	}

	console.log('FileSelectDialog', structure);

	return (<>
		<div className="wrapper" ref={ref}>
			{uploadedFile ?
			<BrowserEditor
				uploadedFile={uploadedFile}
				mainContent={ref.current}
				settings={{csrfToken, baseUrl, selectFile, dismissAndClose, labels: structure.labels}}
			/> : <>
				<MenuBar
					refreshFilesList={refreshFilesList}
					setSearchQuery={setSearchQuery}
					openUploader={() => uploaderRef.current.openUploader()}
					labels={structure.labels}
					searchQuery={structure.search_query}
				/>
				<div className="browser-body">
					<nav className="folder-structure">
						<ul role="navigation">
							{structure.root_folder && <FolderStructure
								baseUrl={baseUrl}
								folder={structure.root_folder}
								lastFolderId={structure.last_folder}
								setCurrentFolder={setCurrentFolder}
								toggleRecursive={toggleRecursive}
								refreshStructure={refreshStructure}
								isListed={structure.recursive ? false : null}
								setCurrentFolderElement={setCurrentFolderElement}
							/>}
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
						<FilesList
							structure={structure}
							fetchFiles={fetchFiles}
							selectFile={selectFile}
						/>
					}</FileUploader>
				</div>
			</>}
		</div>
		<div
			className="close-button"
			role="button"
			onClick={dismissAndClose}
			aria-label={gettext("Close dialog")}
		>
			<CloseIcon/>
		</div>
		<Tooltip id="django-finder-tooltip" place="bottom-start"/>
	</>);
});

export default FileSelectDialog;
