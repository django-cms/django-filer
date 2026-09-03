/**
 * Keyboard navigation through the list of inodes.
 *
 * This is the arithmetic behind the arrow keys of `InodeList`, kept apart from the
 * component so that it can be reasoned about – and tested – on its own.
 */

/** The keys which move the preselection. Every other key leaves it alone. */
const NAVIGATION_KEYS = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'];

export interface Preselection {
	/** `KeyboardEvent.key` of the key which has been pressed. */
	key: string;
	/** Index of the currently preselected inode, or -1 if none of them is. */
	index: number;
	/** Number of inodes listed in the current folder. */
	count: number;
	/** Number of inodes rendered side by side, as computed from the current layout. */
	inodesPerRow: number;
	/** The layout the folder is rendered in, one of tiles, mosaic, list, columns or gallery. */
	layout: string;
}

/**
 * Compute the index the preselection moves to, or `null` if it stays where it is.
 *
 * In the columns layout, ArrowLeft and ArrowRight change the column rather than the
 * row: `FolderAdmin` focuses the neighbouring column and then delegates here, so the
 * preselection starts over at the top of that column.
 */
export function nextPreselectionIndex({key, index, count, inodesPerRow, layout}: Preselection): number | null {
	if (!NAVIGATION_KEYS.includes(key))
		return null;

	let nextIndex: number;
	if (key === 'ArrowLeft') {
		nextIndex = layout === 'columns' ? 0 : index - 1;
	} else if (key === 'ArrowRight') {
		nextIndex = layout === 'columns' ? 0 : index + 1;
	} else if (key === 'ArrowUp') {
		nextIndex = index - inodesPerRow;
	} else {
		nextIndex = index + inodesPerRow;
	}

	// Staying inside the list is what keeps the preselection from wrapping around:
	// `Array.prototype.at()` would resolve a negative index against the end of the list.
	return nextIndex >= 0 && nextIndex < count ? nextIndex : null;
}
