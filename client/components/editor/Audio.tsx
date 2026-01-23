import React, {Fragment, useState} from 'react';
import WavesurferPlayer from '@wavesurfer/react';
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.js';
import FileDetails from '../../admin/FileDetails';
import {useAudioSettings} from '../../common/Storage';
import DropDownMenu from '../../common/DropDownMenu';
import {renderSpeakerIcon} from '../../common/VolumeControl';
import PauseIcon from '../../icons/pause.svg';
import PlayIcon from '../../icons/play.svg';


export default function Audio(props) {
	const {settings, children} = props;
	const sampleFields = {
		start: document.getElementById('id_sample_start') as HTMLInputElement,
		duration: document.getElementById('id_sample_duration') as HTMLInputElement,
	};
	const [wavesurfer, setWavesurfer] = useState(null);
	const [isPlaying, setIsPlaying] = useState(false);
	const [audioSettings, setAudioSettings] = useAudioSettings();

	const onReady = (ws) => {
		document.getElementById('wavesurfer-initializing')?.remove();
		ws.setOptions({height: 128});
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
	};

	const onPlayPause = () => {
		wavesurfer && wavesurfer.playPause();
	};

	function setVolume(event) {
		const volume = parseFloat(event.target.value);
		setAudioSettings({volume: volume});
		wavesurfer && wavesurfer.setVolume(volume);
	}

	const controlButtons = [
		<Fragment key="play-pause">{isPlaying ?
			<button type="button" onClick={onPlayPause}><PauseIcon/>{gettext("Pause")}</button> :
			<button type="button" onClick={onPlayPause}><PlayIcon/>{gettext("Play")}</button>
		}</Fragment>,
		<DropDownMenu
			key="volume-control"
			className="volume-control with-caret"
			label={gettext("Set Volume")}
			icon={renderSpeakerIcon(audioSettings.volume)}
			wrapperElement="div"
		>
			<li>
				<label htmlFor="volume_level">{gettext("Volume level")}:</label>
				<input name="volume_level" type="range" min="0.0" max="1.0" step="0.001" value={audioSettings.volume} onChange={setVolume}/>
			</li>
		</DropDownMenu>,
	];

	const placeholderStyle: React.CSSProperties = {
		height: '143px',
		padding: '2rem',
		fontSize: '18px',
		boxSizing: 'border-box',
		color: 'rgb(128, 128, 128)',
		cursor: 'wait',
	};

	return (<>
		{children}
		<FileDetails controlButtons={controlButtons} {...props}>
			<div id="wavesurfer-initializing" style={placeholderStyle}>
				{gettext("Initializing audio player, please wait ...")}
			</div>
			<WavesurferPlayer
				url={settings.download_url}
				height={0}
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
	</>);
}
