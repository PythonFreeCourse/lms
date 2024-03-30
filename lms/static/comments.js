const FLAKE_COMMENTED_LINE_COLOR = '#fac4c3';
const HOVER_LINE_COLOR = '#0d0d0f';


function removeMark(lineElement) {
  lineElement.classList.remove('marked');
  lineElement.style.background = 'none';
}


function markLine(target, deletion = false) {
  if (target.dataset && target.dataset.marked === 'true' && !deletion) {return;}
  if (target.dataset && target.dataset.vimbackground === 'true' && !deletion) {return;}
  target.classList.add('marked');
  target.style.background = FLAKE_COMMENTED_LINE_COLOR;
}


function hoverLine(targets, hover) {
  const [lineTarget, addCommentTarget] = targets;
  if (lineTarget.dataset && lineTarget.dataset.vimbackground === 'true') {return;}
  const commentOpacity = (hover === true) ? '1' : '0';
  const parsedColor = (hover === true) ? HOVER_LINE_COLOR : '';
  lineTarget.style.borderColor = parsedColor;
  addCommentTarget.style.opacity = commentOpacity;
}

function isSolverComment(commentData) {
  const authorIsSolver = commentData.author_name === sessionStorage.getItem('solver');
  const allowedComment = sessionStorage.getItem('allowedComment') === 'true';
  return (authorIsSolver && allowedComment);
}

function createCommentLine(commentData) {
  const commentLineElement = document.createElement('comment-line');
  const commentContent = DOMPurify.sanitize(marked.parse(commentData.text));

  commentAttributes = {
    'data-comment-id': commentData.id,
    'data-file-id': commentData.file_id,
    'data-line': commentData.line_number,
    'data-author-role': commentData.author_role,
    'data-is-auto': commentData.is_auto,
    'avatar': commentData.avatar,
    'name': commentData.author_name,
    'date': commentData.timestamp,
    'editor': window.isUserGrader() || isSolverComment(commentData),
  }

  for (const [key, value] of Object.entries(commentAttributes)) {
    commentLineElement.setAttribute(key, value);
  }

  commentLineElement.innerHTML = `<span class="comment-text">${commentContent}</span>`;

  return commentLineElement;
}

function getCommentsContainer(line) {
  let commentsContainer = document.querySelector(`.comments-container[data-line="${line}"]`);
  if (commentsContainer !== null) {
    return commentsContainer;
  }

  const lineContainer = document.querySelector(`.line-container[data-line="${line}"]`);
  commentsContainer = document.createElement('div');
  commentsContainer.classList.add('comments-container');
  commentsContainer.setAttribute('data-line', line);

  if (document.documentElement?.dir === 'rtl') {
    commentsContainer.classList.add('rtl');
  }

  lineContainer.insertAdjacentElement('afterend', commentsContainer);
  return commentsContainer;
}


function createToggledComment(lineElement, commentsContainer, authorRole) {
  if (lineElement.classList.contains('marked')) { return; }

  markLine(lineElement);

  commentsContainer.classList.add('d-none');
  lineElement.addEventListener('click', () => {
    commentsContainer.classList.toggle('d-none');
  });
}


function addCommentToLine(line, commentData) {
  const commentedLine = document.querySelector(`.line-container[data-line="${line}"]`);
  if (commentedLine === null) {
    console.error(`No line found for comment: ${commentData.id}`);
    return;
  }

  const commentsContainer = getCommentsContainer(line);
  const commentLine = createCommentLine(commentData);
  commentsContainer.appendChild(commentLine);
  Prism.highlightAllUnder(commentLine);

  if (commentLine.dataset.isAuto === "true") {
    createToggledComment(commentedLine, commentsContainer, commentData.author_role);
  }
  commentedLine.dataset.comment = 'true';

  return commentLine;
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

class LineComment extends HTMLElement {
  static observedAttributes = [
    'data-line', 'avatar', 'name', 'date', 'editor', 'data-comment-id',
    'data-file-id',
  ];

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    const template = document.getElementById('comment-template').content.cloneNode(true);
    this.shadowRoot.appendChild(template);
  }

  connectedCallback() {
    this.#trackEditButton();
    this.#trackDeleteButton();
    this.updateComponent();
  }

  #trackEditButton() {
    const editButton = this.shadowRoot.querySelector('.edit-btn');
    const commentId = this.getAttribute('data-comment-id');
    editButton.addEventListener('click', () => {
      window.location.href = `/comments/${commentId}/edit`;
    });
  }

  #trackDeleteButton() {
    const deleteButton = this.shadowRoot.querySelector('.delete-btn');

    const fileId = this.getAttribute('data-file-id');
    const commentId = this.getAttribute('data-comment-id');

    deleteButton.addEventListener('click', () => {
      deleteComment(fileId, commentId);
    });
  }

  attributeChangedCallback(_, oldValue, newValue) {
    if (oldValue !== newValue) {
      this.updateComponent();
    }
  }

  updateComponent() {
    const img = this.shadowRoot.querySelector('.commenter-image');
    const name = this.shadowRoot.querySelector('.commenter-name');
    const dateElement = this.shadowRoot.querySelector('.comment-date-text');
    const editDeleteBtns = this.shadowRoot.querySelector('.edit-delete-btns');

    img.src = this.getAttribute('avatar') || '/static/avatar.jpg';
    img.alt = `${this.getAttribute('name')}'s profile picture`;

    name.textContent = this.getAttribute('name');

    const dateString = this.getAttribute('date');
    dateElement.textContent = this.formatDate(dateString);
    dateElement.setAttribute('datetime', this.createDatetime(dateString));

    editDeleteBtns.style.display = 'none';
    if (this.getAttribute('editor') === 'true') {
      editDeleteBtns.style.display = 'flex';
    }
  }

  formatDate(dateString) {
    if (!dateString) return '';
    const lang = document.documentElement.lang;
    const date = new Date(dateString);
    const options = {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }
    return new Intl.DateTimeFormat(lang, options).format(date);
  }

  createDatetime(dateString) {
    const date = new Date(dateString);
    let year = date.getFullYear();
    let month = String(date.getMonth() + 1).padStart(2, '0'); // JS months are 0-based
    let day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
}

function configureMarkdownParser() {
  marked.use({
    renderer: {
      code: (code, infoString, _) => {
        const language = infoString || 'plaintext';
        return `<pre><code class="language-${language}">${code}</code></pre>`;
      },
      codespan: (code) => {
        const parsed = (
          code
          .replace(/&quot;/g, '"')
          .replace(/&#39;/g, "'")
          .replace(/&lt;/g, '<')
          .replace(/&gt;/g, '>')
          .replace(/&amp;/g, '&')
        );
        return `<code class="d-inline-block">${parsed}</code>`;
      },
    },
  });
}

window.markLine = markLine;
window.removeMark = removeMark;
window.hoverLine = hoverLine;
window.addCommentToLine = addCommentToLine;

window.addEventListener('load', () => {
  const codeElementData = document.getElementById('code-view').dataset;
  window.solutionId = codeElementData.id;
  window.fileId = codeElementData.file;
  window.exerciseId = codeElementData.exercise;
  sessionStorage.setItem('role', codeElementData.role);
  sessionStorage.setItem('solver', codeElementData.solver);
  sessionStorage.setItem('solverId', codeElementData.solverId);
  sessionStorage.setItem('allowedComment', codeElementData.allowedComment);
  customElements.define('comment-line', LineComment);
  window.dispatchEvent(new Event('defined-window-variables'));
});

window.addEventListener('lines-numbered', () => {
  configureMarkdownParser();
  pullComments(window.fileId, treatComments);
  window.dispatchEvent(new Event('fully-loaded'));
});
