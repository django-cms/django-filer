import React, {
	createRef,
	forwardRef,
	useEffect,
	useImperativeHandle,
	useState,
} from 'react';
import {Folder, File} from './Item';


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


const InodeList = forwardRef((props: any, forwardedRef) => {
	const {
		folderId,
		previousFolderId,
		setCurrentFolder,
		menuBarRef,
		layout,
		clipboard,
		clearClipboard,
		settings
	} = props;
	const [inodes, setInodes] = useState(null);
	const [lastSelectedIndex, setSelectedIndex] = useState(-1);
	const [searchQuery, setSearchQuery] = useState(() => {
		const params = new URLSearchParams(window.location.search);
		return params.get('q');
	});

	useEffect(() => {
		fetchInodes();
	}, [searchQuery]);

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
		} else {
			console.error(response);
		}
	}

	function selectInode(event: PointerEvent, inode) {
		if (inode.disabled)
			return;
		let modifier, selectedIndex = -1;
		if (event.detail === 2) {
			// double click
			if (!settings.is_trash) {
				// prevent editing files in trash folder
				window.location.assign(inode.change_url);
			}
			return;
		}
		if (event.shiftKey) {
			// shift click
			const selectedInodeIndex = inodes.findIndex(f => f.id === inode.id);
			if (selectedInodeIndex < lastSelectedIndex) {
				modifier = (f, k) => ({...f, selected: k >= selectedInodeIndex && k <= lastSelectedIndex || f.selected});
			} else if (lastSelectedIndex !== -1 && selectedInodeIndex > lastSelectedIndex) {
				modifier = (f, k) => ({...f, selected: k >= lastSelectedIndex && k <= selectedInodeIndex || f.selected});
			} else {
				modifier = f => ({...f, selected: f.selected || f.id === inode.id});
			}
		} else if (event.altKey || event.ctrlKey || event.metaKey) {
			// alt/ctrl/meta click
			if (inode.selected) {
				modifier = f => ({...f, selected: f.selected && f.id !== inode.id});
			} else {
				modifier = f => ({...f, selected: f.selected || f.id === inode.id});
				selectedIndex = inodes.findIndex(f => f.id === inode.id);  // remember for an upcoming shift-click
			}
		} else {
			// simple click
			if (inode.selected) {
				modifier = f => ({...f, selected: false});
			} else {
				if (!(event.target as HTMLElement)?.classList.contains('inode-name')) {
					// prevent selecting the inode when clicking on the name field to edit it
					modifier = f => ({...f, selected: f.id === inode.id});
					selectedIndex = inodes.findIndex(f => f.id === inode.id);  // remember for an upcoming shift-click
				} else {
					modifier = f => f;
				}
			}
		}
		if (selectedIndex !== -1) {
			clearClipboard();
		}
		const modifiedInodes = inodes.map((f, k) => ({...modifier(f, k), cutted: false, copied: false}));
		setInodes(modifiedInodes);
		setCurrentFolder(folderId);
		menuBarRef.current.setSelected(modifiedInodes.filter(inode => inode.selected));
		setSelectedIndex(selectedIndex);
	}

	function selectMultipleInodes(selectedInodeIds: Array<string>, extend: boolean = false) {
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
	}

	function deselectInodes() {
		if (inodes.find(inode => inode.selected || inode.dragged)) {
			setInodes(inodes.map(inode => ({...inode, selected: false, dragged: false})));
		}
	}

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

		return inodes.map(inode => inode.is_folder
			? <Folder key={inode.id} {...inode} {...props} isParent={previousFolderId === inode.id} />
			: <File key={inode.id} {...inode} {...props} />
		);
	}

	return inodes === null ? (
		<div className="status">
			{gettext("Loading...")}
		</div>
	) : (
		<ul className={cssClasses()}>
			{layout === 'list' && <InodeListHeader/>}
			{renderInodes()}
		</ul>
	);
});

export default InodeList;
