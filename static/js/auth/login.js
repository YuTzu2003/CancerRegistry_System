document.addEventListener("DOMContentLoaded", () => {
  const data = document.getElementById("loginFlashMessagesData");
  const titles = {
    success: "??",
    danger: "??",
    warning: "??",
  };

  if (data) {
    JSON.parse(data.textContent || "[]").forEach(([category, message]) => {
      Swal.fire({
        icon: category === "danger" ? "error" : (category || "info"),
        title: titles[category] || "??",
        text: message,
        confirmButtonColor: "#2563eb",
      });
    });
  }

  const errorData = document.getElementById("loginErrorData");
  if (errorData) {
    Swal.fire({
      icon: "error",
      title: "??",
      text: JSON.parse(errorData.textContent || "null"),
      confirmButtonColor: "#2563eb",
    });
  }
});
