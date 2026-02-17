import React, {
	forwardRef,
	useEffect,
	useImperativeHandle,
	useRef,
	useState,
} from 'react';
import {useCombobox} from 'downshift';
import Dialog from './Dialog';
import AddEntryIcon from '../icons/add-entry.svg';
import TrashIcon from '../icons/trash.svg';
import EveryoneIcon from '../icons/everyone.svg';
import GroupIcon from '../icons/group.svg';
import UserIcon from '../icons/user.svg';
import UserMeIcon from '../icons/user-me.svg';


enum Privilege {
	READ = 1,
	WRITE = 2,
	READ_WRITE = 3,
	FULL = 7,
}


type AccessControlEntry = {
	type: 'user'|'group'|'everyone',
	principal: number|null,
	name: string,
	privilege: Privilege,
	is_current_user: boolean,
};


const SelectPrincipal = forwardRef(function SelectPrincipal(props: any, forwardedRef) {
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
		<select onChange={event => setValue(parseInt(event.target.value))} value={value}>
			<option value={Privilege.READ}>{gettext("Read")}</option>
			<option value={Privilege.READ_WRITE}>{gettext("Read & Write")}</option>
			<option value={Privilege.WRITE}>{gettext("Write (Dropbox)")}</option>
			<option value={Privilege.FULL}>{gettext("Full Control")}</option>
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


const PermissionEditor = forwardRef(function PermissionEditor(props: any, forwardedRef) {
	const {settings} = props;
	const tbodyRef = useRef<HTMLTableSectionElement>(null);
	const selectPrincipalRef = useRef(null);
	const [toDefault, setToDefault] = useState(false);
	const [newPrincipal, setNewPrincipal] = useState(null);
	const [newPrivilege, setNewPrivilege] = useState(Privilege.READ);
	const [acl, setAcl] = useState<AccessControlEntry[]>([]);
	const [isOpen, setIsOpen] = useState(false);
	const [offset, setOffset] = useState({x: 0, y: 0});

	useImperativeHandle(forwardedRef, () => ({
		show: (toDefault) => fetchPermissions(toDefault).then(() => setIsOpen(true)),
		close: () => setIsOpen(false),
		handleDragStart: (event) => {},
		handleDragEnd: (event) => event.active.id === 'permission-dialog' && setOffset({x: event.delta.x + offset.x, y: event.delta.y + offset.y}),
	}));

	async function fetchPermissions(toDefault: boolean) {
		setToDefault(toDefault);
		const url = `${settings.base_url}${settings.is_folder ? settings.folder_id : settings.file_id}/permissions${toDefault ? '?default' : ''}`;
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
			setNewPrivilege(Privilege.READ);
			tbodyRef.current.scrollBy({top: 50, behavior: 'smooth'});
		}
	}

	function dismissDialog() {
		selectPrincipalRef.current.clearInput();
		setNewPrincipal(null);
		setNewPrivilege(Privilege.READ);
		setIsOpen(false);
		setOffset({x: 0, y: 0});
	}

	async function applyACL(recursive: boolean = false) {
		const accessControlList = newPrincipal ? [...acl, {...newPrincipal, privilege: newPrivilege}] : acl;
		const url = `${settings.base_url}${settings.is_folder ? settings.folder_id : settings.file_id}/permissions`;
		const response = await fetch(url, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': settings.csrf_token,
			},
			body: JSON.stringify({
				access_control_list: accessControlList,
				recursive: recursive,
				to_default: toDefault,
			}),
		});
		if (response.ok) {
			dismissDialog();
		} else {
			console.error(response);
		}
	}

	function updatePrivilege(index: number) {
		return (privilege: Privilege) => {
			const updatedAce = {...acl[index], privilege} as AccessControlEntry;
			setAcl(acl.toSpliced(index, 1, updatedAce));
		};
	}

	function renderLabel() {
		if (settings.is_folder) {
			if (toDefault)
				return gettext("Default Folder Permissions");
			return gettext("Folder and File Permissions");
		}
		return gettext("File Permissions");
	}

	const applyLabel = toDefault ? gettext("Apply as default") : gettext("Apply permissions");
	const recursiveLabel = gettext("Apply recursively");

	return (
		<Dialog id="permission-dialog" label={renderLabel()} isOpen={isOpen} offset={offset}>
			<table>
				<thead>
					<tr>
						<th>{gettext("Principal")}</th>
						<th>{gettext("Privilege")}</th>
						<th></th>
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
						</td>
						<td>
							<span onClick={() => setAcl(acl.toSpliced(index, 1))}>
								<TrashIcon />
							</span>
						</td>
					</tr>
				))}
				{acl.length === 0 && (
					<tr>
						<td colSpan={3}><em>{gettext("Permissions haven't been set.")}</em></td>
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
						</td>
						<td>
							<span onClick={() => addToACL()} aria-disabled={!newPrincipal} >
								<AddEntryIcon />
							</span>
						</td>
					</tr>
				</tfoot>
			</table>
			<div className="button-group">
				<button type="button" onClick={() => dismissDialog()}>{gettext("Dismiss")}</button>
				{settings.is_folder && <button type="button" onClick={() => applyACL(true)}>{recursiveLabel}</button>}
				<button type="button" onClick={() => applyACL()}>{applyLabel}</button>
			</div>
		</Dialog>
	);
});

export default PermissionEditor;
