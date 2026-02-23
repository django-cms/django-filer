import React, {lazy, memo, Suspense, useContext, useEffect, useMemo, useState} from 'react';
import {useDraggable, useDroppable} from '@dnd-kit/core';
import FinderSettings from './FinderSettings';
import DroppableArea from './DroppableArea';
import {useSearchParam} from './SearchField';
import {useSorting} from '../common/SortingOptions';
import {useFilter} from '../common/FilterByTag';
import FileTags from '../common/FileTags';
import {Tooltip, TooltipContent, TooltipTrigger} from "../common/Tooltip";


const dateTimeFormatter = new Intl.DateTimeFormat(
	navigator.language,
	{timeStyle: 'short', dateStyle: 'short'} as Intl.DateTimeFormatOptions,
);


export function DraggableItem(props) {
	const {sortingDisabled} = props;
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
	const [sorting] = useSorting();
	const [filter] = useFilter();
	const [searchQuery] = useSearchParam('q');
	const ReOrdering = useMemo(() => {
		return (props) => {
			if (sortingDisabled || searchQuery || sorting || filter.some(v => v))
				return <div className="reordering"></div>;
			return (
				<DroppableArea
					id={`reorder:${props.id}:${props.folderId}`}
					dragging={props.dragging}
					className="reordering"
				>
					<div></div>
				</DroppableArea>
			);
		};
	}, []);

	useEffect(() => {
		if (!event)
			return;
		const timer = setTimeout(() => {
			if (event.detail === 1 || event.detail === 2) {
				props.listRef.current.selectInode(event, props);
			} else {
				// presumably a triple click, could be used to edit folder details
				console.debug('selectInode', event.detail);
			}
		}, 200);

		return () => {
			clearTimeout(timer);
		};
	}, [event]);

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
		setEvent(event);
		event.stopPropagation();
		event.preventDefault();
	}

	if (props.isDragged)
		return (
			<li data-id={props.id} style={{zoom: props.zoom}}>
				{props.children}
			</li>
		);
	else
		return (
			<li ref={props.elementRef} data-id={props.id} className={cssClasses()} onClick={activateInode}>
				<div ref={setNodeRef} {...listeners} {...attributes}>
					{props.children}
				</div>
				<ReOrdering {...props}></ReOrdering>
			</li>
		);
}


function StaticFigure(props) {
	return (<>{props.children}</>);
}


export function ListItem(props) {
	const settings = useContext(FinderSettings);
	const [focusHandler, setFocusHandler] = useState(null);
	const FigBody = useMemo(() => {
		if (props.folderitem_component) {
			const component = `./components/folderitem/${props.folderitem_component}.js`;
			const LazyItem = lazy(() => import(component));
			return (props) => (
				<Suspense>
					<LazyItem {...props}>{props.children}</LazyItem>
				</Suspense>
			);
		}
		return StaticFigure;
	}, []);

	function handleFocus(event) {
		if (!(event.target.contentEditable))
			return;
		// enforce two slow clicks to focus the contenteditable element
		// they must be at least 333ms apart and the second click must be within 2s of the first
		if (focusHandler === null) {
			event.target.blur();
			setFocusHandler([new Date().getTime(), window.setTimeout(() => {
				setFocusHandler(null);
			}, 2000)]);
		} else if (focusHandler[0] + 333 > new Date().getTime()) {
			event.target.blur();
		}
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
			body: JSON.stringify({id: props.id, ...changedFields}),
		});
		if (response.ok) {
			const current = props.listRef.current;
			const body = await response.json();
			const updated = Object.fromEntries(
				Object.keys(changedFields).map(key => [key, body.new_inode[key]])
			);
			current.setInodes(current.inodes.map(inode =>
				inode.id === body.new_inode.id ? {...inode, ...updated} : inode
			));
			props.folderTabsRef.current.setFavoriteFolders(body.favorite_folders);
		} else if (response.status === 409) {
			alert(await response.text());
			props.elementRef.current.querySelector('.inode-name').innerText = props.name;
		} else {
			console.error(response);
		}
	}

	function timestamp(dateTime: string) {
		const date = new Date(dateTime);
		return dateTimeFormatter.format(date);
	}

	const readonly = settings.is_trash || !props.can_change;
	switch (props.layout) {
		case 'tiles':
			return (
				<figure className={`figure${readonly ? ' readonly' : ''}`}>
					<FigBody {...props}>
						<FileTags tags={props.tags}>
							<img src={props.thumbnail_url} {...props.listeners} {...props.attributes} />
						</FileTags>
					</FigBody>
					<figcaption>
						<div className="inode-name" contentEditable={!readonly} suppressContentEditableWarning={true} onFocus={handleFocus} onBlur={updateName} onKeyDown={updateName}>
							{props.name}
						</div>
					</figcaption>
				</figure>
			);
		case 'mosaic':
			return (
				<Tooltip>
					<TooltipTrigger>
						<div className={`figure${readonly ? ' readonly' : ''}`}>
							<FigBody {...props}>
								<FileTags tags={props.tags}>
									<img src={props.thumbnail_url} {...props.listeners} {...props.attributes} />
								</FileTags>
							</FigBody>
						</div>
					</TooltipTrigger>
					<TooltipContent>{props.name}</TooltipContent>
				</Tooltip>
			);
		case 'list':
			return (<>
				<div className={`figure${readonly ? ' readonly' : ''}`}>
					<FigBody {...props}>
						<FileTags tags={props.tags}>
							<img src={props.thumbnail_url} {...props.listeners} {...props.attributes} />
						</FileTags>
					</FigBody>
				</div>
				<div>
					<div className="inode-name" contentEditable={!readonly} suppressContentEditableWarning={true} onFocus={handleFocus} onBlur={updateName} onKeyDown={updateName}>
						{props.name}
					</div>
				</div>
				<div>
					{props.owner}
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
				<div className={`figure${readonly ? ' readonly' : ''}`}>
					<FigBody {...props}>
						<FileTags tags={props.tags}>
							<img src={props.thumbnail_url} {...props.listeners} {...props.attributes} />
						</FileTags>
					</FigBody>
				</div>
				<div>
					<div className="inode-name" contentEditable={!readonly} suppressContentEditableWarning={true} onFocus={handleFocus} onBlur={updateName} onKeyDown={updateName}>
						{props.name}
					</div>
				</div>
			</>);
	}
}


export const File = memo(function File(props: any) {
	return (
		<DraggableItem {...props}>
			<div className="inode">
				<ListItem {...props} />
			</div>
		</DraggableItem>
	);
});


export const Folder = memo(function Folder(props: any) {
	const {
		isOver,
		active,
		setNodeRef,
	} = useDroppable({
		id: `folder:${props.id}`,
		disabled: props.disabled || props.settings.is_trash,
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
});
