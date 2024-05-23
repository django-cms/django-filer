import React, {SyntheticEvent, useEffect, useRef, useState} from 'react';


function SelectRectangle(props) {
	const {rect, areaRef} = props;
	const inodeList = areaRef.current.querySelector('.inode-list');
	const offsetTop = rect.startScrollTop - inodeList.scrollTop;
	const top = Math.max(rect.top + offsetTop, -1);
	const bottom = Math.min(rect.bottom - offsetTop, areaRef.current.clientHeight);
	const style = {
		left: `${rect.left}px`,
		top: `${top}px`,
		right: `${rect.right}px`,
		bottom: `${rect.bottom}px`,
	};
	return (
		<div className="select-rectangle" style={style}></div>
	);
}


export function SelectableArea(props) {
	const {columnRef} = props;
	const areaRef = useRef(null);
	const [selectionActive, setSelectionActive] = useState(false);
	const [activeRect, setActiveRect] = useState(null);
	//const [scrollTop, setScrollTop] = useState(0);

	//useEffect(() => {
		//const inodeList = areaRef.current.querySelector('.inode-list');

		// function scrollArea(event: SyntheticEvent) {
		// 	if (selectionActive) {
		// 		console.log('scrollTop', inodeList.scrollTop);
		// 	}
		// }
		//
		// inodeList.addEventListener('scroll', scrollArea);
		//
		// return () => {
		// 	areaRef.current.removeEventListener('scroll', scrollArea);
		// };
	//}, [selectionActive]);

	const selectionStart = (event) => {
		// check if the click was on an inode …
		for (let element = event.target; element; element = element.parentElement) {
			if (element.hasAttribute('data-id')) {
				selectionDiscard();
				return;  // … and if so, let the inode handle the click
			}
			if (element === areaRef.current)
				break;
		}
		const areaRect = areaRef.current.getBoundingClientRect();

		console.log('areaRect', areaRect, 'event', event.clientX);
		const rectangle = {
			startX: event.clientX,
			startY: event.clientY,
			left: event.clientX - areaRect.left,
			top: event.clientY - areaRect.top,
			right: areaRect.right - event.clientX,
			bottom: areaRect.bottom - event.clientY,
			startScrollTop: areaRef.current.scrollTop,
			startScrollLeft: areaRef.current.scrollLeft,
		};
		setActiveRect(rectangle);
		console.log('selectionStart', rectangle);
		setSelectionActive(true);
		window.addEventListener('mouseup', selectionEnd, {once: true});
	}

	const selectionExtend = (event) => {
		if (!selectionActive)
			return;
		const areaRect = areaRef.current.getBoundingClientRect();
		const nextRect = {...activeRect};
		if (event.clientX < activeRect.startX) {
			nextRect.left = event.clientX - areaRect.left;
			nextRect.right = areaRect.right - activeRect.startX;
		} else {
			nextRect.left = activeRect.startX - areaRect.left;
			nextRect.right = areaRect.right - event.clientX;
		}
		if (event.clientY < activeRect.startY) {
			nextRect.top = event.clientY - areaRect.top;
			nextRect.bottom = areaRect.bottom - activeRect.startY;
			nextRect.invertedScroll = true;
		} else {
			nextRect.top = activeRect.startY - areaRect.top;
			nextRect.bottom = areaRect.bottom - event.clientY;
			nextRect.invertedScroll = false;
		}
		const scrollableElem = areaRef.current.parentElement;
		if (nextRect.top < scrollableElem.scrollTop) {
			console.log('scroll up', nextRect.top);
		}
		if (nextRect.bottom > scrollableElem.scrollTop + scrollableElem.clientHeight) {
			console.log('scroll down', nextRect.bottom);
		}
		setActiveRect(nextRect);
	};

	const selectionEnd = (event) => {
		function overlaps(rect: DOMRect) : boolean {
			if (rect.left < xMin && rect.right < xMin)
				return false;
			if (rect.left > xMax && rect.right > xMax)
				return false;
			if (rect.top < yMin && rect.bottom < yMin)
				return false;
			if (rect.top > yMax && rect.bottom > yMax)
				return false;
			return true;
		}

		if (!selectionActive)
			return;
		const areaRect = areaRef.current.getBoundingClientRect();
		const xMin = areaRect.left + activeRect.left;
		const xMax = areaRect.right - activeRect.right;
		const yMin = areaRect.top + activeRect.top; // - activeRect.scrollTop;
		const yMax = areaRect.bottom - activeRect.bottom;
		const overlappingInodeIds = [];
		for (let element of areaRef.current.querySelectorAll('.inode-list > li')) {
			const elemRect = element.getBoundingClientRect();
			if (overlaps(elemRect)) {
				overlappingInodeIds.push(element.dataset.id);
			}
		}
		const extend = event.shiftKey || event.ctrlKey || event.metaKey;
		columnRef.current.selectMultipleInodes(overlappingInodeIds, extend);
		selectionDiscard();
	};

	function selectionDiscard() {
		console.log('selectionDiscard');
		setActiveRect(null);
		setSelectionActive(false);
	}

	//console.log('SelectableArea', selectionActive, activeRect);

	return (
		<div
			ref={areaRef}
			className="selectable-area"
			onMouseDown={selectionStart}
			onMouseMove={selectionExtend}
			onMouseUp={selectionEnd}
			onDragStart={(event) => console.log(event)}
			onDrag={(event) => console.log(event)}
			onDragEnter={(event) => console.log(event)}
			onDragCapture={(event) => console.log(event)}
			onDragStartCapture={(event) => console.log(event)}
			onDragOver={(event) => console.log(event)}
			onDragOverCapture={(event) => console.log(event)}
		>
			{props.children}
			{selectionActive && <SelectRectangle rect={activeRect} areaRef={areaRef} />}
		</div>
	);
}
