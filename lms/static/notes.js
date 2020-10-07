function visuallyRemoveNote(noteId) {
  const noteElement = document.querySelector(`.grader-delete[data-noteid="${noteId}"]`).closest('.note');
  const notesElement = document.getElementById('notes-user');
  const removeContent = `${noteElement.outerHTML}`;
  notesElement.outerHTML = notesElement.outerHTML.replace(removeContent, '');
  notesElement.removeChild(noteElement);
}

function deleteNote(userId, noteId) {
  const xhr = new XMLHttpRequest();
  const url = `/notes?act=delete&userId=${userId}&noteId=${noteId}`;
  xhr.open('GET', url, true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.responseType = 'json';
  xhr.onreadystatechange = () => {
    if (xhr.readyState === 4) {
      if (xhr.status === 200) {
        visuallyRemoveNote(noteId);
        window.trackDeleteNotes(document.querySelectorAll('.grader-delete'));
      } else {
        console.log(xhr.status);
      }
    }
  };

  xhr.send('');
}

function trackDeleteNotes(deleteElements) {
  Array.from(deleteElements).forEach((item) => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      deleteNote(window.userId, item.dataset.noteid);
    }, true);
  });
}

window.trackDeleteNotes = trackDeleteNotes;
window.addEventListener('load', () => {
  const userData = document.getElementById('page-user').dataset;
  window.userId = userData.user;
  sessionStorage.setItem('role', userData.role);
  trackDeleteNotes(document.querySelectorAll('.grader-delete'));
});
