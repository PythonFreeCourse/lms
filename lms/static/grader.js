function sendComment(kind, fileId, line, commentData) {
  return new Promise((resolve, _reject) => {
    fetch('/comments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        act: 'create',
        comment: commentData,
        kind, // Should be 'text' or 'id'
        line,
        fileId,
      }),
    })
    .then(response => {
      if (!response.ok) {
        console.log(response.status);
        resolve(false);
      } else {
        return response.json();
      }
    })
    .then(data => {
      if (data) {
        window.addCommentToLine(line, JSON.parse(window.escapeUnicode(data)));
        resolve(true);
      }
    })
    .catch(error => {
      console.error('Error sending comment:', error);
      resolve(false);
    });
  });
}

function visuallyRemoveComment(commentId) {
  const commentElement = document.querySelector(`comment-line[data-comment-id='${commentId}']`);
  const commentsContainer = commentElement.parentElement;
  const lineNumber = commentsContainer.dataset.line;
  commentElement.remove();
  if (commentsContainer.children.length === 0) {
    commentsContainer.remove();
    const lineContainer = document.querySelector(`.line-container[data-line='${lineNumber}']`);
    removeMark(lineContainer);
  }
}

function deleteComment(fileId, commentId) {
  const xhr = new XMLHttpRequest();
  const url = `/comments?act=delete&fileId=${fileId}&commentId=${commentId}`;
  xhr.open('GET', url, true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.responseType = 'json';
  xhr.onreadystatechange = () => {
    if (xhr.readyState === 4) {
      if (xhr.status === 200) {
        visuallyRemoveComment(commentId);
      } else {
        console.log(xhr.status);
      }
    }
  };

  xhr.send('');
}

function sendNewComment(...commentData) {
  return sendComment('text', ...commentData);
}

function sendExistsComment(...commentData) {
  return sendComment('id', ...commentData);
}

function trackDragAreas(lineItems, addCommentItems) {
  function findElementsToMark(e) {
    const span = (e.target.nodeType === 3) ? e.target.parentNode : e.target;
    let lineTarget = span.closest('.line-container');
    let addCommentTarget = span.closest('.grader-add');
    const codeView = document.querySelector('#code-view');
    if (lineTarget === null || addCommentTarget !== null) {
      const commentLine = addCommentTarget.dataset.line;
      lineTarget = codeView.querySelector(`.line-container[data-line="${commentLine}"]`);
    } else {
      const commentLine = lineTarget.dataset.line;
      addCommentTarget = codeView.querySelector(`.grader-add[data-line="${commentLine}"]`);
    }
    return [lineTarget, addCommentTarget];
  }

  Array.from(lineItems).concat(Array.from(addCommentItems)).forEach((item) => {
    item.addEventListener('dragover', (e) => {
      e.preventDefault();
      window.hoverLine(findElementsToMark(e), true);
    }, false);
    item.addEventListener('dragleave', (e) => {
      e.preventDefault();
      window.hoverLine(findElementsToMark(e), false);
    }, false);
    item.addEventListener('dragenter', (e) => {
      e.preventDefault();
    }, false);
    item.addEventListener('mouseenter', (e) => {
      e.preventDefault();
      window.hoverLine(findElementsToMark(e), true);
    }, false);
    item.addEventListener('mouseleave', (e) => {
      e.preventDefault();
      window.hoverLine(findElementsToMark(e), false);
    }, false);
    item.addEventListener('drop', (e) => {
      e.preventDefault();
      const targets = findElementsToMark(e);
      const {line} = targets[0].dataset;
      const commentId = e.dataTransfer.getData('text/plain');
      window.hoverLine(targets, false);
      sendExistsComment(window.fileId, line, commentId);
    }, false);
  });
}

function trackDraggables(elements) {
  Array.from(elements).forEach((item) => {
    item.addEventListener('dragstart', (e) => {
      e.dataTransfer.setData('text/plain', e.target.dataset.commentid);
    });
  });
}


function createEditor(textarea, solutionId, lineNumber) {
  return new EasyMDE({
    autofocus: true,
    autosave: {
      enabled: true,
      uniqueId: `${solutionId}-${lineNumber}`,
    },
    element: textarea,
    direction: document.documentElement.dir,
    spellChecker: false,
    previewClass: ["editor-preview", document.documentElement.dir],
  });
}

function trackCommentSendControllers(
  editor, controllers, fileId, lineNumber, creationTracker,
) {
  const submitButton = controllers.querySelector('.send-comment');
  const cancelButton = controllers.querySelector('.cancel-comment');
  const commentContainer = submitButton.closest('.comments-container');
  const commentsAdder = commentContainer.querySelector('.comments-adder-container');

  function clearElements() {
    commentsAdder.remove();
    editor.element.remove();
    if (commentContainer.children.length === 0) {
      commentContainer.remove();
    }
    editor.cleanup();
  }

  commentsAdder.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      submitButton.click();
    }
  });

  commentsAdder.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      cancelButton.click();
    }
  });

  submitButton.addEventListener('click', () => {
    submitButton.disabled = true;
    const commentData = editor.value();
    sendNewComment(fileId, lineNumber, commentData).then((_) => {
      editor.clearAutosavedValue();
    });
    clearElements();
    creationTracker.delete(lineNumber);
  }, { once: true });

  cancelButton.addEventListener('click', () => {
    clearElements();
    creationTracker.delete(lineNumber);
  }, { once: true });
}
  

function openNewCommentArea(element, content) {
  const created = new Set();
  const currentText = content || "";

  element.addEventListener('click', () => {
    const lineElement = element.closest('.line-container');
    const lineNumber = lineElement.dataset.line;
    const fileId = window.fileId;
    if (created.has(lineNumber)) {
      return;
    }

    comments = getCommentsContainer(lineNumber);
    const newCommentArea = `
      <div class="comments-adder-container">
        <textarea data-line="${lineNumber}">${currentText}</textarea>
        <div class="comment-buttons">
          <button class="btn btn-success send-comment">${_("Submit")}</button>
          <button class="btn btn-danger cancel-comment">${_("Cancel")}</button>
        </div>
      </div>
    `;
    comments.insertAdjacentHTML('beforeend', newCommentArea);

    const newTextarea = comments.querySelector('textarea');
    editor = createEditor(newTextarea, fileId, lineNumber);

    const controllers = comments.querySelector('.comment-buttons');
    trackCommentSendControllers(editor, controllers, fileId, lineNumber, created);

    created.add(lineNumber);
  });
}

function addNewCommentButtons(elements) {
  Array.from(elements).forEach((item) => {
    const newNode = document.createElement('span');
    newNode.className = 'grader-add';
    newNode.dataset.line = item.dataset.line;
    newNode.innerHTML = '<i class="fa fa-plus-square"></i>';
    item.parentNode.insertBefore(newNode, item);
    openNewCommentArea(newNode);
  });
}

window.deleteComment = deleteComment;
window.sendExistsComment = sendExistsComment;
window.addEventListener('fully-loaded', () => {
  const codeView = document.getElementById('code-view');
  const lineItems = codeView.getElementsByClassName('line');
  addNewCommentButtons(lineItems);
  const addCommentItems = codeView.querySelectorAll('.grader-add');
  trackDragAreas(lineItems, addCommentItems);
  trackDraggables(document.getElementsByClassName('known-comment'));
  if (!window.isUserGrader()) {
    sessionStorage.setItem('role', 'grader');
  }
});
