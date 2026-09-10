document.querySelectorAll(".audit-detail").forEach((button) => {
  button.addEventListener("click", () => {
    Swal.fire({
      title: "異動詳細內容",
      html: `<pre class="text-start mb-0">${button.dataset.detail}</pre>`,
      confirmButtonColor: "#2563eb",
      width: 680,
    });
  });
});
