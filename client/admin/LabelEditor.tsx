import React, {
	forwardRef,
	useImperativeHandle,
	useRef,
	useState,
} from 'react';
import Dialog from './Dialog';
import AddEntryIcon from '../icons/add-entry.svg';
import TrashIcon from '../icons/trash.svg';


const LabelEditor = forwardRef((props: any, forwardedRef) => {
	const {settings} = props;
	const tbodyRef = useRef<HTMLTableSectionElement>(null);
	const newLabelInputRef = useRef<HTMLInputElement>(null);
	const [labels, setLabels] = useState(settings.labels);
	const [newLabel, setNewLabel] = useState({name: '', color: '#f0f0f0'});
	const [isOpen, setIsOpen] = useState(false);
	const [offset, setOffset] = useState({x: 0, y: 0});

	useImperativeHandle(forwardedRef, () => ({
		show: () => setIsOpen(true),
		handleDragStart: (event) => {},
		handleDragEnd: (event) => event.active.id === 'labels-dialog' && setOffset({x: event.delta.x + offset.x, y: event.delta.y + offset.y}),
	}));

	function addLabel() {
		if (newLabel.name) {
			setLabels([...labels, newLabel]);
			newLabelInputRef.current.value = '';
			setNewLabel({...newLabel, name: ''});
			tbodyRef.current.scrollBy({top: 50, behavior: 'smooth'});
		}
	}

	function dismissDialog() {
		newLabelInputRef.current.value = '';
		setNewLabel({...newLabel, name: ''});
		setIsOpen(false);
		setOffset({x: 0, y: 0});
	}

	async function applyLabels() {
		const labelsList = newLabel.name ? [...labels, {name: newLabel.name, color: newLabel.color}] : labels;
		const url = `${settings.base_url}${settings.folder_id}/labels`;
		const response = await fetch(url, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': settings.csrf_token,
			},
			body: JSON.stringify({
				labels: labelsList,
			}),
		});
		if (response.ok) {
			const body = await response.json();
			setLabels(body['labels']);
			dismissDialog();
		} else {
			console.error(response);
		}
	}

	function updateLabel(index?: number) : Function {
		if (index === undefined) {
			return (event: Event) => {
				setNewLabel({...newLabel, name: (event.target as HTMLInputElement).value});
			};
		}
		return (event: Event) => {
			const label = {...labels[index], name: (event.target as HTMLInputElement).value};
			setLabels(labels.toSpliced(index, 1, label));
		};
	}

	function updateColor(index?: number) : Function {
		if (index === undefined) {
			return (event: Event) => {
				setNewLabel({...newLabel, color: (event.target as HTMLInputElement).value});
			};
		}
		return (event: Event) => {
			const label = {...labels[index], color: (event.target as HTMLInputElement).value};
			setLabels(labels.toSpliced(index, 1, label));
		};
	}

	return (
		<Dialog id="labels-dialog" label={gettext("Edit Labels")} isOpen={isOpen} offset={offset}>
			<table>
				<thead>
					<tr>
						<th>{gettext("Label")}</th>
						<th>{gettext("Color")}</th>
						<th></th>
					</tr>
				</thead>
				<tbody ref={tbodyRef}>
				{labels.map((entry, index) => (
					<tr key={`label-${index}`}>
						<td>
							<input type="text" name="label" value={entry.name} onChange={event => updateLabel(index)(event)} />
						</td>
						<td>
							<input type="color" name="color" value={entry.color} onChange={event => updateColor(index)(event)} />
						</td>
						<td>
							<span onClick={() => setLabels(labels.toSpliced(index, 1))}>
								<TrashIcon />
							</span>
						</td>
					</tr>
				))}
				{labels.length === 0 && (
					<tr>
						<td colSpan={3}><em>{gettext("Labels haven't been set.")}</em></td>
					</tr>
				)}
				</tbody>
				<tfoot>
					<tr>
						<td>
							<input ref={newLabelInputRef} type="text" name="label" onChange={event => updateLabel()(event)} />
						</td>
						<td>
							<input type="color" name="color" defaultValue={newLabel.color} onChange={event => updateColor()(event)} />
						</td>
						<td>
							<span onClick={() => addLabel()} aria-disabled={!newLabel.name} >
								<AddEntryIcon />
							</span>
						</td>
					</tr>
				</tfoot>
			</table>
			<div className="button-group">
				<button onClick={() => dismissDialog()}>{gettext("Dismiss")}</button>
				<button onClick={() => applyLabels()}>{gettext("Apply")}</button>
			</div>
		</Dialog>
	);
});

export default LabelEditor;
