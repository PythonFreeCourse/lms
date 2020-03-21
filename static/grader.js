function sendComment(kind, exerciseId, line, commentData) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/comments/add/', true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = () => {
    if (xhr.readyState === 4) {
      if (xhr.status === 200) {
        console.log(xhr.responseText);
      } else {
        console.log(xhr.status);
      }
    }
  };

  xhr.send(
    JSON.stringify({
      exercise: exerciseId,
      line,
      comment: commentData,
      kind, // Should be 'text' or 'id'
    }),
  );
}


function sendNewComment(exerciseId, line, commentText) {
  return sendComment('text', exerciseId, line, commentText);
}


function sendExistsComment(exerciseId, line, commentId) {
  return sendComment('id', exerciseId, line, commentId);
}


function trackDragAreas(items) {
  const exerciseId = document.getElementById('code-view').dataset.id;

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
      sendExistsComment(exerciseId, line, commentId);
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


window.addEventListener('lines-numbered', () => {
  trackDragAreas(document.getElementsByClassName('line'));
  trackDraggables(document.getElementsByClassName('known-comment'));
});
