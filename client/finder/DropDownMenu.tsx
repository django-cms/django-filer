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
		const rootNode = ref.current.getRootNode();
		rootNode.addEventListener('click', closeSubmenu);
		return () => rootNode.removeEventListener('click', closeSubmenu);
	}, []);

	function toggleSubmenu() {
		ref.current.setAttribute('aria-expanded', ref.current.ariaExpanded === 'true' ? 'false' : 'true');
	}

	return (
		<Wrapper
			ref={ref}
			role={props.role ? `combobox ${props.role}` : 'combobox'}
			aria-haspopup="listbox"
			aria-expanded="false"
			onClick={toggleSubmenu}
			className={props.className}
			data-tooltip-id="django-finder-tooltip"
			data-tooltip-content={props.tooltip}
		>
			{props.icon}
			<ul role="listbox">
				{props.children}
			</ul>
		</Wrapper>
	)
}
