function trackDragAreas(items) {
  function markLine(e, color) {
      let span = (e.target.nodeType == 3) ? e.target.parentNode : e.target;
      let target = span.closest('.line');
      target.style.background = color;
  }


  Array.from(items).forEach((item) => {
    item.addEventListener('dragover', (e) => {
      markLine(e, '#fac4c3');
    }, false);
    item.addEventListener('dragleave', (e) => {
      markLine(e, 'none');
    }, false);
    item.addEventListener('dragover', (e) => {
      e.preventDefault(); 
      //markLine(e, 'none');
    }, false);
    item.addEventListener('dragenter', (e) => {
      e.preventDefault();
    }, false);
    item.addEventListener('drop', (e) => {
      e.preventDefault()
      let span = (e.target.nodeType == 3) ? e.target.parentNode : e.target;
      let target = span.closest('.line');
      let line = target.dataset.line;
      console.log(e.dataTransfer.getData('text/plain'));
      markLine(e, 'none');
    }, false);
  });
}


function trackDraggables(elements) {
  Array.from(elements).forEach((item) => {
    console.log(item);
    item.addEventListener('dragstart', (e) => {
      console.log(e.target.dataset.commentid);
      e.dataTransfer.setData('text/plain', e.target.dataset.commentid);
    });
  });
}


function sendComment(kind, exerciseId, line, commentData) {
  let xhr = new XMLHttpRequest();
  xhr.open("POST", '/add/comment/', true);
  xhr.setRequestHeader('Content-Type', 'application/json');
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


function drawComment(line, comment) {
}


function addLineSpansToPre(items) {
  Array.from(items).map((item) => {
    item.innerHTML = item.innerHTML.split('\n').map((line, i) => {
     return `<span data-line="${i + 1}" class="line"> ${line}</span>`;
    }).join('\n');
  });
}


window.onload = function(e) {
  let preElements = document.getElementsByTagName('pre');
  addLineSpansToPre(preElements);
  trackDragAreas(document.getElementsByClassName('line'));
  trackDraggables(document.getElementsByClassName('known-comment'));
}
