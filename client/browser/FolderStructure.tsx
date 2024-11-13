import React from 'react';
import ArrowDownIcon from '../icons/arrow-down.svg';
import ArrowRightIcon from '../icons/arrow-right.svg';
import EmptyIcon from '../icons/empty.svg';
import FolderIcon from '../icons/folder.svg';
import FolderOpenIcon from '../icons/folder-open.svg';
import RootIcon from '../icons/root.svg';


function FolderEntry(props) {
	const {folder, toggleOpen, setCurrentFolder, isCurrent} = props;

	if (folder.is_root) {
		return (<span onClick={() => setCurrentFolder(folder.id)}><RootIcon/></span>);
	}

	return (<>
		<i onClick={toggleOpen}>{
			folder.has_subfolders ? folder.is_open ? <ArrowDownIcon/> : <ArrowRightIcon/> : <EmptyIcon/>
		}</i>
		{isCurrent ?
		<strong><FolderOpenIcon/>{folder.name}</strong> :
		<span onClick={() => setCurrentFolder(folder.id)} role="button">
			<FolderIcon/>{folder.name}
		</span>
		}
	</>);
}


export default function FolderStructure(props) {
	const {baseUrl, folder, lastFolderId, setCurrentFolder, refreshStructure} = props;

	async function fetchChildren() {
		const response = await fetch(`${baseUrl}${folder.id}/fetch`);
		if (response.ok) {
			const reply = await response.json();
			folder.name = reply.name;
			folder.has_subfolders = reply.has_subfolders;
			folder.children = reply.children;
		} else {
			console.error(response);
		}
	}

	async function toggleOpen() {
		folder.is_open = !folder.is_open;
		if (folder.is_open) {
			if (folder.children === null) {
				await fetchChildren();
			} else {
				await fetch(`${baseUrl}${folder.id}/open`);
			}
		} else {
			await fetch(`${baseUrl}${folder.id}/close`);
		}
		refreshStructure();
	}

	return folder ? (
		<li>
			<FolderEntry
				folder={folder}
				toggleOpen={toggleOpen}
				setCurrentFolder={setCurrentFolder}
				isCurrent={lastFolderId === folder.id}
			/>
			{folder.is_open && (
			<ul>
			{folder.children.map(child => (
				<FolderStructure
					key={child.id}
					baseUrl={baseUrl}
					folder={child}
					lastFolderId={lastFolderId}
					setCurrentFolder={setCurrentFolder}
					refreshStructure={refreshStructure}
				/>
			))}
			</ul>)}
		</li>
	) : null;
}
