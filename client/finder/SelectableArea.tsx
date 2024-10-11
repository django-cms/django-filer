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


export default function SelectableArea(props) {
	const edgeSize = 16;  // the size of the area near the upper and lower edge where scrolling starts
	const acceleration = 40;  // accelerate scrolling the nearer the cursor reaches one of the edges
	const {deselectAll, columnRef, dragging} = props;
	const areaRef = useRef(null);
	const scrollableRef = useRef(null);
	const [activeRectangle, setActiveRectangle] = useState(null);
	const [timeoutHandler, setTimeoutHandler] = useState(null);

	useEffect(() => {
		setActiveRectangle(null);
		if (dragging)
			return;

		areaRef.current.addEventListener('mousedown', selectionStart);
		return () => {
			areaRef.current.removeEventListener('mousedown', selectionStart);
		};
	}, [dragging]);

	useEffect(() => {
		if (activeRectangle === null)
			return;

		const areaRect = areaRef.current.getBoundingClientRect();

		const handleMouseOut = (event) => {
			if (event.clientX < areaRect.x - edgeSize
			 || event.clientX > areaRect.x + areaRect.width
			 || event.clientY < areaRect.y - edgeSize
			 || event.clientY > areaRect.y + areaRect.height) {
				setActiveRectangle(null);
			}
		};

		const handleEscape = (event) => {
			if (event.key === 'Escape') {
				setActiveRectangle(null);
			}
		};

		areaRef.current.addEventListener('mousemove', selectionExtend);
		window.addEventListener('mouseout', handleMouseOut);
		window.addEventListener('keydown', handleEscape);
		return () => {
			areaRef.current.removeEventListener('mousemove', selectionExtend);
			window.removeEventListener('mouseout', handleMouseOut);
			window.removeEventListener('keydown', handleEscape);
		};
	}, [activeRectangle !== null]);

	useEffect(() => {
		if (activeRectangle === null)
			return;

		areaRef.current.addEventListener('mouseup', selectionEnd);
		return () => {
			areaRef.current.removeEventListener('mouseup', selectionEnd);
		};
	}, [activeRectangle]);

	const selectionStart = (event) => {
		// check if the click was on the image representation of an inode …
		for (let element = event.target; element; element = element.parentElement) {
			if (element instanceof HTMLElement && element.classList.contains('figure')) {
				setActiveRectangle(null);
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
		setActiveRectangle(rectangle);
		if (!(event.shiftKey || event.ctrlKey || event.metaKey)) {
			deselectAll();
		}
	}

	function handleAutoScroll(event) {
		// scroll the area if the mouse is near the edge
		const scrollableRect = scrollableRef.current.getBoundingClientRect();
		let timeout = edgeSize;
		if (event.clientY < scrollableRect.top + edgeSize && scrollableRef.current.scrollTop > 0) {
			timeout = event.clientY - scrollableRect.top;
			scrollableRef.current.scrollTop--;
		} else if (event.clientY > scrollableRect.bottom - edgeSize && scrollableRef.current.scrollTop < areaRef.current.clientHeight - scrollableRect.height) {
			timeout = scrollableRect.bottom - event.clientY;
			scrollableRef.current.scrollTop++;
		}
		if (timeout < edgeSize) {
			setTimeoutHandler(setTimeout(() => handleAutoScroll(event), 100 * timeout / acceleration));
		}
	}

	const selectionExtend = (event) => {
		if (timeoutHandler) {
			clearTimeout(timeoutHandler);
			setTimeoutHandler(null);
		}
		handleAutoScroll(event);

		const scrollTop = scrollableRef.current.scrollTop - activeRectangle.scrollTop;
		const areaRect = areaRef.current.getBoundingClientRect();
		const nextRectangle = {...activeRectangle, lastX: event.clientX, lastY: event.clientY};
		if (event.clientX < activeRectangle.startX) {
			nextRectangle.left = event.clientX - areaRect.left;
		} else {
			nextRectangle.right = areaRect.right - event.clientX;
		}
		if (event.clientY < activeRectangle.startY - scrollTop) {
			nextRectangle.top = event.clientY - areaRect.top;
		} else {
			nextRectangle.bottom = areaRect.bottom - event.clientY;
		}
		setActiveRectangle(nextRectangle);
	};

	const handleScroll = () => {
		if (!activeRectangle)
			return;
		const scrollTop = scrollableRef.current.scrollTop - activeRectangle.scrollTop;
		const areaRect = areaRef.current.getBoundingClientRect();
		const nextRectangle = {...activeRectangle};
		if (activeRectangle.lastY < activeRectangle.startY - scrollTop) {
			nextRectangle.top = activeRectangle.lastY - areaRect.top;
		} else {
			nextRectangle.bottom = areaRect.bottom - activeRectangle.lastY;
		}
		setActiveRectangle(nextRectangle);
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

		const areaRect = areaRef.current.getBoundingClientRect();
		const xMin = areaRect.left + activeRectangle.left;
		const xMax = areaRect.right - activeRectangle.right;
		const yMin = areaRect.top + activeRectangle.top;
		const yMax = areaRect.bottom - activeRectangle.bottom;
		const overlappingInodeIds = [];
		if (xMin !== xMax || yMin !== yMax) {
			for (let element of areaRef.current.querySelectorAll('.inode-list > li')) {
				const elemRect = element.getBoundingClientRect();
				if (overlaps(elemRect)) {
					overlappingInodeIds.push(element.dataset.id);
				}
			}
		}
		const extend = event.shiftKey || event.ctrlKey || event.metaKey;
		columnRef.current.selectMultipleInodes(overlappingInodeIds, extend);
		setActiveRectangle(null);
	};

	return (
		<div className="scrollable-area" onScroll={handleScroll} ref={scrollableRef}>
			<div
				ref={areaRef}
				className="selectable-area"
			>
				{props.children}
				{activeRectangle && <SelectionRectangle rect={activeRectangle} />}
			</div>
		</div>
	);
}
