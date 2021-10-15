function sendComment(kind, fileId, line, commentData) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/comments');
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.responseType = 'json';
  xhr.onreadystatechange = () => {
    if (xhr.readyState === 4) {
      if (xhr.status === 200) {
        const response = JSON.parse(window.escapeUnicode(xhr.response));
        window.addCommentToLine(line, response);
      } else {
        console.log(xhr.status);
      }
    }
  };

  xhr.send(
    JSON.stringify({
      act: 'create',
      comment: commentData,
      kind, // Should be 'text' or 'id'
      line,
      fileId,
    }),
  );
}

function visuallyRemoveComment(commentId) {
  const commentElement = document.querySelector(`.grader-delete[data-commentid="${commentId}"]`).closest('.comment');
  const lineElement = document.querySelector(`.line[data-line="${commentElement.dataset.line}"]`);
  const existingPopover = bootstrap.Popover.getInstance(lineElement);
  const hr = commentElement.nextElementSibling || commentElement.previousElementSibling;
  if (hr === null) {
    lineElement.dataset.marked = false;
    window.markLine(lineElement, 'none');
    const popover = bootstrap.Popover.getInstance(lineElement);
    if (popover !== null) {
      popover.dispose();
    }
  } else {
    let removeContent = `<hr>${commentElement.outerHTML}`;
    if (!existingPopover._config.content.includes(removeContent)) {
      removeContent = `${commentElement.outerHTML} <hr>`;
    }
    existingPopover._config.content = existingPopover._config.content.replace(removeContent, '');
    const commentParent = commentElement.parentNode;
    hr.parentNode.removeChild(hr);
    commentParent.removeChild(commentElement);
    const lastAuthorRole = commentParent.lastChild.previousElementSibling.dataset.authorRole;
    const newLineColor = window.getLineColorByRole(lastAuthorRole);
    window.markLine(lineElement, newLineColor, true);
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
    let lineTarget = span.closest('.line');
    let addCommentTarget = span.closest('.grader-add');
    const codeView = document.querySelector('#code-view');
    if (lineTarget === null || addCommentTarget !== null) {
      const commentLine = addCommentTarget.dataset.line;
      lineTarget = codeView.querySelector(`.line[data-line="${commentLine}"]`);
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

function focusTextArea(lineNumber) {
  const target = document.querySelector(`textarea[data-line='${lineNumber}']`);
  target.focus({preventScroll: true});
}

function trackTextArea(lineNumber) {
  const target = `textarea[data-line='${lineNumber}']`;
  const popoverElement = document.querySelector(`.grader-add[data-line='${lineNumber}']`);
  document.querySelector(target).addEventListener('keydown', (ev) => {
    if ((ev.which === 10 || ev.which === 13) && ev.ctrlKey) { // CTRL + ENTER
      sendNewComment(window.fileId, lineNumber, ev.target.value);
    } else if (ev.key === 'Escape') {
      ev.preventDefault();
    } else {
      return;
    }

    const popover = bootstrap.Popover.getInstance(popoverElement);
    if (popover !== null) {popover.hide();}
  });
}

function registerNewCommentPopover(element) {
  const lineNumber = element.dataset.line;
  const addCommentString = 'הערה חדשה לשורה';
  const popover = new bootstrap.Popover(element, {
    html: true,
    title: `${addCommentString} ${lineNumber}`,
    sanitize: false,
    content: `<textarea data-line='${lineNumber}'></textarea>`,
  });
  element.addEventListener('inserted.bs.popover', () => {
    trackTextArea(lineNumber);
    focusTextArea(lineNumber);
  });
  return popover;
}

function addNewCommentButtons(elements) {
  Array.from(elements).forEach((item) => {
    const newNode = document.createElement('span');
    newNode.className = 'grader-add';
    newNode.dataset.line = item.dataset.line;
    newNode.innerHTML = '<i class="fa fa-plus-square"></i>';
    item.parentNode.insertBefore(newNode, item);
    registerNewCommentPopover(newNode);
  });
}

window.deleteComment = deleteComment;
window.sendExistsComment = sendExistsComment;
window.addEventListener('lines-numbered', () => {
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
