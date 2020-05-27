const templatedWords = /\$\{(\w+?)\}/g;


function escapeUnicode(str) {
  // Thanks to https://stackoverflow.com/a/45315988
  const json = JSON.stringify(str);
  return json.replace(/[\u007F-\uFFFF]/g, (chr) => {
    const step1 = chr.charCodeAt(0).toString(16);
    const step2 = `0000${step1}`.substr(-4);
    return `\\u${step2}`;
  });
}


String.prototype.format = function(kwargs) {
  return text.replace(templatedWords, function(wholeMatch, identifier) {
    const isReplacementExists = Object.keys(kwargs).includes(identifier);
    return isReplacementExists ? kwargs[identifier] : identifier;
  });
}


window.escapeUnicode = escapeUnicode;
