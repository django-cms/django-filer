import React, {useRef, useState} from 'react';
import {useSearchZone} from '../common/Storage';
import DropDownMenu from '../common/DropDownMenu';
import {Tooltip, TooltipTrigger, TooltipContent} from '../common/Tooltip';
import SearchIcon from '../icons/search.svg';


export function useSearchParam(key) : [string, (value: string) => any] {
	const params = new URLSearchParams(window.location.search);
	const [value, setValue] = useState(
		params.get(key) || ''
	);

	function setParam(value) {
		if (value) {
			const params = new URLSearchParams();
			params.set(key, value);
			const url = `${window.location.pathname}?${params.toString()}`;
			window.history.pushState(Object.fromEntries(params.entries()), undefined, url);
		} else {
			window.history.pushState({}, undefined, window.location.pathname);
		}
	}

	return [
		value,
		value => {
			setParam(value);
			setValue(value);
		},
	];
}


export default function SearchField(props) {
	const {columnRefs, setSearchResult, settings} = props;
	const searchRef = useRef(null);
	const [searchQuery, setSearchQuery] = useSearchParam('q');
	const [searchZone, setSearchZone] = useSearchZone('current');

	function handleSearch(event) {
		const performSearch = () => {
			setSearchQuery(searchRef.current.value);
			const current = columnRefs[settings.folder_id].current;
			current.setSearchQuery(searchRef.current.value);
			setSearchResult(true);
		};
		const resetSearch = () => {
			setSearchQuery('');
			Object.entries(columnRefs as React.MutableRefObject<any>).forEach(([folderId, columnRef]) => {
				columnRef.current?.setSearchQuery();
			});
			setSearchResult(false);
		};

		if (event.type === 'change' && searchRef.current.value.length === 0) {
			// clicked on the X button
			resetSearch();
		} else if (event.type === 'keydown' && event.key === 'Enter') {
			// pressed Enter
			searchRef.current.value.length === 0 ? resetSearch() : performSearch();
		} else if (event.type === 'click' && searchRef.current.value.length > 2) {
			// clicked on the search button
			performSearch();
		}
	}

	function changeSearchZone(value) {
		if (value !== searchZone) {
			setSearchZone(value);
			 Object.entries(columnRefs as React.MutableRefObject<any>).forEach(([folderId, columnRef]) => {
			 	columnRef.current?.fetchInodes();
			});
		}
	}

	function getItemProps(value: string) {
		return {
			role: 'option',
			'aria-selected': searchZone === value,
			onClick: () => changeSearchZone(value),
		};
	}

	return (<>
		<input
			ref={searchRef}
			type="search"
			defaultValue={searchQuery}
			placeholder={gettext("Search for …")}
			onChange={handleSearch}
			onKeyDown={handleSearch}
		/>
		<div>
			<Tooltip>
				<TooltipTrigger>
					<span className="search-icon" onClick={handleSearch}><SearchIcon/></span>
				</TooltipTrigger>
				<TooltipContent>{gettext("Search for file")}</TooltipContent>
			</Tooltip>
			<DropDownMenu
				wrapperElement="span"
				role="menuitem"
				className="search-zone with-caret"
			>
				<li {...getItemProps('current')}>{gettext("From current folder")}</li>
				<li {...getItemProps('everywhere')}>{gettext("In all folders")}</li>
				<hr/>
				<li {...getItemProps('filename')}>{gettext("Filename only")}</li>
				<li {...getItemProps('content')}><s>{gettext("Also file content")}</s></li>
			</DropDownMenu>
		</div>
	</>
);
}
