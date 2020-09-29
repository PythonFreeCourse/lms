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
  const commentOpacity = (hover === true) ? '1' : '0';
  let parsedColor = hover;
  if (hover === true) {
    parsedColor = HOVER_LINE_STYLE;
  } else if (hover === false) {
    parsedColor = 'none';
  }
  lineTarget.style.border = parsedColor;
  addCommentTarget.style.opacity = commentOpacity;
}

function isUserGrader() {
  // Obviously should not be trusted security-wise
  return ['staff', 'administrator'].includes(sessionStorage.getItem('role'));
}

function formatCommentData(commentData) {
  let changedCommentText = `<span class="comment-author">${commentData.author_name}:</span> ${commentData.text}`;
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

function updateOpenedSpans(currentSpans, line) {
  /* Because we have each line wrapped in it's own span, we must close
   * all the opened spans in this specific line and re-open them in the next
   * line. This function help us to manage the state of open span tags.
   */
  let isCatching = false;
  let phrase = '';
  for (let i = 0; i < line.length; i += 1) {
    const c = line.length[i];
    if (c === '>') {
      isCatching = false;
      phrase = `<${phrase}>`;
      if (phrase === '</span>') {
        currentSpans.pop();
      } else if (phrase.startsWith('<span')) {
        currentSpans.push(phrase);
      }
      phrase = '';
    } else if (c === '<') {
      isCatching = true;
    } else if (isCatching) {
      phrase += c;
    }
  }
}

function addLineSpansToPre(items) {
  const openSpans = [];
  Array.from(items).forEach((item) => {
    const code = item.innerHTML.trim().split('\n');
    item.innerHTML = code.map(
      (line, i) => {
        let lineContent = openSpans.join('') + line;
        updateOpenedSpans(openSpans, line);
        lineContent += '</span>'.repeat(openSpans.length);
        const wrappedLine = `<span data-line="${i + 1}" class="line">${lineContent}</span>`;
        return wrappedLine;
      },
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
