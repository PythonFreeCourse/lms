const COMMENTED_LINE_COLOR = '#fac4c3';

function markLine(target, color) {
  if (target.dataset.marked === 'true') { return; }
  if (color === true) {
    color = COMMENTED_LINE_COLOR;
  } else if (color === false) {
    color = 'none';
  }
  target.style.background = color;
}

function addPopover(line, lineData) {
  const commentElement = $(`.line[data-line="${line}"]`);
  commentElement.popover({
    html: true,
    title: `שורה ${line}`,
    content: lineData,
    placement: 'left', // Actually right :P
  });
  commentElement[0].dataset.marked = true;
}

function createLineComments(comments) {
  groupedComments = {};
  comments.forEach((comment) => {
    if (groupedComments[comment.line] === undefined) {
      groupedComments[comment.line] = comment.text;
    } else {
      groupedComments[comment.line] += `<hr>${comment.text}`;
    }
  });
  return groupedComments;
}

function treatComments(comments) {
  comments = [{line: 5, text: 'הרצל אל תאכל כרובית בפיתה'}, {line: 5, text: "הרצל שוב פעם אכלת כרובית בפיתה. זו פעם מיליון שאני אומרת לך לא לאכול כרובית בפיתה!!!"}, {line: 20, text: "Hello"}]; // Mock data
  if (comments === undefined) {
    console.error('Probably bad xhr request');
    return;
  }
  const lineComments = createLineComments(comments);
  Object.keys(lineComments).forEach((line) => addPopover(line, lineComments[line]));
  $("[data-toggle=popover]").popover();
}


function pullComments(exerciseId, callback) {
  const url = `/comments/get/${exerciseId}`;
  var xhr = new XMLHttpRequest();

  xhr.onreadystatechange = function() {
    if (xhr.readyState === 4) {
      callback(xhr.response.json);
    }
  }

  xhr.open('GET', url, true);
  xhr.send('');
}


function addLineSpansToPre(items) {
  Array.from(items).map((item) => {
    item.innerHTML = item.innerHTML.split('\n').map((line, i) => {
      return `<span data-line="${i + 1}" class="line"> ${line}</span>`;
    }).join('\n');
  });
  window.dispatchEvent(new Event('lines-numbered'));
}


window.addEventListener('load', (event) => {
  const exerciseId = 1; //  TODO: Get exercise id from URL
  addLineSpansToPre(document.getElementsByTagName('pre'));
  pullComments(exerciseId, treatComments);
});
