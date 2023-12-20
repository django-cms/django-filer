import React, {useContext, useEffect, useMemo, useRef, useState} from 'react';
import ReactCrop, {Crop} from 'react-image-crop';
import {ProgressBar, ProgressOverlay} from '../UploadProgress';
import {FinderSettings} from '../FinderSettings';
import DownloadIcon from '../icons/download.svg';
import FullSizeIcon from '../icons/full-size.svg';
import UploadIcon from '../icons/upload.svg';


export default function Image(props) {
	const settings = useContext(FinderSettings);
	const cropFields = {
		x: document.getElementById('id_crop_x') as HTMLInputElement,
		y: document.getElementById('id_crop_y') as HTMLInputElement,
		size: document.getElementById('id_crop_size') as HTMLInputElement,
		width: document.getElementById('id_width') as HTMLInputElement,
		height: document.getElementById('id_height') as HTMLInputElement,
	};
	const [crop, setCrop] = useState<Crop>();
	const [uploadFile, setUploadFile] = useState<Promise<Response>>(null);
	const ref = useRef(null);
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

	useEffect(() => {
		ref.current.addEventListener('load', () => {
			if (!cropFields.size.value)
				return;
			const rect = ref.current.getBoundingClientRect();
			const size = parseFloat(cropFields.size.value) / parseInt(cropFields.width.value) * rect.width;
			setCrop({
				unit: 'px',
				x: parseFloat(cropFields.x.value) / parseInt(cropFields.width.value) * rect.width,
				y: parseFloat(cropFields.y.value) / parseInt(cropFields.height.value) * rect.height,
				width: size,
				height: size,
			});
		});
	}, []);

	function handleChange(crop) {
		const rect = ref.current.getBoundingClientRect();
		setCrop(crop);
		cropFields.x.value = String(crop.x / rect.width * parseInt(cropFields.width.value));
		cropFields.y.value = String(crop.y / rect.height * parseInt(cropFields.height.value));
		cropFields.size.value = String(crop.width / rect.width * parseInt(cropFields.width.value));
	}

	function renderFullSize() {
		window.open(settings.download_url, '_blank').focus();
	}

	function replaceImage() {
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
		<div className="image-details">
			<h2>{subtitle}</h2>
			<ReactCrop crop={crop} aspect={1} onChange={handleChange}>
				<img src={settings.download_url} ref={ref} />
			</ReactCrop>
			<div className="button-group">
				<a download={settings.filename} href={settings.download_url}><DownloadIcon/>{gettext("Download")}</a>
				<button onClick={renderFullSize}><FullSizeIcon/>{gettext("Full Size")}</button>
				<button onClick={replaceImage}><UploadIcon/>{gettext("Replace Image")}</button>
			</div>
			<a ref={downloadLinkRef} download="download" hidden />
			<input type="file" name="replaceFile" ref={inputRef} accept={settings.file_mime_type} onChange={handleFileSelect} />
		</div>
		{uploadFile &&
		<ProgressOverlay>
			<ProgressBar file={uploadFile} targetId={settings.file_id} />
		</ProgressOverlay>
		}
	</>);
}
