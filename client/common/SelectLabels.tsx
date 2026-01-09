import React from 'react';
import {useMultipleSelection, useSelect} from 'downshift';


type Label = {
	value: string,
	label: string,
	color: string,
};


export default function SelectLabels(props) {
	const {labels, initial, original} = props as { labels: Label[]; initial: Label[]; original: HTMLSelectElement };
	const {
		getSelectedItemProps,
		getDropdownProps,
		addSelectedItem,
		removeSelectedItem,
		selectedItems,
	} = useMultipleSelection({initialSelectedItems: initial});
	const items = labels.filter(label => !selectedItems.find((selectedItem: any) => selectedItem.value === label.value));
	const {
		isOpen,
		getToggleButtonProps,
		getMenuProps,
		getItemProps,
	} = useSelect({
		selectedItem: null,
		items,
		stateReducer: (state, actionAndChanges) => {
			const {changes, type} = actionAndChanges;
			switch (type) {
				case useSelect.stateChangeTypes.ToggleButtonKeyDownEnter:
				case useSelect.stateChangeTypes.ToggleButtonKeyDownSpaceButton:
				case useSelect.stateChangeTypes.ItemClick:
					return {
						...changes,
						isOpen: true,  // keep the menu open after selection.
					}
				default:
					return changes;
			}
		},
		onStateChange: ({type, selectedItem: newSelectedItem}) => {
			switch (type) {
				case useSelect.stateChangeTypes.ToggleButtonKeyDownEnter:
				case useSelect.stateChangeTypes.ToggleButtonKeyDownSpaceButton:
				case useSelect.stateChangeTypes.ItemClick:
				case useSelect.stateChangeTypes.ToggleButtonBlur:
					if (newSelectedItem) {
						const option = Array.from(original.options).find(o => o.value == newSelectedItem.value);
						if (option) {
							option.selected = true;
						}
						addSelectedItem(newSelectedItem);
					}
					break;
				default:
					break;
			}
		},
	});

	function removeLabel(event: React.MouseEvent, label: Label) {
		event.stopPropagation();
		const option = Array.from(original.options).find(o => o.value == label.value);
		if (option) {
			option.selected = false;
		}
		removeSelectedItem(label);
	}

	return (
		<div className="select-field">
			{selectedItems.map((selectedItem, index) => {
				return (
					<div className="select-value"
						 key={`selected-item-${index}`}
						 {...getSelectedItemProps({selectedItem, index})}
					>
						<span style={{backgroundColor: selectedItem.color}} className="select-dot"/>
						{selectedItem.label}
						<span
							className="deselect"
							onClick={(event: React.MouseEvent) => removeLabel(event, selectedItem)}
						>&times;</span>
					</div>
				)
			})}
			<div className="toggle-dropdown" {...getToggleButtonProps(getDropdownProps({preventKeyAction: isOpen}))}></div>
			<ul {...getMenuProps()}>{
				isOpen && items.map((item, index) => (
				<li key={`item-${index}`} {...getItemProps({item, index})}>
					<span style={{backgroundColor: item.color}} className="select-dot"/>
					{item.label}
				</li>
				))
			}</ul>
		</div>
	)
}
