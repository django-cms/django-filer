import React from 'react';


export default function FileTags(props) {
	return (
		<div>
			{props.children}
			<div className="file-tags">
				{props.tags?.map(tag => (
				<span key={tag.id} style={{backgroundColor: tag.color}} aria-labelledby={tag.label}></span>
				))}
			</div>
		</div>
	);
}
