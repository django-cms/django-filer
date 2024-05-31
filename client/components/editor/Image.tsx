import React, {useContext, useEffect, useRef, useState} from 'react';
import ReactCrop, {Crop} from 'react-image-crop';
import {FinderSettings} from 'finder/FinderSettings';
import {FileDetails} from 'finder/FileDetails';


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
	const ref = useRef(null);

	useEffect(() => {
		if (!ref?.current)
			return;
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
		}, {once: true});
	}, []);

	function handleChange(crop) {
		const rect = ref.current.getBoundingClientRect();
		setCrop(crop);
		cropFields.x.value = String(crop.x / rect.width * parseInt(cropFields.width.value));
		cropFields.y.value = String(crop.y / rect.height * parseInt(cropFields.height.value));
		cropFields.size.value = String(crop.width / rect.width * parseInt(cropFields.width.value));
	}

	return (
		<FileDetails>
			<ReactCrop crop={crop} aspect={1} onChange={handleChange}>
				<img className="editable" src={settings.download_url} ref={ref} />
			</ReactCrop>
		</FileDetails>
	);
}
