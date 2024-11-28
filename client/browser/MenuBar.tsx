import React, {useRef} from 'react';
import DropDownMenu from '../common/DropDownMenu';
import {useSearchRealm} from '../common/Storage';
import SortingOptions from '../common/SortingOptions';
import FilterByLabel from '../common/FilterByLabel';
import SearchIcon from '../icons/search.svg';
import UploadIcon from '../icons/upload.svg';


export default function MenuBar(props) {
	const {refreshFilesList, setSearchQuery, openUploader, labels, searchQuery} = props;
	const searchRef = useRef(null);
	const [searchRealm, setSearchRealm] = useSearchRealm('current');

	async function handleSearch(event) {
		const performSearch = async () => {
			const searchQuery = searchRef.current.value || '';
			await setSearchQuery(searchQuery);
		};
		const resetSearch = () => {
			setSearchQuery('');
		};

		if (event.type === 'change' && searchRef.current.value.length === 0) {
			// clicked on the X button
			resetSearch();
		} else if (event.type === 'keydown' && event.key === 'Enter') {
			// pressed Enter
			searchRef.current.value.length === 0 ? resetSearch() : await performSearch();
		} else if (event.type === 'click' && searchRef.current.value.length > 2) {
			// clicked on the search button
			await performSearch();
		}
	}

	function changeSearchRealm(value) {
		if (value !== searchRealm) {
			setSearchRealm(value);
		}
	}

	function getItemProps(value: string) {
		return {
			role: 'option',
			'aria-selected': searchRealm === value,
			onClick: () => setSearchRealm(value),
		};
	}

	return (
		<ul role="menubar">
			<li role="menuitem" className="search-field">
				<input
					ref={searchRef}
					defaultValue={searchQuery}
					type="search"
					placeholder={gettext("Search for …")}
					onChange={handleSearch}
					onKeyDown={handleSearch}
				/>
				<div>
					<span className="search-icon" onClick={handleSearch}><SearchIcon/></span>
					<DropDownMenu
						role="menuitem"
						wrapperElement="span"
						className="search-realm with-caret"
						tooltip={gettext("Restrict search")}
					>
						<li {...getItemProps('current')}>{gettext("From current folder")}</li>
						<li {...getItemProps('everywhere')}>{gettext("In all folders")}</li>
						<hr/>
						<li {...getItemProps('filename')}>{gettext("Filename only")}</li>
						<li {...getItemProps('content')}><s>{gettext("Also file content")}</s></li>
					</DropDownMenu>
				</div>
			</li>
			<SortingOptions refreshFilesList={refreshFilesList}/>
			{labels && <FilterByLabel refreshFilesList={refreshFilesList} labels={labels} />}
			<li role="menuitem" onClick={openUploader} data-tooltip-id="django-finder-tooltip"
				data-tooltip-content={gettext("Upload file")}>
				<UploadIcon/>
			</li>
		</ul>
	);
}
