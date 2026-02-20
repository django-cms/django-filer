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
import FileTags from '../common/FileTags';
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
		<figure className="figure" aria-selected={props.isSelected}>
			<FigBody {...props}>
				<FileTags tags={props.tags}>
					<img src={props.thumbnail_url} {...props.listeners} {...props.attributes} />
				</FileTags>
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


const FilesList = memo(function FilesList(props: any) {
	const {structure, setDirty, isDirty, selectFile, selectedFileId, webAudio} = props;

	return (
		<ul className="files-browser">{
		structure.files.length === 0 ?
			(!isDirty && <li className="status">{gettext("Empty folder")}</li>) : (
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


interface FileStructure {
	root_folder: object | null;
	last_folder: string | null;
	files: any[] | null;
	has_upload_permission: boolean;
	offset: number | null;
	recursive: boolean;
	search_query: string;
	tags: any[];
}


const FileSelectDialog = forwardRef(function FileSelectDialog(props: any, forwardedRef) {
	const {ambit, baseUrl, mimeTypes, csrfToken, selectedFileId, dialogRef} = props;
	const selectedFolderIdRef = useRef(props.selectedFolderId);
	selectedFolderIdRef.current = props.selectedFolderId;
	const structureRef = useRef<FileStructure>(null);
	const [structure, setStructureState] = useState<FileStructure>(() => {
		const initial: FileStructure = {
			root_folder: null,
			last_folder: null,
			files: null,
			has_upload_permission: false,
			offset: null,
			recursive: false,
			search_query: '',
			tags: [],
		};
		structureRef.current = initial;
		return initial;
	});
	const setStructure = useCallback((update: FileStructure | ((prev: FileStructure) => FileStructure)) => {
		setStructureState(prev => {
			const next = typeof update === 'function' ? update(prev) : update;
			structureRef.current = next;
			return next;
		});
	}, []);
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
		if (!dialogRef.current)
			return;

		const observer = new MutationObserver((mutations) => {
			for (const mutation of mutations) {
				if (mutation.attributeName === 'open' && dialogRef.current.open && structure.root_folder === null) {
					initializeStructure();
				}
			}
		});
		observer.observe(dialogRef.current, {attributes: true});

		return () => observer.disconnect();
	}, []);

	useEffect(() => {
		if (isDirty) {
			fetchFiles();
		}
	}, [isDirty]);

	function setCurrentFolderId(folderId){
		setStructure(prev => ({
			...prev,
			last_folder: folderId,
			files: [],
			offset: null,
			recursive: false,
			search_query: '',
		}));
		setDirty(true);
		menuBarRef.current.clearSearch();
	}

	function refreshFilesList() {
		setStructure(prev => ({
			...prev,
			files: [],
			offset: null,
		}));
		setDirty(true);
	}

	function changeSearchZone(value) {
		if (value !== searchZone) {
			setSearchZone(value);
			setStructure(prev => ({
				...prev,
				files: [],
				offset: null,
			}));
			setDirty(true);
		}
	}

	 function toggleRecursive(folderId: string) {
		setStructure(prev => ({
			...prev,
			last_folder: folderId,
			files: [],
			offset: null,
			recursive: !prev.recursive,
		}));
		setDirty(true);
	}

	function setSearchQuery(query) {
		setStructure(prev => ({
			...prev,
			files: [],
			offset: null,
			recursive: false,
			search_query: query,
		}));
		setDirty(true);
	}

	async function initializeStructure() {
		const params = new URLSearchParams();
		if (selectedFolderIdRef.current) {
			params.append('folder', selectedFolderIdRef.current);
		}
		mimeTypes?.forEach(type => params.append('mimetypes', type));
		setDirty(false);
		const response = await fetch(`${baseUrl}structure/${ambit}${params.size === 0 ? '' : `?${params.toString()}`}`);
		if (response.ok) {
			const body = await response.json();
			setStructure(body);
			window.setTimeout(() => {
				// first show the structure from the root for orientation, then scroll to the current folder
				const currentListItem = ref.current.querySelector('ul[role="navigation"] li:has(>[aria-current="true"])');
				if (currentListItem) {
					currentListItem.scrollIntoView({behavior: 'smooth', block: 'center'});
				}
			}, 999);
		} else {
			console.error(response);
		}
	}

	async function fetchFiles() {
		const currentStructure = structureRef.current;

		const fetchUrl = (() => {
			const params = new URLSearchParams();
			mimeTypes?.forEach(type => params.append('mimetypes', type));
			if (currentStructure.recursive) {
				params.set('recursive', '');
			}
			if (currentStructure.offset !== null) {
				params.set('offset', String(currentStructure.offset));
			}
			if (currentStructure.search_query) {
				params.set('q', currentStructure.search_query);
				return `${baseUrl}${currentStructure.last_folder}/search?${params.toString()}`;
			}
			return `${baseUrl}${currentStructure.last_folder}/list${params.size === 0 ? '' : `?${params.toString()}`}`;
		})();
		const response = await fetch(fetchUrl);
		if (response.ok) {
			const body = await response.json();
			setStructure(prev => ({
				...prev,
				files: prev.files.concat(body.files),
				has_upload_permission: body.has_upload_permission,
				offset: body.offset,
			}));
			setDirty(false);
		} else {
			console.error(response);
		}
	}

	function handleUpload(folderId, uploadedFiles) {
		if (structureRef.current.last_folder !== folderId)
			throw new Error('Folder mismatch');
		setUploadedFile(uploadedFiles[0]);
	}

	const selectFile = useCallback(fileInfo => {
		if (props.selectFile) {
			props.selectFile(fileInfo);
			setUploadedFile(null);
			refreshFilesList();
			dialogRef.current.close();
		}
	}, []);

	const selectFolder = useCallback(folder => {
		if (props.selectFolder) {
			props.selectFolder(folder);
			dialogRef.current.close();
		} else if (structureRef.current.last_folder !== folder.id) {
			setCurrentFolderId(folder.id);
		}
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
		dialogRef.current.close();
	}

	return (<>
		<div className="wrapper" ref={ref}>
			{uploadedFile ?
			<BrowserEditor
				uploadedFile={uploadedFile}
				mainContent={ref.current}
				settings={{csrfToken, baseUrl, selectFile, dismissAndClose, tags: structure.tags}}
			/> : <>
				<MenuBar
					ref={menuBarRef}
					openUploader={() => uploaderRef.current.openUploader()}
					tags={structure.tags}
					refreshFilesList={refreshFilesList}
					setDirty={setDirty}
					setSearchQuery={setSearchQuery}
					searchZone={searchZone}
					setSearchZone={changeSearchZone}
					hasUploadPermission={structure.has_upload_permission}
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
								refreshStructure={() => setStructure(prev => ({...prev}))}
								isListed={structure.recursive ? false : null}
								setCurrentFolderId={setCurrentFolderId}
								setCurrentFolderElement={setCurrentFolderElement}
							/>
						}</ul>
					</nav>
					<FileUploader
						folderId={structure.last_folder}
						disabled={!structure.has_upload_permission}
						handleUpload={handleUpload}
						ref={uploaderRef}
						settings={{csrf_token: csrfToken, base_url: baseUrl}}
					>
					{Array.isArray(structure.files) ?
						<FilesList
							structure={structure}
							setDirty={setDirty}
							isDirty={isDirty}
							selectFile={selectFile}
							selectedFileId={selectedFileId}
							webAudio={webAudio}
						/>
						:
						<div className="status">{gettext("Loading structure…")}</div>
					}
					{isDirty && <div className="status">{gettext("Loading files…")}</div>}
					</FileUploader>
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
