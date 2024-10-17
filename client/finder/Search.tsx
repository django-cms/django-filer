import React, {useEffect, useRef, useState} from 'react';
import {useCookie} from './Storage';
import DropDownMenu from './DropDownMenu';
import SearchIcon from 'icons/search.svg';

const useSearchRealm = initial => useCookie('django-finder-search-realm', initial);


function useSearchParam(key) : [string, (value: string) => any] {
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


export function SearchField(props) {
	const {columnRefs, setSearchResult, settings} = props;
	const searchRef = useRef(null);
	const [searchQuery, setSearchQuery] = useSearchParam('q');
	const [searchRealm, setSearchRealm] = useSearchRealm('current');

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

	function changeSearchRealm(value) {
		if (value !== searchRealm) {
			setSearchRealm(value);
			 Object.entries(columnRefs as React.MutableRefObject<any>).forEach(([folderId, columnRef]) => {
			 	columnRef.current?.fetchInodes();
			});
		}
	}

	function isActive(value) {
		return searchRealm === value ? 'active' : null;
	}

	return (<>
		<input ref={searchRef} type="search" defaultValue={searchQuery} placeholder={gettext("Search for …")} onChange={handleSearch} onKeyDown={handleSearch} />
		<div>
			<span className="search-icon" onClick={handleSearch}><SearchIcon/></span>
			<DropDownMenu wrapperElement="span" className="search-realm with-caret" tooltip={gettext("Restrict search")}>
				<li onClick={() => changeSearchRealm('current')}
					className={isActive('current')}>{gettext("From current folder")}
				</li>
				<li onClick={() => changeSearchRealm('everywhere')}
					className={isActive('everywhere')}>{gettext("In all folders")}
				</li>
				<li onClick={() => changeSearchRealm('filename')}
					className={isActive('filename')}>{gettext("Filename only")}
				</li>
				<li onClick={() => changeSearchRealm('content')}
					className={isActive('content')}><s>{gettext("Also file content")}</s>
				</li>
			</DropDownMenu>
		</div>
	</>
);
}