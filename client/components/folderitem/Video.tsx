import React, {useRef} from 'react';
import ReactPlayer from 'react-player/file';
import {FigureLabels} from 'finder/Item';


export default function Video(props) {
	const videoRef = useRef(null);

	const onPlayPause = (isPlaying: boolean) => {
		const player = videoRef.current.getInternalPlayer();
		if (isPlaying) {
			player.pause();
			videoRef.current.seekTo(0);
		} else {
			player.play();
		}
	}

	return (
		<FigureLabels labels={props.labels}>{
		props.sample_url ? (
			<ReactPlayer
				onMouseEnter={() => onPlayPause(false)}
				onMouseLeave={() => onPlayPause(true)}
				url={props.sample_url}
				config={{attributes: {poster: props.thumbnail_url}}}
				controls={false}
				pip={false}
				ref={videoRef}
				width="100%"
				height="100%"
			/>
		) : (
			<img src={props.thumbnail_url} />
		)
		}</FigureLabels>
	);
}
