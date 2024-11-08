import React, {useRef, useEffect} from 'react';
import FigureLabels from '../../common/FigureLabels';


export default function Video(props) {
	const videoRef = useRef(null);

	useEffect(() => {
		if (!(videoRef.current?.parentElement instanceof HTMLElement))
			return;
		const wrapper = videoRef.current.parentElement;
		let timeout = null;

		const play = () => {
			timeout && clearTimeout(timeout);
			videoRef.current.play();
		};

		const pause = () => {
			videoRef.current.pause();
			timeout = setTimeout(() => {
				// Reset the video to the beginning a second after leaving the video element
				videoRef.current.currentTime = 0;
			}, 1000);
		};

		wrapper.addEventListener('mouseenter', play);
		wrapper.addEventListener('mouseleave', pause);

		return () => {
			videoRef.current?.pause();
			timeout && clearTimeout(timeout);
			wrapper.removeEventListener('mouseenter', play);
			wrapper.removeEventListener('mouseleave', pause);
		}
	}, [videoRef]);

	return (
		<FigureLabels labels={props.labels}>{
		props.sample_url ? (
			<video
				ref={videoRef}
				src={props.sample_url}
				poster={props.thumbnail_url}
				controls={false}
				preload="auto"
				style={{width: '100%', height: '100%'}}
			></video>
		) : (
			<img src={props.thumbnail_url} />
		)
		}</FigureLabels>
	);
}
