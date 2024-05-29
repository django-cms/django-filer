import React, {useEffect, useState} from 'react';


export default function Audio(props) {
	const [mouseOver, setMouseOver] = useState(false);

	useEffect(() => {
		if (!mouseOver)
			return;
		const audio = new window.Audio(props.sampleUrl);
		const playPromise = audio.play();

		return () => {
			playPromise.then(() => audio.pause());
		};
	}, [mouseOver]);

	return (
		<div onMouseEnter={() => setMouseOver(true)} onMouseLeave={() => setMouseOver(false)}>
			{props.children}
		</div>
	);
}
