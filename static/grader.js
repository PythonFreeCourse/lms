function trackDragAreas(items) {
  const exerciseId = document.getElementById('code-view').dataset.id;

  function _markLine(e, color) {
    let span = (e.target.nodeType == 3) ? e.target.parentNode : e.target;
    let target = span.closest('.line');
    markLine(target, color);
  }

  Array.from(items).forEach((item) => {
    item.addEventListener('dragover', (e) => {
      e.preventDefault();
      _markLine(e, true);
    }, false);
    item.addEventListener('dragleave', (e) => {
      e.preventDefault();
      _markLine(e, false);
    }, false);
    item.addEventListener('dragenter', (e) => {
      e.preventDefault();
    }, false);
    item.addEventListener('mouseenter', (e) => {
      e.preventDefault();
      _markLine(e, true);
    }, false);
    item.addEventListener('mouseleave', (e) => {
      e.preventDefault();
      _markLine(e, false);
    }, false);
    item.addEventListener('drop', (e) => {
      e.preventDefault()
      let span = (e.target.nodeType == 3) ? e.target.parentNode : e.target;
      let target = span.closest('.line');
      let line = target.dataset.line;
      let commentId = e.dataTransfer.getData('text/plain');
      _markLine(e, false);
      sendComment('id', exerciseId, line, commentId);
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


function sendComment(kind, exerciseId, line, commentData) {
  let xhr = new XMLHttpRequest();
  xhr.open("POST", '/comments/add/', true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = () => {
    if (xhr.readyState == 4) {
      if (xhr.status == 200) {
        console.log(xhr.responseText);
      } else {
        console.log(xhr.status);
      }
    }
  }

  xhr.send(
    JSON.stringify({
      exercise: exerciseId,
      line: line,
      comment: commentData,
      kind: kind,  // Should be 'text' or 'id'
    })
  );

}


function sendNewComment(exerciseId, line, commentText) {
  return sendComment('text', exerciseId, line, commentText);
}


function sendExistsComment(exerciseId, line, commentId) {
  return sendComment('id', exerciseId, line, commentId);
}


window.addEventListener('lines-numbered', (event) => {
  trackDragAreas(document.getElementsByClassName('line'));
  trackDraggables(document.getElementsByClassName('known-comment'));
});
