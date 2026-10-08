import React, {useState, useEffect} from 'react';

type State = 'mixed' | 'true' | 'false';


export default function TriStateCheckbox(props) {
	const {id, name, checked} = props;
	const onChange = typeof props.onChange === 'function' ? props.onChange : () => {};
	const [state, setState] = useState<State>(checked === true ? 'true' : checked === false ? 'false' : 'mixed');

	useEffect(() => {
		setState(checked === true ? 'true' : checked === false ? 'false' : 'mixed');
	}, [checked]);

	function handleCheck() {
		switch (state) {
			case 'mixed':
				setState('true');
				onChange(true);
				break;
			case 'true':
				setState('false');
				onChange(false);
				break;
			case 'false':
				setState('mixed');
				onChange(null);
				break;
		}
	}

	return (
		<div role="checkbox" name={name} id={id} aria-checked={state} onClick={() => handleCheck()}></div>
	);
}
