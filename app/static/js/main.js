// File upload handling
const uploadArea = document.getElementById("upload-area");
const fileInput = document.getElementById("file");
const uploadPrompt = document.getElementById("upload-prompt");
const fileInfo = document.getElementById("file-info");
const fileName = document.getElementById("file-name");

if (uploadArea && fileInput) {
  uploadArea.addEventListener("click", () => fileInput.click());
  uploadArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadArea.classList.add("drag-over");
  });
  uploadArea.addEventListener("dragleave", () => {
    uploadArea.classList.remove("drag-over");
  });
  uploadArea.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadArea.classList.remove("drag-over");
    if (e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      updateFileDisplay();
    }
  });
  fileInput.addEventListener("change", updateFileDisplay);
  function updateFileDisplay() {
    if (fileInput.files.length) {
      fileName.textContent = fileInput.files[0].name;
      uploadPrompt.classList.add("hidden");
      fileInfo.classList.remove("hidden");
    }
  }
}

// Form submission with animation
const form = document.getElementById("upload-form");
if (form) {
  form.addEventListener("submit", function () {
    const button = document.getElementById("submit-button");
    const buttonText = document.getElementById("button-text");
    const spinner = button.querySelector(".spinner");
    button.disabled = true;
    button.classList.remove("hover:bg-green-600");
    button.classList.add("bg-gray-700", "text-white");
    buttonText.textContent = "PROCESSING";
    spinner.classList.remove("hidden");
    spinner.classList.add("spinner-loading"); // Animate flow diagram
    animateFlow();
  });
}

// Flow diagram animation
function animateFlow() {
  const nodes = [
    "node-s3",
    "node-eventbridge",
    "node-stepfn",
    "node-lambda1",
    "node-lambda2",
    "node-output",
  ];
  const arrows = ["arrow-1", "arrow-2", "arrow-3", "arrow-4", "arrow-5"];
  nodes.forEach((id, index) => {
    setTimeout(() => {
      document.getElementById(id)?.classList.add("active");
      if (arrows[index]) {
        document.getElementById(arrows[index])?.classList.add("active");
      }
    }, index * 400);
  });
}

// SORTABLE OPERATION PIPELINE
const operationsList = document.getElementById("operations-list");
const orderInput = document.getElementById("operations_order");

function updateOperationsOrder() {
  const items = [...operationsList.querySelectorAll(".operation-item")];

  // Get the ordered list of values for the backend
  const ordered = items
    .filter((item) => item.querySelector('input[type="checkbox"]').checked)
    .map((item) => item.querySelector("input").value);

  orderInput.value = JSON.stringify(ordered);

  // Update the visual numbering
  items.forEach((item, index) => {
    const indexSpan = item.querySelector(".operation-index");
    if (indexSpan) {
      indexSpan.textContent = `0${index + 1}`.slice(-2);
    }
  });
}

if (operationsList) {
  new Sortable(operationsList, {
    animation: 150,
    ghostClass: "opacity-30",
    onSort: updateOperationsOrder,
  });

  // Update order when checkboxes change
  operationsList.querySelectorAll('input[type="checkbox"]').forEach((chk) => {
    chk.addEventListener("change", updateOperationsOrder);
  });
}
