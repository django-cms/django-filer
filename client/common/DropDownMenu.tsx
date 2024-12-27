import React, {useEffect, useRef} from 'react';


export default function DropDownMenu(props){
	const ref = useRef(null);
	const Wrapper = props.wrapperElement ?? 'li';

	useEffect(() => {
		const handleClick = (event) => {
			const current = ref.current as HTMLElement;
			let target = event.target;
			if (!current.contains(target)) {
				current.setAttribute('aria-expanded', 'false');
				return;
			}
			if (current.ariaExpanded === 'false') {
				for (let target = event.target; target; target = target.parentElement) {
					if (target.role === 'listbox') {
						return;
					}
				}
				current.setAttribute('aria-expanded', 'true');
			} else {
				for (let target = event.target; target; target = target.parentElement) {
					if (target.ariaMultiSelectable) {
						return;
					}
					if (target === current) {
						current.setAttribute('aria-expanded', 'false');
						break;
					}
				}
			}
		};
		const rootNode = ref.current.getRootNode();
		rootNode.addEventListener('click', handleClick);
		return () => rootNode.removeEventListener('click', handleClick);
	}, []);

	return (
		<Wrapper
			ref={ref}
			role={props.role ? `combobox ${props.role}` : 'combobox'}
			aria-haspopup="listbox"
			aria-expanded="false"
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
