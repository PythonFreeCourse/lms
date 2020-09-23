const templatedWords = /\$\{(\w+?)\}/g;
const style = getComputedStyle(document.documentElement);
const badColor = style.getPropertyValue('--danger');
const naturalColor = style.getPropertyValue('--secondary');



function escapeUnicode(str) {
  // Thanks to https://stackoverflow.com/a/45315988
  const json = JSON.stringify(str);
  return json.replace(/[\u007F-\uFFFF]/g, (chr) => {
    const step1 = chr.charCodeAt(0).toString(16);
    const step2 = `0000${step1}`.substr(-4);
    return `\\u${step2}`;
  });
}


function shareSolution(solutionId, isShared, element) {
  element.checked = (isShared == 'True');
  element.addEventListener('click', () => {
    const shareButton = document.getElementById('share-solution');
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/share');
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.responseType = 'json';
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          const response = JSON.parse(window.escapeUnicode(xhr.response))
          if (element.checked) {
            shareButton.style.display = 'block';
          } else {
            shareButton.style.display = 'none';
          }
        } else {
          console.log(xhr.status);
        }
      }
    };

    xhr.send(JSON.stringify({
      solutionId,
    }));
  });
}


function trackCopyCodeButton(button) {
  button.addEventListener('click', () => {
    const copyText = document.getElementById('user-code');
    const last = button.innerHTML;
    navigator.clipboard.writeText(copyText.textContent);
    button.innerHTML = 'Copied!';
    setTimeout(function() {
        button.innerHTML = last;
    }, 2000);
  });
}


function trackShareButton(button) {
  button.addEventListener('click', () => {
    const lastColor = button.style['color'];
    const refLink = window.location.host + '/shared-solution/' + window.location.pathname.split('/')[2];
    const balloonText = document.getElementById('shared-link-text');
    navigator.clipboard.writeText(refLink);
    button.style['color'] = '#007bff';
    balloonText.style.visibility = 'visible';
    setTimeout(function() {
      button.style['color'] = lastColor;
      balloonText.style.visibility = 'hidden';
    }, 1000);
  });
}


function updateNotificationsBadge() {
  const dropdown = document.getElementById('navbarNavDropdown');
  const container = document.getElementById('notifications-list');
  const unread = container.querySelectorAll('.dropdown-item[data-read="false"]');
  const counter = dropdown.querySelector('#notification-count');
  const bgColor = (unread.length > 0) ? badColor : naturalColor;
  counter.textContent = unread.length;
  counter.style['background-color'] = bgColor;
}


function sendReadAllNotificationsRequest() {
  const request = new XMLHttpRequest();
  request.open('PATCH', '/read');
  return request.send();
}


function trackReadAllNotificationsButton(button) {
  button.addEventListener('click', () => {
    sendReadAllNotificationsRequest();
    const notifications = document.querySelectorAll('.dropdown-item[data-read="false"]');
    Array.from(notifications).forEach((notification) => {
      notification.dataset.read = 'true';
    });
    updateNotificationsBadge();
  });
}


String.prototype.format = function(kwargs) {
  return text.replace(templatedWords, function(wholeMatch, identifier) {
    const isReplacementExists = Object.keys(kwargs).includes(identifier);
    return isReplacementExists ? kwargs[identifier] : identifier;
  });
}


window.escapeUnicode = escapeUnicode;

window.addEventListener('load', () => {
  const codeElement = document.getElementById('code-view').dataset
  const solutionId = codeElement.id;
  const shared = codeElement.shared;
  updateNotificationsBadge();
  trackReadAllNotificationsButton(document.getElementById('read-notifications'));
  trackCopyCodeButton(document.getElementById('copy-button'));
  shareSolution(solutionId, shared, document.getElementById('toggle'));
  trackShareButton(document.getElementById('solution-link'));
});
