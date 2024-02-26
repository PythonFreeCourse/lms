const DEFAULT_COMMENTED_LINE_COLOR = '#fab3b0';
const STUDENT_COMMENTED_LINE_COLOR = '#a9f6f9';
const FLAKE_COMMENTED_LINE_COLOR = '#fac4c3';
const HOVER_LINE_STYLE = '1px solid #0d0d0f';

function markLine(target, color, deletion = false) {
  if (target.dataset && target.dataset.marked === 'true' && !deletion) {return;}
  if (target.dataset && target.dataset.vimbackground === 'true' && !deletion) {return;}
  target.style.background = color;
}

function hoverLine(targets, hover) {
  const [lineTarget, addCommentTarget] = targets;
  if (lineTarget.dataset && lineTarget.dataset.vimbackground === 'true') {return;}
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

function isSolverComment(commentData) {
  const authorIsSolver = commentData.author_name === sessionStorage.getItem('solver');
  const allowedComment = sessionStorage.getItem('allowedComment') === 'true';
  return (authorIsSolver && allowedComment);
}

function formatCommentData(commentData) {
  const commentText = DOMPurify.sanitize(marked.parse(commentData.text));
  let changedCommentText = `<span class="comment-author">${commentData.author_name}:</span> ${commentText}`;
  if (window.isUserGrader() || isSolverComment(commentData)) {
    const deleteButton = `<i class="fa fa-trash grader-delete" aria-hidden="true" data-commentid="${commentData.id}" onclick="deleteComment(${window.fileId}, ${commentData.id});"></i>`;
    changedCommentText = `${deleteButton} ${changedCommentText}`;
  }
  return changedCommentText;
}

function addCommentToLine(line, commentData) {
  const commentElement = document.querySelector(`.line-container[data-line="${line}"]`);
  const formattedComment = formatCommentData(commentData);
  const commentText = `<span class="comment" data-line="${line}" data-commentid="${commentData.id}" data-author-role="${commentData.author_role}">${formattedComment}</span>`;
  let existingPopover = bootstrap.Popover.getInstance(commentElement);
  if (existingPopover !== null) {
    const existingContent = `${existingPopover._config.content} <hr>`;
    existingPopover._config.content = existingContent + commentText;
  } else {
    existingPopover = new bootstrap.Popover(commentElement, {
      html: true,
      title: `שורה ${line}`,
      content: commentText,
      sanitize: false,
      boundary: 'viewport',
      placement: 'auto',
    });

    commentElement.addEventListener('shown.bs.popover', function () {
      Prism.highlightAllUnder(existingPopover.tip);
    })
  }

  commentElement.dataset.comment = 'true';
  if ((commentData.is_auto) && (commentElement.dataset.marked !== 'true')) {
    markLine(commentElement, FLAKE_COMMENTED_LINE_COLOR);
  } else {
    const lineColor = window.getLineColorByRole(commentData.author_role);
    markLine(commentElement, lineColor, true);
    commentElement.dataset.marked = true;
  }

  return existingPopover;
}

function getLineColorByRole(authorRole) {
  return authorRole === 1 ? STUDENT_COMMENTED_LINE_COLOR : DEFAULT_COMMENTED_LINE_COLOR;
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
    const c = line[i];
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
    const digits = code.length.toString().length;
    item.innerHTML = code.map(
      (line, i) => {
        let lineContent = openSpans.join('') + line;
        updateOpenedSpans(openSpans, line);
        lineContent += '</span>'.repeat(openSpans.length);
        const wrappedLine = `<div class="line-container" data-line="${i + 1}"><span class="line-number" style="width: ${digits}em">${i + 1}</span> <span data-line="${i + 1}" class="line">${lineContent}</span></div>`;
        return wrappedLine;
      },
    ).join('\n');
  });
  window.dispatchEvent(new Event('lines-numbered'));
}

<<<<<<< HEAD
class LineComment extends HTMLElement {
  static observedAttributes = ['data-line', 'img-src', 'name', 'date'];

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    const template = document.getElementById('comment-template').content.cloneNode(true);
    this.shadowRoot.appendChild(template);
    this.updateComponent();
  }

  attributeChangedCallback(_, oldValue, newValue) {
    if (oldValue !== newValue) {
      this.updateComponent();
    }
  }

  updateComponent() {
    const img = this.shadowRoot.querySelector('.commenter-image');
    const name = this.shadowRoot.querySelector('.commenter-name');
    const dateElement = this.shadowRoot.querySelector('.comment-date');

    img.src = this.getAttribute('img-src') || '/static/avatar.jpg';
    img.alt = `${this.getAttribute('name')}'s profile picture`;
    name.textContent = this.getAttribute('name');

    const dateString = this.getAttribute('date');
    dateElement.textContent = this.formatDate(dateString);
    dateElement.setAttribute('datetime', this.formatDate(dateString));
  }

  formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
  }
}

function configureMarkdownParser() {
  marked.use({
    renderer: {
      code: (code, infoString, _) => {
        const language = infoString || 'plaintext';
        return `<pre><code class="language-${language}">${code}</code></pre>`;
      }
    },
  });
}

window.markLine = markLine;
window.hoverLine = hoverLine;
window.addCommentToLine = addCommentToLine;
window.getLineColorByRole = getLineColorByRole;
window.addEventListener('load', () => {
  const codeElementData = document.getElementById('code-view').dataset;
  window.solutionId = codeElementData.id;
  window.fileId = codeElementData.file;
  window.exerciseId = codeElementData.exercise;
  sessionStorage.setItem('role', codeElementData.role);
  sessionStorage.setItem('solver', codeElementData.solver);
  sessionStorage.setItem('allowedComment', codeElementData.allowedComment);
  customElements.define('line-comment', LineComment);
  configureMarkdownParser();
  addLineSpansToPre(document.getElementsByTagName('code'));
  pullComments(window.fileId, treatComments);
});
