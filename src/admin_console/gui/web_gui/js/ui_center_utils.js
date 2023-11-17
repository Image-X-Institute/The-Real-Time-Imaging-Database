const createCenterButton = document.getElementById("createNewCenter");
const centerName = document.getElementById("centerName");
const centerFullName = document.getElementById("centerFullName");
const centerLocation = document.getElementById("centerLocation");
const clearCenterButton = document.getElementById("clearCenterButton");

createCenterButton.addEventListener("click", (event) => {
  createCenter();
});

centerName.addEventListener("input", (event) => {
  changeCreateCenterButton();
});

clearCenterButton.addEventListener("click", (event) => {
  centerName.value = "";
  centerFullName.value = "";
  centerLocation.value = "";
  changeCreateCenterButton();
});

const changeCreateCenterButton = () => {
  if (centerName.value != "") {
    createCenterButton.disabled = false;
  } else {    
    createCenterButton.disabled = true;
  }
}

const createCenter = () => {
  const pack = {
    "name": centerName.value,
    "fullName": centerFullName.value,
    "location": centerLocation.value,
    "type": "site"
  };
  fetch("http://localhost:8090/add-site-trial", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(pack)
  }).then((response) => {
    if (response.status == 200) {
      alert("Center created successfully!");
      centerName.value = "";
      centerFullName.value = "";
      centerLocation.value = "";
      changeCreateCenterButton();
    } else {
      alert("Center creation failed!");
    }
  });
}