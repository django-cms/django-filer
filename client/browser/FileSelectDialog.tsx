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
import {useAudioSettings, useSearchZone} from '../common/Storage';
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
	}, []);

	return (
		<figure className="figure">
			<FigBody {...props}>
				<FigureLabels labels={props.labels}>
					<img src={props.thumbnail_url} {...props.listeners} {...props.attributes} aria-selected={props.isSelected} />
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
	const {structure, setDirty, selectFile, selectedFileId, webAudio} = props;

	return (
		<ul className="files-browser">{
		structure.files.length === 0 ?
			<li className="status">{gettext("Empty folder")}</li> : (
			<>{structure.files.map(file => (
			<li key={file.id} onClick={() => selectFile(file)}>
				<Figure {...file} webAudio={webAudio} isSelected={file.id === selectedFileId} />
			</li>
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
	const [audioSettings] = useAudioSettings();
	const [webAudio, setWebAudio] = useState(null);
	const menuBarRef = useRef(null);
	const [uploadedFile, setUploadedFile] = useState(null);
	const [currentFolderElement, setCurrentFolderElement] = useState(null);
	const [searchZone, setSearchZone] = useSearchZone('current');

	useImperativeHandle(forwardedRef, () => ({scrollToCurrentFolder, dismissAndClose}));

	useEffect(() => {
		const context = new window.AudioContext();
		const gainNode = context.createGain();
		gainNode.connect(context.destination);
		gainNode.gain.value = audioSettings.volume;
		setWebAudio({context, gainNode});

		return () => {
			if (webAudio) {
				webAudio.context.close();
			}
		};
	}, []);

	useEffect(() => {
		if (structure.root_folder === null) {
			initializeStructure();
		} else if (isDirty) {
			fetchFiles();
		}
	}, [isDirty]);

	function setCurrentFolderId(folderId){
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
		const params = new URLSearchParams();
		mimeTypes?.forEach(type => params.append('mimetypes', type));
		setDirty(false);
		const response = await fetch(`${baseUrl}structure/${realm}${params.size === 0 ? '' : `?${params.toString()}`}`);
		if (response.ok) {
			setStructure(await response.json());
		} else {
			console.error(response);
		}
	}

	async function fetchFiles() {
		const fetchUrl = (() => {
			const params = new URLSearchParams();
			mimeTypes?.forEach(type => params.append('mimetypes', type));
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
		if (props.selectFile) {
			props.selectFile(fileInfo);
			setUploadedFile(null);
			refreshFilesList();
			props.dialogRef.current.close();
		}
	}, []);

	const selectFolder = useCallback(folder => {
		if (props.selectFolder) {
			props.selectFolder(folder);
			props.dialogRef.current.close();
		} else if (structure.last_folder !== folder.id) {
			setCurrentFolderId(folder.id);
		}
	}, [structure.last_folder]);

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
					webAudio={webAudio}
				/>
				<div className="browser-body">
					<nav className="folder-structure">
						<ul role="navigation">{
							structure.root_folder && <FolderStructure
								baseUrl={baseUrl}
								folder={structure.root_folder}
								lastFolderId={structure.last_folder}
								selectFolder={selectFolder}
								selectedFolderId={props.selectedFolderId}
								toggleRecursive={toggleRecursive}
								refreshStructure={() => setStructure({...structure})}
								isListed={structure.recursive ? false : null}
								setCurrentFolderId={setCurrentFolderId}
								setCurrentFolderElement={setCurrentFolderElement}
							/>
						}</ul>
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
							selectedFileId={props.selectedFileId}
							webAudio={webAudio}
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
