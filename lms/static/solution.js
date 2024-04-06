function updateOpenedSpans(currentSpans, line) {
  /* This function manages the state of open span tags by using regular expressions
   * to find span tags and adjust the currentSpans array accordingly.
   */
  const spanRegex = /<span[^>]*>|<\/span>/g;
  let match;

  while ((match = spanRegex.exec(line)) !== null) {
    if (match[0] === '</span>') {
      currentSpans.pop();
    } else {
      currentSpans.push(match[0]);
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

window.addEventListener('defined-window-variables', () => {
  addLineSpansToPre(document.getElementsByTagName('code'));
}, { once: true });
