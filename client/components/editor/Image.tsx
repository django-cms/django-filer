import React, {Fragment, useEffect, useRef, useState} from 'react';
import ReactCrop, {Crop} from 'react-image-crop';
import DropDownMenu from '../../common/DropDownMenu';
import FileDetails from '../../admin/FileDetails';
import ClearCropIcon from '../../icons/clear-crop.svg';


export default function Image(props) {
	const {settings} = props;
	const cropFields = {
		x: document.getElementById('id_crop_x') as HTMLInputElement,
		y: document.getElementById('id_crop_y') as HTMLInputElement,
		size: document.getElementById('id_crop_size') as HTMLInputElement,
		width: document.getElementById('id_width') as HTMLInputElement,
		height: document.getElementById('id_height') as HTMLInputElement,
	};
	const gravityField = document.getElementById('id_gravity') as HTMLInputElement;
	const [crop, setCrop] = useState<Crop>(null);
	const [gravity, setGravity] = useState<string>(gravityField.value);
	const ref = useRef(null);
	const gravityOptions = {
		'': gettext("Center"), 'n': gettext("North"), 'ne': gettext("Northeast"),
		 'e': gettext("East"), 'se': gettext("Southeast"), 's': gettext("South"),
		 'sw': gettext("Southwest"), 'w': gettext("West"), 'nw': gettext("Northwest"),
	};

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

	function getItemProps(value: string) {
		return {
			role: 'option',
			'aria-selected': gravity === value,
			onClick: () => {
				setGravity(value);
				gravityField.value = value;
			},
		};
	}

	const controlButtons = [
		<Fragment key="clear-crop">
			<button type="button" onClick={() => handleChange(null)}><ClearCropIcon/>{gettext("Clear selection")}</button>
			<DropDownMenu className="with-caret" wrapperElement="div" label={gettext("Gravity") + ": " + gravityOptions[gravity]} tooltip={gettext("Align image before cropping")}>
				{Object.entries(gravityOptions).map(([value, label]) => (<li {...getItemProps(value)}>{label}</li>))}
			</DropDownMenu>
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
