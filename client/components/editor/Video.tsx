import React, {Fragment, useRef, useState} from 'react';
import ReactPlayer from 'react-player/file';
import FileDetails from '../../admin/FileDetails';
import PauseIcon from '../../icons/pause.svg';
import PlayIcon from '../../icons/play.svg';
import CameraIcon from '../../icons/camera.svg';


export default function Video(props) {
	const {settings, children} = props;
	const sampleFields = {
		sampleStart: document.getElementById('id_sample_start') as HTMLInputElement,
	};
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

	const setPosterFrame = () => {
		const currentTime = videoRef.current.getCurrentTime();
		sampleFields.sampleStart.value = currentTime;
	}

	const controlButtons = [
		<Fragment key="play-pause">{isPlaying ?
			<button type="button" onClick={onPlayPause}><PauseIcon/>{gettext("Pause")}</button> :
			<button type="button" onClick={onPlayPause}><PlayIcon/>{gettext("Play")}</button>
		}</Fragment>,
		<Fragment key="poster-frame">
			<button type="button" onClick={setPosterFrame}><CameraIcon/>{gettext("Use as Poster")}</button>
		</Fragment>,
	];
	return (<>
		{children}
		<FileDetails controlButtons={controlButtons} style={style} {...props}>
			<ReactPlayer
				url={settings.download_url}
				controls={true}
				controlsList="nofullscreen nodownload"
				onReady={onReady}
				onPlay={() => setIsPlaying(true)}
				onPause={() => setIsPlaying(false)}
				pip={false}
				ref={videoRef}
				width="100%"
				height="100%"
			/>
		</FileDetails>
	</>);
}
