import React from 'react';
import DropDownMenu from './DropDownMenu';
import {useCookie} from './Storage';
import FilterIcon from '../icons/filter.svg';

const useFilter = () => useCookie('django-finder-filter', []);


export default function FilterByLabel(props: any) {
	const {labels, refreshFilesList} = props;
	const [filter, setFilter] = useFilter();

	function changeFilter(value) {
		if (value === null) {
			setFilter([]);
		} else if (filter.includes(value)) {
			setFilter(filter.filter(v => v !== value));
		} else {
			setFilter([...filter, value]);
		}
		refreshFilesList();
	}

	return (
		<DropDownMenu
			icon={<FilterIcon/>}
			role="menuitem"
			aria-selected={filter.length}
			className="filter-by-label with-caret"
			tooltip={gettext("Filter by label")}
			root={props.root}
		>
			<li role="option"><span onClick={() => changeFilter(null)}>{gettext("Clear all")}</span></li>
			<hr/>{labels.map((label, index) => (
			<li key={label.value} role="option" aria-multiselectable={true}>
				<label htmlFor={`filter-${label.value}`}>
					<input
						type="checkbox"
						id={`filter-${label.value}`}
						name={label.value}
						checked={filter.includes(label.value)}
						onChange={() => changeFilter(label.value)}
					/>
					<span className="label-dot" style={{backgroundColor: label.color}}></span>
					{label.label}
				</label>
			</li>
			))}
		</DropDownMenu>
	);
}
