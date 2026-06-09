import React, {
	createRef,
	useCallback,
	useContext,
	useEffect,
	useRef,
	useState
} from 'react';
import {
	DndContext,
	DragOverlay,
	PointerSensor,
	pointerWithin,
	useSensor,
	useSensors
} from '@dnd-kit/core';
import {restrictToWindowEdges} from '@dnd-kit/modifiers';
import {useAudioSettings, useCookie, useSessionStorage} from '../common/Storage';
import FileUploader from '../common/FileUploader';
import FinderSettings from './FinderSettings';
import FolderTabs from './FolderTabs';
import {VERBOSE_HTTP_ERROR_CODES} from './constants';
import MenuBar from './MenuBar';
import SelectableArea from './SelectableArea';
import InodeList from './InodeList';
import DraggedInodes from './DraggedInodes';
import DroppableArea from './DroppableArea';
import DownloadIcon from '../icons/download.svg';
import TrashIcon from '../icons/trash.svg';
import MoreVerticalIcon from '../icons/more-vertical.svg';

// eslint-disable-next-line react-hooks/rules-of-hooks
const useClipboard = useSessionStorage('filer-clipboard', []);


export default function FolderAdmin() {
	const settings = useContext(FinderSettings);
	const [audioSettings] = useAudioSettings();
	const [layout, setLayout] = useCookie('django-finder-layout', 'tiles');
	const [clipboard, setClipboard] = useClipboard();
	const [webAudio, setWebAudio] = useState(null);
	const menuBarRef = useRef(null);
	const folderTabsRef = useRef(null);
	const uploaderRef = useRef(null);
	const columnRefs = useRef(Object.fromEntries(settings.ancestors.map(ancestor => [ancestor.id, useRef(null)])));
	const overlayRef = useRef(null);
	const downloadLinkRef = useRef(null);
	const containerRef = useRef<HTMLElement>(null);
	const [busy, setBusy] = useState(false);
	const [currentFolderId, setCurrentFolderId] = useState(settings.folder_id);
	const [preselectedInode, setPreselectedInode] = useState(null);
	const [activeInode, setActiveInode] = useState(null);
	const [draggedInodes, setDraggedInodes] = useState([]);
	const [isSearchResult, setSearchResult] = useState<boolean>(() => {
		const params = new URLSearchParams(window.location.search);
		return params.get('q') !== null;
	});
	const [draggedInodesStyle, setDraggedInodesStyle] = useState({});
	const [zoomWhenDragging, setZoomWhenDragging] = useState(1);
	const sensors = useSensors(
		useSensor(PointerSensor, {
			activationConstraint: {distance: 4},
		}),
	);
	const dragModifiers = [modifyMovement, restrictToWindowEdges];
	const dragging = draggedInodes.length !== 0;
	const overlayStyle = {
		height: 'fit-content',
		width: 'fit-content',
	};

	useEffect(() => {
		containerRef.current = document.getElementById('content-react');

		const messagelist = document.querySelector('ul.messagelist') as HTMLUListElement;
		if (messagelist) {
			messagelist.classList.add('fade-out');
			setTimeout(() => {
				messagelist.remove();
			}, 5000);
		}

		document.documentElement.style.setProperty('--open-folder-url', `url("${settings.open_folder_icon_url}")`);

		// compute the top offset in order to restrict the height of the `.work-area`
		const headerElement = document.getElementById('header');
		let offsetTop = headerElement?.getBoundingClientRect().height ?? 0;
		if (headerElement?.nextElementSibling?.nodeName === 'NAV') {
			offsetTop += headerElement.nextElementSibling.getBoundingClientRect().height;
			document.documentElement.style.setProperty('--offset-top', `${offsetTop}px`);
		}
	}, []);

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
		containerRef.current?.classList.toggle('busy', busy);
	}, [busy]);

	function modifyMovement(args) {
		const {transform} = args;

		// when dragging elements, we want to offset the drag overlay
		let offsetX = 0, offsetY = 0;
		if (overlayRef.current && activeInode) {
			const activeDraggedElement = overlayRef.current.querySelector(`.inode-list [data-id="${activeInode.id}"]`);
			if (draggedInodes.length > 1) {
				const firstDraggedElement = overlayRef.current.querySelector(`.inode-list [data-id="${draggedInodes[0].id}"]`);
				if (firstDraggedElement && activeDraggedElement) {
					const firstClientRect = firstDraggedElement.getBoundingClientRect();
					const activeClientRect = activeDraggedElement.getBoundingClientRect();
					offsetX = (firstClientRect.left - activeClientRect.left) * zoomWhenDragging;
					offsetY = (firstClientRect.top - activeClientRect.top) * zoomWhenDragging;
				}
			} else if (activeDraggedElement) {
				if (layout === 'tiles') {
					if (activeDraggedElement.querySelector('figure img')?.getAttribute('src').endsWith('svg')) {
						offsetX = offsetY = -30;
					} else {
						offsetX = offsetY = -20;
					}
				} else if (layout === 'mosaic') {
					offsetX = offsetY = -23;
				} else if (layout === 'gallery') {
					offsetX = offsetY = -15;
				}
			}
		}

		return {
			...transform,
			x: transform.x + offsetX,
			y: transform.y + offsetY,
		};
	}

	const setCurrentFolder = useCallback((folderId: string) => {
		if (folderId !== currentFolderId) {
			deselectAll();
			setCurrentFolderId(folderId);
		}
	}, [currentFolderId]);

	const deselectAll = useCallback((event?) => {
		Object.entries(columnRefs.current).forEach(([folderId, columnRef]) => {
			columnRef.current?.deselectInodes();
		});
		menuBarRef.current.setSelected([]);
	}, [columnRefs]);

	const navigatePreselection = useCallback((event: KeyboardEvent) => {
		if (layout === 'columns' && ['ArrowLeft', 'ArrowRight'].includes(event.key)) {
			const currentColumnIndex = settings.ancestors.findIndex(ancestor => ancestor.id === currentFolderId);
			const nextColumnIndex = event.key === 'ArrowRight' ? currentColumnIndex - 1 : currentColumnIndex + 1;
			if (nextColumnIndex >= 0 && nextColumnIndex < settings.ancestors.length) {
				const nextFolderId = settings.ancestors[nextColumnIndex].id;
				setCurrentFolder(nextFolderId);
				columnRefs.current[nextFolderId].current?.navigatePreselection(event);
			}
		} else {
			columnRefs.current[currentFolderId].current?.navigatePreselection(event);
		}
	}, [currentFolderId, layout]);

	const clearClipboard = useCallback(() => {
		setClipboard([]);
		Object.entries(columnRefs.current).forEach(([folderId, columnRef]) => {
			columnRef.current?.setInodes(columnRef.current?.inodes.map(inode =>
				({...inode, cutted: false, copied: false})
			));
		});
	}, [columnRefs]);

	function downloadFiles(inodes) {
		inodes.forEach(inode => {
			downloadLinkRef.current.href = inode.download_url;
			downloadLinkRef.current.download = inode.name;
			downloadLinkRef.current.click();
		});
		deselectAll();
	}

	function refreshColumns() {
		Object.entries(columnRefs.current as React.MutableRefObject<any>).forEach(([folderId, columnRef]) => {
			columnRef.current?.fetchInodes();
		});
	}

	function computeBoundingBox(inodes) {
		let zoom = 1, gap = 1;
		if (inodes.length === 0) {
			setDraggedInodesStyle({width: 0, height: 0});
		} else {
			const workAreaRect = settings.workAreaRect;
			const inodeBox = inodes[0].elementRef.current.getBoundingClientRect();
			if (layout === 'tiles') {
				if (inodes.length > 16) {
					zoom = 0.1;
				} else if (inodes.length > 1) {
					zoom = 0.5;
				}
				gap = 10;
			} else if (layout === 'mosaic') {
				if (inodes.length > 64) {
					zoom = 0.1;
				} else if (inodes.length > 4) {
					zoom = 0.5;
				}
				gap = 5;
			} else if (layout === 'gallery') {
				if (inodes.length > 16) {
					zoom = 0.5;
				}
				gap = 2;
			}
			if (['tiles', 'mosaic', 'gallery'].includes(layout)) {
				const squareRoot = Math.sqrt(inodes.length);
				const width = Math.min(Math.ceil(squareRoot) * (inodeBox.width * zoom + gap) - gap, workAreaRect.width - 10);
				const height = Math.min(Math.floor(squareRoot + 0.5) * inodeBox.height * zoom, workAreaRect.height - 10);
				setDraggedInodesStyle({width: width, height: height});
			} else {
				setDraggedInodesStyle({
					width: inodeBox.width,
					height: Math.min(inodes.length * inodeBox.height, workAreaRect.height - 15),
				});
			}
		}
		setZoomWhenDragging(zoom);
	}

	function handleDragStart(event) {
		const {active} = event;
		const folderId = active.data.current.folderId;
		let inodes = columnRefs.current[folderId].current?.inodes ?? [];
		const multipleSelected = inodes.some(inode => inode.selected && inode.id === active.id);
		overlayRef.current.hidden = false;
		inodes = multipleSelected
			? inodes.map(inode => ({...inode, dragged: inode.selected}))
			: inodes.map(inode => ({...inode, dragged: inode.id === active.id, selected: false}));
		computeBoundingBox(inodes.filter(inode => inode.dragged));
		columnRefs.current[folderId].current.setInodes(inodes);
		setDraggedInodes(inodes.filter(inode => inode.dragged));
		setActiveInode(active);
		setCurrentFolder(folderId);
	}

	async function handleDragEnd(event) {
		const {active, over} = event;
		const sourceFolderId = active.data.current.folderId;
		let inodes = columnRefs.current[sourceFolderId].current?.inodes ?? [];
		if (over) {
			let [what, targetInodeId, targetFolderId] = over.id.split(':');
			if (targetFolderId === undefined) {
				targetFolderId = targetInodeId === 'parent' ? settings.parent_id : targetInodeId;
			}
			if (!draggedInodes.some(inode => [inode.id, inode.parent].includes(targetInodeId))) {
				overlayRef.current.hidden = true;
				let action: string;
				switch (what) {
					case 'download':
						downloadFiles(draggedInodes);
						setTimeout(() => {
							overlayRef.current.hidden = false;
							setDraggedInodes([]);
						}, 1000);
						return;
					case 'folder': case 'column': case 'tab':
						action = 'move';
						break;
					case 'discard':
						action = 'delete';
						break;
					case 'reorder':
						action = 'reorder';
						break;
					default:
						console.error(`Unknown drop target: ${what}`);
						return;
				}
				setBusy(true);
				try {
					let fetchUrl = `${settings.base_url}${settings.folder_id}/${action}`;
					const response = await fetch(fetchUrl, {
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							'X-CSRFToken': settings.csrf_token,
						},
						body: JSON.stringify({
							inode_ids: draggedInodes.map(inode => inode.id),
							target_id: targetInodeId,
						}),
					});
					if (response.ok) {
						const body = await response.json();
						if (body.inodes && columnRefs.current[targetFolderId]?.current) {
							const targetInodes = body.inodes.map(inode => ({...inode, elementRef: createRef()}));
							columnRefs.current[targetFolderId].current.setInodes(targetInodes);
							if (sourceFolderId === targetFolderId) {
								inodes = targetInodes;
							}
						}
						if (body.favorite_folders) {
							folderTabsRef.current.setFavoriteFolders(body.favorite_folders);
						}
						if (sourceFolderId !== targetFolderId) {
							inodes = inodes.filter(inode => !(inode.can_change && inode.dragged));
						}
					} else if (VERBOSE_HTTP_ERROR_CODES.has(response.status)) {
						alert(await response.text());
					} else {
						console.error(response);
					}
				} finally {
					setBusy(false);
					overlayRef.current.hidden = false;
				}
			}
		}
		columnRefs.current[sourceFolderId].current.setInodes(inodes.map(inode => ({...inode, dragged: false})));
		setActiveInode(null);
		setDraggedInodes([]);
	}

	const handleUpload = (folderId, uploadedFiles) => {
		columnRefs.current[folderId].current.fetchInodes();
	};

	function handleDragCancel(event) {
		const {active} = event;
		const activeFolderId = active.data.current.folderId;
		const inodes = columnRefs.current[activeFolderId].current.inodes;
		columnRefs.current[activeFolderId].current.setInodes(inodes.map(inode => ({...inode, dragged: false})));
		setActiveInode(null);
		setDraggedInodes([]);
	}

	function renderTrashArea() {
		return (
			<div className={`work-area ${layout}`}>
				<SelectableArea
					deselectAll={deselectAll}
					columnRef={columnRefs.current[settings.folder_id]}
					dragging={dragging}
				>
					<InodeList
						ref={columnRefs.current[settings.folder_id]}
						folderId={settings.folder_id}
						sortingDisabled={true}
						setCurrentFolder={setCurrentFolder}
						listRef={columnRefs.current[settings.folder_id]}
						menuBarRef={menuBarRef}
						layout={layout}
						clipboard={clipboard}
						setClipboard={setClipboard}
						clearClipboard={clearClipboard}
						preselectedInode={preselectedInode}
						setPreselectedInode={setPreselectedInode}
						settings={settings}
					/>
				</SelectableArea>
			</div>
		);
	}

	function renderWorkArea() {
		let incomplete = false;
		function renderAncestors() {
			const ancestors = [settings.ancestors[0]];
			if (layout === 'columns' && !isSearchResult && settings.workAreaRect) {
				const maxNumAncestors = Math.min(
					Math.floor(settings.workAreaRect.width / 350),
					settings.ancestors.length,
				);
				for (let i = 1; i < maxNumAncestors; i++) {
					ancestors.push(settings.ancestors[i]);
				}
				incomplete = ancestors.length < settings.ancestors.length;
			}
			let previousAncestorId = null;
			return ancestors.map(ancestor => {
				const snippet = (
					<FileUploader
						key={ancestor.id}
						ref={ancestor.id === settings.folder_id ? uploaderRef : null}
						folderId={ancestor.id}
						disabled={!ancestor.can_change}
						handleUpload={handleUpload}
						settings={settings}
						multiple
					>
						<SelectableArea
							folderId={ancestor.id}
							deselectAll={deselectAll}
							columnRef={columnRefs.current[ancestor.id]}
							dragging={dragging}
						>
							<DroppableArea
								id={`column:${ancestor.id}`}
								className="column-droppable"
								currentId={`column:${currentFolderId}`}
								dragging={dragging}
							>
								<InodeList
									ref={columnRefs.current[ancestor.id]}
									folderId={ancestor.id}
									ancestorFolderId={previousAncestorId}
									sortingDisabled={!ancestor.can_change}
									setCurrentFolder={setCurrentFolder}
									listRef={columnRefs.current[ancestor.id]}
									menuBarRef={menuBarRef}
									folderTabsRef={folderTabsRef}
									layout={layout}
									webAudio={webAudio}
									clipboard={clipboard}
									setClipboard={setClipboard}
									clearClipboard={clearClipboard}
									preselectedInode={preselectedInode}
									setPreselectedInode={setPreselectedInode}
									settings={settings}
								/>
							</DroppableArea>
						</SelectableArea>
					</FileUploader>
				);
				previousAncestorId = ancestor.id;
				return snippet;
			});
		}

		return (<>
			<div className={`work-area ${layout}`}>
				{renderAncestors()}
				{incomplete && <div className="trimmed-column"><MoreVerticalIcon/></div>}
			</div>
			{renderDroppables()}
		</>);
	}

	function renderDroppables() {
		return (<>
			<DroppableArea id="download:droppable" className="download-droppable" dragging={dragging}>
				<div className="quadrant"><DownloadIcon /></div>
			</DroppableArea>
			<a ref={downloadLinkRef} download="download" hidden />
			<DroppableArea id="discard:droppable" className="discard-droppable" dragging={dragging}>
				<div className="quadrant"><TrashIcon /></div>
			</DroppableArea>
		</>);
	}

	return (<>
		<MenuBar
			ref={menuBarRef}
			currentFolderId={currentFolderId}
			currentColumns={columnRefs.current}
			folderTabsRef={folderTabsRef}
			openUploader={(isFolder: boolean) => uploaderRef.current.openUploader(isFolder)}
			downloadFiles={downloadFiles}
			layout={layout}
			setLayout={setLayout}
			webAudio={webAudio}
			deselectAll={deselectAll}
			navigatePreselection={navigatePreselection}
			refreshColumns={refreshColumns}
			clipboard={clipboard}
			setClipboard={setClipboard}
			clearClipboard={clearClipboard}
			setSearchResult={setSearchResult}
			setBusy={setBusy}
			settings={settings}
		/>
		<DndContext
			onDragStart={handleDragStart}
			onDragEnd={handleDragEnd}
			onDragCancel={handleDragCancel}
			sensors={sensors}
			collisionDetection={pointerWithin}
			autoScroll={true}
		>
			<FolderTabs ref={folderTabsRef} isSearchResult={isSearchResult} settings={settings} />
			{settings.is_trash ? renderTrashArea() : renderWorkArea()}
			<div ref={overlayRef} className="drag-overlay">
				<DragOverlay className={layout} style={overlayStyle} modifiers={dragModifiers}>
					<DraggedInodes
						inodes={draggedInodes}
						layout={layout}
						style={draggedInodesStyle}
						zoom={zoomWhenDragging}
					/>
				</DragOverlay>
			</div>
		</DndContext>
	</>);
}
