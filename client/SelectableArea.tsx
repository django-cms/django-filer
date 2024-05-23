import React, {useEffect, useRef, useState} from 'react';


function SelectionRectangle(props) {
	const {rect, discard} = props;
	const style = {
		top: `${rect.top}px`,
		left: `${rect.left}px`,
		right: `${rect.right}px`,
		bottom: `${rect.bottom}px`,
	};

	useEffect(() => {
		function handleMouseMove(event) {
			if (event.buttons === 0) {
				discard();
			}
		}

		function handleMouseOut(event) {
			if (event.target === window || event.target === document.documentElement || event.target === document.body) {
				discard();
			}
		}

		window.addEventListener('mousemove', handleMouseMove);
		window.addEventListener('mouseout', handleMouseOut);
		return () => {
			window.removeEventListener('mouseout', handleMouseOut);
		};
	});

	return (
		<div className="selection-rectangle" style={style}></div>
	);
}


export function SelectableArea(props) {
	const acceleration = 3;  // the lower, the faster
	const edgeSize = 15;  // the size of the area near the edge where scrolling starts
	const {columnRef} = props;
	const areaRef = useRef(null);
	const scrollableRef = useRef(null);
	const [activeRectangle, setActiveRectangle] = useState(null);
	const [timeoutHandler, setTimeoutHandler] = useState(null);

	const selectionStart = (event) => {
		// check if the click was on the image representation of an inode …
		for (let element = event.target; element; element = element.parentElement) {
			if (element instanceof HTMLImageElement) {
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
		console.log('selectionStart', rectangle);
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
			console.log('timeout', timeout);
			setTimeoutHandler(setTimeout(() => handleAutoScroll(event), acceleration * timeout));
		}
	}

	const selectionExtend = (event) => {
		if (timeoutHandler) {
			clearTimeout(timeoutHandler);
			setTimeoutHandler(null);
		}
		if (!activeRectangle)
			return;
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
		console.log('handleScroll', nextRectangle, scrollTop);
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

		if (!activeRectangle)
			return;
		const areaRect = areaRef.current.getBoundingClientRect();
		const xMin = areaRect.left + activeRectangle.left;
		const xMax = areaRect.right - activeRectangle.right;
		const yMin = areaRect.top + activeRectangle.top;
		const yMax = areaRect.bottom - activeRectangle.bottom;
		const overlappingInodeIds = [];
		for (let element of areaRef.current.querySelectorAll('.inode-list > li')) {
			const elemRect = element.getBoundingClientRect();
			if (overlaps(elemRect)) {
				overlappingInodeIds.push(element.dataset.id);
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
				onMouseDown={selectionStart}
				onMouseMove={selectionExtend}
				onMouseUp={selectionEnd}
			>
				{props.children}
				{activeRectangle && <SelectionRectangle rect={activeRectangle} discard={() => setActiveRectangle(null)} />}
			</div>
		</div>
	);
}
