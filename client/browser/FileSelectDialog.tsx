import React, {
	forwardRef,
	lazy,
	memo,
	Suspense,
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
		onChange: (loadMore) => {
			if (loadMore && !inView) {
				fetchFiles();
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
			{structure.offset !== null && <ScrollSpy fetchFiles={fetchFiles} />}
			</>
		)}</ul>
	);
});


const FileSelectDialog = forwardRef((props: any, forwardedRef) => {
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
	const dialog = ref.current?.closest('dialog');

	useEffect(() => {
		if (!uploadedFile) {
			getStructure();
		}
	}, [uploadedFile]);

	useImperativeHandle(forwardedRef, () => ({dismissAndClose}));

	const setCurrentFolder = (folderId) => {
		setStructure(prevStructure => {
			const newStructure = Object.assign(structure, {
				...prevStructure,
				last_folder: folderId,
				files: [],
				offset: null,
				recursive: false,
				search_query: '',
			});
			fetchFiles();
			return newStructure;
		});
	};

	async function toggleRecursive(folderId: string) {
		setStructure(prevStructure => {
			const newStructure = Object.assign(structure, {
				...prevStructure,
				last_folder: folderId,
				files: [],
				offset: null,
				recursive: prevStructure.recursive ? false : true,
				search_query: '',
			});
			fetchFiles();
			return newStructure;
		});
	}

	const setSearchQuery = (query) => {
		setStructure(prevStructure => {
			const newStructure = Object.assign(structure, {
				...prevStructure,
				files: [],
				offset: null,
				recursive: false,
				search_query: query,
			});
			fetchFiles();
			return newStructure;
		});
	};

	const refreshFilesList = () => {
		setStructure(prevStructure => {
			const newStructure = Object.assign(structure, {
				root_folder: prevStructure.root_folder,
				files: [],
				last_folder: prevStructure.last_folder,
				offset: null,
				search_query: prevStructure.search_query,
				labels: prevStructure.labels,
			});
			fetchFiles();
			return newStructure;
		});
	};

	async function getStructure() {
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
			return `${baseUrl}${structure.last_folder}/list?${params.toString()}`;
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
	}

	function refreshStructure() {
		setStructure({...structure});
	}

	function handleUpload(folderId, uploadedFiles) {
		setUploadedFile(uploadedFiles[0]);
	}

	function selectFile(fileInfo) {
		props.selectFile(fileInfo);
		setUploadedFile(null);
		props.closeDialog();
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
		props.closeDialog();
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
						refreshFilesList={refreshFilesList}
						setSearchQuery={setSearchQuery}
						openUploader={() => uploaderRef.current.openUploader()}
						labels={structure.labels}
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
