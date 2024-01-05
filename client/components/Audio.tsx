import React, {useContext, useEffect, useMemo, useRef, useState} from 'react';
import WavesurferPlayer from '@wavesurfer/react';
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.js';
import {FinderSettings} from '../FinderSettings';
import DownloadIcon from '../icons/download.svg';
import UploadIcon from '../icons/upload.svg';
import PauseIcon from '../icons/pause.svg';
import PlayIcon from '../icons/play.svg';
import {ProgressBar, ProgressOverlay} from "../UploadProgress";


export default function Audio(props) {
	if (props.editorRef) {
		// in edit view
		const sampleFields = {
			start: document.getElementById('id_sample_start') as HTMLInputElement,
			duration: document.getElementById('id_sample_duration') as HTMLInputElement,
		};
		const settings = useContext(FinderSettings);
		const [uploadFile, setUploadFile] = useState<Promise<Response>>(null);
		const downloadLinkRef = useRef(null);
		const inputRef = useRef(null);
		const subtitle = useMemo(
			() => {
				const subtitle = document.getElementById('id_subtitle');
				subtitle.remove();
				return subtitle.innerHTML;
			},
			[]
		);
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

		function replaceFile() {
			inputRef.current.click();
		}

		function handleFileSelect(event) {
			const file = event.target.files[0];
			const promise = new Promise<Response>((resolve, reject) => {
				file.resolve = resolve;
				file.reject = reject;
			});
			setUploadFile(file);
			promise.then((response) => {
				window.location.reload();
			}).catch((error) => {
				alert(error);
			}).finally( () => {
				setUploadFile(null);
			});
		}

		return (<>
			<div className="file-details">
				<h2>{subtitle}</h2>
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
				<div className="button-group">
					{isPlaying ? <button onClick={onPlayPause}><PauseIcon/>{gettext("Pause")}</button> :
						<button onClick={onPlayPause}><PlayIcon/>{gettext("Play")}</button>}
					<a download={settings.filename} href={settings.download_url}><DownloadIcon/>{gettext("Download")}
					</a>
					<button onClick={replaceFile}><UploadIcon/>{gettext("Replace File")}</button>
				</div>
				<a ref={downloadLinkRef} download="download" hidden/>
				<input type="file" name="replaceFile" ref={inputRef} accept={settings.file_mime_type}
					   onChange={handleFileSelect}/>
			</div>
			{uploadFile &&
				<ProgressOverlay>
					<ProgressBar file={uploadFile} targetId={settings.file_id}/>
				</ProgressOverlay>
			}
		</>);
	} else {
		// in list view
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
}
