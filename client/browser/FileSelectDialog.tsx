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
import FigureLabels from '../common/FigureLabels';
import FileUploader from '../common/FileUploader';
import {useSearchZone} from '../common/Storage';
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


function ScrollSpy(props) {
	const {setDirty} = props;
	const {ref, inView} = useInView({
		triggerOnce: true,
		onChange: async (loadMore) => {
			if (loadMore && !inView) {
				setDirty(true);
			}
		},
	});
	return (
		<div className="scroll-spy" ref={ref}></div>
	);
}


const FilesList = memo((props: any) => {
	const {structure, setDirty, selectFile} = props;

	return (
		<ul className="files-browser">{
		structure.files.length === 0 ?
			<li className="status">{gettext("Empty folder")}</li> : (
			<>{structure.files.map(file => (
			<li key={file.id} onClick={() => selectFile(file)}><Figure {...file} /></li>
			))}
			{structure.offset !== null && <ScrollSpy key={structure.offset} setDirty={setDirty} />}
			</>
		)}</ul>
	);
});


const FileSelectDialog = forwardRef((props: any, forwardedRef) => {
	const {realm, baseUrl, mimeTypes, csrfToken} = props;
	const [structure, setStructure] = useState({
		root_folder: null,
		last_folder: null,
		files: null,
		offset: null,
		recursive: false,
		search_query: '',
		labels: [],
	});
	const [isDirty, setDirty] = useState(false);
	const ref = useRef(null);
	const uploaderRef = useRef(null);
	const menuBarRef = useRef(null);
	const [uploadedFile, setUploadedFile] = useState(null);
	const [currentFolderElement, setCurrentFolderElement] = useState(null);
	const [searchZone, setSearchZone] = useSearchZone('current');

	useImperativeHandle(forwardedRef, () => ({scrollToCurrentFolder, dismissAndClose}));

	useEffect(() => {
		if (structure.root_folder === null) {
			initializeStructure();
		} else if (isDirty) {
			fetchFiles();
		}
	}, [isDirty]);

	function setCurrentFolder(folderId){
		setStructure({
			...structure,
			last_folder: folderId,
			files: [],
			offset: null,
			recursive: false,
			search_query: '',
		});
		setDirty(true);
		menuBarRef.current.clearSearch();
	}

	function refreshFilesList() {
		setStructure({
			...structure,
			files: [],
			offset: null,
		});
		setDirty(true);
	}

	function changeSearchZone(value) {
		if (value !== searchZone) {
			setSearchZone(value);
			setStructure({
				...structure,
				files: [],
				offset: null,
			});
			setDirty(true);
		}
	}

	 function toggleRecursive(folderId: string) {
		setStructure({
			...structure,
			last_folder: folderId,
			files: [],
			offset: null,
			recursive: structure.recursive ? false : true,
		});
		setDirty(true);
	}

	function setSearchQuery(query) {
		setStructure({
			...structure,
			files: [],
			offset: null,
			recursive: false,
			search_query: query,
		});
		setDirty(true);
	}

	async function initializeStructure() {
		setDirty(false);
		const response = await fetch(`${baseUrl}structure/${realm}`);
		if (response.ok) {
			setStructure(await response.json());
		} else {
			console.error(response);
		}
	}

	async function fetchFiles() {
		const fetchUrl = (() => {
			const params = new URLSearchParams();
			mimeTypes.forEach(type => params.append('mimetypes', type));
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
			setDirty(false);
		} else {
			console.error(response);
		}
	}

	function handleUpload(folderId, uploadedFiles) {
		if (structure.last_folder !== folderId)
			throw new Error('Folder mismatch');
		setUploadedFile(uploadedFiles[0]);
	}

	const selectFile = useCallback(fileInfo => {
		props.selectFile(fileInfo);
		setUploadedFile(null);
		refreshFilesList();
		props.dialogRef.current.close();
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
		props.dialogRef.current.close();
	}

	return (<>
		<div className="wrapper" ref={ref}>
			{uploadedFile ?
			<BrowserEditor
				uploadedFile={uploadedFile}
				mainContent={ref.current}
				settings={{csrfToken, baseUrl, selectFile, dismissAndClose, labels: structure.labels}}
			/> : <>
				<MenuBar
					ref={menuBarRef}
					openUploader={() => uploaderRef.current.openUploader()}
					labels={structure.labels}
					refreshFilesList={refreshFilesList}
					setDirty={setDirty}
					setSearchQuery={setSearchQuery}
					searchZone={searchZone}
					setSearchZone={changeSearchZone}
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
								refreshStructure={() => setStructure({...structure})}
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
							setDirty={setDirty}
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
	</>);
});

export default FileSelectDialog;
