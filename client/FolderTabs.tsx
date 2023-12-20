import {useDroppable} from '@dnd-kit/core';
import React, {forwardRef, useContext, useImperativeHandle, useState} from 'react';
import {FinderSettings} from './FinderSettings';
import CloseIcon from './icons/close.svg';
import PinIcon from './icons/pin.svg';
import RecycleIcon from './icons/recycle.svg';
import RootIcon from './icons/root.svg';
import UpIcon from './icons/folder-up.svg';


function FolderTab(props) {
	const settings = useContext(FinderSettings);
	const {folder, isSearchResult} = props;
	const {
		isOver,
		setNodeRef,
	} = useDroppable({
		id: `tab:${folder.id}`,
	});
	const isActive = folder.id === settings.folder_id;

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
		if (folder.is_trash) {
			classes.push('trash');
		}
		if (isOver) {
			classes.push('drag-over');
		}
		return classes.join(' ');
	}

	if (folder.id === 'parent') return (
		<li ref={setNodeRef} className={cssClasses(folder)} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Change to parent folder")}>
			<a href={settings.parent_url}><UpIcon /></a>
		</li>
	);

	if (folder.is_root) return (
		<li ref={setNodeRef} className={cssClasses(folder)} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Root folder")}>
		{!isActive || isSearchResult ? <a href={folder.change_url}><RootIcon /></a> : <RootIcon />}
		</li>
	);

	if (folder.is_trash) return (
		<li ref={setNodeRef} className={cssClasses(folder)} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Trash folder")}>
			{!isActive || isSearchResult ? <a href={folder.change_url}><RecycleIcon /></a> : <RecycleIcon />}
		</li>
	);

	return (
		<li ref={setNodeRef} className={cssClasses(folder)}>
			{!isActive || isSearchResult || settings.download_url ? <a href={folder.change_url}>{folder.name}</a> : folder.name}
			<span onClick={togglePin.bind(folder)}>{folder.is_pinned ? <CloseIcon /> : <PinIcon  data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Pin this folder")} />}</span>
		</li>
	);
}

export const FolderTabs = forwardRef((props: any, forwardedRef) => {
	const settings = useContext(FinderSettings);
	const {isSearchResult} = props;
	const [favoriteFolders, setFavoriteFolders] = useState(settings.favorite_folders);

	useImperativeHandle(forwardedRef, () => ({
		setFavoriteFolders: setFavoriteFolders,
	}));

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

	console.log('render FolderTabs');

	return (
		<ul className="folder-tabs">
			{settings.parent_id && <FolderTab key={'parent'} folder={{id: 'parent'}} />}
			{isSearchResult && <li className="active">{gettext("Search results")}</li>}
			{favoriteFolders.filter(
				folder => !isSearchResult || folder.is_pinned || folder.id !== settings.folder_id
			).map(folder =>
				<FolderTab
					key={folder.id}
					folder={folder}
					togglePin={togglePin}
					isSearchResult={isSearchResult}
				/>
			)}
		</ul>
	);
});
