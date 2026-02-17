import React, {
	forwardRef,
	useImperativeHandle,
	useRef,
	useState,
} from 'react';
import {VERBOSE_HTTP_ERROR_CODES} from './constants';
import Dialog from './Dialog';
import AddEntryIcon from '../icons/add-entry.svg';
import TrashIcon from '../icons/trash.svg';


const TagEditor = forwardRef(function TagEditor(props: any, forwardedRef){
	const {settings} = props;
	const tbodyRef = useRef<HTMLTableSectionElement>(null);
	const newTagInputRef = useRef<HTMLInputElement>(null);
	const [tags, setTags] = useState(settings.tags ?? []);
	const [newTag, setNewTag] = useState({label: '', color: '#f0f0f0'});
	const [isOpen, setIsOpen] = useState(false);
	const [offset, setOffset] = useState({x: 0, y: 0});

	useImperativeHandle(forwardedRef, () => ({
		show: () => setIsOpen(true),
		close: () => setIsOpen(false),
		handleDragStart: (event) => {},
		handleDragEnd: (event) => event.active.id === 'tags-dialog' && setOffset({x: event.delta.x + offset.x, y: event.delta.y + offset.y}),
	}));

	function addTag() {
		if (newTag.label) {
			setTags([...tags, newTag]);
			newTagInputRef.current.value = '';
			setNewTag({...newTag, label: ''});
			tbodyRef.current.scrollBy({top: 50, behavior: 'smooth'});
		}
	}

	function dismissDialog() {
		newTagInputRef.current.value = '';
		setNewTag({...newTag, label: ''});
		setIsOpen(false);
		setOffset({x: 0, y: 0});
	}

	async function applyTags() {
		const tagsList = newTag.label ? [...tags, {label: newTag.label, color: newTag.color}] : tags;
		const url = `${settings.base_url}${settings.folder_id}/update_tags`;
		const response = await fetch(url, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': settings.csrf_token,
			},
			body: JSON.stringify({
				tags: tagsList,
			}),
		});
		if (response.ok) {
			const body = await response.json();
			setTags(body['tags']);
			dismissDialog();
		} else if (VERBOSE_HTTP_ERROR_CODES.has(response.status)) {
			alert(await response.text());
		} else {
			console.error(response);
		}
	}

	function updateLabel(index?: number) : Function {
		if (index === undefined) {
			return (event: Event) => {
				setNewTag({...newTag, label: (event.target as HTMLInputElement).value});
			};
		}
		return (event: Event) => {
			const tag = {...tags[index], label: (event.target as HTMLInputElement).value};
			setTags(tags.toSpliced(index, 1, tag));
		};
	}

	function updateColor(index?: number) : Function {
		if (index === undefined) {
			return (event: Event) => {
				setNewTag({...newTag, color: (event.target as HTMLInputElement).value});
			};
		}
		return (event: Event) => {
			const tag = {...tags[index], color: (event.target as HTMLInputElement).value};
			setTags(tags.toSpliced(index, 1, tag));
		};
	}

	return (
		<Dialog id="tags-dialog" label={gettext("Edit Tags")} isOpen={isOpen} offset={offset}>
			<table>
				<thead>
					<tr>
						<th>{gettext("Label")}</th>
						<th>{gettext("Color")}</th>
						<th></th>
					</tr>
				</thead>
				<tbody ref={tbodyRef}>
				{tags.map((entry, index) => (
					<tr key={`tag-${index}`}>
						<td>
							<input type="text" name="label" value={entry.label} onChange={event => updateLabel(index)(event)} />
						</td>
						<td>
							<input type="color" name="color" value={entry.color} onChange={event => updateColor(index)(event)} />
						</td>
						<td>
							<span onClick={() => setTags(tags.toSpliced(index, 1))}>
								<TrashIcon />
							</span>
						</td>
					</tr>
				))}
				{tags.length === 0 && (
					<tr>
						<td colSpan={3}><em>{gettext("Tags haven't been set.")}</em></td>
					</tr>
				)}
				</tbody>
				<tfoot>
					<tr>
						<td>
							<input ref={newTagInputRef} type="text" name="label" onChange={event => updateLabel()(event)} />
						</td>
						<td>
							<input type="color" name="color" defaultValue={newTag.color} onChange={event => updateColor()(event)} />
						</td>
						<td>
							<span onClick={() => addTag()} aria-disabled={!newTag.label} >
								<AddEntryIcon />
							</span>
						</td>
					</tr>
				</tfoot>
			</table>
			<div className="button-group">
				<button onClick={() => dismissDialog()}>{gettext("Dismiss")}</button>
				<button onClick={() => applyTags()}>{gettext("Apply")}</button>
			</div>
		</Dialog>
	);
});

export default TagEditor;
