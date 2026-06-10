import React from 'react';
import {DraggableItem, ListItem} from './Item';


export default function DraggedInodes(props) {
	const {inodes, layout} = props;

	return (
		<ul className="inode-list">{
			inodes.map(inode =>
			<DraggableItem key={inode.id} {...inode} isDragged={true}>
				<div className="inode">
					<ListItem {...inode} layout={layout} />
				</div>
			</DraggableItem>)
		}</ul>
	);
}
