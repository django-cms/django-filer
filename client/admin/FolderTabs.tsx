import {useDroppable} from '@dnd-kit/core';
import React, {forwardRef, useImperativeHandle, useState} from 'react';
import {Tooltip, TooltipContent, TooltipTrigger} from '../common/Tooltip';
import CloseIcon from '../icons/close.svg';
import PinIcon from '../icons/pin.svg';
import RecycleIcon from '../icons/recycle.svg';
import RootIcon from '../icons/root.svg';
import UpIcon from '../icons/folder-up.svg';


function FolderTab(props) {
	const {folder, isSearchResult, settings} = props;
	const {
		isOver,
		setNodeRef,
	} = useDroppable({
		id: `tab:${folder.id}`,
	});
	const isActive = settings.is_folder && folder.id === settings.folder_id;

	function togglePin(event) {
		props.togglePin(this.id);
		event.stopPropagation();
		event.preventDefault();
	}

	function cssClasses(folder) {
		const classes = [];
		if (isActive) {
			if (!settings.download_url && !isSearchResult) {
				classes.push('active');
			} else {
				classes.push('current');
			}
		}
		if (folder.can_change === false) {
			classes.push('readonly');
		}
		if (folder.is_trash) {
			classes.push('trash');
		}
		if (isOver) {
			classes.push('drag-over');
		}
		return classes.join(' ');
	}

	if (folder.id === 'return') return (
		<li ref={setNodeRef} className={cssClasses(folder)}>
			<Tooltip placement="top-start">
				<TooltipTrigger>
					<a href={settings.folder_url}><UpIcon /></a>
				</TooltipTrigger>
				<TooltipContent>{gettext("Change to folder view")}</TooltipContent>
			</Tooltip>
		</li>
	);

	if (folder.id === 'parent') return (
		<li ref={setNodeRef} className={cssClasses(folder)}>
			<Tooltip placement="top-start">
				<TooltipTrigger>
					<a href={settings.parent_url}><UpIcon /></a>
				</TooltipTrigger>
				<TooltipContent>{gettext("Change to parent folder")}</TooltipContent>
			</Tooltip>
		</li>
	);

	if (folder.is_root) return (
		<li ref={setNodeRef} className={cssClasses(folder)}>
			<Tooltip placement="top-start">
				<TooltipTrigger>
				{!isActive || isSearchResult ? <a href={folder.change_url}><RootIcon /></a> : <RootIcon />}
				</TooltipTrigger>
				<TooltipContent>{gettext("Root folder")}</TooltipContent>
			</Tooltip>
		</li>
	);

	const TrashFolder = () => (
		<Tooltip placement="top-end">
			<TooltipTrigger><RecycleIcon /></TooltipTrigger>
			<TooltipContent root={settings.rootNode}>{gettext("Trash folder")}</TooltipContent>
		</Tooltip>
	);

	if (folder.is_trash) return (
		<li ref={setNodeRef} className={cssClasses(folder)}>
			{!isActive || isSearchResult ? <a href={folder.change_url}><TrashFolder /></a> : <TrashFolder />}
		</li>
	);

	return (
		<li ref={setNodeRef} className={cssClasses(folder)}>
			{!isActive || isSearchResult || settings.download_url ? <a href={folder.change_url}>{folder.name}</a> : folder.name}
			<span onClick={togglePin.bind(folder)}>{folder.is_pinned ?
				<CloseIcon /> :
				<Tooltip placement="top">
					<TooltipTrigger><PinIcon /></TooltipTrigger>
					<TooltipContent>{gettext("Pin this folder")}</TooltipContent>
				</Tooltip>
			}</span>
		</li>
	);
}

const FolderTabs = forwardRef(function FolderTabs(props: any, forwardedRef) {
	const {isSearchResult, settings} = props;
	const [favoriteFolders, setFavoriteFolders] = useState(settings.favorite_folders);

	useImperativeHandle(forwardedRef, () => ({setFavoriteFolders}));

	async function togglePin(pinnedId) {
		const togglePinUrl = `${settings.base_url}${settings.folder_id}/toggle_pin`;
		const response = await fetch(togglePinUrl, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': settings.csrf_token,
			},
			body: JSON.stringify({
				pinned_id: pinnedId
			}),
		});
		if (response.ok) {
			const data = await response.json();
			if (data.success_url) {
				// unpinned current folder, redirect to success_url
				window.location.assign(data.success_url);
				return;
			}
			setFavoriteFolders(data.favorite_folders);
		}
	}

	return (
		<ul className="folder-tabs">
			{isSearchResult || settings.is_trash ? (<>
				<FolderTab key={'return'} folder={{id: 'return'}} isSearchResult={isSearchResult} settings={settings} />
			</>) : (
				settings.parent_id && (<FolderTab key={'parent'} folder={{id: 'parent'}} settings={settings} />)
			)}
			{favoriteFolders.filter(
				folder => !isSearchResult && !settings.file_id || folder.is_pinned || folder.id !== settings.folder_id
			).map(folder =>
				<FolderTab
					key={folder.id}
					folder={folder}
					togglePin={togglePin}
					isSearchResult={isSearchResult}
					settings={settings}
				/>
			)}
		</ul>
	);
});


export default FolderTabs;
