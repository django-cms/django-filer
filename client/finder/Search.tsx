import React, {useContext, useRef, useState} from 'react';
import {FinderSettings} from './FinderSettings';
import {useCookie} from './Storage';
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
	const settings = useContext(FinderSettings);
	const {columnRefs, setSearchResult} = props;
	const searchRef = useRef(null);
	const searchRealmRef = useRef(null);
	const [searchQuery, setSearchQuery] = useSearchParam('q');
	const [searchRealm, setSearchRealm] = useSearchRealm('current');

	window.addEventListener('click', event => {
		if (!searchRealmRef.current?.parentElement?.contains(event.target)) {
			searchRealmRef.current.setAttribute('aria-expanded', 'false');
		}
	});

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

	function renderSearchRealmOptions() {
		const isActive = (value) => searchRealm === value ? 'active' : null;

		return (
			<ul ref={searchRealmRef} role="combobox" aria-expanded="false">
				<li onClick={() => changeSearchRealm('current')} className={isActive('current')}>{gettext("From current folder")}</li>
				<li onClick={() => changeSearchRealm('everywhere')} className={isActive('everywhere')}>{gettext("In all folders")}</li>
				<li onClick={() => changeSearchRealm('filename')} className={isActive('filename')}>{gettext("Filename only")}</li>
				<li onClick={() => changeSearchRealm('content')} className={isActive('content')}>{gettext("Also file content")}</li>
			</ul>
		)
	}

	return (<>
		<input ref={searchRef} type="search" defaultValue={searchQuery} placeholder={gettext("Search for …")} onChange={handleSearch} onKeyDown={handleSearch} />
		<div>
			<span className="search-icon" onClick={handleSearch}><SearchIcon /></span>
			<span className="search-realm" onClick={() => searchRealmRef.current.setAttribute('aria-expanded', searchRealmRef.current.ariaExpanded === 'true' ? 'false': 'true')} aria-haspopup="true" data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Restrict search")}>
				{renderSearchRealmOptions()}
			</span>
		</div>
	</>);
}
