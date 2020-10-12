function getPrivacyLevel(inputRange) {
  const options = window.notesOptions.split(',');
  const privacyText = document.getElementById('privacy-text');
  privacyText.innerText = options[inputRange.value];
  inputRange.addEventListener('change', () => {
    privacyText.innerText = options[inputRange.value];
  });
}

function formatNoteHeader(noteData) {
  let noteHeader = '<div class="card-header">';
  if (window.isUserGrader()) {
    const deleteButton = `<i class="fa fa-trash grader-delete" aria-hidden="true" data-noteid="${noteData.id}"></i>`;
    noteHeader += `${deleteButton}`;
  }
  noteHeader += `${noteData.timestamp}`;
  if (noteData.exercise) {
    noteHeader += ` - ${noteData.exercise}`;
  }
  return `${noteHeader}</div>`;
}

function formatNoteBody(noteData) {
  let title = `${noteData.fullname}`;
  title += (noteData.subject) ? ` - ${noteData.subject}` : '';
  return `<div class="card-body"><h5 class="card-title">${title}</h5><p class="card-text">${noteData.text}</p></div>`;
}

function addNoteToPage(noteData, notesElement) {
  const noteHeader = formatNoteHeader(noteData);
  const noteBody = formatNoteBody(noteData);
  notesElement.innerHTML += `<div class="note card" data-noteid="${noteData.id}" data-author-role="${noteData.fullname}">${noteHeader}${noteBody}</div>`;
}

function treatNotes(notes, notesElement) {
  if (notes === undefined) {
    console.error('Probably bad xhr request');
    return;
  }
  notes.forEach((entry) => {
    addNoteToPage(entry, notesElement);
  });
}

function trackAddNote(formElement) {
  formElement.addEventListener('submit', () => {
    const serializeData = new URLSearchParams(Array.from(new FormData(formElement))).toString();
    const xhr = new XMLHttpRequest();
    const url = `/notes/${window.userId}?act=create&${serializeData}`;
    xhr.open('POST', url);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.responseType = 'json';
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        if (xhr.status !== 200) {
          console.log(xhr.status);
        }
      }
    };

    xhr.send('');
  });
}

function visuallyRemoveNote(noteId) {
  const noteElement = document.querySelector(`.grader-delete[data-noteid="${noteId}"]`).closest('.note');
  const notesElement = document.getElementById('notes-user');
  const removeContent = `${noteElement.outerHTML}`;
  notesElement.outerHTML = notesElement.outerHTML.replace(removeContent, '');
  notesElement.removeChild(noteElement);
}

function deleteNote(userId, noteId) {
  const xhr = new XMLHttpRequest();
  const url = `/notes/${userId}?act=delete&noteId=${noteId}`;
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

function pullNotes(notesElement) {
  const url = `/notes/${window.userId}?act=fetch`;
  const xhr = new XMLHttpRequest();

  xhr.onreadystatechange = () => {
    if (xhr.readyState === 4) {
      treatNotes(JSON.parse(xhr.response), notesElement);
      trackDeleteNotes(document.querySelectorAll('.grader-delete'));
    }
  };

  xhr.open('GET', url, true);
  xhr.send('');
}

window.trackDeleteNotes = trackDeleteNotes;
window.addEventListener('load', () => {
  const userData = document.getElementById('page-user').dataset;
  window.userId = userData.user;
  sessionStorage.setItem('role', userData.role);
  window.notesOptions = userData.notesOptions;
  window.notesElement = document.getElementById('notes-user');
  pullNotes(window.notesElement);
  trackAddNote(document.getElementById('notes-form'));
  getPrivacyLevel(document.getElementById('note-privacy'));
});
