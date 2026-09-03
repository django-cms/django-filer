import {describe, expect, it} from 'vitest';
import {nextPreselectionIndex} from './navigation';

/**
 * A list of 7 inodes rendered 3 per row, ie.
 *
 *     0  1  2
 *     3  4  5
 *     6
 */
const grid = {count: 7, inodesPerRow: 3, layout: 'tiles'};

/** A list of 5 inodes rendered one below the other. */
const column = {count: 5, inodesPerRow: 1, layout: 'list'};


describe('nextPreselectionIndex', () => {
	describe('moving inside the list', () => {
		it.each([
			['ArrowRight', 4, 5],
			['ArrowLeft', 4, 3],
			['ArrowDown', 1, 4],
			['ArrowUp', 4, 1],
		])('%s at index %i moves to %i', (key, index, expected) => {
			expect(nextPreselectionIndex({...grid, key, index})).toBe(expected);
		});

		it('steps a full row at a time', () => {
			expect(nextPreselectionIndex({...grid, key: 'ArrowDown', index: 0})).toBe(3);
			expect(nextPreselectionIndex({...column, key: 'ArrowDown', index: 0})).toBe(1);
		});
	});

	describe('stopping at the edges of the list', () => {
		// Regression test for the fix in 56df1a5: the previous implementation used
		// `inodes.at(index - 1)`, and `Array.prototype.at()` resolves a negative index
		// against the end of the list. Pressing ArrowLeft on the first inode therefore
		// jumped to the last one instead of staying put.
		it('does not wrap around when moving left off the first inode', () => {
			expect(nextPreselectionIndex({...grid, key: 'ArrowLeft', index: 0})).toBeNull();
		});

		it('does not wrap around when moving up out of the first row', () => {
			expect(nextPreselectionIndex({...grid, key: 'ArrowUp', index: 0})).toBeNull();
			expect(nextPreselectionIndex({...grid, key: 'ArrowUp', index: 2})).toBeNull();
		});

		it('does not move past the last inode', () => {
			expect(nextPreselectionIndex({...grid, key: 'ArrowRight', index: 6})).toBeNull();
			expect(nextPreselectionIndex({...grid, key: 'ArrowDown', index: 6})).toBeNull();
		});

		it('does not move down into a row which is not fully populated', () => {
			// index 4 sits in the second row, and 4 + 3 = 7 is past the last inode
			expect(nextPreselectionIndex({...grid, key: 'ArrowDown', index: 4})).toBeNull();
		});

		it('stays put in an empty folder', () => {
			for (const key of ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown']) {
				expect(nextPreselectionIndex({count: 0, inodesPerRow: 3, layout: 'tiles', key, index: -1})).toBeNull();
			}
		});
	});

	describe('in the columns layout', () => {
		// `FolderAdmin` focuses the neighbouring column first and then delegates here,
		// so the preselection restarts at the top of that column.
		it.each(['ArrowLeft', 'ArrowRight'])('%s preselects the first inode of the column', (key) => {
			expect(nextPreselectionIndex({count: 5, inodesPerRow: 1, layout: 'columns', key, index: 3})).toBe(0);
		});

		it('still moves up and down within the column', () => {
			const columns = {count: 5, inodesPerRow: 1, layout: 'columns'};
			expect(nextPreselectionIndex({...columns, key: 'ArrowDown', index: 3})).toBe(4);
			expect(nextPreselectionIndex({...columns, key: 'ArrowUp', index: 3})).toBe(2);
		});

		it('stays put when the column is empty', () => {
			expect(nextPreselectionIndex({
				count: 0, inodesPerRow: 1, layout: 'columns', key: 'ArrowRight', index: -1,
			})).toBeNull();
		});
	});

	describe('keys which do not navigate', () => {
		it.each([' ', 'Enter', 'Escape', 'a', 'Tab'])('leaves the preselection alone on %j', (key) => {
			expect(nextPreselectionIndex({...grid, key, index: 3})).toBeNull();
		});
	});

	describe('without a preselected inode', () => {
		// `index` is -1 when the preselected inode is not part of this list, which
		// happens while the preselection sits in another column.
		it('moves forward into the first inode', () => {
			expect(nextPreselectionIndex({...grid, key: 'ArrowRight', index: -1})).toBe(0);
			expect(nextPreselectionIndex({...column, key: 'ArrowDown', index: -1})).toBe(0);
		});

		it('does not move backwards', () => {
			expect(nextPreselectionIndex({...grid, key: 'ArrowLeft', index: -1})).toBeNull();
			expect(nextPreselectionIndex({...grid, key: 'ArrowUp', index: -1})).toBeNull();
		});
	});
});
