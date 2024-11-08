import React from 'react';


export default function FigureLabels(props) {
	return (
		<div>
			{props.children}
			<div className="figure-labels">
				{props.labels?.map(label => (
				<span key={label.id} style={{backgroundColor: label.color}}>{label.label}</span>
				))}
			</div>
		</div>
	);
}
