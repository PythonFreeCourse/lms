function copy_code(button) {
    button.addEventListener('click', () => {
        var copyText = document.getElementById('python-user-code');
        navigator.clipboard.writeText(copyText.textContent);
        var last = button.innerHTML;
        button.innerHTML = 'Copied!';
        setTimeout(function() {
            button.innerHTML = last;
        }, 3000);
    });
}


window.addEventListener('load', () => {
    copy_code(document.getElementById('copy-button'));
});
