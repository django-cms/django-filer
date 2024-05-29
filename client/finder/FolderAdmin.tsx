import React, {
	createRef,
	useContext,
	useEffect,
	useRef,
	useState
} from 'react';
import {Tooltip} from 'react-tooltip';
import {
	DndContext,
	DragOverlay,
	PointerSensor,
	pointerWithin,
	useSensor,
	useSensors
} from '@dnd-kit/core';
import {restrictToWindowEdges} from '@dnd-kit/modifiers';
import {useCookie} from './Storage';
import {FinderSettings} from './FinderSettings';
import {FileUploader} from './FileUploader';
import {FolderTabs} from './FolderTabs';
import {MenuBar} from './MenuBar';
import {SelectableArea} from './SelectableArea';
import {DraggedInodes, InodeList} from './InodeList';
import {DroppableArea} from './Droppable';
import DownloadIcon from 'icons/download.svg';
import TrashIcon from 'icons/trash.svg';
import MoreVerticalIcon from 'icons/more-vertical.svg';

const useLayout = (initial: string) => useCookie('django-finder-layout', initial);


export function FolderAdmin(props) {
	const settings = useContext(FinderSettings);
	const menuBarRef = useRef(null);
	const folderTabsRef = useRef(null);
	const uploaderRef = useRef(null);
	const columnRefs = Object.fromEntries(settings.ancestors.map(id => [id, useRef(null)]));
	const overlayRef = useRef(null);
	const downloadLinkRef = useRef(null);
	const [currentFolderId, setCurrentFolderId] = useState(settings.folder_id);
	const [layout, setLayout] = useLayout('tiles');
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
	const overlayStyle = {
		height: 'fit-content',
		width: 'fit-content',
	};

	useEffect(() => {
		const messagelist = document.querySelector('ul.messagelist') as HTMLUListElement;
		if (messagelist) {
			messagelist.classList.add('fade-out');
			setTimeout(() => {
				messagelist.remove();
			}, 5000);
		}
	}, []);

	function modifyMovement(args) {
		const {transform} = args;

		// when dragging elements, we want to offset the drag overlay
		let offsetX = 0, offsetY = 0;
		if (overlayRef.current && activeInode) {
			const activeDraggedElement = overlayRef.current.querySelector(`.inode-list [data-id="${activeInode.id}"]`);
			if (draggedInodes.length > 1) {
				const firstDraggedElement = overlayRef.current.querySelector(`.inode-list [data-id="${draggedInodes[0].id}"]`);
				if (firstDraggedElement && activeDraggedElement) {
					offsetX = (firstDraggedElement.getBoundingClientRect().left - activeDraggedElement.getBoundingClientRect().left) * zoomWhenDragging;
					offsetY = (firstDraggedElement.getBoundingClientRect().top - activeDraggedElement.getBoundingClientRect().top) * zoomWhenDragging;
				}
			} else if (activeDraggedElement && ['tiles', 'mosaic'].includes(layout)) {
				offsetX = -15;
				offsetY = -15;
			}
		}

		return {
			...transform,
			x: transform.x + offsetX,
			y: transform.y + offsetY,
		};
	}

	function setCurrentFolder(folderId) {
		if (folderId !== currentFolderId) {
			deselectAll();
		}
		setCurrentFolderId(folderId);
	}

	function deselectAll(event?) {
		Object.entries(columnRefs).forEach(([folderId, columnRef]) => {
			columnRef.current?.deselectInodes();
		});
		menuBarRef.current?.setSelected([]);
	}

	function downloadFiles(inodes) {
		inodes.forEach(inode => {
			downloadLinkRef.current.href = inode.download_url;
			downloadLinkRef.current.download = inode.name;
			downloadLinkRef.current.click();
		});
		deselectAll();
	}

	function computeBoundingBox(inodes) {
		let zoom = 1;
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
			} else if (layout === 'mosaic') {
				if (inodes.length > 64) {
					zoom = 0.1;
				} else if (inodes.length > 4) {
					zoom = 0.5;
				}
			}
			if (['tiles', 'mosaic'].includes(layout)) {
				const squareRoot = Math.sqrt(inodes.length);
				const gap = (layout === 'tiles' ? 10 : 5);
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
		let inodes = columnRefs[folderId].current?.inodes ?? [];
		const multipleSelected = inodes.some(inode => inode.selected && inode.id === active.id);
		overlayRef.current.hidden = false;
		inodes = multipleSelected
			? inodes.map(inode => ({...inode, dragged: inode.selected}))
			: inodes.map(inode => ({...inode, dragged: inode.id === active.id, selected: false}));
		computeBoundingBox(inodes.filter(inode => inode.dragged));
		columnRefs[folderId].current.setInodes(inodes);
		setDraggedInodes(inodes.filter(inode => inode.dragged));
		setActiveInode(active);
		setCurrentFolder(folderId);
	}

	async function handleDragEnd(event) {
		const {active, over} = event;
		const sourceFolderId = active.data.current.folderId;
		let inodes = columnRefs[sourceFolderId].current?.inodes ?? [];
		if (over) {
			let [what, targetFolderId] = over.id.split(':');
			targetFolderId = targetFolderId === 'parent' ? settings.parent_id : targetFolderId;
			if (!draggedInodes.some(inode => [inode.id, inode.parent].includes(targetFolderId))) {
				overlayRef.current.hidden = true;
				if (what === 'download') {
					downloadFiles(draggedInodes);
					setTimeout(() => {
						overlayRef.current.hidden = false;
						setDraggedInodes([]);
					}, 1000);
					return;
				}
				let fetchUrl = `${settings.base_url}${settings.folder_id}/${what === 'discard' ? 'delete' : 'move'}`;
				const response = await fetch(fetchUrl, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						'X-CSRFToken': settings.csrf_token,
					},
					body: JSON.stringify({
						inode_ids: draggedInodes.map(inode => inode.id),
						target_folder: targetFolderId,
					}),
				});
				if (response.ok) {
					const body = await response.json();
					if (body.inodes && columnRefs[targetFolderId]?.current) {
						const inodes = body.inodes.map(inode => ({...inode, elementRef: createRef()}));
						columnRefs[targetFolderId].current.setInodes(inodes);
					}
					if (body.favorite_folders) {
						folderTabsRef.current.setFavoriteFolders(body.favorite_folders);
					}
					inodes = inodes.filter(inode => !inode.dragged);
					columnRefs[sourceFolderId].current.setInodes(inodes);
				} else if (response.status === 409) {
					alert(await response.text());
				} else {
					console.error(response);
				}
				overlayRef.current.hidden = false;
			}
		}
		columnRefs[sourceFolderId].current.setInodes(inodes.map(inode => ({...inode, dragged: false})));
		setActiveInode(null);
		setDraggedInodes([]);
	}

	function handleDragCancel(event) {
		const {active} = event;
		const activeFolderId = active.data.current.folderId;
		const inodes = columnRefs[activeFolderId].current.inodes;
		columnRefs[activeFolderId].current.setInodes(inodes.map(inode => ({...inode, dragged: false})));
		setActiveInode(null);
		setDraggedInodes([]);
	}

	function renderTrashArea() {
		return (
			<div className={`work-area ${layout}`}>
				<SelectableArea folderId={settings.folder_id} deselectAll={deselectAll} columnRef={columnRefs[settings.folder_id]}>
					<InodeList
						ref={columnRefs[settings.folder_id]}
						folderId={settings.folder_id}
						setCurrentFolder={setCurrentFolder}
						listRef={columnRefs[settings.folder_id]}
						menuBarRef={menuBarRef}
						layout={layout}
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
			let previousFolderId = null;
			return ancestors.map(folderId => {
				const snippet = (
					<FileUploader
						key={folderId}
						ref={folderId === settings.folder_id ? uploaderRef : null}
						folderId={folderId}
						handleUpload={id => columnRefs[id].current.fetchInodes()}
					>
						<SelectableArea
							folderId={folderId}
							deselectAll={deselectAll}
							columnRef={columnRefs[folderId]}
						>
							<DroppableArea
								id={`column:${folderId}`}
								className="column-droppable"
								currentId={`column:${currentFolderId}`}
							>
								<InodeList
									ref={columnRefs[folderId]}
									folderId={folderId}
									previousFolderId={previousFolderId}
									setCurrentFolder={setCurrentFolder}
									listRef={columnRefs[folderId]}
									menuBarRef={menuBarRef}
									folderTabsRef={folderTabsRef}
									layout={layout}
								/>
							</DroppableArea>
						</SelectableArea>
					</FileUploader>
				);
				previousFolderId = folderId;
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
			<DroppableArea id="download:droppable" className="download-droppable" dragging={draggedInodes.length !== 0}>
				<div className="quadrant"><DownloadIcon /></div>
			</DroppableArea>
			<a ref={downloadLinkRef} download="download" hidden />
			<DroppableArea id="discard:droppable" className="discard-droppable" dragging={draggedInodes.length !== 0}>
				<div className="quadrant"><TrashIcon /></div>
			</DroppableArea>
		</>);
	}

	return (<>
		<MenuBar
			ref={menuBarRef}
			currentFolderId={currentFolderId}
			columnRefs={columnRefs}
			folderTabsRef={folderTabsRef}
			openUploader={() => uploaderRef.current.openUploader()}
			downloadFiles={downloadFiles}
			layout={layout}
			setLayout={setLayout}
			setSearchResult={setSearchResult}
		/>
		<DndContext
			onDragStart={handleDragStart}
			onDragEnd={handleDragEnd}
			onDragCancel={handleDragCancel}
			sensors={sensors}
			collisionDetection={pointerWithin}
			autoScroll={true}
		>
			<FolderTabs ref={folderTabsRef} isSearchResult={isSearchResult} />
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
		<Tooltip id="django-finder-tooltip" place="bottom-start" />
	</>);
}
