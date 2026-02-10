import React, {
	createRef,
	forwardRef,
	lazy,
	Suspense,
	useEffect,
	useImperativeHandle,
	useMemo,
	useRef,
	useState,
} from 'react';
import {DndContext} from '@dnd-kit/core';
import SearchField from './SearchField';
import PermissionEditor from './PermissionEditor';
import LabelEditor from './LabelEditor';
import DropDownMenu from '../common/DropDownMenu';
import VolumeControl from '../common/VolumeControl';
import FilterByLabel from '../common/FilterByLabel';
import SortingOptions from '../common/SortingOptions';
import {Tooltip, TooltipContent, TooltipTrigger} from '../common/Tooltip';
import MoreVerticalIcon from '../icons/more-vertical.svg';
import CopyIcon from '../icons/copy.svg';
import TilesIcon from '../icons/tiles.svg';
import MosaicIcon from '../icons/mosaic.svg';
import ListIcon from '../icons/list.svg';
import ColumnsIcon from '../icons/columns.svg';
import CutIcon from '../icons/cut.svg';
import PasteIcon from '../icons/paste.svg';
import ClipboardIcon from '../icons/clipboard.svg';
import TrashIcon from '../icons/trash.svg';
import EraseIcon from '../icons/erase.svg';
import AddFolderIcon from '../icons/add-folder.svg';
import ShieldFolderIcon from '../icons/shield-folder.svg';
import FolderShieldIcon from '../icons/folder-shield.svg';
import LabelIcon from '../icons/label.svg';
import DownloadIcon from '../icons/download.svg';
import UndoIcon from '../icons/undo.svg';
import UploadIcon from '../icons/upload.svg';
import FolderUploadIcon from '../icons/folder-upload.svg';


export const VERBOSE_HTTP_ERROR_CODES = new Set([403, 409]);


function MenuExtension(props) {
	const MenuComponent = useMemo(() => {
		const component = `./components/menuextension/${props.extension.component}.js`;
		const LazyItem = lazy(() => import(component));
		return (props) => (
			<Suspense>
				<LazyItem {...props} />
			</Suspense>
		);
	}, []);

	return (
		<MenuComponent {...props} />
	)
}


function ExtraMenu(props) {
	const {
		settings,
		columnRefs,
		openUploader,
		downloadFiles,
		numSelectedFiles,
		numSelectedInodes,
		numClippedInodes,
		currentFolderId,
		copyInodes,
		clearClipboard,
		deselectAll,
		permissionDialogRef,
		labelDialogRef,
	} = props;

	async function addFolder() {
		const folderName = window.prompt(gettext("Enter folder name"));
		if (!folderName)
			return;
		const fetchUrl = `${settings.base_url}${settings.folder_id}/add_folder`;
		const response = await fetch(fetchUrl, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': settings.csrf_token,
			},
			body: JSON.stringify({
				name: folderName,
			}),
		});
		if (response.ok) {
			const current = columnRefs[settings.folder_id].current;
			const body = await response.json();
			current.setInodes([...current.inodes, {...body.new_folder, elementRef: createRef()}]);  // adds new folder to the end of the list
		} else if (VERBOSE_HTTP_ERROR_CODES.has(response.status)) {
			alert(await response.text());
		} else {
			console.error(response);
		}
	}

	function downloadSelectedFiles() {
		const current = columnRefs[currentFolderId].current;
		downloadFiles(current.inodes.filter(inode => !inode.is_folder && inode.selected));
		deselectAll();
	}

	function openPermissionEditorDialog(asDefault: boolean) {
		labelDialogRef.current?.close();
		permissionDialogRef.current.show(asDefault);
	}

	function openLabelEditorDialog() {
		permissionDialogRef.current?.close();
		labelDialogRef.current.show();
	}

	return (
		<DropDownMenu
			role="menuitem"
			className="extra-menu"
			icon={<MoreVerticalIcon/>}
			tooltip={gettext("Extra options")}
		>
			<li role="option" aria-disabled={!settings.can_change} onClick={addFolder}>
				<AddFolderIcon/><span>{gettext("Add new folder")}</span>
			</li>
			<li role="option" aria-disabled={!settings.can_change} onClick={() => openUploader(false)}>
				<UploadIcon/><span>{gettext("Upload local files")}</span>
			</li>
			<li role="option" aria-disabled={!settings.can_change} onClick={() => openUploader(true)}>
				<FolderUploadIcon/><span>{gettext("Upload local folder")}</span>
			</li>
			<li role="option" aria-disabled={numSelectedFiles === 0} onClick={downloadSelectedFiles}>
				<DownloadIcon/><span>{gettext("Download selected files")}</span>
			</li>
			<li role="option" aria-disabled={numSelectedInodes === 0} onClick={copyInodes}>
				<CopyIcon/><span>{gettext("Copy selected to clipboard")}</span>
			</li>
			<li role="option" aria-disabled={numClippedInodes === 0} onClick={clearClipboard}>
				<ClipboardIcon/><span>{gettext("Clear clipboard")}</span>
			</li>
			{settings.is_admin && <>
			<hr/>
			<li role="option" onClick={() => openPermissionEditorDialog(false)}>
				<ShieldFolderIcon/><span>{gettext("Edit folder permissions")}</span>
			</li>
			<li role="option" onClick={() => openPermissionEditorDialog(true)}>
				<FolderShieldIcon/><span>{gettext("Edit default permissions")}</span>
			</li>
				{settings.is_root &&
			<li role="option" onClick={() => openLabelEditorDialog()}>
				<LabelIcon/><span>{gettext("Edit labels")}</span>
			</li>
				}
			</>}
			{settings.menu_extensions.length && <hr/>}
			{settings.menu_extensions.map((extension, index) => (
				<MenuExtension key={index} extension={extension} {...props} />
			))}
		</DropDownMenu>
	);
}


function MenuItem(props) {
	const {children, tooltip} = props;
	const itemProps = Object.fromEntries(Object.entries(props).filter(([key]) => !['children', 'tooltip'].includes(key)));

	return (
		<Tooltip>
			<TooltipTrigger>
				<li {...itemProps} role="menuitem">
					{children}
				</li>
			</TooltipTrigger>
			<TooltipContent>{tooltip}</TooltipContent>
		</Tooltip>
	);
}


const MenuBar = forwardRef((props: any, forwardedRef) => {
	const {
		currentFolderId,
		columnRefs,
		folderTabsRef,
		layout,
		setLayout,
		deselectAll,
		refreshColumns,
		clipboard,
		setClipboard,
		clearClipboard,
		setSearchResult,
		settings
	} = props;
	const [numSelectedInodes, setNumSelectedInodes] = useState(0);
	const [numSelectedFiles, setNumSelectedFiles] = useState(0);
	const permissionDialogRef = useRef(null);
	const labelDialogRef = useRef(null);

	useImperativeHandle(forwardedRef, () => ({
		setSelected: (selectedInodes) => {
			setNumSelectedInodes(selectedInodes.length);
			setNumSelectedFiles(selectedInodes.filter(inode => !inode.is_folder).length);
		},
	}));

	useEffect(() => {
		const handleKeyboardEvents = (event) => {
			if (event.key === 'a' && (event.ctrlKey || event.metaKey || event.altKey)) {
				event.preventDefault();
				selectAllInodes();
			} else if (event.key === 'c' && (event.ctrlKey || event.metaKey || event.altKey)) {
				event.preventDefault();
				copyInodes();
			} else if (event.key === 'x' && (event.ctrlKey || event.metaKey || event.altKey)) {
				event.preventDefault();
				cutInodes();
			} else if (event.key === 'v' && (event.ctrlKey || event.metaKey || event.altKey)) {
				event.preventDefault();
				pasteInodes();
			} else if (['Backspace', 'Delete'].includes(event.key)) {
				deleteInodes();
			}
		};
		window.addEventListener('keydown', handleKeyboardEvents);
		return () => window.removeEventListener('keydown', handleKeyboardEvents);
	}, [currentFolderId]);

	function confirmEraseTrashFolder() {
		if (window.confirm("Erase all files in the trash folder?")) {
			eraseTrashFolder();
		}
	}

	function selectAllInodes() {
		clearClipboard();
		deselectAll();
		const current = columnRefs[currentFolderId].current;
		current.setInodes(current.inodes.map(inode => ({...inode, selected: true, copied: false})));
		setNumSelectedInodes(current.inodes.length);
		setNumSelectedFiles(current.inodes.filter(inode => !inode.is_folder).length);
	}

	function copyInodes() {
		const current = columnRefs[currentFolderId].current;
		if (current.inodes.find(inode => inode.selected)) {
			const clipboard = current.inodes.filter(inode => inode.selected).map(inode => ({
				id: inode.id,
				parent: inode.parent,
				selected: false,
				copied: true
			}));
			setClipboard(clipboard);
			current.setInodes(current.inodes.map(inode => ({...inode, selected: false, copied: inode.selected})));
			setNumSelectedInodes(0);
			setNumSelectedFiles(0);
		}
	}

	function cutInodes() {
		const current = columnRefs[currentFolderId].current;
		if (current.inodes.find(inode => inode.selected && inode.can_change)) {
			const clipboard = current.inodes.filter(inode => inode.selected && inode.can_change).map(inode => ({
				id: inode.id,
				parent: inode.parent,
				selected: false,
				cutted: true,
			}));
			setClipboard(clipboard);
			current.setInodes(current.inodes.map(inode => ({...inode, selected: false, cutted: inode.selected && inode.can_change})));
			setNumSelectedInodes(0);
			setNumSelectedFiles(0);
		}
	}

	async function pasteInodes() {
		let moveInodes = false;
		let inodeIds = clipboard.filter(inode => inode.copied).map(inode => inode.id);
		if (inodeIds.length === 0) {
			inodeIds = clipboard.filter(inode => inode.cutted).map(inode => inode.id);
			if (inodeIds.length === 0) {
				// nothing to paste from clipboard
				return;
			}
			moveInodes = true;
		}
		if (clipboard[0].parent === settings.folder_id) {
			// pasting into itself doesn't perform anything
			return;
		}
		clearClipboard();

		const fetchUrl = `${settings.base_url}${settings.folder_id}/${moveInodes ? 'move' : 'copy'}`;
		const response = await fetch(fetchUrl, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': settings.csrf_token,
			},
			body: JSON.stringify({inode_ids: inodeIds}),
		});
		if (response.ok) {
			const body = await response.json();
			if (moveInodes) {
				const current = columnRefs[clipboard[0].parent]?.current;
				if (current) {
					current.setInodes(current.inodes.filter(inode => inodeIds.find(id => id !== inode.id)));
				}
			}
			columnRefs[settings.folder_id].current.setInodes(
				body.inodes.map(inode => ({...inode, elementRef: createRef()}))
			);
		} else if (VERBOSE_HTTP_ERROR_CODES.has(response.status)) {
			alert(await response.text());
		} else {
			console.error(response);
		}
	}

	async function deleteInodes() {
		const current = columnRefs[currentFolderId].current;
		const inodeIds = current.inodes.filter(inode => inode.selected).map(inode => inode.id);
		if (inodeIds.length === 0)
			return;

		let fetchUrl = `${settings.base_url}${settings.folder_id}/delete`;
		const response = await fetch(fetchUrl, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': settings.csrf_token,
			},
			body: JSON.stringify({inode_ids: inodeIds}),
		});
		if (response.ok) {
			const body = await response.json();
			folderTabsRef.current.setFavoriteFolders(body.favorite_folders);
			current.setInodes(current.inodes.filter(inode => !inodeIds.includes(inode.id)));
		} else if (VERBOSE_HTTP_ERROR_CODES.has(response.status)) {
			alert(await response.text());
		} else {
			console.error(response);
		}
	}

	async function undoDiscardInodes() {
		const current = columnRefs[currentFolderId].current;
		const inodeIds = current.inodes.filter(inode => inode.selected).map(inode => inode.id);
		if (inodeIds.length === 0)
			return;

		const fetchUrl = `${settings.base_url}undo_discard`;
		const response = await fetch(fetchUrl, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': settings.csrf_token,
			},
			body: JSON.stringify({inode_ids: inodeIds}),
		});
		if (response.ok) {
			current.setInodes(current.inodes.filter(inode => !inodeIds.includes(inode.id)));
		} else {
			console.error(response);
		}
	}

	async function eraseTrashFolder() {
		const fetchUrl = `${settings.base_url}${settings.folder_id}/erase_trash_folder`;
		const response = await fetch(fetchUrl, {
			method: 'DELETE',
			headers: {
				'X-CSRFToken': settings.csrf_token,
			},
		});
		if (response.ok) {
			clearClipboard();
			const data = await response.json();
			window.location.assign(data.success_url);
		}
	}

	return (
		<DndContext
			onDragStart={
				event => {
					permissionDialogRef.current?.handleDragStart(event);
					labelDialogRef.current?.handleDragStart(event);
				}
			}
			onDragEnd={
				event => {
					permissionDialogRef.current?.handleDragEnd(event);
					labelDialogRef.current?.handleDragEnd(event);
				}
			}
			autoScroll={false}
		>
			<nav aria-label={gettext("Finder List View")}>
				<ul role="menubar">
					<li className="search-field" role="menuitem">
						<SearchField columnRefs={columnRefs} setSearchResult={setSearchResult} settings={settings}/>
					</li>
					<VolumeControl {...props} />
					<MenuItem aria-selected={layout === 'tiles'} onClick={() => setLayout('tiles')} tooltip={gettext("Tiles view")}>
						<TilesIcon/>
					</MenuItem>
					<MenuItem aria-selected={layout === 'mosaic'} onClick={() => setLayout('mosaic')} tooltip={gettext("Mosaic view")}>
						<MosaicIcon/>
					</MenuItem>
					<MenuItem aria-selected={layout === 'list'} onClick={() => setLayout('list')} tooltip={gettext("List view")}>
						<ListIcon/>
					</MenuItem>
					<MenuItem aria-selected={layout === 'columns'} onClick={() => setLayout('columns')} tooltip={gettext("Columns view")}>
						<ColumnsIcon/>
					</MenuItem>
					<SortingOptions refreshFilesList={refreshColumns} />
					{settings.labels && <FilterByLabel refreshFilesList={refreshColumns} labels={settings.labels} />}
					<MenuItem aria-disabled={numSelectedInodes === 0 || !settings.can_change} onClick={cutInodes} tooltip={gettext("Cut selected to clipboard")}>
						<CutIcon/>
					</MenuItem>
					{settings.is_trash ? (<>
						<MenuItem aria-disabled={numSelectedInodes === 0} onClick={undoDiscardInodes} tooltip={gettext("Undo discarding files/folders")}>
							<UndoIcon/>
						</MenuItem>
						<MenuItem className="erase" onClick={confirmEraseTrashFolder} tooltip={gettext("Empty trash folder")}>
							<EraseIcon/>
						</MenuItem>
					</>) : (<>
						<MenuItem aria-disabled={clipboard.length === 0 || !settings.can_change} onClick={pasteInodes} tooltip={gettext("Paste from clipboard")}>
							<PasteIcon/>
						</MenuItem>
						<MenuItem aria-disabled={numSelectedInodes === 0 || !settings.can_change} onClick={deleteInodes} tooltip={gettext("Move selected to trash folder")}>
							<TrashIcon/>
						</MenuItem>
						<ExtraMenu
							numSelectedFiles={numSelectedFiles}
							numSelectedInodes={numSelectedInodes}
							numClippedInodes={clipboard.length}
							copyInodes={copyInodes}
							clearClipboard={clearClipboard}
							deselectAll={deselectAll}
							permissionDialogRef={permissionDialogRef}
							labelDialogRef={labelDialogRef}
							{...props}
						/>
					</>)}
				</ul>
			</nav>
			{settings.is_admin && <>
			<PermissionEditor ref={permissionDialogRef} settings={settings} />
				{settings.is_root && <LabelEditor ref={labelDialogRef} settings={settings} />}
			</>}
		</DndContext>
	);
});

export default MenuBar;
