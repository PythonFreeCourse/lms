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

function changeAssessmentsAttributes(assessmentGroup, item) {
  if (item.value == assessmentGroup.dataset.checkedid) {
    item.removeAttribute('checked');
    item.checked = false;
    assessmentGroup.dataset.checkedid = null;
  } else {
    assessmentGroup.dataset.checkedid = item.value;
  }
  document.activeElement.blur();

  const xhr = new XMLHttpRequest();
  xhr.open('POST', `/assessment/${solutionId}`, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.responseType = 'json';
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        if (xhr.status !== 200) {
          console.log(xhr.status);
        }
      }
    };

    xhr.send(JSON.stringify({assessment: assessmentGroup.dataset.checkedid}));
}

function trackAssessmentButtons() {
  const assessmentGroup = document.getElementById('solution-assessment');
  const assessmentElements = document.querySelectorAll('input[name="assessment"]');
  Array.from(assessmentElements).forEach((item) => {
    item.addEventListener('click', () => {
      changeAssessmentsAttributes(assessmentGroup, item);
    }, true);
  });
}

window.addEventListener('lines-numbered', () => {
  trackFinished(window.exerciseId, window.solutionId, document.getElementById('save-check'));
  trackAssessmentButtons();
});
