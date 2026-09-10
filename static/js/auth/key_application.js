document.querySelectorAll(".copy-key").forEach((button) => {
    button.addEventListener("click", async () => {
      const response = await fetch(button.dataset.copyUrl);
      const data = await response.json();
      if (!response.ok) {
        Swal.fire({ icon: 'error', title: '複製失敗', text: data.error, confirmButtonColor: '#2563eb' });
        return;
      }
      await navigator.clipboard.writeText(data.key);
      button.innerHTML = '<i class="bi bi-check-lg"></i>';
      button.setAttribute("aria-label", "已複製 Key");
    });
  });
