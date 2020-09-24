const DEFAULT_COMMENTED_LINE_COLOR = '#fab3b0';
const FLAKE_COMMENTED_LINE_COLOR = '#fac4c3';
const HOVER_LINE_STYLE = '1px solid #0d0d0f';


function markLine(target, color) {
  if (target.dataset && target.dataset.marked === 'true') { return; }
  if (target.dataset && target.dataset.vimbackground === 'true') { return; }
  target.style.background = color;
}

function hoverLine(targets, hover) {
  const [lineTarget, addCommentTarget] = targets;
  if (lineTarget.dataset && lineTarget.dataset.vimbackground === 'true') { return; }
  let parsedColor = (
    (hover === true) ? HOVER_LINE_STYLE :
      (hover === false ? 'none' : hover)
  )
  let commentOpacity = (hover === true) ? '1' : '0';
  lineTarget.style.border = parsedColor;
  addCommentTarget.style.opacity = commentOpacity;
}

function isUserGrader() {
  // Obviously should not be trusted security-wise
  return ['staff', 'administrator'].includes(sessionStorage.getItem('role'));
}

function formatCommentData(commentData) {
  let changedCommentText = commentData.text;
  changedCommentText = `<span class="comment-author">${commentData.author_name}:</span> ${commentData.text}`
  if (isUserGrader()) {
    const deleteButton = `<i class="fa fa-trash grader-delete" aria-hidden="true" data-commentid="${commentData.id}" onclick="deleteComment(${window.fileId}, ${commentData.id});"></i>`;
    changedCommentText = `${deleteButton} ${changedCommentText}`;
  }
  return changedCommentText;
}

function addCommentToLine(line, commentData) {
  const commentElement = $(`.line[data-line="${line}"]`);
  const existingPopover = $(commentElement).data('bs.popover');
  const formattedComment = formatCommentData(commentData);
  const commentText = `<span class="comment" data-line="${line}" data-commentid="${commentData.id}">${formattedComment}</span>`;
  if (existingPopover !== undefined) {
    const existingContent = `${existingPopover.config.content} <hr>`;
    existingPopover.config.content = existingContent + commentText;
  } else {
    commentElement.popover({
      html: true,
      title: `שורה ${line}`,
      content: commentText,
      sanitize: false,
      boundary: 'viewport',
      placement: 'auto',
    });
    $(commentElement).popover();
  }
  if (commentData.is_auto) {
      markLine(commentElement[0], FLAKE_COMMENTED_LINE_COLOR);
  } else {
    markLine(commentElement[0], DEFAULT_COMMENTED_LINE_COLOR);
    commentElement[0].dataset.marked = true;
  }
}

function treatComments(comments) {
  if (comments === undefined) {
    console.error('Probably bad xhr request');
    return;
  }
  comments.forEach((entry) => {
    addCommentToLine(entry.line_number, entry);
  });
}


function pullComments(fileId, callback) {
  const url = `/comments?act=fetch&fileId=${fileId}`;
  const xhr = new XMLHttpRequest();

  xhr.onreadystatechange = () => {
    if (xhr.readyState === 4) {
      callback(JSON.parse(xhr.response));
    }
  };

  xhr.open('GET', url, true);
  xhr.send('');
}


function countOpenedSpans(line) {
  const spansOpenCount = (line.match(/\<span/g) || []).length;
  const spansCloseCount = (line.match(/\<\/span\>/g) || []).length;
  return spansOpenCount - spansCloseCount;
}


function addLineSpansToPre(items) {
  let spansOpened = 0;
  Array.from(items).forEach((item) => {
    const code = item.innerHTML.trim().split('\n');
    item.innerHTML = code.map(
      (line, i) => {
        const optionalOpening = (spansOpened === 0) ? `<span data-line="${i + 1}" class="line">` : '';
        spansOpened += countOpenedSpans(line);
        const optionalClosing = (spansOpened === 0) ? '</span>' : '';
        const newLine = `${optionalOpening}${line}${optionalClosing}`;
        return newLine;
      }
    ).join('\n');
  });
  window.dispatchEvent(new Event('lines-numbered'));
}


window.markLink = markLine;
window.hoverLine = hoverLine;
window.addCommentToLine = addCommentToLine;
window.isUserGrader = isUserGrader;
window.addEventListener('load', () => {
  const codeElement = document.getElementById('code-view').dataset;
  window.solutionId = codeElement.id;
  window.fileId = codeElement.file;
  sessionStorage.setItem('role', codeElement.role);
  addLineSpansToPre(document.getElementsByTagName('code'));
  pullComments(window.fileId, treatComments);
});
