import React, {useEffect, useState} from 'react';


export default function Audio(props) {
	const [audioElement, setAudioElement] = useState<HTMLAudioElement>();

	useEffect(() => {
		if (!props.sample_url || !props.webAudio)
			return;
		const audioElement = new window.Audio(props.sample_url);
		const track = props.webAudio.context.createMediaElementSource(audioElement);
		track.connect(props.webAudio.gainNode).connect(props.webAudio.context.destination);
		setAudioElement(audioElement);
		return () => {
			track.disconnect();
		};
	}, []);

	function handleMouseOver() {
		if (!audioElement || !props.webAudio)
			return;
		if (props.webAudio.context.state === 'suspended') {
			props.webAudio.context.resume();
		}
		audioElement.play();
	}

	return (
		<div onMouseEnter={() => handleMouseOver()} onMouseLeave={() => audioElement?.pause()}>
			{props.children}
		</div>
	);
}
