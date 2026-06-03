import React, {lazy, Suspense, useCallback, useContext, useEffect, useMemo, useRef, useState} from 'react';
import FinderSettings from './FinderSettings';
import FileTags from '../common/FileTags';


function StaticFigure(props) {
	return (
		<FileTags tags={props.tags}>
			{props.children}
		</FileTags>
	);
}


function computeHash(selectedInodes): number {
	function djb2Hash(str) {
		let hash = 0;
		for (let i = 0; i < str.length; i++) {
			hash = (hash << 5) - hash + str.charCodeAt(i);
			hash |= 0;  // convert to 32-bit integer
		}
		return Math.abs(hash);
	}

	return selectedInodes.reduce((accum, inode) => djb2Hash(inode.id) ^ accum, 0);
}

export default function GalleryPreview(props) {
	const settings = useContext(FinderSettings);
	const {inodes, setInodes, folderTabsRef} = props;
	const inodeNameRef = useRef(null);
	const isFirstRender = useRef(true);
	const [previewInode, setPreviewInode] = useState(null);
	const selectedInodes = inodes.filter(inode => inode.selected);
	const selectedHash = computeHash(selectedInodes);
	const readonly = !previewInode?.can_change;

	useEffect(() => {
		if (isFirstRender.current) {
			isFirstRender.current = false;
			setPreviewInode(inodes.at(0));
		} else if (selectedInodes.length > 0) {
			setPreviewInode(selectedInodes.at(-1));
		}
	}, [selectedHash]);

	const FigBody = useMemo(() => {
		if (previewInode?.folderitem_component) {
			const component = `./components/folderitem/${previewInode.folderitem_component}.js`;
			const LazyItem = lazy(() => import(component));
			return (props) => (
				<Suspense>
					<LazyItem {...props}>{props.children}</LazyItem>
				</Suspense>
			);
		}
		return StaticFigure;
	}, [previewInode]);

	function handleFocus(event) {
		if (!(event.target.contentEditable))
			return;
	}

	async function updateName(event) {
		if (!(event.target.contentEditable))
			return;
		const enterKey = event.type === 'keydown' && event.key === 'Enter';
		if (event.type === 'blur' || enterKey) {
			const editedName = event.target.innerText.trim();
			if (editedName !== props.name) {
				await updateInode({name: editedName});
			}
			if (enterKey) {
				event.preventDefault();
				event.target.blur();
			}
		}
	}

	async function updateInode(changedFields) {
		const fetchUrl = `${settings.base_url}${settings.folder_id}/update`;
		const response = await fetch(fetchUrl, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': settings.csrf_token,
			},
			body: JSON.stringify({id: previewInode.id, ...changedFields}),
		});
		if (response.ok) {
			const body = await response.json();
			const updated = Object.fromEntries(
				Object.keys(changedFields).map(key => [key, body.new_inode[key]])
			);
			setInodes(inodes.map(inode =>
				inode.id === body.new_inode.id ? {...inode, ...updated} : inode
			));
			folderTabsRef.current.setFavoriteFolders(body.favorite_folders);
		} else if (response.status === 409) {
			alert(await response.text());
			inodeNameRef.current.innerText = previewInode.name;
		} else {
			console.error(response);
		}
	}

	function selectInode(event) {
		if (previewInode.disabled || settings.is_trash)
			return;
		window.location.assign(previewInode.change_url);
	}

	return previewInode && (
		<div className="preview" onDoubleClick={selectInode}>
			<div>
				<figure className={`figure${readonly ? ' readonly' : ''}`}>
					<FigBody sample_url={previewInode.download_url} {...props}>
						<img src={previewInode.preview_url} {...previewInode.listeners} {...previewInode.attributes} />
					</FigBody>
					<figcaption>
						<div ref={inodeNameRef} className="inode-name" contentEditable={!readonly} suppressContentEditableWarning={true} onFocus={handleFocus} onBlur={updateName} onKeyDown={updateName}>
							{previewInode.name}
						</div>
					</figcaption>
				</figure>
			</div>
		</div>
	);
}
