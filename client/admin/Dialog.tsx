import React, {
	useCallback,
	useEffect,
	useRef,
} from 'react';
import {useDraggable} from '@dnd-kit/core';


export default function Dialog (props: any){
	const {children, id, label, isOpen, offset} = props;
	const dialogRef = useRef<HTMLDialogElement>(null);
	const {
		attributes,
		listeners,
		setNodeRef,
		transform,
	} = useDraggable({
		id: id,
	});

	// combined ref: assign dialog element to both dialogRef and dnd-kit setNodeRef
	const combinedRef = useCallback((element: HTMLDialogElement) => {
		dialogRef.current = element;
		setNodeRef(element);
	}, [setNodeRef]);

	useEffect(() => {
		if (dialogRef.current?.open && !isOpen) {
			dialogRef.current.close();
		} else if (!dialogRef.current?.open && isOpen) {
			dialogRef.current.show();
		}
	}, [isOpen]);

	const dialogStyle : React.CSSProperties = {
		transform: transform
			? `translate(${transform.x + offset.x}px, ${transform.y + offset.y}px)`
			: `translate(${offset.x}px, ${offset.y}px)`,
	};

	return (
		<dialog ref={combinedRef} style={dialogStyle}>
			<h3 {...listeners} {...attributes}>{label}</h3>
			{children}
		</dialog>
	);
}
