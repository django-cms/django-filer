import React from 'react';
import DropDownMenu from './DropDownMenu';
import {useCookie} from './Storage';
import FilterIcon from '../icons/filter.svg';

export const useFilter = () => useCookie('django-finder-filter', []);


export default function FilterByTag(props: any) {
	const {tags, refreshFilesList} = props;
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
			className="filter-by-tag with-caret"
			tooltip={gettext("Filter by file tag")}
			root={props.root}
		>
			<li role="option"><span onClick={() => changeFilter(null)}>{gettext("Clear all")}</span></li>
			<hr/>
			{tags.map((tag, index) => (
			<li key={tag.value} role="option" aria-multiselectable={true}>
				<label htmlFor={`filter-${tag.value}`}>
					<input
						type="checkbox"
						id={`filter-${tag.value}`}
						name={tag.value}
						checked={filter.includes(tag.value)}
						onChange={() => changeFilter(tag.value)}
					/>
					<span className="tag-dot" style={{backgroundColor: tag.color}}></span>
					{tag.label}
				</label>
			</li>
			))}
		</DropDownMenu>
	);
}
