import React, {createRef} from 'react';
import ArchiveIcon from 'icons/archive.svg';
import {bool} from "prop-types";


export default function Archive(props) {
	const {settings, columnRefs} = props;

	async function archiveSelectedInodes() {
		const archiveName = window.prompt(gettext("Enter name for the archive file"));
		const [folderId, columnRef] = Object.entries(columnRefs as React.MutableRefObject<any>).find(
			([_, colRef]) => colRef.current?.inodes.find(inode => inode.selected)
		);
		const selectedInodeIds = columnRef.current?.inodes.filter(inode => inode.selected).map(inode => inode.id) ?? [];
		if (selectedInodeIds.length > 0) {
			const fetchUrl = `${settings.base_url}${folderId}/archive`;
			const response = await fetch(fetchUrl, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': settings.csrf_token,
				},
				body: JSON.stringify({
					archive_name: archiveName,
					inode_ids: selectedInodeIds,
				}),
			});
			if (response.ok) {
				const body = await response.json();
				const current = columnRef.current;
				current.setInodes([...current.inodes, {...body.new_file, elementRef: createRef()}]);
			} else if ([409, 415].includes(response.status)) {
				window.alert(await response.text());
			} else {
				console.error(response);
			}
		}
	}

	return (
		<li className={props.numSelectedInodes ? null : "disabled"} onClick={archiveSelectedInodes}>
			<ArchiveIcon/><span>{gettext("Create archive from selection")}</span>
		</li>
	);
}
