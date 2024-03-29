function isNumeric(str) {
  return /^\d+$/.test(str);
}

function hideAllOpenComments() {
  const popovers = Array.from(document.querySelectorAll('[data-comment="true"]'));
  popovers.forEach((popoverElement) => {
    const popover = bootstrap.Popover.getInstance(popoverElement);
    if (popover !== null) {
      popover.hide();
    }
  });
}

function destroyCommentsNotations(comments) {
  Array.from(comments).forEach((comment) => {
    comment.removeAttribute('data-vimkey');
    const popover = bootstrap.Popover.getInstance(comment);
    if (popover !== null) {
      popover.dispose();
    }
  });
}

function showCommentsNotations(comments) {
  Array.from(comments).forEach((comment, id) => {
    const vimkey = String.fromCharCode(97 + id);
    const commentPopover = new bootstrap.Popover(comment, { content: vimkey });
    commentPopover.show();
    comment.dataset.vimkey = vimkey;
  });
}

function highlightLinesThatStartsWith(lineNumber, enable) {
  const highlight = enable || (enable === undefined);
  const specificSelector = lineNumber && `^='${lineNumber}'`;
  const lines = document.querySelectorAll(
    `#code-view .line-container[data-line${specificSelector}]`,
  );
  Array.from(lines).forEach((line) => {
    line.dataset.vimbackground = highlight;
  });
}

function listenToKeys() {
  const ninja = document.getElementById('ninja');
  const knownComments = document.getElementsByClassName('known-comment');

  let vim;
  let lineMode;
  let letterMode;
  let lineNumber;

  function resetStatus() {
    ninja.style.display = 'none';
    vim = false;
    lineMode = false;
    letterMode = false;
    lineNumber = '';
    destroyCommentsNotations(knownComments || []);
    hideAllOpenComments();
    highlightLinesThatStartsWith('', false);
  }

  resetStatus();
  document.addEventListener('keydown', (event) => {
    if (['textarea', 'input'].includes(event.target.tagName.toLowerCase())) {
      return;
    }
    const key = event.key.toLowerCase();
    const linesSelected = `#code-view .line-container[data-line='${lineNumber}']`;
    const graderAddButton = `.grader-add[data-line='${lineNumber}']`;
    if (key === 'q') {
      event.preventDefault();
      if (lineMode === true) {
        if (document.querySelectorAll(linesSelected).length !== 1) {
          alert('You must select only a unique, single line.');
          resetStatus();
        } else {
          lineMode = false;
          letterMode = true;
          if (lineNumber !== '') {
            showCommentsNotations(knownComments);
          }
        }
      } else {
        vim = true;
        lineMode = true;
        ninja.style.display = 'flex';
        lineNumber = '';
      }
    } else if (isNumeric(key) && lineMode === true) {
      event.preventDefault();
      highlightLinesThatStartsWith(lineNumber, false);
      lineNumber += key;
      highlightLinesThatStartsWith(lineNumber);
    } else if (['-', '='].includes(key)) {
      event.preventDefault();
      highlightLinesThatStartsWith(lineNumber, false);
      lineNumber = document.querySelector('.line:last-of-type').dataset.line;
      highlightLinesThatStartsWith(lineNumber);
    } else if (letterMode && key.length === 1 && key >= 'a' && key <= 'z') {
      event.preventDefault();
      const commentId = document.querySelector(
        `.known-comment[data-vimkey='${key}']`,
      ).dataset.commentid;
      if (commentId && lineNumber) {
        window.sendExistsComment(window.fileId, lineNumber, commentId);
        resetStatus();
      }
    } else if (letterMode && (key === '`' || key === ';')) {
      event.preventDefault();
      document.querySelector(graderAddButton).click();
    } else if (key === 'escape') {
      event.preventDefault();
      if (lineMode === true || letterMode === true) {
        resetStatus();
      }
    } else if (key === '!') {
      event.preventDefault();
      document.getElementById('save-check').click();
    }

    if (vim === false) {
      resetStatus();
    }
  });
}

window.addEventListener('lines-numbered', () => {
  listenToKeys();
});
