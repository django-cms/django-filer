import React from 'react';
import DropDownMenu from './DropDownMenu';
import {useCookie} from './Storage';
import TriStateCheckbox from './TriStateCheckbox';
import FilterIcon from '../icons/filter.svg';

export const useFilter = () => useCookie('django-finder-filter', {});


export default function FilterByTag(props: any) {
	const {tags, refreshFilesList} = props;
	const [filtered, setFiltered] = useFilter();

	function changeFiltered(name, value) {
		if (typeof value === 'boolean') {
			setFiltered({...filtered, [name]: value});
		} else {
			setFiltered(Object.fromEntries(Object.entries(filtered).filter(([key]) => key != name)));
		}
		refreshFilesList();
	}

	function clearFiltered() {
		setFiltered({});
		refreshFilesList();
	}

	return (
		<DropDownMenu
			icon={<FilterIcon/>}
			role="menuitem"
			ariaSelected={Object.keys(filtered).length ? 'true' : 'false'}
			className="filter-by-tag with-caret"
			tooltip={gettext("Filter by file tag")}
			root={props.root}
		>
			<li role="option"><span onClick={clearFiltered}>{gettext("Clear all")}</span></li>
			<hr/>
			{tags.map((tag, index) => (
			<li key={tag.value} role="option" aria-multiselectable={true}>
				<label htmlFor={`filter-${tag.value}`}>
					<TriStateCheckbox
						id={`filter-${tag.value}`}
						checked={filtered[tag.value]}
						onChange={(state) => changeFiltered(tag.value, state)}
					/>
					<span className="tag-dot" style={{backgroundColor: tag.color}}></span>
					{tag.label}
				</label>
			</li>
			))}
		</DropDownMenu>
	);
}
