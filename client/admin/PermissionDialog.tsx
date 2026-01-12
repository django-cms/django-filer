import React, {
	forwardRef,
	useCallback,
	useEffect,
	useImperativeHandle,
	useRef,
	useState,
} from 'react';
import {useDraggable, DragStartEvent, DragMoveEvent, DragEndEvent} from '@dnd-kit/core';
import {useCombobox} from 'downshift';
import AddEntryIcon from '../icons/add-entry.svg';
import EveryoneIcon from '../icons/everyone.svg';
import GroupIcon from '../icons/group.svg';
import TrashIcon from '../icons/trash.svg';
import UserIcon from '../icons/user.svg';
import UserMeIcon from '../icons/user-me.svg';


type AccessControlEntry = {
	id: string,
	type: 'user'|'group'|'everyone',
	principal: number|null,
	name: string,
	privilege: ''|'r'|'rw'|'rx'|'rwx',
	is_current_user: boolean,
};


const SelectPrincipal = forwardRef((props: any, forwardedRef) => {
	const {acl, selectedItem, setSelectedItem, settings} = props;
	const inputRef = useRef<HTMLInputElement>(null);
	const [inputValue, setInputValue] = useState<string>('');
	const [principals, setPrincipals] = useState<AccessControlEntry[]>([]);
	const [items, setItems] = useState<AccessControlEntry[]>([]);
	const {
		isOpen,
		getToggleButtonProps,
		getMenuProps,
		getInputProps,
		getItemProps,
	} = useCombobox({
		items,
		itemToString(item) {
			return item ? item.name : ''
		},
		onInputValueChange({inputValue, type}) {
			setInputValue(inputValue);
			if (type === useCombobox.stateChangeTypes.InputChange) {
				fetchPrincipals(new URLSearchParams({q: inputValue}));
				setSelectedItem(null);
			}
		},
		selectedItem,
		onSelectedItemChange: ({selectedItem: newSelectedItem}) => {
			setSelectedItem(newSelectedItem);
			setInputValue(newSelectedItem.name);
			inputRef.current.blur();
		},
	});
	useImperativeHandle(forwardedRef, () => ({
		clearInput: () => {
			fetchPrincipals(new URLSearchParams());
			setInputValue('');
		},
	}));
	useEffect(() => {
		fetchPrincipals(new URLSearchParams());
	}, []);
	useEffect(() => {
		setItems(principals.filter(item => {
			return !acl.find(ace => ace.type === item.type && ace.principal === item.principal)
		}));
	}, [principals, acl]);

	async function fetchPrincipals(params?: URLSearchParams) {
		const url = `${settings.base_url}principals?${params.toString()}`;
		const response = await fetch(url);
		if (response.ok) {
			const body = await response.json();
			setPrincipals(body.access_control_results);
		} else {
			console.error(response);
		}
	}

	return (
		<div className="select-field">
			{selectedItem && !isOpen && (<PrivilegeTypeIcon ace={selectedItem} />)}
			<input
				placeholder={gettext("Select user/group")}
				className="select-input"
				{...getInputProps({ref: inputRef, value: inputValue})}
			/>
			<div className="toggle-dropdown" aria-haspopup="listbox" {...getToggleButtonProps()}></div>
			<ul {...getMenuProps()}>
				{isOpen && items.map((item, index) => (
				<li key={`item-${index}`} {...getItemProps({item, index})}>
					<PrivilegeTypeIcon ace={item} />
					{item.name}
				</li>
				))}
				{isOpen && items.length === 0 && (
				<li><em>{gettext("No principals available.")}</em></li>
				)}
			</ul>
		</div>
	);
});


function SelectPrivilege(props) {
	const {value, setValue} = props;

	return (
		<select onChange={event => setValue(event.target.value)} value={value}>
			<option value="r">{gettext("Read")}</option>
			<option value="rw">{gettext("Read & Write")}</option>
			<option value="rx">{gettext("Read & Execute")}</option>
			<option value="rwx">{gettext("Read, Write & Execute")}</option>
		</select>
	);
}


function PrivilegeTypeIcon(props) {
	const {ace} = props;
	switch (ace.type) {
		case 'user':
			return ace.is_current_user ? <UserMeIcon /> : <UserIcon />;
		case 'group':
			return <GroupIcon />;
		case 'everyone':
			return <EveryoneIcon />;
		default:
			console.error(`Unsupported type "${ace.type}"`);
			return <span>❓</span>;
	}
}


const PermissionDialog = forwardRef((props: any, forwardedRef) => {
	const {settings} = props;
	const dialogRef = useRef<HTMLDialogElement>(null);
	const tbodyRef = useRef<HTMLTableSectionElement>(null);
	const selectPrincipalRef = useRef(null);
	const [isOpen, setIsOpen] = useState(false);
	const [newPrincipal, setNewPrincipal] = useState(null);
	const [newPrivilege, setNewPrivilege] = useState('r');
	const [acl, setAcl] = useState<AccessControlEntry[]>([]);
	const [offset, setOffset] = useState({x: 0, y: 0});
	const {
		attributes,
		listeners,
		setNodeRef,
		transform,
	} = useDraggable({
		id: 'permission-dialog',
	});

	useImperativeHandle(forwardedRef, () => ({
		show: () => setIsOpen(true),
		handleDragStart: () => setOffset({x: offset.x, y: offset.y}),
		handleDragEnd: () => setOffset({x: transform.x + offset.x, y: transform.y + offset.y}),
	}));

	// combined ref: assign dialog element to both dialogRef and dnd-kit setNodeRef
	const combinedRef = useCallback((element: HTMLDialogElement) => {
		dialogRef.current = element;
		setNodeRef(element);
	}, [setNodeRef]);

	useEffect(() => {
		if (dialogRef.current?.open && !isOpen) {
			dialogRef.current.close();
		} else if (!dialogRef.current?.open && isOpen) {
			fetchPermissions().then(() => dialogRef.current.show());
		}
	}, [isOpen]);

	useEffect(() => {
		tbodyRef.current.scrollBy({top: 50, behavior: 'smooth'});
	}, [acl]);

	async function fetchPermissions() {
		const url = `${settings.base_url}${settings.folder_id}/permissions`;
		const response = await fetch(url);
		if (response.ok) {
			const body = await response.json();
			setAcl(body.access_control_list);
		} else {
			console.error(response);
		}
	}

	function addToACL() {
		if (newPrincipal) {
			setAcl([...acl, {...newPrincipal, privilege: newPrivilege}]);
			selectPrincipalRef.current.clearInput();
			setNewPrincipal(null);
			setNewPrivilege('r');
		}
	}

	function dismissDialog() {
		selectPrincipalRef.current.clearInput();
		setNewPrincipal(null);
		setNewPrivilege('r');
		setIsOpen(false);
		setOffset({x: 0, y: 0});
	}

	async function applyACL() {
		const accessControlList = newPrincipal ? [...acl, {...newPrincipal, privilege: newPrivilege}] : acl;
		const url = `${settings.base_url}${settings.folder_id}/permissions`;
		const response = await fetch(url, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': settings.csrf_token,
			},
			body: JSON.stringify({
				access_control_list: accessControlList,
			}),
		});
		if (response.ok) {
			dismissDialog();
		} else {
			console.error(response);
		}
	}

	function updatePrivilege(index: number) {
		return (privilege: string) => {
			const updatedAce = {...acl[index], privilege} as AccessControlEntry;
			setAcl(acl.toSpliced(index, 1, updatedAce));
		};
	}

	const dialogStyle : React.CSSProperties = {
		transform: transform
			? `translate(${transform.x + offset.x}px, ${transform.y + offset.y}px)`
			: `translate(${offset.x}px, ${offset.y}px)`,
	};

	return (
		<dialog ref={combinedRef} style={dialogStyle}>
			<h3 {...listeners} {...attributes}>{gettext("Folder Permissions")}</h3>
			<table>
				<thead>
					<tr>
						<th>{gettext("Principal")}</th>
						<th>{gettext("Privilege")}</th>
					</tr>
				</thead>
				<tbody ref={tbodyRef}>
				{acl.map((ace, index) => (
					<tr key={`ace-${index}`}>
						<td aria-label={`${ace.type}: ${ace.name}`}>
							<PrivilegeTypeIcon ace={ace} />
							{ace.name}
						</td>
						<td>
							<SelectPrivilege value={ace.privilege} setValue={updatePrivilege(index)} />
							<span onClick={() => setAcl(acl.toSpliced(index, 1))}>
								<TrashIcon />
							</span>
						</td>
					</tr>
				))}
				{acl.length === 0 && (
					<tr>
						<td colSpan={2}><em>{gettext("Permissions haven't been set.")}</em></td>
					</tr>
				)}
				</tbody>
				<tfoot>
					<tr>
						<td className="select-container">
							<SelectPrincipal
								ref={selectPrincipalRef}
								acl={acl}
								selectedItem={newPrincipal}
								setSelectedItem={setNewPrincipal}
								settings={settings}
							/>
						</td>
						<td>
							<SelectPrivilege value={newPrivilege} setValue={setNewPrivilege} />
							<span onClick={() => addToACL()} aria-disabled={!newPrincipal} >
								<AddEntryIcon />
							</span>
						</td>
					</tr>
				</tfoot>
			</table>
			<div className="button-group">
				<button onClick={() => dismissDialog()}>{gettext("Dismiss")}</button>
				<button onClick={() => applyACL()}>{gettext("Apply")}</button>
			</div>
		</dialog>
	);
});

export default PermissionDialog;
