function rephraseNotification(notification) {
  const text = (
    notification.text
  );
  return {
    id: notification.id,
    text: notification.text.format(notification.parameters),
    date: notification.date,
  }
}


function parseNotifications(notifications) {
  const container = document.getElementById('notifications-list');
  const template = document.getElementById('notification');
  rephrasedNotifications.map(rephraseNotification).forEach((notification) => {
    let clone = template.content.cloneNode(true);
    clone.querySelector('.notification').dataset.id = notification.id;
    clone.querySelector('.notification-icon').textContent = notification.icon;
    clone.querySelector('.notification-text').textContent = notification.text;
    clone.querySelector('.notification-date').textContent = notification.date;
  });
}


function getNotifications() {
  const xhr = new XMLHttpRequest();
  xhr.open('GET', '/notifications');
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.responseType = 'json';
  xhr.onreadystatechange = () => {
    if (xhr.readyState === 4) {
      if (xhr.status === 200) {
        const response = JSON.parse(window.escapeUnicode(xhr.response));
        parseNotifications(response);
      } else {
        console.log(xhr.status);
      }
    }
  };

  xhr.send('');
}


window.addEventListener('load', () => {
  document.getElementById('notifications-icon').addEventListener('click', (e) => {
    getNotifications();
  });
});
