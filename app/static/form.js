const form = document.querySelector(".form");
const fileInput = document.querySelector(".file-input");
const uploadError = document.querySelector("[data-upload-error]");
const submitButton = form?.querySelector('button[type="submit"]');
const nameInputs = document.querySelectorAll("[data-name-input]");

function setPhotoError(message) {
  uploadError.textContent = message;
  fileInput.setCustomValidity(message);
  submitButton.disabled = Boolean(message);
}

function formatName(value) {
  return value
    .trimStart()
    .split("-")
    .map((part) => (part ? part[0].toUpperCase() + part.slice(1).toLowerCase() : part))
    .join("-");
}

nameInputs.forEach((input) => {
  input.addEventListener("blur", () => {
    input.value = formatName(input.value);
  });
});

if (fileInput && uploadError && submitButton) {
  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    setPhotoError("");

    if (!file) {
      return;
    }

    if (file.size > Number(fileInput.dataset.maxSize)) {
      setPhotoError("Размер фото не должен превышать 200 КБ");
    }
  });

  form.addEventListener("submit", (event) => {
    const file = fileInput.files[0];
    if (file && file.size > Number(fileInput.dataset.maxSize)) {
      event.preventDefault();
      setPhotoError("Размер фото не должен превышать 200 КБ");
    }
  });
}
