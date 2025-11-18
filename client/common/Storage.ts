import {useEffect, useMemo, useState} from 'react';


export function useSessionStorage(storageKey: string, initial) {
	return () => {
		const [value, setValue] = useState(
			JSON.parse(sessionStorage.getItem(storageKey)) ?? initial
		);

		useEffect(() => {
			sessionStorage.setItem(storageKey, JSON.stringify(value));
		}, [value, storageKey]);

		return [value, setValue];
	};
}


export function useCookie(key, initial) : [any, (value: any) => any] {
	const [toConverter, fromConverter] = useMemo(() => {
		if (Array.isArray(initial)) {
			return [
				v => v.join(','),
				v1 => v1.split(',').filter(v2 => isFinite(Number(v2))).map(v3 => Number(v3)),
			];
		}
		if (typeof initial === 'number') {
			return [
				v => v,
				v => Number(v),
			];
		}
		return [
			v => v,
			v => v,
		];
	}, []);

	const [value, setValue] = useState(() => {
		const row = document.cookie.split('; ').find(row => row.startsWith(`${key}=`)); //?.split('=')[1] ?? initial
		return row ? fromConverter(row.split('=')[1]) : initial;
	});

	function setCookie(value) {
		const rhs = toConverter(value);
		document.cookie = `${key}=${rhs}; path=/; expires=Fri, 31 Dec 9999 23:59:59 GMT; SameSite=Lax;`;
	}

	useEffect(() => {
		setCookie(value);
	}, [value]);

	return [
		value,
		value => {
			setCookie(value);
			setValue(value);
		},
	];
}


export const useSearchZone = initial => useCookie('django-finder-search-zone', initial);
