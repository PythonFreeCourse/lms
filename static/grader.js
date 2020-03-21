function sendComment(kind, solutionId, line, commentData) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/comments/add/', true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = () => {
    if (xhr.readyState === 4) {
      if (xhr.status === 200) {
        window.addCommentToLine(line, commentData);
      } else {
        console.log(xhr.status);
      }
    }
  };

  xhr.send(
    JSON.stringify({
      solution: solutionId,
      line,
      comment: commentData,
      kind, // Should be 'text' or 'id'
    }),
  );
}


function sendNewComment(solutionId, line, commentText) {
  return sendComment('text', solutionId, line, commentText);
}


function sendExistsComment(solutionId, line, commentId) {
  return sendComment('id', solutionId, line, commentId);
}


function trackDragAreas(items) {
  const solutionId = document.getElementById('code-view').dataset.id;

  function findElementToMark(e) {
    const span = (e.target.nodeType === 3) ? e.target.parentNode : e.target;
    const target = span.closest('.line');
    return target;
  }

  Array.from(items).forEach((item) => {
    item.addEventListener('dragover', (e) => {
      e.preventDefault();
      window.markLine(findElementToMark(e), true);
    }, false);
    item.addEventListener('dragleave', (e) => {
      e.preventDefault();
      window.markLine(findElementToMark(e), false);
    }, false);
    item.addEventListener('dragenter', (e) => {
      e.preventDefault();
    }, false);
    item.addEventListener('mouseenter', (e) => {
      e.preventDefault();
      window.markLine(findElementToMark(e), true);
    }, false);
    item.addEventListener('mouseleave', (e) => {
      e.preventDefault();
      window.markLine(findElementToMark(e), false);
    }, false);
    item.addEventListener('drop', (e) => {
      e.preventDefault();
      const target = findElementToMark(e);
      const { line } = target.dataset;
      const commentId = e.dataTransfer.getData('text/plain');
      window.markLine(target, false);
      sendExistsComment(solutionId, line, commentId);
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


function trackTextArea(lineNumber) {
  const solutionId = document.getElementById('code-view').dataset.id;
  const target = `textarea[data-line='${lineNumber}']`;
  const popoverElement = `.grader-add[data-line='${lineNumber}']`;
  $(target).keypress((e) => {
    if (e.ctrlKey && e.keyCode === 13) {
      sendNewComment(solutionId, lineNumber, e.target.value);
      $(popoverElement).popover('hide');
    }
  });
}


function registerNewCommentPopover(element) {
  const lineNumber = element.dataset.line;
  $(element).popover({
    html: true,
    title: `הערה חדשה לשורה ${lineNumber}`,
    sanitize: false,
    content: `<textarea data-line='${lineNumber}'></textarea>`,
  });
  $(element).on('inserted.bs.popover', () => {
    trackTextArea(lineNumber);
  });
}


function addNewCommentButtons(elements) {
  Array.from(elements).forEach((item, lineNumber) => {
    const newNode = document.createElement('span');
    newNode.className = 'grader-add';
    newNode.dataset.line = lineNumber + 1;
    newNode.innerHTML = '<i class="fa fa-plus" aria-hidden="true"></i>';
    item.parentNode.insertBefore(newNode, item);
    registerNewCommentPopover(newNode);
  });
  $('[data-toggle=popover]').popover();
}


window.addEventListener('lines-numbered', () => {
  trackDragAreas(document.getElementsByClassName('line'));
  trackDraggables(document.getElementsByClassName('known-comment'));
  addNewCommentButtons(document.getElementsByClassName('line'));
});
