import React, {
	createRef,
	forwardRef,
	SyntheticEvent,
	useContext,
	useEffect,
	useImperativeHandle,
	useState,
} from 'react';
import {Folder, File, Inode, ListItem} from './Inode';
import {FinderSettings} from './FinderSettings';


export const InodeList = forwardRef((props: any, forwardedRef) => {
	const settings = useContext(FinderSettings);
	const {folderId, previousFolderId, setCurrentFolder, menuBarRef, folderTabsRef, layout} = props;
	const [isLoading, setLoading] = useState(false);
	const [inodes, setInodesWithRef] = useState([]);
	const [lastSelectedInode, setSelectedInode] = useState(-1);
	const [searchQuery, setSearchQuery] = useState(() => {
		const params = new URLSearchParams(window.location.search);
		return params.get('q');
	});

	useEffect(() => {
		fetchInodes();
	}, [searchQuery]);

	useImperativeHandle(forwardedRef, () => ({
		inodes: inodes,
		setInodes: setInodes,
		deselectInodes: deselectInodes,
		setSearchQuery: setSearchQuery,
		selectMultipleInodes: selectMultipleInodes,
		async fetchInodes() {
			await fetchInodes();
		},
		async addFolder() {
			await addFolder();
		},
	}));

	function setInodes(inodes) {
		setInodesWithRef(inodes.map(inode => ({...inode, elementRef: createRef()})));
	}

	async function fetchInodes() {
		const params = new URLSearchParams({q: searchQuery});
		const fetchInodesUrl = `${settings.base_url}${folderId}/fetch${searchQuery ? `?${params.toString()}` : ''}`;
		setLoading(true);
		const response = await fetch(fetchInodesUrl);
		if (response.ok) {
			const body = await response.json();
			setInodes(body.inodes);
		} else {
			console.error(response);
		}
		setLoading(false);
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
			const body = await response.json();
			setInodes([...inodes, body.new_folder]);
		} else {
			console.error(response);
			return;
		}
	}

	function selectInode(event: PointerEvent) {
		if (this.disabled)
			return;
		let modifier;
		if (event.detail === 2) {
			// double click
			if (!settings.is_trash) {
				// prevent editing files in trash folder
				window.location.assign(this.change_url);
			}
			return;
		} else if ((event.detail as any)?.selected) {
			// this is a SelectableArea event
			modifier = f => ({...f, selected: f.selected || f.id === this.id});
		} else if (event.shiftKey) {
			// shift click
			const selectedInodeIndex = inodes.findIndex(f => f.id === this.id);
			if (selectedInodeIndex < lastSelectedInode) {
				modifier = (f, k) => ({...f, selected: k >= selectedInodeIndex && k <= lastSelectedInode});
			} else if (lastSelectedInode !== -1 && selectedInodeIndex > lastSelectedInode) {
				modifier = (f, k) => ({...f, selected: k >= lastSelectedInode && k <= selectedInodeIndex});
			} else {
				modifier = f => ({...f, selected: f.selected || f.id === this.id});
			}
		} else if (event.altKey || event.ctrlKey || event.metaKey) {
			// alt/ctrl/meta click
			if (this.selected) {
				modifier = f => ({...f, selected: f.selected && f.id !== this.id});
			} else {
				modifier = f => ({...f, selected: f.selected || f.id === this.id});
			}
		} else {
			// simple click
			if (this.selected) {
				modifier = f => ({...f, selected: false});
			} else {
				modifier = f => ({...f, selected: f.id === this.id});
			}
			if (!this.selected) {
				// remember the last selected inode for upcoming shift-click
				setSelectedInode(inodes.findIndex(inode => inode.id === this.id));
			}
		}
		const modifiedInodes = inodes.map((f, k) => ({...modifier(f, k), cutted: false, copied: false}));
		setCurrentFolder(folderId);
		setInodes(modifiedInodes);
		menuBarRef.current.setSelected(modifiedInodes.filter(inode => inode.selected));
	}

	function selectMultipleInodes(selectedInodeIds: Array<string>) {
		const modifiedInodes = inodes.map(inode => ({...inode, selected: selectedInodeIds.includes(inode.id), cutted: false, copied: false}));
		setCurrentFolder(folderId);
		setInodes(modifiedInodes);
		menuBarRef.current.setSelected(modifiedInodes.filter(inode => inode.selected));
	}

	function deselectInodes() {
		if (inodes.find(inode => inode.selected || inode.dragged)) {
			setInodes(inodes.map(inode => ({...inode, selected: false, dragged: false})));
		}
	}

	async function updateInode(newInode) {
		const fetchUrl = `${settings.base_url}${settings.folder_id}/update`;
		const response = await fetch(fetchUrl, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': settings.csrf_token,
			},
			body: JSON.stringify({id: newInode.id, name: newInode.name}),
		});
		if (response.ok) {
			const body = await response.json();
			setInodes(inodes.map(inode => inode.id === body.new_inode.id ? body.new_inode : inode));
			folderTabsRef.current.setFavoriteFolders(body.favorite_folders);
		} else if (response.status === 409) {
			alert(await response.text());
		} else {
			console.error(response);
		}
		return response.ok;
	}

	const deactivateInodes = (event: SyntheticEvent) => {
		if (event.target instanceof Element && event.target.classList.contains('inode-list')) {
			deselectInodes();
		}
	};

	function cssClasses() {
		const classes = ['inode-list'];
		if (settings.is_trash && !searchQuery) {
			classes.push('trash');
		}
		return classes.join(' ');
	}

	function renderInodes() {
		if (isLoading)
			return (<li className="status">{gettext("Loading...")}</li>);

		if (inodes.length === 0 && searchQuery)
			return (<li className="status">{`No match while searching for “${searchQuery}”`}</li>);

		return inodes.map(inode => inode.is_folder
			? <Folder key={inode.id} {...inode} {...props} selectInode={selectInode} updateInode={updateInode} isParent={previousFolderId === inode.id} />
			: <File key={inode.id} {...inode} {...props} selectInode={selectInode} updateInode={updateInode} />
		);
	}

	console.log('InodeList', folderId, inodes);

	return (
		<ul className={cssClasses()} onClick={deactivateInodes}>
			{layout === 'list' ? (
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
			) : null}
			{renderInodes()}
		</ul>
	)
});


export function DraggedInodes(props) {
	const {inodes, layout, style} = props;

	return (
		<ul className="inode-list" style={style}>{
			inodes.map(inode =>
			<Inode key={inode.id} {...inode}>
				<div className="inode">
					<ListItem {...inode} layout={layout} />
				</div>
			</Inode>)
		}</ul>
	);
}
