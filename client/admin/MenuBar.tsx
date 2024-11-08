import React, {
	createRef,
	forwardRef,
	lazy,
	Suspense,
	useEffect,
	useImperativeHandle,
	useMemo,
	useState,
} from 'react';
import SearchField from './SearchField';
import DropDownMenu from '../common/DropDownMenu';
import FilterByLabel from '../common/FilterByLabel';
import SortingOptions from '../common/SortingOptions';
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
import DownloadIcon from '../icons/download.svg';
import UndoIcon from '../icons/undo.svg';
import UploadIcon from '../icons/upload.svg';



function MenuExtension(props) {
	const MenuComponent = useMemo(() => {
		const component = `./components/menuextension/${props.extension.component}.js`;
		const LazyItem = lazy(() => import(component));
		return (props) => (
			<Suspense>
				<LazyItem {...props} />
			</Suspense>
		);
	},[]);

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
		} else if (response.status === 409) {
			alert(await response.text());
		} else {
			console.error(response);
		}
	}

	function downloadSelectedFiles() {
		const current = columnRefs[currentFolderId].current;
		downloadFiles(current.inodes.filter(inode => !inode.is_folder && inode.selected));
		current.deselectinodes();
	}

	return (
		<DropDownMenu
			role="menuitem"
			className="extra-menu"
			icon={<MoreVerticalIcon/>}
			tooltip={gettext("Extra options")}
		>
			<li role="option" onClick={addFolder}>
				<AddFolderIcon/><span>{gettext("Add new folder")}</span>
			</li>
			<li role="option" aria-disabled={numSelectedFiles === 0} onClick={downloadSelectedFiles}>
				<DownloadIcon/><span>{gettext("Download selected files")}</span>
			</li>
			<li role="option" onClick={openUploader}>
				<UploadIcon/><span>{gettext("Upload local files")}</span>
			</li>
			<li role="option" aria-disabled={numSelectedInodes === 0} onClick={copyInodes}>
				<CopyIcon/><span>{gettext("Copy selected to clipboard")}</span>
			</li>
			<li role="option" aria-disabled={numClippedInodes === 0} onClick={clearClipboard}>
				<ClipboardIcon/><span>{gettext("Clear clipboard")}</span>
			</li>
			{settings.menu_extensions.length && <hr/>}
			{settings.menu_extensions.map((extension, index) => (
				<MenuExtension key={index} extension={extension} {...props} />
			))}
		</DropDownMenu>
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
		if (current.inodes.find(inode => inode.selected)) {
			const clipboard = current.inodes.filter(inode => inode.selected).map(inode => ({
				id: inode.id,
				parent: inode.parent,
				selected: false,
				cutted: true
			}));
			setClipboard(clipboard);
			current.setInodes(current.inodes.map(inode => ({...inode, selected: false, cutted: inode.selected})));
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
		} else if (response.status === 409) {
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
		const fetchUrl = `${settings.base_url}erase_trash_folder`;
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
		// <nav aria-label={gettext("Finder List View")}>
			<ul role="menubar">
				<li className="search-field" role="menuitem" style={{marginRight: 'auto'}}>
					<SearchField columnRefs={columnRefs} setSearchResult={setSearchResult} settings={settings}/>
				</li>
				<li aria-selected={layout === 'tiles'} onClick={() => setLayout('tiles')}
					role="menuitem" data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Tiles view")}>
					<TilesIcon/>
				</li>
				<li aria-selected={layout === 'mosaic'} onClick={() => setLayout('mosaic')}
					role="menuitem" data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Mosaic view")}><MosaicIcon/>
				</li>
				<li aria-selected={layout === 'list'} onClick={() => setLayout('list')}
					role="menuitem" data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("List view")}><ListIcon/>
				</li>
				<li aria-selected={layout === 'columns'} onClick={() => setLayout('columns')}
					role="menuitem" data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Columns view")}>
					<ColumnsIcon/>
				</li>
				<SortingOptions refreshFilesList={refreshColumns} />
				{settings.labels && <FilterByLabel refreshFilesList={refreshColumns} labels={settings.labels} />}
				<li aria-disabled={numSelectedInodes === 0} onClick={cutInodes}
					role="menuitem" data-tooltip-id="django-finder-tooltip"
					data-tooltip-content={gettext("Cut selected to clipboard")}>
					<CutIcon/>
				</li>
				{settings.is_trash ? (<>
				<li aria-disabled={numSelectedInodes === 0} onClick={undoDiscardInodes}
					role="menuitem" data-tooltip-id="django-finder-tooltip"
					data-tooltip-content={gettext("Undo discarding files/folders")}>
					<UndoIcon/>
				</li>
				<li className="erase" onClick={confirmEraseTrashFolder} data-tooltip-id="django-finder-tooltip"
					role="menuitem" data-tooltip-content={gettext("Empty trash folder")}>
					<EraseIcon/>
				</li>
				</>) : (<>
					<li aria-disabled={clipboard.length === 0} onClick={pasteInodes}
						role="menuitem" data-tooltip-id="django-finder-tooltip"
						data-tooltip-content={gettext("Paste from clipboard")}>
						<PasteIcon/>
					</li>
					<li aria-disabled={numSelectedInodes === 0} onClick={deleteInodes}
						role="menuitem" data-tooltip-id="django-finder-tooltip"
						data-tooltip-content={gettext("Move selected to trash folder")}>
						<TrashIcon/>
					</li>
					<ExtraMenu
						numSelectedFiles={numSelectedFiles}
						numSelectedInodes={numSelectedInodes}
						numClippedInodes={clipboard.length}
						copyInodes={copyInodes}
						clearClipboard={clearClipboard}
						{...props}
					/>
				</>)}
			</ul>
		//</nav>
	);
});


export default MenuBar;
