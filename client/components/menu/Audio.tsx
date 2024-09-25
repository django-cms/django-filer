import React, {useEffect, useState} from 'react';
import ArchiveIcon from 'icons/archive.svg';


export default function Audio(props) {
	console.log(props);

	function archiveSelectedIcons() {
	}

	return (
		<li onClick={() => archiveSelectedIcons()} className={props.numSelectedInodes ? null : "disabled"} data-tooltip-id="django-finder-tooltip" data-tooltip-content={gettext("Create archive from selection")}>
			<ArchiveIcon />
		</li>
	);
}
