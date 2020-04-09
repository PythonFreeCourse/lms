function isNumeric(str){
    return /^\d+$/.test(str);
}

function hideAllOpenComments() {
  $("[data-toggle='popover']").popover('hide'); 
}

function destroyCommentsNotations(comments) {
  Array.from(comments).forEach((comment) => {
    comment.removeAttribute('data-vimkey');
  });
  $(comments).popover('dispose');
}


function showCommentsNotations(comments) {
  Array.from(comments).forEach((comment, id) => {
    const vimkey = String.fromCharCode(97 + id);
    $(comment).popover({'content': vimkey});
    $(comment).popover('show');
    comment.dataset.vimkey = vimkey;
  });
  $(comments).popover();
}


function highlightLinesThatStartsWith(lineNumber, enable) {
  const highlight = enable || (enable === undefined ? true : false);
  const specificSelector = lineNumber && `^="${lineNumber}"`;
  const lines = document.querySelectorAll(`.line[data-line${specificSelector}]`);
  Array.from(lines).forEach(line => {
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
    destroyCommentsNotations(knownComments);
    hideAllOpenComments();
    highlightLinesThatStartsWith('', false);
  }

  resetStatus();
  document.addEventListener('keydown', function(event) {
    if (['textarea', 'input'].includes(event.target.tagName.toLowerCase())) { return; }
    let key = event.key.toLowerCase();
    if (key == 'q') {
      event.preventDefault();
      if (lineMode === true) {
        if (document.querySelectorAll(`.line[data-line="${lineNumber}"]`).length != 1) {
          alert('You must select only a unique, single line.');
          return resetStatus();
        }
        lineMode = false;
        letterMode = true;
        if (lineNumber !== '') {
          showCommentsNotations(knownComments);
        }
      } else {
        vim = true;
        lineMode = true;
        ninja.style.display = 'flex';
        lineNumber = '';
      }
    } else if (isNumeric(key) && (lineMode === true)) {
      event.preventDefault();
      highlightLinesThatStartsWith(lineNumber, false);
      lineNumber += key;
      highlightLinesThatStartsWith(lineNumber);
    } else if (['-', '='].includes(key)) {
      event.preventDefault();
      highlightLinesThatStartsWith(lineNumber, false);
      lineNumber = document.querySelector(".line:last-of-type").dataset.line;
      highlightLinesThatStartsWith(lineNumber);
    } else if (letterMode && key.length == 1 && key >= 'a' && key <= 'z') {
      event.preventDefault();
      const comment = document.querySelector(`.known-comment[data-vimkey="${key}"]`);
      const commentId = comment.dataset.commentid;
      if (commentId && lineNumber) {
        window.sendExistsComment(window.solutionId, lineNumber, commentId);
        resetStatus();
      }
    } else if (letterMode && (key == "`" || key == ";")) {
      event.preventDefault();
      document.querySelector(`[data-line="${lineNumber}"]`).click();
    } else if (key == 'escape') {
      event.preventDefault();
      if ((lineMode === true) || (letterMode === true)) {
        resetStatus();
      }
    } else if (key == '!') {
      event.preventDefault();
      return document.getElementById('save-check').click();
    } else {
    }

    if (vim === false) {
      resetStatus();
    }
  });
}


window.addEventListener("lines-numbered", () => {
  listenToKeys();
});
