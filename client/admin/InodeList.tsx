import React, {
	createRef,
	forwardRef,
	useCallback,
	useEffect,
	useImperativeHandle,
	useRef,
	useState,
} from 'react';
import {Folder, File} from './Item';
import GalleryPreview from './GalleryPreview';


function InodeListHeader() {
	return (
		<li className="header">
			<div className="inode">
				<div></div>
				<div>{gettext("Name")}</div>
				<div>{gettext("Owner")}</div>
				<div>{gettext("Details")}</div>
				<div>{gettext("Created at")}</div>
				<div>{gettext("Modified at")}</div>
				<div>{gettext("Mime type")}</div>
			</div>
		</li>
	);
}


const InodeList = forwardRef(function InodeList(props: any, forwardedRef) {
	const {
		folderId,
		ancestorFolderId,
		setCurrentFolder,
		menuBarRef,
		layout,
		clipboard,
		clearClipboard,
		preselectedInode,
		setPreselectedInode,
		settings
	} = props;
	const inodesPerRow = useRef(0);
	const lastSelectedIndex = useRef(-1);
	const [inodes, setInodes] = useState(null);
	const [searchQuery, setSearchQuery] = useState(() => {
		const params = new URLSearchParams(window.location.search);
		return params.get('q');
	});

	useEffect(() => {
		fetchInodes();
	}, [searchQuery]);

	const setListRef = useCallback((listElement: HTMLUListElement) => {
		const inodeElement = listElement?.querySelector(':scope > li');
		if (!inodeElement)
			return;
		switch (layout) {
			case 'tiles':
				// (width - padding-left - padding-right + gap) / (width + gap)
				inodesPerRow.current = Math.floor((listElement.getBoundingClientRect().width - 24) / (inodeElement.getBoundingClientRect().width + 6));
				break;
			case 'mosaic':
				// (width - padding-left - padding-right + gap) / (width + gap)
				inodesPerRow.current = Math.floor((listElement.getBoundingClientRect().width - 28) / (inodeElement.getBoundingClientRect().width + 2));
				break;
			default:
				inodesPerRow.current = 1;
				break;
		}
	}, [layout]);

	useImperativeHandle(forwardedRef, () => ({
		inodes,
		setInodes,
		deselectInodes,
		setSearchQuery,
		selectInode,
		selectMultipleInodes,
		async fetchInodes() {
			await fetchInodes();
		},
		navigatePreselection,
	}));

	async function fetchInodes() {
		const params = new URLSearchParams({q: searchQuery});
		const fetchInodesUrl = `${settings.base_url}${folderId}/fetch${searchQuery ? `?${params.toString()}` : ''}`;
		setInodes(null);
		const response = await fetch(fetchInodesUrl);
		if (response.ok) {
			const body = await response.json();
			setInodes(body.inodes.map(inode => {
				const elementRef = createRef();
				const item = clipboard.find(item => item.id === inode.id);
				if (item) {
					return {...inode, elementRef, copied: item.copied, cutted: item.cutted};
				}
				return {...inode, elementRef};
			}));
			if (preselectedInode === null && ancestorFolderId === null && body.inodes.length > 0) {
				setPreselectedInode(body.inodes.at(0));
			}
		} else {
			console.error(response);
		}
	}

	function openDetailView(inode) {
		if (!settings.is_trash) {
			// prevent editing files in trash folder
			window.location.assign(inode.change_url);
		}
	}

	function modifySelectedInodes(inode, modifier: Function) {
		const modifiedInodes = inodes.map((f, k) => ({...modifier(f, k), cutted: false, copied: false}));
		setInodes(modifiedInodes);
		menuBarRef.current.setSelected(modifiedInodes.filter(inode => inode.selected));
	}

	function extendSelection(inode) {
		const selectedInodeIndex = inodes.findIndex(f => f.id === inode.id);
		let modifier: Function;
		if (selectedInodeIndex < lastSelectedIndex.current) {
			modifier = (f, k) => ({...f, selected: k >= selectedInodeIndex && k <= lastSelectedIndex.current || f.selected});
		} else if (lastSelectedIndex.current !== -1 && selectedInodeIndex > lastSelectedIndex.current) {
			modifier = (f, k) => ({...f, selected: k >= lastSelectedIndex.current && k <= selectedInodeIndex || f.selected});
		} else {
			modifier = f => ({...f, selected: f.selected || f.id === inode.id});
		}
		modifySelectedInodes(inode, modifier);
	}

	function addToSelection(inode) {
		let modifier: Function;
		if (inode.selected) {
			modifier = f => ({...f, selected: f.selected && f.id !== inode.id});
		} else {
			modifier = f => ({...f, selected: f.selected || f.id === inode.id});
			lastSelectedIndex.current = inodes.findIndex(f => f.id === inode.id);  // remember for an upcoming shift-click
			clearClipboard();
		}
		modifySelectedInodes(inode, modifier);
	}

	function toggleSelection(inode) {
		let modifier: Function;
		if (inode.selected) {
			modifier = f => ({...f, selected: false});
		} else {
			modifier = f => ({...f, selected: f.id === inode.id});
			lastSelectedIndex.current = inodes.findIndex(f => f.id === inode.id);
		}
		modifySelectedInodes(inode, modifier);
	}

	const selectInode = useCallback(function selectInode(event: PointerEvent, inode) {
		if (inode.disabled)
			return;
		if (event.detail === 2) {
			// double click
			openDetailView(inode);
		} else if (event.shiftKey) {
			// shift click
			extendSelection(inode);
			setCurrentFolder(folderId);
		} else if (event.altKey || event.ctrlKey || event.metaKey) {
			// alt/ctrl/meta click
			addToSelection(inode);
			setCurrentFolder(folderId);
		} else if (!(event.target as HTMLElement)?.classList.contains('inode-name')) {
			// simple click
			// prevent selecting the inode when clicking on the name field to edit it
			toggleSelection(inode);
			setPreselectedInode(inode);
			setCurrentFolder(folderId);
		}
	}, [inodes]);

	function navigatePreselection(event: KeyboardEvent) {
		const index = inodes.findIndex((inode) => inode.id === preselectedInode.id);
		let nextPreselectedInode;
		if (event.key === 'ArrowLeft') {
			nextPreselectedInode = layout === 'columns' ? inodes.at(0) : inodes.at(index - 1);
		} else if (event.key === 'ArrowRight') {
			nextPreselectedInode = layout === 'columns' ? inodes.at(0) : inodes.at(index + 1);
		} else if (event.key === 'ArrowUp') {
			nextPreselectedInode = inodes.at(index - inodesPerRow.current);
		} else if (event.key === 'ArrowDown') {
			nextPreselectedInode = inodes.at(index + inodesPerRow.current);
		} else if (event.key === ' ') {
			if (event.shiftKey) {
				// shift click
				extendSelection(preselectedInode);
			} else if (event.altKey || event.ctrlKey || event.metaKey) {
				// alt/ctrl/meta click
				addToSelection(preselectedInode);
			} else {
				toggleSelection(preselectedInode);
			}
		}
		if (nextPreselectedInode) {
			nextPreselectedInode.elementRef.current.scrollIntoView({behaviour: 'smooth', block: 'center', container: 'nearest', inline: 'center'});
			setPreselectedInode(nextPreselectedInode);
		}
	}

	// const selectInode = useCallback(function selectInode(event: PointerEvent|KeyboardEvent, inode) {
	// 	if (inode.disabled)
	// 		return;
	// 	let modifier, selectedIndex = -1;
	// 	if (event.detail === 2) {
	// 		// double click
	// 		if (!settings.is_trash) {
	// 			// prevent editing files in trash folder
	// 			window.location.assign(inode.change_url);
	// 		}
	// 		return;
	// 	}
	// 	if (event.shiftKey) {
	// 		// shift click
	// 		const selectedInodeIndex = inodes.findIndex(f => f.id === inode.id);
	// 		if (selectedInodeIndex < lastSelectedIndex) {
	// 			modifier = (f, k) => ({...f, selected: k >= selectedInodeIndex && k <= lastSelectedIndex || f.selected});
	// 		} else if (lastSelectedIndex !== -1 && selectedInodeIndex > lastSelectedIndex) {
	// 			modifier = (f, k) => ({...f, selected: k >= lastSelectedIndex && k <= selectedInodeIndex || f.selected});
	// 		} else {
	// 			modifier = f => ({...f, selected: f.selected || f.id === inode.id});
	// 		}
	// 	} else if (event.altKey || event.ctrlKey || event.metaKey) {
	// 		// alt/ctrl/meta click
	// 		if (inode.selected) {
	// 			modifier = f => ({...f, selected: f.selected && f.id !== inode.id});
	// 		} else {
	// 			modifier = f => ({...f, selected: f.selected || f.id === inode.id});
	// 			selectedIndex = inodes.findIndex(f => f.id === inode.id);  // remember for an upcoming shift-click
	// 		}
	// 	} else {
	// 		// simple click
	// 		if (inode.selected) {
	// 			modifier = f => ({...f, selected: false});
	// 		} else {
	// 			if (!(event.target as HTMLElement)?.classList.contains('inode-name')) {
	// 				// prevent selecting the inode when clicking on the name field to edit it
	// 				modifier = f => ({...f, selected: f.id === inode.id});
	// 				selectedIndex = inodes.findIndex(f => f.id === inode.id);  // remember for an upcoming shift-click
	// 			} else {
	// 				modifier = f => f;
	// 			}
	// 		}
	// 	}
	// 	if (selectedIndex !== -1) {
	// 		clearClipboard();
	// 	}
	// 	const modifiedInodes = inodes.map((f, k) => ({...modifier(f, k), cutted: false, copied: false}));
	// 	setInodes(modifiedInodes);
	// 	setCurrentFolder(folderId);
	// 	menuBarRef.current.setSelected(modifiedInodes.filter(inode => inode.selected));
	// 	setSelectedIndex(selectedIndex);
	// }, [inodes]);

	const selectMultipleInodes = useCallback(function selectMultipleInodes(selectedInodeIds: Array<string>, extend: boolean = false) {
		if (selectedInodeIds.length) {
			clearClipboard();
			const modifiedInodes = inodes.map(inode => ({
				...inode,
				selected: extend && inode.selected || selectedInodeIds.includes(inode.id),
			}));
			setCurrentFolder(folderId);
			setInodes(modifiedInodes);
			menuBarRef.current.setSelected(modifiedInodes.filter(inode => inode.selected));
		}
	}, [inodes]);

	const deselectInodes = useCallback(function deselectInodes() {
		setInodes(prevInodes => {
			if (prevInodes.find(inode => inode.selected || inode.dragged)) {
				return prevInodes.map(inode => ({...inode, selected: false, dragged: false}));
			}
			return prevInodes;
		});
	}, []);

	function cssClasses() {
		const classes = ['inode-list'];
		if (settings.is_trash && !searchQuery) {
			classes.push('trash');
		}
		return classes.join(' ');
	}

	function renderInodes() {
		if (inodes.length === 0) {
			if (searchQuery)
				return (<li className="status">{`No match while searching for “${searchQuery}”`}</li>);
			return (<li className="status">{gettext("This folder is empty")}</li>);
		}
		const isPreselected = inode => preselectedInode?.id === inode.id;

		return inodes.map(inode => inode.is_folder
			? <Folder key={inode.id} {...inode} {...props} isParent={ancestorFolderId === inode.id} preselected={isPreselected(inode)} />
			: <File key={inode.id} {...inode} {...props} preselected={isPreselected(inode)} />
		);
	}

	if (inodes === null) {
		return <div className="status">{gettext("Loading...")}</div>;
	}

	if (layout === 'gallery') {
		return (<>
			<GalleryPreview inodes={inodes} setInodes={setInodes} preselectedInode={preselectedInode} {...props} />
			<div className="thumbnails">
				<ul ref={setListRef} className={cssClasses()}>{renderInodes()}</ul>
			</div>
		</>);
	}

	return (
		<ul ref={setListRef} className={cssClasses()}>
			{layout === 'list' && <InodeListHeader/>}
			{renderInodes()}
		</ul>
	);
});

export default InodeList;
