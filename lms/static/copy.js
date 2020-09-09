function copy_code(button) {
    button.addEventListener('click', () => {
        var copyText = document.getElementById("python-user-code");
        navigator.clipboard.writeText(copyText.textContent);
    });
}


window.addEventListener('load', () => {
    copy_code(document.getElementById('copy-button'));
});
