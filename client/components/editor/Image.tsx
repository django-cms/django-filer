import React, {Fragment, useEffect, useRef, useState} from 'react';
import ReactCrop, {Crop} from 'react-image-crop';
import FileDetails from 'finder/FileDetails';
import ClearCropIcon from 'icons/clear-crop.svg';


export default function Image(props) {
	const {settings} = props;
	const cropFields = {
		x: document.getElementById('id_crop_x') as HTMLInputElement,
		y: document.getElementById('id_crop_y') as HTMLInputElement,
		size: document.getElementById('id_crop_size') as HTMLInputElement,
		width: document.getElementById('id_width') as HTMLInputElement,
		height: document.getElementById('id_height') as HTMLInputElement,
	};
	const [crop, setCrop] = useState<Crop>(null);
	const ref = useRef(null);

	useEffect(() => {
		const crop = () => {
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
		};

		if (ref.current.complete) {
			crop();
		} else {
			ref.current.addEventListener('load', crop, {once: true});
		}
	}, []);

	function handleChange(crop) {
		setCrop(crop);
		if (crop) {
			const rect = ref.current.getBoundingClientRect();
			cropFields.x.value = String(crop.x / rect.width * parseInt(cropFields.width.value));
			cropFields.y.value = String(crop.y / rect.height * parseInt(cropFields.height.value));
			cropFields.size.value = String(crop.width / rect.width * parseInt(cropFields.width.value));
		} else {
			cropFields.x.value = '';
			cropFields.y.value = '';
			cropFields.size.value = '';
		}
	}

	const controlButtons = [
		<Fragment key="clear-crop">
			<button type="button" onClick={() => handleChange(null)}><ClearCropIcon/>{gettext("Clear selection")}</button>
		</Fragment>
	];

	return (
		<FileDetails controlButtons={controlButtons} {...props}>
			<ReactCrop crop={crop} aspect={1} onChange={handleChange}>
				<img className="editable" src={settings.download_url} ref={ref} />
			</ReactCrop>
		</FileDetails>
	);
}
