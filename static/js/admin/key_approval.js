document.querySelectorAll("[data-reject-url]").forEach((button) => {
    button.addEventListener("click", () => {
      const form = document.getElementById("rejectApplicationForm");
      form.action = button.dataset.rejectUrl;
      document.getElementById("rejectApplicationHint").textContent = `請填寫「${button.dataset.userName}」的拒絕原因。`;
      document.getElementById("rejectReason").value = "";
      const modal = new bootstrap.Modal(document.getElementById("rejectApplicationModal"));
      modal.show();
      document.getElementById("rejectApplicationModal").addEventListener("shown.bs.modal", () => document.getElementById("rejectReason").focus(), { once: true });
    });
  });
