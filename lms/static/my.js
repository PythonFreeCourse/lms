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


function shareSolution(solutionId, isShared, sharedByUser, button, getLinkButton) {
  const element = document.getElementById('share-solution');
  button.style.display = (isShared == 'True') ? 'block' : 'none';
  getLinkButton.style.display = (sharedByUser == 'True') ? 'block' : 'none';
  button.addEventListener('click', () => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/share');
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.responseType = 'json';
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          if (xhr.response.shared) {
            element.style['color'] = clickedColor;
            getLinkButton.style.display = 'block';
          } else {
            element.style['color'] = notClickedColor;
            getLinkButton.style.display = 'none';
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
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/share-link');
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.responseType = 'json';
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          const balloonText = document.getElementById('shared-link-text');
          const fullLink = window.location.host + '/shared-solution/' + xhr.response.shared_link;
          navigator.clipboard.writeText(fullLink);
          balloonText.style.visibility = 'visible';
          setTimeout(function() {
            balloonText.style.visibility = 'hidden';
          }, 1000);
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
  const getLinkButton = document.getElementById('get-shared-link');
  const solutionId = codeElement.id;
  const shared = codeElement.shared;
  const sharedByUser = codeElement.user_shared;
  updateNotificationsBadge();
  trackReadAllNotificationsButton(document.getElementById('read-notifications'));
  trackCopyCodeButton(document.getElementById('copy-button'));
  shareSolution(solutionId, shared, sharedByUser, document.getElementById('solution-link'), getLinkButton);
  trackShareButton(getLinkButton);
});
