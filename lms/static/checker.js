function trackFinished(exerciseId, solutionId, element) {
  element.addEventListener('click', () => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `/checked/${exerciseId}/${solutionId}`, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.responseType = 'json';
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          if (xhr.response.next !== null) {
            window.location.href = `/view/${xhr.response.next}`;
          } else {
            alert("Yay! That's it!");
          }
        } else {
          console.log(xhr.status);
        }
      }
    };

    xhr.send(JSON.stringify({}));
  });
}

window.addEventListener('lines-numbered', () => {
  trackFinished(window.exerciseId, window.solutionId, document.getElementById('save-check'));
});
