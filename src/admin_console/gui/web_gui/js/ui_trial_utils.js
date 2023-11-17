

const createTrialButton = document.getElementById("createNewTrial");
const uploadFile = document.getElementById("trialFolderStructureFile");
const trialName = document.getElementById("trialName");
const trialFullName = document.getElementById("trialFullName");
const clearButton = document.getElementById("clearButton");

createTrialButton.addEventListener("click", (event) => {
  createTrial();
});

trialName.addEventListener("input", (event) => {
  changeCreateButton();
});

trialFullName.addEventListener("input", (event) => {
  changeCreateButton();
});

uploadFile.addEventListener("change", (event) => {
  changeCreateButton();
});

clearButton.addEventListener("click", (event) => {
  trialName.value = "";
  trialFullName.value = "";
  uploadFile.value = "";
  changeCreateButton();
});

const uploadFileValidation = (file) => {
  console.log(file);
}

const changeCreateButton = () => {
  if (trialName.value != "" && trialFullName.value != "" && uploadFile.value != "") {
    createTrialButton.disabled = false;
  } else {    
    createTrialButton.disabled = true;
  }
}
const createTrial = () => {
  file = uploadFile.files[0];
  const reader = new FileReader();
  reader.readAsText(file);
  reader.onload = readerEvent => {
    const content = readerEvent.target.result;
    const jsonData = JSON.parse(content);
    const package = {
      "fileStructure": jsonData,
      "trialDetails": {
        "trialName": trialName.value,
        "trialFullName": trialFullName.value
      }
    }
    fetch("http://localhost:8090/trial-structure/addNewTrial", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(package)
    }).then(response => {
      if (response.status == 200) {
        alert("Trial created successfully");
        trialName.value = "";
        trialFullName.value = "";
        uploadFile.value = "";
        changeCreateButton();
      }
    })
  }
}