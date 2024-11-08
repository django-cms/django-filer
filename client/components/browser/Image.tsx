import React, {useRef, useState} from 'react';
import ReactCrop, {Crop} from 'react-image-crop';


export default function Image(props) {
	const {fileInfo} = props;
	const ref = useRef(null);
	const [crop, setCrop] = useState<Crop>(null);

	function handleChange(crop) {
		const shadowRoot = ref.current?.getRootNode();
		if (!(shadowRoot instanceof ShadowRoot))
			return;

		const cropFields = {
			x: shadowRoot.getElementById('id_crop_x') as HTMLInputElement,
			y: shadowRoot.getElementById('id_crop_y') as HTMLInputElement,
			size: shadowRoot.getElementById('id_crop_size') as HTMLInputElement,
			width: shadowRoot.getElementById('id_width') as HTMLInputElement,
			height: shadowRoot.getElementById('id_height') as HTMLInputElement,
		};

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

	return (
		<ReactCrop crop={crop} aspect={1} onChange={handleChange}>
			<img className="editable" src={fileInfo.download_url} ref={ref} />
		</ReactCrop>
	);
}
