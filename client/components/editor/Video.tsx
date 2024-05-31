import React, {useContext, useRef, useState} from 'react';
import ReactPlayer from 'react-player/file';
import {FinderSettings} from 'finder/FinderSettings';
import {FileDetails} from 'finder/FileDetails';
import PauseIcon from 'icons/pause.svg';
import PlayIcon from 'icons/play.svg';
import CameraIcon from 'icons/camera.svg';


export default function Video(props) {
	const sampleFields = {
		posterFrame: document.getElementById('id_poster_frame') as HTMLInputElement,
	};
	const settings = useContext(FinderSettings);
	const style = {
		width: '960px',
		maxWidth: '100%',
		height: 'auto',
	};
	const videoRef = useRef(null);
	const [isPlaying, setIsPlaying] = useState(false);

	const onReady = () => {
	}

	const onPlayPause = () => {
		const player = videoRef.current.getInternalPlayer();
		if (isPlaying) {
			player.pause();
			setIsPlaying(false);
		} else {
			player.play();
			setIsPlaying(true);
		}
	}

	const createPosterFrame = () => {
		const currentTime = videoRef.current.getCurrentTime();
		sampleFields.posterFrame.value = currentTime;
	}

	const controlButtons = [(isPlaying ?
		<button onClick={onPlayPause}><PauseIcon/>{gettext("Pause")}</button> :
		<button onClick={onPlayPause}><PlayIcon/>{gettext("Play")}</button>
	),
		<button onClick={createPosterFrame}><CameraIcon/>{gettext("Create Poster Frame")}</button>
	];
	return (
		<FileDetails controlButtons={controlButtons} style={style}>
			<ReactPlayer
				url={settings.download_url}
				controls={true}
				controlsList="nofullscreen nodownload"
				disablePictureInPicture={true}
				onReady={onReady}
				onPlay={() => setIsPlaying(true)}
				onPause={() => setIsPlaying(false)}
				pip={false}
				ref={videoRef}
				width="100%"
				height="100%"
			/>
		</FileDetails>
	);
}
