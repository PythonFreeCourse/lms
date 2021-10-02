function trackFinished(exerciseId, solutionId, element) {
  element.addEventListener('click', () => {
    const grade = document.querySelector('input[name="grade-mark"]:checked');
    const gradeValue = grade.value;
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

    xhr.send(JSON.stringify({
      grade: gradeValue,
    }));
  });
}

window.addEventListener('lines-numbered', () => {
  trackFinished(window.exerciseId, window.solutionId, document.getElementById('save-check'));
});
