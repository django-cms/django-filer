import React, {forwardRef, useImperativeHandle, useMemo, useRef} from 'react';
import DropDownMenu from '../common/DropDownMenu';
import SortingOptions from '../common/SortingOptions';
import FilterByLabel from '../common/FilterByLabel';
import VolumeControl from '../common/VolumeControl';
import SearchIcon from '../icons/search.svg';
import UploadIcon from '../icons/upload.svg';
import {Tooltip, TooltipContent, TooltipTrigger} from "../common/Tooltip";


const MenuBar = forwardRef((props: any, forwardedRef) => {
	const {openUploader, labels, refreshFilesList, setDirty, setSearchQuery, searchZone, setSearchZone, webAudio} = props;
	const ref = useRef(null);
	const searchRef = useRef(null);

	const rootNode = useMemo(() => {
		return ref.current?.getRootNode().querySelector('dialog');
	}, [ref.current]);

	useImperativeHandle(forwardedRef, () => ({
		clearSearch: () => searchRef.current.value = '',
	}));

	function handleSearch(event) {
		if (event.type === 'change' && searchRef.current.value.length === 0) {
			// clicked on the X button
			setSearchQuery('');
		} else if (event.type === 'keydown' && event.key === 'Enter') {
			// pressed Enter
			setSearchQuery(searchRef.current.value.length === 0 ? '' : searchRef.current.value);
		} else if (event.type === 'click' && searchRef.current.value.length > 2) {
			// clicked on the search button
			setSearchQuery(searchRef.current.value.length === 0 ? '' : searchRef.current.value);
		}
	}

	function changeSearchZone(value) {
		if (value !== searchZone) {
			setSearchZone(value);
			setDirty(true);
		}
	}

	function getItemProps(value: string) {
		return {
			role: 'option',
			'aria-selected': searchZone === value,
			onClick: () => changeSearchZone(value),
		};
	}

	return (
		<ul role="menubar" ref={ref}>
			<li role="menuitem" className="search-field">
				<input
					ref={searchRef}
					type="search"
					placeholder={gettext("Search for …")}
					onChange={handleSearch}
					onKeyDown={handleSearch}
				/>
				<div>
					<Tooltip>
						<TooltipTrigger>
							<span className="search-icon" onClick={handleSearch}><SearchIcon/></span>
						</TooltipTrigger>
						<TooltipContent root={rootNode}>{gettext("Search for file")}</TooltipContent>
					</Tooltip>
					<DropDownMenu
						role="menuitem"
						wrapperElement="span"
						className="search-zone with-caret"
						root={rootNode}
					>
						<li {...getItemProps('current')}>{gettext("From current folder")}</li>
						<li {...getItemProps('everywhere')}>{gettext("In all folders")}</li>
						<hr/>
						<li {...getItemProps('filename')}>{gettext("Filename only")}</li>
						<li {...getItemProps('content')}><s>{gettext("Also file content")}</s></li>
					</DropDownMenu>
				</div>
			</li>
			<VolumeControl webAudio={webAudio} />
			<SortingOptions refreshFilesList={refreshFilesList} root={rootNode} />
			{labels && <FilterByLabel refreshFilesList={refreshFilesList} labels={labels} root={rootNode} />}
			<Tooltip>
				<TooltipTrigger>
					<li role="menuitem" onClick={openUploader}>
						<UploadIcon/>
					</li>
				</TooltipTrigger>
				<TooltipContent root={rootNode}>{gettext("Upload file")}</TooltipContent>
			</Tooltip>
		</ul>
	);
});

export default MenuBar;
