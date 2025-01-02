import React, {
	createContext,
	forwardRef,
	isValidElement,
	HTMLProps,
	ReactNode,
	useContext,
	useMemo,
	useState,
} from 'react';
import {
	useFloating,
	autoUpdate,
	offset,
	flip,
	shift,
	useHover,
	useFocus,
	useDismiss,
	useRole,
	useInteractions,
	useMergeRefs,
	FloatingPortal
} from '@floating-ui/react';
import type {Placement} from "@floating-ui/react";

interface TooltipOptions {
	initialOpen?: boolean;
	placement?: Placement;
	open?: boolean;
	onOpenChange?: (open: boolean) => void;
}

export function useTooltip({initialOpen=false, placement='bottom', open: controlledOpen, onOpenChange: setControlledOpen}: TooltipOptions = {}) {
	const [uncontrolledOpen, setUncontrolledOpen] = useState(initialOpen);
	const open = controlledOpen ?? uncontrolledOpen;
	const setOpen = setControlledOpen ?? setUncontrolledOpen;

	const data = useFloating({
		placement,
		open,
		onOpenChange: setOpen,
		whileElementsMounted: autoUpdate,
		middleware: [
			offset(1),
			flip({
				crossAxis: placement.includes('-'),
				fallbackAxisSideDirection: 'start',
				padding: 5,
			}),
			shift({padding: 5}),
		]
	});

	const context = data.context;

	const hover = useHover(context, {
		move: false,
		enabled: controlledOpen == null
	});
	const focus = useFocus(context, {
		enabled: controlledOpen == null
	});
	const dismiss = useDismiss(context);
	const role = useRole(context, {role: "tooltip"});

	const interactions = useInteractions([hover, focus, dismiss, role]);

	return useMemo(
		() => ({
			open,
			setOpen,
			...interactions,
			...data,
		}),
		[open, setOpen, interactions, data]
	);
}

type ContextType = ReturnType<typeof useTooltip> | null;

const TooltipContext = createContext<ContextType>(null);

export const useTooltipContext = () => {
	const context = useContext(TooltipContext);

	if (context == null) {
		throw new Error("Tooltip components must be wrapped in <Tooltip />");
	}

	return context;
};

export function Tooltip({children, ...options}: { children: ReactNode } & TooltipOptions) {
	// This can accept any props as options, e.g. `placement`,
	// or other positioning options.
	const tooltip = useTooltip(options);
	return (
		<TooltipContext.Provider value={tooltip}>
			{children}
		</TooltipContext.Provider>
	);
}

export const TooltipTrigger = forwardRef<
	HTMLElement,
	HTMLProps<HTMLElement> & {asChild?: boolean}
>(({children, asChild = false, ...props}, forwardedRef) => {
	const context = useTooltipContext();
	const childrenRef = (children as any).ref;
	const ref = useMergeRefs([context.refs.setReference, forwardedRef, childrenRef]);

	// `asChild` allows the user to pass any element as the anchor
	if (asChild && isValidElement(children)) {
		return React.cloneElement(
			children,
			context.getReferenceProps({
				ref,
				...props,
				...children.props,
				'data-state': context.open ? 'open' : 'closed'
			})
		);
	}

	return (
		<div
			ref={ref}
			// The user can style the trigger based on the state
			data-state={context.open ? "open" : "closed"}
			{...context.getReferenceProps(props)}
		>
			{children}
		</div>
	);
});


export const TooltipContent = forwardRef<
	HTMLDivElement,
	HTMLProps<HTMLDivElement> & {root?: HTMLElement}
>(({style, ...props}, forwardedRef) => {
	const context = useTooltipContext();
	const refs = useMergeRefs([context.refs.setFloating, forwardedRef]);

	return context.open ? (
		<FloatingPortal root={props.root}>
			<div
				ref={refs}
				className="django-finder-tooltip"
				style={{...context.floatingStyles, ...style}}
				{...context.getFloatingProps(props)}
			/>
		</FloatingPortal>
	) : null;
});
