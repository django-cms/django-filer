import React, {useEffect, useRef} from 'react';
import {Tooltip, TooltipTrigger, TooltipContent} from '../common/Tooltip';


export default function DropDownMenu(props) {
	const ref = useRef(null);
	const WrapperElement = props.wrapperElement ?? 'li';

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
		<WrapperElement
			ref={ref}
			role={props.role ? `combobox ${props.role}` : 'combobox'}
			aria-haspopup="listbox"
			aria-expanded="false"
			className={props.className}
		>{
		props.tooltip ? (
			<Tooltip>
				<TooltipTrigger>{props.icon && <i>{props.icon}</i>}{props.label ? props.label : ''}</TooltipTrigger>
				<TooltipContent root={props.root}>{props.tooltip}</TooltipContent>
				<ul role="listbox">
					{props.children}
				</ul>
			</Tooltip>
		) : (
			<>
				<div>{props.icon && <i>{props.icon}</i>}{props.label ? props.label : ''}</div>
				<ul role="listbox">
					{props.children}
				</ul>
			</>
		)
		}</WrapperElement>
	)
}
