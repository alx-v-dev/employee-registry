const form = document.querySelector(".form");
const fileInput = document.querySelector(".file-input");
const uploadError = document.querySelector("[data-upload-error]");
const submitButton = form?.querySelector('button[type="submit"]');
const nameInputs = document.querySelectorAll("[data-name-input]");
const phoneInput = document.querySelector("[data-phone-input]");

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

function formatPhone(value) {
  const digits = value.replace(/\D/g, "");
  if (!digits) {
    return "";
  }
  let normalized = digits;
  if (normalized.startsWith("8")) {
    normalized = `7${normalized.slice(1)}`;
  }
  if (!normalized.startsWith("7")) {
    normalized = `7${normalized}`;
  }
  normalized = normalized.slice(0, 11);

  const parts = [
    normalized.slice(1, 4),
    normalized.slice(4, 7),
    normalized.slice(7, 9),
    normalized.slice(9, 11),
  ];

  let result = "+7";
  if (parts[0]) result += ` (${parts[0]}`;
  if (parts[0].length === 3) result += ")";
  if (parts[1]) result += ` ${parts[1]}`;
  if (parts[2]) result += `-${parts[2]}`;
  if (parts[3]) result += `-${parts[3]}`;
  return result;
}

nameInputs.forEach((input) => {
  input.addEventListener("blur", () => {
    input.value = formatName(input.value);
  });
});

if (phoneInput) {
  phoneInput.addEventListener("input", () => {
    phoneInput.value = formatPhone(phoneInput.value);
  });
}

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
