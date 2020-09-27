const templatedWords = /\$\{(\w+?)\}/g;
const style = getComputedStyle(document.documentElement);
const badColor = style.getPropertyValue('--danger');
const naturalColor = style.getPropertyValue('--secondary');
const clickedColor = '#007bff'
const notClickedColor = '#999'



function escapeUnicode(str) {
  // Thanks to https://stackoverflow.com/a/45315988
  const json = JSON.stringify(str);
  return json.replace(/[\u007F-\uFFFF]/g, (chr) => {
    const step1 = chr.charCodeAt(0).toString(16);
    const step2 = `0000${step1}`.substr(-4);
    return `\\u${step2}`;
  });
}


function shareSolution(solutionId, button) {
  const shareTextBox = document.getElementById('share-content-box');
  button.addEventListener('click', () => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/share');
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.responseType = 'json';
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          if (shareTextBox.style.display == 'block') {
            shareTextBox.style.display = 'none';
          } else {
            const link = window.location.host + '/shared/' + xhr.response.shared_link;
            document.getElementById('link-input').value = link;
            shareTextBox.style.display = 'block';
            trackCopyButton(document.getElementById('copy-link'), link);
          }
        } else {
          console.log(xhr.status);
        }
      }
    };

    xhr.send(
      JSON.stringify({
        'act': 'get',
        solutionId,
      }),
    );
  });
}


function trackDisableShareButton(button) {
  const shareTextBox = document.getElementById('share-content-box');
  button.addEventListener('click', () => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/share');
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.responseType = 'json';
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          shareTextBox.style.display = 'none';
        } else {
          console.log(xhr.status);
        }
      }
    };

    xhr.send(
      JSON.stringify({
        'act': 'delete',
        solutionId,
      }),
    );
  });
}


function trackCopyButton(button, context) {
  button.addEventListener('click', () => {
    navigator.clipboard.writeText(context);
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
  updateNotificationsBadge();
  trackReadAllNotificationsButton(document.getElementById('read-notifications'));
  trackCopyButton(document.getElementById('copy-button'), document.getElementById('user-code').textContent);
  shareSolution(solutionId, document.getElementById('solution-link'));
  trackDisableShareButton(document.getElementById('cancel-share'));
});
