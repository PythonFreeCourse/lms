const templatedWords = /\$\{(\w+?)\}/g;


function escapeUnicode(str) {
  // Thanks to https://stackoverflow.com/a/45315988
  const json = JSON.stringify(str);
  return json.replace(/[\u007F-\uFFFF]/g, (chr) => {
    const step1 = chr.charCodeAt(0).toString(16);
    const step2 = `0000${step1}`.substr(-4);
    return `\\u${step2}`;
  });
}


function updateNotificationsCount() {
  const dropdown = document.getElementById('navbarNavDropdown');
  const container = document.getElementById('notifications-list');
  const unread = container.querySelectorAll('.dropdown-item[data-read="false"]');
  const counter = dropdown.querySelector('#notification-count');
  counter.textContent = unread.length;
  if (unread.length > 0) {
    counter.style['background-color'] = '#dc3545';
  }
}


String.prototype.format = function(kwargs) {
  return text.replace(templatedWords, function(wholeMatch, identifier) {
    const isReplacementExists = Object.keys(kwargs).includes(identifier);
    return isReplacementExists ? kwargs[identifier] : identifier;
  });
}


window.escapeUnicode = escapeUnicode;

window.addEventListener('load', () => {
  updateNotificationsCount();
});
