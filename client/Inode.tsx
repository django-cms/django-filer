import React, {useContext, useState} from 'react';
import {useDraggable, useDroppable} from '@dnd-kit/core';
import {FinderSettings} from './FinderSettings';


export function Inode(props) {
	const {
		attributes,
		listeners,
		setNodeRef,
	} = useDraggable({
		id: props.id,
		data: props,
		disabled: props.disabled,
	});
	const [clickHandler, setClickHandler] = useState(null);

	function cssClasses() {
		let classes = [];
		if (props.disabled) {
			classes.push('disabled');
		} else if (props.selected) {
			classes.push('selected');
		} else if (props.copied) {
			classes.push('copied');
		} else if (props.cutted) {
			classes.push('cutted');
		}
		if (props.dragged) {
			classes.push('dragging');
		}
		return classes.join(' ');
	}

	function activateInode(event) {
		if (event.detail === 1) {
			setClickHandler(window.setTimeout(() => {
				props.selectInode.bind(props)(event);
				setClickHandler(null);
			}, 250));
		} else if (event.detail === 2) {
			if (clickHandler) {
				window.clearTimeout(clickHandler);
				setClickHandler(null);
			}
			props.selectInode.bind(props)(event);
		} else if (event.detail.selected) {
			props.selectInode.bind(props)(event);
		}
		event.stopPropagation();
		event.preventDefault();
	}

	if (props.selectInode)
		return (
			<li ref={props.elementRef} data-id={props.id} className={cssClasses()} onClick={activateInode} {...listeners} {...attributes}>
				<div ref={setNodeRef}>
					{props.children}
				</div>
			</li>
		);
	else
		return (
			<li data-id={props.id}>
				{props.children}
			</li>
		);
}


export function ListItem(props) {
	const settings = useContext(FinderSettings);
	const [focusHandler, setFocusHandler] = useState(null);
	const [name, setName] = useState(props.name);

	function swallowEvent(event) {
		event.stopPropagation();
		event.preventDefault();
	}

	function handleFocus(event) {
		if (!(event.target.contentEditable))
			return;
		if (!focusHandler) {
			event.target.blur();
		}
		// enforce two slow clicks to focus the contenteditable element
		setFocusHandler(window.setTimeout(() => {
			if (focusHandler) {
				window.clearTimeout(focusHandler);
			}
			setFocusHandler(null);
		}, 2000));
	}

	async function updateName(event) {
		if (!(event.target.contentEditable))
			return;
		const enterKey = event.type === 'keydown' && event.key === 'Enter';
		if (event.type === 'blur' || enterKey) {
			const editedName = event.target.innerText.trim();
			if (editedName !== props.name) {
				await props.updateInode({...props, name: editedName});
			}
			if (enterKey) {
				event.preventDefault();
				event.target.blur();
			}
		}
	}

	function timestamp(dateTime: string) {
		const date = new Date(dateTime);
		return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
	}

	switch (props.layout) {
		case 'tiles': case 'mosaic':
			return (
				<figure>
					<img src={props.thumbnail_url} />
					<figcaption>
						<div className="inode-name" contentEditable={!settings.is_trash} suppressContentEditableWarning={true} onFocus={handleFocus} onBlur={updateName} onKeyDown={updateName}>
							{props.name}
						</div>
					</figcaption>
				</figure>
			);
		case 'list':
			return (<>
				<div>
					<img src={props.thumbnail_url} />
				</div>
				<div>
					<div className="inode-name" contentEditable={!settings.is_trash} suppressContentEditableWarning={true} onFocus={handleFocus} onBlur={updateName} onKeyDown={updateName}>
						{props.name}
					</div>
				</div>
				<div>
					{props.owner_name}
				</div>
				<div>
					{props.summary}
				</div>
				<div>{timestamp(props.created_at)}</div>
				<div>{timestamp(props.last_modified_at)}</div>
				<div>{props.mime_type}</div>
			</>);
		case 'columns':
			return (<>
				<div>
					<img src={props.thumbnail_url} />
				</div>
				<div>
					<div className="inode-name" contentEditable={!settings.is_trash} suppressContentEditableWarning={true} onFocus={handleFocus} onBlur={updateName} onKeyDown={updateName}>
						{props.name}
					</div>
				</div>
			</>);
	}
}


export function File(props) {
	return (
		<Inode {...props}>
			<div className="inode">
				<ListItem {...props} />
			</div>
		</Inode>
	);
}


export function Folder(props) {
	const {
		isOver,
		active,
		setNodeRef,
	} = useDroppable({
		id: `folder:${props.id}`,
		disabled: props.disabled,
	});

	function cssClasses() {
		const classes = ['inode'];
		if (props.isParent) {
			classes.push('parent');
		}
		if (isOver && active.id !== props.id) {
			classes.push('drag-over');
		}
		if (props.disabled) {
			classes.push('disabled');
		}
		return classes.join(' ');
	}

	return (
		<Inode {...props}>
			<div ref={setNodeRef} className={cssClasses()}>
				<ListItem {...props} />
			</div>
		</Inode>
	);
}
