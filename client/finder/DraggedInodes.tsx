import React from 'react';
import {DraggableItem, ListItem} from './Item';


export default function DraggedInodes(props) {
	const {inodes, layout, style, zoom} = props;

	return (
		<ul className="inode-list" style={style}>{
			inodes.map(inode =>
			<DraggableItem key={inode.id} {...inode} isDragged={true} zoom={zoom}>
				<div className="inode">
					<ListItem {...inode} layout={layout} />
				</div>
			</DraggableItem>)
		}</ul>
	);
}
