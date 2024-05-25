import React, {createRef, lazy, Suspense, useContext, useEffect, useMemo, useState} from 'react';
import {useDraggable, useDroppable} from '@dnd-kit/core';
import {FinderSettings} from './FinderSettings';


const dateTimeFormatter = new Intl.DateTimeFormat(
	navigator.language,
	{timeStyle: 'short', dateStyle: 'short'} as Intl.DateTimeFormatOptions,
);

export function DraggableItem(props) {
	const {
		attributes,
		listeners,
		setNodeRef,
	} = useDraggable({
		id: props.id,
		data: props,
		disabled: props.disabled,
	});
	const [event, setEvent] = useState<PointerEvent>(null);

	useEffect(
		() => {
			if (!event)
				return;
			const timer = setTimeout(() => {
				if (event.detail === 1) {
					props.listRef.current.selectInode(event, props);
				} else if (event.detail === 2) {
					props.listRef.current.selectInode(event, props);
				} else {
					// presumably a triple click, could be used to edit folder details
					console.log('selectInode', event.detail);
				}
			}, 150);

			return () => {
				clearTimeout(timer);
			};
		}, [event]
	);

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
		console.log('activateInode', event, props.id);
		setEvent(event);
		event.stopPropagation();
		event.preventDefault();
	}

	function renderChildren() {
		return React.Children.map(props.children, child => {
			return React.createElement(child.type, {className: child.props.className},
				React.Children.map(child.props.children, grandChild => {
					return React.cloneElement(grandChild, {listeners, attributes});
				})
			);
		});
	}

	if (props.isDragged)
		return (
			<li data-id={props.id}>
				{props.children}
			</li>
		);
	else
		return (
			<li ref={props.elementRef} data-id={props.id} className={cssClasses()} onClick={activateInode}>
				<div ref={setNodeRef}>
					{renderChildren()}
				</div>
			</li>
		);
}


function StaticFigure(props) {
	return (<>{props.children}</>);
}


export function ListItem(props) {
	const settings = useContext(FinderSettings);
	const FigBody = props.editor_component ? useMemo(
		() => {
			const component = `./components/${props.editor_component}.js`;
			const LazyFigure = lazy(() => import(component));
			return (props) => (<Suspense><LazyFigure {...props}>{props.children}</LazyFigure></Suspense>);
		},
		[]
	) : StaticFigure;
	const [focusHandler, setFocusHandler] = useState(null);

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
				await updateInode({...props, name: editedName});
			}
			if (enterKey) {
				event.preventDefault();
				event.target.blur();
			}
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
			const current = props.listRef.current;
			const body = await response.json();
			current.setInodes(current.inodes.map(inode =>
				inode.id === body.new_inode.id ? {...body.new_inode, elementRef: createRef()} : inode
			));
			props.folderTabsRef.current.setFavoriteFolders(body.favorite_folders);
		} else if (response.status === 409) {
			alert(await response.text());
		} else {
			console.error(response);
		}
	}

	function timestamp(dateTime: string) {
		const date = new Date(dateTime);
		return dateTimeFormatter.format(date);
	}

	switch (props.layout) {
		case 'tiles': case 'mosaic':
			return (
				<figure>
					<FigBody sampleUrl={props.sample_url}><img src={props.thumbnail_url} /></FigBody>
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
					<FigBody sampleUrl={props.sample_url}><img src={props.thumbnail_url} /></FigBody>
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
					<FigBody sampleUrl={props.sample_url}><img src={props.thumbnail_url} /></FigBody>
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
		<DraggableItem {...props}>
			<div className="inode">
				<ListItem {...props} />
			</div>
		</DraggableItem>
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
		<DraggableItem {...props}>
			<div ref={setNodeRef} className={cssClasses()}>
				<ListItem {...props} />
			</div>
		</DraggableItem>
	);
}
