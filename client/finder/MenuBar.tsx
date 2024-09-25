import React, {
	useRef,
	forwardRef,
	useState,
	useImperativeHandle,
	useEffect,
	lazy,
	Suspense,
	useMemo
} from 'react';
import {useClipboard, useCookie} from './Storage';
import {SearchField} from './Search';
import {FinderSettings} from './FinderSettings';
import CopyIcon from 'icons/copy.svg';
import TilesIcon from 'icons/tiles.svg';
import MosaicIcon from 'icons/mosaic.svg';
import ListIcon from 'icons/list.svg';
import ColumnsIcon from 'icons/columns.svg';
import SortingIcon from 'icons/sorting.svg';
import SortAscIcon from 'icons/sort-asc.svg';
import SortDescIcon from 'icons/sort-desc.svg';
import CutIcon from 'icons/cut.svg';
import PasteIcon from 'icons/paste.svg';
import TrashIcon from 'icons/trash.svg';
import EraseIcon from 'icons/erase.svg';
import AddFolderIcon from 'icons/add-folder.svg';
import DownloadIcon from 'icons/download.svg';
import UndoIcon from 'icons/undo.svg';
import UploadIcon from 'icons/upload.svg';

const useSorting = () => useCookie('django-finder-sorting', '');


function SortingOptionsItem(props: any) {
	const ref = useRef(null);
	const [sorting, setSorting] = useSorting();

	useEffect(() => {
		const closeSorting = (event) => {
			if (!ref.current?.parentElement?.contains(event.target)) {
				ref.current.setAttribute('aria-expanded', 'false');
			}
		};
		window.addEventListener('click', closeSorting);
		return () => window.removeEventListener('click', closeSorting);
	}, []);

	function toggleSorting() {
		ref.current.setAttribute('aria-expanded', ref.current.ariaExpanded === 'true' ? 'false': 'true');
	}

	function isActive(value) {
		return sorting === value ? 'active' : null;
	}

	function changeSorting(value) {
		if (value !== sorting) {
			setSorting(value);
			Object.entries(props.columnRefs as React.MutableRefObject<any>).forEach(([folderId, columnRef]) => {
				columnRef.current?.fetchInodes();
			});
		}
	}

	return (
		<li className="sorting-dropdown" onClick={toggleSorting} aria-haspopup="true" data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Change sorting order")}>
			<SortingIcon/>
			<ul ref={ref} role="combobox" aria-expanded="false">
				<li onClick={() => changeSorting('')} className={isActive('')}><span>{gettext("Unsorted")}</span></li>
				<li onClick={() => changeSorting('name_asc')} className={isActive('name_asc')}>
					<SortDescIcon/><span>{gettext("Name")}</span></li>
				<li onClick={() => changeSorting('name_desc')} className={isActive('name_desc')}><SortAscIcon /><span>{gettext("Name")}</span></li>
				<li onClick={() => changeSorting('date_asc')} className={isActive('date_asc')}><SortDescIcon /><span>{gettext("Date")}</span></li>
				<li onClick={() => changeSorting('date_desc')} className={isActive('date_desc')}><SortAscIcon /><span>{gettext("Date")}</span></li>
				<li onClick={() => changeSorting('size_asc')} className={isActive('size_asc')}><SortDescIcon /><span>{gettext("Size")}</span></li>
				<li onClick={() => changeSorting('size_desc')} className={isActive('size_desc')}><SortAscIcon /><span>{gettext("Size")}</span></li>
				<li onClick={() => changeSorting('type_asc')} className={isActive('type_asc')}><SortDescIcon /><span>{gettext("Type")}</span></li>
				<li onClick={() => changeSorting('type_desc')} className={isActive('type_desc')}><SortAscIcon /><span>{gettext("Type")}</span></li>
			</ul>
		</li>
	)
}


function MenuExtension(props) {
	console.log(props)

	const MenuComponent = useMemo(() => {
		const component = `./components/menu/${props.extension.component}.js`;
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


export const MenuBar = forwardRef((props: any, forwardedRef) => {
	const {currentFolderId, columnRefs, folderTabsRef, openUploader, downloadFiles, layout, setLayout, setSearchResult, settings} = props;
	const [numSelectedInodes, setNumSelectedInodes] = useState(0);
	const [numSelectedFiles, setNumSelectedFiles] = useState(0);
	const [clipboard, setClipboard] = useClipboard();

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
			} else if (['Backspace', 'Delete'].includes(event.key) && event.shiftKey) {
				event.preventDefault();
				deleteInodes();
			}
		};
		window.addEventListener('keydown', handleKeyboardEvents);
		return () => window.removeEventListener('click', handleKeyboardEvents);
	}, []);

	function confirmEraseTrashFolder() {
		if (window.confirm("Erase all files in the trash folder?")) {
			eraseTrashFolder();
		}
	}

	function clearClipboard() {
		setClipboard([]);
	}

	function selectAllInodes() {
		const current = columnRefs[currentFolderId].current;
		current.setInodes(current.inodes.map(inode => ({...inode, selected: true, copied: false})));
		setNumSelectedInodes(current.selectedInodes.length);
		setNumSelectedFiles(current.selectedInodes.filter(inode => !inode.is_folder).length);
	}

	function copyInodes() {
		const current = columnRefs[currentFolderId].current;
		if (current.inodes.find(inode => inode.selected)) {
			setClipboard(current.inodes.filter(inode => inode.selected).map(inode => ({
				id: inode.id,
				parent: inode.parent,
				selected: false,
				copied: true
			})));
			current.setInodes(current.inodes.map(inode => ({...inode, selected: false, copied: inode.selected})));
			setNumSelectedInodes(0);
			setNumSelectedFiles(0);
		}
	}

	function cutInodes() {
		const current = columnRefs[currentFolderId].current;
		if (current.inodes.find(inode => inode.selected)) {
			setClipboard(current.inodes.filter(inode => inode.selected).map(inode => ({
				id: inode.id,
				parent: inode.parent,
				selected: false,
				cutted: true
			})));
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
			if (inodeIds.length === 0)
				return;
			moveInodes = true;
		}
		if (inodeIds.length === 0 || clipboard[0].parent === currentFolderId)
			return;

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
			columnRefs[settings.folder_id].current.setInodes(body.inodes);
			clearClipboard();
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

	async function addFolder() {
		const folderName = window.prompt("Enter folder name");
		if (!folderName)
			return;
		const addFolderUrl = `${settings.base_url}${settings.folder_id}/add_folder`;
		const response = await fetch(addFolderUrl, {
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
			current.setInodes([...current.inodes, body.new_folder]);  // adds new folder to the end of the list
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

	function isActive(value) {
		return layout === value ? 'active' : null;
	}

	return (
		<nav role="menubar">
			<ul>
				<li className="search-field">
					<SearchField columnRefs={columnRefs} setSearchResult={setSearchResult} settings={settings} />
				</li>
				<li style={{marginLeft: 'auto'}} className={isActive('tiles')} onClick={() => setLayout('tiles')} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Tiles view")}><TilesIcon /></li>
				<li className={isActive('mosaic')} onClick={() => setLayout('mosaic')} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Mosaic view")}><MosaicIcon /></li>
				<li className={isActive('list')} onClick={() => setLayout('list')} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("List view")}><ListIcon /></li>
				<li className={isActive('columns')} onClick={() => setLayout('columns')} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Columns view")}><ColumnsIcon /></li>
				<SortingOptionsItem columnRefs={columnRefs} />
				<li className={numSelectedInodes ? null : "disabled"} onClick={cutInodes} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Cut selected to clipboard")}><CutIcon /></li>
				{settings.is_trash ? (<>
					<li className={numSelectedInodes ? null : "disabled"} onClick={undoDiscardInodes} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Undo discarding files/folders")}><UndoIcon /></li>
					<li className="erase" onClick={confirmEraseTrashFolder} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Empty trash folder")}><EraseIcon /></li>
				</>) : (<>
					<li className={numSelectedInodes ? null : "disabled"} onClick={copyInodes} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Copy selected to clipboard")}><CopyIcon /></li>
					<li className={clipboard.length === 0 ? "disabled" : null} onClick={pasteInodes} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Paste from clipboard")}><PasteIcon /></li>
					<li className={numSelectedInodes ? null : "disabled"} onClick={deleteInodes} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Move selected to trash folder")}><TrashIcon /></li>
					<li onClick={addFolder} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Add new folder")}><AddFolderIcon /></li>
					<li className={numSelectedFiles ? null : "disabled"} onClick={downloadSelectedFiles} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Download selected files")}><DownloadIcon /></li>
					<li onClick={openUploader} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Upload files from local host")}><UploadIcon /></li>
					{settings.menu_extensions.map((extension, index) => (
						<MenuExtension key={index} extension={extension} columnRefs={columnRefs} numSelectedInodes={numSelectedInodes} numSelectedFiles={numSelectedFiles} />
					))}
				</>)}
			</ul>
		</nav>
	);
});
