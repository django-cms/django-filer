import {ReactNode, RefObject, useEffect, useState} from 'react';
import {createPortal} from 'react-dom';


// django CMS edits plugins in an iframe inside its modal, which is too small for the dialog
const CMS_MODAL_SELECTOR = '.cms-modal';


/**
 * If the select widget is rendered inside the iframe of a django CMS modal, create an element
 * with its own shadow root in the parent document, so that the dialog can use the whole window.
 * Returns null otherwise, or if the parent document is not accessible.
 */
function createParentHost(styleUrl: string) : ShadowRoot | null {
	try {
		// `frameElement` is null for a cross-origin parent
		const frameElement = window.frameElement;
		if (!frameElement?.closest(CMS_MODAL_SELECTOR))
			return null;
		const parentDocument = frameElement.ownerDocument;
		const host = parentDocument.createElement('div');
		host.classList.add('finder-dialog-host');
		const shadowRoot = host.attachShadow({mode: 'open'});
		const link = parentDocument.createElement('link');
		link.href = styleUrl;
		link.media = 'all';
		link.rel = 'stylesheet';
		shadowRoot.appendChild(link);
		parentDocument.body.appendChild(host);
		return shadowRoot;
	} catch {
		return null;
	}
}


/**
 * Hook deciding where the select dialog is rendered: in the parent window, if the widget sits
 * in a django CMS modal, otherwise in place. It installs the window listeners of the dialog.
 * Returns a function wrapping the `<dialog>` element accordingly.
 */
export function useDialogHost(styleUrl: string, dialogRef: RefObject<HTMLDialogElement>, onEscape: () => void) {
	const [parentHost] = useState(() => createParentHost(styleUrl));

	useEffect(() => {
		const handleEscape = (event: KeyboardEvent) => {
			if (event.key === 'Escape') {
				onEscape();
			}
		};
		const preventDefault = (event: DragEvent) => {
			event.preventDefault();
		};
		window.addEventListener('keydown', handleEscape);

		// prevent browser from loading a drag-and-dropped file
		window.addEventListener('dragover', preventDefault, false);
		window.addEventListener('drop', preventDefault, false);

		if (!parentHost) {
			return () => {
				window.removeEventListener('keydown', handleEscape);
				window.removeEventListener('dragover', preventDefault);
				window.removeEventListener('drop', preventDefault);
			};
		}

		const host = parentHost.host;
		const parentWindow = host.ownerDocument.defaultView;
		const handleParentEscape = (event: KeyboardEvent) => {
			if (event.key === 'Escape' && dialogRef.current?.open) {
				// django CMS would close its modal, too
				event.stopPropagation();
				onEscape();
			}
		};
		const preventParentDefault = (event: DragEvent) => {
			if (event.composedPath().includes(host)) {
				event.preventDefault();
			}
		};
		const removeHost = () => host.remove();
		parentWindow.addEventListener('keydown', handleParentEscape, true);
		parentWindow.addEventListener('dragover', preventParentDefault, false);
		parentWindow.addEventListener('drop', preventParentDefault, false);
		// React does not unmount, if django CMS closes or reloads its modal
		window.addEventListener('pagehide', removeHost);

		return () => {
			window.removeEventListener('keydown', handleEscape);
			window.removeEventListener('dragover', preventDefault);
			window.removeEventListener('drop', preventDefault);
			parentWindow.removeEventListener('keydown', handleParentEscape, true);
			parentWindow.removeEventListener('dragover', preventParentDefault);
			parentWindow.removeEventListener('drop', preventParentDefault);
			window.removeEventListener('pagehide', removeHost);
			removeHost();
		};
	}, []);

	return (dialog: ReactNode) => parentHost ? createPortal(dialog, parentHost) : dialog;
}
