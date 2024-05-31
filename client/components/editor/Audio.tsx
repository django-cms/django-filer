import React, {useContext, useState} from 'react';
import WavesurferPlayer from '@wavesurfer/react';
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.js';
import {FinderSettings} from 'finder/FinderSettings';
import {FileDetails} from 'finder/FileDetails';
import PauseIcon from 'icons/pause.svg';
import PlayIcon from 'icons/play.svg';


export default function Audio(props) {
	const sampleFields = {
		start: document.getElementById('id_sample_start') as HTMLInputElement,
		duration: document.getElementById('id_sample_duration') as HTMLInputElement,
	};
	const settings = useContext(FinderSettings);
	const [wavesurfer, setWavesurfer] = useState(null);
	const [isPlaying, setIsPlaying] = useState(false);

	const onReady = (ws) => {
		setWavesurfer(ws);

		const wsRegions = ws.registerPlugin(RegionsPlugin.create());
		const start = parseFloat(sampleFields.start.value);
		wsRegions.addRegion({
			content: gettext("Sample Audio"),
			start: start,
			end: start + parseFloat(sampleFields.duration.value),
			color: 'rgba(255, 255, 204, 0.5)',
			drag: true,
			resize: false,
		});
		wsRegions.on('region-updated', (region) => {
			sampleFields.start.value = String(region.start);
			// we actually do not allow the user to set the duration
		});

		setIsPlaying(false);
	}

	const onPlayPause = () => {
		wavesurfer && wavesurfer.playPause();
	}

	const controlButton = isPlaying ?
		<button onClick={onPlayPause}><PauseIcon/>{gettext("Pause")}</button> :
		<button onClick={onPlayPause}><PlayIcon/>{gettext("Play")}</button>;

	return (
		<FileDetails controlButtons={[controlButton]}>
			<WavesurferPlayer
				url={settings.download_url}
				onReady={onReady}
				onPlay={() => setIsPlaying(true)}
				onPause={() => setIsPlaying(false)}
				minPxPerSec={40}
				hideScrollbar={false}
				autoCenter={false}
				cursorColor='rgb(186, 33, 33)'
				cursorWidth={2}
				waveColor='rgb(121, 174, 200)'
				progressColor='rgb(65, 118, 144)'
			/>
		</FileDetails>
	);
}
