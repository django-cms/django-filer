import React from 'react';
import DropDownMenu from './DropDownMenu';
import {useCookie} from './Storage';
import FilterIcon from '../icons/filter.svg';

export const useFilter = () => useCookie('django-finder-filter', []);
// a comma separated string: the array converter of `useCookie` only keeps numbers
export const useProvenanceFilter = () => useCookie('django-finder-provenance', '');

const provenanceOptions = [
	{value: 'ai', label: gettext("Created or edited using generative AI")},
	{value: 'c2pa', label: gettext("Uploaded with Content Credentials")},
];


export default function FilterByTag(props: any) {
	const {tags, refreshFilesList} = props;
	const [filter, setFilter] = useFilter();
	const [provenanceFilter, setProvenanceFilter] = useProvenanceFilter();
	const provenance = provenanceFilter ? provenanceFilter.split(',') : [];

	function changeProvenanceFilter(value) {
		if (provenance.includes(value)) {
			setProvenanceFilter(provenance.filter(v => v !== value).join(','));
		} else {
			setProvenanceFilter([...provenance, value].join(','));
		}
		refreshFilesList();
	}

	function changeFilter(value) {
		if (value === null) {
			setFilter([]);
			setProvenanceFilter('');
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
			aria-selected={filter.length + provenance.length}
			className="filter-by-tag with-caret"
			tooltip={gettext("Filter by file tag or image provenance")}
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
			{tags.length > 0 && <hr/>}
			{provenanceOptions.map(option => (
			<li key={option.value} role="option" aria-multiselectable={true}>
				<label htmlFor={`filter-provenance-${option.value}`}>
					<input
						type="checkbox"
						id={`filter-provenance-${option.value}`}
						name={option.value}
						checked={provenance.includes(option.value)}
						onChange={() => changeProvenanceFilter(option.value)}
					/>
					{option.label}
				</label>
			</li>
			))}
		</DropDownMenu>
	);
}
