document.querySelector(".recalc-index").addEventListener("click", (event) => {
  const link = event.target.closest("a");
  if (!link) return;

  const cancer = document.getElementById(link.hash.slice(1));
  if (cancer) cancer.open = true;
});

const fileInput = document.getElementById("case-file");
if (fileInput) {
  fileInput.addEventListener("change", () => {
    const label = document.getElementById("recalc-file-name");
    if (label) label.textContent = fileInput.files[0]?.name || "尚未選擇檔案";
  });
}
