import React from 'react';
import ArchiveIcon from 'icons/archive.svg';


export default function Audio(props) {
	console.log(props);

	function archiveSelectedIcons() {
		console.log("archiveSelectedIcons", props);
	}

	return (
		<li className={props.numSelectedInodes ? null : "disabled"} onClick={archiveSelectedIcons}>
			<ArchiveIcon/><span>{gettext("Create archive from selection")}</span>
		</li>
	);
}
