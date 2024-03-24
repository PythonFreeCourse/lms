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

window.addEventListener('load', () => {
  addLineSpansToPre(document.getElementsByTagName('code'));
});
