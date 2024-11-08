import React from 'react';
import DropDownMenu from '../common/DropDownMenu';
import {useCookie} from '../common/Storage';
import SortingIcon from '../icons/sorting.svg';
import SortDescIcon from '../icons/sort-desc.svg';
import SortAscIcon from '../icons/sort-asc.svg';


const useSorting = () => useCookie('django-finder-sorting', '');


export default function SortingOptions(props: any) {
	const {refreshFilesList} = props;
	const [sorting, setSorting] = useSorting();

	function changeSorting(value) {
		if (value !== sorting) {
			setSorting(value);
			refreshFilesList();
		}
	}

	function getItemProps(value: string) {
		return {
			role: 'option',
			'aria-selected': sorting === value,
			onClick: () => changeSorting(value),
		};
	}

	return (
		<DropDownMenu
			icon={<SortingIcon/>}
			role="menuitem"
			className="sorting-options with-caret"
			tooltip={gettext("Change sorting order")}
		>
			<li {...getItemProps('')}>
				<span>{gettext("Unsorted")}</span>
			</li>
			<li {...getItemProps('name_asc')}>
				<SortDescIcon/><span>{gettext("Name")}</span>
			</li>
			<li {...getItemProps('name_desc')}>
				<SortAscIcon /><span>{gettext("Name")}</span>
			</li>
			<li {...getItemProps('date_asc')}>
				<SortDescIcon /><span>{gettext("Date")}</span>
			</li>
			<li {...getItemProps('date_desc')}>
				<SortAscIcon /><span>{gettext("Date")}</span>
			</li>
			<li {...getItemProps('size_asc')}>
				<SortDescIcon /><span>{gettext("Size")}</span>
			</li>
			<li {...getItemProps('size_desc')}>
				<SortAscIcon /><span>{gettext("Size")}</span>
			</li>
			<li {...getItemProps('type_asc')}>
				<SortDescIcon /><span>{gettext("Type")}</span>
			</li>
			<li {...getItemProps('type_desc')}>
				<SortAscIcon /><span>{gettext("Type")}</span>
			</li>
		</DropDownMenu>
	);
}
