const COMMENTED_LINE_COLOR = '#fac4c3';

function markLine(target, color) {
  if (target.dataset && target.dataset.marked === 'true') { return; }
  let parsedColor = color;
  if (color === true) {
    parsedColor = COMMENTED_LINE_COLOR;
  } else if (color === false) {
    parsedColor = 'none';
  }
  target.style.background = parsedColor;
}

function isUserGrader() {
  // Obviously should not be trusted security-wise
  return ['staff', 'administrator'].includes(sessionStorage.getItem('role'));
}

function addSpecialCommentButtons(commentData) {
  let changedCommentText = commentData.text;
  if (isUserGrader()) {
    const deleteButton = `<i class="fa fa-trash grader-delete" aria-hidden="true" data-commentid="${commentData.id}" onclick="deleteComment(${window.solutionId}, ${commentData.id});"></i>`;
    changedCommentText = `${deleteButton} ${commentData.text}`;
  }
  return changedCommentText;
}

function addCommentToLine(line, commentData) {
  const commentElement = $(`.line[data-line="${line}"]`);
  const existingPopover = $(commentElement).data('bs.popover');
  const buttonizedComment = addSpecialCommentButtons(commentData);
  const commentText = `<span class="comment" data-line="${line}" data-commentid="${commentData.id}">${buttonizedComment}</span>`;
  if (existingPopover !== undefined) {
    const existingContent = `${existingPopover.config.content} <hr>`;
    existingPopover.config.content = existingContent + commentText;
  } else {
    commentElement.popover({
      html: true,
      title: `שורה ${line}`,
      content: commentText,
      sanitize: false,
      placement: 'left', // Actually right :P
    });
    $(commentElement).popover();
    markLine(commentElement[0], true);
    commentElement[0].dataset.marked = true;
  }
}

function treatComments(comments) {
  /*
  comments = [
    { id: 1, line: 5, text: 'הרצל אל תאכל כרובית בפיתה' },
    { id: 2, line: 5, text: `הרצל שוב פעם אכלת כרובית בפיתה.
                             זו פעם מיליון שאני אומרת לך לא
                             לאכול כרובית בפיתה!!!` },
    { id: 3, line: 20, text: 'Hello' },
  ]; // Mock data */
  if (comments === undefined) {
    console.error('Probably bad xhr request');
    return;
  }
  comments.forEach((entry) => {
    addCommentToLine(entry.line_number, entry);
  });
}


function pullComments(solutionId, callback) {
  const url = `/comments?act=fetch&solutionId=${solutionId}`;
  const xhr = new XMLHttpRequest();

  xhr.onreadystatechange = () => {
    if (xhr.readyState === 4) {
      callback(JSON.parse(xhr.response));
    }
  };

  xhr.open('GET', url, true);
  xhr.send('');
}


function addLineSpansToPre(items) {
  Array.from(items).forEach((item) => {
    item.innerHTML = item.innerHTML.split('\n')
      .map((line, i) => `<span data-line="${i + 1}" class="line"> ${line}</span>`)
      .join('\n');
  });
  window.dispatchEvent(new Event('lines-numbered'));
}


window.markLink = markLine;
window.addCommentToLine = addCommentToLine;
window.isUserGrader = isUserGrader;
window.addEventListener('load', () => {
  const codeElement = document.getElementById('code-view').dataset;
  window.solutionId = codeElement.id;
  sessionStorage.setItem('role', codeElement.role);
  addLineSpansToPre(document.getElementsByTagName('code'));
  pullComments(window.solutionId, treatComments);
});
