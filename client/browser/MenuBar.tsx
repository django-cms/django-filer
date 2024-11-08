import React, {useRef} from 'react';
import DropDownMenu from '../common/DropDownMenu';
import {useSearchRealm} from '../common/Storage';
import SortingOptions from '../common/SortingOptions';
import FilterByLabel from '../common/FilterByLabel';
import SearchIcon from '../icons/search.svg';
import UploadIcon from '../icons/upload.svg';


export default function MenuBar(props) {
	const {lastFolderId, fetchFiles, openUploader, labels} = props;
	const searchRef = useRef(null);
	const [searchRealm, setSearchRealm] = useSearchRealm('current');

	function handleSearch(event) {
		const performSearch = () => {
			const searchQuery = searchRef.current.value || '';
			fetchFiles(lastFolderId, searchQuery);
		};
		const resetSearch = () => {
			fetchFiles(lastFolderId);
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
		}
	}

	function getItemProps(value: string) {
		return {
			role: 'option',
			'aria-selected': searchRealm === value,
			onClick: () => setSearchRealm(value),
		};
	}

	console.log('Menu', lastFolderId);

	return (
		<ul role="menubar">
			<li role="menuitem" className="search-field">
				<input
					ref={searchRef}
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
			<SortingOptions refreshFilesList={() => fetchFiles(lastFolderId)}/>
			{labels && <FilterByLabel refreshFilesList={() => fetchFiles(lastFolderId)} labels={labels} />}
			<li role="menuitem" onClick={openUploader} data-tooltip-id="django-finder-tooltip"
				data-tooltip-content={gettext("Upload file")}>
				<UploadIcon/>
			</li>
		</ul>
	);
}
