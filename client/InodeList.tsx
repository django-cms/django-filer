import React, {
	createRef,
	forwardRef,
	useContext,
	useEffect,
	useImperativeHandle,
	useState,
} from 'react';
import {Folder, File, DraggableItem, ListItem} from './Item';
import {FinderSettings} from './FinderSettings';


export const InodeList = forwardRef((props: any, forwardedRef) => {
	const settings = useContext(FinderSettings);
	const {folderId, previousFolderId, setCurrentFolder, menuBarRef, layout} = props;
	const [isLoading, setLoading] = useState(false);
	const [inodes, setInodes] = useState([]);
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
		selectInode: selectInode,
		selectMultipleInodes: selectMultipleInodes,
		async fetchInodes() {
			await fetchInodes();
		},
		async addFolder() {
			await addFolder();
		},
	}));

	async function fetchInodes() {
		const params = new URLSearchParams({q: searchQuery});
		const fetchInodesUrl = `${settings.base_url}${folderId}/fetch${searchQuery ? `?${params.toString()}` : ''}`;
		setLoading(true);
		const response = await fetch(fetchInodesUrl);
		if (response.ok) {
			const body = await response.json();
			setInodes(body.inodes.map(inode => ({...inode, elementRef: createRef()})));
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
			setInodes([...inodes, {...body.new_folder, elementRef: createRef()}]);
		} else {
			console.error(response);
			return;
		}
	}

	function selectInode(event: PointerEvent, inode) {
		if (inode.disabled)
			return;
		console.log('selectInode', inodes);
		let modifier, selectedInode = -1;
		if (event.detail === 2) {
			// double click
			if (!settings.is_trash) {
				// prevent editing files in trash folder
				window.location.assign(inode.change_url);
			}
			return;
		}
		if ((event.detail as any)?.selected) {
			// this is a SelectableArea event
			console.info('SelectableArea event');
			debugger;
			modifier = f => ({...f, selected: f.selected || f.id === inode.id});
		} else if (event.shiftKey) {
			// shift click
			const selectedInodeIndex = inodes.findIndex(f => f.id === inode.id);
			if (selectedInodeIndex < lastSelectedInode) {
				modifier = (f, k) => ({...f, selected: k >= selectedInodeIndex && k <= lastSelectedInode || f.selected});
			} else if (lastSelectedInode !== -1 && selectedInodeIndex > lastSelectedInode) {
				modifier = (f, k) => ({...f, selected: k >= lastSelectedInode && k <= selectedInodeIndex || f.selected});
			} else {
				modifier = f => ({...f, selected: f.selected || f.id === inode.id});
			}
		} else if (event.altKey || event.ctrlKey || event.metaKey) {
			// alt/ctrl/meta click
			if (inode.selected) {
				modifier = f => ({...f, selected: f.selected && f.id !== inode.id});
			} else {
				modifier = f => ({...f, selected: f.selected || f.id === inode.id});
				selectedInode = inodes.findIndex(f => f.id === inode.id);  // remember for an upcoming shift-click
			}
		} else {
			// simple click
			if (inode.selected) {
				modifier = f => ({...f, selected: false});
			} else {
				if (!(event.target as HTMLElement)?.classList.contains('inode-name')) {
					// prevent selecting the inode when clicking on the name field to edit it
					modifier = f => ({...f, selected: f.id === inode.id});
					selectedInode = inodes.findIndex(f => f.id === inode.id);  // remember for an upcoming shift-click
				} else {
					modifier = f => f;
				}
			}
		}
		const modifiedInodes = inodes.map((f, k) => ({...modifier(f, k), cutted: false, copied: false}));
		setInodes(modifiedInodes);
		menuBarRef.current.setSelected(modifiedInodes.filter(inode => inode.selected));
		setCurrentFolder(folderId);
		setSelectedInode(selectedInode);
	}

	function selectMultipleInodes(selectedInodeIds: Array<string>, extend: boolean = false) {
		const modifiedInodes = inodes.map(inode => ({
			...inode,
			selected: extend && inode.selected || selectedInodeIds.includes(inode.id),
			cutted: false,
			copied: false,
		}));
		setCurrentFolder(folderId);
		setInodes(modifiedInodes);
		menuBarRef.current.setSelected(modifiedInodes.filter(inode => inode.selected));
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
		if (isLoading)
			return (<li className="status">{gettext("Loading...")}</li>);

		if (inodes.length === 0 && searchQuery)
			return (<li className="status">{`No match while searching for “${searchQuery}”`}</li>);

		return inodes.map(inode => inode.is_folder
			? <Folder key={inode.id} {...inode} {...props} isParent={previousFolderId === inode.id} />
			: <File key={inode.id} {...inode} {...props} />
		);
	}

	console.log('InodeList', folderId, inodes);

	return (
		<ul className={cssClasses()}>
			{layout === 'list' &&
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
			}
			{renderInodes()}
		</ul>
	)
});


export function DraggedInodes(props) {
	const {inodes, layout, style} = props;

	return (
		<ul className="inode-list" style={style}>{
			inodes.map(inode =>
			<DraggableItem key={inode.id} {...inode} isDragged={true}>
				<div className="inode">
					<ListItem {...inode} layout={layout} />
				</div>
			</DraggableItem>)
		}</ul>
	);
}
