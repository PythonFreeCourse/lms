function copy_code() {
    var copyText = document.getElementById("python-user-code");
    navigator.clipboard.writeText(copyText.textContent);
}
