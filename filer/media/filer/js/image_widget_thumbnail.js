function dismissRelatedImageLookupPopup(win, chosenId, chosenThumbnailUrl, chosenDescriptionTxt) {
    var name = windowname_to_id(win.name);
	var img_name = name + '_thumbnail_img';
	var txt_name = name + '_description_txt';
    var elem = document.getElementById(name);
    document.getElementById(name).value = chosenId;
	document.getElementById(img_name).src = chosenThumbnailUrl;
	document.getElementById(txt_name).innerHTML = chosenDescriptionTxt;
    win.close();
};
