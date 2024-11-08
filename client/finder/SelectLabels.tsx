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
	})

	function removeLabel(event: React.MouseEvent, label: Label) {
		event.stopPropagation();
		const option = Array.from(original.options).find(o => o.value == label.value);
		if (option) {
			option.selected = false;
		}
		removeSelectedItem(label);
	}

	return (
		<div className="select-labels-field">
			{selectedItems.map((selectedItem, index) => {
				return (
					<div className="select-labels-value"
						 key={`selected-item-${index}`}
						 {...getSelectedItemProps({selectedItem, index})}
					>
						<span style={{backgroundColor: selectedItem.color}} className="select-labels-dot"/>
						{selectedItem.label}
						<span
							className="deselect-label"
							onClick={(event: React.MouseEvent) => removeLabel(event, selectedItem)}
						>&times;</span>
					</div>
				)
			})}
			<div className="caret" {...getToggleButtonProps(getDropdownProps({preventKeyAction: isOpen}))}></div>
			<ul {...getMenuProps()}>{
				isOpen && items.map((item, index) => (
				<li key={`item-${index}`} {...getItemProps({item, index})}>
					<span style={{backgroundColor: item.color}} className="select-labels-dot"/>
					{item.label}
				</li>
				))
			}</ul>
		</div>
	)
}


// function SelectLabels(props) {
// 	const {settings} = props;
// 	const LabelOption = ({innerProps, data}) => (
// 		<div {...innerProps} className="select-labels-option">
// 			<span style={{backgroundColor: data.color}} className="select-labels-dot" />
// 			{data.label}
// 		</div>
// 	);
// 	const MultiValueLabel = ({data}) => (
// 		<div>
// 			<span style={{backgroundColor: data.color}} className="select-labels-dot" />
// 			{data.label}
// 		</div>
// 	);
// 	const MultiValueContainer = ({children}) => (
// 		<div className="select-labels-value">
// 			{children}
// 		</div>
// 	);
// 	const defaultValues = useMemo(() => {
// 		const defaultValues = [];
// 		if (settings.labels) {
// 			const labelsElement = document.getElementById('id_labels') ?? settings.mainContent.querySelector('#id_labels');
// 			if (labelsElement instanceof HTMLSelectElement) {
// 				// extract selected values from the original <select multiple name="labels"> element
// 				for (const option of labelsElement.selectedOptions) {
// 					const found = settings.labels.find(label => label.value == option.value);
// 					if (found) {
// 						defaultValues.push(found);
// 					}
// 				}
// 			}
// 		}
// 		return defaultValues;
// 	}, []);
//
// 	useEffect(() => {
// 		if (settings.labels) {
// 			// remove the original <select multiple name="labels"> element together with its <label> element
// 			let labelsElement = document.getElementById('id_labels') ?? settings.mainContent.querySelector('#id_labels');
// 			while (labelsElement) {
// 				if (labelsElement.classList.contains('form-row')) {
// 					labelsElement.remove();
// 					break;
// 				}
// 				labelsElement = labelsElement.parentElement;
// 			}
// 		}
// 	}, []);
//
// 	if (settings.labels) return (
// 		<div className="aligned">
// 			<div className="form-row" style={{overflow: "visible"}}>
// 				<div className="flex-container">
// 					<label>{gettext("Labels")}:</label>
// 					<Select
// 						components={{Option: LabelOption, MultiValueLabel, MultiValueContainer}}
// 						defaultValue={defaultValues}
// 						options={settings.labels}
// 						name="labels"
// 						placeholder={gettext("Choose Labels")}
// 						className="select-labels-container"
// 						classNamePrefix="select-labels"
// 						isMulti={true}
// 					/>
// 				</div>
// 			</div>
// 		</div>
// 	);
// }
