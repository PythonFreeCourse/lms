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

function addCommentToLine(line, commentData) {
  const commentElement = $(`.line[data-line="${line}"]`);
  const existingPopover = $(commentElement).data('bs.popover');
  if (existingPopover !== undefined) {
    const existingContent = `${existingPopover.config.content} <hr>`;
    existingPopover.config.content = existingContent + commentData;
  } else {
    commentElement.popover({
      html: true,
      title: `שורה ${line}`,
      content: commentData,
      placement: 'left', // Actually right :P
    });
    commentElement[0].dataset.marked = true;
  }
}

function treatComments(comments) {
  /* comments = [
     { line: 5, text: 'הרצל אל תאכל כרובית בפיתה' },
     { line: 5, text: `הרצל שוב פעם אכלת כרובית בפיתה.
                       זו פעם מיליון שאני אומרת לך לא
                       לאכול כרובית בפיתה!!!` },
     { line: 20, text: 'Hello' }
     ]; // Mock data */
  if (comments === undefined) {
    console.error('Probably bad xhr request');
    return;
  }
  comments.forEach((entry) => {
    addCommentToLine(entry.line, entry.text);
  });
  $('[data-toggle=popover]').popover();
}


function pullComments(exerciseId, callback) {
  const url = `/comments/get/${exerciseId}`;
  const xhr = new XMLHttpRequest();

  xhr.onreadystatechange = function () {
    if (xhr.readyState === 4) {
      callback(xhr.response.json);
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
window.addEventListener('load', () => {
  const exerciseId = 1; //  TODO: Get exercise id from URL
  addLineSpansToPre(document.getElementsByTagName('pre'));
  pullComments(exerciseId, treatComments);
});
