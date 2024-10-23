import React, {useEffect, useRef} from 'react';


export default function DropDownMenu(props) {
	const ref = useRef(null);
	const Wrapper = props.wrapperElement ?? 'li';

	useEffect(() => {
		const closeSubmenu = (event) => {
			if (!ref.current?.parentElement?.contains(event.target)) {
				ref.current.setAttribute('aria-expanded', 'false');
			}
		};
		window.addEventListener('click', closeSubmenu);
		return () => window.removeEventListener('click', closeSubmenu);
	}, []);

	function toggleSubmenu() {
		ref.current.setAttribute('aria-expanded', ref.current.ariaExpanded === 'true' ? 'false': 'true');
	}

	return (
		<Wrapper
			aria-haspopup="true"
			onClick={toggleSubmenu}
			className={props.className}
			data-tooltip-id="django-finder-tooltip"
			data-tooltip-content={props.tooltip}
		>
			{props.icon}
			<ul ref={ref} role="combobox" aria-expanded="false">
				{props.children}
			</ul>
		</Wrapper>
	)
}
