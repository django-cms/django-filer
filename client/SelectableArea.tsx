import React, {useEffect, useRef, useState} from 'react';


function SelectionRectangle(props) {
	const {rect} = props;
	const style = {
		top: `${rect.top}px`,
		left: `${rect.left}px`,
		right: `${rect.right}px`,
		bottom: `${rect.bottom}px`,
	};

	return (
		<div className="selection-rectangle" style={style}></div>
	);
}


export function SelectableArea(props) {
	const {columnRef} = props;
	const areaRef = useRef(null);
	const scrollableRef = useRef(null);
	const [selectionActive, setSelectionActive] = useState(false);
	const [activeRect, setActiveRect] = useState(null);

	useEffect(() => {
		function handleMouseOut(event) {
			if (event.target === window || event.target === document.documentElement || event.target === document.body) {
				selectionDiscard();
			}
		}

		window.addEventListener('mouseout', handleMouseOut);
		return () => {
			window.removeEventListener('mouseout', handleMouseOut);
		};
	});

	const selectionStart = (event) => {
		// check if the click was on the image representation of an inode …
		for (let element = event.target; element; element = element.parentElement) {
			if (element instanceof HTMLImageElement) {
				selectionDiscard();
				return;  // … and if so, let the inode handle the click
			}
			if (element === areaRef.current)
				break;
		}

		const areaRect = areaRef.current.getBoundingClientRect();
		const rectangle = {
			startX: event.clientX,
			startY: event.clientY,
			lastX: event.clientX,
			lastY: event.clientY,
			scrollTop: scrollableRef.current.scrollTop,
			top: event.clientY - areaRect.top,
			left: event.clientX - areaRect.left,
			right: areaRect.right - event.clientX,
			bottom: areaRect.bottom - event.clientY,
		};
		setActiveRect(rectangle);
		console.log('selectionStart', rectangle);
		setSelectionActive(true);
	}

	function handleAutoScroll(event) {
		// scroll the area if the mouse is near the edge
		const edgeSize = 10;
		const scrollableRect = scrollableRef.current.getBoundingClientRect();
		let timeout = 0;
		if (event.clientY < scrollableRect.top + edgeSize && scrollableRef.current.scrollTop > 0) {
			timeout = event.clientY - scrollableRect.top;
			scrollableRef.current.scrollTop--;
		} else if (event.clientY > scrollableRect.bottom - edgeSize && scrollableRef.current.scrollTop < areaRef.current.clientHeight - scrollableRect.height) {
			//console.log('scroll down', scrollableRef.current.scrollTop, areaRef.current.clientHeight - scrollableRect.height)
			timeout = scrollableRect.bottom - event.clientY;
			scrollableRef.current.scrollTop++;
		}
		if (timeout) {
			console.log('timeout', timeout);
			//setTimeout(() => handleAutoScroll(event), 25);
		}
	}

	const selectionExtend = (event) => {
		if (!selectionActive)
			return;
		const scrollTop = scrollableRef.current.scrollTop - activeRect.scrollTop;
		const areaRect = areaRef.current.getBoundingClientRect();

		handleAutoScroll(event);
		const nextRect = {...activeRect, lastX: event.clientX, lastY: event.clientY};
		if (event.clientX < activeRect.startX) {
			nextRect.left = event.clientX - areaRect.left;
		} else {
			nextRect.right = areaRect.right - event.clientX;
		}
		if (event.clientY < activeRect.startY - scrollTop) {
			nextRect.top = event.clientY - areaRect.top;
		} else {
			nextRect.bottom = areaRect.bottom - event.clientY;
		}
		setActiveRect(nextRect);
	};

	const handleScroll = () => {
		if (!selectionActive)
			return;
		const scrollTop = scrollableRef.current.scrollTop - activeRect.scrollTop;
		const areaRect = areaRef.current.getBoundingClientRect();
		const nextRect = {...activeRect};
		if (activeRect.lastY < activeRect.startY - scrollTop) {
			nextRect.top = activeRect.lastY - areaRect.top;
		} else {
			nextRect.bottom = areaRect.bottom - activeRect.lastY;
		}
		console.log('handleScroll', nextRect, scrollTop);
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

	return (
		<div className="scrollable-area" onScroll={handleScroll} ref={scrollableRef}>
			<div
				ref={areaRef}
				className="selectable-area"
				onMouseDown={selectionStart}
				onMouseMove={selectionExtend}
				onMouseUp={selectionEnd}
			>
				{props.children}
				{selectionActive && <SelectionRectangle rect={activeRect} />}
			</div>
		</div>
	);
}
