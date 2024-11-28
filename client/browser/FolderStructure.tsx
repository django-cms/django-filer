import React, {useEffect, useRef} from 'react';
import ArrowDownIcon from '../icons/arrow-down.svg';
import ArrowRightIcon from '../icons/arrow-right.svg';
import EmptyIcon from '../icons/empty.svg';
import FolderIcon from '../icons/folder.svg';
import FolderOpenIcon from '../icons/folder-open.svg';
import RootIcon from '../icons/root.svg';


function FolderEntry(props) {
	const {folder, toggleOpen, setCurrentFolder, openRecursive, isCurrent, isListed, setCurrentFolderElement} = props;
	const ref = useRef(null);

	if (folder.is_root) {
		return (<i onClick={() => setCurrentFolder(folder.id)}><RootIcon/></i>);
	}

	useEffect(() => {
		if (isCurrent) {
			setCurrentFolderElement(ref.current);
		}
	}, []);

	return (<>{
		folder.has_subfolders ? <i onClick={toggleOpen}>{
			folder.is_open ? <ArrowDownIcon/> : <ArrowRightIcon/>
		}</i> : <i><EmptyIcon/></i>}
		<i onClick={() => openRecursive()} role="button">{isListed || isCurrent ? <FolderOpenIcon/> : <FolderIcon/>}</i>
		{isCurrent
			? <strong ref={ref}>{folder.name}</strong>
			: <span onClick={() => setCurrentFolder(folder.id)} role="button">{folder.name}</span>
		}
	</>);
}


export default function FolderStructure(props) {
	const {baseUrl, folder, lastFolderId, setCurrentFolder, toggleRecursive, refreshStructure, setCurrentFolderElement} = props;
	const isListed = props.isListed === false ? lastFolderId === folder.id : props.isListed;
	const isCurrent = lastFolderId === folder.id;

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
		if (folder.is_open) {
			folder.is_open = false;
			await fetch(`${baseUrl}${folder.id}/close`);
		} else {
			folder.is_open = true;
			if (folder.children === null) {
				await fetchChildren();
			} else {
				await fetch(`${baseUrl}${folder.id}/open`);
			}
		}
		refreshStructure();
	}

	async function openRecursive() {
		if (lastFolderId === folder.id) {
			if (folder.is_open === false) {
				folder.is_open = true;
				if (folder.children === null) {
					await fetchChildren();
				} else {
					await fetch(`${baseUrl}${folder.id}/open`);
				}
			}
			await toggleRecursive(folder.id);
		} else {
			await setCurrentFolder(folder.id);
		}
	}

	return folder ? (
		<li>
			<FolderEntry
				folder={folder}
				toggleOpen={toggleOpen}
				setCurrentFolder={setCurrentFolder}
				openRecursive={openRecursive}
				isCurrent={isCurrent}
				isListed={isListed}
				setCurrentFolderElement={setCurrentFolderElement}
			/>
			{folder.is_open && folder.children && (
			<ul>
			{folder.children.map(child => (
				<FolderStructure
					key={child.id}
					baseUrl={baseUrl}
					folder={child}
					lastFolderId={lastFolderId}
					setCurrentFolder={setCurrentFolder}
					toggleRecursive={toggleRecursive}
					refreshStructure={refreshStructure}
					isListed={isListed}
					setCurrentFolderElement={setCurrentFolderElement}
				/>
			))}
			</ul>)}
		</li>
	) : null;
}
