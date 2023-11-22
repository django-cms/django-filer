declare module '*.scss' {
	const styles: string;
	export default styles;
}
declare module '*.svg' {
	const content: string;
	export default content;
}
declare function gettext(s: string): string;
