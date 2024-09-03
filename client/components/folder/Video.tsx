import React, {useEffect, useRef, useState} from 'react';
import ReactPlayer from 'react-player/file';


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
		<ReactPlayer
			onMouseEnter={() => onPlayPause(false)}
			onMouseLeave={() => onPlayPause(true)}
			url={props.sampleUrl}
			config={{attributes: {poster: props.thumbnailUrl}}}
			controls={false}
			pip={false}
			ref={videoRef}
			width="100%"
			height="100%"
		/>
	);
}
