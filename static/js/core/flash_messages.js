document.addEventListener("DOMContentLoaded", () => {
  const data = document.getElementById("flashMessagesData");
  if (!data) return;

  const titles = {
    success: "??",
    danger: "??",
    warning: "??",
  };

  JSON.parse(data.textContent || "[]").forEach(([category, message]) => {
    Swal.fire({
      icon: category === "danger" ? "error" : (category || "info"),
      title: titles[category] || "??",
      text: message,
      confirmButtonColor: "#2563eb",
    });
  });
});
