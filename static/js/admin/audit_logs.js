document.querySelectorAll(".audit-detail").forEach((button) => {
  button.addEventListener("click", () => {
    const detail = document.createElement("pre");
    detail.className = "text-start mb-0";
    detail.textContent = button.dataset.detail;
    Swal.fire({
      title: "異動詳細內容",
      html: detail,
      confirmButtonColor: "#2563eb",
      width: 680,
    });
  });
});
