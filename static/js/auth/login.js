document.addEventListener("DOMContentLoaded", () => {
  const data = document.getElementById("loginFlashMessagesData");
  const titles = {
    success: "成功",
    danger: "錯誤",
    warning: "提醒",
  };

  if (data) {
    JSON.parse(data.textContent || "[]").forEach(([category, message]) => {
      Swal.fire({
        icon: category === "danger" ? "error" : (category || "info"),
        title: titles[category] || "通知",
        text: message,
        confirmButtonColor: "#2563eb",
      });
    });
  }

  const errorData = document.getElementById("loginErrorData");
  if (errorData) {
    Swal.fire({
      icon: "error",
      title: "錯誤",
      text: JSON.parse(errorData.textContent || "null"),
      confirmButtonColor: "#2563eb",
    });
  }
});
