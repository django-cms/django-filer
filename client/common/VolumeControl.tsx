import React from 'react';
import {useAudioSettings} from '../common/Storage';
import DropDownMenu from '../common/DropDownMenu';
import SpeakerMutedicon from '../icons/speaker-muted.svg';
import SpeakerSilentIcon from '../icons/speaker-silent.svg';
import SpeakerMediumIcon from '../icons/speaker-medium.svg';
import SpeakerLoudIcon from '../icons/speaker-loud.svg';


export function renderSpeakerIcon(volume) {
	if (volume === 0.0) {
		return <SpeakerMutedicon/>;
	}
	if (volume < 0.33) {
		return <SpeakerSilentIcon/>;
	}
	if (volume < 0.66) {
		return <SpeakerMediumIcon/>;
	}
	return <SpeakerLoudIcon/>;
}


export default function VolumeControl(props: any) {
	const [audioSettings, setAudioSettings] = useAudioSettings();

	function handleChange(event) {
		const volume = parseFloat(event.target.value);
		setAudioSettings({volume: volume});
		props.webAudio.gainNode.gain.setValueAtTime(volume, props.webAudio.context.currentTime);
	}

	return (
		<DropDownMenu
			icon={renderSpeakerIcon(audioSettings.volume)}
			role="menuitem"
			className="volume-control"
			tooltip={gettext("Change volume level")}
			root={props.root}
		>
			<li>
				<label htmlFor="volume_level">{gettext("Volume level")}:</label>
				<input name="volume_level" type="range" min="0.0" max="1.0" step="0.001" value={audioSettings.volume} onChange={handleChange}/>
			</li>
		</DropDownMenu>
	);
}
