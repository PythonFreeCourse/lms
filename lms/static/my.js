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

function sendShareRequest(act, solutionId, callback) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/share');
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.responseType = 'json';

  xhr.onreadystatechange = () => { callback(xhr); };

  xhr.send(
    JSON.stringify({ act, solutionId }),
  );
  return xhr;
}

function trackCopyButton(button, context) {
  button.addEventListener('click', () => {
    navigator.clipboard.writeText(context);
  });
}

function hideShareLink(xhr) {
  const shareBox = document.getElementById('share-box');
  if (xhr.readyState === 4) {
    if (xhr.status === 200) {
      shareBox.classList.add('d-none');
    } else {
      console.log(xhr.status);
    }
  }
}

function updateShareLink(xhr) {
  const shareBox = document.getElementById('share-box');
  const shareText = document.getElementById('share-text');
  if (xhr.readyState === 4) {
    if (xhr.status === 200) {
      if (shareBox.classList.contains('d-none')) {
        const link = `${window.location.origin}/shared/${xhr.response.share_link}`;
        const linkTextbox = document.getElementById('shareable-link');
        linkTextbox.value = link;
        linkTextbox.size = link.length;
        shareBox.classList.remove('d-none');
        trackCopyButton(document.getElementById('copy-link'), link);
      } else {
        hideShareLink(xhr);
      }
      shareText.querySelector('i').className = 'fa fa-share-alt';
    } else {
      console.log(xhr.status);
    }
  }
}

function trackShareSolution(solutionId, button) {
  button.addEventListener('click', () => {
    button.querySelector('i').className = 'fa fa-spinner fa-pulse';
    sendShareRequest('get', solutionId, updateShareLink);
  });
}

function trackDisableShareButton(solutionId, button) {
  button.addEventListener('click', () => {
    sendShareRequest('delete', solutionId, hideShareLink);
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

function getPostUploadMessage() {
  const myDropzone = Dropzone.forElement('#demo-upload');
  const feedbacks = document.getElementById('upload-feedbacks');
  const matchesSpan = document.getElementById('upload-matches');
  const missesSpan = document.getElementById('upload-misses');
  myDropzone.on('success', function() {
    const uploadStatus = Array.from(arguments).slice(1)[0];
    postUploadMessageUpdate(feedbacks, uploadStatus, matchesSpan, missesSpan);
  });
}

function postUploadMessageUpdate(feedbacks, uploadStatus, matchesSpan, missesSpan) {
  const matches = uploadStatus['exercise_matches'];
  const misses = uploadStatus['exercise_misses'];
  if (!feedbacks.classList.contains('feedback-hidden')) {
    feedbacks.classList.add('feedback-hidden');
  }
  matchesSpan.innerText += matches.length ? `${matches},` : '';
  missesSpan.innerText += misses.length ? `${misses},` : '';
  feedbacks.classList.add('feedback-transition');
  feedbacks.clientWidth;  // Forces layout to ensure the transition
  feedbacks.classList.remove('feedback-hidden');
  feedbacks.addEventListener('transitionend', function() {
    feedbacks.classList.remove('feedback-transition');
  });
}

window.escapeUnicode = escapeUnicode;

window.addEventListener('load', () => {
  updateNotificationsBadge();
  trackReadAllNotificationsButton(document.getElementById('read-notifications'));
  const codeElement = document.getElementById('code-view')
  if (codeElement !== null) {
    const codeElementData = codeElement.dataset;
    const solutionId = codeElementData.id;
    const userCode = document.getElementById('user-code').textContent;
    trackCopyButton(document.getElementById('copy-button'), userCode);
    trackShareSolution(solutionId, document.getElementById('share-action'));
    trackDisableShareButton(solutionId, document.getElementById('cancel-share'));
  }
  if (document.getElementById('demo-upload') !== null) {
    getPostUploadMessage();
  }
});
