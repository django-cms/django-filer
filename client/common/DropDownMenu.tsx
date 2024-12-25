import React, {forwardRef, useEffect, useImperativeHandle, useRef} from 'react';
import {types} from "sass";
import Boolean = types.Boolean;


const DropDownMenu = forwardRef((props: any, forwardedRef)=> {
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

	useImperativeHandle(forwardedRef, () => ({toggleSubmenu}));

	function toggleSubmenu(force?: boolean) {
		if (force === undefined) {
			ref.current.setAttribute('aria-expanded', ref.current.ariaExpanded === 'true' ? 'false' : 'true');
		} else {
			ref.current.setAttribute('aria-expanded', (!force).toString());
		}
	}

	return (
		<Wrapper
			ref={ref}
			role={props.role ? `combobox ${props.role}` : 'combobox'}
			aria-haspopup="listbox"
			aria-expanded="false"
			onClick={() => toggleSubmenu()}
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
});


export default DropDownMenu;
