// #DROPZONE#
// This script implements the dropzone settings

var myDropzone = new Dropzone('.js-dropzone', { url: '/file/post'});
Dropzone.autoDiscover = false;
Dropzone.options.jsDropzone = {
    paramName: "file", // The name that will be used to transfer the file
    maxFilesize: 2 // MB
};